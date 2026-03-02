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

class ItemRequest(BaseModel):
    player_id: str
    item_name: str

class CampRequest(BaseModel):
    player_id: str
    camp_name: str

class TravelRequest(BaseModel):
    player_id: str
    waypoint_name: str

class PlayerIdRequest(BaseModel):
    player_id: str

class GameResponse(BaseModel):
    message: str
    player: dict
    location: dict
    time: dict
    available_actions: list[str] = []
    scouted_locations: list | None = None

def get_game_service(repo: GameRepository) -> GameService:
    return GameService(repo)

def serialize_player(player) -> dict:
    data = player.model_dump()
    data["current_weight"] = player.current_weight
    
    if "inventory" in data and data["inventory"]:
        grouped = {}
        for item in data["inventory"]:
            name = item.get("name", "Unknown") if isinstance(item, dict) else (item.name if hasattr(item, "name") else "Unknown")
            if name not in grouped:
                grouped[name] = {"item": item, "qty": 0}
            grouped[name]["qty"] += 1
        
        new_inventory = []
        for name, group_data in grouped.items():
            item_data = group_data["item"]
            if isinstance(item_data, dict):
                item_data["qty"] = group_data["qty"]
                new_inventory.append(item_data)
            else:
                item_dict = item_data.model_dump() if hasattr(item_data, "model_dump") else {"name": name}
                item_dict["qty"] = group_data["qty"]
                new_inventory.append(item_dict)
        data["inventory"] = new_inventory
        
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
    actions = ["look", "inventory", "scout"]
    
    if location:
        if location.get("exits"):
            for direction in location["exits"].keys():
                actions.append(f"move {direction}")
        
        if world_time and world_time.get("is_night"):
            actions.append("sleep")

        has_water = any(inter.startswith("water_source:") for inter in location.get("interactables", []))
        if has_water:
            # Show fill for specific items in inventory
            for item in player.get("inventory", []):
                item_name = item.get("name", "")
                if "Empty" in item_name and "Flask" in item_name:
                    actions.append(f"fill {item_name}")

        if location.get("items"):
            for item in location["items"]:
                name = item.get("name") if isinstance(item, dict) else item
                actions.append(f"take {name}")
                
        if location.get("enemies"):
            for enemy in location["enemies"]:
                name = enemy.get("name") if isinstance(enemy, dict) else enemy
                actions.append(f"attack {name}")
                
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
                    
    return list(dict.fromkeys(actions))  # Deduplicate while preserving order

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
            "coordinates": location.coordinates.model_dump() if location.coordinates else None,
        }
    else:
        serialized_location = location
        
    serialized_time = serialize_time(world_time)
    actions = get_available_actions(serialized_player, serialized_location, serialized_time)

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
def start_game(name: str):
    service = GameService(_repo)
    try:
        player, location = service.create_new_player(name)
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
    try:
        msg, player, location = service.move_player(req.player_id, req.direction)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/take", response_model=GameResponse)
def action_take(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.take_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/drop", response_model=GameResponse)
def action_drop(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.drop_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/equip", response_model=GameResponse)
def action_equip(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.equip_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/unequip", response_model=GameResponse)
def action_unequip(req: SlotRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.unequip_item(req.player_id, req.slot)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/attack", response_model=GameResponse)
def action_attack(req: AttackRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.attack_enemy(req.player_id, req.target_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/scout", response_model=GameResponse)
def action_scout(req: PlayerIdRequest):
    service = GameService(_repo)
    try:
        msg, player, location, scouted = service.scout_area(req.player_id)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time, scouted)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/camp", response_model=GameResponse)
def action_camp(req: CampRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.create_camp(req.player_id, req.camp_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/travel", response_model=GameResponse)
def action_travel(req: TravelRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.fast_travel(req.player_id, req.waypoint_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/store", response_model=GameResponse)
def action_store(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.store_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/retrieve", response_model=GameResponse)
def action_retrieve(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.retrieve_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/consume", response_model=GameResponse)
def action_consume(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.consume_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/action/fill", response_model=GameResponse)
def action_fill(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.fill_vessel(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/look", response_model=GameResponse)
def look(req: PlayerIdRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.look(req.player_id)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)

@router.post("/inventory", response_model=GameResponse)
def inventory(req: PlayerIdRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.map_inventory(req.player_id)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise_game_error(e)
