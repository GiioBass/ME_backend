from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, JSON
from app.core.domain.player import Player
from app.core.domain.location import Location, Coordinates
from app.core.domain.item import Item

class PlayerDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    current_location_id: str
    stats: Dict = Field(default={}, sa_type=JSON)
    inventory: List[dict] = Field(default=[], sa_type=JSON)

    def to_domain(self) -> Player:
        # Reconstruct Domain Player from DB Model
        # Note: Stats and Inventory need proper parsing if they are complex objects
        # For now, simplistic mapping
        p = Player(
            id=self.id,
            name=self.name,
            current_location_id=self.current_location_id,
            # stats=... we need to ensure Stats model can accept dict
            # inventory=... map dicts back to Items
        )
        # Manually set stats if needed, or rely on Pydantic
        if self.stats:
            for k, v in self.stats.items():
                setattr(p.stats, k, v)
        
        if self.inventory:
            p.inventory = [Item(**item_data) for item_data in self.inventory]
            
        return p

    @classmethod
    def from_domain(cls, player: Player) -> "PlayerDB":
        return cls(
            id=player.id,
            name=player.name,
            current_location_id=player.current_location_id,
            stats=player.stats.model_dump(),
            inventory=[item.model_dump() for item in player.inventory]
        )

class LocationDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: str
    exits: Dict = Field(default={}, sa_type=JSON)
    interactables: List[str] = Field(default=[], sa_type=JSON)
    items: List[dict] = Field(default=[], sa_type=JSON)
    coordinates: Optional[Dict] = Field(default=None, sa_type=JSON)

    def to_domain(self) -> Location:
        loc = Location(
            id=self.id,
            name=self.name,
            description=self.description,
            exits=self.exits,
            interactables=self.interactables,
            items=[Item(**i) for i in self.items]
        )
        if self.coordinates:
            loc.coordinates = Coordinates(**self.coordinates)
        return loc

    @classmethod
    def from_domain(cls, location: Location) -> "LocationDB":
        return cls(
            id=location.id,
            name=location.name,
            description=location.description,
            exits=location.exits,
            interactables=location.interactables,
            items=[item.model_dump() for item in location.items],
            coordinates=location.coordinates.model_dump() if location.coordinates else None
        )
