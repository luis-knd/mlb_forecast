"""
TeamStats entity representing statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.stats_factory import build_stats_payload
from src.domain.entities.team import Team


@dataclass
class TeamStats:
    """TeamStats entity representing statistics for a baseball team in the MLB."""

    id: int | None
    team_id: int
    season: int

    # Offensive stats
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    runs_scored: int = 0
    hits: int = 0
    home_runs: int = 0
    batting_average: float = 0.0
    on_base_percentage: float = 0.0
    slugging_percentage: float = 0.0
    ops: float = 0.0  # On-base Plus Slugging
    stolen_bases: int = 0

    # Pitching stats
    earned_run_average: float = 0.0
    whip: float = 0.0  # Walks plus Hits per Inning Pitched
    strikeouts_per_nine: float = 0.0
    walks_per_nine: float = 0.0
    home_runs_allowed: int = 0
    runs_allowed: int = 0

    # Defensive stats
    fielding_percentage: float = 0.0
    errors: int = 0
    double_plays: int = 0

    # Advanced metrics
    run_differential: int = 0
    pythagorean_expectation: float = 0.0  # Expected win percentage based on runs scored/allowed

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
    ) -> "TeamStats":
        """Factory method to create a new TeamStats entity."""
        now, payload = build_stats_payload(
            stats,
            extra_blocked_keys=frozenset({"run_differential", "pythagorean_expectation"}),
        )
        runs_scored = int(payload.get("runs_scored", 0) or 0)
        runs_allowed = int(payload.get("runs_allowed", 0) or 0)
        run_differential = runs_scored - runs_allowed
        pythagorean_expectation = cls._calculate_pythagorean_expectation(runs_scored, runs_allowed)

        return cls(
            id=None,
            team_id=team_id,
            season=season,
            run_differential=run_differential,
            pythagorean_expectation=pythagorean_expectation,
            created_at=now,
            updated_at=now,
            **payload,
        )

    def win_percentage(self) -> float:
        """Calculate the team's win percentage."""
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played

    def update_run_differential(self) -> None:
        """Update the run differential based on runs scored and allowed."""
        self.run_differential = self.runs_scored - self.runs_allowed

        # Update Pythagorean expectation
        self.pythagorean_expectation = self._calculate_pythagorean_expectation(self.runs_scored, self.runs_allowed)

    @staticmethod
    def _calculate_pythagorean_expectation(runs_scored: int, runs_allowed: int) -> float:
        """
        Calculate Pythagorean expectation based on runs scored and allowed.

        Formula: (runs_scored^2) / (runs_scored^2 + runs_allowed^2)
        Handles edge cases where runs_allowed is 0.
        """
        if runs_scored == 0 and runs_allowed == 0:
            return 0.0
        if runs_allowed == 0:
            return 1.0
        return (runs_scored**2) / (runs_scored**2 + runs_allowed**2)
