import pytest
from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.player import Player
from app.core.domain.location import Location

def test_time_advancement():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    
    # Setup
    player, _ = service.create_new_player("TimeTraveler")
    
    # Initial Time
    time = repo.get_world_time()
    assert time.total_ticks == 0
    
    # Action 1: Look (should advance time?)
    # Based on recent edits, Look might not have time_cost > 0.
    # Let's check 'move' which definitely has time_cost=10 (from Step 689).
    service.process_command(player.id, "north")
    
    time = repo.get_world_time()
    assert time.total_ticks == 10
    
    # Action 2: Wait/Time command (no cost usually, check?)
    service.process_command(player.id, "time")
    # Time shouldn't change if command has 0 cost
    assert repo.get_world_time().total_ticks == 10

def test_night_cycle():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, _ = service.create_new_player("NightOwl")
    
    # Advanced to night (20:00 = 20 * 60 = 1200 ticks)
    time = repo.get_world_time()
    time.total_ticks = 1190 # 19:50
    repo.save_world_time(time)
    
    # Move takes 10 mins -> 1200 -> Night
    msg, _, _ = service.process_command(player.id, "north")
    
    assert "Night has fallen" in msg
    assert repo.get_world_time().total_ticks == 1200

if __name__ == "__main__":
    test_time_advancement()
    test_night_cycle()
