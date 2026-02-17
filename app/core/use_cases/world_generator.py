from typing import List, Dict
import random
from app.core.domain.location import Location, Coordinates

class WorldGenerator:
    def generate_start_location(self) -> Location:
        return Location(
            id="start", 
            name="Crossroads", 
            description="You stand at a dusty crossroads. Paths lead in all directions.",
            coordinates=Coordinates(x=0, y=0, z=0)
        )

    def generate_limbo(self) -> Location:
        return Location(id="limbo", name="Limbo", description="You are floating in nothingness.")

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
                loc_id = f"loc_{x}_{y}_0"
                name = f"{biome.capitalize()} Area {x},{y}"
                desc = self._generate_description(biome, x, y)
                
                location = Location(
                    id=loc_id,
                    name=name,
                    description=desc,
                    coordinates=Coordinates(x=x, y=y, z=0)
                )

                # Chance for Cave Entrance
                if random.random() < 0.1: # 10% chance
                    cave_id = f"loc_{x}_{y}_minus1"
                    cave_loc = Location(
                        id=cave_id,
                        name=f"Underground Cave {x},{y}",
                        description="You are in a dark, damp cave beneath the surface.",
                        coordinates=Coordinates(x=x, y=y, z=-1)
                    )
                    # Link them
                    location.exits["down"] = cave_id
                    cave_loc.exits["up"] = loc_id
                    location.description += " You see a dark opening leading down."
                    
                    # Add cave to grid/list so it can be persisted
                    # We add it to the list but maybe not the grid key "x,y" because that overwrites surface?
                    # The grid is used for linking neighbors N/S/E/W. Caves don't link horizontally yet in this step.
                    generated_locations.append(cave_loc)

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
