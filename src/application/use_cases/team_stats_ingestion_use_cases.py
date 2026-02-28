"""
Use cases for team statistics ingestion operations.
These define the application's business logic for ingesting team statistics from the MLB API.
"""

from collections.abc import Iterable
from typing import Any

from src.application.ports.catching_stats_repository import CatchingStatsRepositoryPort
from src.application.ports.fielding_stats_repository import FieldingStatsRepositoryPort
from src.application.ports.hitting_stats_repository import HittingStatsRepositoryPort
from src.application.ports.mlb_api import MLBApiPort
from src.application.ports.pitching_stats_repository import PitchingStatsRepositoryPort
from src.application.ports.team_repository import TeamRepositoryPort
from src.domain.entities.catching_stats import CatchingStats
from src.domain.entities.fielding_stats import FieldingStats
from src.domain.entities.hitting_stats import HittingStats
from src.domain.entities.pitching_stats import PitchingStats


def _build_team_mapping(teams: Iterable[Any]) -> dict[int, int]:
    return {team.mlb_id: team.id for team in teams if team.id is not None}


def _iter_team_stat_splits(
    stats_data: dict[str, Any],
    team_mapping: dict[int, int],
) -> Iterable[tuple[int, dict[str, Any]]]:
    for group in stats_data.get("stats", []):
        for split in group.get("splits", []):
            mlb_team_id = split.get("team", {}).get("id")
            team_id = team_mapping.get(mlb_team_id)
            if team_id is None:
                continue
            yield team_id, split.get("stat", {})


PITCHING_INT_FIELDS = {
    "games_played": "gamesPlayed",
    "wins": "wins",
    "losses": "losses",
    "saves": "saves",
    "save_opportunities": "saveOpportunities",
    "holds": "holds",
    "blown_saves": "blownSaves",
    "batters_faced": "battersFaced",
    "hits_allowed": "hits",
    "runs_allowed": "runs",
    "earned_runs": "earnedRuns",
    "home_runs_allowed": "homeRuns",
    "strikeouts": "strikeOuts",
    "base_on_balls": "baseOnBalls",
    "intentional_walks": "intentionalWalks",
    "hit_batsmen": "hitBatsmen",
    "wild_pitches": "wildPitches",
    "balks": "balks",
    "number_of_pitches": "numberOfPitches",
    "complete_games": "completeGames",
    "shutouts": "shutouts",
    "games_started": "gamesStarted",
    "ground_outs": "groundOuts",
    "air_outs": "airOuts",
    "doubles": "doubles",
    "triples": "triples",
    "at_bats": "atBats",
    "outs": "outs",
    "strikes": "strikes",
    "pickoffs": "pickoffs",
    "total_bases": "totalBases",
    "games_finished": "gamesFinished",
    "catchers_interference": "catchersInterference",
    "sacrifice_bunts": "sacBunts",
    "sacrifice_flies": "sacFlies",
    "ground_into_double_play": "groundIntoDoublePlay",
    "caught_stealing": "caughtStealing",
    "inherited_runners": "inheritedRunners",
    "inherited_runners_scored": "inheritedRunnersScored",
    "quality_starts": "qualityStarts",
}

PITCHING_FLOAT_FIELDS = {
    "innings_pitched": "inningsPitched",
    "earned_run_average": "era",
    "whip": "whip",
    "strikeouts_per_nine": "strikeoutsPer9Inn",
    "walks_per_nine": "walksPer9Inn",
    "hits_per_nine": "hitsPer9Inn",
    "home_runs_per_nine": "homeRunsPer9",
    "strikeout_to_walk_ratio": "strikeoutWalkRatio",
    "ground_outs_to_airouts": "groundOutsToAirouts",
    "pitches_per_inning": "pitchesPerInning",
    "batting_average_against": "avg",
    "on_base_percentage": "obp",
    "slugging_percentage": "slg",
    "ops": "ops",
    "stolen_base_percentage": "stolenBasePercentage",
    "strike_percentage": "strikePercentage",
    "win_percentage": "winPercentage",
    "runs_scored_per_nine": "runsScoredPer9",
}


class IngestTeamHittingStatsUseCase:
    """Use case for ingesting team hitting statistics from the MLB API."""

    def __init__(
        self,
        hitting_stats_repository: HittingStatsRepositoryPort,
        team_repository: TeamRepositoryPort,
        mlb_api: MLBApiPort,
    ):
        self.hitting_stats_repository = hitting_stats_repository
        self.team_repository = team_repository
        self.mlb_api = mlb_api

    async def execute(self, season: int) -> list[HittingStats]:
        """
        Ingest team hitting statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested HittingStats entities
        """
        teams = await self.team_repository.list_all()
        team_mapping = _build_team_mapping(teams)
        stats_data = await self.mlb_api.get_team_stats(season=season, group="hitting")
        if not stats_data:
            return []
        ingested_stats = []
        for team_id, stat_data in _iter_team_stat_splits(stats_data, team_mapping):
            games_played = self._safe_int_conversion(stat_data.get("gamesPlayed"))
            at_bats = self._safe_int_conversion(stat_data.get("atBats"))
            if games_played == 0 and at_bats == 0:
                continue
            hitting_stats = self._build_hitting_stats(team_id, season, stat_data, games_played, at_bats)
            saved_stats = await self.hitting_stats_repository.save(hitting_stats)
            ingested_stats.append(saved_stats)
        return ingested_stats

    def _build_hitting_stats(
        self,
        team_id: int,
        season: int,
        stat_data: dict[str, Any],
        games_played: int,
        at_bats: int,
    ) -> HittingStats:
        return HittingStats.create(
            team_id=team_id,
            season=season,
            games_played=games_played,
            at_bats=at_bats,
            plate_appearances=self._safe_int_conversion(stat_data.get("plateAppearances")),
            hits=self._safe_int_conversion(stat_data.get("hits")),
            doubles=self._safe_int_conversion(stat_data.get("doubles")),
            triples=self._safe_int_conversion(stat_data.get("triples")),
            home_runs=self._safe_int_conversion(stat_data.get("homeRuns")),
            runs_scored=self._safe_int_conversion(stat_data.get("runs")),
            runs_batted_in=self._safe_int_conversion(stat_data.get("rbi")),
            stolen_bases=self._safe_int_conversion(stat_data.get("stolenBases")),
            caught_stealing=self._safe_int_conversion(stat_data.get("caughtStealing")),
            base_on_balls=self._safe_int_conversion(stat_data.get("baseOnBalls")),
            strikeouts=self._safe_int_conversion(stat_data.get("strikeOuts")),
            hit_by_pitch=self._safe_int_conversion(stat_data.get("hitByPitch")),
            sacrifice_hits=self._safe_int_conversion(stat_data.get("sacBunts")),
            sacrifice_flies=self._safe_int_conversion(stat_data.get("sacFlies")),
            ground_into_double_play=self._safe_int_conversion(stat_data.get("groundIntoDoublePlay")),
            left_on_base=self._safe_int_conversion(stat_data.get("leftOnBase")),
            batting_average=self._safe_float_conversion(stat_data.get("avg")),
            on_base_percentage=self._safe_float_conversion(stat_data.get("obp")),
            slugging_percentage=self._safe_float_conversion(stat_data.get("slg")),
            ops=self._safe_float_conversion(stat_data.get("ops")),
            babip=self._safe_float_conversion(stat_data.get("babip")),
            total_bases=self._safe_int_conversion(stat_data.get("totalBases")),
            at_bats_per_home_run=self._safe_float_conversion(stat_data.get("atBatsPerHomeRun")),
            stolen_base_percentage=self._safe_float_conversion(stat_data.get("stolenBasePercentage")),
            ground_outs=self._safe_int_conversion(stat_data.get("groundOuts")),
            air_outs=self._safe_int_conversion(stat_data.get("airOuts")),
            ground_outs_to_airouts=self._safe_float_conversion(stat_data.get("groundOutsToAirouts")),
            number_of_pitches=self._safe_int_conversion(stat_data.get("numberOfPitches")),
            intentional_walks=self._safe_int_conversion(stat_data.get("intentionalWalks")),
        )

    def _safe_int_conversion(self, value) -> int:
        """Safely convert a value to int, handling None values and invalid data."""
        if value is None or value == "":
            return 0

        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def _safe_float_conversion(self, value) -> float:
        """Safely convert a value to float, handling string percentages and None values."""
        if value is None or value == "":
            return 0.0

        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class IngestTeamPitchingStatsUseCase:
    """Use case for ingesting team pitching statistics from the MLB API."""

    def __init__(
        self,
        pitching_stats_repository: PitchingStatsRepositoryPort,
        team_repository: TeamRepositoryPort,
        mlb_api: MLBApiPort,
    ):
        self.pitching_stats_repository = pitching_stats_repository
        self.team_repository = team_repository
        self.mlb_api = mlb_api

    async def execute(self, season: int) -> list[PitchingStats]:
        """
        Ingest team pitching statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested PitchingStats entities
        """
        teams = await self.team_repository.list_all()
        team_mapping = _build_team_mapping(teams)
        stats_data = await self.mlb_api.get_team_stats(season=season, group="pitching")
        if not stats_data:
            return []
        ingested_stats = []
        for team_id, stat_data in _iter_team_stat_splits(stats_data, team_mapping):
            if self._safe_int_conversion(stat_data.get("gamesPlayed")) == 0:
                continue
            pitching_stats = self._build_pitching_stats(team_id, season, stat_data)
            saved_stats = await self.pitching_stats_repository.save(pitching_stats)
            ingested_stats.append(saved_stats)
        return ingested_stats

    def _build_pitching_stats(self, team_id: int, season: int, stat_data: dict[str, Any]) -> PitchingStats:
        numeric_values: dict[str, int | float] = {}
        for field_name, source_key in PITCHING_INT_FIELDS.items():
            numeric_values[field_name] = self._safe_int_conversion(stat_data.get(source_key))
        for field_name, source_key in PITCHING_FLOAT_FIELDS.items():
            numeric_values[field_name] = self._safe_float_conversion(stat_data.get(source_key))
        return PitchingStats.create(team_id=team_id, season=season, **numeric_values)

    def _safe_int_conversion(self, value) -> int:
        """Safely convert a value to int, handling None values and invalid data."""
        if value is None or value == "":
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def _safe_float_conversion(self, value) -> float:
        """Safely convert a value to float, handling string percentages and None values."""
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class IngestTeamFieldingStatsUseCase:
    """Use case for ingesting team fielding statistics from the MLB API."""

    def __init__(
        self,
        fielding_stats_repository: FieldingStatsRepositoryPort,
        team_repository: TeamRepositoryPort,
        mlb_api: MLBApiPort,
    ):
        self.fielding_stats_repository = fielding_stats_repository
        self.team_repository = team_repository
        self.mlb_api = mlb_api

    async def execute(self, season: int) -> list[FieldingStats]:
        """
        Ingest team fielding statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested FieldingStats entities
        """
        teams = await self.team_repository.list_all()
        team_mapping = _build_team_mapping(teams)
        stats_data = await self.mlb_api.get_team_stats(season=season, group="fielding")
        if not stats_data:
            return []
        ingested_stats = []
        for team_id, stat_data in _iter_team_stat_splits(stats_data, team_mapping):
            if self._safe_int_conversion(stat_data.get("gamesPlayed")) == 0:
                continue
            fielding_stats = self._build_fielding_stats(team_id, season, stat_data)
            saved_stats = await self.fielding_stats_repository.save(fielding_stats)
            ingested_stats.append(saved_stats)
        return ingested_stats

    def _build_fielding_stats(self, team_id: int, season: int, stat_data: dict[str, Any]) -> FieldingStats:
        return FieldingStats.create(
            team_id=team_id,
            season=season,
            games_played=self._safe_int_conversion(stat_data.get("gamesPlayed")),
            games_started=self._safe_int_conversion(stat_data.get("gamesStarted")),
            innings_played=self._safe_float_conversion(stat_data.get("innings")),
            total_chances=self._safe_int_conversion(stat_data.get("chances")),
            putouts=self._safe_int_conversion(stat_data.get("putOuts")),
            assists=self._safe_int_conversion(stat_data.get("assists")),
            errors=self._safe_int_conversion(stat_data.get("errors")),
            throwing_errors=self._safe_int_conversion(stat_data.get("throwingErrors")),
            double_plays=self._safe_int_conversion(stat_data.get("doublePlays")),
            triple_plays=self._safe_int_conversion(stat_data.get("triplePlays")),
            fielding_percentage=self._safe_float_conversion(stat_data.get("fielding")),
            defensive_efficiency_ratio=self._safe_float_conversion(stat_data.get("defensiveEfficiency")),
            range_factor_per_game=self._safe_float_conversion(stat_data.get("rangeFactorPerGame")),
            range_factor_per_nine=self._safe_float_conversion(stat_data.get("rangeFactorPer9Inn")),
            outfield_assists=self._safe_int_conversion(stat_data.get("outfieldAssists")),
            passed_balls=self._safe_int_conversion(stat_data.get("passedBall")),
            wild_pitches=self._safe_int_conversion(stat_data.get("wildPitches")),
            stolen_bases_allowed=self._safe_int_conversion(stat_data.get("stolenBases")),
            caught_stealing=self._safe_int_conversion(stat_data.get("caughtStealing")),
            stolen_base_percentage=self._safe_float_conversion(stat_data.get("stolenBasePercentage")),
            catchers_interference=self._safe_int_conversion(stat_data.get("catchersInterference")),
            pickoffs=self._safe_int_conversion(stat_data.get("pickoffs")),
        )

    def _safe_int_conversion(self, value) -> int:
        """Safely convert a value to int, handling None values and invalid data."""
        if value is None or value == "":
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def _safe_float_conversion(self, value) -> float:
        """Safely convert a value to float, handling string percentages and None values."""
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class IngestTeamCatchingStatsUseCase:
    """Use case for ingesting team catching statistics from the MLB API."""

    def __init__(
        self,
        catching_stats_repository: CatchingStatsRepositoryPort,
        team_repository: TeamRepositoryPort,
        mlb_api: MLBApiPort,
    ):
        self.catching_stats_repository = catching_stats_repository
        self.team_repository = team_repository
        self.mlb_api = mlb_api

    async def execute(self, season: int) -> list[CatchingStats]:
        """
        Ingest team catching statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested CatchingStats entities
        """
        teams = await self.team_repository.list_all()
        team_mapping = _build_team_mapping(teams)
        stats_data = await self.mlb_api.get_team_stats(season=season, group="catching")
        if not stats_data:
            return []
        ingested_stats = []
        for team_id, stat_data in _iter_team_stat_splits(stats_data, team_mapping):
            if self._safe_int_conversion(stat_data.get("gamesPlayed")) == 0:
                continue
            catching_stats = self._build_catching_stats(team_id, season, stat_data)
            saved_stats = await self.catching_stats_repository.save(catching_stats)
            ingested_stats.append(saved_stats)
        return ingested_stats

    def _build_catching_stats(self, team_id: int, season: int, stat_data: dict[str, Any]) -> CatchingStats:
        return CatchingStats.create(
            team_id=team_id,
            season=season,
            games_played=self._safe_int_conversion(stat_data.get("gamesPlayed")),
            games_pitched=self._safe_int_conversion(stat_data.get("gamesPitched")),
            at_bats=self._safe_int_conversion(stat_data.get("atBats")),
            hits=self._safe_int_conversion(stat_data.get("hits")),
            runs=self._safe_int_conversion(stat_data.get("runs")),
            home_runs=self._safe_int_conversion(stat_data.get("homeRuns")),
            strikeouts=self._safe_int_conversion(stat_data.get("strikeOuts")),
            base_on_balls=self._safe_int_conversion(stat_data.get("baseOnBalls")),
            intentional_walks=self._safe_int_conversion(stat_data.get("intentionalWalks")),
            hit_by_pitch=self._safe_int_conversion(stat_data.get("hitByPitch")),
            total_bases=self._safe_int_conversion(stat_data.get("totalBases")),
            sacrifice_bunts=self._safe_int_conversion(stat_data.get("sacBunts")),
            sacrifice_flies=self._safe_int_conversion(stat_data.get("sacFlies")),
            batting_average=self._safe_float_conversion(stat_data.get("avg")),
            on_base_percentage=self._safe_float_conversion(stat_data.get("obp")),
            slugging_percentage=self._safe_float_conversion(stat_data.get("slg")),
            ops=self._safe_float_conversion(stat_data.get("ops")),
            passed_balls=self._safe_int_conversion(stat_data.get("passedBall")),
            wild_pitches=self._safe_int_conversion(stat_data.get("wildPitches")),
            stolen_bases_allowed=self._safe_int_conversion(stat_data.get("stolenBases")),
            caught_stealing=self._safe_int_conversion(stat_data.get("caughtStealing")),
            stolen_base_percentage=self._safe_float_conversion(stat_data.get("stolenBasePercentage")),
            pickoffs=self._safe_int_conversion(stat_data.get("pickoffs")),
            pickoff_attempts=self._safe_int_conversion(stat_data.get("pickoffAttempts")),
            catchers_interference=self._safe_int_conversion(stat_data.get("catchersInterference")),
            earned_runs=self._safe_int_conversion(stat_data.get("earnedRuns")),
            batters_faced=self._safe_int_conversion(stat_data.get("battersFaced")),
            hit_batsmen=self._safe_int_conversion(stat_data.get("hitBatsmen")),
            strikeout_walk_ratio=self._safe_float_conversion(stat_data.get("strikeoutWalkRatio")),
        )

    def _safe_int_conversion(self, value) -> int:
        """Safely convert a value to int, handling None values and invalid data."""
        if value is None or value == "":
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def _safe_float_conversion(self, value) -> float:
        """Safely convert a value to float, handling string percentages and None values."""
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class IngestAllTeamStatsUseCase:
    """Use case for ingesting all team statistics from the MLB API."""

    def __init__(
        self,
        hitting_stats_use_case: IngestTeamHittingStatsUseCase,
        pitching_stats_use_case: IngestTeamPitchingStatsUseCase,
        fielding_stats_use_case: IngestTeamFieldingStatsUseCase,
        catching_stats_use_case: IngestTeamCatchingStatsUseCase,
    ):
        self.hitting_stats_use_case = hitting_stats_use_case
        self.pitching_stats_use_case = pitching_stats_use_case
        self.fielding_stats_use_case = fielding_stats_use_case
        self.catching_stats_use_case = catching_stats_use_case

    async def execute(self, season: int) -> dict[str, list]:
        """
        Ingest all team statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            Dictionary containing lists of ingested stats entities by type
        """
        # Ingest all stats types
        hitting_stats = await self.hitting_stats_use_case.execute(season)
        pitching_stats = await self.pitching_stats_use_case.execute(season)
        fielding_stats = await self.fielding_stats_use_case.execute(season)
        catching_stats = await self.catching_stats_use_case.execute(season)

        return {
            "hitting_stats": hitting_stats,
            "pitching_stats": pitching_stats,
            "fielding_stats": fielding_stats,
            "catching_stats": catching_stats,
        }
