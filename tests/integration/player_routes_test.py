from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from application.dto.mlb_api_response import MLBPlayerDTO
from domain.entities.player import Player
from infrastructure.db.models import PlayerModel, TeamModel


@pytest.fixture
def populated_players_db(test_db_session):
    team = TeamModel(
        mlb_id=119,
        name="Los Angeles Dodgers",
        abbreviation="LAD",
        city="Los Angeles",
        division="National League West",
        league="National League",
        venue_name="Dodger Stadium",
    )
    test_db_session.add(team)
    test_db_session.flush()

    player = PlayerModel(
        mlb_id=660271,
        first_name="Shohei",
        last_name="Ohtani",
        position="DH",
        bats="L",
        throws="R",
        birth_date=datetime(1994, 7, 5),
        active=True,
        current_team_id=team.id,
    )
    test_db_session.add(player)
    test_db_session.commit()

    return {"team": team, "player": player}


class TestPlayerRoutesIntegration:
    def test_list_players(self, integration_client, populated_players_db):
        # When
        response = integration_client.get("/api/v1/players")

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["status"] == "success"
        assert len(body["data"]) == 1
        assert body["data"][0]["mlb_id"] == 660271
        assert "current_team" not in body["data"][0]

    def test_list_players_hydrates_current_team_when_requested(self, integration_client, populated_players_db):
        # When
        response = integration_client.get("/api/v1/players?include=current_team")

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["data"][0]["current_team"]["mlb_id"] == 119
        assert body["data"][0]["current_team"]["name"] == "Los Angeles Dodgers"

    def test_get_player_by_mlb_id(self, integration_client, populated_players_db):
        # When
        response = integration_client.get("/api/v1/players/660271")

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["status"] == "success"
        assert body["data"]["mlb_id"] == 660271
        assert body["data"]["full_name"] == "Shohei Ohtani"
        assert "current_team" not in body["data"]

    def test_get_player_by_mlb_id_hydrates_current_team_when_nested_include_is_requested(
        self, integration_client, populated_players_db
    ):
        # When
        response = integration_client.get("/api/v1/players/660271?include=current_team.venue_name")

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["data"]["current_team"]["venue_name"] == "Dodger Stadium"

    def test_list_players_returns_bad_request_for_unknown_include(self, integration_client, populated_players_db):
        # When
        response = integration_client.get("/api/v1/players?include=unknown")

        # Then
        assert response.status_code == HTTP_400_BAD_REQUEST
        body = response.json()
        assert body["status"] == "error"
        assert "Invalid include path 'unknown'" in body["errors"][0]

    def test_get_player_not_found(self, integration_client, populated_players_db):
        # When
        response = integration_client.get("/api/v1/players/999999")

        # Then
        assert response.status_code == HTTP_404_NOT_FOUND
        body = response.json()
        assert body["status"] == "error"
        assert body["message"] == "Resource not found"

    @patch("application.use_cases.player_use_cases.GetPlayerStatsUseCase.execute")
    def test_get_player_stats(self, mock_execute, integration_client, populated_players_db):
        # Given
        internal_player_id = populated_players_db["player"].id
        mock_execute.return_value = {
            "player_id": 660271,
            "stats": "season",
            "group": "hitting",
            "season": 2025,
            "stats_data": [{"type": {"displayName": "season"}, "group": {"displayName": "hitting"}}],
        }

        # When
        response = integration_client.get(
            f"/api/v1/players/{internal_player_id}/stats?stats=season&group=hitting&season=2025"
        )

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["status"] == "success"
        assert body["data"]["player_id"] == internal_player_id
        assert body["data"]["stats"] == "season"
        mock_execute.assert_called_once_with(
            mlb_player_id=660271,
            stats="season",
            group="hitting",
            season=2025,
            game_type=None,
            days_back=None,
        )

    @patch("application.use_cases.player_use_cases.GetPlayerStatsUseCase.execute")
    def test_get_player_stats_group_all(self, mock_execute, integration_client, populated_players_db):
        # Given
        internal_player_id = populated_players_db["player"].id
        mock_execute.return_value = {
            "player_id": 660271,
            "stats": "season",
            "group": "all",
            "season": 2025,
            "stats_data": [
                {"group": {"displayName": "hitting"}},
                {"group": {"displayName": "pitching"}},
            ],
        }

        # When
        response = integration_client.get(
            f"/api/v1/players/{internal_player_id}/stats?stats=season&group=all&season=2025"
        )

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["status"] == "success"
        assert body["data"]["group"] == "all"
        assert body["data"]["player_id"] == internal_player_id

    def test_get_player_stats_not_found_for_unknown_internal_player_id(self, integration_client, populated_players_db):
        # When
        response = integration_client.get("/api/v1/players/999999/stats?stats=season&group=hitting&season=2025")

        # Then
        assert response.status_code == HTTP_404_NOT_FOUND
        body = response.json()
        assert body["status"] == "error"
        assert body["message"] == "Resource not found"

    @patch("application.use_cases.player_use_cases.IngestPlayersBySourceUseCase.execute")
    def test_ingest_players(self, mock_execute, integration_client):
        # Given
        mock_execute.return_value = [
            Player.create(
                mlb_id=660271,
                first_name="Shohei",
                last_name="Ohtani",
                position="DH",
                bats="L",
                throws="R",
                active=True,
            )
        ]

        # When
        response = integration_client.post("/api/v1/data/ingest/players?source=search&q=ohtani")

        # Then
        assert response.status_code == HTTP_201_CREATED
        body = response.json()
        assert body["status"] == "success"
        assert body["data"]["ingestion_summary"]["operation"] == "player_ingestion"
        assert len(body["data"]["sample_players"]) == 1

    @patch("application.use_cases.player_use_cases.IngestPlayersBySourceUseCase.execute")
    def test_ingest_players_sport_source_forwards_internal_team_filter(
        self,
        mock_execute,
        integration_client,
        populated_test_db,
    ):
        # Given
        mock_execute.return_value = []
        athletics = next(team for team in populated_test_db if team.mlb_id == 133)

        # When
        response = integration_client.post(
            f"/api/v1/data/ingest/players?source=sport_players&teamId={athletics.id}&season=2025&sportId=1"
        )

        # Then
        assert response.status_code == HTTP_201_CREATED
        mock_execute.assert_called_once_with(
            source="sport_players",
            season=2025,
            team_mlb_id=133,
            roster_type="active",
            sport_id=1,
            query=None,
        )

    @patch("infrastructure.mlb_api.adapter.MLBApiAdapter.get_players_by_team", new_callable=AsyncMock)
    def test_ingest_players_team_roster_preserves_existing_profile_fields_when_payload_is_partial(
        self,
        mock_get_players_by_team,
        integration_client,
        populated_players_db,
        test_db_session,
    ):
        # Given
        mock_get_players_by_team.return_value = [
            MLBPlayerDTO(
                id=660271,
                first_name="Shohei",
                last_name="Ohtani",
                position="",
                bats="",
                throws="",
                birth_date=None,
                active=True,
                current_team_id=119,
            )
        ]

        # When
        response = integration_client.post(
            f"/api/v1/data/ingest/players?source=team_roster&teamId={populated_players_db['team'].id}&season=2025"
        )

        # Then
        assert response.status_code == HTTP_201_CREATED
        persisted_player = test_db_session.query(PlayerModel).filter(PlayerModel.mlb_id == 660271).first()
        assert persisted_player is not None
        assert persisted_player.position == "DH"
        assert persisted_player.bats == "L"
        assert persisted_player.throws == "R"
        assert persisted_player.birth_date == datetime(1994, 7, 5)

    @patch("application.use_cases.player_use_cases.IngestPlayersBySourceUseCase.execute")
    def test_ingest_players_returns_not_found_for_unknown_internal_team(self, mock_execute, integration_client):
        # When
        response = integration_client.post("/api/v1/data/ingest/players?source=team_roster&teamId=999999&season=2025")

        # Then
        assert response.status_code == HTTP_404_NOT_FOUND
        body = response.json()
        assert body["status"] == "error"
        assert body["message"] == "Resource not found"
        mock_execute.assert_not_called()
