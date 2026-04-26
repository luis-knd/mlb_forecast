from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.team_stats import TeamStats
from infrastructure.db.repositories.team_stats_repository import TeamStatsRepository


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repository(session):
    repo = TeamStatsRepository(session)
    repo.mapper = MagicMock()
    repo.mapper.to_entity.return_value = TeamStats.create(team_id=1, season=2026)
    repo.mapper.update_hitting_model.return_value = SimpleNamespace(id=1, created_at=None, updated_at=None)
    repo.mapper.update_pitching_model.return_value = SimpleNamespace(id=2, created_at=None, updated_at=None)
    repo.mapper.update_fielding_model.return_value = SimpleNamespace(id=3, created_at=None, updated_at=None)
    return repo


@pytest.mark.asyncio
async def test_get_by_id_and_team_season(repository, session):
    # Given
    hitting = SimpleNamespace(id=1, team_id=1, season=2026)
    pitching = SimpleNamespace(team_id=1, season=2026)
    fielding = SimpleNamespace(team_id=1, season=2026)
    q = session.query.return_value
    q.options.return_value.filter.return_value.first.return_value = hitting
    q.filter.return_value.first.side_effect = [pitching, fielding]

    # When
    result = await repository.get_by_id(1)

    # Then
    assert result is not None
    repository.mapper.to_entity.assert_called_once_with(hitting, pitching, fielding)


@pytest.mark.asyncio
async def test_list_and_top_methods(repository, monkeypatch):
    # Given
    repository.get_by_team_and_season = AsyncMock(return_value={"ok": True})
    repository.session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        (2026,),
        (2025,),
    ]
    repository.session.query.return_value.filter.return_value.all.return_value = [(1,), (2,)]

    # When
    by_team = await repository.list_by_team(1)
    by_season = await repository.list_by_season(2026)
    invalid = await repository.list_top_teams_by_stat(2026, "nope")

    # Then
    assert len(by_team) == 2
    assert len(by_season) == 2
    assert invalid == []


@pytest.mark.asyncio
async def test_save_update_delete_and_update_stats_paths(repository, session):
    # Given
    team_stats = TeamStats.create(team_id=1, season=2026)
    repository.get_by_team_and_season = AsyncMock(return_value={"team_id": 1, "season": 2026})

    # For update_stats and delete path order
    session.query.return_value.filter.return_value.first.side_effect = [
        None,
        None,
        None,
        SimpleNamespace(team_id=1, season=2026),  # update hitting found
        SimpleNamespace(team_id=1, season=2026),  # delete hitting found
        None,
        None,
    ]

    # When
    saved = await repository.save(team_stats)
    updated = await repository.update_stats(10, {"wins": 90})
    deleted = await repository.delete(10)
    not_deleted = await repository.delete(999)

    # Then
    assert saved.team_id == 1
    assert updated == {"team_id": 1, "season": 2026}
    assert deleted is True
    assert not_deleted is False
