import asyncio
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.domain.location import Location, Coordinates
from app.core.use_cases.game_service import GameService

repo = SQLGameRepository()
service = GameService(repo)

# 1. Start or get player
try:
    player, _ = service.login_player("TestScout")
except ValueError:
    player = service.create_new_player("TestScout")

player.current_location_id = "loc_0_0_0"
repo.save_player(player)

# Create a Dungeon 3 chunks North, 2 chunks East (dy=3, dx=2 implies 3 chunks distance max)
dungeon = Location(id="loc_2_3_0", name="Forgotten Crypt", description="A scary place", coordinates=Coordinates(x=2, y=3, z=0))
repo.create_location(dungeon)

# Create a generic forest that shouldn't show up
forest = Location(id="loc_1_1_0", name="Forest Area 1,1", description="Trees", coordinates=Coordinates(x=1, y=1, z=0))
repo.create_location(forest)

# Run scout
msg, _, _ = service.scout_area(player.id)
print("Scout Result:\n", msg)
