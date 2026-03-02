import json
import os
import uuid
from typing import List, Dict, Optional
from pydantic import BaseModel
from app.core.domain.enemy import Enemy
from app.core.domain.item import Item, ItemType

class BlueprintEnemyDef(BaseModel):
    name: str
    hp: int
    attack: int
    xp_reward: int

class BlueprintItemDef(BaseModel):
    name: str
    description: str
    type: str
    weight: float
    value: int = 0

class POIBlueprint(BaseModel):
    id: str
    name: str
    description: str
    allowed_biomes: List[str]
    guaranteed_enemies: List[BlueprintEnemyDef] = []
    guaranteed_items: List[BlueprintItemDef] = []

    def create_enemies(self) -> List[Enemy]:
        enemies = []
        for e_def in self.guaranteed_enemies:
            enemies.append(Enemy(
                id=str(uuid.uuid4()),
                name=e_def.name,
                description=f"A hostile {e_def.name}.",
                hp=e_def.hp,
                max_hp=e_def.hp,
                attack=e_def.attack,
                xp_reward=e_def.xp_reward
            ))
        return enemies

    def create_items(self) -> List[Item]:
        items = []
        for i_def in self.guaranteed_items:
            try:
                i_type = ItemType(i_def.type) # e.g. "MATERIAL" -> ItemType.MATERIAL
            except ValueError:
                i_type = ItemType.MATERIAL
                
            items.append(Item(
                id=str(uuid.uuid4()),
                name=i_def.name,
                description=i_def.description,
                item_type=i_type,
                weight=i_def.weight,
                value=i_def.value
            ))
        return items

class BlueprintLoader:
    def __init__(self, file_path: str = "app/data/blueprints.json"):
        self.file_path = file_path
        self.blueprints: List[POIBlueprint] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            return
            
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                bp = POIBlueprint(**item)
                self.blueprints.append(bp)

    def get_blueprints_for_biome(self, biome: str) -> List[POIBlueprint]:
        return [bp for bp in self.blueprints if biome in bp.allowed_biomes]
