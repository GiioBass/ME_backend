from abc import ABC, abstractmethod
from typing import Optional
from app.core.domain.player import Player
from app.core.domain.location import Location

class GameRepository(ABC):
    @abstractmethod
    def get_player(self, player_id: str) -> Optional[Player]:
        pass

    @abstractmethod
    def get_player_by_name(self, name: str) -> Optional[Player]:
        pass

    @abstractmethod
    def save_player(self, player: Player) -> Player:
        pass

    @abstractmethod
    def get_location(self, location_id: str) -> Optional[Location]:
        pass
    
    @abstractmethod
    def create_location(self, location: Location) -> Location:
        pass

    @abstractmethod
    def get_location_by_coordinates(self, x: int, y: int, z: int) -> Optional[Location]:
        pass

    @abstractmethod
    def get_world_time(self) -> 'WorldTime':
        pass

    @abstractmethod
    def save_world_time(self, world_time: 'WorldTime'):
        pass

