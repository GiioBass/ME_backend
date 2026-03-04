import random
import uuid
from typing import List, Dict, Tuple
from app.core.domain.location import Location, Coordinates
from app.core.domain.enemy import Enemy
from app.core.domain.item import Item, ItemType

class DungeonGenerator:
    def __init__(self, repo=None, blueprint_loader=None, loot_tables=None, enemies_config=None):
        self.repo = repo
        self.blueprint_loader = blueprint_loader
        self.loot_tables = loot_tables or {}
        self.enemies_config = enemies_config or {}
        
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
        if not self.enemies_config: return
        
        depth_mult = abs(z)
        conf = self.enemies_config.get("underground", [])
        if not conf:
            # Fallback to biome pool if underground not specifically defined
            conf = self.enemies_config.get("biomes", {}).get("underground", [])
        
        if not conf: return
        
        choice = random.choice(conf)
        base_hp = choice["hp"] * depth_mult
        base_atk = choice["attack"] * depth_mult
        
        if is_hardcore:
            base_hp = int(base_hp * 1.5)
            base_atk = int(base_atk * 1.5)
            
        e1 = Enemy(
            id=str(uuid.uuid4()),
            name=f"{choice['name']} (Lvl {depth_mult})",
            description=f"A vile {choice['name'].lower()} adapted to the dark.",
            hp=base_hp,
            max_hp=base_hp,
            attack=base_atk,
            xp_reward=choice["xp"] * depth_mult
        )
        loc.add_enemy(e1)

    def _spawn_boss(self, loc: Location, z: int):
        if not self.enemies_config: return
        
        boss_conf = self.enemies_config.get("bosses", {})
        depth_mult = abs(z)
        hp = boss_conf.get("base_hp", 100) * depth_mult
        attack = boss_conf.get("base_attack", 15) * depth_mult
        prefixes = boss_conf.get("prefixes", ["Ancient"])
        name = f"{random.choice(prefixes)} Warden"
        
        boss = Enemy(
            id=str(uuid.uuid4()),
            name=name,
            description="The guardian of this dungeon floor. Defeat it to proceed deeper.",
            hp=hp,
            max_hp=hp,
            attack=attack,
            xp_reward=100 * depth_mult,
            is_boss=True
        )
        loc.add_enemy(boss)
        
    def _populate_dungeon_loot(self, loc: Location, z: int, is_hardcore: bool):
        if not self.loot_tables or not self.repo: return
        
        dng_loot = self.loot_tables.get("dungeon", {})
        depth_mult = abs(z)
        loot_roll = random.random()
        
        if loot_roll < dng_loot.get("loot_chance", 0.4):
            pool = dng_loot.get("base_loot", [])
            # Check for rare upgrade
            if random.random() < dng_loot.get("rare_chance", 0.2):
                if random.random() < dng_loot.get("equipment_chance_in_rare", 0.7):
                    # Equipment logic: we'll handle this by choosing from equipment pool if available
                    # For now just use rare_loot
                    pool = dng_loot.get("rare_loot", [])
                else:
                    pool = dng_loot.get("rare_loot", [])

            if not pool: return

            weights = [i.get("weight", 1) for i in pool]
            choice_data = random.choices(pool, weights=weights, k=1)[0]
            
            template = self.repo.get_item_by_name(choice_data["item_id"])
            if not template: return

            item = Item(**template.model_dump())
            item.id = str(uuid.uuid4())
            # Scale value by depth
            item.value = int(item.value * depth_mult)
            loc.add_item(item)
