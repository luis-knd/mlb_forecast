from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Iterable, List, Optional, Type

from src.domain.entities.player import Player
from src.domain.entities.team import Team
from src.interface.rest.generated.models.models import (
    CatchingStatsDTO,
    FieldingStatsDTO,
    GameDTO,
    HittingStatsDTO,
    PitchingStatsDTO,
    TeamDTO,
    TeamSeasonStatsDTO,
)


def _get(source: Any, name: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _to_number(value: Any, caster):
    if value is None:
        return None
    if callable(value):
        try:
            value = value()
        except Exception:
            return None
    try:
        return caster(value)
    except (TypeError, ValueError):
        return None


def _i(v: Any) -> Optional[int]:
    return _to_number(v, int)


def _f(v: Any) -> Optional[float]:
    return _to_number(v, float)


def _build_dto(dto_cls: Type, **kwargs):
    # Solo pasa al DTO las keys que existen en el modelo y con valor no None
    allowed = set(getattr(dto_cls, "model_fields").keys())
    payload = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    return dto_cls(**payload)


PITCHING_INT_DTO_FIELDS = {
    "games_played": "games_played",
    "wins": "wins",
    "losses": "losses",
    "saves": "saves",
    "save_opportunities": "save_opportunities",
    "holds": "holds",
    "blown_saves": "blown_saves",
    "batters_faced": "batters_faced",
    "hits_allowed": "hits_allowed",
    "runs_allowed": "runs_allowed",
    "earned_runs": "earned_runs",
    "home_runs_allowed": "home_runs_allowed",
    "strikeouts": "strikeouts",
    "base_on_balls": "base_on_balls",
    "intentional_walks": "intentional_walks",
    "hit_batsmen": "hit_batsmen",
    "wild_pitches": "wild_pitches",
    "balks": "balks",
    "number_of_pitches": "number_of_pitches",
    "complete_games": "complete_games",
    "shutouts": "shutouts",
    "games_started": "games_started",
    "ground_outs": "ground_outs",
    "air_outs": "air_outs",
    "doubles": "doubles",
    "triples": "triples",
    "at_bats": "at_bats",
    "outs": "outs",
    "strikes": "strikes",
    "pickoffs": "pickoffs",
    "total_bases": "total_bases",
    "games_finished": "games_finished",
    "catchers_interference": "catchers_interference",
    "sacrifice_bunts": "sacrifice_bunts",
    "sacrifice_flies": "sacrifice_flies",
    "ground_into_double_play": "ground_into_double_play",
    "caught_stealing": "caught_stealing",
    "inherited_runners": "inherited_runners",
    "inherited_runners_scored": "inherited_runners_scored",
    "quality_starts": "quality_starts",
}

PITCHING_FLOAT_DTO_FIELDS = {
    "innings_pitched": "innings_pitched",
    "earned_run_average": "earned_run_average",
    "whip": "whip",
    "strikeouts_per_nine": "strikeouts_per_nine",
    "walks_per_nine": "walks_per_nine",
    "hits_per_nine": "hits_per_nine",
    "home_runs_per_nine": "home_runs_per_nine",
    "strikeout_to_walk_ratio": "strikeout_to_walk_ratio",
    "ground_outs_to_airouts": "ground_outs_to_airouts",
    "pitches_per_inning": "pitches_per_inning",
    "batting_average_against": "batting_average_against",
    "on_base_percentage": "on_base_percentage",
    "slugging_percentage": "slugging_percentage",
    "ops": "ops",
    "stolen_base_percentage": "stolen_base_percentage",
    "strike_percentage": "strike_percentage",
    "runs_scored_per_nine": "runs_scored_per_nine",
}


def _resolve_pitching_win_percentage(src: Any) -> Optional[float]:
    win_pct = _f(_get(src, "win_percentage"))
    if win_pct is not None:
        return win_pct
    wins = _f(_get(src, "wins"))
    games_played = _f(_get(src, "games_played"))
    if wins is None or games_played is None or games_played <= 0:
        return None
    return wins / games_played


def to_team_dto(team: Team) -> TeamDTO:
    return TeamDTO(
        id=getattr(team, "id", None),
        mlb_id=getattr(team, "mlb_id", 0),
        name=getattr(team, "name", ""),
        abbreviation=getattr(team, "abbreviation", ""),
        city=getattr(team, "city", ""),
        division=getattr(team, "division", ""),
        league=getattr(team, "league", ""),
        venue_name=getattr(team, "venue_name", None),
        created_at=getattr(team, "created_at", None),
        updated_at=getattr(team, "updated_at", None),
    )


def to_team_dto_list(teams: Iterable[Team]) -> List[TeamDTO]:
    return [to_team_dto(t) for t in teams]


def to_player_payload(player: Player) -> dict[str, Any]:
    return {
        "id": player.id,
        "mlb_id": player.mlb_id,
        "first_name": player.first_name,
        "last_name": player.last_name,
        "full_name": player.full_name(),
        "position": player.position,
        "bats": player.bats,
        "throws": player.throws,
        "birth_date": player.birth_date,
        "active": player.active,
        "current_team_id": player.current_team_id,
        "created_at": player.created_at,
        "updated_at": player.updated_at,
    }


def to_player_payload_list(players: Iterable[Player]) -> List[dict[str, Any]]:
    return [to_player_payload(player) for player in players]


def to_hitting_stats_dto(src: Any) -> HittingStatsDTO:
    data = dict(
        games_played=_i(_get(src, "games_played")),
        plate_appearances=_i(_get(src, "plate_appearances")),
        at_bats=_i(_get(src, "at_bats")),
        hits=_i(_get(src, "hits")),
        doubles=_i(_get(src, "doubles")),
        triples=_i(_get(src, "triples")),
        home_runs=_i(_get(src, "home_runs")),
        # Nombres alineados a DB + alias de compatibilidad
        runs_scored=_i(_get(src, "runs_scored", _get(src, "runs"))),
        runs_batted_in=_i(_get(src, "runs_batted_in", _get(src, "rbi"))),
        stolen_bases=_i(_get(src, "stolen_bases")),
        caught_stealing=_i(_get(src, "caught_stealing")),
        base_on_balls=_i(_get(src, "base_on_balls", _get(src, "walks"))),
        strikeouts=_i(_get(src, "strikeouts")),
        hit_by_pitch=_i(_get(src, "hit_by_pitch")),
        sacrifice_hits=_i(_get(src, "sacrifice_hits", _get(src, "sacrifice_bunts"))),
        sacrifice_flies=_i(_get(src, "sacrifice_flies")),
        ground_into_double_play=_i(_get(src, "ground_into_double_play")),
        left_on_base=_i(_get(src, "left_on_base")),
        total_bases=_i(_get(src, "total_bases")),
        batting_average=_f(_get(src, "batting_average")),
        on_base_percentage=_f(_get(src, "on_base_percentage")),
        slugging_percentage=_f(_get(src, "slugging_percentage")),
        ops=_f(_get(src, "ops")),
        babip=_f(_get(src, "babip")),
        at_bats_per_home_run=_f(_get(src, "at_bats_per_home_run")),
        stolen_base_percentage=_f(_get(src, "stolen_base_percentage")),
        ground_outs=_i(_get(src, "ground_outs")),
        air_outs=_i(_get(src, "air_outs")),
        ground_outs_to_air_outs=_f(_get(src, "ground_outs_to_air_outs", _get(src, "ground_outs_to_airouts"))),
        number_of_pitches=_i(_get(src, "number_of_pitches")),
        intentional_walks=_i(_get(src, "intentional_walks")),
    )
    return _build_dto(HittingStatsDTO, **data)


def to_pitching_stats_dto(src: Any) -> PitchingStatsDTO:
    data: dict[str, Any] = {}
    for field_name, source_name in PITCHING_INT_DTO_FIELDS.items():
        data[field_name] = _i(_get(src, source_name))
    for field_name, source_name in PITCHING_FLOAT_DTO_FIELDS.items():
        data[field_name] = _f(_get(src, source_name))
    data["win_percentage"] = _resolve_pitching_win_percentage(src)
    return _build_dto(PitchingStatsDTO, **data)


def to_fielding_stats_dto(src: Any) -> FieldingStatsDTO:
    return FieldingStatsDTO(
        games_played=_i(_get(src, "games_played")),
        games_started=_i(_get(src, "games_started")),
        innings_played=_i(_get(src, "innings_played")),
        total_chances=_i(_get(src, "total_chances")),
        putouts=_i(_get(src, "putouts")),
        assists=_i(_get(src, "assists")),
        errors=_i(_get(src, "errors")),
        throwing_errors=_i(_get(src, "throwing_errors")),
        double_plays=_i(_get(src, "double_plays")),
        triple_plays=_i(_get(src, "triple_plays")),
        fielding_percentage=_f(_get(src, "fielding_percentage")),
        defensive_efficiency_ratio=_f(_get(src, "defensive_efficiency_ratio")),
        range_factor_per_game=_f(_get(src, "range_factor_per_game")),
        range_factor_per_nine=_f(_get(src, "range_factor_per_nine")),
        outfield_assists=_i(_get(src, "outfield_assists")),
        passed_balls=_i(_get(src, "passed_balls")),
        wild_pitches=_i(_get(src, "wild_pitches")),
        stolen_bases_allowed=_i(_get(src, "stolen_bases_allowed")),
        caught_stealing=_i(_get(src, "caught_stealing")),
        stolen_base_percentage=_f(_get(src, "stolen_base_percentage")),
        catchers_interference=_i(_get(src, "catchers_interference")),
        pickoffs=_i(_get(src, "pickoffs")),
    )


def to_catching_stats_dto(src: Any) -> CatchingStatsDTO:
    return CatchingStatsDTO(
        games_played=_i(_get(src, "games_played")),
        games_pitched=_i(_get(src, "games_pitched")),
        at_bats=_i(_get(src, "at_bats")),
        hits=_i(_get(src, "hits")),
        runs=_i(_get(src, "runs")),
        home_runs=_i(_get(src, "home_runs")),
        strikeouts=_i(_get(src, "strikeouts")),
        base_on_balls=_i(_get(src, "base_on_balls")),
        intentional_walks=_i(_get(src, "intentional_walks")),
        hit_by_pitch=_i(_get(src, "hit_by_pitch")),
        total_bases=_i(_get(src, "total_bases")),
        sacrifice_bunts=_i(_get(src, "sacrifice_bunts")),
        sacrifice_flies=_i(_get(src, "sacrifice_flies")),
        batting_average=_f(_get(src, "batting_average")),
        on_base_percentage=_f(_get(src, "on_base_percentage")),
        slugging_percentage=_f(_get(src, "slugging_percentage")),
        ops=_f(_get(src, "ops")),
        passed_balls=_i(_get(src, "passed_balls")),
        wild_pitches=_i(_get(src, "wild_pitches")),
        stolen_bases_allowed=_i(_get(src, "stolen_bases_allowed")),
        caught_stealing=_i(_get(src, "caught_stealing")),
        stolen_base_percentage=_f(_get(src, "stolen_base_percentage")),
        pickoffs=_i(_get(src, "pickoffs")),
        pickoff_attempts=_i(_get(src, "pickoff_attempts")),
        catchers_interference=_i(_get(src, "catchers_interference")),
        earned_runs=_i(_get(src, "earned_runs")),
        batters_faced=_i(_get(src, "batters_faced")),
        hit_batsmen=_i(_get(src, "hit_batsmen")),
        strikeout_walk_ratio=_f(_get(src, "strikeout_walk_ratio")),
    )


def to_team_stats_dto(model: Any) -> TeamSeasonStatsDTO:
    hitting_src = _get(model, "hitting", _get(model, "hitting_stats", {}))
    pitching_src = _get(model, "pitching", _get(model, "pitching_stats", {}))
    fielding_src = _get(model, "fielding", _get(model, "fielding_stats", {}))
    catching_src = _get(model, "catching", _get(model, "catching_stats", {}))

    return TeamSeasonStatsDTO(
        team_id=(_i(_get(model, "team_id", _get(model, "teamId"))) or 0),
        season=(_i(_get(model, "season")) or 0),
        hitting=to_hitting_stats_dto(hitting_src) if hitting_src is not None else None,
        pitching=to_pitching_stats_dto(pitching_src) if pitching_src is not None else None,
        fielding=to_fielding_stats_dto(fielding_src) if fielding_src is not None else None,
        catching=to_catching_stats_dto(catching_src) if catching_src is not None else None,
        updated_at=_get(model, "updated_at", _get(model, "updatedAt")),
    )


def to_game_dto(game: Any) -> GameDTO:
    return GameDTO(
        id=_get(game, "id"),
        mlb_game_id=_get(game, "mlb_game_id"),
        home_team_id=_get(game, "home_team_id"),
        away_team_id=_get(game, "away_team_id"),
        game_date=_get(game, "game_date"),
        status=_get(game, "status"),
        scheduled_innings=_get(game, "scheduled_innings", 9),
        home_score=_get(game, "home_score"),
        away_score=_get(game, "away_score"),
        winning_team_id=_get(game, "winning_team_id"),
        created_at=_get(game, "created_at"),
        updated_at=_get(game, "updated_at"),
    )


def to_game_dto_list(games: Iterable[Any]) -> List[GameDTO]:
    return [to_game_dto(g) for g in games]
