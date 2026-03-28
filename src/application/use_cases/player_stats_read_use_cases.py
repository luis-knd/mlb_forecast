"""
Read use cases for persisted player stats.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from application.ports.cache import CachePort
from application.ports.player_stats_repository import PlayerStatsRepositoryPort
from application.use_cases.player_stats_support import (
    build_aggregated_group_record,
    build_career_group_record,
    group_records_by_season,
    limit_recent_history,
    normalize_game_type,
    normalize_stat_group,
    resolve_requested_groups,
)
from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord

CACHE_KEY_PREFIX = "player_stats:persisted"
PLAYER_STATS_READ_TTL_SECONDS = 1800
MIN_SUPPORTED_SEASON = 1876
T = TypeVar("T")


def _validate_season(season: int) -> None:
    if season < MIN_SUPPORTED_SEASON:
        raise ValueError(f"season must be greater than or equal to {MIN_SUPPORTED_SEASON}")


def _build_cache_key(
    *,
    player_id: int,
    stats: str,
    group: str,
    game_type: str,
    season: int | None = None,
    days_back: int | None = None,
    limit: int | None = None,
) -> str:
    return (
        f"{CACHE_KEY_PREFIX}:player={player_id}:stats={stats}:group={group}:"
        f"gameType={game_type}:season={season or 'all'}:daysBack={days_back or 'none'}:limit={limit or 'none'}"
    )


async def _get_cached_or_load(
    cache: CachePort,
    cache_key: str,
    loader: Callable[[], Awaitable[T]],
) -> T:
    cached_value = await cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    loaded_value = await loader()
    await cache.set(cache_key, loaded_value, ttl=PLAYER_STATS_READ_TTL_SECONDS)
    return loaded_value


def _filter_group(records: list[PlayerStatsGroupRecord], group: str) -> list[PlayerStatsGroupRecord]:
    if group == "all":
        return records
    return [record for record in records if record.stat_group == group]


def _sort_group_records(records: list[PlayerStatsGroupRecord]) -> list[PlayerStatsGroupRecord]:
    return sorted(
        records,
        key=lambda record: (record.season, record.stat_group, record.team_id or 0),
        reverse=True,
    )


def _sort_history_records(records: list[PlayerStatsHistoryRecord]) -> list[PlayerStatsHistoryRecord]:
    return sorted(
        records,
        key=lambda record: (record.event_date is not None, record.event_date, record.external_reference),
        reverse=True,
    )


class _PlayerStatsReadBase:
    def __init__(self, player_stats_repository: PlayerStatsRepositoryPort, cache: CachePort):
        self.player_stats_repository = player_stats_repository
        self.cache = cache


class GetPersistedPlayerSeasonStatsUseCase(_PlayerStatsReadBase):
    async def execute(
        self,
        player_id: int,
        season: int,
        group: str = "all",
        game_type: str | None = None,
    ) -> list[PlayerStatsGroupRecord]:
        _validate_season(season)
        normalized_group = normalize_stat_group(group)
        normalized_game_type = normalize_game_type(game_type)
        cache_key = _build_cache_key(
            player_id=player_id,
            stats="season",
            group=normalized_group,
            season=season,
            game_type=normalized_game_type,
        )
        return await _get_cached_or_load(
            self.cache,
            cache_key,
            lambda: self._load_records(player_id, season, normalized_group, normalized_game_type),
        )

    async def _load_records(
        self,
        player_id: int,
        season: int,
        group: str,
        game_type: str,
    ) -> list[PlayerStatsGroupRecord]:
        records = await self.player_stats_repository.list_group_records(
            player_id=player_id,
            season=season,
            game_type=game_type,
        )
        return _sort_group_records(_filter_group(records, group))


class GetPersistedPlayerCareerStatsUseCase(_PlayerStatsReadBase):
    async def execute(
        self,
        player_id: int,
        group: str = "all",
        game_type: str | None = None,
    ) -> list[PlayerStatsGroupRecord]:
        normalized_group = normalize_stat_group(group)
        normalized_game_type = normalize_game_type(game_type)
        cache_key = _build_cache_key(
            player_id=player_id,
            stats="career",
            group=normalized_group,
            game_type=normalized_game_type,
        )
        return await _get_cached_or_load(
            self.cache,
            cache_key,
            lambda: self._load_records(player_id, normalized_group, normalized_game_type),
        )

    async def _load_records(
        self,
        player_id: int,
        group: str,
        game_type: str,
    ) -> list[PlayerStatsGroupRecord]:
        records = await self.player_stats_repository.list_group_records(player_id=player_id, game_type=game_type)
        aggregated_records = []
        for current_group in resolve_requested_groups(group):
            group_records = [record for record in records if record.stat_group == current_group]
            if not group_records:
                continue
            aggregated_records.append(
                build_career_group_record(
                    player_id=player_id,
                    game_type=game_type,
                    stat_group=current_group,
                    records=group_records,
                )
            )
        return _sort_group_records(aggregated_records)


class GetPersistedPlayerYearByYearStatsUseCase(_PlayerStatsReadBase):
    async def execute(
        self,
        player_id: int,
        group: str = "all",
        game_type: str | None = None,
    ) -> list[PlayerStatsGroupRecord]:
        normalized_group = normalize_stat_group(group)
        normalized_game_type = normalize_game_type(game_type)
        cache_key = _build_cache_key(
            player_id=player_id,
            stats="yearByYear",
            group=normalized_group,
            game_type=normalized_game_type,
        )
        return await _get_cached_or_load(
            self.cache,
            cache_key,
            lambda: self._load_records(player_id, normalized_group, normalized_game_type),
        )

    async def _load_records(
        self,
        player_id: int,
        group: str,
        game_type: str,
    ) -> list[PlayerStatsGroupRecord]:
        records = await self.player_stats_repository.list_group_records(player_id=player_id, game_type=game_type)
        aggregated_records = []
        for current_group in resolve_requested_groups(group):
            group_records = [record for record in records if record.stat_group == current_group]
            for season, season_records in group_records_by_season(group_records).items():
                aggregated_records.append(
                    build_aggregated_group_record(
                        player_id=player_id,
                        season=season,
                        game_type=game_type,
                        stat_group=current_group,
                        records=season_records,
                    )
                )
        return _sort_group_records(aggregated_records)


class GetPersistedPlayerGameLogsUseCase(_PlayerStatsReadBase):
    async def execute(
        self,
        player_id: int,
        season: int,
        group: str = "all",
        game_type: str | None = None,
        days_back: int | None = None,
        limit: int | None = None,
    ) -> list[PlayerStatsHistoryRecord]:
        _validate_season(season)
        normalized_group = normalize_stat_group(group)
        normalized_game_type = normalize_game_type(game_type)
        cache_key = _build_cache_key(
            player_id=player_id,
            stats="gameLog",
            group=normalized_group,
            game_type=normalized_game_type,
            season=season,
            days_back=days_back,
            limit=limit,
        )
        return await _get_cached_or_load(
            self.cache,
            cache_key,
            lambda: self._load_records(player_id, season, normalized_group, normalized_game_type, days_back, limit),
        )

    async def _load_records(
        self,
        player_id: int,
        season: int,
        group: str,
        game_type: str,
        days_back: int | None,
        limit: int | None,
    ) -> list[PlayerStatsHistoryRecord]:
        records = await self.player_stats_repository.list_history_records(
            player_id=player_id,
            stat_type="gameLog",
            season=season,
            game_type=game_type,
            stat_group=None if group == "all" else group,
            limit=limit,
        )
        return _sort_history_records(limit_recent_history(records, days_back))


class GetPersistedPlayerStatSplitsUseCase(_PlayerStatsReadBase):
    async def execute(
        self,
        player_id: int,
        season: int,
        group: str = "all",
        game_type: str | None = None,
        limit: int | None = None,
    ) -> list[PlayerStatsHistoryRecord]:
        _validate_season(season)
        normalized_group = normalize_stat_group(group)
        normalized_game_type = normalize_game_type(game_type)
        cache_key = _build_cache_key(
            player_id=player_id,
            stats="statSplits",
            group=normalized_group,
            game_type=normalized_game_type,
            season=season,
            limit=limit,
        )
        return await _get_cached_or_load(
            self.cache,
            cache_key,
            lambda: self._load_records(player_id, season, normalized_group, normalized_game_type, limit),
        )

    async def _load_records(
        self,
        player_id: int,
        season: int,
        group: str,
        game_type: str,
        limit: int | None,
    ) -> list[PlayerStatsHistoryRecord]:
        records = await self.player_stats_repository.list_history_records(
            player_id=player_id,
            stat_type="statSplits",
            season=season,
            game_type=game_type,
            stat_group=None if group == "all" else group,
            limit=limit,
        )
        return _sort_history_records(records)
