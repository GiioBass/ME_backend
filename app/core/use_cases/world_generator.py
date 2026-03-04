from typing import List, Dict
import random
from app.core.domain.location import Location, Coordinates
from app.core.use_cases.blueprint_loader import BlueprintLoader

class WorldGenerator:
    def __init__(self, repo=None, world_config=None, loot_tables=None, enemies_config=None):
        self.blueprint_loader = BlueprintLoader()
        self.repo = repo
        self.world_config = world_config or {}
        self.loot_tables = loot_tables or {}
        self.enemies_config = enemies_config or {}
    def generate_start_location(self) -> Location:
        return Location(
            id="start", 
            name="Crossroads", 
            description="You stand at a dusty crossroads. Paths lead in all directions.",
            coordinates=Coordinates(x=0, y=0, z=0)
        )

    def generate_limbo(self) -> Location:
        return Location(id="limbo", name="Limbo", description="You are floating in nothingness.")

    def generate_single_location(self, x: int, y: int, z: int, biome: str = "forest") -> Location:
        """Generates a single location at specific coordinates."""
        loc_id = f"loc_{x}_{y}_{z}"
        
        if z < 0:
            location = Location(
                id=loc_id,
                name=f"Deep Cavern {x},{y}",
                description="The air is stale and cold here. You are underground.",
                coordinates=Coordinates(x=x, y=y, z=z)
            )
        else:
            # Check for POIs in world_config
            poi = next((p for p in self.world_config.get("pois", []) 
                       if p["coords"]["x"] == x and p["coords"]["y"] == y and p["coords"]["z"] == z), None)
            
            if poi:
                name = poi["name"]
                desc = poi["description"]
                attached_bp = None
            else:
                if random.random() < 0.05:
                    # Spawn a POI instead of Wilderness
                    valid_blueprints = self.blueprint_loader.get_blueprints_for_biome(biome)
                    if valid_blueprints:
                        bp = random.choice(valid_blueprints)
                        name = bp.name
                        desc = bp.description
                        attached_bp = bp
                    else:
                        name = f"{biome.capitalize()} {x},{y}"
                        desc = self._generate_description(biome, x, y)
                        attached_bp = None
                else:
                    name = f"{biome.capitalize()} {x},{y}"
                    desc = self._generate_description(biome, x, y)
                    attached_bp = None
            
            location = Location(
                id=loc_id,
                name=name,
                description=desc,
                coordinates=Coordinates(x=x, y=y, z=z)
            )

            # Chance for Cave Entrance
            cave_conf = self.world_config.get("cave_entrance", {"chance": 0.1, "description_suffix": " You see a dark opening leading down."})
            if z == 0 and random.random() < cave_conf["chance"]:
                location.description += cave_conf["description_suffix"]
                cave_id = f"dng_{x}_{y}_{z-1}_start"
                location.exits["down"] = cave_id

            # Chance for Water Source
            water_conf = self.world_config.get("water_sources", {"chance": 0.15, "types": ["River", "Stream", "Small Lake", "Old Well"]})
            if z == 0 and random.random() < water_conf["chance"]:
                w_type = random.choice(water_conf["types"])
                location.name = f"{w_type} at {x},{y}"
                location.description += f" A refreshing {w_type.lower()} is here."
                location.interactables.append(f"water_source:{w_type}")

            if attached_bp:
                for e in attached_bp.create_enemies(): location.add_enemy(e)
                for i in attached_bp.create_items(): location.add_item(i)
        
        self._populate_items(location, biome)
        
        # Special Enemies from config
        special = next((s for s in self.enemies_config.get("specials", [])
                       if s["trigger_coords"]["x"] == x and s["trigger_coords"]["y"] == y and s["trigger_coords"]["z"] == z), None)
        
        if special:
            from app.core.domain.enemy import Enemy
            import uuid
            e_data = special["enemy"]
            special_enemy = Enemy(
                id=str(uuid.uuid4()),
                name=e_data["name"],
                description=e_data["description"],
                hp=e_data["hp"],
                max_hp=e_data["hp"],
                attack=e_data["attack"],
                xp_reward=e_data["xp_reward"]
            )
            location.add_enemy(special_enemy)
        else:
            self._populate_enemies(location, biome, z)
        return location

    def generate_chunk(self, start_x: int, start_y: int, size: int = 5, biome: str = "forest") -> List[Location]:
        """
        Generates a connected grid of locations (Chunk).
        Returns a list of generated Location objects.
        """
        generated_locations = []
        grid: Dict[str, Location] = {}  # key: "x,y", val: Location

        # 1. Create Nodes
        for x in range(start_x, start_x + size):
            for y in range(start_y, start_y + size):
                location = self.generate_single_location(x, y, 0, biome)
                grid[f"{x},{y}"] = location
                generated_locations.append(location)

        # 2. Link Nodes (Grid connection)
        for x in range(start_x, start_x + size):
            for y in range(start_y, start_y + size):
                current_loc = grid.get(f"{x},{y}")
                if not current_loc: continue

                # North (y+1)
                north = grid.get(f"{x},{y+1}")
                if north:
                    current_loc.exits["north"] = north.id
                    north.exits["south"] = current_loc.id
                
                # East (x+1)
                east = grid.get(f"{x+1},{y}")
                if east:
                    current_loc.exits["east"] = east.id
                    east.exits["west"] = current_loc.id

        return generated_locations

    def _generate_description(self, biome: str, x: int, y: int) -> str:
        variations = self.world_config.get("biome_descriptions", {}).get(biome, 
                     self.world_config.get("biome_descriptions", {}).get("default", ["Unknown surroundings."]))
        return f"You are in a {biome}. {random.choice(variations)}"



    def _populate_items(self, location: Location, biome: str):
        if not self.loot_tables or not self.repo: return
        
        biome_loot = self.loot_tables.get("biomes", {}).get(biome, self.loot_tables.get("biomes", {}).get("default", {}))
        if random.random() > biome_loot.get("item_spawn_chance", 0.3):
            return

        from app.core.domain.item import Item
        import uuid

        # Chance for equipment
        if random.random() < biome_loot.get("equipment_chance", 0.05) and biome_loot.get("equipment_pool"):
            pool = biome_loot["equipment_pool"]
        else:
            pool = biome_loot.get("loot_pool", [])

        if not pool: return

        # Weighted choice
        weights = [i.get("weight", 1) for i in pool]
        choice_data = random.choices(pool, weights=weights, k=1)[0]
        
        # Fetch template from repo
        template = self.repo.get_item_by_name(choice_data["item_id"]) # Expecting item_id in pool to be the name or ID
        # Actually, if we use ID, it's safer. Let's try getting by ID first, then name.
        if not template:
            # Fallback to searching all items or just use a placeholder if not found during gen
            return

        item = Item(**template.model_dump())
        item.id = str(uuid.uuid4())
        location.items.append(item)

    def _populate_enemies(self, location: Location, biome: str, z: int):
        if not self.enemies_config: return
        
        from app.core.domain.enemy import Enemy
        import uuid
        
        # 20% chance of enemy
        is_at_start = location.coordinates and location.coordinates.x == 0 and location.coordinates.y == 0 and location.coordinates.z == 0
        if "Hub" in location.name or "Crossroads" in location.name or is_at_start:
            return

        if random.random() < self.enemies_config.get("spawn_chance", 0.2):
            biome_key = "underground" if z < 0 else biome
            pool = self.enemies_config.get("biomes", {}).get(biome_key, [])
            if not pool: return
            
            choice = random.choice(pool)
            name = choice["name"]
            hp = choice["hp"]
            attack = choice["attack"]
            xp = choice["xp"]
            
            # Apply depth scaling
            if z < 0:
                scale = self.enemies_config.get("depth_scaling", {})
                depth_multiplier = abs(z)
                hp = int(hp * (1 + (depth_multiplier * scale.get("hp_increase", 0.5))))
                attack = int(attack * (1 + (depth_multiplier * scale.get("attack_increase", 0.3))))
                xp = int(xp * (1 + (depth_multiplier * scale.get("xp_increase", 0.5))))
                
                if depth_multiplier > 1 and scale.get("prefixes"):
                    name = f"{random.choice(scale['prefixes'])} {name}"
            
            enemy = Enemy(
                id=str(uuid.uuid4()),
                name=name,
                description=f"A hostile {name}.",
                hp=hp,
                max_hp=hp,
                attack=attack,
                xp_reward=xp
            )
            location.add_enemy(enemy)
