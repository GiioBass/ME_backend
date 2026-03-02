import pytest
from app.core.domain.player import Player
from app.core.domain.item import Item, ItemType
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.time_system import WorldTime

def test_survival_degradation():
    from app.core.domain.location import Location
    import uuid
    repo = SQLGameRepository()
    service = GameService(repo)
    player_name = f"survivor_{uuid.uuid4().hex[:8]}"
    player, _ = service.create_new_player(player_name)
    
    # Move to trigger _advance_time_and_events cleanly without overriding DB
    # or just call it directly.
    world_time = repo.get_world_time()
    service._advance_time_and_events(world_time, player, 100)
    
    # 100 // 10 = 10 hunger loss
    assert player.stats.hunger == 90
    # 100 // 8 = 12 thirst loss
    assert player.stats.thirst == 88

    service._advance_time_and_events(world_time, player, 1000)
    assert player.stats.hunger == 0
    assert player.stats.thirst == 0
    
    # Total damage from 1000 // 10 (100) and 1000 // 8 (125) = 225
    # Since hp is 100, player hp will be 0
    assert player.stats.hp == 0

def test_consume_item():
    import uuid
    repo = SQLGameRepository()
    service = GameService(repo)
    player_name = f"consumer_{uuid.uuid4().hex[:8]}"
    player, _ = service.create_new_player(player_name)
    
    apple = Item(name="Apple", description="A red apple", item_type=ItemType.CONSUMABLE, restore_hunger=20, restore_hp=10)
    player.add_item(apple)
    repo.save_player(player)
    
    player.stats.hunger = 50
    player.stats.hp = 50
    repo.save_player(player)
    
    msg, p, l = service.consume_item(player.id, "Apple")
    assert "You consumed Apple" in msg
    assert "Restored 20 Hunger" in msg
    assert p.stats.hunger == 70
    assert p.stats.hp == 60
    assert not p.has_item("Apple")
