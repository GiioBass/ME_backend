from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class DialogueChoice(BaseModel):
    choice_id: str
    text: str
    next_node_id: Optional[str] = None
    action: Optional[str] = None # e.g. "open_shop", "give_quest:the_awakening", "start_combat", "give_reward"
    required_stat: Optional[Dict[str, int]] = None # e.g. {"strength": 15}
    cost_gold: Optional[int] = None

class DialogueNode(BaseModel):
    id: str
    text: str
    choices: List[DialogueChoice] = []

class ShopItem(BaseModel):
    item_name: str
    buy_price: int
    sell_price: int
    stock: int = -1 # -1 for infinite

class NPC(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    description: str
    location_id: Optional[str] = None
    npc_type: str = "villager" # villager, merchant, quest_giver, bandit
    is_hostile: bool = False
    dialogue_root_node_id: str = "root"
    dialogue_nodes: Dict[str, DialogueNode] = Field(default_factory=dict)
    shop_inventory: List[ShopItem] = Field(default_factory=list)
