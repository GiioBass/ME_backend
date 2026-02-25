from sqlmodel import Session, select
from app.adapters.driven.persistence.db_config import engine
from app.adapters.driven.persistence.sql_models import LocationDB

with Session(engine) as session:
    locs = session.exec(select(LocationDB)).all()
    print(f"Total Locs: {len(locs)}")
    for loc in locs:
        if loc.id == "loc_2_2_0" or loc.id == "loc_1_4_0":
            print(loc.id, loc.name, loc.coordinates)
