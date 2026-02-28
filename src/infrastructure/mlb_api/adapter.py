"""
MLB API adapter implementation.
This module implements the MLBApiPort interface using httpx for HTTP requests.
"""

import asyncio
import logging
from datetime import date, datetime
from typing import Any, Dict, Iterator, List, Optional, Protocol

import httpx

from src.application.dto.mlb_api_response import MLBGameDTO, MLBPlayerDTO, MLBTeamDTO
from src.application.ports.mlb_api import MLBApiPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
COMPLETED_DETAILED_STATES = {"final", "completed", "game over"}
COMPLETED_ABSTRACT_STATES = {"final", "completed"}
COMPLETED_CODED_STATES = {"F", "C"}
CANCELLED_STATES = {"cancelled", "postponed", "suspended"}
IN_PROGRESS_STATES = {"in progress", "live", "in-progress"}
SCHEDULED_STATES = {"scheduled", "pre-game", "warmup", "pregame"}

TEAM_STATS_DEFAULTS: Dict[str, Any] = {
    "games_played": 0,
    "wins": 0,
    "losses": 0,
    "runs_scored": 0,
    "runs_allowed": 0,
    "hits": 0,
    "home_runs": 0,
    "batting_average": 0.0,
    "on_base_percentage": 0.0,
    "slugging_percentage": 0.0,
    "ops": 0.0,
    "stolen_bases": 0,
    "earned_run_average": 0.0,
    "strikeouts": 0,
    "walks_allowed": 0,
    "saves": 0,
    "whip": 0.0,
    "strikeouts_per_nine": 0.0,
    "walks_per_nine": 0.0,
    "home_runs_allowed": 0,
    "fielding_percentage": 0.0,
    "errors": 0,
    "double_plays": 0,
    "run_differential": 0,
    "pythagorean_expectation": 0.0,
}

FIELDING_STATS_DEFAULTS: Dict[str, Any] = {
    "games_played": 0,
    "games_started": 0,
    "innings_played": 0.0,
    "total_chances": 0,
    "putouts": 0,
    "assists": 0,
    "errors": 0,
    "throwing_errors": 0,
    "double_plays": 0,
    "triple_plays": 0,
    "fielding_percentage": 0.0,
    "defensive_efficiency_ratio": 0.0,
    "range_factor_per_game": 0.0,
    "range_factor_per_nine": 0.0,
    "outfield_assists": 0,
    "passed_balls": 0,
    "wild_pitches": 0,
    "stolen_bases_allowed": 0,
    "caught_stealing": 0,
    "stolen_base_percentage": 0.0,
    "catchers_interference": 0,
    "pickoffs": 0,
}


def _safe_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class MLBApiException(Exception):
    """Custom exception for MLB API errors."""


class _RequestContext(Protocol):
    base_url: str
    max_retries: int
    timeout: int | float
    backoff_factor: int | float


class _RequestMixin:
    async def _make_request(
        self: _RequestContext, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params or {})
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as error:
                status_code = error.response.status_code
                if status_code in RETRYABLE_STATUS_CODES and attempt < attempts:
                    await asyncio.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                    continue
                logger.error("HTTP error in %s: %s", url, status_code)
                raise MLBApiException(f"HTTP error: {status_code}") from error
            except httpx.RequestError as error:
                if attempt < attempts:
                    await asyncio.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                    continue
                logger.error("Connection error in %s: %s", url, error)
                raise MLBApiException(f"Connection error: {error}") from error
            except Exception as error:
                logger.error("Unexpected error in %s: %s", url, error)
                raise MLBApiException(f"Unexpected error: {error}") from error
        raise MLBApiException(f"Unexpected retry exhaustion for endpoint: {endpoint}")


class _TeamSplitMixin:
    @staticmethod
    def _iter_matching_team_stats(stats_data: Dict[str, Any], mlb_team_id: int) -> Iterator[tuple[str, Dict[str, Any]]]:
        for group in stats_data.get("stats", []):
            group_name = str(group.get("group", {}).get("displayName", "")).lower()
            for split in group.get("splits", []):
                if split.get("team", {}).get("id") != mlb_team_id:
                    continue
                yield group_name, split.get("stat", {})


class _TeamTransformMixin:
    def _transform_team_data(self, team_data: Dict[str, Any]) -> MLBTeamDTO:
        division_info = team_data.get("division", {})
        league_info = team_data.get("league", {})
        venue_info = team_data.get("venue", {})
        return MLBTeamDTO(
            id=int(team_data.get("id", 0)),
            name=team_data.get("name", ""),
            abbreviation=team_data.get("abbreviation", ""),
            city=team_data.get("locationName", ""),
            division=division_info.get("name", ""),
            league=league_info.get("name", ""),
            venue_name=venue_info.get("name", ""),
        )


class _GameTransformMixin:
    def _transform_game_data(self, game_data: Dict[str, Any]) -> MLBGameDTO:
        teams = game_data.get("teams", {})
        home_team_data = teams.get("home", {}).get("team", {})
        away_team_data = teams.get("away", {}).get("team", {})
        home_score = teams.get("home", {}).get("score")
        away_score = teams.get("away", {}).get("score")
        status_context = self._build_status_context(game_data)
        winning_team_id = self._resolve_winning_team_id(home_team_data, away_team_data, home_score, away_score)
        return MLBGameDTO(
            id=int(game_data.get("gamePk", 0)),
            home_team_id=int(home_team_data.get("id", 0)),
            away_team_id=int(away_team_data.get("id", 0)),
            game_date=self._parse_game_date(game_data.get("gameDate")),
            status=self._normalize_game_status(**status_context),
            scheduled_innings=game_data.get("scheduledInnings", 9),
            home_score=home_score,
            away_score=away_score,
            winning_team_id=winning_team_id,
        )

    def _parse_game_date(self, game_date_raw: Any) -> Optional[datetime]:
        if not game_date_raw:
            return None
        try:
            return datetime.fromisoformat(str(game_date_raw).replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Invalid date format: %s", game_date_raw)
            return None

    def _build_status_context(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        status_data = game_data.get("status", {})
        detailed_state = str(status_data.get("detailedState", "")).lower()
        abstract_state = str(status_data.get("abstractGameState", "")).lower()
        coded_state = str(status_data.get("codedGameState", "")).upper()
        return {
            "detailed_state": detailed_state,
            "abstract_state": abstract_state,
            "coded_state": coded_state,
            "is_rescheduled": game_data.get("rescheduledFrom") is not None,
            "is_completed": self._is_game_completed(detailed_state, abstract_state, coded_state),
        }

    def _resolve_winning_team_id(
        self,
        home_team_data: Dict[str, Any],
        away_team_data: Dict[str, Any],
        home_score: Optional[int],
        away_score: Optional[int],
    ) -> Optional[int]:
        if home_score is None or away_score is None:
            return None
        if home_score == away_score:
            return None
        if home_score > away_score:
            return home_team_data.get("id")
        return away_team_data.get("id")

    def _is_game_completed(self, detailed_state: str, abstract_state: str, coded_state: str) -> bool:
        return (
            detailed_state in COMPLETED_DETAILED_STATES
            or abstract_state in COMPLETED_ABSTRACT_STATES
            or coded_state in COMPLETED_CODED_STATES
        )

    def _normalize_game_status(
        self,
        detailed_state: str,
        abstract_state: str = "",
        coded_state: str = "",
        is_rescheduled: bool = False,
        is_completed: bool = False,
    ) -> str:
        if is_completed:
            return "completed"
        if detailed_state in CANCELLED_STATES:
            return "cancelled"
        if detailed_state in IN_PROGRESS_STATES:
            return "in_progress"
        if detailed_state in SCHEDULED_STATES:
            return "scheduled"
        if detailed_state not in {"", "unknown"}:
            logger.warning(
                "Unknown game status encountered: detailed='%s', abstract='%s', coded='%s', rescheduled=%s",
                detailed_state,
                abstract_state,
                coded_state,
                is_rescheduled,
            )
        return "scheduled"


class _TeamStatsTransformMixin(_TeamSplitMixin):
    def _transform_team_stats_data(self, stats_data: Dict[str, Any], mlb_team_id: int, season: int) -> Dict[str, Any]:
        result = {"team_id": mlb_team_id, "season": season, **TEAM_STATS_DEFAULTS}
        for group_name, stat_data in self._iter_matching_team_stats(stats_data, mlb_team_id):
            self._apply_team_group_stats(group_name, stat_data, result)
        self._apply_team_derived_metrics(result)
        return result

    def _apply_team_group_stats(self, group_name: str, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        if group_name == "hitting":
            self._process_hitting_stats(stat_data, result)
            return
        if group_name == "pitching":
            self._process_pitching_stats(stat_data, result)

    def _process_hitting_stats(self, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        mapping = {
            "gamesPlayed": "games_played",
            "runs": "runs_scored",
            "hits": "hits",
            "homeRuns": "home_runs",
            "stolenBases": "stolen_bases",
            "groundIntoDoublePlay": "double_plays",
        }
        for source_key, target_key in mapping.items():
            if source_key in stat_data:
                result[target_key] = stat_data[source_key]
        result["batting_average"] = _safe_float(stat_data.get("avg")) or result["batting_average"]
        result["on_base_percentage"] = _safe_float(stat_data.get("obp")) or result["on_base_percentage"]
        result["slugging_percentage"] = _safe_float(stat_data.get("slg")) or result["slugging_percentage"]
        result["ops"] = _safe_float(stat_data.get("ops")) or result["ops"]

    def _process_pitching_stats(self, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        mapping = {
            "wins": "wins",
            "losses": "losses",
            "saves": "saves",
            "runs": "runs_allowed",
            "homeRuns": "home_runs_allowed",
            "strikeOuts": "strikeouts",
            "baseOnBalls": "walks_allowed",
            "errors": "errors",
            "fielding_percentage": "fielding_percentage",
        }
        for source_key, target_key in mapping.items():
            if source_key in stat_data:
                result[target_key] = stat_data[source_key]
        result["earned_run_average"] = _safe_float(stat_data.get("era")) or result["earned_run_average"]
        result["whip"] = _safe_float(stat_data.get("whip")) or result["whip"]
        strikeouts_per_nine = _safe_float(stat_data.get("strikeoutsPer9Inn"))
        walks_per_nine = _safe_float(stat_data.get("walksPer9Inn"))
        result["strikeouts_per_nine"] = strikeouts_per_nine or result["strikeouts_per_nine"]
        result["walks_per_nine"] = walks_per_nine or result["walks_per_nine"]

    def _apply_team_derived_metrics(self, result: Dict[str, Any]) -> None:
        runs_scored = result["runs_scored"]
        runs_allowed = result["runs_allowed"]
        result["run_differential"] = runs_scored - runs_allowed
        if runs_scored <= 0 or runs_allowed <= 0:
            result["pythagorean_expectation"] = 0.0
            return
        result["pythagorean_expectation"] = (runs_scored**2) / ((runs_scored**2) + (runs_allowed**2))


class _PlayerTransformMixin:
    def _transform_player_data(self, player_data: Dict[str, Any]) -> MLBPlayerDTO:
        first_name, last_name = self._extract_player_names(player_data)
        position = self._extract_player_position(player_data)
        return MLBPlayerDTO(
            id=int(player_data.get("id", 0)),
            first_name=first_name,
            last_name=last_name,
            position=position,
            bats=player_data.get("batSide", {}).get("code", ""),
            throws=player_data.get("pitchHand", {}).get("code", ""),
            birth_date=self._parse_player_birth_date(player_data),
            active=player_data.get("active", True),
            current_team_id=player_data.get("currentTeam", {}).get("id"),
        )

    def _parse_player_birth_date(self, player_data: Dict[str, Any]) -> Optional[datetime]:
        birth_date = player_data.get("birthDate")
        if not birth_date:
            return None
        try:
            return datetime.fromisoformat(str(birth_date).replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Invalid birth date format: %s", birth_date)
            return None

    def _extract_player_names(self, player_data: Dict[str, Any]) -> tuple[str, str]:
        first_name = str(player_data.get("firstName", "")).strip()
        last_name = str(player_data.get("lastName", "")).strip()
        if first_name and last_name:
            return first_name, last_name
        full_name = str(player_data.get("fullName", "")).strip()
        if not full_name:
            return first_name, last_name
        split_name = full_name.split()
        if not split_name:
            return first_name, last_name
        resolved_first_name = first_name or split_name[0]
        resolved_last_name = last_name or " ".join(split_name[1:])
        return resolved_first_name, resolved_last_name

    def _extract_player_position(self, player_data: Dict[str, Any]) -> str:
        position = self._extract_position_value(player_data.get("position"))
        if position:
            return position
        return self._extract_position_value(player_data.get("primaryPosition"))

    @staticmethod
    def _extract_position_value(position_data: Any) -> str:
        if isinstance(position_data, dict):
            for field in ("abbreviation", "code", "name"):
                value = str(position_data.get(field, "")).strip()
                if value:
                    return value
            return ""
        if position_data is None:
            return ""
        return str(position_data).strip()

    def _transform_player_stats_data(
        self,
        stats_data: Dict[str, Any],
        mlb_player_id: int,
        stats: str,
        group: str,
        season: Optional[int] = None,
        game_type: Optional[str] = None,
        days_back: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "player_id": mlb_player_id,
            "stats": stats,
            "group": group,
            "season": season,
            "game_type": game_type,
            "days_back": days_back,
            "stats_data": stats_data.get("stats", []),
        }


class _FieldingStatsTransformMixin(_TeamSplitMixin):
    def _transform_fielding_stats_data(
        self,
        stats_data: Dict[str, Any],
        mlb_team_id: int,
        season: int,
    ) -> Dict[str, Any]:
        result = {"team_id": mlb_team_id, "season": season, **FIELDING_STATS_DEFAULTS}
        for group_name, stat_data in self._iter_matching_team_stats(stats_data, mlb_team_id):
            if group_name == "fielding":
                self._process_fielding_stats(stat_data, result)
        return result

    def _process_fielding_stats(self, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        self._apply_fielding_raw_stats(stat_data, result)
        self._apply_fielding_percentage_stats(stat_data, result)
        self._apply_fielding_derived_stats(result)

    def _apply_fielding_raw_stats(self, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        mapping = {
            "gamesPlayed": "games_played",
            "gamesStarted": "games_started",
            "chances": "total_chances",
            "putOuts": "putouts",
            "assists": "assists",
            "errors": "errors",
            "throwingErrors": "throwing_errors",
            "doublePlays": "double_plays",
            "triplePlays": "triple_plays",
            "outfieldAssists": "outfield_assists",
            "passedBall": "passed_balls",
            "wildPitches": "wild_pitches",
            "stolenBases": "stolen_bases_allowed",
            "caughtStealing": "caught_stealing",
            "catchersInterference": "catchers_interference",
            "pickoffs": "pickoffs",
        }
        for source_key, target_key in mapping.items():
            if source_key in stat_data:
                result[target_key] = stat_data[source_key]
        innings_played = _safe_float(stat_data.get("innings"))
        if innings_played:
            result["innings_played"] = innings_played

    def _apply_fielding_percentage_stats(self, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        fielding_percentage = _safe_float(stat_data.get("fielding"))
        stolen_base_percentage = _safe_float(stat_data.get("stolenBasePercentage"))
        if fielding_percentage:
            result["fielding_percentage"] = fielding_percentage
        if stolen_base_percentage:
            result["stolen_base_percentage"] = stolen_base_percentage

    def _apply_fielding_derived_stats(self, result: Dict[str, Any]) -> None:
        successful_plays = result["putouts"] + result["assists"]
        if result["total_chances"] > 0 and result["fielding_percentage"] == 0.0:
            result["fielding_percentage"] = successful_plays / result["total_chances"]
        if result["games_played"] > 0 and result["range_factor_per_game"] == 0.0:
            result["range_factor_per_game"] = successful_plays / result["games_played"]
        if result["innings_played"] > 0 and result["range_factor_per_nine"] == 0.0:
            result["range_factor_per_nine"] = (successful_plays * 9) / result["innings_played"]


class MLBApiAdapter(
    _RequestMixin,
    _TeamTransformMixin,
    _GameTransformMixin,
    _TeamStatsTransformMixin,
    _PlayerTransformMixin,
    _FieldingStatsTransformMixin,
    MLBApiPort,
):
    """Implementation of the MLBApiPort interface using httpx."""

    def __init__(self):
        self.base_url = settings.MLB_API_BASE_URL
        self.api_version = settings.MLB_API_VERSION
        self.timeout = settings.MLB_API_TIMEOUT
        self.max_retries = settings.MLB_API_MAX_RETRIES
        self.backoff_factor = settings.MLB_API_BACKOFF_FACTOR

    async def get_teams(self) -> List[MLBTeamDTO]:
        endpoint = f"/{self.api_version}/teams"
        params = {"sportId": 1}
        data = await self._make_request(endpoint, params)
        return [self._transform_team_data(team) for team in data.get("teams", [])]

    async def get_team_by_id(self, mlb_team_id: int) -> Optional[MLBTeamDTO]:
        endpoint = f"/{self.api_version}/teams/{mlb_team_id}"
        try:
            data = await self._make_request(endpoint)
            teams_data = data.get("teams", [])
            if not teams_data:
                return None
            return self._transform_team_data(teams_data[0])
        except MLBApiException:
            logger.warning("Team with MLB ID %s not found", mlb_team_id)
            return None

    async def get_games_by_date(self, game_date: date) -> List[MLBGameDTO]:
        endpoint = f"/{self.api_version}/schedule"
        params = {"sportId": 1, "date": game_date.strftime("%Y-%m-%d")}
        data = await self._make_request(endpoint, params)
        return [
            self._transform_game_data(game_data)
            for date_info in data.get("dates", [])
            for game_data in date_info.get("games", [])
        ]

    async def get_game_by_id(self, mlb_game_id: int) -> Optional[MLBGameDTO]:
        endpoint = f"/{self.api_version}/game/{mlb_game_id}/feed/live"
        try:
            data = await self._make_request(endpoint)
            return self._transform_game_data(data)
        except MLBApiException:
            logger.warning("Game with MLB ID %s not found", mlb_game_id)
            return None

    async def get_team_stats(
        self,
        season: int,
        group: str,
        mlb_team_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint = f"/{self.api_version}/teams/stats"
        params: Dict[str, Any] = {
            "season": season,
            "sportId": 1,
            "group": group,
            "stats": "season",
        }
        if mlb_team_id is not None:
            params["teamId"] = mlb_team_id
        try:
            return await self._make_request(endpoint, params)
        except MLBApiException:
            logger.warning("Stats not found: group=%s, team=%s, season=%s", group, mlb_team_id or "all", season)
            return None

    async def get_player_by_id(self, mlb_player_id: int) -> Optional[MLBPlayerDTO]:
        endpoint = f"/{self.api_version}/people/{mlb_player_id}"
        try:
            data = await self._make_request(endpoint)
            people_data = data.get("people", [])
            if not people_data:
                return None
            return self._transform_player_data(people_data[0])
        except MLBApiException:
            logger.warning("Player with MLB ID %s not found", mlb_player_id)
            return None

    async def get_players_by_team(
        self,
        mlb_team_id: int,
        season: Optional[int] = None,
        roster_type: str = "active",
    ) -> List[MLBPlayerDTO]:
        endpoint = f"/{self.api_version}/teams/{mlb_team_id}/roster"
        params: Dict[str, Any] = {"rosterType": roster_type}
        if season is not None:
            params["season"] = season
        try:
            data = await self._make_request(endpoint, params)
            players: List[MLBPlayerDTO] = []
            for roster_entry in data.get("roster", []):
                player_data = dict(roster_entry.get("person", {}))
                player_data["position"] = roster_entry.get("position", {}).get("abbreviation", "")
                players.append(self._transform_player_data(player_data))
            return players
        except MLBApiException:
            logger.warning("Roster for team with MLB ID %s not found", mlb_team_id)
            return []

    async def get_players_by_sport(
        self,
        sport_id: int = 1,
        season: Optional[int] = None,
        team_mlb_id: Optional[int] = None,
    ) -> List[MLBPlayerDTO]:
        endpoint = f"/{self.api_version}/sports/{sport_id}/players"
        params: Dict[str, Any] = {}
        if season is not None:
            params["season"] = season
        if team_mlb_id is not None:
            params["teamId"] = team_mlb_id
        try:
            data = await self._make_request(endpoint, params)
            return [self._transform_player_data(player) for player in data.get("people", [])]
        except MLBApiException:
            logger.warning("Players not found for sport=%s, season=%s, team=%s", sport_id, season, team_mlb_id)
            return []

    async def get_player_stats(
        self,
        mlb_player_id: int,
        stats: str,
        group: str,
        season: Optional[int] = None,
        game_type: Optional[str] = None,
        days_back: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint = f"/{self.api_version}/people/{mlb_player_id}/stats"
        params: Dict[str, Any] = {"stats": stats, "group": group}
        if season is not None:
            params["season"] = season
        if game_type:
            params["gameType"] = game_type
        if days_back is not None:
            params["daysBack"] = days_back
        try:
            data = await self._make_request(endpoint, params)
            return self._transform_player_stats_data(
                stats_data=data,
                mlb_player_id=mlb_player_id,
                stats=stats,
                group=group,
                season=season,
                game_type=game_type,
                days_back=days_back,
            )
        except MLBApiException:
            logger.warning(
                "Stats not found for player_id=%s, stats=%s, group=%s, season=%s, game_type=%s, days_back=%s",
                mlb_player_id,
                stats,
                group,
                season,
                game_type,
                days_back,
            )
            return None

    async def search_players(self, query: str) -> List[MLBPlayerDTO]:
        endpoint = f"/{self.api_version}/people/search"
        try:
            data = await self._make_request(endpoint, params={"q": query})
            return [self._transform_player_data(player) for player in data.get("people", [])]
        except MLBApiException:
            logger.warning("No players found for query: %s", query)
            return []
