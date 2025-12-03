"""
TeamStats entity representing statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.team import Team


@dataclass
class TeamStats:
    """TeamStats entity representing statistics for a baseball team in the MLB."""

    id: Optional[int]
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

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # This is not stored but can be set for convenience
    team: Optional[Team] = None

    @classmethod
    def create(
        cls,
        team_id: int,
        season: int,
        games_played: int = 0,
        wins: int = 0,
        losses: int = 0,
        runs_scored: int = 0,
        hits: int = 0,
        home_runs: int = 0,
        batting_average: float = 0.0,
        on_base_percentage: float = 0.0,
        slugging_percentage: float = 0.0,
        ops: float = 0.0,
        stolen_bases: int = 0,
        earned_run_average: float = 0.0,
        whip: float = 0.0,
        strikeouts_per_nine: float = 0.0,
        walks_per_nine: float = 0.0,
        home_runs_allowed: int = 0,
        runs_allowed: int = 0,
        fielding_percentage: float = 0.0,
        errors: int = 0,
        double_plays: int = 0,
    ) -> "TeamStats":
        """Factory method to create a new TeamStats entity."""
        run_differential = runs_scored - runs_allowed

        # Simple Pythagorean expectation formula
        pythagorean_expectation = 0.0
        if runs_scored > 0 and runs_allowed > 0:
            pythagorean_expectation = (runs_scored**2) / (runs_scored**2 + runs_allowed**2)

        return cls(
            id=None,
            team_id=team_id,
            season=season,
            games_played=games_played,
            wins=wins,
            losses=losses,
            runs_scored=runs_scored,
            hits=hits,
            home_runs=home_runs,
            batting_average=batting_average,
            on_base_percentage=on_base_percentage,
            slugging_percentage=slugging_percentage,
            ops=ops,
            stolen_bases=stolen_bases,
            earned_run_average=earned_run_average,
            whip=whip,
            strikeouts_per_nine=strikeouts_per_nine,
            walks_per_nine=walks_per_nine,
            home_runs_allowed=home_runs_allowed,
            runs_allowed=runs_allowed,
            fielding_percentage=fielding_percentage,
            errors=errors,
            double_plays=double_plays,
            run_differential=run_differential,
            pythagorean_expectation=pythagorean_expectation,
            created_at=datetime.now(),
            updated_at=datetime.now(),
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
        if self.runs_scored > 0 and self.runs_allowed > 0:
            self.pythagorean_expectation = (self.runs_scored**2) / (self.runs_scored**2 + self.runs_allowed**2)
        else:
            self.pythagorean_expectation = 0.0
