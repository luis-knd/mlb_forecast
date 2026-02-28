from src.domain.entities.team import Team
from src.domain.entities.team_stats import TeamStats
from src.infrastructure.db.models import FieldingStatsModel, HittingStatsModel, PitchingStatsModel, TeamModel

HITTING_TO_TEAM_STATS_FIELDS = {
    "games_played": "games_played",
    "runs_scored": "runs_scored",
    "hits": "hits",
    "home_runs": "home_runs",
    "batting_average": "batting_average",
    "on_base_percentage": "on_base_percentage",
    "slugging_percentage": "slugging_percentage",
    "ops": "ops",
    "stolen_bases": "stolen_bases",
}

PITCHING_TO_TEAM_STATS_FIELDS = {
    "wins": "wins",
    "losses": "losses",
    "earned_run_average": "earned_run_average",
    "whip": "whip",
    "strikeouts_per_nine": "strikeouts_per_nine",
    "walks_per_nine": "walks_per_nine",
    "home_runs_allowed": "home_runs_allowed",
    "runs_allowed": "runs_allowed",
}

FIELDING_TO_TEAM_STATS_FIELDS = {
    "fielding_percentage": "fielding_percentage",
    "errors": "errors",
    "double_plays": "double_plays",
}


class TeamStatsMapper:
    """Mapper for converting between TeamStats entities and database models."""

    @staticmethod
    def to_entity(
        hitting_stats: HittingStatsModel | None,
        pitching_stats: PitchingStatsModel | None,
        fielding_stats: FieldingStatsModel | None,
    ) -> TeamStats | None:
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

        payload = TeamStatsMapper._extract_fields(hitting_stats, HITTING_TO_TEAM_STATS_FIELDS)
        payload.update(TeamStatsMapper._extract_fields(pitching_stats, PITCHING_TO_TEAM_STATS_FIELDS))
        payload.update(TeamStatsMapper._extract_fields(fielding_stats, FIELDING_TO_TEAM_STATS_FIELDS))
        team_stats = TeamStats.create(team_id=hitting_stats.team_id, season=hitting_stats.season, **payload)
        team_stats.id = hitting_stats.id
        team_stats.created_at = hitting_stats.created_at
        team_stats.updated_at = hitting_stats.updated_at
        if hasattr(hitting_stats, "team") and hitting_stats.team:
            team_stats.team = TeamStatsMapper._team_model_to_entity(hitting_stats.team)
        return team_stats

    @staticmethod
    def _extract_fields(model: object | None, field_map: dict[str, str]) -> dict[str, int | float]:
        if model is None:
            return {}
        return {target: getattr(model, source, 0) for target, source in field_map.items()}

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
    def update_hitting_model(entity: TeamStats, model: HittingStatsModel | None = None) -> HittingStatsModel:
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
    def update_pitching_model(entity: TeamStats, model: PitchingStatsModel | None = None) -> PitchingStatsModel:
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
    def update_fielding_model(entity: TeamStats, model: FieldingStatsModel | None = None) -> FieldingStatsModel:
        """Update or create a FieldingStatsModel from a TeamStats entity."""
        if not model:
            model = FieldingStatsModel(team_id=entity.team_id, season=entity.season)

        model.fielding_percentage = entity.fielding_percentage
        model.errors = entity.errors
        model.double_plays = entity.double_plays
        return model
