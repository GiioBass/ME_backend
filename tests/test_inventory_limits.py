import pytest
from app.core.domain.player import Player
from app.core.domain.location import Location, Coordinates
from app.core.domain.item import Item, ItemType
from app.core.use_cases.game_service import GameService
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from sqlmodel import SQLModel, create_engine
from app.adapters.driven.persistence import db_config

@pytest.fixture
def repo(monkeypatch):
    # Use an in-memory SQLite database for testing
    from sqlmodel import StaticPool
    engine = create_engine("sqlite:///:memory:", 
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return SQLGameRepository(db_engine=engine)

@pytest.fixture
def game_service(repo):
    return GameService(repository=repo)

def test_take_item_weight_limit(game_service, repo):
    # Create player and location
    player = Player(name="TestPlayer", current_location_id="test_loc")
    player.stats.max_weight = 10.0
    repo.save_player(player)

    loc = Location(id="test_loc", name="Test Room", description="A room")
    
    # Create items
    heavy_item = Item(name="Anvil", description="Very heavy", item_type=ItemType.MATERIAL, weight=8.0)
    light_item = Item(name="Feather", description="Very light", item_type=ItemType.MATERIAL, weight=1.0)
    another_heavy = Item(name="Boulder", description="Too heavy", item_type=ItemType.MATERIAL, weight=5.0)

    loc.add_item(heavy_item)
    loc.add_item(light_item)
    loc.add_item(another_heavy)
    repo.create_location(loc)

    # Pick up first heavy item
    msg, p, l = game_service.take_item(player.id, "Anvil")
    assert "You picked up 1x Anvil" in msg
    assert p.current_weight == 8.0

    # Pick up light item
    msg, p, l = game_service.take_item(player.id, "Feather")
    assert "You picked up 1x Feather" in msg
    assert p.current_weight == 9.0

    # Try to pick up another heavy item (would exceed max_weight)
    msg, p, l = game_service.take_item(player.id, "Boulder")
    assert "Inventory full!" in msg
    assert p.current_weight == 9.0
    
    # Assert the boulder is still in the room
    assert len(l.items) == 1
    assert l.items[0].name == "Boulder"
    
    # Test inventory command shows weight
    msg, p, l = game_service.map_inventory(player.id)
    assert "Weight: 9.0/10.0" in msg
