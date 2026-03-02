from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel, Field
from enum import Enum

class ItemType(str, Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    TOOL = "tool"
    OTHER = "other"

class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    item_type: ItemType
    value: int = 0
    weight: float = 0.0
    durability: Optional[int] = None
    max_durability: Optional[int] = None
    equip_slot: Optional[str] = None # e.g., "weapon", "armor"
    restore_hp: int = 0
    restore_hp_pct: float = 0.0 # e.g., 0.1 for 10%
    restore_mp: int = 0
    restore_mp_pct: float = 0.0
    restore_hunger: int = 0
    restore_thirst: int = 0
    stat_bonuses: Dict[str, int] = Field(default_factory=dict) # e.g., {"strength": 5}
    effects: List[Dict[str, Any]] = Field(default_factory=list) # e.g., [{"type": "heal", "amount": 20}]
    is_dropped: bool = False
    is_light_source: bool = False
