from typing import Tuple, Dict, Optional, List
from app.core.domain.player import Player
from app.core.domain.location import Location

class CommandResult:
    def __init__(self, message: str, player: Player, location: Location, time_cost: int = 0):
        self.message = message
        self.player = player
        self.location = location
        self.time_cost = time_cost

class CommandParser:
    def parse(self, command_text: str, player: Player, location: Location, world_time, save_player_callback, save_location_callback=None) -> CommandResult:
        args = command_text.lower().split()
        if not args:
            return CommandResult("Please enter a command.", player, location)
        
        action = args[0]
        
        if action in ["go", "move", "walk", "north", "south", "east", "west", "up", "down", "enter", "climb"]:
            return self._handle_movement(args, action, player, location, save_player_callback)
        elif action in ["look", "examine"]:
            return self._handle_look(args, player, location, world_time)
        elif action in ["stats", "status"]:
            return CommandResult(str(player.stats), player, location)
        elif action in ["take", "get", "pickup", "grab"]:
            return self._handle_take(args, player, location, save_player_callback, save_location_callback)
        elif action in ["drop", "discard"]:
            return self._handle_drop(args, player, location, save_player_callback, save_location_callback)
        elif action in ["inventory", "inv", "i"]:
            return self._handle_inventory(player, location)
        elif action in ["attack", "fight", "hit", "kill"]:
            return self._handle_attack(args, player, location, save_player_callback, save_location_callback)
        elif action in ["time", "clock", "date"]:
            return CommandResult(f"It is {world_time.get_time_string()}.", player, location)
        
        return CommandResult("I don't understand that command.", player, location)

    def _handle_look(self, args: List[str], player: Player, location: Location, world_time) -> CommandResult:
        base_desc = location.description
        
        if world_time and world_time.is_night():
            base_desc = f"[NIGHT] {base_desc} (It is dark)"
        
        # Append items found
        if location.items:
            item_names = [i.name for i in location.items]
            base_desc += f"\nYou see items: {', '.join(item_names)}"
            
        # Append enemies
        if location.enemies:
            enemy_names = [f"{e.name} (HP:{e.hp})" for e in location.enemies]
            base_desc += f"\nEnemies here: {', '.join(enemy_names)}"
            
        return CommandResult(base_desc, player, location)

    def _handle_inventory(self, player: Player, location: Location) -> CommandResult:
        if not player.inventory:
            return CommandResult("You are not carrying anything.", player, location)
        
        # Group items by (name, type) to count quantities
        from collections import Counter
        counts = Counter((i.name, i.item_type) for i in player.inventory)
        
        items_list = []
        # Sort by name for cleaner display
        for (name, item_type), count in sorted(counts.items()):
            display = f"- {name} ({item_type})"
            if count > 1:
                display += f" x{count}"
            items_list.append(display)
            
        return CommandResult(f"Inventory:\n" + "\n".join(items_list), player, location)

    def _handle_take(self, args: List[str], player: Player, location: Location, save_player, save_location) -> CommandResult:
        if len(args) < 2:
            return CommandResult("Take what?", player, location)
        
        item_name = " ".join(args[1:])
        
        # Check if item in location
        # Naive matching by name
        found_item = location.remove_item(item_name)
        if found_item:
            player.add_item(found_item)
            if save_player: save_player(player)
            if save_location: save_location(location)
            return CommandResult(f"You picked up {found_item.name}.", player, location, time_cost=1)
        
        return CommandResult("You don't see that here.", player, location)

    def _handle_drop(self, args: List[str], player: Player, location: Location, save_player, save_location) -> CommandResult:
        if len(args) < 2:
            return CommandResult("Drop what?", player, location)
        
        item_name = " ".join(args[1:])
        
        found_item = player.remove_item(item_name)
        if found_item:
            location.add_item(found_item)
            if save_player: save_player(player)
            if save_location: save_location(location)
            return CommandResult(f"You dropped {found_item.name}.", player, location, time_cost=1)
            
        return CommandResult("You don't have that.", player, location)

    def _handle_attack(self, args: List[str], player: Player, location: Location, save_player, save_location) -> CommandResult:
        if len(args) < 2:
            return CommandResult("Attack what?", player, location)
        
        target_name = " ".join(args[1:])
        enemy = location.get_enemy(target_name)
        
        if not enemy:
             return CommandResult(f"You don't see '{target_name}' here.", player, location)

        # 1. Player Attacks Enemy
        # Damage formula (simple for now)
        damage = max(1, (player.stats.strength // 2))
        actual_dmg = enemy.take_damage(damage)
        
        combat_log = f"You hit {enemy.name} for {actual_dmg} damage. (Enemy HP: {enemy.hp}/{enemy.max_hp})"
        
        # 2. Check Enemy Death
        if enemy.is_dead:
            combat_log += f"\n{enemy.name} collapses and dies!"
            location.remove_enemy(enemy.id)
            player.gain_xp(enemy.xp_reward)
            combat_log += f"\nYou gain {enemy.xp_reward} XP."
            
            # Simple Loot (Drop items?)
            # For now, no loot drops logic implemented yet in Enemy
            
            if save_player: save_player(player)
            if save_location: save_location(location)
            return CommandResult(combat_log, player, location, time_cost=2)
            
        # 3. Enemy Attacks Player (if alive)
        enemy_dmg = max(1, enemy.attack) # Simple logic, no defense yet
        player.take_damage(enemy_dmg)
        combat_log += f"\n{enemy.name} attacks you for {enemy_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"
        
        if not player.is_alive():
            combat_log += "\nYou have been defeated..."
            # Respawn logic to be handled by GameService or here?
            # Let's handle it here for MVP simplicity: Reset HP, move to start
            player.heal()
            player.current_location_id = "loc_0_0_0" # Hardcoded start or "start"
            combat_log += "\nYou wake up back at the start, feeling woozy."
            # We need to update location implies moving...
            # The parser returns the OLD location object usually, but ID changed.
            # GameService will fetch the new location.
        
        if save_player: save_player(player)
        if save_location: save_location(location) # Enemy HP updated
        
        return CommandResult(combat_log, player, location, time_cost=2)

    def _handle_movement(self, args: List[str], action: str, player: Player, location: Location, save_player_callback) -> CommandResult:
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
            if save_player_callback: save_player_callback(player)
            # We need the new location, but the parser doesn't have access to repo directly usually
            # However, for simplicity, we return the old location object, and let the service fetch the new one?
            # Or we change the return signature to indicate a location change?
            # Let's keep it simple: The service handles fetching the new location if the ID changed.
            # But here we are returning CommandResult with `location`. 
            # If we return the OLD location object with the NEW player state (ID changed), the Service can detect the mismatch.
            return CommandResult(f"You travel {direction}...", player, location, time_cost=10)
        else:
            return CommandResult("You can't go that way.", player, location)
