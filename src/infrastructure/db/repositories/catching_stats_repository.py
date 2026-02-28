"""
Implementation of the CatchingStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.catching_stats_repository import CatchingStatsRepositoryPort
from src.domain.entities.catching_stats import CatchingStats
from src.infrastructure.db.models import CatchingStatsModel
from src.infrastructure.db.repositories.entity_mapping_helpers import delete_model_by_id, team_model_to_entity

CATCHING_STAT_FIELDS = (
    "games_played",
    "games_pitched",
    "at_bats",
    "hits",
    "runs",
    "home_runs",
    "strikeouts",
    "base_on_balls",
    "intentional_walks",
    "hit_by_pitch",
    "total_bases",
    "sacrifice_bunts",
    "sacrifice_flies",
    "batting_average",
    "on_base_percentage",
    "slugging_percentage",
    "ops",
    "passed_balls",
    "wild_pitches",
    "stolen_bases_allowed",
    "caught_stealing",
    "stolen_base_percentage",
    "pickoffs",
    "pickoff_attempts",
    "catchers_interference",
    "earned_runs",
    "batters_faced",
    "hit_batsmen",
    "strikeout_walk_ratio",
)


def _catching_payload_from_entity(entity: CatchingStats) -> dict[str, Any]:
    return {field_name: getattr(entity, field_name) for field_name in CATCHING_STAT_FIELDS}


class CatchingStatsRepository(CatchingStatsRepositoryPort):
    """Implementation of the CatchingStatsRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, stats_id: int) -> CatchingStats | None:
        """Get catching statistics by its ID."""
        stats_model = (
            self.session.query(CatchingStatsModel)
            .options(joinedload(CatchingStatsModel.team))
            .filter(CatchingStatsModel.id == stats_id)
            .first()
        )
        if not stats_model:
            return None
        return self._model_to_entity(stats_model)

    async def get_by_team_and_season(self, team_id: int, season: int) -> CatchingStats | None:
        """Get catching statistics by team ID and season."""
        stats_model = (
            self.session.query(CatchingStatsModel)
            .options(joinedload(CatchingStatsModel.team))
            .filter(
                CatchingStatsModel.team_id == team_id,
                CatchingStatsModel.season == season,
            )
            .first()
        )
        if not stats_model:
            return None
        return self._model_to_entity(stats_model)

    async def list_by_team(self, team_id: int) -> list[CatchingStats]:
        """List all catching statistics for a specific team across seasons."""
        stats_models = (
            self.session.query(CatchingStatsModel)
            .options(joinedload(CatchingStatsModel.team))
            .filter(CatchingStatsModel.team_id == team_id)
            .order_by(CatchingStatsModel.season.desc())
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_by_season(self, season: int) -> list[CatchingStats]:
        """List catching statistics for all teams in a specific season."""
        stats_models = (
            self.session.query(CatchingStatsModel)
            .options(joinedload(CatchingStatsModel.team))
            .filter(CatchingStatsModel.season == season)
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> list[CatchingStats]:
        """List top teams by a specific catching statistic."""
        # Validate that the stat_name is a valid column
        if not hasattr(CatchingStatsModel, stat_name):
            return []

        # Get the column to sort by
        stat_column = getattr(CatchingStatsModel, stat_name)

        # Determine sort order
        order_func = desc if descending else asc

        stats_models = (
            self.session.query(CatchingStatsModel)
            .options(joinedload(CatchingStatsModel.team))
            .filter(CatchingStatsModel.season == season)
            .order_by(order_func(stat_column))
            .limit(limit)
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def save(self, catching_stats: CatchingStats) -> CatchingStats:
        """Save catching statistics (create or update)."""
        stats_model = self._get_existing_model(catching_stats)
        if stats_model is None:
            stats_model = CatchingStatsModel(
                team_id=catching_stats.team_id,
                season=catching_stats.season,
                **_catching_payload_from_entity(catching_stats),
            )
            self.session.add(stats_model)
        else:
            self._update_stats_model(stats_model, catching_stats)
        self.session.commit()
        return await self.get_by_id(stats_model.id)

    def _get_existing_model(self, catching_stats: CatchingStats) -> CatchingStatsModel | None:
        if catching_stats.id:
            stats_model = (
                self.session.query(CatchingStatsModel).filter(CatchingStatsModel.id == catching_stats.id).first()
            )
            if stats_model is not None:
                return stats_model
        return (
            self.session.query(CatchingStatsModel)
            .filter(
                CatchingStatsModel.team_id == catching_stats.team_id,
                CatchingStatsModel.season == catching_stats.season,
            )
            .first()
        )

    async def update_stats(self, stats_id: int, updated_stats: dict[str, Any]) -> CatchingStats | None:
        """Update specific catching statistics for a team."""
        stats_model = self.session.query(CatchingStatsModel).filter(CatchingStatsModel.id == stats_id).first()
        if not stats_model:
            return None

        # Update only the provided fields
        for key, value in updated_stats.items():
            if hasattr(stats_model, key):
                setattr(stats_model, key, value)

        self.session.commit()
        return await self.get_by_id(stats_id)

    async def delete(self, stats_id: int) -> bool:
        """Delete catching statistics by its ID."""
        return delete_model_by_id(self.session, CatchingStatsModel, stats_id)

    @staticmethod
    def _model_to_entity(model: CatchingStatsModel) -> CatchingStats:
        """Convert a CatchingStatsModel to a CatchingStats entity."""
        team = team_model_to_entity(model.team)

        return CatchingStats(
            id=model.id,
            team_id=model.team_id,
            season=model.season,
            games_played=model.games_played,
            games_pitched=model.games_pitched,
            at_bats=model.at_bats,
            hits=model.hits,
            runs=model.runs,
            home_runs=model.home_runs,
            strikeouts=model.strikeouts,
            base_on_balls=model.base_on_balls,
            intentional_walks=model.intentional_walks,
            hit_by_pitch=model.hit_by_pitch,
            total_bases=model.total_bases,
            sacrifice_bunts=model.sacrifice_bunts,
            sacrifice_flies=model.sacrifice_flies,
            batting_average=model.batting_average,
            on_base_percentage=model.on_base_percentage,
            slugging_percentage=model.slugging_percentage,
            ops=model.ops,
            passed_balls=model.passed_balls,
            wild_pitches=model.wild_pitches,
            stolen_bases_allowed=model.stolen_bases_allowed,
            caught_stealing=model.caught_stealing,
            stolen_base_percentage=model.stolen_base_percentage,
            pickoffs=model.pickoffs,
            pickoff_attempts=model.pickoff_attempts,
            catchers_interference=model.catchers_interference,
            earned_runs=model.earned_runs,
            batters_faced=model.batters_faced,
            hit_batsmen=model.hit_batsmen,
            strikeout_walk_ratio=model.strikeout_walk_ratio,
            created_at=model.created_at,
            updated_at=model.updated_at,
            team=team,
        )

    @staticmethod
    def _update_stats_model(model: CatchingStatsModel, entity: CatchingStats) -> None:
        """Update a CatchingStatsModel with values from a CatchingStats entity."""
        model.team_id = entity.team_id
        model.season = entity.season
        for field_name, value in _catching_payload_from_entity(entity).items():
            setattr(model, field_name, value)
