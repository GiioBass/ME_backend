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

    def _generate_enemy_loot(self, enemy, location: Location) -> str:
        import uuid
        from app.core.domain.item import Item, ItemType

        name_lower = enemy.name.lower()
        drops = []
        
        # Determine candidate drops based on monster type
        if "spider" in name_lower:
            drops.append("base_spider_silk")
            if random.random() < 0.40: drops.append("base_poison_sac")
        elif "wolf" in name_lower:
            drops.append("base_wolf_pelt")
            if random.random() < 0.50: drops.append("base_bone")
        elif "boar" in name_lower:
            drops.append("base_leather")
            if random.random() < 0.50: drops.append("base_bone")
            if random.random() < 0.30: drops.append("base_wild_apple")
        elif "scorpion" in name_lower:
            drops.append("base_scorpion_tail")
            if random.random() < 0.40: drops.append("base_poison_sac")
            if random.random() < 0.30: drops.append("base_cactus_spine")
        elif "vulture" in name_lower:
            drops.append("base_bone")
            if random.random() < 0.40: drops.append("base_stick")
        elif "skeleton" in name_lower:
            drops.append("base_bone")
            if random.random() < 0.35: drops.append("base_iron_ingot")
            if random.random() < 0.20: drops.append("base_rusty_sword")
            if random.random() < 0.15: drops.append("base_cracked_shield")
        elif "goblin" in name_lower:
            drops.append("base_cloth")
            if random.random() < 0.50: drops.append("base_wool")
            if random.random() < 0.30: drops.append("base_stone")
            if random.random() < 0.15: drops.append("base_rusty_sword")
        elif any(k in name_lower for k in ["bandit", "mercenary", "deserter"]):
            drops.append("base_cloth")
            if random.random() < 0.50: drops.append("base_wool")
            if random.random() < 0.35: drops.append("base_bandage")
            if random.random() < 0.20: drops.append("base_rusty_sword")
            if random.random() < 0.15: drops.append("base_leather_armor")
        elif "slime" in name_lower:
            drops.append("base_poison_sac")
        elif "bat" in name_lower:
            drops.append("base_bone")
        else:
            drops.append("base_bone")
            if random.random() < 0.15: drops.append("base_rusty_sword")

        # Boss or abyssal loot bonus
        if getattr(enemy, 'is_boss', False) or any(k in name_lower for k in ["warden", "abyssal", "boss", "tyrant", "dread"]):
            drops.append("base_abyssal_core")
            if random.random() < 0.50: drops.append("base_iron_sword")

        FALLBACK_ITEMS = {
            "base_spider_silk": {"name": "Spider Silk", "description": "Strong, sticky thread spun by giant spiders.", "item_type": ItemType.MATERIAL, "value": 6, "weight": 0.1},
            "base_poison_sac": {"name": "Poison Sac", "description": "A venom gland extracted from arachnids or serpents.", "item_type": ItemType.MATERIAL, "value": 10, "weight": 0.2},
            "base_wolf_pelt": {"name": "Wolf Pelt", "description": "Thick fur hide from a timber wolf.", "item_type": ItemType.MATERIAL, "value": 8, "weight": 1.2},
            "base_leather": {"name": "Leather", "description": "Cured animal hide.", "item_type": ItemType.MATERIAL, "value": 6, "weight": 0.8},
            "base_bone": {"name": "Bone", "description": "A sturdy animal bone.", "item_type": ItemType.MATERIAL, "value": 2, "weight": 0.5},
            "base_scorpion_tail": {"name": "Scorpion Tail", "description": "A venomous tail.", "item_type": ItemType.MATERIAL, "value": 10, "weight": 0.3},
            "base_cactus_spine": {"name": "Cactus Spine", "description": "A sharp cactus spine.", "item_type": ItemType.MATERIAL, "value": 1, "weight": 0.1},
            "base_cloth": {"name": "Cloth", "description": "Woven plant fabric.", "item_type": ItemType.MATERIAL, "value": 3, "weight": 0.2},
            "base_wool": {"name": "Wool", "description": "Soft fleece sheared from sheep or wild beasts.", "item_type": ItemType.MATERIAL, "value": 3, "weight": 0.3},
            "base_stone": {"name": "Stone", "description": "A sharp stone.", "item_type": ItemType.MATERIAL, "value": 1, "weight": 0.5},
            "base_stick": {"name": "Stick", "description": "A sturdy wooden stick.", "item_type": ItemType.MATERIAL, "value": 1, "weight": 0.5},
            "base_iron_ingot": {"name": "Iron Ingot", "description": "A heavy bar of refined iron metal.", "item_type": ItemType.MATERIAL, "value": 15, "weight": 2.0},
            "base_bandage": {"name": "Bandage", "description": "Sterile cloth wraps to treat bleeding.", "item_type": ItemType.CONSUMABLE, "value": 8, "weight": 0.2, "restore_hp": 25},
            "base_rusty_sword": {"name": "Rusty Sword", "description": "An old sword, heavily rusted.", "item_type": ItemType.WEAPON, "value": 10, "weight": 3.0, "equip_slot": "weapon", "stat_bonuses": {"strength": 2}, "durability": 10, "max_durability": 100},
            "base_torn_tunic": {"name": "Torn Tunic", "description": "A moth-eaten cloth tunic.", "item_type": ItemType.ARMOR, "value": 5, "weight": 1.0, "equip_slot": "armor", "stat_bonuses": {"defense": 1}, "durability": 15, "max_durability": 100},
            "base_leather_armor": {"name": "Worn Leather Armor", "description": "A stiff leather chestpiece.", "item_type": ItemType.ARMOR, "value": 30, "weight": 4.0, "equip_slot": "armor", "stat_bonuses": {"defense": 2}, "durability": 20, "max_durability": 100},
            "base_cracked_shield": {"name": "Cracked Wooden Shield", "description": "A wooden board that barely resembles a shield.", "item_type": ItemType.ARMOR, "value": 15, "weight": 2.5, "equip_slot": "armor", "stat_bonuses": {"defense": 1}, "durability": 8, "max_durability": 100},
            "base_iron_sword": {"name": "Iron Sword", "description": "A lethal sharpened blade forged of solid iron.", "item_type": ItemType.WEAPON, "value": 60, "weight": 3.5, "equip_slot": "weapon", "stat_bonuses": {"strength": 12}, "durability": 100, "max_durability": 100},
            "base_abyssal_core": {"name": "Abyssal Core", "description": "A glowing dark core.", "item_type": ItemType.MATERIAL, "value": 500, "weight": 1.0},
            "base_wild_apple": {"name": "Wild Apple", "description": "A crunchy wild apple.", "item_type": ItemType.CONSUMABLE, "value": 3, "weight": 0.2, "restore_hunger": 15, "restore_hp_pct": 0.15, "restore_thirst": 5}
        }

        log_lines = []
        for item_id in drops:
            template = self.repo.get_item_by_name(item_id) if hasattr(self.repo, "get_item_by_name") else None
            if template:
                new_item = Item(**template.model_dump())
            elif item_id in FALLBACK_ITEMS:
                new_item = Item(**FALLBACK_ITEMS[item_id])
            else:
                continue
            new_item.id = str(uuid.uuid4())
            location.add_item(new_item)
            log_lines.append(f"\n{enemy.name} dropped {new_item.name}!")
            
        return "".join(log_lines)

