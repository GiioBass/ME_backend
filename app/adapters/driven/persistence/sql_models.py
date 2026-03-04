from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON
from app.core.domain.player import Player, Stats
from app.core.domain.location import Location, Coordinates
from app.core.domain.item import Item, ItemType
from app.core.domain.enemy import Enemy
import uuid

# --- Shared Item Model ---
class ItemDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: str
    item_type: str
    value: int = 0
    weight: float = 0.0
    durability: Optional[int] = None
    max_durability: Optional[int] = None
    equip_slot: Optional[str] = None
    restore_hp: int = 0
    restore_hp_pct: float = 0.0
    restore_mp: int = 0
    restore_mp_pct: float = 0.0
    restore_hunger: int = 0
    restore_thirst: int = 0
    is_dropped: bool = False
    is_light_source: bool = False
    
    stat_bonuses: Dict[str, int] = Field(default={}, sa_type=JSON)
    effects: List[Dict[str, Any]] = Field(default=[], sa_type=JSON)

    def to_domain(self) -> Item:
        return Item(**self.model_dump())

    @classmethod
    def from_domain(cls, item: Item) -> "ItemDB":
        return cls(**item.model_dump())

# --- Player Related Models ---

class PlayerStatsDB(SQLModel, table=True):
    player_id: str = Field(primary_key=True, foreign_key="playerdb.id")
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    hunger: int = 100
    thirst: int = 100
    strength: int = 10
    agility: int = 10
    intelligence: int = 10
    level: int = 1
    xp: int = 0
    max_weight: float = 50.0

class InventoryItemDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: str = Field(foreign_key="playerdb.id", index=True)
    item_id: str = Field(foreign_key="itemdb.id")
    quantity: int = 1

class EquipmentDB(SQLModel, table=True):
    player_id: str = Field(primary_key=True, foreign_key="playerdb.id")
    weapon_id: Optional[str] = Field(default=None, foreign_key="itemdb.id")
    armor_id: Optional[str] = Field(default=None, foreign_key="itemdb.id")

class WaypointDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: str = Field(foreign_key="playerdb.id", index=True)
    name: str
    location_id: str

class PlayerDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str = Field(index=True, unique=True)
    current_location_id: str

# --- Location Related Models ---

class LocationDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: str
    x: int = Field(index=True)
    y: int = Field(index=True)
    z: int = Field(index=True)
    is_dark: bool = False
    trap_damage: int = 0

class LocationExitDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location_id: str = Field(foreign_key="locationdb.id", index=True)
    direction: str
    destination_id: str

class LocationInteractableDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location_id: str = Field(foreign_key="locationdb.id", index=True)
    name: str

class LocationItemDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location_id: str = Field(foreign_key="locationdb.id", index=True)
    item_id: str = Field(foreign_key="itemdb.id")
    is_camp_storage: bool = False

class EnemyDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: str
    hp: int
    max_hp: int
    attack: int
    xp_reward: int
    is_dead: bool = False
    is_boss: bool = False
    level: int = 1
    loot: List[dict] = Field(default=[], sa_type=JSON)

class LocationEnemyDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location_id: str = Field(foreign_key="locationdb.id", index=True)
    enemy_id: str = Field(foreign_key="enemydb.id")

# --- World State ---
class WorldStateDB(SQLModel, table=True):
    id: str = Field(primary_key=True, default="world_state")
    total_ticks: int = 0

# --- Command Help ---
class CommandHelpDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    command: str = Field(index=True, unique=True)
    alias: Optional[str] = None
    description: str
    usage: str
    category: str = "general" # e.g., "movement", "combat", "inventory", "special"

# --- Recipes ---
class RecipeDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str
    ingredients: Dict[str, int] = Field(default={}, sa_type=JSON) # itemName : quantity
    result_item_id: str = Field(foreign_key="itemdb.id")
    result_qty: int = 1
    category: str = "general"

    def to_domain(self, result_item: Optional[Item] = None) -> "Recipe":
        from app.core.domain.recipe import Recipe
        return Recipe(
            id=self.id,
            name=self.name,
            description=self.description,
            ingredients=self.ingredients,
            result_item_id=self.result_item_id,
            result_qty=self.result_qty,
            category=self.category,
            result_template=result_item
        )
    
    @classmethod
    def from_domain(cls, recipe: "Recipe") -> "RecipeDB":
        return cls(
            id=recipe.id,
            name=recipe.name,
            description=recipe.description,
            ingredients=recipe.ingredients,
            result_item_id=recipe.result_item_id,
            result_qty=recipe.result_qty,
            category=recipe.category
        )
