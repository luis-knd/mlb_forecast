"""
Implementation of the PitchingStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.pitching_stats_repository import PitchingStatsRepositoryPort
from src.domain.entities.pitching_stats import PitchingStats
from src.infrastructure.db.models import PitchingStatsModel
from src.infrastructure.db.repositories.entity_mapping_helpers import delete_model_by_id, team_model_to_entity

PITCHING_STAT_FIELDS = (
    "games_played",
    "wins",
    "losses",
    "saves",
    "save_opportunities",
    "holds",
    "blown_saves",
    "innings_pitched",
    "batters_faced",
    "hits_allowed",
    "runs_allowed",
    "earned_runs",
    "home_runs_allowed",
    "strikeouts",
    "base_on_balls",
    "intentional_walks",
    "hit_batsmen",
    "wild_pitches",
    "balks",
    "number_of_pitches",
    "complete_games",
    "shutouts",
    "games_started",
    "ground_outs",
    "air_outs",
    "doubles",
    "triples",
    "at_bats",
    "outs",
    "strikes",
    "pickoffs",
    "total_bases",
    "games_finished",
    "catchers_interference",
    "sacrifice_bunts",
    "sacrifice_flies",
    "ground_into_double_play",
    "caught_stealing",
    "earned_run_average",
    "whip",
    "strikeouts_per_nine",
    "walks_per_nine",
    "hits_per_nine",
    "home_runs_per_nine",
    "strikeout_to_walk_ratio",
    "ground_outs_to_airouts",
    "pitches_per_inning",
    "batting_average_against",
    "inherited_runners",
    "inherited_runners_scored",
    "quality_starts",
    "on_base_percentage",
    "slugging_percentage",
    "ops",
    "stolen_base_percentage",
    "strike_percentage",
    "win_percentage",
    "runs_scored_per_nine",
)


def _pitching_payload_from_entity(entity: PitchingStats) -> dict[str, Any]:
    return {field_name: getattr(entity, field_name) for field_name in PITCHING_STAT_FIELDS}


def _pitching_payload_from_model(model: PitchingStatsModel) -> dict[str, Any]:
    return {field_name: getattr(model, field_name) for field_name in PITCHING_STAT_FIELDS}


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
        stats_model = self._get_existing_model(pitching_stats)
        if stats_model is None:
            stats_model = PitchingStatsModel(
                team_id=pitching_stats.team_id,
                season=pitching_stats.season,
                **_pitching_payload_from_entity(pitching_stats),
            )
            self.session.add(stats_model)
        else:
            self._update_stats_model(stats_model, pitching_stats)
        self.session.commit()
        return await self.get_by_id(stats_model.id)

    def _get_existing_model(self, pitching_stats: PitchingStats) -> Optional[PitchingStatsModel]:
        if pitching_stats.id:
            stats_model = (
                self.session.query(PitchingStatsModel).filter(PitchingStatsModel.id == pitching_stats.id).first()
            )
            if stats_model is not None:
                return stats_model
        return (
            self.session.query(PitchingStatsModel)
            .filter(
                PitchingStatsModel.team_id == pitching_stats.team_id,
                PitchingStatsModel.season == pitching_stats.season,
            )
            .first()
        )

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
        return delete_model_by_id(self.session, PitchingStatsModel, stats_id)

    def _model_to_entity(self, model: PitchingStatsModel) -> PitchingStats:
        """Convert a PitchingStatsModel to a PitchingStats entity."""
        team = team_model_to_entity(model.team)
        return PitchingStats(
            id=model.id,
            team_id=model.team_id,
            season=model.season,
            created_at=model.created_at,
            updated_at=model.updated_at,
            team=team,
            **_pitching_payload_from_model(model),
        )

    def _update_stats_model(self, model: PitchingStatsModel, entity: PitchingStats) -> None:
        """Update a PitchingStatsModel with values from a PitchingStats entity."""
        model.team_id = entity.team_id
        model.season = entity.season
        for field_name, value in _pitching_payload_from_entity(entity).items():
            setattr(model, field_name, value)
