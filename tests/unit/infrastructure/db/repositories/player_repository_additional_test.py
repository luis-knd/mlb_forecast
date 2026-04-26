from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.player import Player
from infrastructure.db.repositories.player_repository import PlayerRepository


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repository(session, monkeypatch):
    repo = PlayerRepository(session)
    monkeypatch.setattr(repo, "_model_to_entity", lambda model: model)
    return repo


@pytest.mark.asyncio
async def test_get_and_list_methods(repository, session):
    # Given
    model = MagicMock()
    q = session.query.return_value.options.return_value
    q.filter.return_value.first.side_effect = [model, model]
    q.filter.return_value.all.return_value = [model]

    # When
    by_id = await repository.get_by_id(1)
    by_mlb = await repository.get_by_mlb_id(2)
    by_team = await repository.list_by_team(10)
    by_position = await repository.list_by_position("P")
    active = await repository.list_active_players()

    # Then
    assert by_id is model
    assert by_mlb is model
    assert len(by_team) == 1
    assert len(by_position) == 1
    assert len(active) == 1


@pytest.mark.asyncio
async def test_list_players_search_and_mutations(repository, session):
    # Given
    model = MagicMock(id=7)
    query = session.query.return_value.options.return_value
    query.filter.return_value = query
    query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [model]
    session.query.return_value.options.return_value.filter.return_value.all.return_value = [model]
    responses = [model, model, model, None, None]

    def _next_first_result():
        return responses.pop(0) if responses else None

    session.query.return_value.filter.return_value.first.side_effect = _next_first_result

    repository.get_by_id = AsyncMock(return_value=model)

    entity = Player.create(
        mlb_id=77,
        first_name="Aaron",
        last_name="Judge",
        position="OF",
        bats="R",
        throws="R",
        birth_date=datetime(1992, 4, 26),
        active=True,
    )
    entity.id = 7

    # When
    listed = await repository.list_players(team_id=1, position="OF", name="Aaron Judge", active=True, limit=5, offset=0)
    searched = await repository.search_by_name("Judge")
    saved = await repository.save(entity)
    moved = await repository.update_team(7, 9)
    deleted = await repository.delete(7)
    deleted_missing = await repository.delete(999)

    # Then
    assert len(listed) == 1
    assert len(searched) == 1
    assert saved is model
    assert moved is model
    assert deleted is True
    assert deleted_missing is False


def test_merge_helpers_cover_blank_and_non_blank(repository):
    # Given / When / Then
    assert repository._merge_required_text_field(" ", "OF") == "OF"
    assert repository._merge_required_text_field("P", "OF") == "P"
    assert repository._merge_optional_text_field(None, "R") == "R"
    assert repository._merge_optional_text_field(" ", "R") == "R"
    assert repository._merge_optional_text_field("L", "R") == "L"
    now = datetime(2020, 1, 1)
    assert repository._merge_birth_date(None, now) == now
