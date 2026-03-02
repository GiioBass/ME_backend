import random
import uuid
from typing import List, Dict, Tuple
from app.core.domain.location import Location, Coordinates
from app.core.domain.enemy import Enemy
from app.core.domain.item import Item, ItemType

class DungeonGenerator:
    def __init__(self, blueprint_loader=None):
        self.blueprint_loader = blueprint_loader
        
    def generate_floor(self, root_x: int, root_y: int, z: int) -> List[Location]:
        """
        Generates a small mapped dungeon floor (e.g., 3x3 or cross shape).
        z should be negative.
        Returns a list of locations created.
        """
        
        locations = []
        is_hardcore = random.random() < 0.5
        dungeon_type = "Hardcore Instanced" if is_hardcore else "Farmable Ruins"
        
        # Grid layout: Let's do a simple cross or fixed shape for now
        # Center (0,0) relative to floor: Start/Up stairs
        # North (0,1): Enemy room
        # East (1,0): Loot room
        # South (0,-1): Trap / Empty
        # North-North (0,2): Boss room / Down stairs
        
        base_id = f"dng_{root_x}_{root_y}_{z}"
        
        # 1. Start Room (Up stairs connecting to Z+1)
        start_loc = Location(
            id=f"{base_id}_start",
            name=f"Dungeon Floor {abs(z)} Entrance",
            description=f"You are in a damp, dark room. The air is thick. ({dungeon_type}).",
            coordinates=Coordinates(x=root_x, y=root_y, z=z)
        )
        if z == -1:
            start_loc.exits["up"] = f"loc_{root_x}_{root_y}_0"
        else:
            start_loc.exits["up"] = f"dng_{root_x}_{root_y}_{z+1}_boss"
            
        locations.append(start_loc)
        
        # 2. Corridor N
        corr_n = Location(
            id=f"{base_id}_n",
            name="Dark Corridor",
            description="A cold, narrow corridor.",
            coordinates=Coordinates(x=root_x, y=root_y+1, z=z)
        )
        self._link(start_loc, corr_n, "north")
        corr_n.is_dark = True
        if random.random() < 0.2: # 20% trap chance
            corr_n.trap_damage = random.randint(10, 20)
            corr_n.description += " You feel an uneasy draft here." # Subtle hint
        self._populate_dungeon_enemies(corr_n, z, is_hardcore)
        locations.append(corr_n)
        
        # 3. Loot Room E
        loot_e = Location(
            id=f"{base_id}_e",
            name="Storage Room",
            description="An old storage room scattered with debris.",
            coordinates=Coordinates(x=root_x+1, y=root_y, z=z)
        )
        self._link(start_loc, loot_e, "east")
        loot_e.is_dark = True
        if random.random() < 0.2: # 20% trap chance
            loot_e.trap_damage = random.randint(10, 20)
        self._populate_dungeon_loot(loot_e, z, is_hardcore)
        locations.append(loot_e)
        
        # 4. Boss Room NN
        boss_nn = Location(
            id=f"{base_id}_boss",
            name="Boss Chamber",
            description="A massive chamber covered in blood and bones. A terrifying presence watches you.",
            coordinates=Coordinates(x=root_x, y=root_y+2, z=z)
        )
        self._link(corr_n, boss_nn, "north")
        boss_nn.is_dark = True
        self._spawn_boss(boss_nn, z)
        
        # Next floor exit
        boss_nn.exits["down"] = f"dng_{root_x}_{root_y}_{z-1}_start"
        locations.append(boss_nn)
        
        return locations
        
    def _link(self, a: Location, b: Location, dir_a_to_b: str):
        opposites = {"north": "south", "south": "north", "east": "west", "west": "east"}
        a.exits[dir_a_to_b] = b.id
        b.exits[opposites[dir_a_to_b]] = a.id

    def _populate_dungeon_enemies(self, loc: Location, z: int, is_hardcore: bool):
        depth_mult = abs(z)
        base_hp = 20 * depth_mult
        base_atk = 5 * depth_mult
        
        if is_hardcore:
            base_hp = int(base_hp * 1.5)
            base_atk = int(base_atk * 1.5)
            
        e1 = Enemy(
            id=str(uuid.uuid4()),
            name=f"Dungeon Crawler (Lvl {depth_mult})",
            description="A vile creature adapted to the dark.",
            hp=base_hp,
            max_hp=base_hp,
            attack=base_atk,
            xp_reward=20 * depth_mult
        )
        loc.add_enemy(e1)

    def _spawn_boss(self, loc: Location, z: int):
        depth_mult = abs(z)
        hp = 100 * depth_mult
        attack = 15 * depth_mult
        prefixes = ["Abyssal", "Tyrant", "Cursed", "Ancient", "Dread"]
        name = f"{random.choice(prefixes)} Warden"
        
        boss = Enemy(
            id=str(uuid.uuid4()),
            name=name,
            description="The guardian of this dungeon floor. Defeat it to proceed deeper.",
            hp=hp,
            max_hp=hp,
            attack=attack,
            xp_reward=100 * depth_mult,
            is_boss=True  # We can add this attribute later, or just treat it by stats
        )
        loc.add_enemy(boss)
        
    def _populate_dungeon_loot(self, loc: Location, z: int, is_hardcore: bool):
        depth_mult = abs(z)
        loot_roll = random.random()
        
        from app.core.domain.item import ItemType
        
        if loot_roll < 0.4:  # 40% chance for some basic loot
            loot_options = [
                {"name": "Wild Apple", "type": ItemType.CONSUMABLE, "desc": "A crunchy wild apple found in a crate.", "restore_hunger": 15, "restore_hp_pct": 0.15, "restore_thirst": 5},
                {"name": "Torch", "type": ItemType.TOOL, "desc": "A wooden torch to illuminate dark places.", "weight": 1.0, "is_light_source": True},
                {"name": "Water Flask (Empty)", "type": ItemType.TOOL, "desc": "An empty glass flask.", "weight": 0.5},
                {"name": "Stick", "type": ItemType.MATERIAL, "desc": "A wooden stick used for fuel."},
            ]
            choice = random.choice(loot_options)
            item = Item(
                id=str(uuid.uuid4()),
                name=choice["name"],
                description=choice["desc"],
                item_type=choice["type"],
                weight=choice.get("weight", 0.1),
                restore_hunger=choice.get("restore_hunger", 0),
                restore_hp_pct=choice.get("restore_hp_pct", 0.0),
                restore_thirst=choice.get("restore_thirst", 0),
                is_light_source=choice.get("is_light_source", False),
                value=5 * depth_mult
            )
            loc.add_item(item)
        elif loot_roll < 0.6:  # 20% chance for equipment or rare items
            if random.random() < 0.7:  # Equipment
                item = Item(
                    id=str(uuid.uuid4()),
                    name=f"Obsidian Blade +{depth_mult}",
                    description="A heavy, sharp dark blade.",
                    item_type=ItemType.WEAPON,
                    equip_slot="weapon",
                    weight=5.0,
                    stat_bonuses={"strength": 5 * depth_mult},
                    value=50 * depth_mult
                )
            else:  # Rare material
                item = Item(
                    id=str(uuid.uuid4()),
                    name="Abyssal Core",
                    description="A glowing dark core. Very valuable.",
                    item_type=ItemType.MATERIAL,
                    value=100 * depth_mult,
                    weight=1.0
                )
            loc.add_item(item)
