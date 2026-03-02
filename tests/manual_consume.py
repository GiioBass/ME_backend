from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.use_cases.game_service import GameService
from app.core.domain.item import Item, ItemType
import uuid

repo = SQLGameRepository()
service = GameService(repo)

player = repo.get_player_by_name("ScoxAleera")

if player:
    player.stats.hp = 50
    repo.save_player(player)

    apple = Item(
        id=str(uuid.uuid4()),
        name="Red Apple Test 2",
        description="A juicy red apple.",
        item_type=ItemType.CONSUMABLE,
        restore_hp=10,
        restore_thirst=15,
        restore_hunger=20
    )
    player.add_item(apple)
    repo.save_player(player)
    print(f"Before eating: HP={player.stats.hp}, Hunger={player.stats.hunger}")
    msg, p, loc = service.consume_item(player.id, "Red Apple Test 2")
    
    print(msg)
    print(f"After eating: HP={p.stats.hp}, Hunger={p.stats.hunger}")


    # check if "Red Apple Test 2" still exists in inventory.
    has_apple = any(item.name == "Red Apple Test 2" for item in p.inventory)
    print("Does player still have apple?", has_apple)

else:
    print("Player not found!")
