import asyncio
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.domain.item import Item
from app.core.use_cases.game_service import GameService

repo = SQLGameRepository()
service = GameService(repo)

# 1. Start or get player
player, loc = service.login_player("TestHero")

# 2. Create a test weapon and add to inventory
sword = Item(name="Iron Sword", description="A rusty iron sword.", item_type="weapon", equip_slot="weapon", stat_bonuses={"strength": 5})
player.add_item(sword)
repo.save_player(player)

print("Pre-equip Inventory:", [i.name for i in player.inventory])
print("Pre-equip Weapon:", player.equipment.get("weapon").name if player.equipment.get("weapon") else "None")

# 3. Equip it via service
msg, p, l = service.equip_item(player.id, "Iron Sword")
print("Response:", msg)
print("Post-equip Inventory:", [i.name for i in p.inventory])
print("Post-equip Weapon:", p.equipment.get("weapon").name if p.equipment.get("weapon") else "None")

# 4. Check attack damage
print("Testing Attack damage multiplier...")
# We will spawn a dummy enemy
from app.core.domain.enemy import Enemy
dummy = Enemy(name="Target Dummy", hp=100, max_hp=100, attack=0, xp_reward=0)
l.add_enemy(dummy)
repo.create_location(l)

msg, p, l = service.attack_enemy(player.id, "Target Dummy")
print("Attack Result:", msg)

