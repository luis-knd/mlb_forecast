from application.ports.mlb_api import MLBApiPort
from application.ports.team_repository import TeamRepositoryPort
from domain.entities.team import Team
from domain.exceptions import InvalidDataError, TeamNotFoundError

VALID_LEAGUES = {"American League", "American", "National League", "National"}
VALID_DIVISIONS = {"East", "West", "Central"}
CACHE_TIMEOUT_IN_SECONDS = 3600


class ListTeamsUseCase:
    def __init__(self, team_repository: TeamRepositoryPort):
        self.team_repository = team_repository

    async def execute(self, league: str | None = None, division: str | None = None) -> list[Team]:
        normalized_league = self._normalize_league(league) if league else None
        normalized_division = self._normalize_division(division) if division else None

        return await self._fetch_teams(normalized_league, normalized_division)

    async def _fetch_teams(self, league: str | None, division: str | None) -> list[Team]:
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
            raise InvalidDataError(f"Invalid league: `{league}`. Expected one of these values: {VALID_LEAGUES}")

        return league_clean

    def _normalize_division(self, division: str) -> str:
        if not division:
            raise ValueError("Division cannot be empty")

        division_clean = division.strip().title()
        if division_clean not in VALID_DIVISIONS:
            raise InvalidDataError(f"Invalid division: `{division}`. Expected one of these values: {VALID_DIVISIONS}")

        return division_clean


class GetTeamUseCase:
    def __init__(self, team_repository: TeamRepositoryPort):
        self.team_repository = team_repository

    async def execute(self, team_id: int) -> Team | None:
        if team_id is None or team_id <= 0:
            raise InvalidDataError("Invalid team ID. Must be a positive integer")

        team = await self.team_repository.get_by_id(team_id)

        if not team:
            raise TeamNotFoundError(team_id)

        return team


class IngestTeamsUseCase:
    def __init__(self, team_repository: TeamRepositoryPort, mlb_api: MLBApiPort):
        self.team_repository = team_repository
        self.mlb_api = mlb_api

    async def execute(self) -> list[Team]:
        teams_dto = await self.mlb_api.get_teams()

        ingested_teams = []
        for team_dto in teams_dto:
            team = Team.create(
                mlb_id=team_dto.id,
                name=team_dto.name,
                abbreviation=team_dto.abbreviation,
                city=team_dto.city,
                division=team_dto.division,
                league=team_dto.league,
                venue_name=team_dto.venue_name,
            )

            saved_team = await self.team_repository.save(team)
            ingested_teams.append(saved_team)

        return ingested_teams
