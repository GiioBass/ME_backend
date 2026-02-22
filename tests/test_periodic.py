import pytest
from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.player import Player

def test_passive_heal():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player = service.create_new_player("Healer")
    
    # Damage Player
    player.stats.hp = 50
    repo.save_player(player)
    
    # Set time to 9 ticks
    time = repo.get_world_time()
    time.total_ticks = 9
    repo.save_world_time(time)
    
    # Action takes 1 tick (Look usually 0, but take/drop/move use time)
    # Move is 10 ticks.
    # Take is 1 tick.
    # We need an action that hits the % 10 == 0 mark.
    # If Look is 0 cost, it won't advance time.
    # Let's assume we implement 'wait' command or similar, or just relying on existing commands.
    # 'take' is 1 min.
    
    # Add dummy item to take
    loc = repo.get_location(player.current_location_id)
    from app.core.domain.item import Item
    loc.add_item(Item(name="Rock", description="rock", item_type="junk", value=0))
    repo.create_location(loc)
    
    # Take Rock (Cost 1) -> Total 10 -> Heal Trigger
    service.process_command(player.id, "take Rock")
    
    updated_player = repo.get_player(player.id)
    assert updated_player.stats.hp == 51 # Healed by 1

if __name__ == "__main__":
    test_passive_heal()
