from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class CharacterClass(str, Enum):
    ADVENTURER = "adventurer"
    FIGHTER = "fighter"
    MARKSMAN = "marksman"
    MAGE = "mage"

class SkillType(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"

class Skill(BaseModel):
    id: str
    name: str
    description: str
    character_class: CharacterClass
    skill_type: SkillType
    required_level: int = 1
    mp_cost: int = 0
    energy_cost: int = 0
    cooldown_turns: int = 0
    damage_multiplier: float = 1.0 # Multiplier over basic attack
    bonus_damage: int = 0
    effect_type: Optional[str] = None # stun, shield, dot, aoe, buff_strength
    effect_duration: int = 0
    effect_value: int = 0
