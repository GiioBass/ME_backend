from typing import List, Dict
import random
from app.core.domain.location import Location, Coordinates
from app.core.use_cases.blueprint_loader import BlueprintLoader

class WorldGenerator:
    def __init__(self):
        self.blueprint_loader = BlueprintLoader()
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
            # For surface (z >= 0)
            # Hardcode some initial POIs near spawn for radar testing
            if x == 2 and y == 2 and z == 0:
                name = "Abandoned Outpost"
                desc = "A ruined stone structure. It looks like it was used for observation long ago."
                attached_bp = None
            elif x == 1 and y == 4 and z == 0:
                name = "Ancient Ruins"
                desc = "Crumbling pillars covered in glowing moss surround a cracked dais."
                attached_bp = None
            elif x == 4 and y == 4 and z == 0:
                name = "Goblin's Clearing"
                desc = "A suspiciously cozy clearing in the forest. Something feels... off."
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
            if z == 0 and random.random() < 0.1:
                location.description += " You see a dark opening leading down."
                cave_id = f"dng_{x}_{y}_{z-1}_start"
                location.exits["down"] = cave_id

            # Chance for Water Source
            if z == 0 and random.random() < 0.15:
                water_types = ["River", "Stream", "Small Lake", "Old Well"]
                w_type = random.choice(water_types)
                location.name = f"{w_type} at {x},{y}"
                location.description += f" A refreshing {w_type.lower()} is here."
                location.interactables.append(f"water_source:{w_type}")

            if attached_bp:
                for e in attached_bp.create_enemies(): location.add_enemy(e)
                for i in attached_bp.create_items(): location.add_item(i)
        
        self._populate_items(location, biome)
        
        # Special Goblin at 4,4,0
        if x == 4 and y == 4 and z == 0:
            from app.core.domain.enemy import Enemy
            import uuid
            special_goblin = Enemy(
                id=str(uuid.uuid4()),
                name="Friendly Goblin",
                description="He's smiling at you. A bit too broadly.",
                hp=10,
                max_hp=10,
                attack=0,
                xp_reward=100
            )
            location.add_enemy(special_goblin)
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
        variations = [
            "The trees are dense here.",
            "A small clearing opens up.",
            "You hear distant birds.",
            "Sunlight filters through the canopy.",
            "Roots cover the ground."
        ]
        if biome == "desert":
            variations = [
                "Endless sand dunes stretch out.",
                "The heat is oppressive.",
                "A dry wind blows.",
                "You see a mirage in the distance.",
                "Cracked earth beneath your feet."
            ]
        
        return f"You are in a {biome}. {random.choice(variations)}"



    def _populate_items(self, location: Location, biome: str):
        from app.core.domain.item import Item, ItemType
        import uuid
        import random
        
        # 30% chance of item
        if random.random() < 0.3:
            # 5% chance relative to spawning an item (so 1.5% global chance per room) to spawn equipment
            if random.random() < 0.05:
                equipment_pool = [
                    {"name": "Rusty Sword", "type": ItemType.WEAPON, "desc": "An old sword, heavily rusted.", "weight": 3.0, "slot": "weapon", "stats": {"strength": 2}, "durability": 10, "max_durability": 100},
                    {"name": "Torn Tunic", "type": ItemType.ARMOR, "desc": "A moth-eaten cloth tunic.", "weight": 1.0, "slot": "armor", "stats": {"defense": 1}, "durability": 15, "max_durability": 100},
                    {"name": "Worn Leather Armor", "type": ItemType.ARMOR, "desc": "A stiff, poorly maintained leather chestpiece.", "weight": 4.0, "slot": "armor", "stats": {"defense": 2}, "durability": 20, "max_durability": 100},
                    {"name": "Cracked Wooden Shield", "type": ItemType.ARMOR, "desc": "A wooden board that barely resembles a shield.", "weight": 2.5, "slot": "armor", "stats": {"defense": 1}, "durability": 8, "max_durability": 100}
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
            else:
                if biome == "forest":
                    options = [
                        {"name": "Stick", "type": ItemType.MATERIAL, "desc": "A sturdy wooden stick."},
                        {"name": "Stone", "type": ItemType.MATERIAL, "desc": "A sharp stone."},
                        {"name": "Mushroom", "type": ItemType.CONSUMABLE, "desc": "A questioned forest mushroom.", "restore_hunger": 10, "restore_hp_pct": 0.05, "restore_thirst": 0},
                        {"name": "Berry", "type": ItemType.CONSUMABLE, "desc": "A sweet red berry.", "restore_hunger": 5, "restore_hp_pct": 0.08, "restore_thirst": 0},
                        {"name": "Wild Apple", "type": ItemType.CONSUMABLE, "desc": "A crunchy wild apple.", "restore_hunger": 15, "restore_hp_pct": 0.15, "restore_thirst": 5},
                        {"name": "Torch", "type": ItemType.TOOL, "desc": "A wooden torch to illuminate dark places.", "weight": 1.0, "is_light_source": True},
                        {"name": "Water Flask (Empty)", "type": ItemType.TOOL, "desc": "An empty glass flask. Can be filled at a water source.", "weight": 0.5},
                        {"name": "Empty Flask", "type": ItemType.TOOL, "desc": "An empty glass bottle.", "weight": 0.5}
                    ]
                elif biome == "desert":
                    options = [
                        {"name": "Cactus Spine", "type": ItemType.MATERIAL, "desc": "A sharp cactus spine."},
                        {"name": "Sandstone", "type": ItemType.MATERIAL, "desc": "A chunk of sandstone."},
                        {"name": "Scorpion Tail", "type": ItemType.MATERIAL, "desc": "A venomous tail."},
                        {"name": "Cactus Water", "type": ItemType.CONSUMABLE, "desc": "Water extracted from a cactus.", "restore_thirst": 20, "restore_hunger": 0},
                        {"name": "Empty Flask", "type": ItemType.TOOL, "desc": "An empty glass bottle.", "weight": 0.5}
                    ]
                else:
                    options = [
                        {"name": "Unknown Debris", "type": ItemType.MATERIAL, "desc": "Useless debris."},
                        {"name": "Empty Flask", "type": ItemType.TOOL, "desc": "An empty glass bottle.", "weight": 0.5}
                    ]

                choice = random.choice(options)
                item = Item(
                    id=str(uuid.uuid4()),
                    name=choice["name"],
                    description=choice["desc"],
                    item_type=choice["type"],
                    restore_hunger=choice.get("restore_hunger", 0),
                    restore_thirst=choice.get("restore_thirst", 0),
                    restore_hp=choice.get("restore_hp", 0),
                    value=1,
                    weight=0.5
                )
            location.items.append(item)

    def _populate_enemies(self, location: Location, biome: str, z: int):
        from app.core.domain.enemy import Enemy
        import uuid
        import random
        
        # 20% chance of enemy
        # Safety check: Don't spawn hostiles in hubs or starting crossroads
        is_at_start = location.coordinates and location.coordinates.x == 0 and location.coordinates.y == 0 and location.coordinates.z == 0
        if "Hub" in location.name or "Crossroads" in location.name or is_at_start:
            return

        if random.random() < 0.2:
            if z < 0: # Underground
                pool = [
                    {"name": "Cave Spider", "hp": 20, "attack": 4, "xp": 20},
                    {"name": "Skeleton Warrior", "hp": 25, "attack": 5, "xp": 25},
                    {"name": "Green Slime", "hp": 15, "attack": 3, "xp": 15},
                    {"name": "Vampire Bat", "hp": 12, "attack": 4, "xp": 18},
                ]
            elif biome == "desert":
                pool = [
                    {"name": "Sand Scorpion", "hp": 15, "attack": 3, "xp": 15},
                    {"name": "Vulture", "hp": 12, "attack": 2, "xp": 12},
                    {"name": "Desert Bandit", "hp": 25, "attack": 4, "xp": 20},
                ]
            else: # Forest
                pool = [
                    {"name": "Goblin", "hp": 10, "attack": 2, "xp": 10},
                    {"name": "Gray Wolf", "hp": 15, "attack": 3, "xp": 15},
                    {"name": "Giant Spider", "hp": 18, "attack": 4, "xp": 18},
                    {"name": "Furious Boar", "hp": 30, "attack": 5, "xp": 30},
                ]
            
            choice = random.choice(pool)
            name = choice["name"]
            hp = choice["hp"]
            attack = choice["attack"]
            xp = choice["xp"]
            
            # Apply depth scaling
            if z < 0:
                depth_multiplier = abs(z)
                hp = int(hp * (1 + (depth_multiplier * 0.5)))
                attack = int(attack * (1 + (depth_multiplier * 0.3)))
                xp = int(xp * (1 + (depth_multiplier * 0.5)))
                
                # Add prefix for deeper floors
                if depth_multiplier > 1:
                    prefixes = ["Deep", "Ancient", "Abyssal", "Cursed"]
                    name = f"{random.choice(prefixes)} {name}"
            
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
