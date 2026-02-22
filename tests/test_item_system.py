import pytest
from app.core.domain.item import Item
from app.core.domain.player import Player
from app.core.domain.location import Location, Coordinates
from app.core.use_cases.command_parser import CommandParser
from app.adapters.driven.persistence.sql_models import PlayerDB, LocationDB

def test_item_flow():
    # Setup
    loc = Location(id="loc1", name="Room", description="A room", coordinates=Coordinates(x=0,y=0))
    sword = Item(name="Sword", description="Sharp", item_type="weapon", value=10)
    loc.add_item(sword)
    
    player = Player(id="p1", name="Hero", current_location_id="loc1")
    
    parser = CommandParser()
    
    # Mock WorldTime
    wt = None
    
    # 1. Look (should see item)
    res = parser.parse("look", player, loc, wt, lambda p: None)
    assert "Sword" in res.message
    
    # 2. Take Item
    # Mock save callbacks
    saved_player = None
    saved_loc = None
    def save_p(p): nonlocal saved_player; saved_player = p
    def save_l(l): nonlocal saved_loc; saved_loc = l
    
    res = parser.parse("take Sword", player, loc, wt, save_p, save_l)
    
    assert "picked up Sword" in res.message
    assert len(player.inventory) == 1
    assert player.inventory[0].name == "Sword"
    assert len(loc.items) == 0
    
    # Verify persistence triggers
    assert saved_player is not None
    assert saved_loc is not None
        
    # 3. Inventory
    res = parser.parse("inventory", player, loc, wt, lambda p: None)
    assert "Sword" in res.message
    
    # 4. Drop Item
    res = parser.parse("drop Sword", player, loc, wt, save_p, save_l)
    assert "dropped Sword" in res.message
    assert len(player.inventory) == 0
    assert len(loc.items) == 1
    assert loc.items[0].name == "Sword"

def test_inventory_grouping():
    # Setup
    loc = Location(id="loc1", name="Room", description="A room", coordinates=Coordinates(x=0,y=0))
    player = Player(id="p2", name="Hoarder", current_location_id="loc1")
    parser = CommandParser()
    wt = None
    
    # Add 2 Swords of same name
    from app.core.domain.item import Item # Ensure Item is imported if not at top level
    
    sword1 = Item(name="Sword", description="Sharp", item_type="weapon", value=10)
    sword2 = Item(name="Sword", description="Dull", item_type="weapon", value=5)
    player.add_item(sword1)
    player.add_item(sword2)
    
    res = parser.parse("inventory", player, loc, wt, lambda p: None)
    assert "Sword (weapon) x2" in res.message

def test_persistence_serialization():
    # Verify that Item objects survive DB roundtrip via Pydantic/SQLModel
    sword = Item(name="Sword", description="Sharp", item_type="weapon", value=10)
    player = Player(name="Hero", current_location_id="loc1")
    player.add_item(sword)
    
    # To DB Model
    player_db = PlayerDB.from_domain(player)
    # Using dict access for inventory list of dicts
    # inventory is List[dict] in DB model
    # Wait, lets check if the previous test was correct. Yes it checked ['name']
    assert player_db.inventory[0]["name"] == "Sword"
    
    # Back to Domain
    player_restored = player_db.to_domain()
    assert len(player_restored.inventory) == 1
    assert isinstance(player_restored.inventory[0], Item)
    assert player_restored.inventory[0].name == "Sword"
