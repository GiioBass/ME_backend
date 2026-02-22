from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.use_cases.game_service import GameService
from app.ports.repositories import GameRepository

# DTOs (Data Transfer Objects)
class CommandRequest(BaseModel):
    player_id: str
    command: str

class GameResponse(BaseModel):
    message: str
    player: dict
    location: dict

# Dependency Injection Helper (Mockable)
# In a real app, use a proper DI container or FastAPI's Depends with a provider
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
        
        # Format the grouped inventory list for the frontend
        # Assuming the original item dictionary as base, adding qty
        new_inventory = []
        for name, group_data in grouped.items():
            item_data = group_data["item"]
            if isinstance(item_data, dict):
                item_data["qty"] = group_data["qty"]
                new_inventory.append(item_data)
            else:
                # If it's a model instance somehow, try dumping or set attribute
                item_dict = item_data.model_dump() if hasattr(item_data, "model_dump") else {"name": name}
                item_dict["qty"] = group_data["qty"]
                new_inventory.append(item_dict)
        data["inventory"] = new_inventory
    return data

router = APIRouter()

# Global Repo instance
# In production, this would be dependency injected
# from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
# _repo = InMemoryGameRepository()

from app.adapters.driven.persistence.sql_repository import SQLGameRepository
_repo = SQLGameRepository()

@router.post("/start", response_model=GameResponse)
def start_game(name: str):
    service = GameService(_repo)
    player = service.create_new_player(name)
    # Get initial location
    location = _repo.get_location(player.current_location_id)
    return {
        "message": f"Welcome, {name}! Your adventure begins.",
        "player": serialize_player(player),
        "location": location.model_dump() if location else {}
    }

@router.post("/command", response_model=GameResponse)
def send_command(req: CommandRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.process_command(req.player_id, req.command)
        return {
            "message": msg,
            "player": serialize_player(player),
            "location": location.model_dump()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
