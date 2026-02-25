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
    equipment: Dict[str, Optional[Item]] = Field(default_factory=lambda: {"weapon": None, "armor": None})
    
    def equip(self, item: Item) -> str:
        if not item.equip_slot:
            return "You cannot equip that."
        
        # Take it out of inventory
        if not self.remove_item(item.id):
            return "Item not found in inventory."
            
        slot = item.equip_slot
        msg = f"You equipped the {item.name}."
        
        # If something was already equipped in that slot, put it back in the inventory
        if slot in self.equipment and self.equipment[slot] is not None:
            old_item = self.equipment[slot]
            self.add_item(old_item)
            msg += f" You unequal the {old_item.name}."
            
        self.equipment[slot] = item
        return msg

    def unequip(self, slot: str) -> str:
        if slot not in self.equipment or self.equipment[slot] is None:
            return "Nothing is equipped there."
            
        item = self.equipment[slot]
        self.equipment[slot] = None
        self.add_item(item)
        return f"You unequipped the {item.name}."
    def move(self, direction: str, location_exits: Dict[str, str]) -> Optional[str]:
        return location_exits.get(direction)

    def add_item(self, item: Item):
        self.inventory.append(item)
    
    def remove_item(self, item_id: str) -> Optional[Item]:
        for i, item in enumerate(self.inventory):
            if item.id == item_id or item.name.lower() == item_id.lower():
                return self.inventory.pop(i)
        return None
    
    def has_item(self, item_name: str) -> bool:
        return any(i.name.lower() == item_name.lower() for i in self.inventory)

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

    def take_damage(self, amount: int) -> int:
        self.stats.hp -= amount
        if self.stats.hp < 0:
            self.stats.hp = 0
        return amount

    def is_alive(self) -> bool:
        return self.stats.hp > 0
    
    def heal(self):
        self.stats.hp = self.stats.max_hp
