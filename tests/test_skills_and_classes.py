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

    # Cast Heavy Strike (costs 10 energy)
    msg, p, loc = service.process_command(player.id, "skill Heavy Strike")
    assert "You cast [Heavy Strike]" in msg
    assert loc.enemies[0].hp < 50
    assert p.stats.hp < start_hp # Energy cost or retaliation
