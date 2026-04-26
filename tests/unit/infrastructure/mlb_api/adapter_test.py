from datetime import date
from unittest.mock import AsyncMock

import httpx
import pytest

from infrastructure.mlb_api.adapter import MLBApiAdapter, MLBApiException, _safe_float


class TestMLBApiAdapter:
    def test_safe_float_handles_invalid_values(self):
        # Given / When / Then
        assert _safe_float(None) == 0.0
        assert _safe_float("") == 0.0
        assert _safe_float("abc") == 0.0
        assert _safe_float("1.25") == 1.25

    def test_extract_player_position_uses_primary_position_when_position_is_empty(self):
        # Given
        adapter = MLBApiAdapter()
        player_data = {
            "position": "   ",
            "primaryPosition": {"abbreviation": "P", "code": "1", "name": "Pitcher"},
        }

        # When
        position = adapter._extract_player_position(player_data)

        # Then
        assert position == "P"

    def test_extract_player_position_uses_position_name_when_abbreviation_and_code_are_blank(self):
        # Given
        adapter = MLBApiAdapter()
        player_data = {
            "position": {"abbreviation": " ", "code": "", "name": "Designated Hitter"},
            "primaryPosition": {"abbreviation": "DH"},
        }

        # When
        position = adapter._extract_player_position(player_data)

        # Then
        assert position == "Designated Hitter"

    def test_transform_game_data_normalizes_completed_and_winner(self):
        # Given
        adapter = MLBApiAdapter()
        game_data = {
            "gamePk": 100,
            "gameDate": "2026-04-20T19:10:00Z",
            "scheduledInnings": 9,
            "status": {"detailedState": "Final", "codedGameState": "F"},
            "teams": {
                "home": {"team": {"id": 1}, "score": 5},
                "away": {"team": {"id": 2}, "score": 3},
            },
        }

        # When
        dto = adapter._transform_game_data(game_data)

        # Then
        assert dto.id == 100
        assert dto.status == "completed"
        assert dto.winning_team_id == 1

    def test_transform_team_stats_applies_defaults_and_derived_metrics(self):
        # Given
        adapter = MLBApiAdapter()
        stats_data = {
            "stats": [
                {
                    "group": {"displayName": "hitting"},
                    "splits": [{"team": {"id": 10}, "stat": {"runs": 10, "avg": ".300"}}],
                },
                {
                    "group": {"displayName": "pitching"},
                    "splits": [{"team": {"id": 10}, "stat": {"runs": 5, "era": "2.50"}}],
                },
            ]
        }

        # When
        result = adapter._transform_team_stats_data(stats_data, mlb_team_id=10, season=2026)

        # Then
        assert result["team_id"] == 10
        assert result["season"] == 2026
        assert result["runs_scored"] == 10
        assert result["runs_allowed"] == 5
        assert result["run_differential"] == 5
        assert result["pythagorean_expectation"] > 0

    def test_transform_fielding_stats_calculates_derived_values(self):
        # Given
        adapter = MLBApiAdapter()
        stats_data = {
            "stats": [
                {
                    "group": {"displayName": "fielding"},
                    "splits": [
                        {
                            "team": {"id": 20},
                            "stat": {
                                "gamesPlayed": 2,
                                "chances": 10,
                                "putOuts": 6,
                                "assists": 2,
                                "innings": "18.0",
                            },
                        }
                    ],
                }
            ]
        }

        # When
        result = adapter._transform_fielding_stats_data(stats_data, mlb_team_id=20, season=2026)

        # Then
        assert result["fielding_percentage"] == 0.8
        assert result["range_factor_per_game"] == 4
        assert result["range_factor_per_nine"] == 4

    @pytest.mark.asyncio
    async def test_get_players_by_sport_passes_team_id_query_parameter(self):
        # Given
        adapter = MLBApiAdapter()
        adapter._make_request = AsyncMock(return_value={"people": []})

        # When
        players = await adapter.get_players_by_sport(sport_id=1, season=2025, team_mlb_id=133)

        # Then
        assert players == []
        adapter._make_request.assert_called_once_with(
            f"/{adapter.api_version}/sports/1/players",
            {"season": 2025, "teamId": 133},
        )

    @pytest.mark.asyncio
    async def test_get_team_by_id_returns_none_on_api_error(self):
        # Given
        adapter = MLBApiAdapter()
        adapter._make_request = AsyncMock(side_effect=MLBApiException("404"))

        # When
        result = await adapter.get_team_by_id(999)

        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_get_games_by_date_flattens_schedule(self):
        # Given
        adapter = MLBApiAdapter()
        adapter._make_request = AsyncMock(
            return_value={
                "dates": [
                    {"games": [{"gamePk": 1, "teams": {"home": {"team": {"id": 1}}, "away": {"team": {"id": 2}}}}]},
                    {"games": [{"gamePk": 2, "teams": {"home": {"team": {"id": 3}}, "away": {"team": {"id": 4}}}}]},
                ]
            }
        )

        # When
        result = await adapter.get_games_by_date(date(2026, 4, 1))

        # Then
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_team_stats_adds_team_filter(self):
        # Given
        adapter = MLBApiAdapter()
        adapter._make_request = AsyncMock(return_value={"stats": []})

        # When
        result = await adapter.get_team_stats(season=2026, group="hitting", mlb_team_id=123)

        # Then
        assert result == {"stats": []}
        endpoint, params = adapter._make_request.call_args.args
        assert endpoint == f"/{adapter.api_version}/teams/stats"
        assert params["teamId"] == 123

    @pytest.mark.asyncio
    async def test_get_player_stats_returns_none_on_error(self):
        # Given
        adapter = MLBApiAdapter()
        adapter._make_request = AsyncMock(side_effect=MLBApiException("boom"))

        # When
        result = await adapter.get_player_stats(1, "season", "hitting", season=2026)

        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_search_players_returns_empty_on_error(self):
        # Given
        adapter = MLBApiAdapter()
        adapter._make_request = AsyncMock(side_effect=MLBApiException("boom"))

        # When
        players = await adapter.search_players("judge")

        # Then
        assert players == []


def test_parse_game_date_and_status_fallbacks():
    # Given
    adapter = MLBApiAdapter()

    # When
    invalid_date = adapter._parse_game_date("not-a-date")
    cancelled = adapter._normalize_game_status(detailed_state="cancelled")
    unknown = adapter._normalize_game_status(detailed_state="mystery")

    # Then
    assert invalid_date is None
    assert cancelled == "cancelled"
    assert unknown == "scheduled"


@pytest.mark.asyncio
async def test_get_players_by_team_and_get_player_by_id_error_paths():
    # Given
    adapter = MLBApiAdapter()
    adapter._make_request = AsyncMock(side_effect=MLBApiException("boom"))

    # When
    roster = await adapter.get_players_by_team(1)
    player = await adapter.get_player_by_id(10)

    # Then
    assert roster == []
    assert player is None


@pytest.mark.asyncio
async def test_get_teams_and_team_stats_and_player_stats_success_paths():
    # Given
    adapter = MLBApiAdapter()
    adapter._make_request = AsyncMock(
        side_effect=[
            {"teams": [{"id": 1, "name": "A"}]},
            {"stats": [{"dummy": 1}]},
            {"stats": []},
        ]
    )

    # When
    teams = await adapter.get_teams()
    team_stats = await adapter.get_team_stats(2026, "hitting", mlb_team_id=1)
    player_stats = await adapter.get_player_stats(10, "season", "hitting", season=2026)

    # Then
    assert len(teams) == 1
    assert team_stats is not None
    assert player_stats is not None


@pytest.mark.asyncio
async def test_make_request_wraps_http_and_request_errors(monkeypatch):
    # Given
    adapter = MLBApiAdapter()
    adapter.max_retries = 0

    class _ErrorResponse:
        status_code = 500

    class _FakeClientHTTP:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            raise httpx.HTTPStatusError("http", request=None, response=_ErrorResponse())

    monkeypatch.setattr("infrastructure.mlb_api.adapter.httpx.AsyncClient", lambda timeout: _FakeClientHTTP())

    # When / Then
    with pytest.raises(MLBApiException, match="HTTP error"):
        await adapter._make_request("/x")

    class _FakeClientReq:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            raise httpx.RequestError("conn", request=None)

    monkeypatch.setattr("infrastructure.mlb_api.adapter.httpx.AsyncClient", lambda timeout: _FakeClientReq())

    with pytest.raises(MLBApiException, match="Connection error"):
        await adapter._make_request("/x")
