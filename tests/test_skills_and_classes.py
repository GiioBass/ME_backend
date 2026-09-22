from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.enemy import Enemy
import uuid

def test_class_selection_and_skills():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, _ = service.create_new_player("MageHero")
    assert player.stats.character_class == "adventurer"

    # 1. Select Mage class
    msg, p, _ = service.process_command(player.id, "class mage")
    assert "You are now a Mage" in msg
    assert p.stats.character_class == "mage"
    assert "Fireball" in p.skills

    # 2. View Skills
    msg, _, _ = service.process_command(player.id, "skills")
    assert "Fireball" in msg
    assert "20 MP" in msg

def test_skill_combat_execution():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, location = service.create_new_player("FighterHero", character_class="fighter")
    assert "Heavy Strike" in player.skills
    start_hp = player.stats.hp

    # Add enemy
    goblin = Enemy(
        id=str(uuid.uuid4()),
        name="Goblin Raider",
        description="A fierce goblin",
        hp=50,
        max_hp=50,
        attack=5,
        xp_reward=20
    )
    location.enemies.append(goblin)

    # Cast Heavy Strike (costs 10 MP)
    start_mp = player.stats.mp
    msg, p, loc = service.process_command(player.id, "skill Heavy Strike")
    assert "You cast [Heavy Strike]" in msg
    assert loc.enemies[0].hp < 50
    assert p.stats.mp < start_mp # MP cost deducted

def test_free_skill_cooldown_and_alternation():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, location = service.create_new_player("AdventurerHero", character_class="adventurer")
    
    goblin = Enemy(
        id=str(uuid.uuid4()),
        name="Training Dummy",
        description="A training dummy",
        hp=100,
        max_hp=100,
        attack=1,
        xp_reward=10
    )
    location.enemies.append(goblin)
    repo.create_location(location)
    
    # 1. Cast Slash first time -> succeeds and triggers cooldown
    msg, p, loc = service.process_command(player.id, "skill Slash Training Dummy")
    assert "You cast [Slash]" in msg
    assert p.skill_cooldowns.get("slash", 0) > 0
    
    # 2. Cast Slash immediately second time -> rejected due to cooldown / alternation
    msg_fail, p2, _ = service.process_command(player.id, "skill Slash Training Dummy")
    assert "is on cooldown" in msg_fail
    
    # 3. Perform a basic attack -> hits and recharges tactical stance
    msg_atk, p3, _ = service.process_command(player.id, "attack Training Dummy")
    assert "You strike Training Dummy" in msg_atk
    assert p3.skill_cooldowns.get("slash", 0) == 0
    
    # 4. Cast Slash again -> succeeds now that it has recharged
    msg_success, p4, _ = service.process_command(player.id, "skill Slash Training Dummy")
    assert "You cast [Slash]" in msg_success

