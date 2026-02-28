"""
Team entity representing a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Team:
    """Team entity representing a baseball team in the MLB."""

    id: int | None
    mlb_id: int
    name: str
    abbreviation: str
    city: str
    division: str
    league: str
    venue_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        mlb_id: int,
        name: str,
        abbreviation: str,
        city: str,
        division: str,
        league: str,
        venue_name: str | None = None,
    ) -> "Team":
        """Factory method to create a new Team entity."""
        return cls(
            id=None,
            mlb_id=mlb_id,
            name=name,
            abbreviation=abbreviation,
            city=city,
            division=division,
            league=league,
            venue_name=venue_name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
