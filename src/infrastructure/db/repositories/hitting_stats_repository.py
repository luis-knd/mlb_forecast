"""
Implementation of the HittingStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.hitting_stats_repository import HittingStatsRepositoryPort
from src.domain.entities.hitting_stats import HittingStats
from src.domain.entities.team import Team
from src.infrastructure.db.models import HittingStatsModel


class HittingStatsRepository(HittingStatsRepositoryPort):
    """Implementation of the HittingStatsRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, stats_id: int) -> Optional[HittingStats]:
        """Get hitting statistics by its ID."""
        stats_model = (
            self.session.query(HittingStatsModel)
            .options(joinedload(HittingStatsModel.team))
            .filter(HittingStatsModel.id == stats_id)
            .first()
        )
        if not stats_model:
            return None
        return self._model_to_entity(stats_model)

    async def get_by_team_and_season(self, team_id: int, season: int) -> Optional[HittingStats]:
        """Get hitting statistics by team ID and season."""
        stats_model = (
            self.session.query(HittingStatsModel)
            .options(joinedload(HittingStatsModel.team))
            .filter(HittingStatsModel.team_id == team_id, HittingStatsModel.season == season)
            .first()
        )
        if not stats_model:
            return None
        return self._model_to_entity(stats_model)

    async def list_by_team(self, team_id: int) -> List[HittingStats]:
        """List all hitting statistics for a specific team across seasons."""
        stats_models = (
            self.session.query(HittingStatsModel)
            .options(joinedload(HittingStatsModel.team))
            .filter(HittingStatsModel.team_id == team_id)
            .order_by(HittingStatsModel.season.desc())
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_by_season(self, season: int) -> List[HittingStats]:
        """List hitting statistics for all teams in a specific season."""
        stats_models = (
            self.session.query(HittingStatsModel)
            .options(joinedload(HittingStatsModel.team))
            .filter(HittingStatsModel.season == season)
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> List[HittingStats]:
        """List top teams by a specific hitting statistic."""
        # Validate that the stat_name is a valid column
        if not hasattr(HittingStatsModel, stat_name):
            return []

        # Get the column to sort by
        stat_column = getattr(HittingStatsModel, stat_name)

        # Determine sort order
        order_func = desc if descending else asc

        stats_models = (
            self.session.query(HittingStatsModel)
            .options(joinedload(HittingStatsModel.team))
            .filter(HittingStatsModel.season == season)
            .order_by(order_func(stat_column))
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def save(self, hitting_stats: HittingStats) -> HittingStats:
        """Save hitting statistics (create or update)."""
        # Check if hitting stats already exists
        if hitting_stats.id:
            stats_model = self.session.query(HittingStatsModel).filter(HittingStatsModel.id == hitting_stats.id).first()
            if stats_model:
                # Update existing hitting stats
                self._update_stats_model(stats_model, hitting_stats)
                self.session.commit()
                return await self.get_by_id(stats_model.id)

        # Check if hitting stats exists by team_id and season
        stats_model = (
            self.session.query(HittingStatsModel)
            .filter(
                HittingStatsModel.team_id == hitting_stats.team_id,
                HittingStatsModel.season == hitting_stats.season,
            )
            .first()
        )
        if stats_model:
            # Update existing hitting stats
            self._update_stats_model(stats_model, hitting_stats)
            self.session.commit()
            return await self.get_by_id(stats_model.id)

        # Create new hitting stats
        stats_model = HittingStatsModel(
            team_id=hitting_stats.team_id,
            season=hitting_stats.season,
            games_played=hitting_stats.games_played,
            at_bats=hitting_stats.at_bats,
            plate_appearances=hitting_stats.plate_appearances,
            hits=hitting_stats.hits,
            doubles=hitting_stats.doubles,
            triples=hitting_stats.triples,
            home_runs=hitting_stats.home_runs,
            runs_scored=hitting_stats.runs_scored,
            runs_batted_in=hitting_stats.runs_batted_in,
            stolen_bases=hitting_stats.stolen_bases,
            caught_stealing=hitting_stats.caught_stealing,
            base_on_balls=hitting_stats.base_on_balls,
            strikeouts=hitting_stats.strikeouts,
            hit_by_pitch=hitting_stats.hit_by_pitch,
            sacrifice_hits=hitting_stats.sacrifice_hits,
            sacrifice_flies=hitting_stats.sacrifice_flies,
            ground_into_double_play=hitting_stats.ground_into_double_play,
            left_on_base=hitting_stats.left_on_base,
            batting_average=hitting_stats.batting_average,
            on_base_percentage=hitting_stats.on_base_percentage,
            slugging_percentage=hitting_stats.slugging_percentage,
            ops=hitting_stats.ops,
            babip=hitting_stats.babip,
            total_bases=hitting_stats.total_bases,
            at_bats_per_home_run=hitting_stats.at_bats_per_home_run,
            stolen_base_percentage=hitting_stats.stolen_base_percentage,
            ground_outs=hitting_stats.ground_outs,
            air_outs=hitting_stats.air_outs,
            ground_outs_to_airouts=hitting_stats.ground_outs_to_airouts,
            number_of_pitches=hitting_stats.number_of_pitches,
            intentional_walks=hitting_stats.intentional_walks,
        )
        self.session.add(stats_model)
        self.session.commit()
        self.session.refresh(stats_model)
        return await self.get_by_id(stats_model.id)

    async def update_stats(self, stats_id: int, updated_stats: Dict[str, Any]) -> Optional[HittingStats]:
        """Update specific hitting statistics for a team."""
        stats_model = self.session.query(HittingStatsModel).filter(HittingStatsModel.id == stats_id).first()
        if not stats_model:
            return None

        # Update only the provided fields
        for key, value in updated_stats.items():
            if hasattr(stats_model, key):
                setattr(stats_model, key, value)

        self.session.commit()
        return await self.get_by_id(stats_id)

    async def delete(self, stats_id: int) -> bool:
        """Delete hitting statistics by its ID."""
        stats_model = self.session.query(HittingStatsModel).filter(HittingStatsModel.id == stats_id).first()
        if not stats_model:
            return False

        self.session.delete(stats_model)
        self.session.commit()
        return True

    def _model_to_entity(self, model: HittingStatsModel) -> HittingStats:
        """Convert a HittingStatsModel to a HittingStats entity."""
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

        return HittingStats(
            id=model.id,
            team_id=model.team_id,
            season=model.season,
            games_played=model.games_played,
            at_bats=model.at_bats,
            plate_appearances=model.plate_appearances,
            hits=model.hits,
            doubles=model.doubles,
            triples=model.triples,
            home_runs=model.home_runs,
            runs_scored=model.runs_scored,
            runs_batted_in=model.runs_batted_in,
            stolen_bases=model.stolen_bases,
            caught_stealing=model.caught_stealing,
            base_on_balls=model.base_on_balls,
            strikeouts=model.strikeouts,
            hit_by_pitch=model.hit_by_pitch,
            sacrifice_hits=model.sacrifice_hits,
            sacrifice_flies=model.sacrifice_flies,
            ground_into_double_play=model.ground_into_double_play,
            left_on_base=model.left_on_base,
            batting_average=model.batting_average,
            on_base_percentage=model.on_base_percentage,
            slugging_percentage=model.slugging_percentage,
            ops=model.ops,
            babip=model.babip,
            total_bases=model.total_bases,
            at_bats_per_home_run=model.at_bats_per_home_run,
            stolen_base_percentage=model.stolen_base_percentage,
            ground_outs=model.ground_outs,
            air_outs=model.air_outs,
            ground_outs_to_airouts=model.ground_outs_to_airouts,
            number_of_pitches=model.number_of_pitches,
            intentional_walks=model.intentional_walks,
            created_at=model.created_at,
            updated_at=model.updated_at,
            team=team,
        )

    def _update_stats_model(self, model: HittingStatsModel, entity: HittingStats) -> None:
        """Update a HittingStatsModel with values from a HittingStats entity."""
        model.team_id = entity.team_id
        model.season = entity.season
        model.games_played = entity.games_played
        model.at_bats = entity.at_bats
        model.plate_appearances = entity.plate_appearances
        model.hits = entity.hits
        model.doubles = entity.doubles
        model.triples = entity.triples
        model.home_runs = entity.home_runs
        model.runs_scored = entity.runs_scored
        model.runs_batted_in = entity.runs_batted_in
        model.stolen_bases = entity.stolen_bases
        model.caught_stealing = entity.caught_stealing
        model.base_on_balls = entity.base_on_balls
        model.strikeouts = entity.strikeouts
        model.hit_by_pitch = entity.hit_by_pitch
        model.sacrifice_hits = entity.sacrifice_hits
        model.sacrifice_flies = entity.sacrifice_flies
        model.ground_into_double_play = entity.ground_into_double_play
        model.left_on_base = entity.left_on_base
        model.batting_average = entity.batting_average
        model.on_base_percentage = entity.on_base_percentage
        model.slugging_percentage = entity.slugging_percentage
        model.ops = entity.ops
        model.babip = entity.babip
        model.total_bases = entity.total_bases
        model.at_bats_per_home_run = entity.at_bats_per_home_run
        model.stolen_base_percentage = entity.stolen_base_percentage
        model.ground_outs = entity.ground_outs
        model.air_outs = entity.air_outs
        model.ground_outs_to_airouts = entity.ground_outs_to_airouts
        model.number_of_pitches = entity.number_of_pitches
        model.intentional_walks = entity.intentional_walks
