import json
from typing import List
import os
from app.core.domain.location import Location, Coordinates

class StaticAreaLoader:
    def __init__(self, file_path: str = None):
        if file_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
            file_path = os.path.join(base_dir, "static_areas.json")
        self.file_path = file_path

    def load_static_areas(self) -> List[Location]:
        if not os.path.exists(self.file_path):
            if os.path.exists("data/static_areas.json"):
                self.file_path = "data/static_areas.json"
            else:
                return []
            
        locations = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            for item in data:
                coords_data = item.get("coordinates")
                coords = None
                if coords_data:
                    coords = Coordinates(
                        x=coords_data.get("x", 0),
                        y=coords_data.get("y", 0),
                        z=coords_data.get("z", 0)
                    )
                
                location = Location(
                    id=item.get("id"),
                    name=item.get("name"),
                    description=item.get("description"),
                    coordinates=coords,
                    interactables=item.get("interactables", []),
                    exits=item.get("exits", {})
                )
                locations.append(location)
                
        return locations
