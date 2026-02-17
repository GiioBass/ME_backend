from typing import List, Dict, Optional
import uuid
from pydantic import BaseModel, Field
from app.core.domain.item import Item

class Coordinates(BaseModel):
    x: int
    y: int
    z: int = 0  # 0 for surface, <0 for dungeons

class Location(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    exits: Dict[str, str] = {}  # direction -> location_id interaction
    interactables: List[str] = [] # List of interactable object names not picked up
    items: List[Item] = []
    coordinates: Optional[Coordinates] = None
