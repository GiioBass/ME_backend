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

class PlayerIdRequest(BaseModel):
    player_id: str

class GameResponse(BaseModel):
    message: str
    player: dict
    location: dict
    time: dict
    scouted_locations: list | None = None

def get_game_service(repo: GameRepository) -> GameService:
    return GameService(repo)

def serialize_player(player) -> dict:
    data = player.model_dump()
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
            elif isinstance(item, dict):
                eq_data[slot] = item
            elif hasattr(item, "model_dump"):
                eq_data[slot] = item.model_dump()
            else:
                eq_data[slot] = {"name": str(item)}
        data["equipment"] = eq_data
        
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

def format_response(msg: str, player: dict, location: dict, world_time: dict, scouted: list = None) -> dict:
    resp = {
        "message": msg,
        "player": serialize_player(player),
        "location": location.model_dump() if hasattr(location, "model_dump") else location,
        "time": serialize_time(world_time)
    }
    if scouted is not None:
        resp["scouted_locations"] = scouted
    return resp

@router.post("/start", response_model=GameResponse)
def start_game(name: str):
    service = GameService(_repo)
    # create_new_player now gracefully returns the existing player if the name is taken
    # but strictly speaking this is the 'register' endpoint
    player = service.create_new_player(name)
    location = _repo.get_location(player.current_location_id)
    world_time = _repo.get_world_time()
    return format_response(f"Welcome, {name}! Your adventure begins.", player, location, world_time)

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
        raise HTTPException(status_code=404, detail=str(e))

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
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/action/move", response_model=GameResponse)
def action_move(req: MoveRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.move_player(req.player_id, req.direction)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/action/take", response_model=GameResponse)
def action_take(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.take_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/action/drop", response_model=GameResponse)
def action_drop(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.drop_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/action/equip", response_model=GameResponse)
def action_equip(req: ItemRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.equip_item(req.player_id, req.item_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/action/unequip", response_model=GameResponse)
def action_unequip(req: SlotRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.unequip_item(req.player_id, req.slot)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/action/attack", response_model=GameResponse)
def action_attack(req: AttackRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.attack_enemy(req.player_id, req.target_name)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/action/scout", response_model=GameResponse)
def action_scout(req: PlayerIdRequest):
    service = GameService(_repo)
    try:
        msg, player, location, scouted = service.scout_area(req.player_id)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time, scouted)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/look", response_model=GameResponse)
def look(req: PlayerIdRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.look(req.player_id)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/inventory", response_model=GameResponse)
def inventory(req: PlayerIdRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.map_inventory(req.player_id)
        world_time = _repo.get_world_time()
        return format_response(msg, player, location, world_time)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
