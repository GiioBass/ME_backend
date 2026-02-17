from typing import List, Optional
import uuid
from pydantic import BaseModel, Field

class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    item_type: str  # weapon, armor, potion, tool, material
    value: int = 0
