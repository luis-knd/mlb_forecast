"""
FieldingStats entity representing fielding statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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
        games_played: int = 0,
        games_started: int = 0,
        innings_played: float = 0.0,
        total_chances: int = 0,
        putouts: int = 0,
        assists: int = 0,
        errors: int = 0,
        throwing_errors: int = 0,
        double_plays: int = 0,
        triple_plays: int = 0,
        fielding_percentage: float = 0.0,
        defensive_efficiency_ratio: float = 0.0,
        range_factor_per_game: float = 0.0,
        range_factor_per_nine: float = 0.0,
        outfield_assists: int = 0,
        passed_balls: int = 0,
        wild_pitches: int = 0,
        stolen_bases_allowed: int = 0,
        caught_stealing: int = 0,
        stolen_base_percentage: float = 0.0,
        catchers_interference: int = 0,
        pickoffs: int = 0,
    ) -> "FieldingStats":
        """Factory method to create a new FieldingStats entity."""
        return cls(
            id=None,
            team_id=team_id,
            season=season,
            games_played=games_played,
            games_started=games_started,
            innings_played=innings_played,
            total_chances=total_chances,
            putouts=putouts,
            assists=assists,
            errors=errors,
            throwing_errors=throwing_errors,
            double_plays=double_plays,
            triple_plays=triple_plays,
            fielding_percentage=fielding_percentage,
            defensive_efficiency_ratio=defensive_efficiency_ratio,
            range_factor_per_game=range_factor_per_game,
            range_factor_per_nine=range_factor_per_nine,
            outfield_assists=outfield_assists,
            passed_balls=passed_balls,
            wild_pitches=wild_pitches,
            stolen_bases_allowed=stolen_bases_allowed,
            caught_stealing=caught_stealing,
            stolen_base_percentage=stolen_base_percentage,
            catchers_interference=catchers_interference,
            pickoffs=pickoffs,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
