from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.item import Item, ItemType
from app.core.domain.enemy import Enemy
import uuid

def test_quest_lifecycle_and_turnin():
    repo = InMemoryGameRepository()
    service = GameService(repo)
    player, location = service.create_new_player("QuestHero")

    # 1. Accept quest via elder dialogue or quest command
    msg, p, _ = service.process_command(player.id, "talk Farmer Ted")
    assert "Giant vermin" in msg
    msg, p, _ = service.process_command(player.id, "dialogue 1") # What kind of vermin
    assert "Slay 3 of them" in msg
    assert "worried_farmer" in p.active_quests

    # 2. Check quest journal
    msg, _, _ = service.process_command(player.id, "quests")
    assert "The Worried Farmer" in msg
    assert "[ ] Eliminate 3 hostile monsters (0/3)" in msg

    # 3. Simulate killing cave spiders
    spider = Enemy(
        id=str(uuid.uuid4()),
        name="Cave Spider",
        description="A skittering cave spider",
        hp=5,
        max_hp=5,
        attack=1,
        xp_reward=10
    )
    location.enemies.append(spider)

    # Attack and kill spider 1
    msg, p, _ = service.attack_enemy(player.id, "Cave Spider")
    assert "(1/3)" in msg

    # Kill spider 2 and 3
    spider2 = Enemy(id=str(uuid.uuid4()), name="Cave Spider", description="sp2", hp=5, max_hp=5, attack=1, xp_reward=10)
    spider3 = Enemy(id=str(uuid.uuid4()), name="Cave Spider", description="sp3", hp=5, max_hp=5, attack=1, xp_reward=10)
    location.enemies.extend([spider2, spider3])
    
    service.attack_enemy(player.id, "Cave Spider")
    msg, p, _ = service.attack_enemy(player.id, "Cave Spider")
    assert "is ready to turn in" in msg

    # 4. Turn in quest
    start_gold = p.stats.gold
    msg, p, _ = service.process_command(player.id, "turnin worried_farmer")
    assert "*** QUEST COMPLETED: The Worried Farmer ***" in msg
    assert p.stats.gold == start_gold + 20 # 20g reward
    assert "worried_farmer" in p.completed_quests
    assert "worried_farmer" not in p.active_quests
    assert any(i.name == "Apple" for i in p.inventory)
