"""
Game entity representing a baseball game in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.team import Team


@dataclass
class Game:
    """Game entity representing a baseball game in the MLB."""

    id: Optional[int]
    mlb_game_id: int
    home_team_id: int
    away_team_id: int
    game_date: datetime
    status: str  # scheduled, in_progress, completed, cancelled
    scheduled_innings: int = 9
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    winning_team_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # These are not stored but can be set for convenience
    home_team: Optional[Team] = None
    away_team: Optional[Team] = None
    winning_team: Optional[Team] = None

    @classmethod
    def create(
        cls,
        mlb_game_id: int,
        home_team_id: int,
        away_team_id: int,
        game_date: datetime,
        status: str,
        scheduled_innings: int = 9,
        home_score: Optional[int] = None,
        away_score: Optional[int] = None,
        winning_team_id: Optional[int] = None,
    ) -> "Game":
        """Factory method to create a new Game entity."""
        return cls(
            id=None,
            mlb_game_id=mlb_game_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            game_date=game_date,
            status=status,
            scheduled_innings=scheduled_innings,
            home_score=home_score,
            away_score=away_score,
            winning_team_id=winning_team_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def is_completed(self) -> bool:
        """Check if the game is completed."""
        return self.status == "completed"

    def get_winner(self) -> Optional[int]:
        """Get the ID of the winning team, if the game is completed."""
        if not self.is_completed() or self.home_score is None or self.away_score is None:
            return None

        if self.home_score > self.away_score:
            return self.home_team_id
        elif self.away_score > self.home_score:
            return self.away_team_id

        return None  # Tie game
