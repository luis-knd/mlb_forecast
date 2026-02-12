"""
Use cases for team statistics ingestion operations.
These define the application's business logic for ingesting team statistics from the MLB API.
"""

from typing import Dict, List

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

    async def execute(self, season: int) -> List[HittingStats]:
        """
        Ingest team hitting statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested HittingStats entities
        """
        # Get all teams for mapping MLB IDs to our team IDs
        teams = await self.team_repository.list_all()
        team_mapping = {team.mlb_id: team.id for team in teams}

        # Get stats data from MLB API for the hitting group
        stats_data = await self.mlb_api.get_team_stats(season=season, group="hitting")
        if not stats_data:
            return []

        # Extract hitting stats from the API response
        ingested_stats = []
        stats_groups = stats_data.get("stats", [])
        for group in stats_groups:
            splits = group.get("splits", [])
            for split in splits:
                # Get team info from the split
                team_info = split.get("team", {})
                mlb_team_id = team_info.get("id")

                # Skip if we don't have this team in our database
                if mlb_team_id not in team_mapping:
                    continue

                team_id = team_mapping[mlb_team_id]
                stat_data = split.get("stat", {})

                # Validate that we have meaningful statistical data
                # Skip teams with no games played or completely empty stats
                games_played = self._safe_int_conversion(stat_data.get("gamesPlayed"))
                at_bats = self._safe_int_conversion(stat_data.get("atBats"))

                # For future seasons or teams with no data, skip the ingestion
                # rather than creating records with all zeros
                if games_played == 0 and at_bats == 0:
                    continue

                # Validate team_id is not None before creating HittingStats
                if team_id is None:
                    continue

                # Create HittingStats entity with improved data validation
                hitting_stats = HittingStats.create(
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

                # Save to repository
                saved_stats = await self.hitting_stats_repository.save(hitting_stats)
                ingested_stats.append(saved_stats)

        return ingested_stats

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

    async def execute(self, season: int) -> List[PitchingStats]:
        """
        Ingest team pitching statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested PitchingStats entities
        """
        # Get all teams for mapping MLB IDs to our team IDs
        teams = await self.team_repository.list_all()
        team_mapping = {team.mlb_id: team.id for team in teams}

        # Get stats data from MLB API for the pitching group
        stats_data = await self.mlb_api.get_team_stats(season=season, group="pitching")
        if not stats_data:
            return []

        ingested_stats = []
        stats_groups = stats_data.get("stats", [])
        for group in stats_groups:
            splits = group.get("splits", [])
            for split in splits:
                team_info = split.get("team", {})
                mlb_team_id = team_info.get("id")

                if mlb_team_id not in team_mapping:
                    continue

                team_id = team_mapping[mlb_team_id]
                stat_data = split.get("stat", {})

                if self._safe_int_conversion(stat_data.get("gamesPlayed")) == 0:
                    continue

                # Validate team_id is not None before creating PitchingStats
                if team_id is None:
                    continue

                pitching_stats = PitchingStats.create(
                    team_id=team_id,
                    season=season,
                    games_played=self._safe_int_conversion(stat_data.get("gamesPlayed")),
                    wins=self._safe_int_conversion(stat_data.get("wins")),
                    losses=self._safe_int_conversion(stat_data.get("losses")),
                    saves=self._safe_int_conversion(stat_data.get("saves")),
                    save_opportunities=self._safe_int_conversion(stat_data.get("saveOpportunities")),
                    holds=self._safe_int_conversion(stat_data.get("holds")),
                    blown_saves=self._safe_int_conversion(stat_data.get("blownSaves")),
                    innings_pitched=self._safe_float_conversion(stat_data.get("inningsPitched")),
                    batters_faced=self._safe_int_conversion(stat_data.get("battersFaced")),
                    hits_allowed=self._safe_int_conversion(stat_data.get("hits")),
                    runs_allowed=self._safe_int_conversion(stat_data.get("runs")),
                    earned_runs=self._safe_int_conversion(stat_data.get("earnedRuns")),
                    home_runs_allowed=self._safe_int_conversion(stat_data.get("homeRuns")),
                    strikeouts=self._safe_int_conversion(stat_data.get("strikeOuts")),
                    base_on_balls=self._safe_int_conversion(stat_data.get("baseOnBalls")),
                    intentional_walks=self._safe_int_conversion(stat_data.get("intentionalWalks")),
                    hit_batsmen=self._safe_int_conversion(stat_data.get("hitBatsmen")),
                    wild_pitches=self._safe_int_conversion(stat_data.get("wildPitches")),
                    balks=self._safe_int_conversion(stat_data.get("balks")),
                    number_of_pitches=self._safe_int_conversion(stat_data.get("numberOfPitches")),
                    complete_games=self._safe_int_conversion(stat_data.get("completeGames")),
                    shutouts=self._safe_int_conversion(stat_data.get("shutouts")),
                    games_started=self._safe_int_conversion(stat_data.get("gamesStarted")),
                    ground_outs=self._safe_int_conversion(stat_data.get("groundOuts")),
                    air_outs=self._safe_int_conversion(stat_data.get("airOuts")),
                    # Additional basic stats from MLB API
                    doubles=self._safe_int_conversion(stat_data.get("doubles")),
                    triples=self._safe_int_conversion(stat_data.get("triples")),
                    at_bats=self._safe_int_conversion(stat_data.get("atBats")),
                    outs=self._safe_int_conversion(stat_data.get("outs")),
                    strikes=self._safe_int_conversion(stat_data.get("strikes")),
                    pickoffs=self._safe_int_conversion(stat_data.get("pickoffs")),
                    total_bases=self._safe_int_conversion(stat_data.get("totalBases")),
                    games_finished=self._safe_int_conversion(stat_data.get("gamesFinished")),
                    catchers_interference=self._safe_int_conversion(stat_data.get("catchersInterference")),
                    sacrifice_bunts=self._safe_int_conversion(stat_data.get("sacBunts")),
                    sacrifice_flies=self._safe_int_conversion(stat_data.get("sacFlies")),
                    ground_into_double_play=self._safe_int_conversion(stat_data.get("groundIntoDoublePlay")),
                    caught_stealing=self._safe_int_conversion(stat_data.get("caughtStealing")),
                    # Advanced stats
                    earned_run_average=self._safe_float_conversion(stat_data.get("era")),
                    whip=self._safe_float_conversion(stat_data.get("whip")),
                    strikeouts_per_nine=self._safe_float_conversion(stat_data.get("strikeoutsPer9Inn")),
                    walks_per_nine=self._safe_float_conversion(stat_data.get("walksPer9Inn")),
                    hits_per_nine=self._safe_float_conversion(stat_data.get("hitsPer9Inn")),
                    home_runs_per_nine=self._safe_float_conversion(stat_data.get("homeRunsPer9")),
                    strikeout_to_walk_ratio=self._safe_float_conversion(stat_data.get("strikeoutWalkRatio")),
                    ground_outs_to_airouts=self._safe_float_conversion(stat_data.get("groundOutsToAirouts")),
                    pitches_per_inning=self._safe_float_conversion(stat_data.get("pitchesPerInning")),
                    batting_average_against=self._safe_float_conversion(stat_data.get("avg")),
                    inherited_runners=self._safe_int_conversion(stat_data.get("inheritedRunners")),
                    inherited_runners_scored=self._safe_int_conversion(stat_data.get("inheritedRunnersScored")),
                    quality_starts=self._safe_int_conversion(stat_data.get("qualityStarts")),
                    # Additional advanced stats from MLB API
                    on_base_percentage=self._safe_float_conversion(stat_data.get("obp")),
                    slugging_percentage=self._safe_float_conversion(stat_data.get("slg")),
                    ops=self._safe_float_conversion(stat_data.get("ops")),
                    stolen_base_percentage=self._safe_float_conversion(stat_data.get("stolenBasePercentage")),
                    strike_percentage=self._safe_float_conversion(stat_data.get("strikePercentage")),
                    win_percentage=self._safe_float_conversion(stat_data.get("winPercentage")),
                    runs_scored_per_nine=self._safe_float_conversion(stat_data.get("runsScoredPer9")),
                )

                saved_stats = await self.pitching_stats_repository.save(pitching_stats)
                ingested_stats.append(saved_stats)

        return ingested_stats

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

    async def execute(self, season: int) -> List[FieldingStats]:
        """
        Ingest team fielding statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested FieldingStats entities
        """
        teams = await self.team_repository.list_all()
        team_mapping = {team.mlb_id: team.id for team in teams}

        # Get stats data from MLB API for the fielding group
        stats_data = await self.mlb_api.get_team_stats(season=season, group="fielding")
        if not stats_data:
            return []

        ingested_stats = []
        stats_groups = stats_data.get("stats", [])
        for group in stats_groups:
            splits = group.get("splits", [])
            for split in splits:
                team_info = split.get("team", {})
                mlb_team_id = team_info.get("id")

                if mlb_team_id not in team_mapping:
                    continue

                team_id = team_mapping[mlb_team_id]
                stat_data = split.get("stat", {})

                if self._safe_int_conversion(stat_data.get("gamesPlayed")) == 0:
                    continue

                # Validate team_id is not None before creating FieldingStats
                if team_id is None:
                    continue

                fielding_stats = FieldingStats.create(
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

                saved_stats = await self.fielding_stats_repository.save(fielding_stats)
                ingested_stats.append(saved_stats)

        return ingested_stats

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

    async def execute(self, season: int) -> List[CatchingStats]:
        """
        Ingest team catching statistics from the MLB API for a specific season.

        Args:
            season: The season year to ingest statistics for

        Returns:
            List of ingested CatchingStats entities
        """
        teams = await self.team_repository.list_all()
        team_mapping = {team.mlb_id: team.id for team in teams}

        # Get stats data from MLB API for the catching group
        stats_data = await self.mlb_api.get_team_stats(season=season, group="catching")
        if not stats_data:
            return []

        ingested_stats = []
        stats_groups = stats_data.get("stats", [])
        for group in stats_groups:
            splits = group.get("splits", [])
            for split in splits:
                team_info = split.get("team", {})
                mlb_team_id = team_info.get("id")

                if mlb_team_id not in team_mapping:
                    continue

                team_id = team_mapping[mlb_team_id]
                stat_data = split.get("stat", {})

                if self._safe_int_conversion(stat_data.get("gamesPlayed")) == 0:
                    continue

                # Validate team_id is not None before creating CatchingStats
                if team_id is None:
                    continue

                catching_stats = CatchingStats.create(
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

                saved_stats = await self.catching_stats_repository.save(catching_stats)
                ingested_stats.append(saved_stats)

        return ingested_stats

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

    async def execute(self, season: int) -> Dict[str, List]:
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
