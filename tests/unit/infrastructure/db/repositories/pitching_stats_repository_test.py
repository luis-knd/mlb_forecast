from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.pitching_stats import PitchingStats
from infrastructure.db.repositories.pitching_stats_repository import PitchingStatsRepository


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repository(session, monkeypatch):
    repo = PitchingStatsRepository(session)
    monkeypatch.setattr(PitchingStatsRepository, "_model_to_entity", staticmethod(lambda model: model))
    return repo


@pytest.fixture
def entity():
    return PitchingStats.create(team_id=1, season=2026, wins=5)


@pytest.mark.asyncio
async def test_list_top_teams_by_stat_and_get_methods(repository, session):
    # Given
    fake = PitchingStats.create(team_id=1, season=2026)
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
async def test_save_update_delete(repository, session, entity, monkeypatch):
    # Given
    existing = MagicMock(id=3)
    session.query.return_value.filter.return_value.first.side_effect = [existing, existing, None]
    repository.get_by_id = AsyncMock(return_value=entity)
    delete_mock = MagicMock(return_value=True)
    monkeypatch.setattr("infrastructure.db.repositories.pitching_stats_repository.delete_model_by_id", delete_mock)

    # When
    saved = await repository.save(entity)
    updated = await repository.update_stats(3, {"wins": 7, "not_valid": 1})
    deleted = await repository.delete(3)

    # Then
    assert saved is entity
    assert updated is entity
    assert existing.wins == 7
    assert deleted is True
