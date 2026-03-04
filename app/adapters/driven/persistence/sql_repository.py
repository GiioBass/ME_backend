from typing import Optional, List, Dict, Any
from sqlmodel import Session, select, delete
from app.ports.repositories import GameRepository
from app.core.domain.player import Player, Stats
from app.core.domain.location import Location, Coordinates
from app.core.domain.item import Item
from app.core.domain.enemy import Enemy
from app.adapters.driven.persistence.sql_models import (
    PlayerDB, PlayerStatsDB, InventoryItemDB, EquipmentDB, WaypointDB,
    LocationDB, LocationExitDB, LocationInteractableDB, LocationItemDB,
    EnemyDB, LocationEnemyDB, ItemDB, WorldStateDB, CommandHelpDB, RecipeDB
)
from app.adapters.driven.persistence.db_config import engine

class SQLGameRepository(GameRepository):
    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    # --- Player Persistence ---
    def get_player(self, player_id: str) -> Optional[Player]:
        with Session(self.engine) as session:
            db_player = session.get(PlayerDB, player_id)
            if not db_player: return None
            
            # Stats
            db_stats = session.get(PlayerStatsDB, player_id)
            stats = Stats(**db_stats.model_dump()) if db_stats else Stats()
            
            # Inventory
            inventory = []
            inv_items = session.exec(
                select(InventoryItemDB, ItemDB)
                .join(ItemDB, InventoryItemDB.item_id == ItemDB.id)
                .where(InventoryItemDB.player_id == player_id)
            ).all()
            for inv_link, db_item in inv_items:
                item = db_item.to_domain()
                # For now we don't have qty in domain Item, but we could add it back.
                # If qty > 1, we might need to duplicate or handle it.
                for _ in range(inv_link.quantity):
                    inventory.append(item)
            
            # Equipment
            equipment = {"weapon": None, "armor": None}
            db_equip = session.get(EquipmentDB, player_id)
            if db_equip:
                if db_equip.weapon_id:
                    item_db = session.get(ItemDB, db_equip.weapon_id)
                    if item_db: equipment["weapon"] = item_db.to_domain()
                if db_equip.armor_id:
                    item_db = session.get(ItemDB, db_equip.armor_id)
                    if item_db: equipment["armor"] = item_db.to_domain()
            
            # Waypoints
            waypoints = {}
            db_waypoints = session.exec(select(WaypointDB).where(WaypointDB.player_id == player_id)).all()
            for wp in db_waypoints:
                waypoints[wp.name] = wp.location_id
                
            player = Player(
                id=db_player.id,
                name=db_player.name,
                current_location_id=db_player.current_location_id,
                stats=stats,
                inventory=inventory,
                equipment=equipment,
                waypoints=waypoints
            )
            return player

    def get_player_by_name(self, name: str) -> Optional[Player]:
        with Session(self.engine) as session:
            db_player = session.exec(select(PlayerDB).where(PlayerDB.name == name)).first()
            if db_player:
                return self.get_player(db_player.id)
            return None

    def save_player(self, player: Player) -> Player:
        with Session(self.engine) as session:
            # 1. Save Player Core
            db_player = PlayerDB(id=player.id, name=player.name, current_location_id=player.current_location_id)
            session.merge(db_player)
            
            # 2. Save Stats
            db_stats = PlayerStatsDB(player_id=player.id, **player.stats.model_dump())
            session.merge(db_stats)
            
            # 3. Handle Items (Inventory & Equipment)
            all_items = player.inventory + [i for i in player.equipment.values() if i]
            for item in all_items:
                session.merge(ItemDB.from_domain(item))
            
            # 4. Save Inventory (Clear and Rebuild)
            session.exec(delete(InventoryItemDB).where(InventoryItemDB.player_id == player.id))
            from collections import Counter
            item_counts = Counter(item.id for item in player.inventory)
            for item_id, qty in item_counts.items():
                session.add(InventoryItemDB(player_id=player.id, item_id=item_id, quantity=qty))
                
            # 5. Save Equipment
            db_equip = EquipmentDB(
                player_id=player.id,
                weapon_id=player.equipment.get("weapon").id if player.equipment.get("weapon") else None,
                armor_id=player.equipment.get("armor").id if player.equipment.get("armor") else None
            )
            session.merge(db_equip)
            
            # 6. Save Waypoints
            session.exec(delete(WaypointDB).where(WaypointDB.player_id == player.id))
            for name, loc_id in player.waypoints.items():
                session.add(WaypointDB(player_id=player.id, name=name, location_id=loc_id))
            
            session.commit()
            return player

    # --- Location Persistence ---
    def get_location(self, location_id: str) -> Optional[Location]:
        with Session(self.engine) as session:
            db_loc = session.get(LocationDB, location_id)
            if not db_loc: return None
            
            # Exits
            exits = {e.direction: e.destination_id for e in session.exec(select(LocationExitDB).where(LocationExitDB.location_id == location_id)).all()}
            
            # Interactables
            interactables = [i.name for i in session.exec(select(LocationInteractableDB).where(LocationInteractableDB.location_id == location_id)).all()]
            
            # Items
            items = []
            camp_storage = []
            loc_items = session.exec(
                select(LocationItemDB, ItemDB)
                .join(ItemDB, LocationItemDB.item_id == ItemDB.id)
                .where(LocationItemDB.location_id == location_id)
            ).all()
            for link, db_item in loc_items:
                if link.is_camp_storage:
                    camp_storage.append(db_item.to_domain())
                else:
                    items.append(db_item.to_domain())
            
            # Enemies
            enemies = []
            loc_enemies = session.exec(
                select(LocationEnemyDB, EnemyDB)
                .join(EnemyDB, LocationEnemyDB.enemy_id == EnemyDB.id)
                .where(LocationEnemyDB.location_id == location_id)
            ).all()
            for link, db_enemy in loc_enemies:
                enemies.append(Enemy(**db_enemy.model_dump()))
                
            return Location(
                id=db_loc.id,
                name=db_loc.name,
                description=db_loc.description,
                exits=exits,
                interactables=interactables,
                items=items,
                camp_storage=camp_storage,
                enemies=enemies,
                coordinates=Coordinates(x=db_loc.x, y=db_loc.y, z=db_loc.z),
                is_dark=db_loc.is_dark,
                trap_damage=db_loc.trap_damage
            )

    def create_location(self, location: Location):
        with Session(self.engine) as session:
            # 1. Base Location
            db_loc = LocationDB(
                id=location.id,
                name=location.name,
                description=location.description,
                x=location.coordinates.x if location.coordinates else 0,
                y=location.coordinates.y if location.coordinates else 0,
                z=location.coordinates.z if location.coordinates else 0,
                is_dark=location.is_dark,
                trap_damage=location.trap_damage
            )
            session.merge(db_loc)
            
            # 2. Exits
            session.exec(delete(LocationExitDB).where(LocationExitDB.location_id == location.id))
            for direction, dest in location.exits.items():
                session.add(LocationExitDB(location_id=location.id, direction=direction, destination_id=dest))
                
            # 3. Interactables
            session.exec(delete(LocationInteractableDB).where(LocationInteractableDB.location_id == location.id))
            for name in location.interactables:
                session.add(LocationInteractableDB(location_id=location.id, name=name))
                
            # 4. Items (Ground and Storage)
            session.exec(delete(LocationItemDB).where(LocationItemDB.location_id == location.id))
            for item in location.items:
                session.merge(ItemDB.from_domain(item))
                session.add(LocationItemDB(location_id=location.id, item_id=item.id, is_camp_storage=False))
            for item in location.camp_storage:
                session.merge(ItemDB.from_domain(item))
                session.add(LocationItemDB(location_id=location.id, item_id=item.id, is_camp_storage=True))
                
            # 5. Enemies
            session.exec(delete(LocationEnemyDB).where(LocationEnemyDB.location_id == location.id))
            for enemy in location.enemies:
                session.merge(EnemyDB(**enemy.model_dump()))
                session.add(LocationEnemyDB(location_id=location.id, enemy_id=enemy.id))
                
            session.commit()

    def get_location_by_coordinates(self, x: int, y: int, z: int) -> Optional[Location]:
        with Session(self.engine) as session:
            # Optimized direct query!
            db_loc = session.exec(select(LocationDB).where(LocationDB.x == x, LocationDB.y == y, LocationDB.z == z)).first()
            if db_loc:
                return self.get_location(db_loc.id)
            return None

    def get_locations_in_radius(self, x: int, y: int, z: int, radius: int) -> list[Location]:
        with Session(self.engine) as session:
            # Optimized range query
            statement = select(LocationDB).where(
                LocationDB.z == z,
                LocationDB.x >= x - radius,
                LocationDB.x <= x + radius,
                LocationDB.y >= y - radius,
                LocationDB.y <= y + radius
            )
            db_locs = session.exec(statement).all()
            return [self.get_location(loc.id) for loc in db_locs if not (loc.x == x and loc.y == y)]

    # --- Time Persistence ---
    def get_world_time(self):
        from app.core.domain.time_system import WorldTime
        with Session(self.engine) as session:
            state = session.get(WorldStateDB, "world_state")
            return WorldTime(total_ticks=state.total_ticks if state else 0)

    def save_world_time(self, world_time):
        with Session(self.engine) as session:
            state = WorldStateDB(id="world_state", total_ticks=world_time.total_ticks)
            session.merge(state)
            session.commit()

    def get_command_help(self) -> list[Dict[str, Any]]:
        with Session(self.engine) as session:
            commands = session.exec(select(CommandHelpDB)).all()
            return [cmd.model_dump() for cmd in commands]

    def create_command_help(self, command: str, description: str, usage: str, category: str, alias: Optional[str] = None):
        with Session(self.engine) as session:
            existing = session.exec(select(CommandHelpDB).where(CommandHelpDB.command == command)).first()
            if not existing:
                db_cmd = CommandHelpDB(
                    command=command,
                    alias=alias,
                    description=description,
                    usage=usage,
                    category=category
                )
                session.add(db_cmd)
                session.commit()

    def save_item(self, item: Item):
        with Session(self.engine) as session:
            session.merge(ItemDB.from_domain(item))
            session.commit()

    def get_recipes(self) -> List[Any]:
        with Session(self.engine) as session:
            db_recipes = session.exec(
                select(RecipeDB, ItemDB)
                .join(ItemDB, RecipeDB.result_item_id == ItemDB.id)
            ).all()
            
            recipes = []
            for db_recipe, db_item in db_recipes:
                recipes.append(db_recipe.to_domain(result_item=db_item.to_domain()))
            return recipes

    def create_recipe(self, recipe: Any):
        with Session(self.engine) as session:
            # Check for existing recipe by name to avoid IntegrityError on unique name
            existing = session.exec(select(RecipeDB).where(RecipeDB.name == recipe.name)).first()
            db_recipe = RecipeDB.from_domain(recipe)
            if existing:
                # Use same ID as existing to update correctly via merge
                db_recipe.id = existing.id
            session.merge(db_recipe)
            session.commit()

    def get_items_by_type(self, item_type: str) -> List[Item]:
        with Session(self.engine) as session:
            db_items = session.exec(select(ItemDB).where(ItemDB.item_type == item_type)).all()
            return [item.to_domain() for item in db_items]

    def get_item_by_name(self, name_or_id: str) -> Optional[Item]:
        with Session(self.engine) as session:
            # 1. Try by ID
            db_item = session.get(ItemDB, name_or_id)
            if db_item:
                return db_item.to_domain()
            
            # 2. Try by Name (Case-insensitive)
            db_item = session.exec(select(ItemDB).where(ItemDB.name.ilike(name_or_id))).first()
            if db_item:
                return db_item.to_domain()
            
            return None
