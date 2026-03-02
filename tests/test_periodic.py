import pytest
from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.player import Player

def test_passive_heal():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, _ = service.create_new_player("Healer")
    
    # Damage Player
    player.stats.hp = 50
    repo.save_player(player)
    
    # Set time
    time = repo.get_world_time()
    time.total_ticks = 0
    repo.save_world_time(time)

    loc = repo.get_location(player.current_location_id)
    # create north location to move to
    loc.exits["north"] = "loc_0_1_0"
    repo.create_location(loc)
    from app.core.domain.location import Coordinates, Location
    loc_n = Location(id="loc_0_1_0", name="N", description="N", coordinates=Coordinates(x=0,y=1,z=0))
    repo.create_location(loc_n)

    # Move North (Cost 10) -> Heal Trigger
    service.process_command(player.id, "go north")
    
    updated_player = repo.get_player(player.id)
    assert updated_player.stats.hp == 51 # Healed by 1

if __name__ == "__main__":
    test_passive_heal()
