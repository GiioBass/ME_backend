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

