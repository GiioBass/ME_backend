import pytest
from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.domain.item import Item

def test_inventory_flow():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    
    # Setup: Player and Location
    player = service.create_new_player("Gatherer")
    loc = repo.get_location(player.current_location_id)
    
    # 1. Add item to location manually (simulating generation)
    sword = Item(name="Rusty Sword", description="Old sword", item_type="weapon", value=10)
    loc.add_item(sword)
    repo.create_location(loc) # Update repo
    
    # 2. Look - See item
    msg, _, _ = service.process_command(player.id, "look")
    assert "Rusty Sword" in msg
    
    # 3. Take Item
    msg, p, l = service.process_command(player.id, "take Rusty Sword")
    assert "picked up Rusty Sword" in msg
    
    # Verify persistence
    updated_player = repo.get_player(player.id)
    updated_loc = repo.get_location(player.current_location_id)
    
    assert len(updated_player.inventory) == 1
    assert updated_player.inventory[0].name == "Rusty Sword"
    assert len(updated_loc.items) == 0
    
    # 4. Inventory
    msg, _, _ = service.process_command(player.id, "inventory")
    assert "Rusty Sword" in msg
    assert "weapon" in msg
    
    # 5. Drop Item
    msg, _, _ = service.process_command(player.id, "drop Rusty Sword")
    assert "dropped Rusty Sword" in msg
    
    # Verify persistence
    updated_player = repo.get_player(player.id)
    updated_loc = repo.get_location(player.current_location_id)
    
    assert len(updated_player.inventory) == 0
    assert len(updated_loc.items) == 1
    assert updated_loc.items[0].name == "Rusty Sword"

if __name__ == "__main__":
    test_inventory_flow()
