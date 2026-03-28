"""
Mappers for persisted player stats REST payloads.
"""

from __future__ import annotations

from typing import Any

from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord


def to_group_record_payload(record: PlayerStatsGroupRecord) -> dict[str, Any]:
    return {
        "player_id": record.player_id,
        "team_id": record.team_id,
        "season": record.season,
        "game_type": record.game_type,
        "stat_group": record.stat_group,
        "metrics": record.metrics,
        "source": record.source,
        "source_updated_at": record.source_updated_at,
        "ingested_at": record.ingested_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def to_history_record_payload(record: PlayerStatsHistoryRecord) -> dict[str, Any]:
    return {
        "player_id": record.player_id,
        "team_id": record.team_id,
        "season": record.season,
        "game_type": record.game_type,
        "stat_group": record.stat_group,
        "external_reference": record.external_reference,
        "event_date": record.event_date,
        "payload": record.payload,
        "context_key": record.context_key,
        "context_value": record.context_value,
        "context_label": record.context_label,
        "source": record.source,
        "ingested_at": record.ingested_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def to_group_collection_payload(
    *,
    player_id: int,
    stats: str,
    group: str,
    game_type: str,
    records: list[PlayerStatsGroupRecord],
    season: int | None = None,
) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "stats": stats,
        "group": group,
        "season": season,
        "game_type": game_type,
        "records": [to_group_record_payload(record) for record in records],
    }


def to_history_collection_payload(
    *,
    player_id: int,
    stats: str,
    group: str,
    game_type: str,
    season: int,
    records: list[PlayerStatsHistoryRecord],
    days_back: int | None = None,
) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "stats": stats,
        "group": group,
        "season": season,
        "game_type": game_type,
        "days_back": days_back,
        "records": [to_history_record_payload(record) for record in records],
    }
