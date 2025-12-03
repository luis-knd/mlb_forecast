"""
Implementation of the FieldingStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.fielding_stats_repository import FieldingStatsRepositoryPort
from src.domain.entities.fielding_stats import FieldingStats
from src.domain.entities.team import Team
from src.infrastructure.db.models import FieldingStatsModel


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
        # Check if fielding stats already exists
        if fielding_stats.id:
            stats_model = (
                self.session.query(FieldingStatsModel).filter(FieldingStatsModel.id == fielding_stats.id).first()
            )
            if stats_model:
                # Update existing fielding stats
                self._update_stats_model(stats_model, fielding_stats)
                self.session.commit()
                return await self.get_by_id(stats_model.id)

        # Check if fielding stats exists by team_id and season
        stats_model = (
            self.session.query(FieldingStatsModel)
            .filter(
                FieldingStatsModel.team_id == fielding_stats.team_id,
                FieldingStatsModel.season == fielding_stats.season,
            )
            .first()
        )
        if stats_model:
            # Update existing fielding stats
            self._update_stats_model(stats_model, fielding_stats)
            self.session.commit()
            return await self.get_by_id(stats_model.id)

        # Create new fielding stats
        stats_model = FieldingStatsModel(
            team_id=fielding_stats.team_id,
            season=fielding_stats.season,
            games_played=fielding_stats.games_played,
            games_started=fielding_stats.games_started,
            innings_played=fielding_stats.innings_played,
            total_chances=fielding_stats.total_chances,
            putouts=fielding_stats.putouts,
            assists=fielding_stats.assists,
            errors=fielding_stats.errors,
            throwing_errors=fielding_stats.throwing_errors,
            double_plays=fielding_stats.double_plays,
            triple_plays=fielding_stats.triple_plays,
            fielding_percentage=fielding_stats.fielding_percentage,
            defensive_efficiency_ratio=fielding_stats.defensive_efficiency_ratio,
            range_factor_per_game=fielding_stats.range_factor_per_game,
            range_factor_per_nine=fielding_stats.range_factor_per_nine,
            outfield_assists=fielding_stats.outfield_assists,
            passed_balls=fielding_stats.passed_balls,
            wild_pitches=fielding_stats.wild_pitches,
            stolen_bases_allowed=fielding_stats.stolen_bases_allowed,
            caught_stealing=fielding_stats.caught_stealing,
            stolen_base_percentage=fielding_stats.stolen_base_percentage,
            catchers_interference=fielding_stats.catchers_interference,
            pickoffs=fielding_stats.pickoffs,
        )
        self.session.add(stats_model)
        self.session.commit()
        self.session.refresh(stats_model)
        return await self.get_by_id(stats_model.id)

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
        stats_model = self.session.query(FieldingStatsModel).filter(FieldingStatsModel.id == stats_id).first()
        if not stats_model:
            return False

        self.session.delete(stats_model)
        self.session.commit()
        return True

    def _model_to_entity(self, model: FieldingStatsModel) -> FieldingStats:
        """Convert a FieldingStatsModel to a FieldingStats entity."""
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
        model.games_played = entity.games_played
        model.games_started = entity.games_started
        model.innings_played = entity.innings_played
        model.total_chances = entity.total_chances
        model.putouts = entity.putouts
        model.assists = entity.assists
        model.errors = entity.errors
        model.throwing_errors = entity.throwing_errors
        model.double_plays = entity.double_plays
        model.triple_plays = entity.triple_plays
        model.fielding_percentage = entity.fielding_percentage
        model.defensive_efficiency_ratio = entity.defensive_efficiency_ratio
        model.range_factor_per_game = entity.range_factor_per_game
        model.range_factor_per_nine = entity.range_factor_per_nine
        model.outfield_assists = entity.outfield_assists
        model.passed_balls = entity.passed_balls
        model.wild_pitches = entity.wild_pitches
        model.stolen_bases_allowed = entity.stolen_bases_allowed
        model.caught_stealing = entity.caught_stealing
        model.stolen_base_percentage = entity.stolen_base_percentage
        model.catchers_interference = entity.catchers_interference
        model.pickoffs = entity.pickoffs
