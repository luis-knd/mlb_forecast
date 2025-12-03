"""
Player entity representing a baseball player in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.team import Team


@dataclass
class Player:
    """Player entity representing a baseball player in the MLB."""

    id: Optional[int]
    mlb_id: int
    first_name: str
    last_name: str
    position: str
    bats: Optional[str] = None  # L, R, S (switch)
    throws: Optional[str] = None  # L, R
    birth_date: Optional[datetime] = None
    active: bool = True
    current_team_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # This is not stored but can be set for convenience
    current_team: Optional[Team] = None

    @classmethod
    def create(
        cls,
        mlb_id: int,
        first_name: str,
        last_name: str,
        position: str,
        bats: Optional[str] = None,
        throws: Optional[str] = None,
        birth_date: Optional[datetime] = None,
        active: bool = True,
        current_team_id: Optional[int] = None,
    ) -> "Player":
        """Factory method to create a new Player entity."""
        return cls(
            id=None,
            mlb_id=mlb_id,
            first_name=first_name,
            last_name=last_name,
            position=position,
            bats=bats,
            throws=throws,
            birth_date=birth_date,
            active=active,
            current_team_id=current_team_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def full_name(self) -> str:
        """Get the player's full name."""
        return f"{self.first_name} {self.last_name}"

    def is_pitcher(self) -> bool:
        """Check if the player is a pitcher."""
        return self.position.lower() in ["p", "pitcher"]

    def is_batter(self) -> bool:
        """Check if the player is a batter (non-pitcher)."""
        return not self.is_pitcher()
