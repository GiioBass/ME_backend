from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
import uuid
from app.core.domain.item import Item

class Recipe(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    ingredients: Dict[str, int] # itemName: quantity
    result_item_id: str
    result_qty: int = 1
    category: str = "general"
    
    # We might want to store the item template too to be able to create it
    result_template: Optional[Item] = None
