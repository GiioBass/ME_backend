from typing import Tuple, List, Dict, Optional, Any
import json
import os
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.domain.skill import Skill, CharacterClass, SkillType
from app.core.config import settings
from app.core.use_cases.services.base_service import BaseGameService

class SkillService(BaseGameService):
    def __init__(self, repository, world_gen=None, dungeon_gen=None, game_settings=None, combat_service=None, quest_service=None):
        super().__init__(repository, world_gen, dungeon_gen, game_settings)
        self.combat_service = combat_service
        self.quest_service = quest_service
        self.skills_registry: Dict[str, Skill] = {}
        self._load_skills()

    def _load_skills(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data"))
        file_path = os.path.join(base_dir, "skills.json")
        if not os.path.exists(file_path):
            file_path = "data/skills.json"
        if not os.path.exists(file_path):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for s_data in data:
                skill = Skill(
                    id=s_data["id"],
                    name=s_data["name"],
                    description=s_data["description"],
                    character_class=CharacterClass(s_data.get("character_class", "adventurer")),
                    skill_type=SkillType(s_data.get("skill_type", "active")),
                    required_level=s_data.get("required_level", 1),
                    mp_cost=s_data.get("mp_cost", 0),
                    energy_cost=s_data.get("energy_cost", 0),
                    cooldown_turns=s_data.get("cooldown_turns", 0),
                    damage_multiplier=s_data.get("damage_multiplier", 1.0),
                    bonus_damage=s_data.get("bonus_damage", 0),
                    effect_type=s_data.get("effect_type"),
                    effect_duration=s_data.get("effect_duration", 0),
                    effect_value=s_data.get("effect_value", 0)
                )
                self.skills_registry[skill.id.lower()] = skill
                self.skills_registry[skill.name.lower()] = skill

    def select_class(self, player_id: str, class_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        class_name_clean = class_name.lower().strip()
        
        valid_classes = {
            "adventurer": CharacterClass.ADVENTURER,
            "fighter": CharacterClass.FIGHTER,
            "marksman": CharacterClass.MARKSMAN,
            "mage": CharacterClass.MAGE
        }
        if class_name_clean not in valid_classes:
            return f"Invalid class '{class_name}'. Choose from: Fighter, Marksman, Mage, Adventurer.", player, location

        chosen = valid_classes[class_name_clean]
        current_class = getattr(player.stats, 'character_class', 'adventurer')
        if current_class and current_class != "adventurer" and current_class != chosen.value:
            return f"Your class is permanently set to {current_class.capitalize()}. Classes cannot be changed after character creation.", player, location

        player.stats.character_class = chosen.value

        # Grant class starter skills
        class_skills = [
            s.name for s in self.skills_registry.values() 
            if s.character_class == chosen and s.required_level <= player.stats.level
        ]
        player.skills = list(set(player.skills + class_skills))

        # Adjust initial base stats based on class archetype
        if chosen == CharacterClass.FIGHTER:
            player.stats.max_hp += 20
            player.stats.hp = player.stats.max_hp
            player.stats.strength += 4
        elif chosen == CharacterClass.MAGE:
            player.stats.max_mp += 40
            player.stats.mp = player.stats.max_mp
            player.stats.intelligence += 6
        elif chosen == CharacterClass.MARKSMAN:
            player.stats.agility += 5
            player.stats.strength += 2

        self.repo.save_player(player)
        return f"*** You are now a {chosen.value.title()}! ***\nUnlocked skills: {', '.join(class_skills)}", player, location

    def list_skills(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not player.skills:
            return f"Class: {player.stats.character_class.title()}\nYou have not learned any special skills yet. Choose a class or level up!", player, location

        lines = [f"=== SKILLS & ABILITIES ({player.stats.character_class.title()}) ==="]
        for s_name in player.skills:
            skill = self.skills_registry.get(s_name.lower())
            if skill:
                cost_str = ""
                if skill.mp_cost > 0: cost_str += f" | {skill.mp_cost} MP"
                if skill.energy_cost > 0: cost_str += f" | {skill.energy_cost} Energy"
                lines.append(f"• {skill.name} (Lvl {skill.required_level}{cost_str}): {skill.description}")
            else:
                lines.append(f"• {s_name}")

        return "\n".join(lines), player, location

    def use_skill(self, player_id: str, skill_name: str, target_name: Optional[str] = None) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        world_time = self.repo.get_world_time()

        if not skill_name:
            return "Use which skill? (e.g., 'skill Heavy Strike [target]')", player, location

        skill = self.skills_registry.get(skill_name.lower())
        if not skill:
            return f"Skill '{skill_name}' not found.", player, location

        # Auto-grant skill if valid for player class and level
        cls_val = getattr(player.stats, 'character_class', 'adventurer')
        is_class_skill = (skill.character_class.value == cls_val or skill.character_class.value == 'adventurer')
        if is_class_skill and player.stats.level >= skill.required_level:
            if skill.name not in player.skills and skill.id not in player.skills:
                player.skills.append(skill.name)
                self.repo.save_player(player)

        if skill.name not in player.skills and skill.id not in player.skills:
            return f"You have not unlocked the skill '{skill.name}'.", player, location

        # Check skill cooldown / alternation requirement
        skill_cd = player.skill_cooldowns.get(skill.name.lower(), 0) or player.skill_cooldowns.get(skill.id.lower(), 0)
        if skill_cd > 0:
            return f"Skill '{skill.name}' is on cooldown! Strike with a basic attack ('attack [target]') to regain your tactical stance and recharge.", player, location

        # Check MP cost
        if skill.mp_cost > 0 and player.stats.mp < skill.mp_cost:
            return f"Not enough Mana! Requires {skill.mp_cost} MP (You have {player.stats.mp}/{player.stats.max_mp} MP).", player, location

        # Check HP/Energy cost
        if skill.energy_cost > 0 and player.stats.hp <= skill.energy_cost:
            return f"You are too exhausted to use {skill.name}!", player, location

        # Target enemy check
        enemy = None
        if target_name:
            enemy = location.get_enemy(target_name)
        elif location.enemies:
            # Pick first alive enemy
            enemy = next((e for e in location.enemies if not getattr(e, "is_dead", False)), None)

        if not enemy and skill.damage_multiplier > 0:
            return f"There are no hostile enemies here to target with {skill.name}.", player, location

        # Deduct costs
        if skill.mp_cost > 0:
            player.stats.mp = max(0, player.stats.mp - skill.mp_cost)
        if skill.energy_cost > 0:
            player.take_damage(skill.energy_cost)

        # Set cooldown for free skill or skill with cooldown_turns
        if skill.mp_cost == 0 or getattr(skill, "cooldown_turns", 0) > 0:
            cd_val = getattr(skill, "cooldown_turns", 0) if getattr(skill, "cooldown_turns", 0) > 0 else 1
            player.skill_cooldowns[skill.name.lower()] = cd_val
            player.skill_cooldowns[skill.id.lower()] = cd_val

        combat_log = f"You cast [{skill.name}]!"
        if skill.mp_cost > 0:
            combat_log += f" (-{skill.mp_cost} MP)"

        # Apply damage to enemy
        if enemy:
            if skill.character_class == CharacterClass.MAGE:
                base_attr = player.stats.intelligence
            else:
                base_attr = player.stats.strength

            weapon = player.equipment.get("weapon")
            weapon_bonus = 0
            if weapon:
                if skill.character_class == CharacterClass.MAGE and "intelligence" in weapon.stat_bonuses:
                    weapon_bonus = weapon.stat_bonuses["intelligence"]
                elif "strength" in weapon.stat_bonuses:
                    weapon_bonus = weapon.stat_bonuses["strength"]

            base_power = max(1, (base_attr // 2)) + weapon_bonus
            dmg = max(1, int(base_power * skill.damage_multiplier))
            actual_dmg = enemy.take_damage(dmg)
            combat_log += f" Dealt {actual_dmg} damage to {enemy.name}! (Enemy HP: {enemy.hp}/{enemy.max_hp})"

            if enemy.is_dead:
                combat_log += f"\n{enemy.name} was obliterated by your skill!"
                location.remove_enemy(enemy.id)
                player.gain_xp(enemy.xp_reward)
                combat_log += f"\nYou gain {enemy.xp_reward} XP."
                
                # Update quest kill objective
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

        # Apply self buffs/shields/heals
        if skill.effect_type == "shield":
            player.stats.hp = min(player.stats.max_hp, player.stats.hp + skill.effect_value)
            combat_log += f" Absorbed energy, granting +{skill.effect_value} temporary vitality!"
        elif skill.effect_type == "heal":
            old_hp = player.stats.hp
            player.stats.hp = min(player.stats.max_hp, player.stats.hp + skill.effect_value)
            healed = player.stats.hp - old_hp
            combat_log += f" Restored +{healed} HP! ({player.stats.hp}/{player.stats.max_hp} HP)"

        # Enemy retaliation if alive (unless stunned by skill)
        if enemy and not enemy.is_dead:
            if skill.effect_type == "stun":
                combat_log += f"\n{enemy.name} is stunned by the impact and cannot retaliate!"
            else:
                enemy_dmg = max(1, enemy.attack)
                armor = player.equipment.get("armor")
                mitigation = armor.stat_bonuses.get("defense", 0) if armor else 0
                final_dmg = max(1, enemy_dmg - mitigation)
                player.take_damage(final_dmg)
                combat_log += f"\n{enemy.name} retaliates for {final_dmg} damage! (Your HP: {player.stats.hp}/{player.stats.max_hp})"

        self.repo.save_player(player)
        self.repo.create_location(location)
        time_msg = self._advance_time_and_events(world_time, player, settings.TIME_COST_ATTACK)
        return combat_log + time_msg, player, location
