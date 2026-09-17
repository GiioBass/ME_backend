from typing import Tuple, List, Dict, Optional, Any
import json
import os
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.domain.npc import NPC, DialogueNode, DialogueChoice, ShopItem
from app.core.domain.item import Item
from app.core.use_cases.services.base_service import BaseGameService
import uuid

class DialogueService(BaseGameService):
    def __init__(self, repository, world_gen=None, dungeon_gen=None, game_settings=None, quest_service=None):
        super().__init__(repository, world_gen, dungeon_gen, game_settings)
        self.quest_service = quest_service
        self.npcs: Dict[str, NPC] = {}
        self._load_npcs()

    def _load_npcs(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data"))
        file_path = os.path.join(base_dir, "npcs.json")
        if not os.path.exists(file_path):
            file_path = "data/npcs.json"
        if not os.path.exists(file_path):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                nodes_dict = {}
                for nid, ndata in item.get("dialogue_nodes", {}).items():
                    choices = [DialogueChoice(**c) for c in ndata.get("choices", [])]
                    nodes_dict[nid] = DialogueNode(id=ndata["id"], text=ndata["text"], choices=choices)
                
                shop_items = [ShopItem(**s) for s in item.get("shop_inventory", [])]
                
                npc = NPC(
                    id=item["id"],
                    name=item["name"],
                    title=item.get("title"),
                    description=item["description"],
                    location_id=item.get("location_id"),
                    npc_type=item.get("npc_type", "villager"),
                    is_hostile=item.get("is_hostile", False),
                    dialogue_root_node_id=item.get("dialogue_root_node_id", "root"),
                    dialogue_nodes=nodes_dict,
                    shop_inventory=shop_items
                )
                self.npcs[npc.name.lower()] = npc
                self.npcs[npc.id.lower()] = npc

    def get_npcs_in_location(self, location_id: str) -> List[NPC]:
        matched = []
        for npc in self.npcs.values():
            if npc.location_id == location_id:
                if npc not in matched:
                    matched.append(npc)
        return matched

    def talk_to_npc(self, player_id: str, npc_name_or_id: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not npc_name_or_id:
            return "Talk to whom?", player, location

        query = npc_name_or_id.lower()
        npc = self.npcs.get(query)
        if not npc:
            # Try fuzzy match
            npc = next((n for n in self.npcs.values() if query in n.name.lower() or query in n.id.lower()), None)
            
        if not npc or (npc.location_id and npc.location_id != location.id):
            return f"There is no one named '{npc_name_or_id}' here to talk to.", player, location

        # Start conversation at root node
        root_node = npc.dialogue_nodes.get(npc.dialogue_root_node_id)
        if not root_node:
            return f"{npc.name} has nothing to say right now.", player, location

        player.active_dialogue = {
            "npc_id": npc.id,
            "npc_name": npc.name,
            "node_id": root_node.id
        }
        self.repo.save_player(player)

        response_lines = [f"[{npc.name}] \"{root_node.text}\"\n"]
        response_lines.append("Dialogue Options:")
        for idx, choice in enumerate(root_node.choices, 1):
            response_lines.append(f" {idx}. {choice.text}")

        return "\n".join(response_lines), player, location

    def choose_dialogue_option(self, player_id: str, choice_input: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not player.active_dialogue:
            return "You are not currently in a conversation with anyone.", player, location

        npc_id = player.active_dialogue.get("npc_id")
        npc = self.npcs.get(npc_id.lower())
        if not npc:
            player.active_dialogue = None
            self.repo.save_player(player)
            return "The conversation ended.", player, location

        curr_node_id = player.active_dialogue.get("node_id")
        current_node = npc.dialogue_nodes.get(curr_node_id)
        if not current_node or not current_node.choices:
            player.active_dialogue = None
            self.repo.save_player(player)
            return "The conversation ended.", player, location

        # Match choice by index (1, 2, 3...) or partial text
        selected_choice: Optional[DialogueChoice] = None
        if choice_input.strip().isdigit():
            choice_idx = int(choice_input.strip()) - 1
            if 0 <= choice_idx < len(current_node.choices):
                selected_choice = current_node.choices[choice_idx]
        else:
            q = choice_input.lower()
            selected_choice = next((c for c in current_node.choices if q in c.text.lower() or q in c.choice_id.lower()), None)

        if not selected_choice:
            return f"Invalid option. Please choose a valid number (1-{len(current_node.choices)}) or choice text.", player, location

        # Check stat requirements
        if selected_choice.required_stat:
            for stat_name, min_val in selected_choice.required_stat.items():
                player_stat = getattr(player.stats, stat_name, 0)
                if player_stat < min_val:
                    return f"You lack the required {stat_name.title()} ({player_stat}/{min_val}) for that option.", player, location

        # Check gold cost
        if selected_choice.cost_gold and selected_choice.cost_gold > 0:
            if player.stats.gold < selected_choice.cost_gold:
                return f"You do not have enough gold ({player.stats.gold}/{selected_choice.cost_gold} Gold).", player, location
            player.stats.gold -= selected_choice.cost_gold

        action_msg = ""
        # Process action
        if selected_choice.action:
            action_parts = selected_choice.action.split(":")
            action_type = action_parts[0]
            if action_type == "open_shop":
                action_msg = f"\n\n[SHOP] {self._render_shop(npc)}"
            elif action_type == "give_quest" and len(action_parts) > 1:
                quest_id = action_parts[1]
                if self.quest_service:
                    q_msg = self.quest_service.accept_quest(player, quest_id)
                    action_msg = f"\n\n[QUEST ACCEPTED] {q_msg}"

        # Advance to next node or exit conversation
        if not selected_choice.next_node_id or selected_choice.next_node_id not in npc.dialogue_nodes:
            player.active_dialogue = None
            self.repo.save_player(player)
            return f"[{npc.name}] Farewell.{action_msg}", player, location

        next_node = npc.dialogue_nodes[selected_choice.next_node_id]
        player.active_dialogue["node_id"] = next_node.id
        self.repo.save_player(player)

        response_lines = [f"[{npc.name}] \"{next_node.text}\""]
        if next_node.choices:
            response_lines.append("\nDialogue Options:")
            for idx, choice in enumerate(next_node.choices, 1):
                response_lines.append(f" {idx}. {choice.text}")
        else:
            player.active_dialogue = None
            self.repo.save_player(player)
            
        if action_msg:
            response_lines.append(action_msg)

        return "\n".join(response_lines), player, location

    def _render_shop(self, npc: NPC) -> str:
        if not npc.shop_inventory:
            return f"{npc.name} has no items for sale."
        lines = [f"--- {npc.name}'s Shop ---"]
        for item in npc.shop_inventory:
            lines.append(f"- {item.item_name}: Buy {item.buy_price}g | Sell {item.sell_price}g")
        lines.append("\nUse 'buy [item]' or 'sell [item]'.")
        return "\n".join(lines)

    def buy_item(self, player_id: str, item_name: str, npc_name_or_id: Optional[str] = None) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not item_name:
            return "Buy what?", player, location

        # Locate merchant in location
        npcs = self.get_npcs_in_location(location.id)
        merchant = next((n for n in npcs if n.npc_type == "merchant" or n.shop_inventory), None)
        if not merchant:
            return "There is no merchant here to buy from.", player, location

        shop_entry = next((s for s in merchant.shop_inventory if s.item_name.lower() == item_name.lower()), None)
        if not shop_entry:
            return f"{merchant.name} does not sell '{item_name}'.", player, location

        if player.stats.gold < shop_entry.buy_price:
            return f"You do not have enough gold. Requires {shop_entry.buy_price}g (You have {player.stats.gold}g).", player, location

        # Create item from registry template
        template = self.repo.get_item_by_name(shop_entry.item_name)
        if not template:
            # Generic fallback
            from app.core.domain.item import ItemType
            template = Item(
                id=str(uuid.uuid4()),
                name=shop_entry.item_name,
                description=f"A purchased {shop_entry.item_name}.",
                item_type=ItemType.MATERIAL,
                value=shop_entry.sell_price,
                weight=1.0
            )
        else:
            template = Item(**template.model_dump())
            template.id = str(uuid.uuid4())

        if player.current_weight + template.weight > player.stats.max_weight:
            return f"You cannot carry {template.name}, your inventory is full.", player, location

        player.stats.gold -= shop_entry.buy_price
        player.add_item(template)
        self.repo.save_player(player)

        return f"You bought {template.name} for {shop_entry.buy_price} Gold. (Remaining Gold: {player.stats.gold}g)", player, location

    def sell_item(self, player_id: str, item_name: str) -> Tuple[str, Player, Location]:
        player, location = self._get_player_and_location(player_id)
        if not item_name:
            return "Sell what?", player, location

        npcs = self.get_npcs_in_location(location.id)
        merchant = next((n for n in npcs if n.npc_type == "merchant" or n.shop_inventory), None)
        if not merchant:
            return "There is no merchant here to sell items to.", player, location

        found_item = player.remove_item(item_name)
        if not found_item:
            return f"You don't have '{item_name}' in your inventory.", player, location

        shop_entry = next((s for s in merchant.shop_inventory if s.item_name.lower() == found_item.name.lower()), None)
        sell_price = shop_entry.sell_price if shop_entry else max(1, found_item.value // 2)

        player.stats.gold += sell_price
        self.repo.save_player(player)

        return f"You sold {found_item.name} to {merchant.name} for {sell_price} Gold. (Current Gold: {player.stats.gold}g)", player, location
