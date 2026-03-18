from unittest.mock import patch

from starlette.status import HTTP_201_CREATED


class TestGameIngestionRoute:
    @patch("application.use_cases.game_use_cases.IngestGamesUseCase.execute")
    def test_ingest_games_created_envelope(self, mock_execute, integration_client):
        mock_execute.return_value = []
        response = integration_client.post("/api/v1/data/ingest/games?days_back=3")

        assert response.status_code == HTTP_201_CREATED
        body = response.json()
        assert body["status"] == "success"
        assert body["code"] == HTTP_201_CREATED
        assert "ingestion_summary" in body["data"]
        assert body["data"]["ingestion_summary"]["operation"] == "game_ingestion"
