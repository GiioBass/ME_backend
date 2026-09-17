from typing import Tuple, Optional
import random
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.ports.repositories import GameRepository
from app.core.config import settings

class BaseGameService:
    def __init__(self, repository: GameRepository, world_gen=None, dungeon_gen=None, game_settings: dict = None):
        self.repo = repository
        self.world_gen = world_gen
        self.dungeon_gen = dungeon_gen
        self.game_settings = game_settings or {}

    def _get_player_and_location(self, player_id: str) -> Tuple[Player, Location]:
        player = self.repo.get_player(player_id)
        if not player:
            raise ValueError("Player not found")
        current_location = self.repo.get_location(player.current_location_id)
        if not current_location:
            if self.world_gen:
                current_location = self.world_gen.generate_limbo()
            else:
                current_location = Location(
                    id=player.current_location_id,
                    name="Limbo",
                    description="You are lost in an undefined void."
                )
        return player, current_location

    def _apply_survival_mechanics(self, time_passed: int, player: Player) -> str:
        if not hasattr(player, "stats"):
            return ""
            
        s = self.game_settings.get("survival", {})
        msg = ""
        hunger_loss = max(0, time_passed // s.get("hunger_drain_rate", settings.HUNGER_DRAIN_INTERVAL))
        thirst_loss = max(0, time_passed // s.get("thirst_drain_rate", settings.THIRST_DRAIN_INTERVAL))
        
        if hunger_loss > 0:
            player.stats.hunger = max(0, player.stats.hunger - hunger_loss)
        if thirst_loss > 0:
            player.stats.thirst = max(0, player.stats.thirst - thirst_loss)
            
        is_starving = player.stats.hunger == 0
        is_dehydrated = player.stats.thirst == 0
        
        damage = 0
        if is_starving:
            damage += max(1, time_passed // s.get("starvation_damage_rate", settings.STARVATION_DAMAGE_INTERVAL))
            msg += "\nYou are starving! You lose HP."
        if is_dehydrated:
            damage += max(1, time_passed // s.get("dehydration_damage_rate", settings.DEHYDRATION_DAMAGE_INTERVAL))
            msg += "\nYou are dehydrated! You lose HP."
            
        if damage > 0:
            player.take_damage(damage)
        elif player.stats.hp < player.stats.max_hp:
            heal_interval = s.get("passive_heal_rate", settings.NATURAL_HEAL_INTERVAL)
            threshold = s.get("passive_heal_threshold_mins", 10)
            if time_passed >= threshold:
                heal_amount = time_passed // heal_interval
                player.stats.hp = min(player.stats.max_hp, player.stats.hp + heal_amount)
            
        return msg

    def _advance_time_and_events(self, world_time, player: Player, time_cost: int) -> str:
        msg_add = ""
        if time_cost > 0:
            world_time.advance(time_cost)
            self.repo.save_world_time(world_time)
            ticks_start = world_time.total_ticks - time_cost
            ticks_end = world_time.total_ticks
            
            def check_transition(threshold_hour):
                for t in range(ticks_start + 1, ticks_end + 1):
                    if (t % 1440) == (threshold_hour * 60):
                        return True
                return False

            if check_transition(settings.HOUR_NIGHT):
                msg_add += "\nNight has fallen."
            elif check_transition(settings.HOUR_DAWN):
                msg_add += "\nDawn breaks."

            msg_add += self._apply_survival_mechanics(time_cost, player)
            self.repo.save_player(player)
        return msg_add

    def _process_enemy_turns(self, player: Player, location: Location, excluded_enemy_id: str = None, chance: float = 1.0) -> Tuple[str, bool]:
        if not getattr(location, 'enemies', None):
            return "", False
            
        combat_log = ""
        armor = player.equipment.get("armor")
        mitigation = 0
        if armor and "defense" in armor.stat_bonuses:
            mitigation = armor.stat_bonuses["defense"]
 
        is_dead = False
        for enemy in location.enemies:
            if enemy.id == excluded_enemy_id or enemy.is_dead:
                continue
                
            if random.random() > chance:
                continue
 
            enemy_dmg = max(1, enemy.attack)
            final_dmg = max(1, enemy_dmg - mitigation)
            player.take_damage(final_dmg)
            
            combat_log += f"\n{enemy.name} attacks you for {final_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"
            
            if not player.is_alive():
                combat_log += "\nYou have been defeated...\nYou wake up back at the start, feeling woozy."
                player.heal()
                player.current_location_id = "loc_0_0_0"
                is_dead = True
                break
                
        return combat_log, is_dead

    def _ensure_neighbors(self, location: Location):
        if not location.coordinates:
            return
        if location.id.startswith("dng_"):
            return
        
        x, y, z = location.coordinates.x, location.coordinates.y, location.coordinates.z
        deltas = {
            "north": (0, 1, 0), "south": (0, -1, 0),
            "east": (1, 0, 0), "west": (-1, 0, 0),
        }
        for direction, (dx, dy, dz) in deltas.items():
            nx, ny, nz = x + dx, y + dy, z + dz
            if direction in location.exits:
                continue
            neighbor = self.repo.get_location_by_coordinates(nx, ny, nz)
            if not neighbor:
                if self.world_gen:
                    neighbor = self.world_gen.generate_single_location(nx, ny, nz)
                    self.repo.create_location(neighbor)
            if neighbor:
                self._link_locations(location, neighbor, direction)

    def _link_locations(self, loc_a: Location, loc_b: Location, dir_a_to_b: str):
        opposites = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
        dir_b_to_a = opposites.get(dir_a_to_b)
        loc_a.exits[dir_a_to_b] = loc_b.id
        loc_b.exits[dir_b_to_a] = loc_a.id
        self.repo.create_location(loc_a)
        self.repo.create_location(loc_b)
