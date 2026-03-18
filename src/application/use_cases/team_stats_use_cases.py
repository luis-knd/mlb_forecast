"""
Use cases for team statistics operations.
These define the application's business logic for team statistics operations.
"""

from typing import Any

from application.ports.cache import CachePort
from application.ports.mlb_api import MLBApiPort
from application.ports.team_repository import TeamRepositoryPort
from application.ports.team_stats_repository import TeamStatsRepositoryPort
from domain.entities.team_stats import TeamStats
from domain.value_objects.team_stats_category import TeamStatsCategory


class GetTeamStatsUseCase:
    """Use case for getting team statistics."""

    CACHE_TTL_SECONDS = 3600
    CATEGORY_KEYS = {
        TeamStatsCategory.HITTING: ("hitting_stats", "hitting"),
        TeamStatsCategory.PITCHING: ("pitching_stats", "pitching"),
        TeamStatsCategory.FIELDING: ("fielding_stats", "fielding"),
        TeamStatsCategory.CATCHING: ("catching_stats", "catching"),
    }

    def __init__(self, team_stats_repository: TeamStatsRepositoryPort, cache: CachePort):
        self.team_stats_repository = team_stats_repository
        self.cache = cache

    async def execute(
        self,
        team_id: int,
        season: int,
        category: TeamStatsCategory = TeamStatsCategory.ALL,
    ) -> dict[str, Any] | None:
        """
        Get statistics for a specific team and season.

        Args:
            team_id: The ID of the team
            season: The season year
            category: Optional stats category to filter

        Returns:
            Aggregated statistics dictionary or None if not found
        """
        cache_key = self._build_cache_key(team_id, season, category)
        cached_stats = await self.cache.get(cache_key)
        if cached_stats is not None:
            return cached_stats

        team_stats = await self.team_stats_repository.get_by_team_and_season(team_id, season)

        if not team_stats:
            return None

        filtered_stats = self._filter_by_category(team_stats, category)

        await self.cache.set(cache_key, filtered_stats, ttl=self.CACHE_TTL_SECONDS)

        return filtered_stats

    def _filter_by_category(self, stats: dict[str, Any], category: TeamStatsCategory) -> dict[str, Any]:
        if category is TeamStatsCategory.ALL:
            return stats

        filtered_stats = dict(stats)
        for cat, keys in self.CATEGORY_KEYS.items():
            if cat is category:
                continue
            for key in keys:
                if key in filtered_stats:
                    filtered_stats[key] = None
        return filtered_stats

    def _build_cache_key(self, team_id: int, season: int, category: TeamStatsCategory) -> str:
        base_key = f"team_stats:{team_id}:{season}"
        if category is TeamStatsCategory.ALL:
            return base_key
        return f"{base_key}:{category.value}"


class ListTeamStatsBySeason:
    """Use case for listing team statistics by season."""

    def __init__(self, team_stats_repository: TeamStatsRepositoryPort):
        self.team_stats_repository = team_stats_repository

    async def execute(self, season: int) -> list[TeamStats]:
        """
        List statistics for all teams in a specific season.

        Args:
            season: The season year

        Returns:
            List of TeamStats entities
        """
        return await self.team_stats_repository.list_by_season(season)


class ListTopTeamsByStatUseCase:
    """Use case for listing top teams by a specific statistic."""

    def __init__(self, team_stats_repository: TeamStatsRepositoryPort):
        self.team_stats_repository = team_stats_repository

    async def execute(self, season: int, stat_name: str, limit: int = 10, descending: bool = True) -> list[TeamStats]:
        """
        List top teams by a specific statistic.

        Args:
            season: The season year
            stat_name: The name of the statistic to sort by
            limit: Maximum number of teams to return
            descending: Whether to sort in descending order

        Returns:
            List of TeamStats entities
        """
        return await self.team_stats_repository.list_top_teams_by_stat(season, stat_name, limit, descending)


class IngestTeamStatsUseCase:
    """Use case for ingesting team statistics from the MLB API."""

    def __init__(
        self,
        team_stats_repository: TeamStatsRepositoryPort,
        team_repository: TeamRepositoryPort,
        mlb_api: MLBApiPort,
    ):
        self.team_stats_repository = team_stats_repository
        self.team_repository = team_repository
        self.mlb_api = mlb_api

    async def execute(self, season: int) -> list[TeamStats]:
        """
        Ingest team statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested TeamStats entities
        """
        # Get all teams
        teams = await self.team_repository.list_all()

        # Ingest stats for each team
        ingested_stats = []
        for team in teams:
            # Get team stats from MLB API - correct parameter order: team_id as int, season as str
            stats_data = await self.mlb_api.get_team_stats(team.mlb_id, str(season))
            if not stats_data:
                continue

            # Validate team.id is not None before creating TeamStats
            if team.id is None:
                continue

            # Create TeamStats entity
            team_stats = TeamStats.create(
                team_id=team.id,
                season=season,
                games_played=stats_data.get("games_played", 0),
                wins=stats_data.get("wins", 0),
                losses=stats_data.get("losses", 0),
                runs_scored=stats_data.get("runs_scored", 0),
                hits=stats_data.get("hits", 0),
                home_runs=stats_data.get("home_runs", 0),
                batting_average=stats_data.get("batting_average", 0.0),
                on_base_percentage=stats_data.get("on_base_percentage", 0.0),
                slugging_percentage=stats_data.get("slugging_percentage", 0.0),
                ops=stats_data.get("ops", 0.0),
                stolen_bases=stats_data.get("stolen_bases", 0),
                earned_run_average=stats_data.get("earned_run_average", 0.0),
                whip=stats_data.get("whip", 0.0),
                strikeouts_per_nine=stats_data.get("strikeouts_per_nine", 0.0),
                walks_per_nine=stats_data.get("walks_per_nine", 0.0),
                home_runs_allowed=stats_data.get("home_runs_allowed", 0),
                runs_allowed=stats_data.get("runs_allowed", 0),
                fielding_percentage=stats_data.get("fielding_percentage", 0.0),
                errors=stats_data.get("errors", 0),
                double_plays=stats_data.get("double_plays", 0),
            )

            # Save to repository
            saved_stats = await self.team_stats_repository.save(team_stats)
            ingested_stats.append(saved_stats)

        return ingested_stats


class UpdateTeamStatsUseCase:
    """Use case for updating specific team statistics."""

    def __init__(self, team_stats_repository: TeamStatsRepositoryPort):
        self.team_stats_repository = team_stats_repository

    async def execute(self, stats_id: int, updated_stats: dict[str, Any]) -> TeamStats | None:
        """
        Update specific statistics for a team.

        Args:
            stats_id: The ID of the team statistics to update
            updated_stats: Dictionary of statistics to update

        Returns:
            Updated TeamStats entity or None if update failed
        """
        # Update in repository
        updated_team_stats = await self.team_stats_repository.update_stats(stats_id, updated_stats)

        if updated_team_stats:
            # Update run differential and Pythagorean expectation
            updated_team_stats.update_run_differential()

            # Save the updated stats
            updated_team_stats = await self.team_stats_repository.save(updated_team_stats)

        return updated_team_stats
