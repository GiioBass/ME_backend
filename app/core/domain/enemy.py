import uuid
from typing import Optional
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

    def take_damage(self, amount: int) -> int:
        """Takes damage and returns actual damage taken."""
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_dead = True
        return amount
