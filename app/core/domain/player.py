from typing import List, Dict, Optional
import uuid
from pydantic import BaseModel, Field
from app.core.domain.item import Item

class Stats(BaseModel):
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    strength: int = 10
    agility: int = 10
    intelligence: int = 10
    level: int = 1
    xp: int = 0

class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    stats: Stats = Field(default_factory=Stats)
    current_location_id: str
    inventory: List[Item] = []
    
    def move(self, direction: str, location_exits: Dict[str, str]) -> Optional[str]:
        return location_exits.get(direction)

    def gain_xp(self, amount: int):
        self.stats.xp += amount
        # Simple level up logic
        if self.stats.xp >= self.stats.level * 100:
            self.stats.level += 1
            self.stats.xp = 0
            self.stats.max_hp += 10
            self.stats.hp = self.stats.max_hp
            return True
        return False
