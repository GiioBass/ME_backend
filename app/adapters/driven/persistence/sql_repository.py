from typing import Optional
from sqlmodel import Session, select
from app.ports.repositories import GameRepository
from app.core.domain.player import Player
from app.core.domain.location import Location
from app.adapters.driven.persistence.sql_models import PlayerDB, LocationDB
from app.adapters.driven.persistence.db_config import engine

class SQLGameRepository(GameRepository):
    def get_player(self, player_id: str) -> Optional[Player]:
        with Session(engine) as session:
            player_db = session.get(PlayerDB, player_id)
            if player_db:
                return player_db.to_domain()
            return None

    def get_player_by_name(self, name: str) -> Optional[Player]:
        with Session(engine) as session:
            statement = select(PlayerDB).where(PlayerDB.name == name)
            player_db = session.exec(statement).first()
            if player_db:
                return player_db.to_domain()
            return None

    def save_player(self, player: Player) -> Player:
        with Session(engine) as session:
            # Check if exists to update, or just merge
            # sqlmodel merge is tricky with non-ORM objects, but we have PlayerDB
            player_db = PlayerDB.from_domain(player)
            session.merge(player_db)
            session.commit()
            return player

    def get_location(self, location_id: str) -> Optional[Location]:
        with Session(engine) as session:
            loc_db = session.get(LocationDB, location_id)
            if loc_db:
                return loc_db.to_domain()
            return None
    
    def create_location(self, location: Location) -> Location:
        with Session(engine) as session:
            loc_db = LocationDB.from_domain(location)
            session.merge(loc_db) # Use merge to handle potential duplicates if we regenerate?
            session.commit()
            return location

    def get_location_by_coordinates(self, x: int, y: int, z: int) -> Optional[Location]:
        with Session(engine) as session:
            # This is tricky with JSON fields in SQLite/SQLModel without specific extensions
            # But since we are using python, we can fetch all (bad perf) or use a filter if we used separate columns.
            # OPTIMIZATION: We should probably promote x,y,z to real columns in LocationDB instead of JSON.
            # For now, let's try to filter using simple python logic if the DB is small, 
            # OR better: Add columns to LocationDB?
            # User didn't ask for schema migration, but for "Infinite Gen".
            # Let's add columns to LocationDB to make this efficient.
            pass
            # Wait, I can't easily change schema without dropping DB (which is fine for now).
            
        with Session(engine) as session:
            # Alternative: Load all locations and filter. (Prototyping)
            locs = session.exec(select(LocationDB)).all()
            for loc in locs:
                if loc.coordinates:
                    # loc.coordinates is a Dict from JSON
                    if loc.coordinates.get("x") == x and loc.coordinates.get("y") == y and loc.coordinates.get("z") == z:
                        return loc.to_domain()
            return None

    def get_locations_in_radius(self, x: int, y: int, z: int, radius: int) -> list[Location]:
        with Session(engine) as session:
            locs = session.exec(select(LocationDB)).all()
            results = []
            for loc in locs:
                if loc.coordinates:
                    lx = loc.coordinates.get("x")
                    ly = loc.coordinates.get("y")
                    lz = loc.coordinates.get("z")
                    if lz == z and lx is not None and ly is not None:
                        # Simple Chebyshev distance for grid/chunks
                        if abs(lx - x) <= radius and abs(ly - y) <= radius:
                            # Exclude self
                            if lx == x and ly == y:
                                continue
                            results.append(loc.to_domain())
            return results

    def get_world_time(self):
        from app.core.domain.time_system import WorldTime
        from app.adapters.driven.persistence.sql_models import WorldStateDB
        
        with Session(engine) as session:
            state = session.get(WorldStateDB, "world_state")
            if not state:
                return WorldTime(total_ticks=0)
            return WorldTime(total_ticks=state.total_ticks)

    def save_world_time(self, world_time):
        from app.adapters.driven.persistence.sql_models import WorldStateDB
        
        with Session(engine) as session:
            state = WorldStateDB(id="world_state", total_ticks=world_time.total_ticks)
            session.merge(state)
            session.commit()
