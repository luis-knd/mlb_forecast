"""
MLB API adapter implementation.
This module implements the MLBApiPort interface using httpx for HTTP requests.
"""

import asyncio
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import httpx

from src.application.dto.mlb_api_response import MLBGameDTO, MLBPlayerDTO, MLBTeamDTO
from src.application.ports.mlb_api import MLBApiPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class MLBApiException(Exception):
    """Custom exception for MLB API errors."""

    pass


class MLBApiAdapter(MLBApiPort):
    """Implementation of the MLBApiPort interface using httpx."""

    def __init__(self):
        self.base_url = settings.MLB_API_BASE_URL
        self.api_version = settings.MLB_API_VERSION
        self.timeout = settings.MLB_API_TIMEOUT
        self.max_retries = settings.MLB_API_MAX_RETRIES
        self.backoff_factor = settings.MLB_API_BACKOFF_FACTOR

    async def get_teams(self) -> List[MLBTeamDTO]:
        """Get all MLB teams from the API."""
        endpoint = f"/{self.api_version}/teams"
        params = {"sportId": 1}

        data = await self._make_request(endpoint, params)
        teams_data = data.get("teams", [])

        # Transform the data to match our domain model
        return [self._transform_team_data(team) for team in teams_data]

    async def get_team_by_id(self, mlb_team_id: int) -> Optional[MLBTeamDTO]:
        """Get a specific team by its MLB ID."""
        endpoint = f"/{self.api_version}/teams/{mlb_team_id}"

        try:
            data = await self._make_request(endpoint)
            teams_data = data.get("teams", [])

            if not teams_data:
                return None

            return self._transform_team_data(teams_data[0])
        except MLBApiException:
            logger.warning(f"Team with MLB ID {mlb_team_id} not found")
            return None

    async def get_games_by_date(self, game_date: date) -> List[MLBGameDTO]:
        """Get all games for a specific date."""
        endpoint = f"/{self.api_version}/schedule"
        params = {"sportId": 1, "date": game_date.strftime("%Y-%m-%d")}

        data = await self._make_request(endpoint, params)
        dates_data = data.get("dates", [])

        games = []
        for date_info in dates_data:
            games_data = date_info.get("games", [])
            for game_data in games_data:
                games.append(self._transform_game_data(game_data))

        return games

    async def get_game_by_id(self, mlb_game_id: int) -> Optional[MLBGameDTO]:
        """Get a specific game by its MLB ID."""
        endpoint = f"/{self.api_version}/game/{mlb_game_id}/feed/live"

        try:
            data = await self._make_request(endpoint)
            return self._transform_game_data(data)
        except MLBApiException:
            logger.warning(f"Game with MLB ID {mlb_game_id} not found")
            return None

    async def get_team_stats(
        self, season: int, group: str, mlb_team_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific team and season, or all teams if mlb_team_id is None."""
        endpoint = f"/{self.api_version}/teams/stats"
        params = {
            "season": season,
            "sportId": 1,
            "group": group,
            "stats": "season",
        }

        # If a specific team is requested, add the team parameter
        if mlb_team_id is not None:
            params["teamId"] = mlb_team_id

        try:
            data = await self._make_request(endpoint, params)
            return data  # Return the raw data structure
        except MLBApiException:
            logger.warning(f"Stats not found: group={group}, team={mlb_team_id or 'all'}, season={season}")
            return None

    async def get_player_by_id(self, mlb_player_id: int) -> Optional[MLBPlayerDTO]:
        """Get a specific player by its MLB ID."""
        endpoint = f"/{self.api_version}/people/{mlb_player_id}"

        try:
            data = await self._make_request(endpoint)
            people_data = data.get("people", [])

            if not people_data:
                return None

            return self._transform_player_data(people_data[0])
        except MLBApiException:
            logger.warning(f"Player with MLB ID {mlb_player_id} not found")
            return None

    async def get_players_by_team(
        self,
        mlb_team_id: int,
        season: Optional[int] = None,
        roster_type: str = "active",
    ) -> List[MLBPlayerDTO]:
        """Get players for a specific team/season and roster type."""
        endpoint = f"/{self.api_version}/teams/{mlb_team_id}/roster"
        params: Dict[str, Any] = {"rosterType": roster_type}
        if season is not None:
            params["season"] = season

        try:
            data = await self._make_request(endpoint, params)
            roster_data = data.get("roster", [])

            players = []
            for roster_entry in roster_data:
                player_data = roster_entry.get("person", {})
                position_data = roster_entry.get("position", {})

                # Add position to player data
                player_data["position"] = position_data.get("abbreviation", "")

                players.append(self._transform_player_data(player_data))

            return players
        except MLBApiException:
            logger.warning(f"Roster for team with MLB ID {mlb_team_id} not found")
            return []

    async def get_players_by_sport(self, sport_id: int = 1, season: Optional[int] = None) -> List[MLBPlayerDTO]:
        """Get players by sport and optional season."""
        endpoint = f"/{self.api_version}/sports/{sport_id}/players"
        params: Dict[str, Any] = {}
        if season is not None:
            params["season"] = season

        try:
            data = await self._make_request(endpoint, params)
            people_data = data.get("people", [])
            return [self._transform_player_data(player) for player in people_data]
        except MLBApiException:
            logger.warning(f"Players not found for sport={sport_id}, season={season}")
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
        """Get player statistics using StatsAPI filters."""
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
        """Search for players by name or other criteria."""
        endpoint = f"/{self.api_version}/people/search"
        params = {"q": query}

        try:
            data = await self._make_request(endpoint, params)
            people_data = data.get("people", [])

            return [self._transform_player_data(player) for player in people_data]
        except MLBApiException:
            logger.warning(f"No players found for query: {query}")
            return []

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a request to the MLB API with retry/backoff for transient failures."""
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
                should_retry = status_code in {429, 500, 502, 503, 504}
                if should_retry and attempt < attempts:
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

    def _transform_team_data(self, team_data: Dict[str, Any]) -> MLBTeamDTO:
        """Transform team data from the MLB API to match our domain model."""
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

    def _transform_game_data(self, game_data: Dict[str, Any]) -> MLBGameDTO:
        """Transform game data from the MLB API to match our domain model."""
        teams = game_data.get("teams", {})
        home_team_data = teams.get("home", {}).get("team", {})
        away_team_data = teams.get("away", {}).get("team", {})
        status_data = game_data.get("status", {})

        # Parse game date
        game_date_str = game_data.get("gameDate")
        game_date = None
        if game_date_str:
            try:
                game_date = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid date format: {game_date_str}")

        # Get scores if available
        home_score = teams.get("home", {}).get("score")
        away_score = teams.get("away", {}).get("score")

        # Get status information
        status_state = status_data.get("detailedState", "").lower()
        abstract_game_state = status_data.get("abstractGameState", "").lower()
        coded_game_state = status_data.get("codedGameState", "").upper()

        # Enhanced status determination for rescheduled games
        is_rescheduled = game_data.get("rescheduledFrom") is not None
        is_completed = self._is_game_completed(status_state, abstract_game_state, coded_game_state)

        # Determine winner if game is completed
        winning_team_id = None
        if is_completed and home_score is not None and away_score is not None:
            if home_score > away_score:
                winning_team_id = home_team_data.get("id")
            elif away_score > home_score:
                winning_team_id = away_team_data.get("id")
            # If scores are equal, winning_team_id remains None (tie)

        # Get the normalized status
        normalized_status = self._normalize_game_status(
            status_state,
            abstract_game_state,
            coded_game_state,
            is_rescheduled,
            is_completed,
        )

        return MLBGameDTO(
            id=int(game_data.get("gamePk", 0)),
            home_team_id=int(home_team_data.get("id", 0)),
            away_team_id=int(away_team_data.get("id", 0)),
            game_date=game_date,
            status=normalized_status,
            scheduled_innings=game_data.get("scheduledInnings", 9),
            home_score=home_score,
            away_score=away_score,
            winning_team_id=winning_team_id,
        )

    def _is_game_completed(self, detailed_state: str, abstract_state: str, coded_state: str) -> bool:
        """Determine if a game has been completed based on multiple status indicators."""
        completed_detailed_states = {"final", "completed", "game over"}
        completed_abstract_states = {"final", "completed"}
        completed_coded_states = {"F", "C"}  # F = Final, C = Completed

        return (
            detailed_state in completed_detailed_states
            or abstract_state in completed_abstract_states
            or coded_state in completed_coded_states
        )

    def _normalize_game_status(
        self,
        detailed_state: str,
        abstract_state: str = "",
        coded_state: str = "",
        is_rescheduled: bool = False,
        is_completed: bool = False,
    ) -> str:
        """
        Normalize game status to our domain values with enhanced logic for rescheduled games.

        Args:
            detailed_state: The detailed state from MLB API
            abstract_state: The abstract game state from MLB API
            coded_state: The coded game state from MLB API
            is_rescheduled: Whether the game was rescheduled
            is_completed: Whether the game is completed based on multiple indicators
        """
        detailed_state_lower = detailed_state.lower()
        abstract_state_lower = abstract_state.lower()

        # Priority 1: Check if game is completed using multiple indicators
        if is_completed:
            return "completed"

        # Priority 2: Handle cancelled/postponed states
        cancelled_states = {"cancelled", "postponed", "suspended"}
        if detailed_state_lower in cancelled_states:
            return "cancelled"

        # Priority 3: Handle in-progress states
        in_progress_states = {"in progress", "live", "in-progress"}
        if detailed_state_lower in in_progress_states:
            return "in_progress"

        # Priority 4: Handle scheduled states (default for most cases)
        scheduled_states = {"scheduled", "pre-game", "warmup", "pregame"}
        if detailed_state_lower in scheduled_states:
            return "scheduled"

        # Default fallback - log for investigation
        if detailed_state_lower not in {"", "unknown"}:
            logger.warning(
                f"Unknown game status encountered: detailed='{detailed_state}', "
                f"abstract='{abstract_state_lower}', coded='{coded_state}', "
                f"rescheduled={is_rescheduled}"
            )

        return "scheduled"

    def _transform_team_stats_data(self, stats_data: Dict[str, Any], mlb_team_id: int, season: int) -> Dict[str, Any]:
        """Transform team stats data from the MLB API to match our domain model."""
        stats_groups = stats_data.get("stats", [])

        # Initialize with default values
        result = {
            "team_id": mlb_team_id,
            "season": season,
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

        # Process each stats group (hitting and pitching)
        for group in stats_groups:
            group_info = group.get("group", {})
            group_name = group_info.get("displayName", "")

            splits = group.get("splits", [])
            for split in splits:
                # Verify that the split corresponds to the current team
                split_team = split.get("team", {})
                split_team_id = split_team.get("id")

                if split_team_id == mlb_team_id:
                    stat_data = split.get("stat", {})

                    # Process hitting stats
                    if group_name.lower() == "hitting":
                        self._process_hitting_stats(stat_data, result)

                    # Process pitching stats
                    elif group_name.lower() == "pitching":
                        self._process_pitching_stats(stat_data, result)

        # Calculate derived metrics
        result["run_differential"] = result["runs_scored"] - result["runs_allowed"]

        if result["runs_scored"] > 0 and result["runs_allowed"] > 0:
            result["pythagorean_expectation"] = (result["runs_scored"] ** 2) / (
                result["runs_scored"] ** 2 + result["runs_allowed"] ** 2
            )
        else:
            result["pythagorean_expectation"] = 0.0

        return result

    def _process_hitting_stats(self, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Process hitting statistics from the API response."""
        # Basic stats
        if "gamesPlayed" in stat_data:
            result["games_played"] = stat_data["gamesPlayed"]
        if "runs" in stat_data:
            result["runs_scored"] = stat_data["runs"]
        if "hits" in stat_data:
            result["hits"] = stat_data["hits"]
        if "homeRuns" in stat_data:
            result["home_runs"] = stat_data["homeRuns"]
        if "stolenBases" in stat_data:
            result["stolen_bases"] = stat_data["stolenBases"]
        if "groundIntoDoublePlay" in stat_data:
            result["double_plays"] = stat_data["groundIntoDoublePlay"]

        # Percentage stats (convert from string format like ".258" to float)
        if "avg" in stat_data and stat_data["avg"]:
            try:
                result["batting_average"] = float(stat_data["avg"])
            except (ValueError, TypeError):
                result["batting_average"] = 0.0

        if "obp" in stat_data and stat_data["obp"]:
            try:
                result["on_base_percentage"] = float(stat_data["obp"])
            except (ValueError, TypeError):
                result["on_base_percentage"] = 0.0

        if "slg" in stat_data and stat_data["slg"]:
            try:
                result["slugging_percentage"] = float(stat_data["slg"])
            except (ValueError, TypeError):
                result["slugging_percentage"] = 0.0

        if "ops" in stat_data and stat_data["ops"]:
            try:
                result["ops"] = float(stat_data["ops"])
            except (ValueError, TypeError):
                result["ops"] = 0.0

    def _process_pitching_stats(self, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Process pitching statistics from the API response."""
        # Win/Loss record
        if "wins" in stat_data:
            result["wins"] = stat_data["wins"]
        if "losses" in stat_data:
            result["losses"] = stat_data["losses"]
        if "saves" in stat_data:
            result["saves"] = stat_data["saves"]

        # Runs allowed
        if "runs" in stat_data:
            result["runs_allowed"] = stat_data["runs"]
        if "homeRuns" in stat_data:
            result["home_runs_allowed"] = stat_data["homeRuns"]

        # Strikeouts and walks
        if "strikeOuts" in stat_data:
            result["strikeouts"] = stat_data["strikeOuts"]
        if "baseOnBalls" in stat_data:
            result["walks_allowed"] = stat_data["baseOnBalls"]

        # Defensive stats
        if "errors" in stat_data:
            result["errors"] = stat_data["errors"]
        if "fielding_percentage" in stat_data:
            result["fielding_percentage"] = stat_data["fielding_percentage"]

        # Percentage/ratio stats (convert from string format)
        if "era" in stat_data and stat_data["era"]:
            try:
                result["earned_run_average"] = float(stat_data["era"])
            except (ValueError, TypeError):
                result["earned_run_average"] = 0.0

        if "whip" in stat_data and stat_data["whip"]:
            try:
                result["whip"] = float(stat_data["whip"])
            except (ValueError, TypeError):
                result["whip"] = 0.0

        if "strikeoutsPer9Inn" in stat_data and stat_data["strikeoutsPer9Inn"]:
            try:
                result["strikeouts_per_nine"] = float(stat_data["strikeoutsPer9Inn"])
            except (ValueError, TypeError):
                result["strikeouts_per_nine"] = 0.0

        if "walksPer9Inn" in stat_data and stat_data["walksPer9Inn"]:
            try:
                result["walks_per_nine"] = float(stat_data["walksPer9Inn"])
            except (ValueError, TypeError):
                result["walks_per_nine"] = 0.0

    def _transform_player_data(self, player_data: Dict[str, Any]) -> MLBPlayerDTO:
        """Transform player data from the MLB API to match our domain model."""
        # Parse birth date if available
        birth_date = None
        if "birthDate" in player_data:
            try:
                birth_date = datetime.fromisoformat(player_data["birthDate"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid birth date format: {player_data.get('birthDate')}")

        first_name = player_data.get("firstName", "")
        last_name = player_data.get("lastName", "")
        if (not first_name or not last_name) and player_data.get("fullName"):
            full_name = str(player_data.get("fullName", "")).strip()
            split_name = full_name.split()
            if split_name:
                first_name = first_name or split_name[0]
                last_name = last_name or " ".join(split_name[1:]) if len(split_name) > 1 else ""

        position = player_data.get("position", "")
        if isinstance(position, dict):
            position = position.get("abbreviation", "") or position.get("code", "") or position.get("name", "")

        return MLBPlayerDTO(
            id=int(player_data.get("id", 0)),
            first_name=first_name,
            last_name=last_name,
            position=position,
            bats=player_data.get("batSide", {}).get("code", ""),
            throws=player_data.get("pitchHand", {}).get("code", ""),
            birth_date=birth_date,
            active=player_data.get("active", True),
            current_team_id=player_data.get("currentTeam", {}).get("id"),
        )

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
        """Transform player stats data from the MLB API to a normalized response payload."""
        stats_blocks = stats_data.get("stats", [])
        return {
            "player_id": mlb_player_id,
            "stats": stats,
            "group": group,
            "season": season,
            "game_type": game_type,
            "days_back": days_back,
            "stats_data": stats_blocks,
        }

    def _transform_fielding_stats_data(
        self, stats_data: Dict[str, Any], mlb_team_id: int, season: int
    ) -> Dict[str, Any]:
        """Transform fielding stats data from the MLB API to match our domain model."""
        stats_groups = stats_data.get("stats", [])

        # Initialize with default values
        result = {
            "team_id": mlb_team_id,
            "season": season,
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

        # Process each stats group (should be fielding)
        for group in stats_groups:
            group_info = group.get("group", {})
            group_name = group_info.get("displayName", "")

            splits = group.get("splits", [])
            for split in splits:
                # Verify that the split corresponds to the current team
                split_team = split.get("team", {})
                split_team_id = split_team.get("id")

                if split_team_id == mlb_team_id:
                    stat_data = split.get("stat", {})

                    # Process fielding stats
                    if group_name.lower() == "fielding":
                        self._process_fielding_stats(stat_data, result)

        return result

    def _process_fielding_stats(self, stat_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Process fielding statistics from the API response."""
        # Basic game stats
        if "gamesPlayed" in stat_data:
            result["games_played"] = stat_data["gamesPlayed"]
        if "gamesStarted" in stat_data:
            result["games_started"] = stat_data["gamesStarted"]
        if "innings" in stat_data:
            try:
                result["innings_played"] = float(stat_data["innings"])
            except (ValueError, TypeError):
                result["innings_played"] = 0.0

        # Fielding stats
        if "chances" in stat_data:
            result["total_chances"] = stat_data["chances"]
        if "putOuts" in stat_data:
            result["putouts"] = stat_data["putOuts"]
        if "assists" in stat_data:
            result["assists"] = stat_data["assists"]
        if "errors" in stat_data:
            result["errors"] = stat_data["errors"]
        if "throwingErrors" in stat_data:
            result["throwing_errors"] = stat_data["throwingErrors"]
        if "doublePlays" in stat_data:
            result["double_plays"] = stat_data["doublePlays"]
        if "triplePlays" in stat_data:
            result["triple_plays"] = stat_data["triplePlays"]
        if "outfieldAssists" in stat_data:
            result["outfield_assists"] = stat_data["outfieldAssists"]
        if "passedBall" in stat_data:
            result["passed_balls"] = stat_data["passedBall"]
        if "wildPitches" in stat_data:
            result["wild_pitches"] = stat_data["wildPitches"]
        if "stolenBases" in stat_data:
            result["stolen_bases_allowed"] = stat_data["stolenBases"]
        if "caughtStealing" in stat_data:
            result["caught_stealing"] = stat_data["caughtStealing"]
        if "catchersInterference" in stat_data:
            result["catchers_interference"] = stat_data["catchersInterference"]
        if "pickoffs" in stat_data:
            result["pickoffs"] = stat_data["pickoffs"]

        # Percentage stats (convert from string format like ".985" to float)
        if "fielding" in stat_data and stat_data["fielding"]:
            try:
                result["fielding_percentage"] = float(stat_data["fielding"])
            except (ValueError, TypeError):
                result["fielding_percentage"] = 0.0

        if "stolenBasePercentage" in stat_data and stat_data["stolenBasePercentage"]:
            try:
                result["stolen_base_percentage"] = float(stat_data["stolenBasePercentage"])
            except (ValueError, TypeError):
                result["stolen_base_percentage"] = 0.0

        # Calculate derived stats if base stats are available
        if result["total_chances"] > 0:
            successful_plays = result["putouts"] + result["assists"]
            if result["fielding_percentage"] == 0.0:  # Not provided by API
                result["fielding_percentage"] = successful_plays / result["total_chances"]

        if result["games_played"] > 0:
            if result["range_factor_per_game"] == 0.0:  # Calculate if not provided
                result["range_factor_per_game"] = (result["putouts"] + result["assists"]) / result["games_played"]

        if result["innings_played"] > 0:
            if result["range_factor_per_nine"] == 0.0:  # Calculate if not provided
                result["range_factor_per_nine"] = ((result["putouts"] + result["assists"]) * 9) / result[
                    "innings_played"
                ]
