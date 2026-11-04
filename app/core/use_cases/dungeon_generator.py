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
        Generates a procedurally generated dungeon floor using a random walk algorithm.
        Creates 8 to 15 rooms that are connected, forming closed walls at the edges.
        """
        locations = []
        is_hardcore = random.random() < 0.5
        dungeon_type = "Hardcore Instanced" if is_hardcore else "Farmable Ruins"
        base_id = f"dng_{root_x}_{root_y}_{z}"
        
        num_rooms = random.randint(8, 15)
        grid = {} # Map (x, y) -> Location
        
        # Room definitions
        start_coords = (root_x, root_y)
        
        # Create start room
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
            
        grid[start_coords] = start_loc
        locations.append(start_loc)
        
        # Generate layout via random walk
        curr_x, curr_y = root_x, root_y
        directions = [(0, 1, 'north', 'south'), (0, -1, 'south', 'north'), (1, 0, 'east', 'west'), (-1, 0, 'west', 'east')]
        
        for i in range(1, num_rooms):
            dx, dy, dir_to, dir_from = random.choice(directions)
            
            # Simple walk but try to find an empty spot
            attempts = 0
            while (curr_x + dx, curr_y + dy) in grid and attempts < 4:
                dx, dy, dir_to, dir_from = random.choice(directions)
                attempts += 1
                
            # If still stuck, find any existing room with free space around it
            if (curr_x + dx, curr_y + dy) in grid:
                for (cx, cy) in list(grid.keys()):
                    found_free = False
                    for (ndx, ndy, ndir_to, ndir_from) in directions:
                        if (cx + ndx, cy + ndy) not in grid:
                            curr_x, curr_y = cx, cy
                            dx, dy, dir_to, dir_from = ndx, ndy, ndir_to, ndir_from
                            found_free = True
                            break
                    if found_free: break
                            
            curr_x += dx
            curr_y += dy
            
            # Decide room type (last room is boss)
            is_boss = (i == num_rooms - 1)
            is_loot = not is_boss and random.random() < 0.3
            
            room_id = f"{base_id}_{abs(curr_x)}_{abs(curr_y)}_{i}"
            if is_boss: room_id = f"{base_id}_boss"
            
            name = "Dark Corridor"
            desc = "A cold, narrow corridor."
            if is_boss:
                name = "Boss Chamber"
                desc = "A massive chamber covered in blood and bones. A terrifying presence watches you."
            elif is_loot:
                name = "Storage Room"
                desc = "An old storage room scattered with debris."
                
            new_room = Location(
                id=room_id,
                name=name,
                description=desc,
                coordinates=Coordinates(x=curr_x, y=curr_y, z=z)
            )
            new_room.is_dark = True
            
            grid[(curr_x, curr_y)] = new_room
            locations.append(new_room)
            
            # Link room with its adjacent neighbors if they exist in the grid
            for (nx, ny, ndir_to, ndir_from) in directions:
                neighbor = grid.get((curr_x + nx, curr_y + ny))
                if neighbor:
                    # Link them
                    new_room.exits[ndir_to] = neighbor.id
                    neighbor.exits[ndir_from] = new_room.id

            # Populate rooms
            if is_boss:
                self._spawn_boss(new_room, z)
                new_room.exits["down"] = f"dng_{root_x}_{root_y}_{z-1}_start"
            elif is_loot:
                if random.random() < 0.2: new_room.trap_damage = random.randint(10, 20)
                self._populate_dungeon_loot(new_room, z, is_hardcore)
            else:
                if random.random() < 0.2:
                    new_room.trap_damage = random.randint(10, 20)
                    new_room.description += " You feel an uneasy draft here."
                self._populate_dungeon_enemies(new_room, z, is_hardcore)
                
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
        prefixes = boss_conf.get("prefixes", ["Ancient"])
        is_desert = loc.coordinates and loc.coordinates.y <= -2
        desert_boss_conf = boss_conf.get("desert_boss")

        boss_skills = []
        if is_desert and desert_boss_conf:
            base_name = desert_boss_conf.get("name", "Black Hound Sphinx")
            name = base_name if depth_mult == 1 else f"{random.choice(prefixes)} {base_name}"
            desc = desert_boss_conf.get("description", "An ancient desert sphinx with the sleek obsidian body of a black hound.")
            hp = desert_boss_conf.get("hp", 90) * depth_mult
            attack = desert_boss_conf.get("attack", 11) * depth_mult
            xp_reward = desert_boss_conf.get("xp_reward", 150) * depth_mult
            boss_skills = [dict(s) for s in desert_boss_conf.get("skills", [])]
        else:
            hp = boss_conf.get("base_hp", 100) * depth_mult
            attack = boss_conf.get("base_attack", 15) * depth_mult
            name = f"{random.choice(prefixes)} Warden"
            desc = "The guardian of this dungeon floor. Defeat it to proceed deeper."
            xp_reward = 100 * depth_mult
            boss_skills = [dict(s) for s in boss_conf.get("skills", [])]
        
        boss = Enemy(
            id=str(uuid.uuid4()),
            name=name,
            description=desc,
            hp=hp,
            max_hp=hp,
            attack=attack,
            xp_reward=xp_reward,
            is_boss=True,
            level=depth_mult * 2,
            skills=boss_skills
        )
        loc.add_enemy(boss)

    def generate_mountain_floor(self, root_x: int, root_y: int, z: int) -> List[Location]:
        """
        Generates an ascending snow mountain dungeon floor (z > 0).
        z=1: Frostspire Lower Caverns (exits: down to surface loc_{root_x}_{root_y}_0, up to z=2)
        z=2: Frostspire Glacial Chasm (exits: down to z=1, up to summit z=3)
        z=3: Mount Frostspire Frozen Summit (exits: down to z=2, boss: Monstrous Snow Golem)
        """
        locations = []
        base_id = f"mtn_{root_x}_{root_y}_{z}"
        
        if z == 3:
            # Summit of Mount Frostspire (Final Peak & Monstrous Snow Golem Boss)
            summit_loc = Location(
                id=f"{base_id}_summit",
                name="Mount Frostspire Frozen Summit",
                description="You stand atop the open, wind-blasted glacial peak of Mount Frostspire. Endless snowy mountain ranges stretch below. At the center of an icy dais looms the Monstrous Snow Golem, guardian of the frozen summit.",
                coordinates=Coordinates(x=root_x, y=root_y, z=z)
            )
            summit_loc.exits["down"] = f"mtn_{root_x}_{root_y}_2_boss"
            
            boss_conf = self.enemies_config.get("bosses", {}).get("mountain_boss", {})
            golem_boss = Enemy(
                id=str(uuid.uuid4()),
                name=boss_conf.get("name", "Monstrous Snow Golem"),
                description=boss_conf.get("description", "A towering titan carved from glacial permafrost and enchanted mountain ice."),
                hp=boss_conf.get("hp", 120),
                max_hp=boss_conf.get("hp", 120),
                attack=boss_conf.get("attack", 14),
                xp_reward=boss_conf.get("xp_reward", 250),
                is_boss=True,
                level=6,
                skills=[dict(s) for s in boss_conf.get("skills", [])]
            )
            summit_loc.add_enemy(golem_boss)
            locations.append(summit_loc)
            return locations

        # Floors 1 and 2: Ascending cavern complex
        num_rooms = random.randint(6, 9)
        grid = {}
        curr_x, curr_y = root_x, root_y
        directions = [(0, 1, 'north', 'south'), (0, -1, 'south', 'north'), (1, 0, 'east', 'west'), (-1, 0, 'west', 'east')]
        
        start_name = "Frostspire Lower Caverns" if z == 1 else "Frostspire Glacial Chasm"
        start_desc = "Ice crystals cling to the frozen stone walls as the mountain tunnel winds upward." if z == 1 else "Subzero winds whistle through frozen crevasses. The path ascends steeply toward the summit."
        
        start_loc = Location(
            id=f"{base_id}_start",
            name=f"{start_name} (Level {z})",
            description=start_desc,
            coordinates=Coordinates(x=root_x, y=root_y, z=z)
        )
        if z == 1:
            start_loc.exits["down"] = f"loc_{root_x}_{root_y}_0"
        else:
            start_loc.exits["down"] = f"mtn_{root_x}_{root_y}_{z-1}_boss"
            
        grid[(curr_x, curr_y)] = start_loc
        locations.append(start_loc)
        
        for i in range(1, num_rooms):
            dx, dy, dir_to, dir_from = random.choice(directions)
            attempts = 0
            while (curr_x + dx, curr_y + dy) in grid and attempts < 4:
                dx, dy, dir_to, dir_from = random.choice(directions)
                attempts += 1
                
            if (curr_x + dx, curr_y + dy) in grid:
                for (cx, cy) in list(grid.keys()):
                    found_free = False
                    for (ndx, ndy, ndir_to, ndir_from) in directions:
                        if (cx + ndx, cy + ndy) not in grid:
                            curr_x, curr_y = cx, cy
                            dx, dy, dir_to, dir_from = ndx, ndy, ndir_to, ndir_from
                            found_free = True
                            break
                    if found_free: break
                    
            curr_x += dx
            curr_y += dy
            
            is_boss_room = (i == num_rooms - 1)
            room_id = f"{base_id}_boss" if is_boss_room else f"{base_id}_{abs(curr_x)}_{abs(curr_y)}_{i}"
            
            if is_boss_room:
                room_name = "Frostspire Ascent Portal"
                room_desc = f"A vast ice cavern overlooking a sheer precipice. An ancient stairway of solid ice spirals UP toward {'the mountain summit' if z == 2 else 'the higher glacial chasm'}."
            else:
                room_name = random.choice(["Frozen Crevasse", "Glacial Tunnel", "Ice Shelf", "Frostbound Chamber"])
                room_desc = "Glacial frost coats the floor and ceiling. Subzero drafts pierce through the mountain rock."
                
            new_room = Location(
                id=room_id,
                name=room_name,
                description=room_desc,
                coordinates=Coordinates(x=curr_x, y=curr_y, z=z)
            )
            
            grid[(curr_x, curr_y)] = new_room
            locations.append(new_room)
            
            for (nx, ny, ndir_to, ndir_from) in directions:
                neighbor = grid.get((curr_x + nx, curr_y + ny))
                if neighbor:
                    new_room.exits[ndir_to] = neighbor.id
                    neighbor.exits[ndir_from] = new_room.id
                    
            if is_boss_room:
                if z == 1:
                    new_room.exits["up"] = f"mtn_{root_x}_{root_y}_2_start"
                    guardian = Enemy(
                        id=str(uuid.uuid4()),
                        name="Glacial Yeti Alpha",
                        description="A massive, white-furred yeti with deadly icicle-tipped claws guarding the mountain stairs.",
                        hp=65,
                        max_hp=65,
                        attack=12,
                        xp_reward=90,
                        is_boss=True,
                        skills=[{"name": "Frost Roar", "damage": 15, "cooldown": 3, "desc": "unleashes a terrifying frost roar"}]
                    )
                    new_room.add_enemy(guardian)
                elif z == 2:
                    new_room.exits["up"] = f"mtn_{root_x}_{root_y}_3_summit"
                    guardian = Enemy(
                        id=str(uuid.uuid4()),
                        name="Frostfire Wraith",
                        description="An ethereal specter of blazing blue frost hovering over the summit staircase.",
                        hp=85,
                        max_hp=85,
                        attack=13,
                        xp_reward=130,
                        is_boss=True,
                        skills=[{"name": "Spectral Frostwave", "damage": 18, "cooldown": 2, "desc": "casts a piercing wave of spectral cold"}]
                    )
                    new_room.add_enemy(guardian)
            else:
                self._populate_mountain_room(new_room, z)
                
        return locations

    def _populate_mountain_room(self, loc: Location, z: int):
        snow_enemies = self.enemies_config.get("biomes", {}).get("snow", [])
        if snow_enemies and random.random() < 0.70:
            e_data = random.choice(snow_enemies)
            mult = 1.0 + (0.3 * (z - 1))
            enemy = Enemy(
                id=str(uuid.uuid4()),
                name=f"{e_data['name']} (Lvl {z + 1})",
                description="A ferocious creature adapted to the mountain subzero cold.",
                hp=max(15, int(e_data["hp"] * mult)),
                max_hp=max(15, int(e_data["hp"] * mult)),
                attack=max(3, int(e_data["attack"] * mult)),
                xp_reward=int(e_data["xp"] * mult)
            )
            loc.add_enemy(enemy)
        elif random.random() < 0.40:
            self._populate_dungeon_loot(loc, z, is_hardcore=False)
        
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
