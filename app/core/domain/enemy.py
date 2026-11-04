import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class Enemy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    hp: int
    max_hp: int
    attack: int
    xp_reward: int
    is_dead: bool = False
    is_boss: bool = False
    level: int = 1
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    cooldowns: Dict[str, int] = Field(default_factory=dict)
    base_hp: Optional[int] = None
    base_attack: Optional[int] = None
    scaled_players_count: int = 1

    def take_damage(self, amount: int) -> int:
        """Takes damage and returns actual damage taken."""
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_dead = True
        return amount

    def heal(self, amount: int) -> int:
        """Heals HP up to max_hp."""
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp
