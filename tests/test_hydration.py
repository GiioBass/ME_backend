import pytest
import uuid
from app.core.domain.player import Player
from app.core.domain.item import Item, ItemType
from app.core.domain.location import Location, Coordinates
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.use_cases.game_service import GameService
from app.core.use_cases.world_generator import WorldGenerator
from sqlmodel import SQLModel, create_engine

@pytest.fixture
def repo(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    import app.adapters.driven.persistence.sql_repository as sql_repo
    monkeypatch.setattr(sql_repo, "engine", engine)
    return SQLGameRepository()

@pytest.fixture
def game_service(repo):
    return GameService(repository=repo)

def test_fill_flask_logic(game_service, repo):
    player_name = f"hydrator_{uuid.uuid4().hex[:8]}"
    player, _ = game_service.create_new_player(player_name)
    
    # Manually create a location with water
    loc = Location(
        id="water_loc", 
        name="River Bank", 
        description="A nice river.",
        coordinates=Coordinates(x=10, y=10, z=0),
        interactables=["water_source:River"]
    )
    repo.create_location(loc)
    player.current_location_id = "water_loc"
    
    # Add empty flask
    flask = Item(id="flask1", name="Empty Flask", description="Empty", item_type=ItemType.TOOL)
    player.add_item(flask)
    repo.save_player(player)
    
    # Try to fill
    msg, p, l = game_service.process_command(player.id, "fill flask")
    assert "fill the Empty Flask with water" in msg
    assert p.has_item("Water Flask")
    assert not p.has_item("Empty Flask")
    
    # Test consumption of Water Flask
    p.stats.thirst = 50
    repo.save_player(p)
    
    msg, p, l = game_service.process_command(player.id, "consume Water Flask")
    assert "consumed Water Flask" in msg
    assert "Restored 40 Thirst" in msg
    assert p.stats.thirst == 90

def test_no_water_fill(game_service, repo):
    player_name = f"dry_{uuid.uuid4().hex[:8]}"
    player, _ = game_service.create_new_player(player_name)
    
    # Create dry location
    loc = Location(id="dry_loc", name="Desert", description="Dry.", coordinates=Coordinates(x=11, y=11, z=0))
    repo.create_location(loc)
    player.current_location_id = "dry_loc"
    
    # Add empty flask
    flask = Item(id="flask2", name="Empty Flask", description="Empty", item_type=ItemType.TOOL)
    player.add_item(flask)
    repo.save_player(player)
    
    # Try to fill
    msg, p, l = game_service.process_command(player.id, "fill flask")
    assert "no water source here" in msg
    assert p.has_item("Empty Flask")
    assert not p.has_item("Water Flask")

def test_water_source_generation():
    # Test that WorldGenerator actually produces water sources sometimes
    gen = WorldGenerator()
    found = False
    for i in range(200):
        # We need to vary x and y to avoid hitting the same seed/location if there's any caching (though there isn't here)
        loc = gen.generate_single_location(i, i+100, 0)
        if any(inter.startswith("water_source:") for inter in loc.interactables):
            found = True
            break
    assert found, "Should generate at least one water source in 200 attempts"
