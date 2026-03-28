"""
Player stats persistence entities.
These entities model persisted player stat snapshots and history records.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

VALID_PLAYER_STAT_GROUPS = frozenset({"hitting", "pitching", "fielding", "catching", "running"})
VALID_PLAYER_HISTORY_TYPES = frozenset({"gameLog", "statSplits"})


def _normalize_stat_group(stat_group: str) -> str:
    normalized_group = stat_group.strip().lower()
    if normalized_group not in VALID_PLAYER_STAT_GROUPS:
        raise ValueError(f"stat_group must be one of: {', '.join(sorted(VALID_PLAYER_STAT_GROUPS))}")
    return normalized_group


def _normalize_history_type(stat_type: str) -> str:
    normalized_type = stat_type.strip()
    if normalized_type not in VALID_PLAYER_HISTORY_TYPES:
        raise ValueError(f"stat_type must be one of: {', '.join(sorted(VALID_PLAYER_HISTORY_TYPES))}")
    return normalized_type


@dataclass
class PlayerStatsGroupRecord:
    """Persisted aggregate player stats for one player, season, game type, and stat group."""

    id: int | None
    player_id: int
    team_id: int | None
    season: int
    game_type: str
    stat_group: str
    metrics: dict[str, Any] = field(default_factory=dict)
    source: str = "statsapi"
    source_updated_at: datetime | None = None
    ingested_at: datetime | None = None
    raw_payload: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        player_id: int,
        team_id: int | None,
        season: int,
        game_type: str,
        stat_group: str,
        metrics: dict[str, Any],
        source: str = "statsapi",
        source_updated_at: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> "PlayerStatsGroupRecord":
        """Create a new persisted player stats snapshot."""
        now = datetime.now()
        return cls(
            id=None,
            player_id=player_id,
            team_id=team_id,
            season=season,
            game_type=game_type.strip().upper(),
            stat_group=_normalize_stat_group(stat_group),
            metrics=dict(metrics),
            source=source,
            source_updated_at=source_updated_at,
            ingested_at=now,
            raw_payload=raw_payload,
            created_at=now,
            updated_at=now,
        )

    def cache_key(self) -> str:
        """Build a deterministic cache token for a persisted group record."""
        return (
            f"player_stats:aggregate:player={self.player_id}:season={self.season}:"
            f"gameType={self.game_type}:group={self.stat_group}"
        )


@dataclass
class PlayerStatsHistoryRecord:
    """Persisted player stats history entry for game logs or stat splits."""

    id: int | None
    player_id: int
    team_id: int | None
    season: int
    game_type: str
    stat_group: str
    stat_type: str
    external_reference: str
    history_entry_key: str
    event_date: datetime | None
    payload: dict[str, Any]
    context_key: str | None = None
    context_value: str | None = None
    context_label: str | None = None
    source: str = "statsapi"
    ingested_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        player_id: int,
        team_id: int | None,
        season: int,
        game_type: str,
        stat_group: str,
        stat_type: str,
        external_reference: str,
        payload: dict[str, Any],
        history_entry_key: str | None = None,
        event_date: datetime | None = None,
        context_key: str | None = None,
        context_value: str | None = None,
        context_label: str | None = None,
        source: str = "statsapi",
    ) -> "PlayerStatsHistoryRecord":
        """Create a new persisted player history record."""
        now = datetime.now()
        normalized_external_reference = str(external_reference).strip()
        normalized_history_entry_key = (
            str(history_entry_key).strip() if history_entry_key is not None else normalized_external_reference
        )
        if not normalized_history_entry_key:
            normalized_history_entry_key = normalized_external_reference
        return cls(
            id=None,
            player_id=player_id,
            team_id=team_id,
            season=season,
            game_type=game_type.strip().upper(),
            stat_group=_normalize_stat_group(stat_group),
            stat_type=_normalize_history_type(stat_type),
            external_reference=normalized_external_reference,
            history_entry_key=normalized_history_entry_key,
            event_date=event_date,
            payload=dict(payload),
            context_key=context_key,
            context_value=context_value,
            context_label=context_label,
            source=source,
            ingested_at=now,
            created_at=now,
            updated_at=now,
        )

    def cache_key(self) -> str:
        """Build a deterministic cache token for a persisted history record family."""
        return (
            f"player_stats:history:player={self.player_id}:season={self.season}:"
            f"gameType={self.game_type}:group={self.stat_group}:type={self.stat_type}"
        )
