"""
Implementation of the FieldingStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.fielding_stats_repository import FieldingStatsRepositoryPort
from src.domain.entities.fielding_stats import FieldingStats
from src.infrastructure.db.models import FieldingStatsModel
from src.infrastructure.db.repositories.entity_mapping_helpers import delete_model_by_id, team_model_to_entity

FIELDING_STAT_FIELDS = (
    "games_played",
    "games_started",
    "innings_played",
    "total_chances",
    "putouts",
    "assists",
    "errors",
    "throwing_errors",
    "double_plays",
    "triple_plays",
    "fielding_percentage",
    "defensive_efficiency_ratio",
    "range_factor_per_game",
    "range_factor_per_nine",
    "outfield_assists",
    "passed_balls",
    "wild_pitches",
    "stolen_bases_allowed",
    "caught_stealing",
    "stolen_base_percentage",
    "catchers_interference",
    "pickoffs",
)


def _fielding_payload_from_entity(entity: FieldingStats) -> dict[str, Any]:
    return {field_name: getattr(entity, field_name) for field_name in FIELDING_STAT_FIELDS}


class FieldingStatsRepository(FieldingStatsRepositoryPort):
    """Implementation of the FieldingStatsRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, stats_id: int) -> Optional[FieldingStats]:
        """Get fielding statistics by its ID."""
        stats_model = (
            self.session.query(FieldingStatsModel)
            .options(joinedload(FieldingStatsModel.team))
            .filter(FieldingStatsModel.id == stats_id)
            .first()
        )
        if not stats_model:
            return None
        return self._model_to_entity(stats_model)

    async def get_by_team_and_season(self, team_id: int, season: int) -> Optional[FieldingStats]:
        """Get fielding statistics by team ID and season."""
        stats_model = (
            self.session.query(FieldingStatsModel)
            .options(joinedload(FieldingStatsModel.team))
            .filter(
                FieldingStatsModel.team_id == team_id,
                FieldingStatsModel.season == season,
            )
            .first()
        )
        if not stats_model:
            return None
        return self._model_to_entity(stats_model)

    async def list_by_team(self, team_id: int) -> List[FieldingStats]:
        """List all fielding statistics for a specific team across seasons."""
        stats_models = (
            self.session.query(FieldingStatsModel)
            .options(joinedload(FieldingStatsModel.team))
            .filter(FieldingStatsModel.team_id == team_id)
            .order_by(FieldingStatsModel.season.desc())
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_by_season(self, season: int) -> List[FieldingStats]:
        """List fielding statistics for all teams in a specific season."""
        stats_models = (
            self.session.query(FieldingStatsModel)
            .options(joinedload(FieldingStatsModel.team))
            .filter(FieldingStatsModel.season == season)
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> List[FieldingStats]:
        """List top teams by a specific fielding statistic."""
        # Validate that the stat_name is a valid column
        if not hasattr(FieldingStatsModel, stat_name):
            return []

        # Get the column to sort by
        stat_column = getattr(FieldingStatsModel, stat_name)

        # Determine sort order
        order_func = desc if descending else asc

        stats_models = (
            self.session.query(FieldingStatsModel)
            .options(joinedload(FieldingStatsModel.team))
            .filter(FieldingStatsModel.season == season)
            .order_by(order_func(stat_column))
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def save(self, fielding_stats: FieldingStats) -> FieldingStats:
        """Save fielding statistics (create or update)."""
        stats_model = self._get_existing_model(fielding_stats)
        if stats_model is None:
            stats_model = FieldingStatsModel(
                team_id=fielding_stats.team_id,
                season=fielding_stats.season,
                **_fielding_payload_from_entity(fielding_stats),
            )
            self.session.add(stats_model)
        else:
            self._update_stats_model(stats_model, fielding_stats)
        self.session.commit()
        return await self.get_by_id(stats_model.id)

    def _get_existing_model(self, fielding_stats: FieldingStats) -> Optional[FieldingStatsModel]:
        if fielding_stats.id:
            stats_model = (
                self.session.query(FieldingStatsModel).filter(FieldingStatsModel.id == fielding_stats.id).first()
            )
            if stats_model is not None:
                return stats_model
        return (
            self.session.query(FieldingStatsModel)
            .filter(
                FieldingStatsModel.team_id == fielding_stats.team_id,
                FieldingStatsModel.season == fielding_stats.season,
            )
            .first()
        )

    async def update_stats(self, stats_id: int, updated_stats: Dict[str, Any]) -> Optional[FieldingStats]:
        """Update specific fielding statistics for a team."""
        stats_model = self.session.query(FieldingStatsModel).filter(FieldingStatsModel.id == stats_id).first()
        if not stats_model:
            return None

        # Update only the provided fields
        for key, value in updated_stats.items():
            if hasattr(stats_model, key):
                setattr(stats_model, key, value)

        self.session.commit()
        return await self.get_by_id(stats_id)

    async def delete(self, stats_id: int) -> bool:
        """Delete fielding statistics by its ID."""
        return delete_model_by_id(self.session, FieldingStatsModel, stats_id)

    def _model_to_entity(self, model: FieldingStatsModel) -> FieldingStats:
        """Convert a FieldingStatsModel to a FieldingStats entity."""
        team = team_model_to_entity(model.team)

        return FieldingStats(
            id=model.id,
            team_id=model.team_id,
            season=model.season,
            games_played=model.games_played,
            games_started=model.games_started,
            innings_played=model.innings_played,
            total_chances=model.total_chances,
            putouts=model.putouts,
            assists=model.assists,
            errors=model.errors,
            throwing_errors=model.throwing_errors,
            double_plays=model.double_plays,
            triple_plays=model.triple_plays,
            fielding_percentage=model.fielding_percentage,
            defensive_efficiency_ratio=model.defensive_efficiency_ratio,
            range_factor_per_game=model.range_factor_per_game,
            range_factor_per_nine=model.range_factor_per_nine,
            outfield_assists=model.outfield_assists,
            passed_balls=model.passed_balls,
            wild_pitches=model.wild_pitches,
            stolen_bases_allowed=model.stolen_bases_allowed,
            caught_stealing=model.caught_stealing,
            stolen_base_percentage=model.stolen_base_percentage,
            catchers_interference=model.catchers_interference,
            pickoffs=model.pickoffs,
            created_at=model.created_at,
            updated_at=model.updated_at,
            team=team,
        )

    def _update_stats_model(self, model: FieldingStatsModel, entity: FieldingStats) -> None:
        """Update a FieldingStatsModel with values from a FieldingStats entity."""
        model.team_id = entity.team_id
        model.season = entity.season
        for field_name, value in _fielding_payload_from_entity(entity).items():
            setattr(model, field_name, value)
