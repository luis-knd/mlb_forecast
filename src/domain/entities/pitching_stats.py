"""
PitchingStats entity representing pitching statistics for a baseball team in the MLB.
This is a pure domain entity without any framework dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.team import Team


@dataclass
class PitchingStats:
    """PitchingStats entity representing pitching statistics for a baseball team in the MLB."""

    id: Optional[int]
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
        saves: int = 0,
        save_opportunities: int = 0,
        holds: int = 0,
        blown_saves: int = 0,
        innings_pitched: float = 0.0,
        batters_faced: int = 0,
        hits_allowed: int = 0,
        runs_allowed: int = 0,
        earned_runs: int = 0,
        home_runs_allowed: int = 0,
        strikeouts: int = 0,
        base_on_balls: int = 0,
        intentional_walks: int = 0,
        hit_batsmen: int = 0,
        wild_pitches: int = 0,
        balks: int = 0,
        number_of_pitches: int = 0,
        complete_games: int = 0,
        shutouts: int = 0,
        games_started: int = 0,
        ground_outs: int = 0,
        air_outs: int = 0,
        earned_run_average: float = 0.0,
        whip: float = 0.0,
        strikeouts_per_nine: float = 0.0,
        walks_per_nine: float = 0.0,
        hits_per_nine: float = 0.0,
        home_runs_per_nine: float = 0.0,
        strikeout_to_walk_ratio: float = 0.0,
        ground_outs_to_airouts: float = 0.0,
        pitches_per_inning: float = 0.0,
        batting_average_against: float = 0.0,
        inherited_runners: int = 0,
        inherited_runners_scored: int = 0,
        quality_starts: int = 0,
        doubles: int = 0,
        triples: int = 0,
        at_bats: int = 0,
        outs: int = 0,
        strikes: int = 0,
        pickoffs: int = 0,
        total_bases: int = 0,
        games_finished: int = 0,
        catchers_interference: int = 0,
        sacrifice_bunts: int = 0,
        sacrifice_flies: int = 0,
        ground_into_double_play: int = 0,
        caught_stealing: int = 0,
        on_base_percentage: float = 0.0,
        slugging_percentage: float = 0.0,
        ops: float = 0.0,
        stolen_base_percentage: float = 0.0,
        strike_percentage: float = 0.0,
        win_percentage: float = 0.0,
        runs_scored_per_nine: float = 0.0,
    ) -> "PitchingStats":
        """Factory method to create a new PitchingStats entity."""
        return cls(
            id=None,
            team_id=team_id,
            season=season,
            games_played=games_played,
            wins=wins,
            losses=losses,
            saves=saves,
            save_opportunities=save_opportunities,
            holds=holds,
            blown_saves=blown_saves,
            innings_pitched=innings_pitched,
            batters_faced=batters_faced,
            hits_allowed=hits_allowed,
            runs_allowed=runs_allowed,
            earned_runs=earned_runs,
            home_runs_allowed=home_runs_allowed,
            strikeouts=strikeouts,
            base_on_balls=base_on_balls,
            intentional_walks=intentional_walks,
            hit_batsmen=hit_batsmen,
            wild_pitches=wild_pitches,
            balks=balks,
            number_of_pitches=number_of_pitches,
            complete_games=complete_games,
            shutouts=shutouts,
            games_started=games_started,
            ground_outs=ground_outs,
            air_outs=air_outs,
            earned_run_average=earned_run_average,
            whip=whip,
            strikeouts_per_nine=strikeouts_per_nine,
            walks_per_nine=walks_per_nine,
            hits_per_nine=hits_per_nine,
            home_runs_per_nine=home_runs_per_nine,
            strikeout_to_walk_ratio=strikeout_to_walk_ratio,
            ground_outs_to_airouts=ground_outs_to_airouts,
            pitches_per_inning=pitches_per_inning,
            batting_average_against=batting_average_against,
            inherited_runners=inherited_runners,
            inherited_runners_scored=inherited_runners_scored,
            quality_starts=quality_starts,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            doubles=doubles,
            triples=triples,
            at_bats=at_bats,
            outs=outs,
            strikes=strikes,
            pickoffs=pickoffs,
            total_bases=total_bases,
            games_finished=games_finished,
            catchers_interference=catchers_interference,
            sacrifice_bunts=sacrifice_bunts,
            sacrifice_flies=sacrifice_flies,
            ground_into_double_play=ground_into_double_play,
            caught_stealing=caught_stealing,
            on_base_percentage=on_base_percentage,
            slugging_percentage=slugging_percentage,
            ops=ops,
            stolen_base_percentage=stolen_base_percentage,
            strike_percentage=strike_percentage,
            win_percentage=win_percentage,
            runs_scored_per_nine=runs_scored_per_nine,
        )
