from typing import List, Optional

from src.application.ports.cache import CachePort
from src.application.ports.mlb_api import MLBApiPort
from src.application.ports.team_repository import TeamRepositoryPort
from src.domain.entities.team import Team
from src.interface.rest.exception_handlers import DomainExceptions

VALID_LEAGUES = {"American League", "American", "National League", "National"}
VALID_DIVISIONS = {"East", "West", "Central"}
CACHE_TIMEOUT_IN_SECONDS = 3600


class ListTeamsUseCase:
    def __init__(self, team_repository: TeamRepositoryPort, cache: CachePort):
        self.team_repository = team_repository
        self.cache = cache

    async def execute(self, league: Optional[str] = None, division: Optional[str] = None) -> List[Team]:
        normalized_league = self._normalize_league(league) if league else None
        normalized_division = self._normalize_division(division) if division else None

        cache_key = f"teams:list:{normalized_league or 'all'}:{normalized_division or 'all'}"

        cached_teams = await self.cache.get(cache_key)
        if cached_teams:
            return cached_teams

        teams = await self._fetch_teams(normalized_league, normalized_division)

        await self.cache.set(cache_key, teams, ttl=CACHE_TIMEOUT_IN_SECONDS)
        return teams

    async def _fetch_teams(self, league: Optional[str], division: Optional[str]) -> List[Team]:
        if league and division:
            return await self.team_repository.list_by_league_and_division(league, division)
        elif league:
            return await self.team_repository.list_by_league(league)
        elif division:
            return await self.team_repository.list_by_division(division)
        else:
            return await self.team_repository.list_all()

    def _normalize_league(self, league: str) -> str:
        if not league:
            raise ValueError("League cannot be empty")

        league_clean = league.strip().title()
        if league_clean not in VALID_LEAGUES:
            raise DomainExceptions.InvalidDataError(
                f"Invalid league: `{league}`. Expected one of these values: {VALID_LEAGUES}"
            )

        return league_clean

    def _normalize_division(self, division: str) -> str:
        if not division:
            raise ValueError("Division cannot be empty")

        division_clean = division.strip().title()
        if division_clean not in VALID_DIVISIONS:
            raise DomainExceptions.InvalidDataError(
                f"Invalid division: `{division}`. Expected one of these values: {VALID_DIVISIONS}"
            )

        return division_clean


class GetTeamUseCase:

    def __init__(self, team_repository: TeamRepositoryPort, cache: CachePort):
        self.team_repository = team_repository
        self.cache = cache

    async def execute(self, team_id: int) -> Optional[Team]:
        if team_id is None or team_id <= 0:
            raise DomainExceptions.InvalidDataError("Invalid team ID. Must be a positive integer")

        cache_key = f"teams:id:{team_id}"
        cached_team = await self.cache.get(cache_key)
        if cached_team:
            return cached_team

        team = await self.team_repository.get_by_id(team_id)

        if not team:
            raise DomainExceptions.TeamNotFoundError(team_id)

        await self.cache.set(cache_key, team, ttl=CACHE_TIMEOUT_IN_SECONDS)
        return team


class IngestTeamsUseCase:

    def __init__(self, team_repository: TeamRepositoryPort, mlb_api: MLBApiPort, cache: CachePort):
        self.team_repository = team_repository
        self.mlb_api = mlb_api
        self.cache = cache

    async def execute(self) -> List[Team]:
        teams_data = await self.mlb_api.get_teams()

        ingested_teams = []
        for team_data in teams_data:
            team = Team.create(
                mlb_id=team_data["id"],
                name=team_data["name"],
                abbreviation=team_data["abbreviation"],
                city=team_data["city"],
                division=team_data["division"],
                league=team_data["league"],
                venue_name=team_data.get("venue_name"),
            )

            saved_team = await self.team_repository.save(team)
            ingested_teams.append(saved_team)

        await self.cache.clear(pattern="teams:*")
        return ingested_teams
