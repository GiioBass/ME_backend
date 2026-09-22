from typing import Tuple
import random
import uuid
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.domain.item import Item, ItemType
from app.core.config import settings
from app.core.use_cases.services.base_service import BaseGameService

class CombatService(BaseGameService):
    def __init__(self, repository, world_gen=None, dungeon_gen=None, game_settings=None, quest_service=None):
        super().__init__(repository, world_gen, dungeon_gen, game_settings)
        self.quest_service = quest_service

    def attack_enemy(self, player_id: str, target_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()
        if not target_name:
            return "Attack what?", player, location
        
        enemy = location.get_enemy(target_name)
        if not enemy:
            return f"You don't see '{target_name}' here.", player, location

        # Calculate player damage (balanced base scaling)
        total_strength = player.stats.strength
        weapon = player.equipment.get("weapon")
        if weapon and "strength" in weapon.stat_bonuses:
            total_strength += weapon.stat_bonuses["strength"]
            
        damage = max(1, (total_strength // 3))
        actual_dmg = enemy.take_damage(damage)
        combat_log = f"You strike {enemy.name} for {actual_dmg} damage. (Enemy HP: {enemy.hp}/{enemy.max_hp})"
        
        # Basic attack recharges tactical stance/skills
        if getattr(player, "skill_cooldowns", None):
            player.skill_cooldowns.clear()
            combat_log += " Tactical stance refreshed!"
        
        if enemy.is_dead:
            combat_log += f"\n{enemy.name} collapses and dies!"
            location.remove_enemy(enemy.id)
            player.gain_xp(enemy.xp_reward)
            combat_log += f"\nYou gain {enemy.xp_reward} XP."
            
            if self.quest_service:
                q_log = self.quest_service.update_kill_progress(player, enemy.name)
                combat_log += q_log
            
            # Thematic Monster Drops
            drop_log = self._generate_enemy_loot(enemy, location)
            combat_log += drop_log
            
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_ATTACK)
            return combat_log + time_msg, player, location
            
        # Enemy retaliates (the one being attacked)
        enemy_dmg = max(1, enemy.attack)
        armor = player.equipment.get("armor")
        mitigation = 0
        if armor and "defense" in armor.stat_bonuses:
            mitigation = armor.stat_bonuses["defense"]
            
        final_dmg = max(1, enemy_dmg - mitigation)
        player.take_damage(final_dmg)
        combat_log += f"\n{enemy.name} retaliates for {final_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"
        
        # Other enemies attack
        other_combat_log, _ = self._process_enemy_turns(player, location, excluded_enemy_id=enemy.id)
        combat_log += other_combat_log
        
        if not player.is_alive():
            combat_log += "\nYou have been defeated...\nYou wake up back at the start, feeling woozy."
            player.heal()
            player.current_location_id = "loc_0_0_0"
            self.repo.save_player(player)
            self.repo.create_location(location)
            time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_ATTACK)
            return combat_log + time_msg, player, self.repo.get_location("loc_0_0_0") or location
        
        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_ATTACK)
        return combat_log + time_msg, player, location
