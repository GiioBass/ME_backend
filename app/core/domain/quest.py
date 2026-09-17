from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class ObjectiveType(str, Enum):
    KILL = "kill"
    GATHER = "gather"
    DISCOVER = "discover"
    CRAFT = "craft"
    TALK = "talk"

class QuestObjective(BaseModel):
    id: str
    description: str
    objective_type: ObjectiveType
    target: str # enemy name, item name, location id or NPC name
    required_count: int = 1
    current_count: int = 0

    @property
    def is_completed(self) -> bool:
        return self.current_count >= self.required_count

class QuestReward(BaseModel):
    xp: int = 0
    gold: int = 0
    items: List[Dict[str, Any]] = [] # [{"name": "Torch", "qty": 1}]

class QuestStatus(str, Enum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class Quest(BaseModel):
    id: str
    title: str
    description: str
    is_main_quest: bool = False
    giver_npc_id: Optional[str] = None
    turn_in_npc_id: Optional[str] = None
    objectives: List[QuestObjective] = Field(default_factory=list)
    reward: QuestReward = Field(default_factory=QuestReward)
    status: QuestStatus = QuestStatus.NOT_STARTED

    @property
    def all_objectives_completed(self) -> bool:
        return all(obj.is_completed for obj in self.objectives)
