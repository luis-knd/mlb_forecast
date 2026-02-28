"""Helpers for building typed payloads used by stats entities factories."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

COMMON_BLOCKED_KEYS = frozenset({"id", "team_id", "season", "created_at", "updated_at"})


def build_stats_payload(
    stats: Mapping[str, int | float],
    extra_blocked_keys: frozenset[str] = frozenset(),
) -> tuple[datetime, dict[str, Any]]:
    blocked_keys = COMMON_BLOCKED_KEYS | extra_blocked_keys
    payload: dict[str, Any] = {}
    for key, value in stats.items():
        if key in blocked_keys:
            continue
        payload[key] = value
    return datetime.now(), payload
