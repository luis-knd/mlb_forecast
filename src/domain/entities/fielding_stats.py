"""
FieldingStats entity representing fielding statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.stats_factory import build_stats_payload
from src.domain.entities.team import Team


@dataclass
class FieldingStats:
    """FieldingStats entity representing fielding statistics for a baseball team in the MLB."""

    id: Optional[int]
    team_id: int
    season: int

    # Basic stats
    games_played: int = 0
    games_started: int = 0
    innings_played: float = 0.0
    total_chances: int = 0
    putouts: int = 0
    assists: int = 0
    errors: int = 0
    throwing_errors: int = 0
    double_plays: int = 0
    triple_plays: int = 0
    fielding_percentage: float = 0.0
    defensive_efficiency_ratio: float = 0.0
    range_factor_per_game: float = 0.0
    range_factor_per_nine: float = 0.0
    outfield_assists: int = 0
    passed_balls: int = 0
    wild_pitches: int = 0
    stolen_bases_allowed: int = 0
    caught_stealing: int = 0
    stolen_base_percentage: float = 0.0
    catchers_interference: int = 0
    pickoffs: int = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # This is not stored but can be set for convenience
    team: Optional[Team] = None

    @classmethod
    def create(
        cls,
        team_id: int,
        season: int,
        **stats: int | float,
    ) -> "FieldingStats":
        """Factory method to create a new FieldingStats entity."""
        now, payload = build_stats_payload(stats)
        return cls(
            id=None,
            team_id=team_id,
            season=season,
            created_at=now,
            updated_at=now,
            **payload,
        )
