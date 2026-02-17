from app.core.use_cases.world_generator import WorldGenerator
from app.core.domain.location import Location

def test_generate_chunk_connectivity():
    gen = WorldGenerator()
    # Generate a 3x3 chunk starting at 0,0
    chunk = gen.generate_chunk(start_x=0, start_y=0, size=3)
    
    assert len(chunk) == 9
    
    # helper to find loc by x,y
    def get_loc(x, y):
        for loc in chunk:
            if loc.coordinates.x == x and loc.coordinates.y == y:
                return loc
        return None

    # Check center (1,1) connectivity
    center = get_loc(1, 1)
    assert center is not None
    
    # It should have neighbors on all 4 sides since it's 3x3
    # North (1,2)
    assert "north" in center.exits
    assert center.exits["north"] == get_loc(1, 2).id
    
    # South (1,0)
    assert "south" in center.exits
    assert center.exits["south"] == get_loc(1, 0).id
    
    # East (2,1)
    assert "east" in center.exits
    assert center.exits["east"] == get_loc(2, 1).id
    
    # West (0,1)
    assert "west" in center.exits
    assert center.exits["west"] == get_loc(0, 1).id

    # Check corner (0,0) - should only have North and East
    corner = get_loc(0, 0)
    assert "north" in corner.exits
    assert "east" in corner.exits
    assert "south" not in corner.exits # Edge of map
    assert "west" not in corner.exits # Edge of map

