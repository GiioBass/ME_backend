from typing import Tuple
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.ports.repositories import GameRepository
from app.core.use_cases.world_generator import WorldGenerator
from app.core.use_cases.static_area_loader import StaticAreaLoader
from collections import Counter
import random
from app.core.config import settings

class GameService:
    def __init__(self, repository: GameRepository):
        self.repo = repository
        from app.core.use_cases.data_loader import DataLoader
        loader = DataLoader(repository)
        self.world_config = loader.get_world_config()
        self.loot_tables = loader.get_loot_tables()
        self.enemies_config = loader.get_enemies_config()
        self.game_settings = loader.get_game_settings()

        self.world_gen = WorldGenerator(
            repo=repository, 
            world_config=self.world_config, 
            loot_tables=self.loot_tables, 
            enemies_config=self.enemies_config
        )
        self.static_area_loader = StaticAreaLoader()
        from app.core.use_cases.dungeon_generator import DungeonGenerator
        self.dungeon_gen = DungeonGenerator(
            repo=repository, 
            loot_tables=self.loot_tables, 
            enemies_config=self.enemies_config
        )
        self._setup_command_registry()

    def _setup_command_registry(self):
        self.registry = {
            # Movement
            "north": self._cmd_move, "n": self._cmd_move,
            "south": self._cmd_move, "s": self._cmd_move,
            "east": self._cmd_move, "e": self._cmd_move,
            "west": self._cmd_move, "w": self._cmd_move,
            "up": self._cmd_move, "u": self._cmd_move,
            "down": self._cmd_move, "d": self._cmd_move,
            "go": self._cmd_move, "move": self._cmd_move, "walk": self._cmd_move,
            "enter": self._cmd_move, "climb": self._cmd_move,
            
            # General
            "look": lambda p, a: self.look(p), "l": lambda p, a: self.look(p),
            "examine": lambda p, a: self.look(p),
            "stats": self._cmd_stats, "status": self._cmd_stats,
            "inventory": lambda p, a: self.map_inventory(p), "inv": lambda p, a: self.map_inventory(p), "i": lambda p, a: self.map_inventory(p),
            "time": self._cmd_time,
            "help": self._cmd_help,
            "clear": lambda p, a: ("Terminal cleared.", *self._get_player_and_location(p)),
            "scout": self._cmd_scout, "radar": self._cmd_scout, "map": self._cmd_scout,

            # Interaction
            "take": self.take_item, "get": self.take_item, "pickup": self.take_item, "grab": self.take_item,
            "drop": self.drop_item, "discard": self.drop_item,
            "consume": self._cmd_consume, "eat": self._cmd_consume, "drink": self._cmd_consume, "use": self._cmd_consume,
            "fill": self.fill_flask, "refill": self.fill_flask,
            "attack": self.attack_enemy, "fight": self.attack_enemy, "hit": self.attack_enemy, "kill": self.attack_enemy,

            # Advanced
            "equip": self.equip_item, "wear": self.equip_item, "wield": self.equip_item,
            "unequip": self.unequip_item, "remove": self.unequip_item,
            "camp": self.create_camp, "waypoint": self.create_camp,
            "travel": self.fast_travel, "fasttravel": self.fast_travel,
            "rest": lambda p, a: self.rest(p), "sleep": lambda p, a: self.rest(p), "wait": lambda p, a: self.rest(p),
            "chest": lambda p, a: self.list_chest(p), "storage": lambda p, a: self.list_chest(p),
            "store": self.store_item, "stash": self.store_item,
            "retrieve": self.retrieve_item, "withdraw": self.retrieve_item,
            "admin": self.admin_command, "god": self.admin_command,
            "craft": self.craft_item, "make": self.craft_item, "create": self.craft_item,
            "recipes": lambda p, a: self.get_recipes_list(p), "blueprints": lambda p, a: self.get_recipes_list(p), "formulas": lambda p, a: self.get_recipes_list(p),
        }

    # Command Wrappers
    def _cmd_move(self, player_id: str, arg_str: str) -> Tuple:
        # If arg_str is empty, we use the command name (e.g., 'north') as the direction
        # This is handled by process_command injecting it
        direction = arg_str if arg_str else "unknown" 
        return self.move_player(player_id, direction)

    def _cmd_stats(self, player_id: str, arg_str: str) -> Tuple:
        player, location = self._get_player_and_location(player_id)
        return str(player.stats), player, location

    def _cmd_time(self, player_id: str, arg_str: str) -> Tuple:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        return world_time.get_time_string(), player, location

    def _cmd_help(self, player_id: str, arg_str: str) -> Tuple:
        player, location = self._get_player_and_location(player_id)
        commands = self.repo.get_command_help()
        lines = ["Available Commands:"]
        for cmd in commands:
            lines.append(f"- {cmd['command']}: {cmd['description']}")
        return "\n".join(lines), player, location

    def _cmd_scout(self, player_id: str, arg_str: str) -> Tuple:
        res = self.scout_area(player_id)
        msg, p, l = res[:3]
        scouted = res[3] if len(res) > 3 else None
        return msg, p, l, scouted

    def _cmd_consume(self, player_id: str, arg_str: str) -> Tuple:
        # Special logic for drinking from source
        if not arg_str or arg_str == "water":
            msg, p, l = self.drink_from_source(player_id)
            if "no water source" not in msg:
                return msg, p, l
            # If no source, fall through to consuming from inventory if "water" was specified
            if not arg_str: arg_str = "water" 
        
        return self.consume_item(player_id, arg_str)

    def create_new_player(self, name: str) -> Tuple[Player, Location]:
        # Check if player already exists
        existing_player = self.repo.get_player_by_name(name)
        if existing_player:
            raise ValueError(f"Player name '{name}' is already taken.")

        start_id = "loc_0_0_0"
        start_location = self.repo.get_location(start_id)
        if not start_location:
            print("GENERATING NEW CHUNK AROUND 0,0")
            generated_locations = self.world_gen.generate_chunk(start_x=-2, start_y=-2, size=5)
            # Load static areas and override generated ones
            static_locations = self.static_area_loader.load_static_areas()
            static_coords = {(loc.coordinates.x, loc.coordinates.y, loc.coordinates.z): loc for loc in static_locations if loc.coordinates}
            
            print(f"Generated {len(generated_locations)} locations.")
            for loc in generated_locations:
                coords = (loc.coordinates.x, loc.coordinates.y, loc.coordinates.z)
                if coords in static_coords:
                    # Replace with static location data
                    static_loc = static_coords[coords]
                    loc.name = static_loc.name
                    loc.description = static_loc.description
                    loc.interactables = static_loc.interactables
                    # Note: We keep the exits that might have been generated or we let them be overridden if needed?
                    # The chunk generator will still link neighbors.
                self.repo.create_location(loc)
            start_location = self.repo.get_location(start_id)
            if not start_location:
                # Fallback just in case, find it in the generated list
                start_location = next((l for l in generated_locations if l.id == start_id), None)
            print("FINISHED GENERATING NEW CHUNK")

        if start_location:
            self._ensure_neighbors(start_location)
            
        player = Player(name=name, current_location_id=start_id)
        saved_player = self.repo.save_player(player)
        return saved_player, start_location

    def login_player(self, name: str) -> Tuple[Player, Location]:
        player = self.repo.get_player_by_name(name)
        if not player:
            raise ValueError(f"Player '{name}' not found.")
        
        location = self.repo.get_location(player.current_location_id)
        if not location:
            location = self.world_gen.generate_limbo()
            
        return player, location

    def _get_player_and_location(self, player_id: str) -> Tuple[Player, Location]:
        player = self.repo.get_player(player_id)
        if not player:
            raise ValueError("Player not found")
        current_location = self.repo.get_location(player.current_location_id)
        if not current_location:
            current_location = self.world_gen.generate_limbo()
        return player, current_location

    def _advance_time_and_events(self, world_time, player: Player, time_cost: int) -> str:
        msg_add = ""
        if time_cost > 0:
            old_hour = world_time.hour
            world_time.advance(time_cost)
            self.repo.save_world_time(world_time)
            new_hour = world_time.hour
            
            # More robust transition check: check if we crossed 6:00 or 20:00
            # Normalize hours to 24 scale for easier comparison
            def crossed(h_start, h_end, target):
                # Simple case: target is between start and end (inclusive of end)
                if h_start < target <= h_end: return True
                # Wrap-around case: e.g. from 23 to 2
                if h_start > h_end:
                    if h_start < target or target <= h_end: return True
                return False

            # We use a simpler logic for now: if total_ticks // 60 changed and hits/passes the threshold
            ticks_start = world_time.total_ticks - time_cost
            ticks_end = world_time.total_ticks
            
            def check_transition(threshold_hour):
                # Total minutes at which the threshold occurs on day N
                # This is tricky because of multiple days.
                # Easier: check if (ticks // 60) % 24 passed the threshold.
                for t in range(ticks_start + 1, ticks_end + 1):
                    if (t % 1440) == (threshold_hour * 60):
                        return True
                return False

            if check_transition(settings.HOUR_NIGHT):
                msg_add += "\nNight has fallen."
            elif check_transition(settings.HOUR_DAWN):
                msg_add += "\nDawn breaks."

            msg_add += self._apply_survival_mechanics(time_cost, player)
            self.repo.save_player(player)
        return msg_add

    def look(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        base_desc = location.description
        if world_time and world_time.is_night():
            base_desc = f"[NIGHT] {base_desc} (It is dark)"
        
        # Darkness check override
        if location.is_dark:
            has_light = any(getattr(item, "is_light_source", False) for item in player.inventory)
            if not has_light:
                return "It is pitch black. You cannot see anything without a light source.", player, location

        if location.items:
            item_names = [i.name for i in location.items]
            base_desc += f"\nYou see items: {', '.join(item_names)}"
            
        if location.enemies:
            enemy_names = [f"{e.name} (HP:{e.hp})" for e in location.enemies]
            base_desc += f"\nEnemies here: {', '.join(enemy_names)}"
        
        # Special Goblin Encounter at 4,4,0
        if location.coordinates and location.coordinates.x == 4 and location.coordinates.y == 4 and location.coordinates.z == 0:
            if any(e.name == "Friendly Goblin" and not getattr(e, "is_dead", False) for e in location.enemies):
                base_desc += "\n\n[SPECIAL] A goblin has given you such an... intense 'welcome' that you've discovered new meanings for the word 'flexibility'. He seems to have thoroughly enjoyed your company!"
            
        return base_desc, player, location

    def map_inventory(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not player.inventory:
            return "You are not carrying anything.", player, location
        counts = Counter((i.name, i.item_type) for i in player.inventory)
        items_list = []
        for (name, item_type), count in sorted(counts.items()):
            display = f"- {name} ({item_type})"
            if count > 1: display += f" x{count}"
            items_list.append(display)
        weight_info = f"Weight: {player.current_weight:.1f}/{player.stats.max_weight:.1f}"
        return f"Inventory ({weight_info}):\n" + "\n".join(items_list), player, location

    def move_player(self, player_id: str, direction: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()

        if direction in ["enter", "dive", "down"]: direction = "down"
        elif direction in ["climb", "surface", "up"]: direction = "up"
        if direction not in ["north", "south", "east", "west", "up", "down"]:
            return "Go where?", player, location
            
        if direction == "down":
            bosses = [e for e in location.enemies if getattr(e, "is_boss", False) and not getattr(e, "is_dead", False)]
            if bosses:
                return f"The {bosses[0].name} blocks your path deeper into the dungeon!", player, location

        # Engagement Check: Dungeon enemies and provoked enemies block movement
        alive_enemies = [e for e in location.enemies if not getattr(e, "is_dead", False)]
        bypass_msg = ""
        if alive_enemies:
            is_dungeon = location.id.startswith("dng_")
            is_provoked = any(e.hp < e.max_hp for e in alive_enemies)
            
            if is_dungeon or is_provoked:
                # Engagement Block (Either Dungeon depth or player initiated combat)
                enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_MOVE_DUNGEON)
                block_reason = "in a dungeon" if is_dungeon else "engaged in combat"
                msg = f"You are {block_reason}! The {alive_enemies[0].name} blocks your escape!"
                if enemy_log:
                    msg += f"\nAs you turn to run, they strike: {enemy_log}"
                
                self.repo.save_player(player)
                if is_dead:
                    return msg, player, self.repo.get_location("loc_0_0_0") or location
                return msg, player, location
            else:
                # Soft Bypass (Wilderness enemies not yet provoked)
                enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_MOVE_WILDERNESS)
                if is_dead:
                    return f"You try to slip past the {alive_enemies[0].name}, but it's fatal! {enemy_log}", player, self.repo.get_location("loc_0_0_0") or location
                if enemy_log:
                    bypass_msg = f"\nAs you slip past, the {alive_enemies[0].name} lunges: {enemy_log}"

        next_location_id = player.move(direction, location.exits)
        if next_location_id:
            # ... (rest of movement logic)
            # Clear dropped items when player successfully leaves the location
            original_item_count = len(location.items)
            location.items = [item for item in location.items if not getattr(item, 'is_dropped', False)]
            if len(location.items) != original_item_count:
                self.repo.create_location(location)

            # Check if entering an ungenerated dungeon floor
            new_loc = self.repo.get_location(next_location_id)
            if not new_loc and next_location_id.startswith("dng_"):
                parts = next_location_id.split("_") # dng_x_y_z_start
                x, y, z = int(parts[1]), int(parts[2]), int(parts[3])
                
                # Generate floor
                dungeon_locations = self.dungeon_gen.generate_floor(x, y, z)
                for loc in dungeon_locations:
                    self.repo.create_location(loc)
                    
                new_loc = self.repo.get_location(next_location_id)

            player.current_location_id = next_location_id
            self.repo.save_player(player)
            
            # Trap logic
            trap_msg = ""
            if new_loc and new_loc.trap_damage > 0:
                damage = new_loc.trap_damage
                player.take_damage(damage)
                trap_msg = f"\n[TRAP] You triggered a trap and took {damage} damage!"
                if not player.is_alive():
                    trap_msg += "\nThe trap was fatal..."
                    player.heal()
                    player.current_location_id = "loc_0_0_0"
                    self.repo.save_player(player)
                    new_loc = self.repo.get_location("loc_0_0_0")
                else:
                    self.repo.save_player(player)

            time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_MOVE)
            
            if new_loc:
                self._ensure_neighbors(new_loc)
                return f"{bypass_msg}You travel {direction}...{trap_msg}{time_msg}", player, new_loc
            return f"{bypass_msg}You travel {direction}...{trap_msg}{time_msg}", player, location
        return "You can't go that way.", player, location

    def _parse_item_arg(self, arg_str: str) -> Tuple[str, int]:
        parts = arg_str.strip().split()
        if not parts:
            return "", 1
        if parts[-1].isdigit():
            return " ".join(parts[:-1]), int(parts[-1])
        return arg_str, 1

    def take_item(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        item_name, quantity = self._parse_item_arg(arg_str)
        if not item_name: return "Take what?", player, location
        
        taken_count = 0
        taken_names = []
        for _ in range(quantity):
            found_item = location.remove_item(item_name)
            if not found_item:
                break
            
            if player.current_weight + found_item.weight > player.stats.max_weight:
                location.add_item(found_item) # put it back
                msg = f"Inventory full! ({player.current_weight:.1f}/{player.stats.max_weight:.1f})."
                if taken_count > 0:
                    msg = f"You grabbed {taken_count}x {taken_names[-1]} before getting too heavy. {msg}"
                return msg, player, location
                
            # Reset is_dropped if it was a player-dropped item
            found_item.is_dropped = False
            player.add_item(found_item)
            taken_count += 1
            taken_names.append(found_item.name)

        if taken_count == 0:
            return "You don't see that here.", player, location

        time_cost = 1
        name_display = taken_names[0]
        base_msg = f"You picked up {taken_count}x {name_display}."
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        if is_dead:
            return base_msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg + time_msg, player, location

    def drop_item(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        item_name, quantity = self._parse_item_arg(arg_str)
        if not item_name: return "Drop what?", player, location
        
        dropped_count = 0
        dropped_names = []
        for _ in range(quantity):
            found_item = player.remove_item(item_name)
            if not found_item:
                break
            found_item.is_dropped = True
            location.add_item(found_item)
            dropped_count += 1
            dropped_names.append(found_item.name)

        if dropped_count == 0:
            return "You don't have that.", player, location

        time_cost = 1
        name_display = dropped_names[0]
        base_msg = f"You dropped {dropped_count}x {name_display}."
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        base_msg += enemy_log

        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        if is_dead:
            return base_msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg + time_msg, player, location

    def equip_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        if not item_name:
            return "Equip what?", player, location
            
        found_item = next((i for i in player.inventory if i.name.lower() == item_name.lower()), None)
        if not found_item:
            return f"You don't have a '{item_name}' in your inventory.", player, location
            
        base_msg = player.equip(found_item)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        if is_dead:
            return base_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg, player, location

    def unequip_item(self, player_id: str, slot: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        if not slot:
            return "Unequip from what slot?", player, location
            
        base_msg = player.unequip(slot)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        if is_dead:
            return base_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg, player, location

    def _process_enemy_turns(self, player: Player, location: Location, excluded_enemy_id: str = None, chance: float = 1.0) -> Tuple[str, bool]:
        """
        Allows all enemies in the location (except excluded_enemy_id) to attack the player.
        Returns a tuple: (combat_log_string, is_player_dead_boolean)
        """
        if not getattr(location, 'enemies', None):
            return "", False
            
        combat_log = ""
        armor = player.equipment.get("armor")
        mitigation = 0
        if armor and "defense" in armor.stat_bonuses:
            mitigation = armor.stat_bonuses["defense"]
 
        is_dead = False
        for enemy in location.enemies:
            if enemy.id == excluded_enemy_id or enemy.is_dead:
                continue
                
            # Random chance for the enemy to actually take an action
            if random.random() > chance:
                continue
 
            enemy_dmg = max(1, enemy.attack)
            final_dmg = max(1, enemy_dmg - mitigation)
            player.take_damage(final_dmg)
            
            combat_log += f"\n{enemy.name} attacks you for {final_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"
            
            if not player.is_alive():
                combat_log += "\nYou have been defeated...\nYou wake up back at the start, feeling woozy."
                player.heal()
                player.current_location_id = "loc_0_0_0"
                is_dead = True
                break
                
        return combat_log, is_dead

    def attack_enemy(self, player_id: str, target_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        if not target_name: return "Attack what?", player, location
        
        enemy = location.get_enemy(target_name)
        if not enemy: return f"You don't see '{target_name}' here.", player, location

        # Calculate player damage
        total_strength = player.stats.strength
        weapon = player.equipment.get("weapon")
        if weapon and "strength" in weapon.stat_bonuses:
            total_strength += weapon.stat_bonuses["strength"]
            
        damage = max(1, (total_strength // 2))
        actual_dmg = enemy.take_damage(damage)
        combat_log = f"You hit {enemy.name} for {actual_dmg} damage. (Enemy HP: {enemy.hp}/{enemy.max_hp})"
        
        if enemy.is_dead:
            combat_log += f"\n{enemy.name} collapses and dies!"
            location.remove_enemy(enemy.id)
            player.gain_xp(enemy.xp_reward)
            combat_log += f"\nYou gain {enemy.xp_reward} XP."
            
            # Chance to drop worn equipment (10%)
            import random
            if random.random() < 0.10:
                from app.core.domain.item import Item, ItemType
                import uuid
                equipment_pool = [
                    {"name": "Rusty Sword", "type": ItemType.WEAPON, "desc": "An old sword, heavily rusted.", "weight": 3.0, "slot": "weapon", "stats": {"strength": 1}, "durability": 5, "max_durability": 100},
                    {"name": "Torn Tunic", "type": ItemType.ARMOR, "desc": "A moth-eaten cloth tunic.", "weight": 1.0, "slot": "armor", "stats": {"defense": 1}, "durability": 10, "max_durability": 100}
                ]
                choice = random.choice(equipment_pool)
                item = Item(
                    id=str(uuid.uuid4()),
                    name=choice["name"],
                    description=choice["desc"],
                    item_type=choice["type"],
                    value=5,
                    weight=choice["weight"],
                    equip_slot=choice["slot"],
                    stat_bonuses=choice["stats"],
                    durability=choice["durability"],
                    max_durability=choice["max_durability"]
                )
                location.items.append(item)
                combat_log += f"\n{enemy.name} dropped a {item.name}!"
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_ATTACK)
            return combat_log + time_msg, player, location
            
        # Enemy retaliates (the one being attacked)
        enemy_dmg = max(1, enemy.attack)
        armor = player.equipment.get("armor")
        mitigation = 0
        if armor and "defense" in armor.stat_bonuses:
            mitigation = armor.stat_bonuses["defense"]
            
        final_dmg = max(1, enemy_dmg - mitigation)
        player.take_damage(final_dmg)
        combat_log += f"\n{enemy.name} retaliates for {final_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"
        
        # Other enemies attack
        other_combat_log, _ = self._process_enemy_turns(player, location, excluded_enemy_id=enemy.id)
        combat_log += other_combat_log
        
        if not player.is_alive():
            combat_log += "\nYou have been defeated...\nYou wake up back at the start, feeling woozy."
            player.heal()
            player.current_location_id = "loc_0_0_0"
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_ATTACK)
            return combat_log + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        
        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_ATTACK)
        return combat_log + time_msg, player, location

    def scout_area(self, player_id: str) -> Tuple[str, Player, Location, list]:
        player, location = self._get_player_and_location(player_id)
        if not location.coordinates:
            return "You cannot orient yourself here.", player, location, []
            
        x, y, z = location.coordinates.x, location.coordinates.y, location.coordinates.z
        radius = settings.SCOUT_RADIUS
        nearby = self.repo.get_locations_in_radius(x, y, z, radius)
        
        if not nearby:
            return "You scout the area but see nothing of interest.", player, location, []
            
        scouted_data = []
        found_landmarks = []
        for loc in nearby:
            nx, ny = loc.coordinates.x, loc.coordinates.y
            dx = nx - x
            dy = ny - y
            
            # Distance
            dist = max(abs(dx), abs(dy))
            
            report_name = loc.name
            
            # Detect vertical connections
            if z == 0 and "down" in loc.exits:
                report_name = "Cave Entrance"
            elif z < 0 and "up" in loc.exits:
                report_name = "Surface Exit"
            # Filter generic names if no special exits
            import re
            generic_biomes = ["Forest", "Desert", "Wilderness", "Deep Cavern", "Mountain", "Plains", "Forest Area", "Desert Area"]
            is_generic_biome = any(loc.name.startswith(b) for b in generic_biomes)
            if is_generic_biome and re.search(r"\s-?\d+,-?\d+$", loc.name):
                continue

            # Skip reporting the exact same location unless it's a special POI or exit
            if dist == 0 and report_name == loc.name:
                continue
                
            # Simple cardinal logic
            dir_str = ""
            if dy > 0: dir_str += "North"
            elif dy < 0: dir_str += "South"
            
            if dx > 0: dir_str += "East" if not dir_str else "-East"
            elif dx < 0: dir_str += "West" if not dir_str else "-West"
            
            dir_text = f"{dist} chunks {dir_str}" if dist > 0 else "Here"
            found_landmarks.append(f"- {report_name} ({dir_text})")
            scouted_data.append({
                "name": report_name,
                "distance": dist,
                "direction": dir_str if dist > 0 else "Here"
            })
            
        if not found_landmarks:
            return "You scout the area but only see endless wilderness.", player, location, []
            
        msg = "You look around and spot notable landmarks:\n" + "\n".join(found_landmarks)
        
        # Scouting takes 2 ticks
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 2)
        return msg + time_msg, player, location, scouted_data

    def get_time_status(self) -> str:
        world_time = self.repo.get_world_time()
        return f"It is {world_time.get_time_string()}."

    def create_camp(self, player_id: str, camp_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not camp_name:
            return "You must provide a name for your camp.", player, location
            
        msg = player.add_waypoint(camp_name, location.id)
        self.repo.save_player(player)
        return msg, player, location

    def fast_travel(self, player_id: str, waypoint_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not waypoint_name:
            return "Travel where?", player, location
            
        target_id = player.waypoints.get(waypoint_name)
        if not target_id:
            return f"You don't know the way to '{waypoint_name}'.", player, location
            
        if target_id == location.id:
            return "You are already there.", player, location

        target_loc = self.repo.get_location(target_id)
        if not target_loc:
            return "The destination is unreachable.", player, location

        dist = 0
        if location.coordinates and target_loc.coordinates:
            import math
            dx = location.coordinates.x - target_loc.coordinates.x
            dy = location.coordinates.y - target_loc.coordinates.y
            dist = math.ceil(math.sqrt(dx*dx + dy*dy))
        else:
            # If undefined coordinates, assume a baseline distance
            dist = 5
            
        energy_cost = dist * settings.TRAVEL_ENERGY_COST_MULT
        time_cost = dist * settings.TIME_COST_TRAVEL_BASE
        
        if player.stats.hp <= energy_cost:
            return f"You are too exhausted to make the journey to {waypoint_name} (Requires {energy_cost} HP).", player, location
            
        player.take_damage(energy_cost)
        player.current_location_id = target_loc.id
        self.repo.save_player(player)
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        travel_narrative = f"You traveled to {waypoint_name}, covering a great distance. You spent {energy_cost} HP."
            
        return f"{travel_narrative}{time_msg}", player, target_loc

    def list_chest(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here.", player, location
            
        if not location.camp_storage:
            return "The camp chest is empty.", player, location
            
        counts = Counter((i.name, i.item_type) for i in location.camp_storage)
        items_list = []
        for (name, item_type), count in sorted(counts.items()):
            display = f"- {name} ({item_type})"
            if count > 1: display += f" x{count}"
            items_list.append(display)
            
        return "Camp Chest Contents:\n" + "\n".join(items_list), player, location

    def store_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here to store items.", player, location
            
        if not item_name:
            return "Store what?", player, location
            
        found_item = player.remove_item(item_name)
        if found_item:
            location.store_camp_item(found_item)
            
            base_msg = f"You stored {found_item.name} in the camp chest."
            enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
            base_msg += enemy_log
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            
            if is_dead:
                return base_msg, player, self.repo.get_location("loc_0_0_0") or location
            return base_msg, player, location
            
        return f"You don't have '{item_name}'.", player, location

    def retrieve_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here to retrieve items from.", player, location
            
        if not item_name:
            return "Retrieve what?", player, location
            
        found_item = location.retrieve_camp_item(item_name)
        if found_item:
            if player.current_weight + found_item.weight > player.stats.max_weight:
                location.store_camp_item(found_item) # put it back
                return f"You cannot carry {found_item.name}, it is too heavy.", player, location
                
            player.add_item(found_item)
            
            base_msg = f"You retrieved {found_item.name} from the camp chest."
            enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
            base_msg += enemy_log
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            
            if is_dead:
                return base_msg, player, self.repo.get_location("loc_0_0_0") or location
            return base_msg, player, location
            
        return f"There is no '{item_name}' in the camp chest.", player, location

    def process_command(self, player_id: str, command_text: str) -> Tuple:
        raw_args = command_text.split()
        if not raw_args:
            player, location = self._get_player_and_location(player_id)
            return "Please enter a command.", player, location
        
        action = raw_args[0].lower()
        arg_str = " ".join(raw_args[1:])
        
        handler = self.registry.get(action)
        if not handler:
            player, location = self._get_player_and_location(player_id)
            return f"Unknown command: '{action}'. Type 'help' for a list of commands.", player, location

        # Special case for movement shortcuts where direction IS the command
        if action in ["north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d"] and not arg_str:
            arg_str = action

        res = handler(player_id, arg_str)
        
        # Unpack results to apply post-processing
        msg, p, l = res[:3]
        scouted = res[3] if len(res) > 3 else None
        
        final_msg, final_p, final_l = self._post_process_special_encounters(msg, p, l)
        
        if scouted is not None:
            return final_msg, final_p, final_l, scouted
        return final_msg, final_p, final_l

    def _post_process_special_encounters(self, message: str, player: Player, location: Location) -> Tuple[str, Player, Location]:
        # Special Goblin Encounter at 4,4,0
        if location.coordinates and location.coordinates.x == 4 and location.coordinates.y == 4 and location.coordinates.z == 0:
            if any(e.name == "Friendly Goblin" and not getattr(e, "is_dead", False) for e in location.enemies):
                special_msg = "\n\n[SPECIAL] A goblin has given you such an... intense 'welcome' that you've discovered new meanings for the word 'flexibility'. He seems to have thoroughly enjoyed your company!"
                if special_msg not in message:
                    message += special_msg
        return message, player, location

    def _apply_survival_mechanics(self, time_passed: int, player: Player) -> str:
        if not hasattr(player, "stats"):
            return ""
            
        s = self.game_settings.get("survival", {})
        msg = ""
        hunger_loss = max(0, time_passed // s.get("hunger_drain_rate", settings.HUNGER_DRAIN_INTERVAL))
        thirst_loss = max(0, time_passed // s.get("thirst_drain_rate", settings.THIRST_DRAIN_INTERVAL))
        
        if hunger_loss > 0:
            player.stats.hunger = max(0, player.stats.hunger - hunger_loss)
        if thirst_loss > 0:
            player.stats.thirst = max(0, player.stats.thirst - thirst_loss)
            
        is_starving = player.stats.hunger == 0
        is_dehydrated = player.stats.thirst == 0
        
        damage = 0
        if is_starving:
            damage += max(1, time_passed // s.get("starvation_damage_rate", settings.STARVATION_DAMAGE_INTERVAL))
            msg += "\nYou are starving! You lose HP."
        if is_dehydrated:
            damage += max(1, time_passed // s.get("dehydration_damage_rate", settings.DEHYDRATION_DAMAGE_INTERVAL))
            msg += "\nYou are dehydrated! You lose HP."
            
        if damage > 0:
            player.take_damage(damage)
        elif player.stats.hp < player.stats.max_hp:
            heal_interval = s.get("passive_heal_rate", settings.NATURAL_HEAL_INTERVAL)
            threshold = s.get("passive_heal_threshold_mins", 10)
            if time_passed >= threshold:
                heal_amount = time_passed // heal_interval
                player.stats.hp = min(player.stats.max_hp, player.stats.hp + heal_amount)
            
        return msg

    def consume_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not item_name: return "Consume what?", player, location
        
        found_item = player.remove_item(item_name)
        if not found_item:
            return f"You don't have '{item_name}'.", player, location
            
        item_type_str = str(found_item.item_type).lower()
        if not item_type_str.endswith("consumable"):
            player.add_item(found_item) # Put it back
            return f"{found_item.name} is not consumable.", player, location
            
        # Apply effects
        msg = f"You consumed {found_item.name}."
        
        if found_item.restore_hp != 0 or found_item.restore_hp_pct != 0:
            pct_restore = int(player.stats.max_hp * found_item.restore_hp_pct)
            total_hp_restore = found_item.restore_hp + pct_restore
            player.stats.hp = min(player.stats.max_hp, max(0, player.stats.hp + total_hp_restore))
            action_word = "Restored" if total_hp_restore > 0 else "Lost"
            msg += f" {action_word} {abs(total_hp_restore)} HP."
            
        if found_item.restore_mp != 0 or found_item.restore_mp_pct != 0:
            pct_restore = int(player.stats.max_mp * found_item.restore_mp_pct)
            total_mp_restore = found_item.restore_mp + pct_restore
            player.stats.mp = min(player.stats.max_mp, max(0, player.stats.mp + total_mp_restore))
            action_word = "Restored" if total_mp_restore > 0 else "Lost"
            msg += f" {action_word} {abs(total_mp_restore)} MP."
        if found_item.restore_hunger != 0:
            player.stats.hunger = min(100, max(0, player.stats.hunger + found_item.restore_hunger))
            action_word = "Restored" if found_item.restore_hunger > 0 else "Lost"
            msg += f" {action_word} {abs(found_item.restore_hunger)} Hunger."
        if found_item.restore_thirst != 0:
            player.stats.thirst = min(100, max(0, player.stats.thirst + found_item.restore_thirst))
            action_word = "Restored" if found_item.restore_thirst > 0 else "Lost"
            msg += f" {action_word} {abs(found_item.restore_thirst)} Thirst."
            
        # Process arbitrary effects if any
        for effect in found_item.effects:
            if effect.get("type") == "heal":
                amount = effect.get("amount", 0)
                player.stats.hp = min(player.stats.max_hp, player.stats.hp + amount)
                msg += f" Restored {amount} HP."
                
        self.repo.save_player(player)
        
        # Recycling logic: if Water Flask was consumed, give back Empty Flask
        if found_item.name.lower() == "water flask":
            from app.core.domain.item import Item, ItemType
            import uuid
            empty_flask = Item(
                id=str(uuid.uuid4()),
                name="Empty Flask",
                description="An empty glass vessel, useful for holding liquids.",
                item_type=ItemType.OTHER,
                value=1,
                weight=0.5
            )
            player.add_item(empty_flask)
            self.repo.save_player(player)
            msg += " You now have an Empty Flask."

        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 1)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        msg += enemy_log
        
        if is_dead:
            return msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return msg + time_msg, player, location

    def fill_flask(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        # Check for water source
        has_water = any(inter.startswith("water_source:") for inter in location.interactables)
        if not has_water:
            return "There is no water source here to fill anything.", player, location
            
        # Find empty flask - allow both names
        valid_flask_names = ["empty flask", "water flask (empty)"]
        empty_flask = next((i for i in player.inventory if i.name.lower() in valid_flask_names), None)
        
        if not empty_flask:
            return "You don't have an Empty Flask to fill.", player, location
            
        # Replace Empty Flask with Water Flask
        player.remove_item(empty_flask.name)
        
        from app.core.domain.item import Item, ItemType
        import uuid
        water_flask = Item(
            id=str(uuid.uuid4()),
            name="Water Flask",
            description="A flask filled with fresh water.",
            item_type=ItemType.CONSUMABLE,
            restore_thirst=40,
            value=2,
            weight=1.0
        )
        player.add_item(water_flask)
        
        msg = f"You fill the {empty_flask.name} with water."
        self.repo.save_player(player)
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 2)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        msg += enemy_log
        
        if is_dead:
            return msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return msg + time_msg, player, location

    def drink_from_source(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        # Check for water source
        has_water = any(inter.startswith("water_source:") for inter in location.interactables)
        if not has_water:
            return "There is no water source here to drink from.", player, location
            
        if player.stats.thirst >= 100:
            return "You are not thirsty.", player, location

        restore_amount = 30
        player.stats.thirst = min(100, player.stats.thirst + restore_amount)
        
        msg = "You cup your hands and drink the cool, refreshing water."
        self.repo.save_player(player)
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 1)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        msg += enemy_log
        
        if is_dead:
            return msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return msg + time_msg, player, location

    def _ensure_neighbors(self, location: Location):
        if not location.coordinates: return
        x, y, z = location.coordinates.x, location.coordinates.y, location.coordinates.z
        deltas = {
            "north": (0, 1, 0), "south": (0, -1, 0),
            "east": (1, 0, 0), "west": (-1, 0, 0),
        }
        for direction, (dx, dy, dz) in deltas.items():
            nx, ny, nz = x + dx, y + dy, z + dz
            if direction in location.exits: continue
            neighbor = self.repo.get_location_by_coordinates(nx, ny, nz)
            if not neighbor:
                neighbor = self.world_gen.generate_single_location(nx, ny, nz)
                self.repo.create_location(neighbor)
            self._link_locations(location, neighbor, direction)

    def _link_locations(self, loc_a: Location, loc_b: Location, dir_a_to_b: str):
        opposites = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
        dir_b_to_a = opposites.get(dir_a_to_b)
        loc_a.exits[dir_a_to_b] = loc_b.id
        loc_b.exits[dir_b_to_a] = loc_a.id
        self.repo.create_location(loc_a)
        self.repo.create_location(loc_b)

    def fill_vessel(self, player_id: str, item_name: str = None) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        # Check for water_source in interactables
        if "water_source" not in location.interactables:
             return "There is no water source here.", player, location
             
        found_flask = None
        if item_name:
            found_flask = player.remove_item(item_name)
            if not found_flask:
                return f"You don't have '{item_name}'.", player, location
        else:
            # Fallback to first empty flask if no name provided
            for item in player.inventory:
                if "Empty" in item.name and "Flask" in item.name:
                    found_flask = player.remove_item(item.name)
                    break
        
        if not found_flask:
            return "You don't have an empty flask to fill.", player, location
            
        if "Empty" not in found_flask.name or "Flask" not in found_flask.name:
            player.add_item(found_flask) # Put it back
            return f"You can't fill {found_flask.name}.", player, location

        # Transform it
        from app.core.domain.item import ItemType
        found_flask.name = "Water Flask (Full)"
        found_flask.description = "A flask filled with fresh water."
        found_flask.item_type = ItemType.CONSUMABLE
        found_flask.restore_thirst = 30
        found_flask.restore_hunger = 0
        found_flask.restore_hp = 0
        
        player.add_item(found_flask) # Put back the transformed item
        self.repo.save_player(player)
        return f"You filled the {found_flask.name} from the {location.name}.", player, location

    def get_command_help(self) -> list:
        return self.repo.get_command_help()

    def rest(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        r_conf = self.game_settings.get("rest", {})
        
        hunger_cost = r_conf.get("hunger_cost", 15)
        thirst_cost = r_conf.get("thirst_cost", 15)
        
        if player.stats.hunger < hunger_cost or player.stats.thirst < thirst_cost:
            return "You are too hungry or thirsty to rest effectively.", player, location
            
        if player.stats.hp >= player.stats.max_hp:
            return "You are already fully rested.", player, location

        # Cost
        player.stats.hunger = max(0, player.stats.hunger - hunger_cost)
        player.stats.thirst = max(0, player.stats.thirst - thirst_cost)
        
        if r_conf.get("full_heal", settings.REST_HEAL_FULL):
            player.heal()
            msg = "You take a long rest and wake up feeling completely refreshed. Your HP is fully restored."
        else:
            heal_amt = r_conf.get("heal_amount", settings.REST_BASE_HEAL)
            player.stats.hp = min(player.stats.max_hp, player.stats.hp + heal_amt)
            msg = f"You take a rest. You've recovered {heal_amt} HP, but you're now hungrier and thirstier."
        
        duration = r_conf.get("duration_mins", settings.REST_DURATION_MINS)
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, duration)
        
        self.repo.save_player(player)
        return msg + time_msg, player, location

    def admin_command(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        parts = arg_str.split() # Keep case for the key maybe? or lower? Let's keep it exact for the key.
        
        # System Key check
        SYSTEM_KEY = self.game_settings.get("admin", {}).get("system_key", "ME_ROOT_2026")
        if not parts or parts[0].upper() != SYSTEM_KEY:
            return "Unauthorized access to system override. Protocol terminated.", player, location
            
        if len(parts) < 2:
            return f"Admin authenticated. Subcommands: heal, god, tp [x] [y], give [item]", player, location
            
        sub = parts[1].lower()
        if sub == "heal":
            player.heal()
            player.stats.hunger = 100
            player.stats.thirst = 100
            msg = "[ADMIN] Vitality restored to 100%."
        elif sub == "god":
            player.stats.max_hp = 9999
            player.stats.hp = 9999
            player.stats.strength = 100
            msg = "[ADMIN] God Mode engaged."
        elif sub == "teleport" or sub == "tp":
            if len(parts) >= 4:
                try:
                    tx, ty = int(parts[2]), int(parts[3])
                    target_id = f"loc_{tx}_{ty}_0"
                    target_loc = self.repo.get_location(target_id)
                    if not target_loc:
                        target_loc = self.world_gen.generate_single_location(tx, ty, 0)
                        self.repo.create_location(target_loc)
                    player.current_location_id = target_loc.id
                    location = target_loc
                    msg = f"[ADMIN] Teleported to {tx}, {ty}."
                except:
                    msg = "[ADMIN] Invalid coordinates."
            else:
                msg = "[ADMIN] Usage: admin [key] tp [x] [y]"
        elif sub == "give":
            if len(parts) >= 3:
                item_name = " ".join(parts[2:])
                from app.core.domain.item import Item
                import uuid
                
                template = self.repo.get_item_by_name(item_name)
                if template:
                    item = Item(**template.model_dump())
                    item.id = str(uuid.uuid4())
                    player.add_item(item)
                    msg = f"[ADMIN] Item '{item.name}' granted."
                else:
                    msg = f"[ADMIN] Item '{item_name}' not found in registry."
            else:
                msg = "[ADMIN] Usage: admin [key] give [item_name]"
        else:
            msg = f"[ADMIN] Unknown subcommand: {sub}"
            
        self.repo.save_player(player)
        return msg, player, location

    def get_recipes_list(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        recipes = self.repo.get_recipes()
        if not recipes:
            return "No recipes discovered yet.", player, location
            
        lines = ["Available Recipes:"]
        for r in recipes:
            ing_list = ", ".join([f"{name} x{qty}" for name, qty in r.ingredients.items()])
            lines.append(f"- {r.name}: {ing_list}")
            
        return "\n".join(lines), player, location

    def craft_item(self, player_id: str, recipe_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not recipe_name:
            return "Craft what? Use 'recipes' to see available options.", player, location
            
        recipes = self.repo.get_recipes()
        recipe = next((r for r in recipes if r.name.lower() == recipe_name.lower()), None)
        
        if not recipe:
            return f"Recipe for '{recipe_name}' not found.", player, location
            
        # Check ingredients
        from collections import Counter
        inv_counts = Counter(item.name for item in player.inventory)
        
        missing = []
        for ing_name, qty in recipe.ingredients.items():
            if inv_counts[ing_name] < qty:
                missing.append(f"{ing_name} (need {qty - inv_counts[ing_name]} more)")
                
        if missing:
            return f"Missing ingredients: {', '.join(missing)}", player, location
            
        # All good, consume ingredients
        for ing_name, qty in recipe.ingredients.items():
            count = 0
            new_inv = []
            for item in player.inventory:
                if item.name == ing_name and count < qty:
                    count += 1
                    continue
                new_inv.append(item)
            player.inventory = new_inv
            
        # Create result
        import uuid
        from app.core.domain.item import Item
        
        result_template = recipe.result_template
        new_items = []
        for _ in range(recipe.result_qty):
            new_item = Item(**result_template.model_dump())
            new_item.id = str(uuid.uuid4()) # New unique ID
            player.add_item(new_item)
            new_items.append(new_item.name)
            
        msg = f"Successfully crafted {recipe.result_qty}x {recipe.name}!"
        
        # Advance time
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_CRAFT) # 10 mins to craft
        
        self.repo.save_player(player)
        return msg + time_msg, player, location
