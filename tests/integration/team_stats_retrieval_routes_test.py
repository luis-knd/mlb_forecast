from unittest.mock import ANY

import pytest

from src.infrastructure.db.models import (
    CatchingStatsModel,
    FieldingStatsModel,
    HittingStatsModel,
    PitchingStatsModel,
    TeamModel,
)


@pytest.fixture
def team_with_full_stats(test_db_session):
    team = TeamModel(
        id=62,
        mlb_id=1462,
        name="Test Team",
        abbreviation="TST",
        city="Test City",
        division="Test Division",
        league="Test League",
        venue_name="Test Venue",
    )
    season = 2025

    test_db_session.add(team)
    test_db_session.flush()

    hitting = HittingStatsModel(team_id=team.id, season=season, hits=150, games_played=162)
    pitching = PitchingStatsModel(team_id=team.id, season=season, wins=90, games_played=162)
    fielding = FieldingStatsModel(team_id=team.id, season=season, total_chances=5000)
    catching = CatchingStatsModel(team_id=team.id, season=season, caught_stealing=30)

    test_db_session.add_all([hitting, pitching, fielding, catching])
    test_db_session.commit()

    return {"team": team, "season": season}


def test_get_team_stats_returns_all_categories_by_default(
    integration_client,
    team_with_full_stats,
    mock_cache_for_integration,
):
    team_id = team_with_full_stats["team"].id
    season = team_with_full_stats["season"]

    mock_cache_for_integration.reset_mock()

    response = integration_client.get(f"/api/v1/teams/{team_id}/stats/{season}")

    body = response.json()
    assert response.status_code == 200
    assert body["data"]["hitting"]["hits"] == 150
    assert body["data"]["pitching"]["wins"] == 90
    assert body["data"]["fielding"]["total_chances"] == 5000
    assert body["data"]["catching"]["caught_stealing"] == 30
    mock_cache_for_integration.get.assert_awaited_once_with(f"team_stats:{team_id}:{season}")
    mock_cache_for_integration.set.assert_awaited_once_with(
        f"team_stats:{team_id}:{season}",
        ANY,
        ttl=3600,
    )


@pytest.mark.parametrize(
    "category,expected_present_key",
    [
        ("hitting", "hits"),
        ("pitching", "wins"),
        ("fielding", "total_chances"),
        ("catching", "caught_stealing"),
    ],
)
def test_get_team_stats_filters_single_category(
    integration_client,
    team_with_full_stats,
    mock_cache_for_integration,
    category,
    expected_present_key,
):
    team_id = team_with_full_stats["team"].id
    season = team_with_full_stats["season"]

    mock_cache_for_integration.reset_mock()

    response = integration_client.get(f"/api/v1/teams/{team_id}/stats/{season}?category={category}")

    body = response.json()
    assert response.status_code == 200
    assert body["data"][category][expected_present_key] is not None

    for other_category in {"hitting", "pitching", "fielding", "catching"} - {category}:
        assert body["data"][other_category] is None

    cache_key = f"team_stats:{team_id}:{season}:{category}"
    mock_cache_for_integration.get.assert_awaited_once_with(cache_key)
    mock_cache_for_integration.set.assert_awaited_once_with(cache_key, ANY, ttl=3600)


def test_get_team_stats_accepts_all_alias(integration_client, team_with_full_stats):
    team_id = team_with_full_stats["team"].id
    season = team_with_full_stats["season"]

    response = integration_client.get(f"/api/v1/teams/{team_id}/stats/{season}?category=all")

    body = response.json()
    assert response.status_code == 200
    assert body["data"]["hitting"]["hits"] == 150
    assert body["data"]["pitching"]["wins"] == 90
    assert body["data"]["fielding"]["total_chances"] == 5000
    assert body["data"]["catching"]["caught_stealing"] == 30


def test_get_team_stats_handles_case_insensitive_category(
    integration_client,
    team_with_full_stats,
):
    team_id = team_with_full_stats["team"].id
    season = team_with_full_stats["season"]

    response = integration_client.get(f"/api/v1/teams/{team_id}/stats/{season}?category=HITTING")

    body = response.json()
    assert response.status_code == 200
    assert body["data"]["hitting"]["hits"] == 150
    assert body["data"]["pitching"] is None
    assert body["data"]["fielding"] is None
    assert body["data"]["catching"] is None


def test_get_team_stats_rejects_invalid_category(integration_client, team_with_full_stats):
    team_id = team_with_full_stats["team"].id
    season = team_with_full_stats["season"]

    response = integration_client.get(f"/api/v1/teams/{team_id}/stats/{season}?category=defense")

    body = response.json()
    assert response.status_code == 422
    assert any("category must be one of" in message for message in body["errors"])


def test_get_team_stats_rejects_non_numeric_season(integration_client):
    response = integration_client.get("/api/v1/teams/62/stats/abcd")

    body = response.json()
    assert response.status_code == 422
    assert any("season must be an integer year" in message for message in body["errors"])
