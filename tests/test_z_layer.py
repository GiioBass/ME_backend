import pytest
from unittest.mock import patch
from app.core.use_cases.world_generator import WorldGenerator
from app.core.use_cases.command_parser import CommandParser
from app.core.domain.player import Player
from app.core.domain.location import Location, Coordinates

def test_cave_generation():
    generator = WorldGenerator()
    
    # Mock random to ensure a cave is generated (probability < 0.1)
    with patch('random.random', return_value=0.05):
        locations = generator.generate_chunk(0, 0, size=1)
        
    # Should generate surface + cave
    assert len(locations) == 2
    
    surface = next(l for l in locations if l.coordinates.z == 0)
    cave = next(l for l in locations if l.coordinates.z == -1)
    
    assert surface.coordinates.z == 0
    assert cave.coordinates.z == -1
    
    assert "down" in surface.exits
    assert surface.exits["down"] == cave.id
    assert "up" in cave.exits
    assert cave.exits["up"] == surface.id

def test_vertical_movement_commands():
    parser = CommandParser()
    
    # Setup locations
    surface = Location(id="surf", name="Surface", description="Desc", coordinates=Coordinates(x=0,y=0,z=0))
    cave = Location(id="cave", name="Cave", description="Desc", coordinates=Coordinates(x=0,y=0,z=-1))
    
    surface.exits["down"] = cave.id
    cave.exits["up"] = surface.id
    
    player = Player(name="Hero", current_location_id="surf")
    
    # Test "enter"
    wt = None
    result = parser.parse("enter", player, surface, wt, lambda p: None)
    assert "You travel down" in result.message
    assert player.current_location_id == "cave"
    
    # Test "climb" (from cave)
    player.current_location_id = "cave" # Manually move player for test
    result = parser.parse("climb", player, cave, wt, lambda p: None)
    assert "You travel up" in result.message
    assert player.current_location_id == "surf"

    # Test "down" explicit
    player.current_location_id = "surf"
    result = parser.parse("down", player, surface, wt, lambda p: None)
    assert "You travel down" in result.message
