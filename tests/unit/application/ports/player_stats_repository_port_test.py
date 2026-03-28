import pytest

from application.ports.player_stats_repository import PlayerStatsRepositoryPort
from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord


class _DummyRepository:
    pass


@pytest.mark.asyncio
async def test_player_stats_repository_port_upsert_group_record_executes_abstract_body():
    # Given
    record = PlayerStatsGroupRecord.create(1, 2, 2025, "R", "hitting", {})

    # When
    result = await PlayerStatsRepositoryPort.upsert_group_record(_DummyRepository(), record)

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_player_stats_repository_port_replace_group_records_executes_abstract_body():
    # Given / When
    result = await PlayerStatsRepositoryPort.replace_group_records(_DummyRepository(), 1, 2025, "R", "hitting", [])

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_player_stats_repository_port_list_group_records_executes_abstract_body():
    # Given / When
    result = await PlayerStatsRepositoryPort.list_group_records(_DummyRepository(), 1)

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_player_stats_repository_port_history_methods_execute_abstract_body():
    # Given
    record = PlayerStatsHistoryRecord.create(1, 2, 2025, "R", "hitting", "gameLog", "1", {})

    # When
    replace_result = await PlayerStatsRepositoryPort.replace_history_records(
        _DummyRepository(),
        1,
        2025,
        "R",
        "hitting",
        "gameLog",
        [record],
    )
    list_result = await PlayerStatsRepositoryPort.list_history_records(_DummyRepository(), 1, "gameLog")

    # Then
    assert replace_result is None
    assert list_result is None
