"""
CatchingStats entity representing catching statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.team import Team


@dataclass
class CatchingStats:
    """CatchingStats entity representing catching statistics for a baseball team in the MLB."""

    id: Optional[int]
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
        games_pitched: int = 0,
        at_bats: int = 0,
        hits: int = 0,
        runs: int = 0,
        home_runs: int = 0,
        strikeouts: int = 0,
        base_on_balls: int = 0,
        intentional_walks: int = 0,
        hit_by_pitch: int = 0,
        total_bases: int = 0,
        sacrifice_bunts: int = 0,
        sacrifice_flies: int = 0,
        batting_average: float = 0.0,
        on_base_percentage: float = 0.0,
        slugging_percentage: float = 0.0,
        ops: float = 0.0,
        passed_balls: int = 0,
        wild_pitches: int = 0,
        stolen_bases_allowed: int = 0,
        caught_stealing: int = 0,
        stolen_base_percentage: float = 0.0,
        pickoffs: int = 0,
        pickoff_attempts: int = 0,
        catchers_interference: int = 0,
        earned_runs: int = 0,
        batters_faced: int = 0,
        hit_batsmen: int = 0,
        strikeout_walk_ratio: float = 0.0,
    ) -> "CatchingStats":
        """Factory method to create a new CatchingStats entity."""
        return cls(
            id=None,
            team_id=team_id,
            season=season,
            games_played=games_played,
            games_pitched=games_pitched,
            at_bats=at_bats,
            hits=hits,
            runs=runs,
            home_runs=home_runs,
            strikeouts=strikeouts,
            base_on_balls=base_on_balls,
            intentional_walks=intentional_walks,
            hit_by_pitch=hit_by_pitch,
            total_bases=total_bases,
            sacrifice_bunts=sacrifice_bunts,
            sacrifice_flies=sacrifice_flies,
            batting_average=batting_average,
            on_base_percentage=on_base_percentage,
            slugging_percentage=slugging_percentage,
            ops=ops,
            passed_balls=passed_balls,
            wild_pitches=wild_pitches,
            stolen_bases_allowed=stolen_bases_allowed,
            caught_stealing=caught_stealing,
            stolen_base_percentage=stolen_base_percentage,
            pickoffs=pickoffs,
            pickoff_attempts=pickoff_attempts,
            catchers_interference=catchers_interference,
            earned_runs=earned_runs,
            batters_faced=batters_faced,
            hit_batsmen=hit_batsmen,
            strikeout_walk_ratio=strikeout_walk_ratio,
            created_at=datetime.now(),
            updated_at=datetime.now(),
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
