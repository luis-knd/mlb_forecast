"""
Implementation of the PitchingStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.pitching_stats_repository import PitchingStatsRepositoryPort
from src.domain.entities.pitching_stats import PitchingStats
from src.domain.entities.team import Team
from src.infrastructure.db.models import PitchingStatsModel


class PitchingStatsRepository(PitchingStatsRepositoryPort):
    """Implementation of the PitchingStatsRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, stats_id: int) -> Optional[PitchingStats]:
        """Get pitching statistics by its ID."""
        stats_model = (
            self.session.query(PitchingStatsModel)
            .options(joinedload(PitchingStatsModel.team))
            .filter(PitchingStatsModel.id == stats_id)
            .first()
        )
        if not stats_model:
            return None
        return self._model_to_entity(stats_model)

    async def get_by_team_and_season(self, team_id: int, season: int) -> Optional[PitchingStats]:
        """Get pitching statistics by team ID and season."""
        stats_model = (
            self.session.query(PitchingStatsModel)
            .options(joinedload(PitchingStatsModel.team))
            .filter(
                PitchingStatsModel.team_id == team_id,
                PitchingStatsModel.season == season,
            )
            .first()
        )
        if not stats_model:
            return None
        return self._model_to_entity(stats_model)

    async def list_by_team(self, team_id: int) -> List[PitchingStats]:
        """List all pitching statistics for a specific team across seasons."""
        stats_models = (
            self.session.query(PitchingStatsModel)
            .options(joinedload(PitchingStatsModel.team))
            .filter(PitchingStatsModel.team_id == team_id)
            .order_by(PitchingStatsModel.season.desc())
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_by_season(self, season: int) -> List[PitchingStats]:
        """List pitching statistics for all teams in a specific season."""
        stats_models = (
            self.session.query(PitchingStatsModel)
            .options(joinedload(PitchingStatsModel.team))
            .filter(PitchingStatsModel.season == season)
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> List[PitchingStats]:
        """List top teams by a specific pitching statistic."""
        # Validate that the stat_name is a valid column
        if not hasattr(PitchingStatsModel, stat_name):
            return []

        # Get the column to sort by
        stat_column = getattr(PitchingStatsModel, stat_name)

        # Determine sort order
        order_func = desc if descending else asc

        stats_models = (
            self.session.query(PitchingStatsModel)
            .options(joinedload(PitchingStatsModel.team))
            .filter(PitchingStatsModel.season == season)
            .order_by(order_func(stat_column))
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def save(self, pitching_stats: PitchingStats) -> PitchingStats:
        """Save pitching statistics (create or update)."""
        # Check if pitching stats already exists
        if pitching_stats.id:
            stats_model = (
                self.session.query(PitchingStatsModel).filter(PitchingStatsModel.id == pitching_stats.id).first()
            )
            if stats_model:
                # Update existing pitching stats
                self._update_stats_model(stats_model, pitching_stats)
                self.session.commit()
                return await self.get_by_id(stats_model.id)

        # Check if pitching stats exists by team_id and season
        stats_model = (
            self.session.query(PitchingStatsModel)
            .filter(
                PitchingStatsModel.team_id == pitching_stats.team_id,
                PitchingStatsModel.season == pitching_stats.season,
            )
            .first()
        )
        if stats_model:
            # Update existing pitching stats
            self._update_stats_model(stats_model, pitching_stats)
            self.session.commit()
            return await self.get_by_id(stats_model.id)

        # Create new pitching stats
        stats_model = PitchingStatsModel(
            team_id=pitching_stats.team_id,
            season=pitching_stats.season,
            games_played=pitching_stats.games_played,
            wins=pitching_stats.wins,
            losses=pitching_stats.losses,
            saves=pitching_stats.saves,
            save_opportunities=pitching_stats.save_opportunities,
            holds=pitching_stats.holds,
            blown_saves=pitching_stats.blown_saves,
            innings_pitched=pitching_stats.innings_pitched,
            batters_faced=pitching_stats.batters_faced,
            hits_allowed=pitching_stats.hits_allowed,
            runs_allowed=pitching_stats.runs_allowed,
            earned_runs=pitching_stats.earned_runs,
            home_runs_allowed=pitching_stats.home_runs_allowed,
            strikeouts=pitching_stats.strikeouts,
            base_on_balls=pitching_stats.base_on_balls,
            intentional_walks=pitching_stats.intentional_walks,
            hit_batsmen=pitching_stats.hit_batsmen,
            wild_pitches=pitching_stats.wild_pitches,
            balks=pitching_stats.balks,
            number_of_pitches=pitching_stats.number_of_pitches,
            complete_games=pitching_stats.complete_games,
            shutouts=pitching_stats.shutouts,
            games_started=pitching_stats.games_started,
            ground_outs=pitching_stats.ground_outs,
            air_outs=pitching_stats.air_outs,
            # Additional basic stats from MLB API
            doubles=pitching_stats.doubles,
            triples=pitching_stats.triples,
            at_bats=pitching_stats.at_bats,
            outs=pitching_stats.outs,
            strikes=pitching_stats.strikes,
            pickoffs=pitching_stats.pickoffs,
            total_bases=pitching_stats.total_bases,
            games_finished=pitching_stats.games_finished,
            catchers_interference=pitching_stats.catchers_interference,
            sacrifice_bunts=pitching_stats.sacrifice_bunts,
            sacrifice_flies=pitching_stats.sacrifice_flies,
            ground_into_double_play=pitching_stats.ground_into_double_play,
            caught_stealing=pitching_stats.caught_stealing,
            # Advanced stats
            earned_run_average=pitching_stats.earned_run_average,
            whip=pitching_stats.whip,
            strikeouts_per_nine=pitching_stats.strikeouts_per_nine,
            walks_per_nine=pitching_stats.walks_per_nine,
            hits_per_nine=pitching_stats.hits_per_nine,
            home_runs_per_nine=pitching_stats.home_runs_per_nine,
            strikeout_to_walk_ratio=pitching_stats.strikeout_to_walk_ratio,
            ground_outs_to_airouts=pitching_stats.ground_outs_to_airouts,
            pitches_per_inning=pitching_stats.pitches_per_inning,
            batting_average_against=pitching_stats.batting_average_against,
            inherited_runners=pitching_stats.inherited_runners,
            inherited_runners_scored=pitching_stats.inherited_runners_scored,
            quality_starts=pitching_stats.quality_starts,
            # Additional advanced stats from MLB API
            on_base_percentage=pitching_stats.on_base_percentage,
            slugging_percentage=pitching_stats.slugging_percentage,
            ops=pitching_stats.ops,
            stolen_base_percentage=pitching_stats.stolen_base_percentage,
            strike_percentage=pitching_stats.strike_percentage,
            win_percentage=pitching_stats.win_percentage,
            runs_scored_per_nine=pitching_stats.runs_scored_per_nine,
        )
        self.session.add(stats_model)
        self.session.commit()
        self.session.refresh(stats_model)
        return await self.get_by_id(stats_model.id)

    async def update_stats(self, stats_id: int, updated_stats: Dict[str, Any]) -> Optional[PitchingStats]:
        """Update specific pitching statistics for a team."""
        stats_model = self.session.query(PitchingStatsModel).filter(PitchingStatsModel.id == stats_id).first()
        if not stats_model:
            return None

        # Update only the provided fields
        for key, value in updated_stats.items():
            if hasattr(stats_model, key):
                setattr(stats_model, key, value)

        self.session.commit()
        return await self.get_by_id(stats_id)

    async def delete(self, stats_id: int) -> bool:
        """Delete pitching statistics by its ID."""
        stats_model = self.session.query(PitchingStatsModel).filter(PitchingStatsModel.id == stats_id).first()
        if not stats_model:
            return False

        self.session.delete(stats_model)
        self.session.commit()
        return True

    def _model_to_entity(self, model: PitchingStatsModel) -> PitchingStats:
        """Convert a PitchingStatsModel to a PitchingStats entity."""
        team = None
        if model.team:
            team = Team(
                id=model.team.id,
                mlb_id=model.team.mlb_id,
                name=model.team.name,
                abbreviation=model.team.abbreviation,
                city=model.team.city,
                division=model.team.division,
                league=model.team.league,
                venue_name=model.team.venue_name,
                created_at=model.team.created_at,
                updated_at=model.team.updated_at,
            )

        return PitchingStats(
            id=model.id,
            team_id=model.team_id,
            season=model.season,
            games_played=model.games_played,
            wins=model.wins,
            losses=model.losses,
            saves=model.saves,
            save_opportunities=model.save_opportunities,
            holds=model.holds,
            blown_saves=model.blown_saves,
            innings_pitched=model.innings_pitched,
            batters_faced=model.batters_faced,
            hits_allowed=model.hits_allowed,
            runs_allowed=model.runs_allowed,
            earned_runs=model.earned_runs,
            home_runs_allowed=model.home_runs_allowed,
            strikeouts=model.strikeouts,
            base_on_balls=model.base_on_balls,
            intentional_walks=model.intentional_walks,
            hit_batsmen=model.hit_batsmen,
            wild_pitches=model.wild_pitches,
            balks=model.balks,
            number_of_pitches=model.number_of_pitches,
            complete_games=model.complete_games,
            shutouts=model.shutouts,
            games_started=model.games_started,
            ground_outs=model.ground_outs,
            air_outs=model.air_outs,
            # Additional basic stats from MLB API
            doubles=model.doubles,
            triples=model.triples,
            at_bats=model.at_bats,
            outs=model.outs,
            strikes=model.strikes,
            pickoffs=model.pickoffs,
            total_bases=model.total_bases,
            games_finished=model.games_finished,
            catchers_interference=model.catchers_interference,
            sacrifice_bunts=model.sacrifice_bunts,
            sacrifice_flies=model.sacrifice_flies,
            ground_into_double_play=model.ground_into_double_play,
            caught_stealing=model.caught_stealing,
            # Advanced stats
            earned_run_average=model.earned_run_average,
            whip=model.whip,
            strikeouts_per_nine=model.strikeouts_per_nine,
            walks_per_nine=model.walks_per_nine,
            hits_per_nine=model.hits_per_nine,
            home_runs_per_nine=model.home_runs_per_nine,
            strikeout_to_walk_ratio=model.strikeout_to_walk_ratio,
            ground_outs_to_airouts=model.ground_outs_to_airouts,
            pitches_per_inning=model.pitches_per_inning,
            batting_average_against=model.batting_average_against,
            inherited_runners=model.inherited_runners,
            inherited_runners_scored=model.inherited_runners_scored,
            quality_starts=model.quality_starts,
            # Additional advanced stats from MLB API
            on_base_percentage=model.on_base_percentage,
            slugging_percentage=model.slugging_percentage,
            ops=model.ops,
            stolen_base_percentage=model.stolen_base_percentage,
            strike_percentage=model.strike_percentage,
            win_percentage=model.win_percentage,
            runs_scored_per_nine=model.runs_scored_per_nine,
            created_at=model.created_at,
            updated_at=model.updated_at,
            team=team,
        )

    def _update_stats_model(self, model: PitchingStatsModel, entity: PitchingStats) -> None:
        """Update a PitchingStatsModel with values from a PitchingStats entity."""
        model.team_id = entity.team_id
        model.season = entity.season
        model.games_played = entity.games_played
        model.wins = entity.wins
        model.losses = entity.losses
        model.saves = entity.saves
        model.save_opportunities = entity.save_opportunities
        model.holds = entity.holds
        model.blown_saves = entity.blown_saves
        model.innings_pitched = entity.innings_pitched
        model.batters_faced = entity.batters_faced
        model.hits_allowed = entity.hits_allowed
        model.runs_allowed = entity.runs_allowed
        model.earned_runs = entity.earned_runs
        model.home_runs_allowed = entity.home_runs_allowed
        model.strikeouts = entity.strikeouts
        model.base_on_balls = entity.base_on_balls
        model.intentional_walks = entity.intentional_walks
        model.hit_batsmen = entity.hit_batsmen
        model.wild_pitches = entity.wild_pitches
        model.balks = entity.balks
        model.number_of_pitches = entity.number_of_pitches
        model.complete_games = entity.complete_games
        model.shutouts = entity.shutouts
        model.games_started = entity.games_started
        model.ground_outs = entity.ground_outs
        model.air_outs = entity.air_outs
        # Additional basic stats from MLB API
        model.doubles = entity.doubles
        model.triples = entity.triples
        model.at_bats = entity.at_bats
        model.outs = entity.outs
        model.strikes = entity.strikes
        model.pickoffs = entity.pickoffs
        model.total_bases = entity.total_bases
        model.games_finished = entity.games_finished
        model.catchers_interference = entity.catchers_interference
        model.sacrifice_bunts = entity.sacrifice_bunts
        model.sacrifice_flies = entity.sacrifice_flies
        model.ground_into_double_play = entity.ground_into_double_play
        model.caught_stealing = entity.caught_stealing
        # Advanced stats
        model.earned_run_average = entity.earned_run_average
        model.whip = entity.whip
        model.strikeouts_per_nine = entity.strikeouts_per_nine
        model.walks_per_nine = entity.walks_per_nine
        model.hits_per_nine = entity.hits_per_nine
        model.home_runs_per_nine = entity.home_runs_per_nine
        model.strikeout_to_walk_ratio = entity.strikeout_to_walk_ratio
        model.ground_outs_to_airouts = entity.ground_outs_to_airouts
        model.pitches_per_inning = entity.pitches_per_inning
        model.batting_average_against = entity.batting_average_against
        model.inherited_runners = entity.inherited_runners
        model.inherited_runners_scored = entity.inherited_runners_scored
        model.quality_starts = entity.quality_starts
        # Additional advanced stats from MLB API
        model.on_base_percentage = entity.on_base_percentage
        model.slugging_percentage = entity.slugging_percentage
        model.ops = entity.ops
        model.stolen_base_percentage = entity.stolen_base_percentage
        model.strike_percentage = entity.strike_percentage
        model.win_percentage = entity.win_percentage
        model.runs_scored_per_nine = entity.runs_scored_per_nine
