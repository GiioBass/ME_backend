from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService

def test_npc_dialogue_flow():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, location = service.create_new_player("Hero")

    # 1. Look should show NPCs in Oakfield
    msg, _, _ = service.look(player.id)
    assert "Village Elder" in msg
    assert "Merchant Silas" in msg

    # 2. Talk to Village Elder
    msg, p, _ = service.process_command(player.id, "talk Village Elder")
    assert "Greetings, traveler" in msg
    assert p.active_dialogue is not None

    # 3. Choose dialogue option 1 ("Who are you?")
    msg, p, _ = service.process_command(player.id, "dialogue 1")
    assert "guardian of this settlement" in msg

    # 4. Choose dialogue option 2 (Leave)
    msg, p, _ = service.process_command(player.id, "dialogue 2")
    assert p.active_dialogue is None

def test_explicit_end_dialogue():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, _ = service.create_new_player("Talker")

    # Start dialogue
    service.process_command(player.id, "talk Village Elder")
    p = repo.get_player(player.id)
    assert p.active_dialogue is not None

    # End dialogue via command 'leave'
    msg, p, _ = service.process_command(player.id, "leave")
    assert "Farewell" in msg or "ended" in msg
    assert p.active_dialogue is None

    # Start dialogue again and end via end_dialogue
    service.process_command(player.id, "talk Village Elder")
    msg, p, _ = service.end_dialogue(player.id)
    assert p.active_dialogue is None

def test_merchant_trade_system():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, _ = service.create_new_player("TraderHero")
    assert player.stats.gold == 50

    # 1. View shop
    msg, _, _ = service.process_command(player.id, "shop")
    assert "Merchant Silas's Shop" in msg
    assert "Health Potion" in msg

    # 2. Buy Health Potion (20g)
    msg, p, _ = service.process_command(player.id, "buy Health Potion")
    assert "You bought Health Potion for 20 Gold" in msg
    assert p.stats.gold == 30
    assert any(i.name == "Health Potion" for i in p.inventory)

    # 3. Sell Health Potion (10g)
    msg, p, _ = service.process_command(player.id, "sell Health Potion")
    assert "You sold Health Potion" in msg
    assert p.stats.gold == 40
    assert not any(i.name == "Health Potion" for i in p.inventory)
