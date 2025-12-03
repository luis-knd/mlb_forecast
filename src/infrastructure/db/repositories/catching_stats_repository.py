"""
Implementation of the CatchingStatsRepositoryPort interface using SQLAlchemy.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.application.ports.catching_stats_repository import CatchingStatsRepositoryPort
from src.domain.entities.catching_stats import CatchingStats
from src.domain.entities.team import Team
from src.infrastructure.db.models import CatchingStatsModel


class CatchingStatsRepository(CatchingStatsRepositoryPort):
    """Implementation of the CatchingStatsRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, stats_id: int) -> Optional[CatchingStats]:
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

    async def get_by_team_and_season(self, team_id: int, season: int) -> Optional[CatchingStats]:
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

    async def list_by_team(self, team_id: int) -> List[CatchingStats]:
        """List all catching statistics for a specific team across seasons."""
        stats_models = (
            self.session.query(CatchingStatsModel)
            .options(joinedload(CatchingStatsModel.team))
            .filter(CatchingStatsModel.team_id == team_id)
            .order_by(CatchingStatsModel.season.desc())
            .all()
        )
        return [self._model_to_entity(model) for model in stats_models]

    async def list_by_season(self, season: int) -> List[CatchingStats]:
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
    ) -> List[CatchingStats]:
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
        # Check if catching stats already exists
        if catching_stats.id:
            stats_model = (
                self.session.query(CatchingStatsModel).filter(CatchingStatsModel.id == catching_stats.id).first()
            )
            if stats_model:
                # Update existing catching stats
                self._update_stats_model(stats_model, catching_stats)
                self.session.commit()
                return await self.get_by_id(stats_model.id)

        # Check if catching stats exists by team_id and season
        stats_model = (
            self.session.query(CatchingStatsModel)
            .filter(
                CatchingStatsModel.team_id == catching_stats.team_id,
                CatchingStatsModel.season == catching_stats.season,
            )
            .first()
        )
        if stats_model:
            # Update existing catching stats
            self._update_stats_model(stats_model, catching_stats)
            self.session.commit()
            return await self.get_by_id(stats_model.id)

        # Create new catching stats
        stats_model = CatchingStatsModel(
            team_id=catching_stats.team_id,
            season=catching_stats.season,
            games_played=catching_stats.games_played,
            games_pitched=catching_stats.games_pitched,
            at_bats=catching_stats.at_bats,
            hits=catching_stats.hits,
            runs=catching_stats.runs,
            home_runs=catching_stats.home_runs,
            strikeouts=catching_stats.strikeouts,
            base_on_balls=catching_stats.base_on_balls,
            intentional_walks=catching_stats.intentional_walks,
            hit_by_pitch=catching_stats.hit_by_pitch,
            total_bases=catching_stats.total_bases,
            sacrifice_bunts=catching_stats.sacrifice_bunts,
            sacrifice_flies=catching_stats.sacrifice_flies,
            batting_average=catching_stats.batting_average,
            on_base_percentage=catching_stats.on_base_percentage,
            slugging_percentage=catching_stats.slugging_percentage,
            ops=catching_stats.ops,
            passed_balls=catching_stats.passed_balls,
            wild_pitches=catching_stats.wild_pitches,
            stolen_bases_allowed=catching_stats.stolen_bases_allowed,
            caught_stealing=catching_stats.caught_stealing,
            stolen_base_percentage=catching_stats.stolen_base_percentage,
            pickoffs=catching_stats.pickoffs,
            pickoff_attempts=catching_stats.pickoff_attempts,
            catchers_interference=catching_stats.catchers_interference,
            earned_runs=catching_stats.earned_runs,
            batters_faced=catching_stats.batters_faced,
            hit_batsmen=catching_stats.hit_batsmen,
            strikeout_walk_ratio=catching_stats.strikeout_walk_ratio,
        )
        self.session.add(stats_model)
        self.session.commit()
        self.session.refresh(stats_model)
        return await self.get_by_id(stats_model.id)

    async def update_stats(self, stats_id: int, updated_stats: Dict[str, Any]) -> Optional[CatchingStats]:
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
        stats_model = self.session.query(CatchingStatsModel).filter(CatchingStatsModel.id == stats_id).first()
        if not stats_model:
            return False

        self.session.delete(stats_model)
        self.session.commit()
        return True

    def _model_to_entity(self, model: CatchingStatsModel) -> CatchingStats:
        """Convert a CatchingStatsModel to a CatchingStats entity."""
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

    def _update_stats_model(self, model: CatchingStatsModel, entity: CatchingStats) -> None:
        """Update a CatchingStatsModel with values from a CatchingStats entity."""
        model.team_id = entity.team_id
        model.season = entity.season
        model.games_played = entity.games_played
        model.games_pitched = entity.games_pitched
        model.at_bats = entity.at_bats
        model.hits = entity.hits
        model.runs = entity.runs
        model.home_runs = entity.home_runs
        model.strikeouts = entity.strikeouts
        model.base_on_balls = entity.base_on_balls
        model.intentional_walks = entity.intentional_walks
        model.hit_by_pitch = entity.hit_by_pitch
        model.total_bases = entity.total_bases
        model.sacrifice_bunts = entity.sacrifice_bunts
        model.sacrifice_flies = entity.sacrifice_flies
        model.batting_average = entity.batting_average
        model.on_base_percentage = entity.on_base_percentage
        model.slugging_percentage = entity.slugging_percentage
        model.ops = entity.ops
        model.passed_balls = entity.passed_balls
        model.wild_pitches = entity.wild_pitches
        model.stolen_bases_allowed = entity.stolen_bases_allowed
        model.caught_stealing = entity.caught_stealing
        model.stolen_base_percentage = entity.stolen_base_percentage
        model.pickoffs = entity.pickoffs
        model.pickoff_attempts = entity.pickoff_attempts
        model.catchers_interference = entity.catchers_interference
        model.earned_runs = entity.earned_runs
        model.batters_faced = entity.batters_faced
        model.hit_batsmen = entity.hit_batsmen
        model.strikeout_walk_ratio = entity.strikeout_walk_ratio
