from unittest.mock import AsyncMock

import pytest

from tests.unit.use_cases.player_stats_test_support_test import build_player, build_team, stats_response


@pytest.fixture
def mock_player_repository() -> AsyncMock:
    repository = AsyncMock()
    repository.get_by_id.return_value = build_player()
    repository.list_by_team.return_value = [build_player()]
    return repository


@pytest.fixture
def mock_team_repository() -> AsyncMock:
    repository = AsyncMock()
    repository.get_by_mlb_id.return_value = build_team()
    return repository


@pytest.fixture
def mock_player_stats_repository() -> AsyncMock:
    repository = AsyncMock()
    repository.list_group_records.return_value = []
    repository.replace_group_records.side_effect = lambda **kwargs: kwargs["records"]
    repository.list_history_records.return_value = []
    repository.replace_history_records.side_effect = lambda **kwargs: kwargs["records"]
    return repository


@pytest.fixture
def mock_mlb_api() -> AsyncMock:
    api = AsyncMock()
    api.get_player_stats.side_effect = [
        stats_response(
            {"team": {"id": 119}, "stat": {"hits": 3, "plateAppearances": 10, "avg": 0.3}},
            {"team": {"id": 147}, "stat": {"hits": 2, "plateAppearances": 8, "avg": 0.25}},
        ),
        stats_response(
            {"team": {"id": 119}, "stat": {"ops": 0.95}},
            {"team": {"id": 147}, "stat": {"ops": 0.7}},
        ),
    ]
    return api
