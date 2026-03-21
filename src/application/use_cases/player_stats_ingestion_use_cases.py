"""
Player stats ingestion use cases.
These use cases persist player seasonal aggregates and history for future forecasting.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from application.ports.cache import CachePort
from application.ports.mlb_api import MLBApiPort
from application.ports.player_repository import PlayerRepositoryPort
from application.ports.player_stats_repository import PlayerStatsRepositoryPort
from application.ports.team_repository import TeamRepositoryPort
from application.use_cases.player_stats_support import (
    build_group_record,
    build_history_record,
    iter_response_splits,
    merge_metrics,
    normalize_aggregate_metrics,
    normalize_game_type,
    resolve_requested_groups,
    resolve_team_mlb_id,
)
from domain.entities.player import Player
from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord

CACHE_KEY_PREFIX = "player_stats:persisted"


def _validate_target_selector(player_id: int | None, team_id: int | None) -> None:
    selected_targets = [target for target in (player_id, team_id) if target is not None]
    if len(selected_targets) != 1:
        raise ValueError("Exactly one of playerId or teamId must be provided")


def _validate_season(season: int) -> None:
    if season < 1876:
        raise ValueError("season must be greater than or equal to 1876")


def _should_refresh_existing_records(
    existing_records: list[Any],
    season: int,
    force_refresh: bool,
) -> bool:
    if force_refresh or not existing_records:
        return True
    return season >= datetime.now().year


def _index_splits_by_team(stats_response: dict[str, Any] | None) -> dict[int | None, dict[str, Any]]:
    indexed_splits: dict[int | None, dict[str, Any]] = {}
    for split_payload in iter_response_splits(stats_response or {}):
        indexed_splits[resolve_team_mlb_id(split_payload)] = split_payload
    return indexed_splits


class _PlayerStatsIngestionBase:
    def __init__(
        self,
        player_repository: PlayerRepositoryPort,
        team_repository: TeamRepositoryPort,
        player_stats_repository: PlayerStatsRepositoryPort,
        mlb_api: MLBApiPort,
        cache: CachePort,
    ):
        self.player_repository = player_repository
        self.team_repository = team_repository
        self.player_stats_repository = player_stats_repository
        self.mlb_api = mlb_api
        self.cache = cache

    async def _resolve_target_players(self, player_id: int | None, team_id: int | None) -> list[Player]:
        _validate_target_selector(player_id=player_id, team_id=team_id)
        if player_id is not None:
            player = await self.player_repository.get_by_id(player_id)
            return [player] if player is not None else []
        return await self.player_repository.list_by_team(team_id or 0)

    async def _resolve_internal_team_id(self, player: Player, split_payload: dict[str, Any]) -> int | None:
        mlb_team_id = resolve_team_mlb_id(split_payload)
        if mlb_team_id is None:
            return player.current_team_id
        team = await self.team_repository.get_by_mlb_id(mlb_team_id)
        if team is None:
            return player.current_team_id
        return team.id

    async def _clear_player_stats_cache(self, player_id: int) -> None:
        await self.cache.clear(pattern=f"{CACHE_KEY_PREFIX}:player={player_id}:*")


class IngestPlayerSeasonStatsUseCase(_PlayerStatsIngestionBase):
    """Persist player seasonal aggregate stats from StatsAPI."""

    async def execute(
        self,
        season: int,
        group: str = "all",
        game_type: str | None = None,
        player_id: int | None = None,
        team_id: int | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        _validate_season(season)
        normalized_game_type = normalize_game_type(game_type)
        target_groups = resolve_requested_groups(group)
        players = await self._resolve_target_players(player_id=player_id, team_id=team_id)
        stats_created = 0
        stats_skipped = 0

        for player in players:
            player_updated = False
            for current_group in target_groups:
                upserted_count = await self._ingest_one_group(
                    player=player,
                    season=season,
                    game_type=normalized_game_type,
                    stat_group=current_group,
                    force_refresh=force_refresh,
                )
                if upserted_count > 0:
                    stats_created += upserted_count
                    player_updated = True
                else:
                    stats_skipped += 1
            if player_updated and player.id is not None:
                await self._clear_player_stats_cache(player.id)

        return {
            "operation": "player_stats_seasonal_ingestion",
            "players_processed": len(players),
            "group_records_upserted": stats_created,
            "group_records_skipped": stats_skipped,
            "season": season,
            "group": group,
            "game_type": normalized_game_type,
        }

    async def _fetch_group_payloads(
        self,
        player_mlb_id: int,
        season: int,
        game_type: str,
        stat_group: str,
    ) -> tuple[dict[str, Any] | None, dict[int | None, dict[str, Any]]]:
        season_response = await self.mlb_api.get_player_stats(
            mlb_player_id=player_mlb_id,
            stats="season",
            group=stat_group,
            season=season,
            game_type=game_type,
        )
        if season_response is None:
            return None, {}

        advanced_response = await self.mlb_api.get_player_stats(
            mlb_player_id=player_mlb_id,
            stats="seasonAdvanced",
            group=stat_group,
            season=season,
            game_type=game_type,
        )
        return season_response, _index_splits_by_team(advanced_response)

    async def _build_group_records(
        self,
        player: Player,
        season: int,
        game_type: str,
        stat_group: str,
        season_response: dict[str, Any],
        advanced_splits_by_team: dict[int | None, dict[str, Any]],
    ) -> list[PlayerStatsGroupRecord]:
        if player.id is None:
            return []

        group_records: list[PlayerStatsGroupRecord] = []
        for season_split in iter_response_splits(season_response):
            team_id = await self._resolve_internal_team_id(player, season_split)
            if team_id is None:
                continue
            team_mlb_id = resolve_team_mlb_id(season_split)
            advanced_split = advanced_splits_by_team.get(team_mlb_id)
            merged_metrics = normalize_aggregate_metrics(stat_group, season_split.get("stat", {}))
            if advanced_split is not None:
                merged_metrics = merge_metrics(
                    merged_metrics,
                    normalize_aggregate_metrics(stat_group, advanced_split.get("stat", {})),
                )
            group_records.append(
                build_group_record(
                    player_id=player.id,
                    team_id=team_id,
                    season=season,
                    game_type=game_type,
                    stat_group=stat_group,
                    metrics=merged_metrics,
                    raw_payload={"season": season_split, "seasonAdvanced": advanced_split},
                )
            )
        return group_records

    async def _ingest_one_group(
        self,
        player: Player,
        season: int,
        game_type: str,
        stat_group: str,
        force_refresh: bool,
    ) -> int:
        if player.id is None:
            return 0
        existing_records = await self.player_stats_repository.list_group_records(
            player_id=player.id,
            game_type=game_type,
            stat_group=stat_group,
            season=season,
        )
        if not _should_refresh_existing_records(existing_records, season, force_refresh):
            return 0

        season_response, advanced_splits_by_team = await self._fetch_group_payloads(
            player_mlb_id=player.mlb_id,
            season=season,
            game_type=game_type,
            stat_group=stat_group,
        )
        if season_response is None:
            return 0

        group_records = await self._build_group_records(
            player=player,
            season=season,
            game_type=game_type,
            stat_group=stat_group,
            season_response=season_response,
            advanced_splits_by_team=advanced_splits_by_team,
        )
        if not group_records:
            return 0
        persisted_records = await self.player_stats_repository.replace_group_records(
            player_id=player.id,
            season=season,
            game_type=game_type,
            stat_group=stat_group,
            records=group_records,
        )
        return len(persisted_records)


class IngestPlayerStatsHistoryUseCase(_PlayerStatsIngestionBase):
    """Persist player game logs and stat splits from StatsAPI."""

    async def execute(
        self,
        season: int,
        group: str = "all",
        game_type: str | None = None,
        player_id: int | None = None,
        team_id: int | None = None,
        days_back: int | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        _validate_season(season)
        normalized_game_type = normalize_game_type(game_type)
        target_groups = resolve_requested_groups(group)
        players = await self._resolve_target_players(player_id=player_id, team_id=team_id)
        history_records_replaced = 0
        history_contexts_skipped = 0

        for player in players:
            player_updated = False
            for current_group in target_groups:
                replaced = await self._ingest_group_history(
                    player=player,
                    season=season,
                    game_type=normalized_game_type,
                    stat_group=current_group,
                    days_back=days_back,
                    force_refresh=force_refresh,
                )
                history_records_replaced += replaced
                if replaced > 0:
                    player_updated = True
                elif not force_refresh and season < datetime.now().year:
                    history_contexts_skipped += len(("gameLog", "statSplits"))
            if player_updated and player.id is not None:
                await self._clear_player_stats_cache(player.id)

        return {
            "operation": "player_stats_history_ingestion",
            "players_processed": len(players),
            "history_records_replaced": history_records_replaced,
            "history_contexts_skipped": history_contexts_skipped,
            "season": season,
            "group": group,
            "game_type": normalized_game_type,
            "days_back": days_back,
        }

    async def _ingest_group_history(
        self,
        player: Player,
        season: int,
        game_type: str,
        stat_group: str,
        days_back: int | None,
        force_refresh: bool,
    ) -> int:
        if player.id is None:
            return 0
        total_replaced = 0
        for stat_type in ("gameLog", "statSplits"):
            existing_records = await self.player_stats_repository.list_history_records(
                player_id=player.id,
                stat_type=stat_type,
                game_type=game_type,
                stat_group=stat_group,
                season=season,
            )
            if not _should_refresh_existing_records(existing_records, season, force_refresh):
                continue
            stats_response = await self.mlb_api.get_player_stats(
                mlb_player_id=player.mlb_id,
                stats=stat_type,
                group=stat_group,
                season=season,
                game_type=game_type,
                days_back=days_back,
            )
            records = await self._build_history_records(
                player=player,
                season=season,
                game_type=game_type,
                stat_group=stat_group,
                stat_type=stat_type,
                stats_response=stats_response,
            )
            persisted_records = await self.player_stats_repository.replace_history_records(
                player_id=player.id,
                season=season,
                game_type=game_type,
                stat_group=stat_group,
                stat_type=stat_type,
                records=records,
            )
            total_replaced += len(persisted_records)
        return total_replaced

    async def _build_history_records(
        self,
        player: Player,
        season: int,
        game_type: str,
        stat_group: str,
        stat_type: str,
        stats_response: dict[str, Any] | None,
    ) -> list[PlayerStatsHistoryRecord]:
        if player.id is None or stats_response is None:
            return []
        records: list[PlayerStatsHistoryRecord] = []
        for index, split_payload in enumerate(iter_response_splits(stats_response)):
            team_id = await self._resolve_internal_team_id(player, split_payload)
            records.append(
                build_history_record(
                    player_id=player.id,
                    team_id=team_id,
                    season=season,
                    game_type=game_type,
                    stat_group=stat_group,
                    stat_type=stat_type,
                    split_payload=split_payload,
                    index=index,
                )
            )
        return records
