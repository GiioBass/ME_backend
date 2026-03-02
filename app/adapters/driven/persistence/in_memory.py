from typing import Dict, Optional
from app.ports.repositories import GameRepository
from app.core.domain.player import Player
from app.core.domain.location import Location

class InMemoryGameRepository(GameRepository):
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.locations: Dict[str, Location] = {}

    def get_player(self, player_id: str) -> Optional[Player]:
        return self.players.get(player_id)

    def get_player_by_name(self, name: str) -> Optional[Player]:
        for p in self.players.values():
            if p.name.lower() == name.lower():
                return p
        return None

    def save_player(self, player: Player) -> Player:
        self.players[player.id] = player
        return player

    def get_location(self, location_id: str) -> Optional[Location]:
        return self.locations.get(location_id)
    
    def create_location(self, location: Location) -> Location:
        self.locations[location.id] = location
        return location

    def get_location_by_coordinates(self, x: int, y: int, z: int) -> Optional[Location]:
        for loc in self.locations.values():
            if loc.coordinates and loc.coordinates.x == x and loc.coordinates.y == y and loc.coordinates.z == z:
                return loc
        return None

    def get_locations_in_radius(self, x: int, y: int, z: int, radius: int) -> list[Location]:
        nearby = []
        for loc in self.locations.values():
            if loc.coordinates and loc.coordinates.z == z:
                dist_x = abs(loc.coordinates.x - x)
                dist_y = abs(loc.coordinates.y - y)
                if dist_x <= radius and dist_y <= radius:
                    nearby.append(loc)
        return nearby

    def get_world_time(self):
        from app.core.domain.time_system import WorldTime
        return getattr(self, "world_time", WorldTime(total_ticks=0))

    def save_world_time(self, world_time):
        self.world_time = world_time

