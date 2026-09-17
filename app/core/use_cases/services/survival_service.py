from typing import Tuple, Optional
import uuid
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.domain.item import Item, ItemType
from app.core.config import settings
from app.core.use_cases.services.base_service import BaseGameService

class SurvivalService(BaseGameService):
    def consume_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not item_name:
            return "Consume what?", player, location
        
        found_item = player.remove_item(item_name)
        if not found_item:
            return f"You don't have '{item_name}'.", player, location
            
        item_type_str = str(found_item.item_type).lower()
        if not item_type_str.endswith("consumable"):
            player.add_item(found_item) # Put it back
            return f"{found_item.name} is not consumable.", player, location
            
        # Apply effects
        msg = f"You consumed {found_item.name}."
        
        if found_item.restore_hp != 0 or found_item.restore_hp_pct != 0:
            pct_restore = int(player.stats.max_hp * found_item.restore_hp_pct)
            total_hp_restore = found_item.restore_hp + pct_restore
            player.stats.hp = min(player.stats.max_hp, max(0, player.stats.hp + total_hp_restore))
            action_word = "Restored" if total_hp_restore > 0 else "Lost"
            msg += f" {action_word} {abs(total_hp_restore)} HP."
            
        if found_item.restore_mp != 0 or found_item.restore_mp_pct != 0:
            pct_restore = int(player.stats.max_mp * found_item.restore_mp_pct)
            total_mp_restore = found_item.restore_mp + pct_restore
            player.stats.mp = min(player.stats.max_mp, max(0, player.stats.mp + total_mp_restore))
            action_word = "Restored" if total_mp_restore > 0 else "Lost"
            msg += f" {action_word} {abs(total_mp_restore)} MP."
            
        if found_item.restore_hunger != 0:
            player.stats.hunger = min(100, max(0, player.stats.hunger + found_item.restore_hunger))
            action_word = "Restored" if found_item.restore_hunger > 0 else "Lost"
            msg += f" {action_word} {abs(found_item.restore_hunger)} Hunger."
            
        if found_item.restore_thirst != 0:
            player.stats.thirst = min(100, max(0, player.stats.thirst + found_item.restore_thirst))
            action_word = "Restored" if found_item.restore_thirst > 0 else "Lost"
            msg += f" {action_word} {abs(found_item.restore_thirst)} Thirst."
            
        for effect in found_item.effects:
            if effect.get("type") == "heal":
                amount = effect.get("amount", 0)
                player.stats.hp = min(player.stats.max_hp, player.stats.hp + amount)
                msg += f" Restored {amount} HP."
                
        self.repo.save_player(player)
        
        # Recycling logic: if Water Flask was consumed, give back Empty Flask
        if found_item.name.lower() == "water flask":
            empty_flask = Item(
                id=str(uuid.uuid4()),
                name="Empty Flask",
                description="An empty glass vessel, useful for holding liquids.",
                item_type=ItemType.OTHER,
                value=1,
                weight=0.5
            )
            player.add_item(empty_flask)
            self.repo.save_player(player)
            msg += " You now have an Empty Flask."

        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 1)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        msg += enemy_log
        
        if is_dead:
            return msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return msg + time_msg, player, location

    def fill_flask(self, player_id: str, arg_str: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        has_water = any(inter.startswith("water_source:") for inter in location.interactables)
        if not has_water:
            return "There is no water source here to fill anything.", player, location
            
        valid_flask_names = ["empty flask", "water flask (empty)"]
        empty_flask = next((i for i in player.inventory if i.name.lower() in valid_flask_names), None)
        
        if not empty_flask:
            return "You don't have an Empty Flask to fill.", player, location
            
        player.remove_item(empty_flask.name)
        water_flask = Item(
            id=str(uuid.uuid4()),
            name="Water Flask",
            description="A flask filled with fresh water.",
            item_type=ItemType.CONSUMABLE,
            restore_thirst=40,
            value=2,
            weight=1.0
        )
        player.add_item(water_flask)
        
        msg = f"You fill the {empty_flask.name} with water."
        self.repo.save_player(player)
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 2)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        msg += enemy_log
        
        if is_dead:
            return msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return msg + time_msg, player, location

    def drink_from_source(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        
        has_water = any(inter.startswith("water_source:") for inter in location.interactables)
        if not has_water:
            return "There is no water source here to drink from.", player, location
            
        if player.stats.thirst >= 100:
            return "You are not thirsty.", player, location

        restore_amount = 30
        player.stats.thirst = min(100, player.stats.thirst + restore_amount)
        
        msg = "You cup your hands and drink the cool, refreshing water."
        self.repo.save_player(player)
        
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, 1)
        
        enemy_log, is_dead = self._process_enemy_turns(player, location, chance=settings.ENEMY_ATTACK_CHANCE_INTERACTION)
        msg += enemy_log
        
        if is_dead:
            return msg + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        return msg + time_msg, player, location

    def rest(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        r_conf = self.game_settings.get("rest", {})
        
        hunger_cost = r_conf.get("hunger_cost", 15)
        thirst_cost = r_conf.get("thirst_cost", 15)
        
        if player.stats.hunger < hunger_cost or player.stats.thirst < thirst_cost:
            return "You are too hungry or thirsty to rest effectively.", player, location
            
        if player.stats.hp >= player.stats.max_hp:
            return "You are already fully rested.", player, location

        player.stats.hunger = max(0, player.stats.hunger - hunger_cost)
        player.stats.thirst = max(0, player.stats.thirst - thirst_cost)
        
        if r_conf.get("full_heal", settings.REST_HEAL_FULL):
            player.heal()
            msg = "You take a long rest and wake up feeling completely refreshed. Your HP is fully restored."
        else:
            heal_amt = r_conf.get("heal_amount", settings.REST_BASE_HEAL)
            player.stats.hp = min(player.stats.max_hp, player.stats.hp + heal_amt)
            msg = f"You take a rest. You've recovered {heal_amt} HP, but you're now hungrier and thirstier."
        
        duration = r_conf.get("duration_mins", settings.REST_DURATION_MINS)
        world_time = self.repo.get_world_time()
        time_msg = self._advance_time_and_events(world_time, player, duration)
        
        self.repo.save_player(player)
        return msg + time_msg, player, location
