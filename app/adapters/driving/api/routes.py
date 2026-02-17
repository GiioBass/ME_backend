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
        "player": player.model_dump(),
        "location": location.model_dump() if location else {}
    }

@router.post("/command", response_model=GameResponse)
def send_command(req: CommandRequest):
    service = GameService(_repo)
    try:
        msg, player, location = service.process_command(req.player_id, req.command)
        return {
            "message": msg,
            "player": player.model_dump(),
            "location": location.model_dump()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
