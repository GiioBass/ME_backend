from typing import List, Optional, Dict
import uuid
from pydantic import BaseModel, Field

class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    item_type: str  # weapon, armor, potion, tool, material
    value: int = 0
    equip_slot: Optional[str] = None # e.g., "weapon", "armor"
    stat_bonuses: Dict[str, int] = Field(default_factory=dict) # e.g., {"strength": 5}
