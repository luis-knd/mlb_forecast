"""
TeamStats repository implementation.
This module implements the TeamStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.team_stats_repository import TeamStatsRepositoryPort
from src.domain.entities.team_stats import TeamStats
from src.infrastructure.db.models import CatchingStatsModel, FieldingStatsModel, HittingStatsModel, PitchingStatsModel
from src.infrastructure.mappers.team_stats_mapper import TeamStatsMapper


class TeamStatsRepository(TeamStatsRepositoryPort):
    """Implementation of the TeamStatsRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session
        self.mapper = TeamStatsMapper()

    async def get_by_id(self, stats_id: int) -> TeamStats | None:
        """Get team statistics by its ID."""
        # Since we no longer have a TeamStatsModel, we need to query the individual stats models
        # and aggregate them into a TeamStats entity

        # For simplicity, we'll use the hitting_stats table as the base for team stats
        # and join with other stats tables as needed
        hitting_stats = (
            self.session.query(HittingStatsModel)
            .options(joinedload(HittingStatsModel.team))
            .filter(HittingStatsModel.id == stats_id)
            .first()
        )

        if not hitting_stats:
            return None

        # Get corresponding pitching and fielding stats
        team_id = hitting_stats.team_id
        season = hitting_stats.season

        pitching_stats = (
            self.session.query(PitchingStatsModel)
            .filter(
                PitchingStatsModel.team_id == team_id,
                PitchingStatsModel.season == season,
            )
            .first()
        )

        fielding_stats = (
            self.session.query(FieldingStatsModel)
            .filter(
                FieldingStatsModel.team_id == team_id,
                FieldingStatsModel.season == season,
            )
            .first()
        )

        # Aggregate stats into a TeamStats entity
        return self.mapper.to_entity(hitting_stats, pitching_stats, fielding_stats)

    async def get_by_team_and_season(self, team_id: int, season: int):
        """Aggregate per-table stats into a composite structure the mapper understands."""
        # Base rows (cada tabla es única por team_id+season)
        hitting = (
            self.session.query(HittingStatsModel)
            .filter(HittingStatsModel.team_id == team_id, HittingStatsModel.season == season)
            .first()
        )
        pitching = (
            self.session.query(PitchingStatsModel)
            .filter(PitchingStatsModel.team_id == team_id, PitchingStatsModel.season == season)
            .first()
        )
        fielding = (
            self.session.query(FieldingStatsModel)
            .filter(FieldingStatsModel.team_id == team_id, FieldingStatsModel.season == season)
            .first()
        )
        catching = (
            self.session.query(CatchingStatsModel)
            .filter(CatchingStatsModel.team_id == team_id, CatchingStatsModel.season == season)
            .first()
        )

        if not any((hitting, pitching, fielding, catching)):
            return None

        def _ts(o):
            return getattr(o, "updated_at", None) if o is not None else None

        updated_at_candidates = [ts for ts in (_ts(hitting), _ts(pitching), _ts(fielding), _ts(catching)) if ts]
        updated_at = max(updated_at_candidates) if updated_at_candidates else None

        return {
            "team_id": team_id,
            "season": season,
            "hitting_stats": self._model_to_dict(hitting),
            "pitching_stats": self._model_to_dict(pitching),
            "fielding_stats": self._model_to_dict(fielding),
            "catching_stats": self._model_to_dict(catching),
            "updated_at": updated_at,
        }

    @staticmethod
    def _model_to_dict(model):
        """Convert SQLAlchemy model to dictionary."""
        if not model:
            return None
        return {c.name: getattr(model, c.name) for c in model.__table__.columns}

    async def list_by_team(self, team_id: int) -> list[TeamStats]:
        """List all statistics for a specific team across seasons."""
        # Get all seasons for which the team has hitting stats
        seasons = (
            self.session.query(HittingStatsModel.season)
            .filter(HittingStatsModel.team_id == team_id)
            .order_by(HittingStatsModel.season.desc())
            .all()
        )

        # For each season, get the team stats
        team_stats_list = []
        for season_row in seasons:
            season = season_row[0]
            team_stats = await self.get_by_team_and_season(team_id, season)
            if team_stats:
                team_stats_list.append(team_stats)

        return team_stats_list

    async def list_by_season(self, season: int) -> list[TeamStats]:
        """List statistics for all teams in a specific season."""
        # Get all teams that have hitting stats for the given season
        team_ids = self.session.query(HittingStatsModel.team_id).filter(HittingStatsModel.season == season).all()

        # For each team, get the team stats
        team_stats_list = []
        for team_id_row in team_ids:
            team_id = team_id_row[0]
            team_stats = await self.get_by_team_and_season(team_id, season)
            if team_stats:
                team_stats_list.append(team_stats)

        return team_stats_list

    async def list_top_teams_by_stat(
        self, season: int, stat_name: str, limit: int = 10, descending: bool = True
    ) -> list[TeamStats]:
        """List top teams by a specific statistic."""

        # Check if the stat is in HittingStatsModel
        if hasattr(HittingStatsModel, stat_name):
            model_with_stat = HittingStatsModel
        # Check if the stat is in PitchingStatsModel
        elif hasattr(PitchingStatsModel, stat_name):
            model_with_stat = PitchingStatsModel
        # Check if the stat is in FieldingStatsModel
        elif hasattr(FieldingStatsModel, stat_name):
            model_with_stat = FieldingStatsModel
        else:
            # Stat not found in any model
            return []

        # Get the column to sort by
        stat_column = getattr(model_with_stat, stat_name)

        # Determine sort order
        order_func = desc if descending else asc

        # Get team IDs sorted by the requested stat
        team_ids = (
            self.session.query(model_with_stat.team_id)
            .filter(model_with_stat.season == season)
            .order_by(order_func(stat_column))
            .limit(limit)
            .all()
        )

        # For each team, get the team stats
        team_stats_list = []
        for team_id_row in team_ids:
            team_id = team_id_row[0]
            team_stats = await self.get_by_team_and_season(team_id, season)
            if team_stats:
                team_stats_list.append(team_stats)

        return team_stats_list

    async def save(self, team_stats: TeamStats) -> TeamStats:
        hitting_stats = self._upsert_model(HittingStatsModel, self.mapper.update_hitting_model, team_stats)
        pitching_stats = self._upsert_model(PitchingStatsModel, self.mapper.update_pitching_model, team_stats)
        fielding_stats = self._upsert_model(FieldingStatsModel, self.mapper.update_fielding_model, team_stats)
        try:
            self.session.commit()
            self.session.refresh(hitting_stats)
            self.session.refresh(pitching_stats)
            self.session.refresh(fielding_stats)
            team_stats.id = hitting_stats.id
            team_stats.created_at = hitting_stats.created_at
            team_stats.updated_at = hitting_stats.updated_at
            return team_stats
        except Exception as e:
            self.session.rollback()
            raise e

    def _upsert_model(self, model_class, model_updater, team_stats: TeamStats):
        model = (
            self.session.query(model_class)
            .filter(model_class.team_id == team_stats.team_id, model_class.season == team_stats.season)
            .first()
        )
        if model is None:
            model = model_updater(team_stats)
            self.session.add(model)
            return model
        model_updater(team_stats, model)
        return model

    async def update_stats(self, stats_id: int, updated_stats: dict[str, Any]) -> TeamStats | None:
        """
        Update specific statistics for a team.

        Note: This method is now a facade that delegates to the individual stats repositories.
        In a production environment, you would likely want to use a transaction to ensure
        all stats are updated atomically.
        """
        # Since we no longer have a TeamStatsModel, we need to determine which model to update
        # based on the stats_id and the updated_stats dictionary

        # For this implementation, we'll just return None
        # In a real implementation, you would need to update the appropriate stats model
        # and then return the aggregated TeamStats entity

        # Get the hitting stats with the given ID
        hitting_stats = self.session.query(HittingStatsModel).filter(HittingStatsModel.id == stats_id).first()

        if hitting_stats:
            # Get the team_id and season from the hitting stats
            team_id = hitting_stats.team_id
            season = hitting_stats.season

            # Get the team stats for this team and season
            return await self.get_by_team_and_season(team_id, season)

        # Try with pitching stats
        pitching_stats = self.session.query(PitchingStatsModel).filter(PitchingStatsModel.id == stats_id).first()

        if pitching_stats:
            # Get the team_id and season from the pitching stats
            team_id = pitching_stats.team_id
            season = pitching_stats.season

            # Get the team stats for this team and season
            return await self.get_by_team_and_season(team_id, season)

        # Try with fielding stats
        fielding_stats = self.session.query(FieldingStatsModel).filter(FieldingStatsModel.id == stats_id).first()

        if fielding_stats:
            # Get the team_id and season from the fielding stats
            team_id = fielding_stats.team_id
            season = fielding_stats.season

            # Get the team stats for this team and season
            return await self.get_by_team_and_season(team_id, season)

        # No stats found with the given ID
        return None

    async def delete(self, stats_id: int) -> bool:
        """
        Delete team statistics by its ID.

        Note: This method is now a facade that delegates to the individual stats repositories.
        In a production environment, you would likely want to use a transaction to ensure
        all stats are deleted atomically.
        """
        # Since we no longer have a TeamStatsModel, we need to determine which model to delete
        # based on the stats_id

        # Try to find and delete hitting stats
        hitting_stats = self.session.query(HittingStatsModel).filter(HittingStatsModel.id == stats_id).first()

        if hitting_stats:
            # Delete the hitting stats
            self.session.delete(hitting_stats)
            self.session.commit()

            # For a complete implementation, you would also delete the corresponding
            # pitching and fielding stats for this team and season
            return True

        # Try with pitching stats
        pitching_stats = self.session.query(PitchingStatsModel).filter(PitchingStatsModel.id == stats_id).first()

        if pitching_stats:
            # Delete the pitching stats
            self.session.delete(pitching_stats)
            self.session.commit()
            return True

        # Try with fielding stats
        fielding_stats = self.session.query(FieldingStatsModel).filter(FieldingStatsModel.id == stats_id).first()

        if fielding_stats:
            # Delete the fielding stats
            self.session.delete(fielding_stats)
            self.session.commit()
            return True

        # No stats found with the given ID
        return False
