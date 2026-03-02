from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.adapters.driving.api.routes import get_available_actions, serialize_player

repo = SQLGameRepository()
player = repo.get_player_by_name("ScoxAleera")

if player:
    print(f"Player ID: {player.id}")
    serialized_player = serialize_player(player)
    actions = get_available_actions(serialized_player, None)
    print(f"ACTIONS: {actions}")
else:
    print("Player not found!")
