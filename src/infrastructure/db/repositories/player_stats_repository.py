"""
Player stats repository implementation.
This module persists aggregate player stats and supporting history tables.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from application.ports.player_stats_repository import PlayerStatsRepositoryPort
from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord
from infrastructure.db.player_stats_models import (
    PlayerCatchingStatsModel,
    PlayerFieldingStatsModel,
    PlayerGameLogModel,
    PlayerHittingStatsModel,
    PlayerPitchingStatsModel,
    PlayerRunningStatsModel,
    PlayerStatSplitModel,
)

GROUP_MODEL_MAP = {
    "hitting": PlayerHittingStatsModel,
    "pitching": PlayerPitchingStatsModel,
    "fielding": PlayerFieldingStatsModel,
    "catching": PlayerCatchingStatsModel,
    "running": PlayerRunningStatsModel,
}

HISTORY_MODEL_MAP = {
    "gameLog": PlayerGameLogModel,
    "statSplits": PlayerStatSplitModel,
}

AGGREGATE_METADATA_FIELDS = {
    "id",
    "player_id",
    "team_id",
    "season",
    "game_type",
    "source",
    "source_updated_at",
    "ingested_at",
    "raw_payload",
    "created_at",
    "updated_at",
}

HISTORY_METADATA_FIELDS = {
    "id",
    "player_id",
    "team_id",
    "season",
    "game_type",
    "stat_group",
    "external_reference",
    "history_entry_key",
    "event_date",
    "payload",
    "context_key",
    "context_value",
    "context_label",
    "source",
    "ingested_at",
    "created_at",
    "updated_at",
}


class PlayerStatsRepository(PlayerStatsRepositoryPort):
    """SQLAlchemy implementation for persisted player stats."""

    def __init__(self, session: Session):
        self.session = session

    def _commit_or_rollback(self) -> None:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    async def upsert_group_record(self, record: PlayerStatsGroupRecord) -> PlayerStatsGroupRecord:
        model_class = GROUP_MODEL_MAP[record.stat_group]
        model = (
            self.session.query(model_class)
            .filter(
                model_class.player_id == record.player_id,
                model_class.team_id == record.team_id,
                model_class.season == record.season,
                model_class.game_type == record.game_type,
            )
            .first()
        )
        if model is None:
            model = model_class(
                player_id=record.player_id,
                team_id=record.team_id,
                season=record.season,
                game_type=record.game_type,
            )
            self.session.add(model)

        self._apply_group_record(model, record)
        self._commit_or_rollback()
        self.session.refresh(model)
        return self._to_group_record(model, record.stat_group)

    async def replace_group_records(
        self,
        player_id: int,
        season: int,
        game_type: str,
        stat_group: str,
        records: list[PlayerStatsGroupRecord],
    ) -> list[PlayerStatsGroupRecord]:
        model_class = GROUP_MODEL_MAP[stat_group]
        (
            self.session.query(model_class)
            .filter(
                model_class.player_id == player_id,
                model_class.season == season,
                model_class.game_type == game_type,
            )
            .delete(synchronize_session=False)
        )

        persisted_models = []
        for record in records:
            model = model_class(
                player_id=record.player_id,
                team_id=record.team_id,
                season=record.season,
                game_type=record.game_type,
            )
            self._apply_group_record(model, record)
            self.session.add(model)
            persisted_models.append(model)

        self._commit_or_rollback()
        for model in persisted_models:
            self.session.refresh(model)
        return [self._to_group_record(model, stat_group) for model in persisted_models]

    async def list_group_records(
        self,
        player_id: int,
        game_type: str | None = None,
        stat_group: str | None = None,
        season: int | None = None,
    ) -> list[PlayerStatsGroupRecord]:
        groups = [stat_group] if stat_group else list(GROUP_MODEL_MAP.keys())
        records: list[PlayerStatsGroupRecord] = []

        for current_group in groups:
            model_class = GROUP_MODEL_MAP[current_group]
            query = self.session.query(model_class).filter(model_class.player_id == player_id)
            if game_type is not None:
                query = query.filter(model_class.game_type == game_type)
            if season is not None:
                query = query.filter(model_class.season == season)

            records.extend(
                self._to_group_record(model, current_group)
                for model in query.order_by(model_class.season.desc(), model_class.id.desc()).all()
            )

        records.sort(key=lambda current: (current.season, current.stat_group), reverse=True)
        return records

    async def replace_history_records(
        self,
        player_id: int,
        season: int,
        game_type: str,
        stat_group: str,
        stat_type: str,
        records: list[PlayerStatsHistoryRecord],
    ) -> list[PlayerStatsHistoryRecord]:
        model_class = HISTORY_MODEL_MAP[stat_type]
        (
            self.session.query(model_class)
            .filter(
                model_class.player_id == player_id,
                model_class.season == season,
                model_class.game_type == game_type,
                model_class.stat_group == stat_group,
            )
            .delete(synchronize_session=False)
        )

        persisted_models = []
        for record in records:
            model = model_class(
                player_id=record.player_id,
                team_id=record.team_id,
                season=record.season,
                game_type=record.game_type,
                stat_group=record.stat_group,
                external_reference=record.external_reference,
                history_entry_key=record.history_entry_key,
                event_date=record.event_date,
                payload=record.payload,
                context_key=record.context_key,
                context_value=record.context_value,
                context_label=record.context_label,
                source=record.source,
                ingested_at=record.ingested_at,
            )
            self.session.add(model)
            persisted_models.append(model)

        self._commit_or_rollback()
        for model in persisted_models:
            self.session.refresh(model)
        return [self._to_history_record(model, stat_type) for model in persisted_models]

    async def list_history_records(
        self,
        player_id: int,
        stat_type: str,
        game_type: str | None = None,
        stat_group: str | None = None,
        season: int | None = None,
        limit: int | None = None,
    ) -> list[PlayerStatsHistoryRecord]:
        model_class = HISTORY_MODEL_MAP[stat_type]
        query = self.session.query(model_class).filter(model_class.player_id == player_id)
        if game_type is not None:
            query = query.filter(model_class.game_type == game_type)
        if stat_group is not None:
            query = query.filter(model_class.stat_group == stat_group)
        if season is not None:
            query = query.filter(model_class.season == season)
        query = query.order_by(model_class.event_date.desc(), model_class.id.desc())
        if limit is not None:
            query = query.limit(limit)
        return [self._to_history_record(model, stat_type) for model in query.all()]

    @staticmethod
    def _apply_group_record(model: Any, record: PlayerStatsGroupRecord) -> None:
        model.source = record.source
        model.source_updated_at = record.source_updated_at
        model.ingested_at = record.ingested_at
        model.raw_payload = record.raw_payload
        for key, value in record.metrics.items():
            if hasattr(model, key):
                setattr(model, key, value)

    @staticmethod
    def _to_group_record(model: Any, stat_group: str) -> PlayerStatsGroupRecord:
        return PlayerStatsGroupRecord(
            id=model.id,
            player_id=model.player_id,
            team_id=model.team_id,
            season=model.season,
            game_type=model.game_type,
            stat_group=stat_group,
            metrics=PlayerStatsRepository._extract_metrics(model, AGGREGATE_METADATA_FIELDS),
            source=model.source,
            source_updated_at=model.source_updated_at,
            ingested_at=model.ingested_at,
            raw_payload=model.raw_payload,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_history_record(model: Any, stat_type: str) -> PlayerStatsHistoryRecord:
        return PlayerStatsHistoryRecord(
            id=model.id,
            player_id=model.player_id,
            team_id=model.team_id,
            season=model.season,
            game_type=model.game_type,
            stat_group=model.stat_group,
            stat_type=stat_type,
            external_reference=model.external_reference,
            history_entry_key=model.history_entry_key,
            event_date=model.event_date,
            payload=model.payload,
            context_key=model.context_key,
            context_value=model.context_value,
            context_label=model.context_label,
            source=model.source,
            ingested_at=model.ingested_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _extract_metrics(model: Any, metadata_fields: set[str]) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        for column in model.__table__.columns:
            if column.name in metadata_fields:
                continue
            metrics[column.name] = getattr(model, column.name)
        return metrics
