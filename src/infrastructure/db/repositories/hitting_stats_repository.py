"""
Implementation of the HittingStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.hitting_stats_repository import HittingStatsRepositoryPort
from src.domain.entities.hitting_stats import HittingStats
from src.infrastructure.db.models import HittingStatsModel
from src.infrastructure.db.repositories.entity_mapping_helpers import delete_model_by_id, team_model_to_entity

HITTING_STAT_FIELDS = (
    "games_played",
    "at_bats",
    "plate_appearances",
    "hits",
    "doubles",
    "triples",
    "home_runs",
    "runs_scored",
    "runs_batted_in",
    "stolen_bases",
    "caught_stealing",
    "base_on_balls",
    "strikeouts",
    "hit_by_pitch",
    "sacrifice_hits",
    "sacrifice_flies",
    "ground_into_double_play",
    "left_on_base",
    "batting_average",
    "on_base_percentage",
    "slugging_percentage",
    "ops",
    "babip",
    "total_bases",
    "at_bats_per_home_run",
    "stolen_base_percentage",
    "ground_outs",
    "air_outs",
    "ground_outs_to_airouts",
    "number_of_pitches",
    "intentional_walks",
)


def _hitting_payload_from_entity(entity: HittingStats) -> dict[str, Any]:
    return {field_name: getattr(entity, field_name) for field_name in HITTING_STAT_FIELDS}


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
        stats_model = self._get_existing_model(hitting_stats)
        if stats_model is None:
            stats_model = HittingStatsModel(
                team_id=hitting_stats.team_id,
                season=hitting_stats.season,
                **_hitting_payload_from_entity(hitting_stats),
            )
            self.session.add(stats_model)
        else:
            self._update_stats_model(stats_model, hitting_stats)
        self.session.commit()
        return await self.get_by_id(stats_model.id)

    def _get_existing_model(self, hitting_stats: HittingStats) -> Optional[HittingStatsModel]:
        if hitting_stats.id:
            stats_model = self.session.query(HittingStatsModel).filter(HittingStatsModel.id == hitting_stats.id).first()
            if stats_model is not None:
                return stats_model
        return (
            self.session.query(HittingStatsModel)
            .filter(
                HittingStatsModel.team_id == hitting_stats.team_id,
                HittingStatsModel.season == hitting_stats.season,
            )
            .first()
        )

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
        return delete_model_by_id(self.session, HittingStatsModel, stats_id)

    def _model_to_entity(self, model: HittingStatsModel) -> HittingStats:
        """Convert a HittingStatsModel to a HittingStats entity."""
        team = team_model_to_entity(model.team)

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
        for field_name, value in _hitting_payload_from_entity(entity).items():
            setattr(model, field_name, value)
