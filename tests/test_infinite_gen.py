import pytest
from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.player import Player
from app.core.domain.location import Location, Coordinates

def test_infinite_generation():
    # Setup
    repo = InMemoryGameRepository()
    service = GameService(repo)
    
    # 1. Create player (generates 0,0 chunk)
    player = service.create_new_player("Explorer")
    
    start_loc = repo.get_location(player.current_location_id)
    assert start_loc.coordinates.x == 0
    assert start_loc.coordinates.y == 0
    
    # 2. Move North up to limit of chunk (0,0 to 0,4)
    # Chunk size 5, centered at 0,0? No, typically 0..4 in previous impl
    # WorldGenerator: start_x=0, start_y=0, size=5. -> x 0..4, y 0..4
    
    # Let's move to (0,4)
    for _ in range(4):
        msg, p, loc = service.process_command(player.id, "go north")
        assert "travel north" in msg.lower()
    
    current_loc = repo.get_location(player.current_location_id)
    assert current_loc.coordinates.y == 4
    
    # 3. Move North again (to 0,5) - Should trigger expansion
    msg, p, loc = service.process_command(player.id, "go north")
    
    assert "uncharted lands" in msg.lower() or "travel north" in msg.lower()
    assert loc.coordinates.y == 5
    
    # Verify new chunk exists
    # If we are at 0,5. Chunk size 5. (0//5)*5 = 0.
    # (5//5)*5 = 5.
    # So new chunk starts at y=5.
    
    # Check if (0,6) exists (it should be part of the new 5x5 chunk)
    loc_next = repo.get_location_by_coordinates(0, 6, 0)
    assert loc_next is not None

if __name__ == "__main__":
    test_infinite_generation()
