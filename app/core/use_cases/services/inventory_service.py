from typing import Tuple, List, Dict
from collections import Counter
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.config import settings
from app.core.use_cases.services.base_service import BaseGameService

class InventoryService(BaseGameService):
    def __init__(self, repository, world_gen=None, dungeon_gen=None, game_settings=None, quest_service=None):
        super().__init__(repository, world_gen, dungeon_gen, game_settings)
        self.quest_service = quest_service

    def _parse_item_arg(self, arg_str: str) -> Tuple[str, int]:
        parts = arg_str.strip().split()
        if not parts:
            return "", 1
        if parts[-1].isdigit():
            return " ".join(parts[:-1]), int(parts[-1])
        return arg_str, 1

    def map_inventory(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not player.inventory:
            return "You are not carrying anything.", player, location
        counts = Counter((i.name, i.item_type) for i in player.inventory)
        items_list = []
        for (name, item_type), count in sorted(counts.items()):
            display = f"- {name} ({item_type})"
            if count > 1:
                display += f" x{count}"
            items_list.append(display)
        weight_info = f"Weight: {player.current_weight:.1f}/{player.stats.max_weight:.1f}"
        return f"Inventory ({weight_info}):\n" + "\n".join(items_list), player, location

    def take_item(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        item_name, quantity = self._parse_item_arg(arg_str)
        if not item_name:
            return "Take what?", player, location
        
        taken_count = 0
        taken_names = []
        for _ in range(quantity):
            found_item = location.remove_item(item_name)
            if not found_item:
                break
            
            if player.current_weight + found_item.weight > player.stats.max_weight:
                location.add_item(found_item) # put it back
                msg = f"Inventory full! ({player.current_weight:.1f}/{player.stats.max_weight:.1f})."
                if taken_count > 0:
                    msg = f"You grabbed {taken_count}x {taken_names[-1]} before getting too heavy. {msg}"
                return msg, player, location
                
            found_item.is_dropped = False
            player.add_item(found_item)
            taken_count += 1
            taken_names.append(found_item.name)

        if taken_count == 0:
            return "You don't see that here.", player, location

        time_cost = 1
        name_display = taken_names[0]
        base_msg = f"You picked up {taken_count}x {name_display}."
        
        if self.quest_service:
            for t_name in taken_names:
                q_log = self.quest_service.update_gather_progress(player, t_name)
                base_msg += q_log
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        if is_dead:
            return base_msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg + time_msg, player, location

    def drop_item(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        
        item_name, quantity = self._parse_item_arg(arg_str)
        if not item_name:
            return "Drop what?", player, location
        
        dropped_count = 0
        dropped_names = []
        for _ in range(quantity):
            found_item = player.remove_item(item_name)
            if not found_item:
                break
            found_item.is_dropped = True
            location.add_item(found_item)
            dropped_count += 1
            dropped_names.append(found_item.name)

        if dropped_count == 0:
            return "You don't have that.", player, location

        time_cost = 1
        name_display = dropped_names[0]
        base_msg = f"You dropped {dropped_count}x {name_display}."
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        base_msg += enemy_log

        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, time_cost)
        
        if is_dead:
            return base_msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg + time_msg, player, location

    def equip_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not item_name:
            return "Equip what?", player, location
            
        found_item = next((i for i in player.inventory if i.name.lower() == item_name.lower()), None)
        if not found_item:
            return f"You don't have a '{item_name}' in your inventory.", player, location
            
        base_msg = player.equip(found_item)
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        if is_dead:
            return base_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg, player, location

    def unequip_item(self, player_id: str, slot: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not slot:
            return "Unequip from what slot?", player, location
            
        base_msg = player.unequip(slot)
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        base_msg += enemy_log
        
        self.repo.save_player(player)
        if is_dead:
            return base_msg, player, self.repo.get_location("loc_0_0_0") or location
        return base_msg, player, location

    def list_chest(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here.", player, location
            
        if not location.camp_storage:
            return "The camp chest is empty.", player, location
            
        counts = Counter((i.name, i.item_type) for i in location.camp_storage)
        items_list = []
        for (name, item_type), count in sorted(counts.items()):
            display = f"- {name} ({item_type})"
            if count > 1:
                display += f" x{count}"
            items_list.append(display)
            
        return "Camp Chest Contents:\n" + "\n".join(items_list), player, location

    def store_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here to store items.", player, location
            
        if not item_name:
            return "Store what?", player, location
            
        found_item = player.remove_item(item_name)
        if found_item:
            location.store_camp_item(found_item)
            
            base_msg = f"You stored {found_item.name} in the camp chest."
            enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
            base_msg += enemy_log
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            
            if is_dead:
                return base_msg, player, self.repo.get_location("loc_0_0_0") or location
            return base_msg, player, location
            
        return f"You don't have '{item_name}'.", player, location

    def retrieve_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if location.id not in player.waypoints.values():
            return "There is no camp chest here to retrieve items from.", player, location
            
        if not item_name:
            return "Retrieve what?", player, location
            
        found_item = location.retrieve_camp_item(item_name)
        if found_item:
            if player.current_weight + found_item.weight > player.stats.max_weight:
                location.store_camp_item(found_item) # put it back
                return f"You cannot carry {found_item.name}, it is too heavy.", player, location
                
            player.add_item(found_item)
            
            base_msg = f"You retrieved {found_item.name} from the camp chest."
            enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
            base_msg += enemy_log
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            
            if is_dead:
                return base_msg, player, self.repo.get_location("loc_0_0_0") or location
            return base_msg, player, location
            
        return f"There is no '{item_name}' in the camp chest.", player, location
