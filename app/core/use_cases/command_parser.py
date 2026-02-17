from typing import Tuple, Dict, Optional, List
from app.core.domain.player import Player
from app.core.domain.location import Location

class CommandResult:
    def __init__(self, message: str, player: Player, location: Location):
        self.message = message
        self.player = player
        self.location = location

class CommandParser:
    def parse(self, command_text: str, player: Player, location: Location, save_callback) -> CommandResult:
        args = command_text.lower().split()
        if not args:
            return CommandResult("Please enter a command.", player, location)
        
        action = args[0]
        
        if action in ["go", "move", "walk", "north", "south", "east", "west", "up", "down", "enter", "climb"]:
            return self._handle_movement(args, action, player, location, save_callback)
        elif action in ["look", "examine"]:
            return CommandResult(location.description, player, location)
        elif action in ["stats", "status"]:
            return CommandResult(str(player.stats), player, location)
        
        return CommandResult("I don't understand that command.", player, location)

    def _handle_movement(self, args: List[str], action: str, player: Player, location: Location, save_callback) -> CommandResult:
        direction = args[1] if len(args) > 1 else action
        
        # Map aliases
        if direction in ["enter", "dive", "down"]:
            direction = "down"
        elif direction in ["climb", "surface", "up"]:
            direction = "up"
            
        if direction not in ["north", "south", "east", "west", "up", "down"]:
                 if action in ["north", "south", "east", "west", "up", "down"]:
                     direction = action
                 else:
                     return CommandResult("Go where?", player, location)


        next_location_id = player.move(direction, location.exits)
        if next_location_id:
            player.current_location_id = next_location_id
            save_callback(player)
            # We need the new location, but the parser doesn't have access to repo directly usually
            # However, for simplicity, we return the old location object, and let the service fetch the new one?
            # Or we change the return signature to indicate a location change?
            # Let's keep it simple: The service handles fetching the new location if the ID changed.
            # But here we are returning CommandResult with `location`. 
            # If we return the OLD location object with the NEW player state (ID changed), the Service can detect the mismatch.
            return CommandResult(f"You travel {direction}...", player, location)
        else:
            return CommandResult("You can't go that way.", player, location)
