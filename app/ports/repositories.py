from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.domain.player import Player
    from app.core.domain.location import Location
    from app.core.domain.recipe import Recipe

class GameRepository(ABC):
    @abstractmethod
    def get_player(self, player_id: str) -> Optional['Player']:
        pass

    @abstractmethod
    def get_player_by_name(self, name: str) -> Optional['Player']:
        pass

    @abstractmethod
    def save_player(self, player: 'Player') -> 'Player':
        pass

    @abstractmethod
    def get_location(self, location_id: str) -> Optional['Location']:
        pass
    
    @abstractmethod
    def create_location(self, location: 'Location') -> 'Location':
        pass

    @abstractmethod
    def get_location_by_coordinates(self, x: int, y: int, z: int) -> Optional['Location']:
        pass

    @abstractmethod
    def get_locations_in_radius(self, x: int, y: int, z: int, radius: int) -> list['Location']:
        pass

    @abstractmethod
    def get_world_time(self) -> 'WorldTime':
        pass

    @abstractmethod
    def save_world_time(self, world_time: 'WorldTime'):
        pass

    @abstractmethod
    def get_command_help(self) -> list[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_command_help(self, command: str, description: str, usage: str, category: str, alias: Optional[str] = None):
        pass

    @abstractmethod
    def save_item(self, item: 'Item'):
        pass

    @abstractmethod
    def get_recipes(self) -> List['Recipe']:
        pass

    @abstractmethod
    def create_recipe(self, recipe: 'Recipe'):
        pass

    @abstractmethod
    def get_items_by_type(self, item_type: str) -> List['Item']:
        pass

    @abstractmethod
    def get_item_by_name(self, name_or_id: str) -> Optional['Item']:
        pass

