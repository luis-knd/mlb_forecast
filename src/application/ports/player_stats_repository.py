"""
Player stats repository port.
This defines how the application persists and reads player aggregate stats and history.
"""

from abc import ABC, abstractmethod

from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord


class PlayerStatsRepositoryPort(ABC):
    """Repository interface for persisted player stats."""

    @abstractmethod
    async def upsert_group_record(self, record: PlayerStatsGroupRecord) -> PlayerStatsGroupRecord:
        """Create or update one aggregate group record."""
        pass

    @abstractmethod
    async def replace_group_records(
        self,
        player_id: int,
        season: int,
        game_type: str,
        stat_group: str,
        records: list[PlayerStatsGroupRecord],
    ) -> list[PlayerStatsGroupRecord]:
        """Replace all aggregate records for one player season, game type, and stat group."""
        pass

    @abstractmethod
    async def list_group_records(
        self,
        player_id: int,
        game_type: str | None = None,
        stat_group: str | None = None,
        season: int | None = None,
    ) -> list[PlayerStatsGroupRecord]:
        """List aggregate group records using internal player filters."""
        pass

    @abstractmethod
    async def replace_history_records(
        self,
        player_id: int,
        season: int,
        game_type: str,
        stat_group: str,
        stat_type: str,
        records: list[PlayerStatsHistoryRecord],
    ) -> list[PlayerStatsHistoryRecord]:
        """Replace the stored history records for one player, context, group, and type."""
        pass

    @abstractmethod
    async def list_history_records(
        self,
        player_id: int,
        stat_type: str,
        game_type: str | None = None,
        stat_group: str | None = None,
        season: int | None = None,
        limit: int | None = None,
    ) -> list[PlayerStatsHistoryRecord]:
        """List persisted history records."""
        pass
