"""
HittingStats entity representing hitting statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.stats_factory import build_stats_payload
from src.domain.entities.team import Team


@dataclass
class HittingStats:
    """HittingStats entity representing hitting statistics for a baseball team in the MLB."""

    id: int | None
    team_id: int
    season: int

    # Basic stats
    games_played: int = 0
    at_bats: int = 0
    plate_appearances: int = 0
    hits: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    runs_scored: int = 0
    runs_batted_in: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    base_on_balls: int = 0
    strikeouts: int = 0
    hit_by_pitch: int = 0
    sacrifice_hits: int = 0
    sacrifice_flies: int = 0
    ground_into_double_play: int = 0
    left_on_base: int = 0

    # Advanced stats
    batting_average: float = 0.0
    on_base_percentage: float = 0.0
    slugging_percentage: float = 0.0
    ops: float = 0.0  # On-base Plus Slugging
    babip: float = 0.0  # Batting Average on Balls In Play
    total_bases: int = 0
    at_bats_per_home_run: float = 0.0
    stolen_base_percentage: float = 0.0

    # Additional stats
    ground_outs: int = 0
    air_outs: int = 0
    ground_outs_to_airouts: float = 0.0
    number_of_pitches: int = 0
    intentional_walks: int = 0

    created_at: datetime | None = None
    updated_at: datetime | None = None

    # This is not stored but can be set for convenience
    team: Team | None = None

    @classmethod
    def create(
        cls,
        team_id: int,
        season: int,
        **stats: int | float,
    ) -> "HittingStats":
        """Factory method to create a new HittingStats entity."""
        now, payload = build_stats_payload(stats)
        return cls(
            id=None,
            team_id=team_id,
            season=season,
            created_at=now,
            updated_at=now,
            **payload,
        )
