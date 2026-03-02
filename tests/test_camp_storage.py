import pytest
from app.core.domain.player import Player
from app.core.domain.location import Location, Coordinates
from app.core.domain.item import Item, ItemType
from app.core.use_cases.game_service import GameService
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
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

def test_store_and_retrieve_items(game_service, repo):
    player = Player(name="StorageMaster", current_location_id="camp_loc")
    player.stats.max_weight = 100.0
    repo.save_player(player)

    loc = Location(id="camp_loc", name="Camp", description="A cozy camp")
    repo.create_location(loc)

    # 1. Player has item, creates camp
    sword = Item(name="Old Sword", description="A rusty old blade.", item_type=ItemType.WEAPON, weight=5.0)
    player.add_item(sword)
    repo.save_player(player)

    msg, p, l = game_service.create_camp(player.id, "My Camp")
    assert "Waypoint 'My Camp' created" in msg

    # 2. Store item
    msg, p, l = game_service.store_item(player.id, "Old Sword")
    assert "You stored Old Sword" in msg
    assert len(p.inventory) == 0
    assert len(l.camp_storage) == 1

    # try store something you dont have
    msg, p, l = game_service.store_item(player.id, "Ghost Sword")
    assert "You don't have 'Ghost Sword'" in msg

    # 3. List chest
    loc_from_db = repo.get_location("camp_loc")
    print("DEBUG DB CAMP STORAGE:", loc_from_db.camp_storage if loc_from_db else "NO LOC")

    msg, p, l = game_service.list_chest(player.id)
    assert "Camp Chest Contents" in msg
    assert "Old Sword" in msg

    # 4. Retrieve item
    msg, p, l = game_service.retrieve_item(player.id, "Old Sword")
    assert "You retrieved Old Sword" in msg
    assert len(p.inventory) == 1
    assert len(l.camp_storage) == 0
    assert p.inventory[0].name == "Old Sword"

    # try retrieve something chest doesnt have
    msg, p, l = game_service.retrieve_item(player.id, "Old Sword")
    assert "There is no 'Old Sword' in the camp chest" in msg
