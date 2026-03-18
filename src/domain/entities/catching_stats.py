"""
CatchingStats entity representing catching statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime

from domain.entities.stats_factory import build_stats_payload
from domain.entities.team import Team


@dataclass
class CatchingStats:
    """CatchingStats entity representing catching statistics for a baseball team in the MLB."""

    id: int | None
    team_id: int
    season: int

    # Basic game stats
    games_played: int = 0
    games_pitched: int = 0

    # Offensive stats (catchers can bat)
    at_bats: int = 0
    hits: int = 0
    runs: int = 0
    home_runs: int = 0
    strikeouts: int = 0
    base_on_balls: int = 0
    intentional_walks: int = 0
    hit_by_pitch: int = 0
    total_bases: int = 0
    sacrifice_bunts: int = 0
    sacrifice_flies: int = 0

    # Batting averages and percentages
    batting_average: float = 0.0
    on_base_percentage: float = 0.0
    slugging_percentage: float = 0.0
    ops: float = 0.0

    # Catching-specific defensive stats
    passed_balls: int = 0
    wild_pitches: int = 0
    stolen_bases_allowed: int = 0
    caught_stealing: int = 0
    stolen_base_percentage: float = 0.0
    pickoffs: int = 0
    pickoff_attempts: int = 0
    catchers_interference: int = 0

    # Pitching stats (catchers may occasionally pitch)
    earned_runs: int = 0
    batters_faced: int = 0
    hit_batsmen: int = 0
    strikeout_walk_ratio: float = 0.0

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
    ) -> "CatchingStats":
        """Factory method to create a new CatchingStats entity."""
        now, payload = build_stats_payload(stats)
        return cls(
            id=None,
            team_id=team_id,
            season=season,
            created_at=now,
            updated_at=now,
            **payload,
        )

    def calculate_caught_stealing_percentage(self) -> float:
        """Calculate the caught stealing percentage."""
        total_attempts = self.caught_stealing + self.stolen_bases_allowed
        if total_attempts == 0:
            return 0.0
        return (self.caught_stealing / total_attempts) * 100.0

    def update_calculated_fields(self) -> None:
        """Update calculated fields based on raw statistics."""
        self.stolen_base_percentage = self.calculate_caught_stealing_percentage()

        # Calculate OPS if not provided
        if self.ops == 0.0 and (self.on_base_percentage > 0.0 or self.slugging_percentage > 0.0):
            self.ops = self.on_base_percentage + self.slugging_percentage
