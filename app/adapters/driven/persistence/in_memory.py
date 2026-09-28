from typing import Dict, Optional
from app.ports.repositories import GameRepository
from app.core.domain.player import Player
from app.core.domain.location import Location

class InMemoryGameRepository(GameRepository):
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.locations: Dict[str, Location] = {}
        self.commands = []
        self.items = {} # name_or_id -> Item
        self.recipes = []

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

    def get_command_help(self):
        return self.commands

    def create_command_help(self, command, description, usage, category, alias=None):
        self.commands.append({
            "command": command,
            "description": description,
            "usage": usage,
            "category": category,
            "alias": alias
        })

    def save_item(self, item):
        self.items[item.id] = item
        self.items[item.name.lower()] = item

    def get_recipes(self):
        return self.recipes

    def create_recipe(self, recipe):
        self.recipes.append(recipe)

    def get_items_by_type(self, item_type):
        return [i for i in self.items.values() if i.item_type == item_type]

    def get_item_by_name(self, name_or_id):
        return self.items.get(name_or_id) or self.items.get(name_or_id.lower())

    def get_player_account(self, name: str):
        if not hasattr(self, "accounts"):
            self.accounts = {}
        return self.accounts.get(name.lower())

    def save_player_credentials(self, player_id: str, password_hash: str, salt: str):
        if not hasattr(self, "accounts"):
            self.accounts = {}
        player = self.get_player(player_id)
        if player:
            self.accounts[player.name.lower()] = {
                "id": player.id,
                "name": player.name,
                "password_hash": password_hash,
                "salt": salt
            }

    def get_players_in_location(self, location_id: str):
        result = []
        for p in self.players.values():
            if p.current_location_id == location_id:
                result.append({
                    "id": p.id,
                    "name": p.name,
                    "character_class": p.stats.character_class if p.stats else "adventurer",
                    "level": p.stats.level if p.stats else 1
                })
        return result

