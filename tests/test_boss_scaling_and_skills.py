import pytest
from app.core.use_cases.game_service import GameService
from app.adapters.driven.persistence.in_memory import InMemoryGameRepository
from app.core.domain.enemy import Enemy
from app.core.domain.player import Player

def test_boss_group_scaling():
    repo = InMemoryGameRepository()
    service = GameService(repo)

    p1, loc = service.create_new_player("Hero1")
    p2, _ = service.create_new_player("Hero2")
    p2.current_location_id = loc.id
    repo.save_player(p2)

    boss = Enemy(
        name="Monstrous Snow Golem",
        description="A frozen titan",
        hp=100,
        max_hp=100,
        attack=10,
        xp_reward=200,
        is_boss=True,
        skills=[
            {"name": "Glacial Avalanche", "damage": 25, "cooldown": 3, "desc": "avalanche"}
        ]
    )
    loc.add_enemy(boss)
    repo.create_location(loc)

    # When Hero1 attacks, boss scales for the 2 players present
    msg, updated_p1, updated_loc = service.combat_service.attack_enemy(p1.id, "Monstrous Snow Golem")
    assert "BOSS CHALLENGE" in msg or "power surges" in msg
    assert boss.max_hp > 100
    assert boss.attack > 10

def test_boss_skills_and_cooperative_xp():
    repo = InMemoryGameRepository()
    service = GameService(repo)

    p1, loc = service.create_new_player("Attacker")
    p2, _ = service.create_new_player("Ally")
    p2.current_location_id = loc.id
    repo.save_player(p2)

    boss = Enemy(
        name="Black Hound Sphinx",
        description="Desert boss",
        hp=2,
        max_hp=100,
        attack=10,
        xp_reward=150,
        is_boss=True,
        skills=[
            {"name": "Obsidian Sandstorm", "damage": 20, "cooldown": 2, "desc": "sandstorm"}
        ]
    )
    loc.add_enemy(boss)
    repo.create_location(loc)

    # Attack to kill the boss
    msg, updated_p1, updated_loc = service.combat_service.attack_enemy(p1.id, "Black Hound Sphinx")
    assert "collapses and dies" in msg
    assert "Cooperative Victory" in msg

    # Both players should have gained XP (and leveled up)
    reloaded_p2 = repo.get_player(p2.id)
    assert reloaded_p2.stats.level > 1 or reloaded_p2.stats.xp > 0

def test_mountain_dungeon_generation():
    repo = InMemoryGameRepository()
    service = GameService(repo)

    # Generate mountain floors
    floor1 = service.dungeon_gen.generate_mountain_floor(root_x=0, root_y=4, z=1)
    assert len(floor1) > 0
    assert any(l.id.startswith("mtn_0_4_1") for l in floor1)

    summit = service.dungeon_gen.generate_mountain_floor(root_x=0, root_y=4, z=3)
    assert len(summit) == 1
    assert summit[0].id == "mtn_0_4_3_summit"
    assert any(e.name == "Monstrous Snow Golem" for e in summit[0].enemies)
