"""
PitchingStats entity representing pitching statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime

from domain.entities.stats_factory import build_stats_payload
from domain.entities.team import Team


@dataclass
class PitchingStats:
    """PitchingStats entity representing pitching statistics for a baseball team in the MLB."""

    id: int | None
    team_id: int
    season: int

    # Basic stats
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    saves: int = 0
    save_opportunities: int = 0
    holds: int = 0
    blown_saves: int = 0
    innings_pitched: float = 0.0
    batters_faced: int = 0
    hits_allowed: int = 0
    runs_allowed: int = 0
    earned_runs: int = 0
    home_runs_allowed: int = 0
    strikeouts: int = 0
    base_on_balls: int = 0
    intentional_walks: int = 0
    hit_batsmen: int = 0
    wild_pitches: int = 0
    balks: int = 0
    number_of_pitches: int = 0
    complete_games: int = 0
    shutouts: int = 0
    games_started: int = 0
    ground_outs: int = 0
    air_outs: int = 0

    # Additional basic stats from MLB API
    doubles: int = 0
    triples: int = 0
    at_bats: int = 0
    outs: int = 0
    strikes: int = 0
    pickoffs: int = 0
    total_bases: int = 0
    games_finished: int = 0
    catchers_interference: int = 0
    sacrifice_bunts: int = 0
    sacrifice_flies: int = 0
    ground_into_double_play: int = 0
    caught_stealing: int = 0

    # Advanced stats
    earned_run_average: float = 0.0
    whip: float = 0.0  # Walks plus Hits per Inning Pitched
    strikeouts_per_nine: float = 0.0
    walks_per_nine: float = 0.0
    hits_per_nine: float = 0.0
    home_runs_per_nine: float = 0.0
    strikeout_to_walk_ratio: float = 0.0
    ground_outs_to_airouts: float = 0.0
    pitches_per_inning: float = 0.0
    batting_average_against: float = 0.0
    inherited_runners: int = 0
    inherited_runners_scored: int = 0
    quality_starts: int = 0

    # Additional advanced stats from MLB API
    on_base_percentage: float = 0.0  # obp
    slugging_percentage: float = 0.0  # slg
    ops: float = 0.0  # On-base Plus Slugging
    stolen_base_percentage: float = 0.0
    strike_percentage: float = 0.0
    win_percentage: float = 0.0
    runs_scored_per_nine: float = 0.0

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
    ) -> "PitchingStats":
        """Factory method to create a new PitchingStats entity."""
        now, payload = build_stats_payload(stats)
        return cls(
            id=None,
            team_id=team_id,
            season=season,
            created_at=now,
            updated_at=now,
            **payload,
        )
