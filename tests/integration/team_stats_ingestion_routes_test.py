from types import SimpleNamespace
from unittest.mock import patch

import pytest
from starlette.status import HTTP_201_CREATED


class TestTeamStatsIngestionRoutes:

    @pytest.fixture
    def sample_stats(self):
        return [
            SimpleNamespace(
                team_id=1,
                games_played=10,
                fielding_percentage=0.98,
                errors=2,
                double_plays=5,
                stolen_base_percentage=0.7,
                passed_balls=1,
                stolen_bases_allowed=3,
            )
        ]

    @patch("src.application.use_cases.team_stats_ingestion_use_cases.IngestAllTeamStatsUseCase.execute")
    def test_ingest_all_team_stats(self, mock_execute, integration_client, sample_stats):
        mock_execute.return_value = {
            "hitting_stats": sample_stats,
            "pitching_stats": sample_stats,
            "fielding_stats": sample_stats,
            "catching_stats": sample_stats,
        }

        response = integration_client.post("/api/v1/data/ingest/team_stats?season=2025")
        assert response.status_code == HTTP_201_CREATED
        body = response.json()
        assert body["status"] == "success"
        assert body["code"] == HTTP_201_CREATED
        assert body["data"]["hitting_stats_count"] == 1
        assert body["data"]["pitching_stats_count"] == 1
        assert body["data"]["fielding_stats_count"] == 1
        assert body["data"]["catching_stats_count"] == 1
        assert body["data"]["season"] == 2025

    @patch("src.application.use_cases.team_stats_ingestion_use_cases.IngestTeamHittingStatsUseCase.execute")
    def test_ingest_team_hitting_stats(self, mock_execute, integration_client, sample_stats):
        mock_execute.return_value = sample_stats
        response = integration_client.post("/api/v1/data/ingest/team_stats/hitting?season=2024")
        assert response.status_code == HTTP_201_CREATED
        body = response.json()
        assert body["status"] == "success"
        assert body["code"] == HTTP_201_CREATED
        assert body["data"]["hitting_stats_count"] == 1
        assert body["data"]["season"] == 2024

    @patch("src.application.use_cases.team_stats_ingestion_use_cases.IngestTeamPitchingStatsUseCase.execute")
    def test_ingest_team_pitching_stats(self, mock_execute, integration_client, sample_stats):
        mock_execute.return_value = sample_stats
        response = integration_client.post("/api/v1/data/ingest/team_stats/pitching?season=2023")
        assert response.status_code == HTTP_201_CREATED
        body = response.json()
        assert body["status"] == "success"
        assert body["code"] == HTTP_201_CREATED
        assert body["data"]["pitching_stats_count"] == 1
        assert body["data"]["season"] == 2023

    @patch("src.application.use_cases.team_stats_ingestion_use_cases.IngestTeamFieldingStatsUseCase.execute")
    def test_ingest_team_fielding_stats(self, mock_execute, integration_client, sample_stats):
        mock_execute.return_value = sample_stats
        response = integration_client.post("/api/v1/data/ingest/team_stats/fielding?season=2022")
        assert response.status_code == HTTP_201_CREATED
        body = response.json()
        assert body["status"] == "success"
        assert body["code"] == HTTP_201_CREATED
        assert body["data"]["fielding_stats_count"] == 1
        assert body["data"]["season"] == 2022

    @patch("src.application.use_cases.team_stats_ingestion_use_cases.IngestTeamCatchingStatsUseCase.execute")
    def test_ingest_team_catching_stats(self, mock_execute, integration_client, sample_stats):
        mock_execute.return_value = sample_stats
        response = integration_client.post("/api/v1/data/ingest/team_stats/catching?season=2021")
        assert response.status_code == HTTP_201_CREATED
        body = response.json()
        assert body["status"] == "success"
        assert body["code"] == HTTP_201_CREATED
        assert body["data"]["catching_stats_count"] == 1
        assert body["data"]["season"] == 2021
