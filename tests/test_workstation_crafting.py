from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.item import Item, ItemType
import uuid

def test_workstation_validation():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, location = service.create_new_player("CraftHero")

    # Seed materials in inventory: 2 Iron Ingot + 1 Stick
    iron1 = Item(id=str(uuid.uuid4()), name="Iron Ingot", description="iron", item_type=ItemType.MATERIAL, value=15, weight=2.0)
    iron2 = Item(id=str(uuid.uuid4()), name="Iron Ingot", description="iron", item_type=ItemType.MATERIAL, value=15, weight=2.0)
    stick = Item(id=str(uuid.uuid4()), name="Stick", description="stick", item_type=ItemType.MATERIAL, value=1, weight=0.5)
    player.inventory.extend([iron1, iron2, stick])

    # Location without anvil -> should fail
    location.interactables = []
    msg, p, _ = service.craft_item(player.id, "Iron Sword")
    assert "You need a Anvil nearby" in msg

    # Add anvil to location interactables -> should succeed
    location.interactables = ["station:anvil", "anvil"]
    msg, p, _ = service.craft_item(player.id, "Iron Sword")
    assert "Successfully crafted 1x Iron Sword" in msg
    assert any(i.name == "Iron Sword" for i in p.inventory)
