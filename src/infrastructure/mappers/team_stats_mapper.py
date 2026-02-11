from typing import Optional

from src.domain.entities.team import Team
from src.domain.entities.team_stats import TeamStats
from src.infrastructure.db.models import FieldingStatsModel, HittingStatsModel, PitchingStatsModel, TeamModel


class TeamStatsMapper:
    """Mapper for converting between TeamStats entities and database models."""

    @staticmethod
    def to_entity(
        hitting_stats: Optional[HittingStatsModel],
        pitching_stats: Optional[PitchingStatsModel],
        fielding_stats: Optional[FieldingStatsModel],
    ) -> Optional[TeamStats]:
        """
        Aggregate stats from different models into a TeamStats entity.

        Args:
            hitting_stats: The hitting stats model
            pitching_stats: The pitching stats model
            fielding_stats: The fielding stats model

        Returns:
            A TeamStats entity with aggregated stats, or None if hitting_stats is missing.
        """
        if not hitting_stats:
            return None

        # Use hitting stats as the base for team_id and season
        team_id = hitting_stats.team_id
        season = hitting_stats.season

        # Get games_played from hitting stats
        games_played = hitting_stats.games_played

        # Get wins and losses from pitching stats
        wins = pitching_stats.wins if pitching_stats else 0
        losses = pitching_stats.losses if pitching_stats else 0

        # Get offensive stats from hitting stats
        runs_scored = hitting_stats.runs_scored
        hits = hitting_stats.hits
        home_runs = hitting_stats.home_runs
        batting_average = hitting_stats.batting_average
        on_base_percentage = hitting_stats.on_base_percentage
        slugging_percentage = hitting_stats.slugging_percentage
        ops = hitting_stats.ops
        stolen_bases = hitting_stats.stolen_bases

        # Get pitching stats
        earned_run_average = pitching_stats.earned_run_average if pitching_stats else 0.0
        whip = pitching_stats.whip if pitching_stats else 0.0
        strikeouts_per_nine = pitching_stats.strikeouts_per_nine if pitching_stats else 0.0
        walks_per_nine = pitching_stats.walks_per_nine if pitching_stats else 0.0
        home_runs_allowed = pitching_stats.home_runs_allowed if pitching_stats else 0
        runs_allowed = pitching_stats.runs_allowed if pitching_stats else 0

        # Get fielding stats
        fielding_percentage = fielding_stats.fielding_percentage if fielding_stats else 0.0
        errors = fielding_stats.errors if fielding_stats else 0
        double_plays = fielding_stats.double_plays if fielding_stats else 0

        # Calculate run differential
        run_differential = runs_scored - runs_allowed

        # Calculate Pythagorean expectation using the shared domain logic
        pythagorean_expectation = TeamStats._calculate_pythagorean_expectation(runs_scored, runs_allowed)

        # Create TeamStats entity
        team_stats = TeamStats(
            id=hitting_stats.id,  # Use hitting stats ID as the team stats ID
            team_id=team_id,
            season=season,
            games_played=games_played,
            wins=wins,
            losses=losses,
            runs_scored=runs_scored,
            hits=hits,
            home_runs=home_runs,
            batting_average=batting_average,
            on_base_percentage=on_base_percentage,
            slugging_percentage=slugging_percentage,
            ops=ops,
            stolen_bases=stolen_bases,
            earned_run_average=earned_run_average,
            whip=whip,
            strikeouts_per_nine=strikeouts_per_nine,
            walks_per_nine=walks_per_nine,
            home_runs_allowed=home_runs_allowed,
            runs_allowed=runs_allowed,
            fielding_percentage=fielding_percentage,
            errors=errors,
            double_plays=double_plays,
            run_differential=run_differential,
            pythagorean_expectation=pythagorean_expectation,
            created_at=hitting_stats.created_at,
            updated_at=hitting_stats.updated_at,
        )

        # Set related team if loaded
        if hasattr(hitting_stats, "team") and hitting_stats.team:
            team_stats.team = TeamStatsMapper._team_model_to_entity(hitting_stats.team)

        return team_stats

    @staticmethod
    def _team_model_to_entity(model: TeamModel) -> Team:
        """Convert a TeamModel to a Team entity."""
        return Team(
            id=model.id,
            mlb_id=model.mlb_id,
            name=model.name,
            abbreviation=model.abbreviation,
            city=model.city,
            division=model.division,
            league=model.league,
            venue_name=model.venue_name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def update_hitting_model(entity: TeamStats, model: Optional[HittingStatsModel] = None) -> HittingStatsModel:
        """Update or create a HittingStatsModel from a TeamStats entity."""
        if not model:
            model = HittingStatsModel(team_id=entity.team_id, season=entity.season)

        model.games_played = entity.games_played
        model.runs_scored = entity.runs_scored
        model.hits = entity.hits
        model.home_runs = entity.home_runs
        model.batting_average = entity.batting_average
        model.on_base_percentage = entity.on_base_percentage
        model.slugging_percentage = entity.slugging_percentage
        model.ops = entity.ops
        model.stolen_bases = entity.stolen_bases
        return model

    @staticmethod
    def update_pitching_model(entity: TeamStats, model: Optional[PitchingStatsModel] = None) -> PitchingStatsModel:
        """Update or create a PitchingStatsModel from a TeamStats entity."""
        if not model:
            model = PitchingStatsModel(team_id=entity.team_id, season=entity.season)

        model.wins = entity.wins
        model.losses = entity.losses
        model.earned_run_average = entity.earned_run_average
        model.whip = entity.whip
        model.strikeouts_per_nine = entity.strikeouts_per_nine
        model.walks_per_nine = entity.walks_per_nine
        model.home_runs_allowed = entity.home_runs_allowed
        model.runs_allowed = entity.runs_allowed
        return model

    @staticmethod
    def update_fielding_model(entity: TeamStats, model: Optional[FieldingStatsModel] = None) -> FieldingStatsModel:
        """Update or create a FieldingStatsModel from a TeamStats entity."""
        if not model:
            model = FieldingStatsModel(team_id=entity.team_id, season=entity.season)

        model.fielding_percentage = entity.fielding_percentage
        model.errors = entity.errors
        model.double_plays = entity.double_plays
        return model
