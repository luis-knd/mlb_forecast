from datetime import datetime
from unittest.mock import patch

import pytest
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

from src.domain.entities.player import Player
from src.infrastructure.db.models import PlayerModel, TeamModel


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

    def test_get_player_by_mlb_id(self, integration_client, populated_players_db):
        # When
        response = integration_client.get("/api/v1/players/660271")

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["status"] == "success"
        assert body["data"]["mlb_id"] == 660271
        assert body["data"]["full_name"] == "Shohei Ohtani"

    def test_get_player_not_found(self, integration_client, populated_players_db):
        # When
        response = integration_client.get("/api/v1/players/999999")

        # Then
        assert response.status_code == HTTP_404_NOT_FOUND
        body = response.json()
        assert body["status"] == "error"
        assert body["message"] == "Resource not found"

    @patch("src.application.use_cases.player_use_cases.GetPlayerStatsUseCase.execute")
    def test_get_player_stats(self, mock_execute, integration_client, populated_players_db):
        # Given
        mock_execute.return_value = {
            "player_id": 660271,
            "stats": "season",
            "group": "hitting",
            "season": 2025,
            "stats_data": [{"type": {"displayName": "season"}, "group": {"displayName": "hitting"}}],
        }

        # When
        response = integration_client.get("/api/v1/players/660271/stats?stats=season&group=hitting&season=2025")

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["status"] == "success"
        assert body["data"]["player_id"] == 660271
        assert body["data"]["stats"] == "season"

    @patch("src.application.use_cases.player_use_cases.IngestPlayersBySourceUseCase.execute")
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

    @patch("src.application.use_cases.player_use_cases.IngestPlayersBySourceUseCase.execute")
    def test_ingest_players_sport_source_forwards_team_filter(self, mock_execute, integration_client):
        # Given
        mock_execute.return_value = []

        # When
        response = integration_client.post(
            "/api/v1/data/ingest/players?source=sport_players&teamId=133&season=2025&sportId=1"
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
