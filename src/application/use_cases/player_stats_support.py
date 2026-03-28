"""
Support functions for player stats persistence use cases.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord

PLAYER_STATS_GROUP_SEQUENCE = ("hitting", "pitching", "fielding", "catching", "running")
PLAYER_STATS_HISTORY_TYPES = ("gameLog", "statSplits")
ALLOWED_PLAYER_STATS_GROUPS = set(PLAYER_STATS_GROUP_SEQUENCE) | {"all"}
ALLOWED_PLAYER_GAME_TYPES = {"R", "S", "P", "W", "A", "D", "F", "L"}

PLAYER_STATS_SEASONAL_FIELDS = {
    "hitting": {
        "int": {
            "games_played": "gamesPlayed",
            "at_bats": "atBats",
            "plate_appearances": "plateAppearances",
            "hits": "hits",
            "doubles": "doubles",
            "triples": "triples",
            "home_runs": "homeRuns",
            "runs_scored": "runs",
            "runs_batted_in": "rbi",
            "stolen_bases": "stolenBases",
            "caught_stealing": "caughtStealing",
            "base_on_balls": "baseOnBalls",
            "strikeouts": "strikeOuts",
            "hit_by_pitch": "hitByPitch",
            "sacrifice_hits": "sacBunts",
            "sacrifice_flies": "sacFlies",
            "left_on_base": "leftOnBase",
            "intentional_walks": "intentionalWalks",
            "total_bases": "totalBases",
        },
        "float": {
            "batting_average": "avg",
            "on_base_percentage": "obp",
            "slugging_percentage": "slg",
            "ops": "ops",
            "babip": "babip",
            "at_bats_per_home_run": "atBatsPerHomeRun",
            "stolen_base_percentage": "stolenBasePercentage",
        },
        "weight_field": "plate_appearances",
    },
    "pitching": {
        "int": {
            "games_played": "gamesPlayed",
            "games_started": "gamesStarted",
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
            "outs": "outs",
            "strikes": "strikes",
            "pickoffs": "pickoffs",
            "quality_starts": "qualityStarts",
        },
        "float": {
            "innings_pitched": "inningsPitched",
            "earned_run_average": "era",
            "whip": "whip",
            "strikeouts_per_nine": "strikeoutsPer9Inn",
            "walks_per_nine": "walksPer9Inn",
            "hits_per_nine": "hitsPer9Inn",
            "home_runs_per_nine": "homeRunsPer9",
            "strikeout_to_walk_ratio": "strikeoutWalkRatio",
            "pitches_per_inning": "pitchesPerInning",
            "batting_average_against": "avg",
            "on_base_percentage": "obp",
            "slugging_percentage": "slg",
            "ops": "ops",
            "strike_percentage": "strikePercentage",
            "win_percentage": "winPercentage",
        },
        "weight_field": "innings_pitched",
    },
    "fielding": {
        "int": {
            "games_played": "gamesPlayed",
            "games_started": "gamesStarted",
            "total_chances": "chances",
            "putouts": "putOuts",
            "assists": "assists",
            "errors": "errors",
            "throwing_errors": "throwingErrors",
            "double_plays": "doublePlays",
            "triple_plays": "triplePlays",
            "outfield_assists": "outfieldAssists",
            "passed_balls": "passedBall",
            "wild_pitches": "wildPitches",
            "stolen_bases_allowed": "stolenBases",
            "caught_stealing": "caughtStealing",
            "catchers_interference": "catchersInterference",
            "pickoffs": "pickoffs",
        },
        "float": {
            "innings_played": "innings",
            "fielding_percentage": "fielding",
            "defensive_efficiency_ratio": "defensiveEfficiencyRatio",
            "range_factor_per_game": "rangeFactorPerGame",
            "range_factor_per_nine": "rangeFactorPer9Inn",
            "stolen_base_percentage": "stolenBasePercentage",
        },
        "weight_field": "total_chances",
    },
    "catching": {
        "int": {
            "games_played": "gamesPlayed",
            "games_pitched": "gamesPitched",
            "at_bats": "atBats",
            "hits": "hits",
            "runs": "runs",
            "home_runs": "homeRuns",
            "strikeouts": "strikeOuts",
            "base_on_balls": "baseOnBalls",
            "intentional_walks": "intentionalWalks",
            "hit_by_pitch": "hitByPitch",
            "total_bases": "totalBases",
            "sacrifice_bunts": "sacBunts",
            "sacrifice_flies": "sacFlies",
            "passed_balls": "passedBall",
            "wild_pitches": "wildPitches",
            "stolen_bases_allowed": "stolenBases",
            "caught_stealing": "caughtStealing",
            "pickoffs": "pickoffs",
            "pickoff_attempts": "pickoffAttempts",
            "catchers_interference": "catchersInterference",
            "earned_runs": "earnedRuns",
            "batters_faced": "battersFaced",
            "hit_batsmen": "hitBatsmen",
        },
        "float": {
            "batting_average": "avg",
            "on_base_percentage": "obp",
            "slugging_percentage": "slg",
            "ops": "ops",
            "stolen_base_percentage": "stolenBasePercentage",
            "strikeout_walk_ratio": "strikeoutWalkRatio",
        },
        "weight_field": "games_played",
    },
    "running": {
        "int": {
            "games_played": "gamesPlayed",
            "plate_appearances": "plateAppearances",
            "stolen_bases": "stolenBases",
            "caught_stealing": "caughtStealing",
            "runs": "runs",
            "base_on_balls": "baseOnBalls",
            "opportunities": "opportunities",
        },
        "float": {
            "stolen_base_percentage": "stolenBasePercentage",
        },
        "weight_field": "opportunities",
    },
}


def normalize_stat_group(group: str) -> str:
    normalized_group = group.strip().lower()
    if normalized_group not in ALLOWED_PLAYER_STATS_GROUPS:
        raise ValueError(f"group must be one of: {', '.join(sorted(ALLOWED_PLAYER_STATS_GROUPS))}")
    return normalized_group


def normalize_game_type(game_type: str | None) -> str:
    normalized_game_type = (game_type or "R").strip().upper()
    if normalized_game_type not in ALLOWED_PLAYER_GAME_TYPES:
        raise ValueError(f"gameType must be one of: {', '.join(sorted(ALLOWED_PLAYER_GAME_TYPES))}")
    return normalized_game_type


def safe_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def safe_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_datetime_candidate(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def iter_response_splits(stats_response: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for block in stats_response.get("stats_data", []):
        yield from block.get("splits", [])


def resolve_requested_groups(group: str) -> tuple[str, ...]:
    normalized_group = normalize_stat_group(group)
    if normalized_group == "all":
        return PLAYER_STATS_GROUP_SEQUENCE
    return (normalized_group,)


def normalize_aggregate_metrics(stat_group: str, stat_payload: dict[str, Any]) -> dict[str, Any]:
    field_config = PLAYER_STATS_SEASONAL_FIELDS[stat_group]
    metrics: dict[str, Any] = {}
    for field_name, source_key in field_config["int"].items():
        metrics[field_name] = safe_int(stat_payload.get(source_key))
    for field_name, source_key in field_config["float"].items():
        metrics[field_name] = safe_float(stat_payload.get(source_key))
    return metrics


def merge_metrics(base_metrics: dict[str, Any], incoming_metrics: dict[str, Any]) -> dict[str, Any]:
    merged_metrics = dict(base_metrics)
    for key, value in incoming_metrics.items():
        if isinstance(value, float):
            if value != 0.0:
                merged_metrics[key] = value
            continue
        if value not in (None, 0, ""):
            merged_metrics[key] = value
    return merged_metrics


def resolve_team_mlb_id(split_payload: dict[str, Any]) -> int | None:
    team_data = split_payload.get("team") or {}
    team_id = team_data.get("id")
    return safe_int(team_id) or None


def build_external_reference(stat_type: str, split_payload: dict[str, Any], index: int) -> str:
    if stat_type == "gameLog":
        for candidate in (
            split_payload.get("game", {}).get("gamePk"),
            split_payload.get("gamePk"),
            split_payload.get("gameId"),
            split_payload.get("date"),
        ):
            if candidate:
                return str(candidate)
    canonical = json.dumps(split_payload, sort_keys=True, default=str)
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()
    return f"{stat_type}-{index}-{digest[:16]}"


def build_history_entry_key(
    stat_type: str,
    external_reference: str,
    split_payload: dict[str, Any],
    context_key: str | None,
    context_value: str | None,
) -> str:
    canonical_payload = json.dumps(split_payload, sort_keys=True, separators=(",", ":"), default=str)
    payload_digest = hashlib.sha1(canonical_payload.encode("utf-8")).hexdigest()[:16]
    return "|".join((stat_type, external_reference, context_key or "-", context_value or "-", payload_digest))


def build_history_context(split_payload: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    split_context = split_payload.get("split")
    if not isinstance(split_context, dict):
        return None, None, None
    context_key = split_context.get("code") or split_context.get("id")
    context_value = split_context.get("value") or split_context.get("code")
    context_label = split_context.get("description") or split_context.get("displayName") or split_context.get("name")
    return _to_optional_string(context_key), _to_optional_string(context_value), _to_optional_string(context_label)


def build_group_record(
    player_id: int,
    team_id: int,
    season: int,
    game_type: str,
    stat_group: str,
    metrics: dict[str, Any],
    raw_payload: dict[str, Any],
    source_updated_at: datetime | None = None,
) -> PlayerStatsGroupRecord:
    return PlayerStatsGroupRecord.create(
        player_id=player_id,
        team_id=team_id,
        season=season,
        game_type=game_type,
        stat_group=stat_group,
        metrics=metrics,
        raw_payload=raw_payload,
        source_updated_at=source_updated_at,
    )


def build_history_record(
    player_id: int,
    team_id: int | None,
    season: int,
    game_type: str,
    stat_group: str,
    stat_type: str,
    split_payload: dict[str, Any],
    index: int,
) -> PlayerStatsHistoryRecord:
    context_key, context_value, context_label = build_history_context(split_payload)
    event_date = parse_datetime_candidate(split_payload.get("date"))
    external_reference = build_external_reference(stat_type, split_payload, index)
    return PlayerStatsHistoryRecord.create(
        player_id=player_id,
        team_id=team_id,
        season=season,
        game_type=game_type,
        stat_group=stat_group,
        stat_type=stat_type,
        external_reference=external_reference,
        history_entry_key=build_history_entry_key(
            stat_type=stat_type,
            external_reference=external_reference,
            split_payload=split_payload,
            context_key=context_key,
            context_value=context_value,
        ),
        payload=split_payload,
        event_date=event_date,
        context_key=context_key,
        context_value=context_value,
        context_label=context_label,
    )


def build_career_group_record(
    player_id: int,
    game_type: str,
    stat_group: str,
    records: list[PlayerStatsGroupRecord],
) -> PlayerStatsGroupRecord:
    return build_aggregated_group_record(
        player_id=player_id,
        season=0,
        game_type=game_type,
        stat_group=stat_group,
        records=records,
    )


def build_aggregated_group_record(
    player_id: int,
    season: int,
    game_type: str,
    stat_group: str,
    records: list[PlayerStatsGroupRecord],
) -> PlayerStatsGroupRecord:
    metrics = aggregate_metrics(records, stat_group)
    source_updated_at = max((record.source_updated_at for record in records if record.source_updated_at), default=None)
    ingested_at = max((record.ingested_at for record in records if record.ingested_at), default=None)
    created_at = min((record.created_at for record in records if record.created_at), default=None)
    updated_at = max((record.updated_at for record in records if record.updated_at), default=None)
    return PlayerStatsGroupRecord(
        id=None,
        player_id=player_id,
        team_id=None,
        season=season,
        game_type=game_type,
        stat_group=stat_group,
        metrics=metrics,
        source="derived",
        source_updated_at=source_updated_at,
        ingested_at=ingested_at,
        raw_payload=None,
        created_at=created_at,
        updated_at=updated_at,
    )


def aggregate_metrics(records: list[PlayerStatsGroupRecord], stat_group: str) -> dict[str, Any]:
    if not records:
        return {}

    field_config = PLAYER_STATS_SEASONAL_FIELDS[stat_group]
    weight_field = field_config["weight_field"]
    aggregate_totals: dict[str, float] = defaultdict(float)

    for record in records:
        for field_name in field_config["int"]:
            aggregate_totals[field_name] += safe_int(record.metrics.get(field_name))

    for field_name in field_config["float"]:
        weight_total = 0.0
        weighted_sum = 0.0
        for record in records:
            weight = float(record.metrics.get(weight_field) or 0.0)
            value = float(record.metrics.get(field_name) or 0.0)
            weight_total += weight
            weighted_sum += value * weight
        aggregate_totals[field_name] = (weighted_sum / weight_total) if weight_total > 0 else 0.0

    aggregated_metrics: dict[str, Any] = {}
    for field_name in field_config["int"]:
        aggregated_metrics[field_name] = int(aggregate_totals[field_name])
    for field_name in field_config["float"]:
        aggregated_metrics[field_name] = round(aggregate_totals[field_name], 6)
    return aggregated_metrics


def group_records_by_season(records: Iterable[PlayerStatsGroupRecord]) -> dict[int, list[PlayerStatsGroupRecord]]:
    grouped_records: dict[int, list[PlayerStatsGroupRecord]] = defaultdict(list)
    for record in records:
        grouped_records[record.season].append(record)
    return dict(grouped_records)


def limit_recent_history(
    records: list[PlayerStatsHistoryRecord],
    days_back: int | None,
) -> list[PlayerStatsHistoryRecord]:
    if days_back is None:
        return records
    threshold = datetime.now(UTC).replace(tzinfo=None)  # compare against naive dates from sqlite safely
    limited_records: list[PlayerStatsHistoryRecord] = []
    for record in records:
        if record.event_date is None:
            continue
        event_date = (
            record.event_date.astimezone(UTC).replace(tzinfo=None) if record.event_date.tzinfo else record.event_date
        )
        if (threshold - event_date).days <= days_back:
            limited_records.append(record)
    return limited_records


def deduplicate_history_records(records: list[PlayerStatsHistoryRecord]) -> list[PlayerStatsHistoryRecord]:
    deduplicated_records: list[PlayerStatsHistoryRecord] = []
    seen_entry_keys: set[str] = set()

    for record in records:
        if record.history_entry_key in seen_entry_keys:
            continue
        seen_entry_keys.add(record.history_entry_key)
        deduplicated_records.append(record)

    return deduplicated_records


def _to_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized_value = str(value).strip()
    return normalized_value or None
