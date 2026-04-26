from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.team_stats import TeamStats
from infrastructure.db.models import FieldingStatsModel, HittingStatsModel, PitchingStatsModel
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
    responses = [
        None,
        None,
        None,
        SimpleNamespace(team_id=1, season=2026),  # update hitting found
        SimpleNamespace(team_id=1, season=2026),  # delete hitting found
        None,
        None,
        None,
        None,
    ]

    def _next_query_result():
        return responses.pop(0) if responses else None

    session.query.return_value.filter.return_value.first.side_effect = _next_query_result

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


@pytest.mark.asyncio
async def test_get_by_team_and_season_returns_none_when_all_stats_missing(repository, session):
    # Given
    session.query.return_value.filter.return_value.first.return_value = None

    # When
    result = await repository.get_by_team_and_season(1, 2026)

    # Then
    assert result is None


def test_model_to_dict_handles_none_model():
    # Given / When / Then
    assert TeamStatsRepository._model_to_dict(None) is None


@pytest.mark.asyncio
async def test_update_stats_and_delete_cover_pitching_and_fielding_branches(repository, session):
    # Given
    repository.get_by_team_and_season = AsyncMock(return_value={"ok": True})
    query_mock = MagicMock()
    filter_mock = MagicMock()
    session.query.return_value = query_mock
    query_mock.filter.return_value = filter_mock

    calls: dict[type, int] = {HittingStatsModel: 0, PitchingStatsModel: 0, FieldingStatsModel: 0}

    def _first_side_effect():
        model_class = session.query.call_args.args[0]
        calls[model_class] += 1
        # update_stats(1): miss hitting -> hit pitching
        if model_class is HittingStatsModel and calls[model_class] == 1:
            return None
        if model_class is PitchingStatsModel and calls[model_class] == 1:
            return SimpleNamespace(team_id=9, season=2026)
        # update_stats(2): miss hitting/pitching -> hit fielding
        if model_class is HittingStatsModel and calls[model_class] == 2:
            return None
        if model_class is PitchingStatsModel and calls[model_class] == 2:
            return None
        if model_class is FieldingStatsModel and calls[model_class] == 1:
            return SimpleNamespace(team_id=9, season=2026)
        # delete(88): miss hitting -> hit pitching
        if model_class is HittingStatsModel and calls[model_class] == 3:
            return None
        if model_class is PitchingStatsModel and calls[model_class] == 3:
            return SimpleNamespace(id=88)
        # delete(77): miss hitting/pitching -> hit fielding
        if model_class is HittingStatsModel and calls[model_class] == 4:
            return None
        if model_class is PitchingStatsModel and calls[model_class] == 4:
            return None
        if model_class is FieldingStatsModel and calls[model_class] == 2:
            return SimpleNamespace(id=77)
        return None

    filter_mock.first.side_effect = _first_side_effect

    # When
    updated_pitching = await repository.update_stats(1, {})
    updated_fielding = await repository.update_stats(2, {})
    deleted_pitching = await repository.delete(88)
    deleted_fielding = await repository.delete(77)

    # Then
    assert updated_pitching == {"ok": True}
    assert updated_fielding == {"ok": True}
    assert deleted_pitching is True
    assert deleted_fielding is True


@pytest.mark.asyncio
async def test_save_rolls_back_when_commit_fails(repository, session):
    # Given
    team_stats = TeamStats.create(team_id=1, season=2026)
    session.query.return_value.filter.return_value.first.return_value = None
    session.commit.side_effect = RuntimeError("commit failed")

    # When / Then
    with pytest.raises(RuntimeError, match="commit failed"):
        await repository.save(team_stats)

    session.rollback.assert_called_once()
