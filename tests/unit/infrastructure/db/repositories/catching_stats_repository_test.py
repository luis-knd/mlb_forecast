from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.catching_stats import CatchingStats
from infrastructure.db.repositories.catching_stats_repository import CatchingStatsRepository


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repository(session, monkeypatch):
    repo = CatchingStatsRepository(session)
    monkeypatch.setattr(CatchingStatsRepository, "_model_to_entity", staticmethod(lambda model: model))
    return repo


@pytest.fixture
def entity():
    return CatchingStats.create(team_id=1, season=2026, passed_balls=1)


@pytest.mark.asyncio
async def test_get_list_and_invalid_top_stat(repository, session):
    # Given
    fake = CatchingStats.create(team_id=1, season=2026)
    q = session.query.return_value.options.return_value
    q.filter.return_value.first.return_value = fake
    q.filter.return_value.order_by.return_value.all.return_value = [fake]
    q.filter.return_value.all.return_value = [fake]

    # When
    by_id = await repository.get_by_id(1)
    by_team = await repository.get_by_team_and_season(1, 2026)
    by_team_list = await repository.list_by_team(1)
    by_season = await repository.list_by_season(2026)
    invalid = await repository.list_top_teams_by_stat(2026, "invalid")

    # Then
    assert by_id is fake
    assert by_team is fake
    assert len(by_team_list) == 1
    assert len(by_season) == 1
    assert invalid == []


@pytest.mark.asyncio
async def test_save_update_and_delete(repository, session, entity, monkeypatch):
    # Given
    existing = MagicMock(id=6)
    session.query.return_value.filter.return_value.first.side_effect = [existing, existing, None]
    repository.get_by_id = AsyncMock(return_value=entity)
    delete_mock = MagicMock(return_value=True)
    monkeypatch.setattr("infrastructure.db.repositories.catching_stats_repository.delete_model_by_id", delete_mock)

    # When
    saved = await repository.save(entity)
    updated = await repository.update_stats(6, {"passed_balls": 3, "unknown": 1})
    deleted = await repository.delete(6)

    # Then
    assert saved is entity
    assert updated is entity
    assert existing.passed_balls == 3
    assert deleted is True
