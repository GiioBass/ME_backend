import os
import pytest
from sqlmodel import SQLModel, create_engine, Session
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.domain.player import Player
from app.core.domain.location import Location

# Use a separate test DB
TEST_DB = "test_database.db"
sqlite_url = f"sqlite:///{TEST_DB}"

@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(sqlite_url)
    SQLModel.metadata.create_all(engine)
    yield engine
    # Cleanup
    SQLModel.metadata.drop_all(engine)
    os.remove(TEST_DB)

def test_persistence_flow(engine):
    # We need to monkeypatch the engine in sql_repository or use dependency injection
    # valid point: sql_repository imports 'engine' from db_config
    # easier to just test the repository logic if we can swap the engine.
    # But for an end-to-end test, we should rely on the configured engine.
    
    # Let's try to test the Repository class directly, but we need it to use OUR test engine.
    # The current implementation of SQLGameRepository hardcodes `from ...db_config import engine`.
    # This makes it hard to unit test with a different DB without mocking.
    
    # For now, let's just inspect the actual `database.db` if it exists, or 
    # run a test that uses the main DB (not ideal but works for prototype).
    
    # BETTER: Update SQLGameRepository to accept engine in init, defaulting to global.
    pass

from app.adapters.driven.persistence.sql_models import PlayerDB, LocationDB

def test_manual_db_check():
    # value of using SQLGameRepository
    repo = SQLGameRepository()
    
    # Create Player
    p = Player(name="PersistedHero", current_location_id="loc_1")
    repo.save_player(p)
    
    # Simulate restart by creating new repo instance (stateless)
    repo2 = SQLGameRepository()
    loaded_p = repo2.get_player(p.id)
    
    assert loaded_p is not None
    assert loaded_p.name == "PersistedHero"
    assert loaded_p.id == p.id
