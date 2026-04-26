from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.hitting_stats import HittingStats
from infrastructure.db.repositories.hitting_stats_repository import HittingStatsRepository


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repository(session, monkeypatch):
    repo = HittingStatsRepository(session)
    monkeypatch.setattr(HittingStatsRepository, "_model_to_entity", staticmethod(lambda model: model))
    return repo


@pytest.fixture
def entity():
    return HittingStats.create(team_id=1, season=2026, games_played=10, hits=20)


@pytest.mark.asyncio
async def test_query_methods_and_invalid_top_stat(repository, session):
    # Given
    fake = HittingStats.create(team_id=1, season=2026)
    q = session.query.return_value.options.return_value
    q.filter.return_value.first.return_value = fake
    q.filter.return_value.order_by.return_value.all.return_value = [fake]
    q.filter.return_value.all.return_value = [fake]

    # When
    by_id = await repository.get_by_id(1)
    by_team = await repository.get_by_team_and_season(1, 2026)
    list_team = await repository.list_by_team(1)
    list_season = await repository.list_by_season(2026)
    invalid = await repository.list_top_teams_by_stat(2026, "not_exists")

    # Then
    assert by_id is fake
    assert by_team is fake
    assert len(list_team) == 1
    assert len(list_season) == 1
    assert invalid == []


@pytest.mark.asyncio
async def test_save_update_stats_and_delete(repository, session, entity, monkeypatch):
    # Given
    existing = MagicMock(id=7)
    session.query.return_value.filter.return_value.first.side_effect = [existing, existing, None]
    repository.get_by_id = AsyncMock(return_value=entity)
    delete_mock = MagicMock(return_value=True)
    monkeypatch.setattr("infrastructure.db.repositories.hitting_stats_repository.delete_model_by_id", delete_mock)

    # When
    saved = await repository.save(entity)
    updated = await repository.update_stats(7, {"hits": 99, "unknown": 1})
    deleted = await repository.delete(7)

    # Then
    assert saved is entity
    assert updated is entity
    assert existing.hits == 99
    assert deleted is True
    delete_mock.assert_called_once()
