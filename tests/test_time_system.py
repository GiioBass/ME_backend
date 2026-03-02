import pytest
from app.core.domain.time_system import WorldTime
from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.player import Player
from app.core.domain.location import Location, Coordinates

def test_world_time_logic():
    wt = WorldTime()
    assert wt.total_ticks == 0
    assert wt.day == 1
    assert wt.hour == 0
    assert wt.minute == 0
    
    # Advance 1 hour
    wt.advance(60)
    assert wt.hour == 1
    assert wt.minute == 0
    
    # Advance to Night (20:00 = 20 * 60 = 1200 ticks)
    # Current 60. Need 1140 more.
    wt.advance(1140)
    assert wt.hour == 20
    assert wt.is_night() is True
    
    # Advance to next day (Total 1440)
    # Current 1200. Need 240.
    wt.advance(240)
    assert wt.day == 2
    assert wt.hour == 0
    assert wt.is_night() is True # 00:00 is night

def test_game_service_time_integration():
    # Use InMemoryRepo but we need to mock get/save_world_time if not in InMemoryRepo
    # Let's quickly patch InMemoryRepo to support time or just mock it?
    # Better to verify using SQLRepo if possible or update InMemoryRepo.
    # Since I didn't update InMemoryRepo in the previous turn, I should probably do that 
    # OR mock the repo.
    # Let's fail fast if InMemoryRepo abstract methods are missing.
    # I'll update InMemoryRepo in the test setup or using a Mock.
    
    class MockRepo(InMemoryGameRepository):
        def __init__(self):
            super().__init__()
            self.time = WorldTime()
            
        def get_world_time(self):
            return self.time
            
        def save_world_time(self, wt):
            self.time = wt
            
        def get_location_by_coordinates(self, x, y, z):
            return None # Not needed for this test

    repo = MockRepo()
    service = GameService(repo)
    
    # Setup player
    player, _ = service.create_new_player("TimeTraveler")
    
    # 1. Check Time Command
    msg, _, _ = service.process_command(player.id, "time")
    assert "Day 1, 00:00" in msg
    
    # 2. Move (Cost 10 min)
    # We need a neighbor to move to.
    # create_new_player generates current loc and neighbors.
    # let's move north.
    msg, _, _ = service.process_command(player.id, "north")
    assert "You travel north" in msg
    
    # Check time advanced
    wt = repo.get_world_time()
    assert wt.total_ticks == 10
    assert wt.minute == 10
    
    # 3. Look at Night
    # Fast forward to night
    repo.time.advance(1200 - 10) # Set to 20:00
    
    msg, _, _ = service.process_command(player.id, "look")
    assert "[NIGHT]" in msg
    assert "dark" in msg

if __name__ == "__main__":
    test_world_time_logic()
    test_game_service_time_integration()
