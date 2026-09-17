from typing import Tuple, List, Dict, Optional, Any
import json
import os
import uuid
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.domain.quest import Quest, QuestObjective, QuestReward, QuestStatus, ObjectiveType
from app.core.domain.item import Item, ItemType
from app.core.use_cases.services.base_service import BaseGameService

class QuestService(BaseGameService):
    def __init__(self, repository, world_gen=None, dungeon_gen=None, game_settings=None):
        super().__init__(repository, world_gen, dungeon_gen, game_settings)
        self.quest_registry: Dict[str, Quest] = {}
        self._load_quests()

    def _load_quests(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data"))
        file_path = os.path.join(base_dir, "quests.json")
        if not os.path.exists(file_path):
            file_path = "data/quests.json"
        if not os.path.exists(file_path):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for q_data in data:
                objectives = [QuestObjective(**obj) for obj in q_data.get("objectives", [])]
                reward = QuestReward(**q_data.get("reward", {}))
                quest = Quest(
                    id=q_data["id"],
                    title=q_data["title"],
                    description=q_data["description"],
                    is_main_quest=q_data.get("is_main_quest", False),
                    giver_npc_id=q_data.get("giver_npc_id"),
                    turn_in_npc_id=q_data.get("turn_in_npc_id"),
                    objectives=objectives,
                    reward=reward,
                    status=QuestStatus(q_data.get("status", "not_started"))
                )
                self.quest_registry[quest.id] = quest

    def get_quest_template(self, quest_id: str) -> Optional[Quest]:
        return self.quest_registry.get(quest_id)

    def accept_quest(self, player: Player, quest_id: str) -> str:
        if quest_id in player.completed_quests:
            return f"You have already completed this quest."
        if quest_id in player.active_quests:
            return f"You are already pursuing this quest."

        template = self.get_quest_template(quest_id)
        if not template:
            return f"Quest '{quest_id}' not found."

        # Instantiate fresh copy for player
        quest_inst = template.model_copy(deep=True)
        quest_inst.status = QuestStatus.ACTIVE
        
        # Check initial progress against player inventory for gather objectives
        for obj in quest_inst.objectives:
            if obj.objective_type == ObjectiveType.GATHER:
                count = sum(1 for item in player.inventory if item.name.lower() == obj.target.lower())
                obj.current_count = min(obj.required_count, count)

        player.active_quests[quest_id] = quest_inst.model_dump()
        self.repo.save_player(player)
        return f"Accepted Quest: {quest_inst.title} - {quest_inst.description}"

    def update_kill_progress(self, player: Player, enemy_name: str) -> str:
        notifications = []
        if not player.active_quests:
            return ""

        updated = False
        for q_id, q_data in player.active_quests.items():
            for obj_data in q_data.get("objectives", []):
                if obj_data.get("objective_type") == "kill":
                    target = obj_data.get("target", "").lower()
                    if target in enemy_name.lower() or enemy_name.lower() in target or target == "boss":
                        if obj_data["current_count"] < obj_data["required_count"]:
                            obj_data["current_count"] += 1
                            updated = True
                            notifications.append(
                                f"[QUEST] {q_data['title']}: {obj_data['description']} ({obj_data['current_count']}/{obj_data['required_count']})"
                            )
                            if obj_data["current_count"] >= obj_data["required_count"]:
                                notifications.append(f"[QUEST READY] {q_data['title']} is ready to turn in!")

        if updated:
            self.repo.save_player(player)
        return "\n" + "\n".join(notifications) if notifications else ""

    def update_craft_progress(self, player: Player, recipe_name: str) -> str:
        notifications = []
        if not player.active_quests:
            return ""

        updated = False
        for q_id, q_data in player.active_quests.items():
            for obj_data in q_data.get("objectives", []):
                if obj_data.get("objective_type") == "craft":
                    target = obj_data.get("target", "").lower()
                    if target in recipe_name.lower() or recipe_name.lower() in target:
                        if obj_data["current_count"] < obj_data["required_count"]:
                            obj_data["current_count"] += 1
                            updated = True
                            notifications.append(
                                f"[QUEST] {q_data['title']}: {obj_data['description']} ({obj_data['current_count']}/{obj_data['required_count']})"
                            )

        if updated:
            self.repo.save_player(player)
        return "\n" + "\n".join(notifications) if notifications else ""

    def update_gather_progress(self, player: Player, item_name: str) -> str:
        notifications = []
        if not player.active_quests:
            return ""

        updated = False
        for q_id, q_data in player.active_quests.items():
            for obj_data in q_data.get("objectives", []):
                if obj_data.get("objective_type") == "gather":
                    target = obj_data.get("target", "").lower()
                    if target in item_name.lower() or item_name.lower() in target:
                        # Count total items currently in inventory
                        total_inv = sum(1 for i in player.inventory if i.name.lower() == item_name.lower())
                        obj_data["current_count"] = min(obj_data["required_count"], total_inv)
                        updated = True
                        notifications.append(
                            f"[QUEST] {q_data['title']}: {obj_data['description']} ({obj_data['current_count']}/{obj_data['required_count']})"
                        )

        if updated:
            self.repo.save_player(player)
        return "\n" + "\n".join(notifications) if notifications else ""

    def turn_in_quest(self, player_id: str, quest_id_or_title: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not quest_id_or_title:
            return "Turn in which quest?", player, location

        q_key = None
        q_data = None
        for q_id, data in player.active_quests.items():
            if q_id.lower() == quest_id_or_title.lower() or data.get("title", "").lower() == quest_id_or_title.lower() or quest_id_or_title.lower() in q_id.lower():
                q_key = q_id
                q_data = data
                break

        if not q_key or not q_data:
            return f"You do not have active quest '{quest_id_or_title}'.", player, location

        # Check if all objectives are completed
        objectives = q_data.get("objectives", [])
        incomplete = [obj for obj in objectives if obj.get("current_count", 0) < obj.get("required_count", 1)]
        if incomplete:
            lines = [f"Quest '{q_data.get('title')}' is not yet completed:"]
            for obj in incomplete:
                lines.append(f"- {obj.get('description')} ({obj.get('current_count', 0)}/{obj.get('required_count', 1)})")
            return "\n".join(lines), player, location

        # Grant rewards
        reward = q_data.get("reward", {})
        xp = reward.get("xp", 0)
        gold = reward.get("gold", 0)
        items_given = []

        if xp > 0:
            player.gain_xp(xp)
        if gold > 0:
            player.stats.gold += gold

        for it in reward.get("items", []):
            it_name = it.get("name")
            qty = it.get("qty", 1)
            for _ in range(qty):
                template = self.repo.get_item_by_name(it_name)
                if template:
                    new_item = Item(**template.model_dump())
                    new_item.id = str(uuid.uuid4())
                else:
                    new_item = Item(
                        id=str(uuid.uuid4()),
                        name=it_name,
                        description=f"Quest reward: {it_name}",
                        item_type=ItemType.MATERIAL,
                        value=10,
                        weight=0.5
                    )
                player.add_item(new_item)
                items_given.append(new_item.name)

        # Move to completed
        del player.active_quests[q_key]
        player.completed_quests.append(q_key)
        self.repo.save_player(player)

        reward_summary = []
        if xp > 0: reward_summary.append(f"{xp} XP")
        if gold > 0: reward_summary.append(f"{gold} Gold")
        if items_given: reward_summary.append(f"Items: {', '.join(items_given)}")

        msg = f"*** QUEST COMPLETED: {q_data.get('title')} ***\nRewards received: {', '.join(reward_summary)}"
        return msg, player, location

    def list_player_quests(self, player_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not player.active_quests and not player.completed_quests:
            return "You have no active or completed quests.", player, location

        lines = ["=== QUEST LOG ==="]
        if player.active_quests:
            lines.append("\n[Active Quests]")
            for q_id, q_data in player.active_quests.items():
                lines.append(f"• {q_data.get('title')}: {q_data.get('description')}")
                for obj in q_data.get("objectives", []):
                    status_mark = "[✓]" if obj.get("current_count", 0) >= obj.get("required_count", 1) else "[ ]"
                    lines.append(f"   {status_mark} {obj.get('description')} ({obj.get('current_count', 0)}/{obj.get('required_count', 1)})")
        
        if player.completed_quests:
            lines.append("\n[Completed Quests]")
            for q_id in player.completed_quests:
                lines.append(f"• {q_id} [Completed]")

        return "\n".join(lines), player, location
