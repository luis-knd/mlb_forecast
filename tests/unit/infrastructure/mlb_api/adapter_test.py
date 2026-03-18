from unittest.mock import AsyncMock

import pytest

from infrastructure.mlb_api.adapter import MLBApiAdapter


class TestMLBApiAdapter:
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
