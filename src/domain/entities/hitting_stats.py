"""
HittingStats entity representing hitting statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.team import Team


@dataclass
class HittingStats:
    """HittingStats entity representing hitting statistics for a baseball team in the MLB."""

    id: Optional[int]
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
        at_bats: int = 0,
        plate_appearances: int = 0,
        hits: int = 0,
        doubles: int = 0,
        triples: int = 0,
        home_runs: int = 0,
        runs_scored: int = 0,
        runs_batted_in: int = 0,
        stolen_bases: int = 0,
        caught_stealing: int = 0,
        base_on_balls: int = 0,
        strikeouts: int = 0,
        hit_by_pitch: int = 0,
        sacrifice_hits: int = 0,
        sacrifice_flies: int = 0,
        ground_into_double_play: int = 0,
        left_on_base: int = 0,
        batting_average: float = 0.0,
        on_base_percentage: float = 0.0,
        slugging_percentage: float = 0.0,
        ops: float = 0.0,
        babip: float = 0.0,
        total_bases: int = 0,
        at_bats_per_home_run: float = 0.0,
        stolen_base_percentage: float = 0.0,
        ground_outs: int = 0,
        air_outs: int = 0,
        ground_outs_to_airouts: float = 0.0,
        number_of_pitches: int = 0,
        intentional_walks: int = 0,
    ) -> "HittingStats":
        """Factory method to create a new HittingStats entity."""
        return cls(
            id=None,
            team_id=team_id,
            season=season,
            games_played=games_played,
            at_bats=at_bats,
            plate_appearances=plate_appearances,
            hits=hits,
            doubles=doubles,
            triples=triples,
            home_runs=home_runs,
            runs_scored=runs_scored,
            runs_batted_in=runs_batted_in,
            stolen_bases=stolen_bases,
            caught_stealing=caught_stealing,
            base_on_balls=base_on_balls,
            strikeouts=strikeouts,
            hit_by_pitch=hit_by_pitch,
            sacrifice_hits=sacrifice_hits,
            sacrifice_flies=sacrifice_flies,
            ground_into_double_play=ground_into_double_play,
            left_on_base=left_on_base,
            batting_average=batting_average,
            on_base_percentage=on_base_percentage,
            slugging_percentage=slugging_percentage,
            ops=ops,
            babip=babip,
            total_bases=total_bases,
            at_bats_per_home_run=at_bats_per_home_run,
            stolen_base_percentage=stolen_base_percentage,
            ground_outs=ground_outs,
            air_outs=air_outs,
            ground_outs_to_airouts=ground_outs_to_airouts,
            number_of_pitches=number_of_pitches,
            intentional_walks=intentional_walks,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
