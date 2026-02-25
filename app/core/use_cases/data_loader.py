import json
import os
from app.ports.repositories import GameRepository
from app.core.domain.location import Location, Coordinates

class DataLoader:
    def __init__(self, repo: GameRepository):
        self.repo = repo
        self.data_path = os.path.join(os.path.dirname(__file__), "../../../data")

    def load_static_locations(self):
        file_path = os.path.join(self.data_path, "static_locations.json")
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found.")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for loc_data in data:
                # loc_0_0_0 must be generated through the world_generator.generate_chunk now
                if loc_data["id"] == "loc_0_0_0":
                    continue
                # Check if it already exists
                existing = self.repo.get_location(loc_data["id"])
                if not existing:
                    # Construct Domain Location
                    coordinates = None
                    if "coordinates" in loc_data:
                        coordinates = Coordinates(
                            x=loc_data["coordinates"]["x"],
                            y=loc_data["coordinates"]["y"],
                            z=loc_data["coordinates"]["z"]
                        )
                    
                    loc = Location(
                        id=loc_data["id"],
                        name=loc_data["name"],
                        description=loc_data["description"],
                        exits=loc_data.get("exits", {}),
                        interactables=loc_data.get("interactables", []),
                        coordinates=coordinates
                    )
                    
                    self.repo.create_location(loc)
                    print(f"Loaded static location: {loc.name} ({loc.id})")
