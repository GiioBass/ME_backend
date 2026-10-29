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


def test_merchant_full_inventory_and_i18n():
    from app.core.i18n import set_current_lang, translate_text

    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, location = service.create_new_player("RichTrader")
    player.stats.gold = 200
    repo.save_player(player)

    shop_data = service.dialogue_service.get_merchant_shop_data(location.id)
    assert shop_data is not None
    item_names = [item["name"] for item in shop_data["items"]]
    assert "Iron Dagger" in item_names
    assert "Leather Armor" in item_names
    assert "Rations" in item_names
    assert "Health Potion" in item_names
    assert "Mana Potion" in item_names

    # Buy Iron Dagger (35g), Leather Armor (45g), Rations (10g)
    msg, p, _ = service.process_command(player.id, "buy Iron Dagger")
    assert "You bought Iron Dagger for 35 Gold" in msg
    assert p.stats.gold == 165

    msg, p, _ = service.process_command(player.id, "buy Leather Armor")
    assert "You bought Leather Armor for 45 Gold" in msg
    assert p.stats.gold == 120

    # Test Spanish command alias ('comprar Rations') and Spanish translation
    set_current_lang("es")
    try:
        msg, p, _ = service.process_command(player.id, "comprar Rations")
        translated = translate_text(msg, "es")
        assert "Compraste Rations por 10 de Oro" in translated
        assert p.stats.gold == 110
    finally:
        set_current_lang("en")

