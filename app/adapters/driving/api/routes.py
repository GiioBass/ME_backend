from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.use_cases.game_service import GameService
from app.ports.repositories import GameRepository

# DTOs
class CommandRequest(BaseModel):
    player_id: str
    command: str

class MoveRequest(BaseModel):
    player_id: str
    direction: str

class ItemRequest(BaseModel):
    player_id: str
    item_name: str

class SlotRequest(BaseModel):
    player_id: str
    slot: str

class AttackRequest(BaseModel):
    player_id: str
    target_name: str

class CampRequest(BaseModel):
    player_id: str
    camp_name: str

class TravelRequest(BaseModel):
    player_id: str
    waypoint_name: str

class PlayerIdRequest(BaseModel):
    player_id: str

class CraftRequest(BaseModel):
    player_id: str
    recipe_name: str

class TalkRequest(BaseModel):
    player_id: str
    npc_name: str

class DialogueRequest(BaseModel):
    player_id: str
    choice: str

class TradeRequest(BaseModel):
    player_id: str
    item_name: str

class QuestTurnInRequest(BaseModel):
    player_id: str
    quest_id: str

class ClassSelectRequest(BaseModel):
    player_id: str
    character_class: str

class SkillUseRequest(BaseModel):
    player_id: str
    skill_name: str
    target_name: Optional[str] = None

class CommandHelpResponse(BaseModel):
    command: str
    alias: Optional[str] = None
    description: str
    usage: str
    category: str

class GameResponse(BaseModel):
    message: str
    player: dict
    location: dict
    time: dict
    available_actions: list[str] = []
    scouted_locations: list | None = None

def get_game_service(repo: GameRepository) -> GameService:
    return GameService(repo)

def serialize_inventory(inventory_list) -> list:
    if not inventory_list:
        return []
        
    grouped = {}
    for item in inventory_list:
        name = item.get("name", "Unknown") if isinstance(item, dict) else (item.name if hasattr(item, "name") else "Unknown")
        if name not in grouped:
            grouped[name] = {"item": item, "qty": 0}
        grouped[name]["qty"] += 1
    
    new_inventory = []
    for name, group_data in grouped.items():
        item_data = group_data["item"]
        if isinstance(item_data, dict):
            serialized_item = item_data.copy()
        else:
            serialized_item = item_data.model_dump() if hasattr(item_data, "model_dump") else {"name": name}
            
        serialized_item["qty"] = group_data["qty"]
        
        # Add damage and shield stats for the frontend
        item_type_str = str(serialized_item.get("item_type", "")).lower()
        equip_slot = str(serialized_item.get("equip_slot", "")).lower()
        if "stat_bonuses" in serialized_item and serialized_item["stat_bonuses"]:
            if "weapon" in item_type_str or equip_slot == "weapon":
                serialized_item["damage"] = serialized_item["stat_bonuses"].get("strength", 0)
            if "armor" in item_type_str or equip_slot == "armor":
                serialized_item["shield"] = serialized_item["stat_bonuses"].get("defense", 0)
                
        new_inventory.append(serialized_item)
    return new_inventory

def serialize_player(player) -> dict:
    data = player.model_dump()
    data["current_weight"] = player.current_weight
    
    if "inventory" in data and data["inventory"]:
        data["inventory"] = serialize_inventory(data["inventory"])

    # Enrich active_dialogue with text and choices if active
    if data.get("active_dialogue"):
        try:
            dlg = data["active_dialogue"]
            npc_id = (dlg.get("npc_id") or "").lower()
            node_id = dlg.get("node_id")
            service = GameService(_repo)
            npc = service.dialogue_service.npcs.get(npc_id)
            if npc and node_id and node_id in npc.dialogue_nodes:
                node = npc.dialogue_nodes[node_id]
                dlg["text"] = node.text
                dlg["options"] = [
                    {"id": str(i + 1), "text": c.text, "choice_id": c.choice_id}
                    for i, c in enumerate(node.choices)
                ]
        except Exception:
            pass
        
    # Serialize equipment which might contain domain Items
    if "equipment" in data and data["equipment"]:
        eq_data = {}
        for slot, item in data["equipment"].items():
            if item is None:
                eq_data[slot] = None
                continue
                
            if isinstance(item, dict):
                serialized_item = item
            elif hasattr(item, "model_dump"):
                serialized_item = item.model_dump()
            else:
                serialized_item = {"name": str(item)}
                
            # Inject 'bonus' field for frontend display based on slot
            if slot == "weapon" and "stat_bonuses" in serialized_item:
                serialized_item["bonus"] = serialized_item["stat_bonuses"].get("strength", 0)
            elif slot == "armor" and "stat_bonuses" in serialized_item:
                serialized_item["bonus"] = serialized_item["stat_bonuses"].get("defense", 0)
                
            eq_data[slot] = serialized_item
            
        data["equipment"] = eq_data

    # Calculate Total Stats
    if "stats" in data:
        base_str = data["stats"].get("strength", 10)
        base_def = data["stats"].get("defense", 5) # Default defense
        
        bonus_str = 0
        bonus_def = 0
        
        eq = data.get("equipment", {})
        weapon = eq.get("weapon")
        if weapon and isinstance(weapon, dict):
            bonus_str += weapon.get("stat_bonuses", {}).get("strength", 0)
            
        armor = eq.get("armor")
        if armor and isinstance(armor, dict):
            bonus_def += armor.get("stat_bonuses", {}).get("defense", 0)
            
        data["stats"]["strength"] = base_str + bonus_str
        data["stats"]["base_strength"] = base_str
        # Frontend doesn't show defense yet, but good to have
        data["stats"]["defense"] = base_def + bonus_def
        data["stats"]["base_defense"] = base_def

    return data


def execute_game_action(service, func_name, *args):
    try:
        res = getattr(service, func_name)(*args)
        if isinstance(res, tuple) and len(res) == 4:
            msg, player, location, scouted = res
        elif isinstance(res, tuple) and len(res) == 3:
            msg, player, location = res
            scouted = None
        else:
            return res # fallback
            
        if not player.is_alive():
            player.heal()
            player.current_location_id = "loc_0_0_0"
            service.repo.save_player(player)
            location = service.repo.get_location("loc_0_0_0")
            if not location:
                location = service.world_gen.generate_start_location()
            msg += "\n\n*** YOU DIED ***\nYou succumbed to the elements and perished. You wake up at the start."
            
        world_time = service.repo.get_world_time()
        return format_response(msg, player, location, world_time, scouted)
    except ValueError as e:
        raise_game_error(e)

router = APIRouter()

from app.adapters.driven.persistence.sql_repository import SQLGameRepository
_repo = SQLGameRepository()

def serialize_time(world_time) -> dict:
    return {
        "total_ticks": world_time.total_ticks,
        "day": world_time.day,
        "hour": world_time.hour,
        "minute": world_time.minute,
        "is_night": world_time.is_night()
    }

def serialize_item(item) -> dict:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return {"name": str(item)}

def serialize_enemy(enemy) -> dict:
    if hasattr(enemy, "model_dump"):
        return enemy.model_dump()
    return {"name": str(enemy)}

def raise_game_error(e: ValueError):
    raise HTTPException(
        status_code=400, 
        detail={"error": True, "message": str(e), "code": "INVALID_ACTION"}
    )

def get_available_actions(player: dict, location: dict, world_time: dict) -> list[str]:
    actions = ["look", "inventory", "scout", "quests"]
    
    if player and player.get("skills"):
        actions.append("skills")

    # If currently in dialogue
    if player and player.get("active_dialogue"):
        actions.extend(["dialogue 1", "dialogue 2", "dialogue 3", "dialogue 4"])

    if location:
        if location.get("exits"):
            for direction in location["exits"].keys():
                actions.append(f"move {direction}")
        
        if world_time and world_time.get("is_night"):
            actions.append("sleep")

        # NPCs in location
        if location.get("id") == "loc_0_0_0":
            actions.extend(["talk Village Elder", "talk Merchant Silas", "talk Farmer Ted", "shop"])

        # Robust water detection: interactables OR location name
        has_water = any(str(inter).startswith("water_source:") for inter in location.get("interactables", []))
        if not has_water:
            loc_name = str(location.get("name", "")).lower()
            if any(w in loc_name for w in ["river", "lake", "stream", "well", "font", "source", "water"]):
                has_water = True

        if has_water:
            actions.append("drink")
            for item in player.get("inventory", []):
                item_name = (item.get("name", "") if isinstance(item, dict) else getattr(item, "name", "")).lower()
                if "empty" in item_name and ("flask" in item_name or "vessel" in item_name):
                    display_name = item.get("name") if isinstance(item, dict) else getattr(item, "name", "")
                    actions.append(f"fill {display_name}")

        if location.get("items"):
            for item in location["items"]:
                name = item.get("name") if isinstance(item, dict) else item
                actions.append(f"take {name}")
                
        if location.get("enemies"):
            for enemy in location["enemies"]:
                name = enemy.get("name") if isinstance(enemy, dict) else enemy
                actions.append(f"attack {name}")
                if player and player.get("skills"):
                    for sk in player["skills"]:
                        actions.append(f"skill {sk} {name}")
                
    if player:
        if player.get("inventory"):
            for item in player["inventory"]:
                name = item.get("name") if isinstance(item, dict) else getattr(item, "name", str(item))
                actions.append(f"drop {name}")
                
                item_type_str = str(item.get("item_type") if isinstance(item, dict) else getattr(item, "item_type", ""))
                is_consumable_type = item_type_str.endswith("consumable") or item_type_str.endswith("CONSUMABLE")
                has_restore_stats = False
                
                if isinstance(item, dict):
                    has_restore_stats = any(item.get(k, 0) > 0 for k in ["restore_hp", "restore_mp", "restore_hunger", "restore_thirst", "restore_hp_pct", "restore_mp_pct"])
                else:
                    has_restore_stats = any(getattr(item, k, 0) > 0 for k in ["restore_hp", "restore_mp", "restore_hunger", "restore_thirst", "restore_hp_pct", "restore_mp_pct"])
                
                if is_consumable_type or has_restore_stats:
                    actions.append(f"consume {name}")
                else:
                    actions.append(f"equip {name}")
                
        if player.get("equipment"):
            for slot, item in player["equipment"].items():
                if item:
                    actions.append(f"unequip {slot}")
        
        if player.get("waypoints"):
            for wp in player["waypoints"].keys():
                actions.append(f"travel {wp}")
                
        if location and location.get("id") in player.get("waypoints", {}).values():
            actions.append("chest")
            if player.get("inventory"):
                for item in player["inventory"]:
                    name = item.get("name") if isinstance(item, dict) else item
                    actions.append(f"store {name}")
            if location.get("camp_storage"):
                for item in location["camp_storage"]:
                    name = item.get("name") if isinstance(item, dict) else item
                    actions.append(f"retrieve {name}")
                    
    # Workstation & Crafting Checks
    loc_interactables = location.get("interactables", []) if location else []
    
    has_workbench = any("workbench" in str(inter).lower() for inter in loc_interactables)
    has_forge = any(any(k in str(inter).lower() for k in ["forge", "anvil"]) for inter in loc_interactables)
    has_alchemy = any("alchemy" in str(inter).lower() for inter in loc_interactables)
    has_campfire = any("campfire" in str(inter).lower() for inter in loc_interactables)
    has_any_station = has_workbench or has_forge or has_alchemy or has_campfire or any("station:" in str(inter).lower() or "workshop" in str(inter).lower() for inter in loc_interactables)

    if has_any_station:
        actions.append("workshop")

    # Only provide craft actions if the player is actually at a valid workstation
    recipes = _repo.get_recipes()
    if player and player.get("inventory") and has_any_station:
        from collections import Counter
        inv_counts = Counter(item.get("name") if isinstance(item, dict) else getattr(item, "name", "") for item in player["inventory"])
        
        for r in recipes:
            req_station = getattr(r, 'required_station', 'none').lower()
            station_ok = False
            if req_station in ["none", ""]:
                station_ok = True
            elif req_station == "workbench" and has_workbench:
                station_ok = True
            elif req_station in ["anvil", "forge"] and has_forge:
                station_ok = True
            elif req_station in ["alchemy_table", "alchemy"] and has_alchemy:
                station_ok = True
            elif req_station == "campfire" and has_campfire:
                station_ok = True
            elif any(req_station in str(inter).lower() for inter in loc_interactables):
                station_ok = True
                
            if station_ok:
                can_craft = True
                for ing_name, qty in r.ingredients.items():
                    if inv_counts[ing_name] < qty:
                        can_craft = False
                        break
                if can_craft:
                    actions.append(f"craft {r.name}")

    return list(dict.fromkeys(actions))

def format_response(msg: str, player: dict, location: dict, world_time: dict, scouted: list = None) -> dict:
    serialized_player = serialize_player(player)
    
    if hasattr(location, "model_dump"):
        serialized_location = {
            "id": getattr(location, "id", None),
            "name": location.name,
            "description": location.description,
            "exits": location.exits,
            "items": [serialize_item(i) for i in location.items],
            "camp_storage": [serialize_item(i) for i in getattr(location, 'camp_storage', [])],
            "enemies": [serialize_enemy(e) for e in location.enemies],
            "interactables": list(getattr(location, 'interactables', [])),
            "coordinates": location.coordinates.model_dump() if location.coordinates else None,
        }
    else:
        serialized_location = dict(location)
        if "interactables" not in serialized_location:
            serialized_location["interactables"] = []
        
    serialized_time = serialize_time(world_time)
    actions = get_available_actions(serialized_player, serialized_location, serialized_time)

    if "inventory" in serialized_player:
        del serialized_player["inventory"]

    resp = {
        "message": msg,
        "player": serialized_player,
        "location": serialized_location,
        "time": serialized_time,
        "available_actions": actions
    }
    if scouted is not None:
        resp["scouted_locations"] = scouted
    return resp

@router.post("/start", response_model=GameResponse)
def start_game(name: str, character_class: Optional[str] = None):
    service = GameService(_repo)
    try:
        player, location = service.create_new_player(name, character_class)
        world_time = _repo.get_world_time()
        return format_response(f"Welcome, {name}! Your adventure begins.", player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

class LoginRequest(BaseModel):
    name: str

@router.post("/login", response_model=GameResponse)
def login_game(req: LoginRequest):
    service = GameService(_repo)
    try:
        player, location = service.login_player(req.name)
        world_time = _repo.get_world_time()
        return format_response(f"Welcome back, {player.name}.", player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/command", response_model=GameResponse)
def send_command(req: CommandRequest):
    service = GameService(_repo)
    try:
        res = service.process_command(req.player_id, req.command)
        msg, player, location = res[:3]
        scouted = res[3] if len(res) > 3 else None
        
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time, scouted)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/move", response_model=GameResponse)
def action_move(req: MoveRequest):
    service = GameService(_repo)
    return execute_game_action(service, "move_player", req.player_id, req.direction)

@router.post("/action/take", response_model=GameResponse)
def action_take(req: ItemRequest):
    service = GameService(_repo)
    return execute_game_action(service, "take_item", req.player_id, req.item_name)

@router.post("/action/drop", response_model=GameResponse)
def action_drop(req: ItemRequest):
    service = GameService(_repo)
    return execute_game_action(service, "drop_item", req.player_id, req.item_name)

@router.post("/action/equip", response_model=GameResponse)
def action_equip(req: ItemRequest):
    service = GameService(_repo)
    return execute_game_action(service, "equip_item", req.player_id, req.item_name)

@router.post("/action/unequip", response_model=GameResponse)
def action_unequip(req: SlotRequest):
    service = GameService(_repo)
    return execute_game_action(service, "unequip_item", req.player_id, req.slot)

@router.post("/action/attack", response_model=GameResponse)
def action_attack(req: AttackRequest):
    service = GameService(_repo)
    return execute_game_action(service, "attack_enemy", req.player_id, req.target_name)

@router.post("/action/scout", response_model=GameResponse)
def action_scout(req: PlayerIdRequest):
    service = GameService(_repo)
    return execute_game_action(service, "scout_area", req.player_id)

@router.post("/action/camp", response_model=GameResponse)
def action_camp(req: CampRequest):
    service = GameService(_repo)
    return execute_game_action(service, "create_camp", req.player_id, req.camp_name)

@router.post("/action/travel", response_model=GameResponse)
def action_travel(req: TravelRequest):
    service = GameService(_repo)
    return execute_game_action(service, "fast_travel", req.player_id, req.waypoint_name)

@router.post("/action/store", response_model=GameResponse)
def action_store(req: ItemRequest):
    service = GameService(_repo)
    return execute_game_action(service, "store_item", req.player_id, req.item_name)

@router.post("/action/retrieve", response_model=GameResponse)
def action_retrieve(req: ItemRequest):
    service = GameService(_repo)
    return execute_game_action(service, "retrieve_item", req.player_id, req.item_name)

@router.post("/action/consume", response_model=GameResponse)
def action_consume(req: ItemRequest):
    service = GameService(_repo)
    return execute_game_action(service, "consume_item", req.player_id, req.item_name)

@router.post("/action/craft", response_model=GameResponse)
def action_craft(req: CraftRequest):
    service = GameService(_repo)
    return execute_game_action(service, "craft_item", req.player_id, req.recipe_name)

@router.post("/action/recipes", response_model=GameResponse)
def action_recipes(req: PlayerIdRequest):
    service = GameService(_repo)
    return execute_game_action(service, "get_recipes_list", req.player_id)

@router.post("/action/fill", response_model=GameResponse)
def action_fill(req: ItemRequest):
    service = GameService(_repo)
    return execute_game_action(service, "fill_flask", req.player_id, req.item_name)

@router.post("/action/talk", response_model=GameResponse)
def action_talk(req: TalkRequest):
    service = GameService(_repo)
    return execute_game_action(service, "talk_to_npc", req.player_id, req.npc_name)

@router.post("/action/dialogue", response_model=GameResponse)
def action_dialogue(req: DialogueRequest):
    service = GameService(_repo)
    return execute_game_action(service, "choose_dialogue_option", req.player_id, req.choice)

@router.post("/action/dialogue/end", response_model=GameResponse)
def action_dialogue_end(req: PlayerIdRequest):
    service = GameService(_repo)
    return execute_game_action(service, "end_dialogue", req.player_id)

@router.post("/action/buy", response_model=GameResponse)
def action_buy(req: TradeRequest):
    service = GameService(_repo)
    return execute_game_action(service, "buy_item", req.player_id, req.item_name)

@router.post("/action/sell", response_model=GameResponse)
def action_sell(req: TradeRequest):
    service = GameService(_repo)
    return execute_game_action(service, "sell_item", req.player_id, req.item_name)

@router.post("/action/quests", response_model=GameResponse)
def action_quests(req: PlayerIdRequest):
    service = GameService(_repo)
    return execute_game_action(service, "list_player_quests", req.player_id)

@router.post("/action/quest/turnin", response_model=GameResponse)
def action_quest_turnin(req: QuestTurnInRequest):
    service = GameService(_repo)
    return execute_game_action(service, "turn_in_quest", req.player_id, req.quest_id)

@router.post("/action/class", response_model=GameResponse)
def action_class(req: ClassSelectRequest):
    service = GameService(_repo)
    return execute_game_action(service, "select_class", req.player_id, req.character_class)

@router.post("/action/skill", response_model=GameResponse)
def action_skill(req: SkillUseRequest):
    service = GameService(_repo)
    return execute_game_action(service, "use_skill", req.player_id, req.skill_name, req.target_name)

@router.post("/action/skills", response_model=GameResponse)
def action_skills(req: PlayerIdRequest):
    service = GameService(_repo)
    return execute_game_action(service, "list_skills", req.player_id)

@router.post("/look", response_model=GameResponse)
def look(req: PlayerIdRequest):
    service = GameService(_repo)
    return execute_game_action(service, "look", req.player_id)

@router.post("/inventory", response_model=GameResponse)
def inventory(req: PlayerIdRequest):
    service = GameService(_repo)
    return execute_game_action(service, "map_inventory", req.player_id)

@router.get("/commands", response_model=list[CommandHelpResponse])
def get_commands():
    service = GameService(_repo)
    return service.get_command_help()

@router.post("/player/inventory")
def get_player_inventory(req: PlayerIdRequest):
    service = GameService(_repo)
    try:
        player, _ = service._get_player_and_location(req.player_id)
        if hasattr(player, "inventory") and player.inventory:
            return serialize_inventory(player.inventory)
        return []
    except ValueError as e:
        raise_game_error(e)
