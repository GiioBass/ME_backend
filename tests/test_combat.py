import pytest
from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.core.domain.enemy import Enemy

def test_combat_flow():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    
    # 1. Setup Player & Location
    player, _ = service.create_new_player("Warrior")
    loc = repo.get_location(player.current_location_id)
    
    # 2. Add Enemy Manually
    goblin = Enemy(name="Goblin", description="Nasty", hp=10, max_hp=10, attack=2, xp_reward=50)
    loc.add_enemy(goblin)
    repo.create_location(loc)
    
    # 3. Look - See enemy
    msg, _, _ = service.process_command(player.id, "look")
    assert "Goblin" in msg
    
    # 4. Attack Enemy (First Hit)
    # Player strength 10 -> damage 5. Enemy HP 10 -> 5.
    msg, p, l = service.process_command(player.id, "attack Goblin")
    assert "hit Goblin for 5" in msg
    assert "Goblin retaliates for" in msg
    
    # Check Persistence
    updated_loc = repo.get_location(player.current_location_id)
    assert len(updated_loc.enemies) == 1
    assert updated_loc.enemies[0].hp == 5
    
    # 5. Kill Enemy
    msg, p, l = service.process_command(player.id, "attack Goblin")
    assert "Goblin collapses and dies" in msg
    assert "gain 50 XP" in msg
    
    # Check Enemy Removal & XP
    updated_player = repo.get_player(player.id)
    updated_loc = repo.get_location(player.current_location_id)
    
    assert len(updated_loc.enemies) == 0
    assert updated_player.stats.xp == 50

def test_player_death():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, _ = service.create_new_player("Victim")
    loc = repo.get_location(player.current_location_id)
    
    # Boss Enemy
    boss = Enemy(name="Dragon", description="Huge", hp=100, max_hp=100, attack=200, xp_reward=1000)
    loc.add_enemy(boss)
    repo.create_location(loc)
    
    # Verify Start Location
    start_id = player.current_location_id
    
    # Attack -> Boss hits back -> instant death
    msg, p, l = service.process_command(player.id, "attack Dragon")
    
    assert "defeated" in msg
    assert "wake up back at the start" in msg
    
    # Verify Respawn (Full HP, same location or start?)
    # Logic says: loc_0_0_0 hardcoded.
    updated_player = repo.get_player(player.id)
    assert updated_player.stats.hp == updated_player.stats.max_hp
    assert updated_player.current_location_id == "loc_0_0_0"

if __name__ == "__main__":
    test_combat_flow()
    test_player_death()
