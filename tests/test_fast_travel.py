import pytest
from app.core.domain.player import Player
from app.core.domain.location import Location, Coordinates
from app.core.use_cases.game_service import GameService
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from sqlmodel import SQLModel, create_engine
from app.adapters.driven.persistence import db_config

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

def test_fast_travel_and_camp(game_service, repo):
    # Setup player and two locations
    player = Player(name="Traveler", current_location_id="loc_1")
    player.stats.max_hp = 100
    player.stats.hp = 100
    repo.save_player(player)

    loc1 = Location(id="loc_1", name="Home Base", description="Start point", coordinates=Coordinates(x=0, y=0, z=0))
    loc2 = Location(id="loc_2", name="Distant Ruins", description="End point", coordinates=Coordinates(x=10, y=10, z=0))
    repo.create_location(loc1)
    repo.create_location(loc2)

    # Cannot travel to unknown waypoint
    msg, p, l = game_service.fast_travel(player.id, "Ruins")
    assert "don't know the way" in msg
    assert p.current_location_id == "loc_1"

    # Move player manually to loc_2 and camp
    player.current_location_id = "loc_2"
    repo.save_player(player)
    
    msg, p, l = game_service.create_camp(player.id, "Ruins Camp")
    assert "Waypoint 'Ruins Camp' created" in msg
    assert "Ruins Camp" in p.waypoints
    assert p.waypoints["Ruins Camp"] == "loc_2"

    # Move player back to loc 1
    p.current_location_id = "loc_1"
    repo.save_player(p)

    # Travel to the newly created camp
    msg, p, l = game_service.fast_travel(player.id, "Ruins Camp")
    assert "You traveled to Ruins Camp" in msg
    assert p.current_location_id == "loc_2"
    assert l.id == "loc_2"
    
    # Distance from 0,0 to 10,10 is roughly 15 (hypotenuse ~14.14 -> ceil 15)
    # energy_cost = dist * 2 = 15 * 2 = 30. But player regens 15 HP because 150 ticks // 10 == 15.
    assert "spent 30 HP" in msg
    assert p.stats.hp == 85

def test_exhausted_travel(game_service, repo):
    player = Player(name="Tired", current_location_id="loc_1")
    player.stats.hp = 10  # Low HP
    repo.save_player(player)

    loc1 = Location(id="loc_1", name="Home Base", description="Start", coordinates=Coordinates(x=0, y=0, z=0))
    loc2 = Location(id="loc_2", name="Far away", description="End", coordinates=Coordinates(x=10, y=10, z=0))
    repo.create_location(loc1)
    repo.create_location(loc2)
    
    player.add_waypoint("FarCamp", "loc_2")
    repo.save_player(player)

    # Try to travel, but require 30 HP, player has only 10
    msg, p, l = game_service.fast_travel(player.id, "FarCamp")
    assert "too exhausted" in msg
    assert p.current_location_id == "loc_1" # Did not move
    assert p.stats.hp == 10 # Didn't consume hp
