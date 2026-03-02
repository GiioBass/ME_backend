from typing import List, Dict, Optional, Any
import uuid
from pydantic import BaseModel, Field
from app.core.domain.item import Item
from app.core.domain.enemy import Enemy

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
    camp_storage: List[Item] = []
    coordinates: Optional[Coordinates] = None
    is_dark: bool = False
    trap_damage: int = 0

    def add_item(self, item: Item):
        self.items.append(item)
    
    def remove_item(self, item_id: str) -> Optional[Item]:
        for i, item in enumerate(self.items):
            if item.id == item_id or item.name.lower() == item_id.lower():
                return self.items.pop(i)
        return None

    def store_camp_item(self, item: Item):
        self.camp_storage.append(item)
        
    def retrieve_camp_item(self, item_name: str) -> Optional[Item]:
        for i, item in enumerate(self.camp_storage):
            if item.id == item_name or item.name.lower() == item_name.lower():
                return self.camp_storage.pop(i)
        return None

    # Forward reference handled by not typing explicitly or using string
    enemies: List['Enemy'] = [] 

    def add_enemy(self, enemy):
        self.enemies.append(enemy)

    def remove_enemy(self, enemy_id: str):
        for i, enemy in enumerate(self.enemies):
            if enemy.id == enemy_id or enemy.name.lower() == enemy_id.lower():
                return self.enemies.pop(i)
        return None
    
    def get_enemy(self, enemy_name: str):
        for enemy in self.enemies:
            if enemy.name.lower() == enemy_name.lower():
                return enemy
        return None
