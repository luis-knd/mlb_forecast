from unittest.mock import patch

import pytest
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from domain.entities.team import Team


class TestTeamRoutesIntegration:
    def test_list_all_teams(self, integration_client, populated_test_db):
        # When
        response = integration_client.get("/api/v1/teams")

        # Then
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["code"] == HTTP_200_OK
        assert len(data["data"]) == 6
        assert "Retrieved 6 teams successfully" in data["message"]

        team_names = {team["name"] for team in data["data"]}
        expected_names = {
            "Oakland Athletics",
            "Seattle Mariners",
            "New York Yankees",
            "Los Angeles Dodgers",
            "San Francisco Giants",
            "New York Mets",
        }
        assert team_names == expected_names

    @pytest.mark.parametrize(
        "league, expected_league, expected_teams",
        [
            ("American League", "American League", {"Oakland Athletics", "Seattle Mariners", "New York Yankees"}),
            ("american league", "American League", {"Oakland Athletics", "Seattle Mariners", "New York Yankees"}),
            ("  AMERICAN LEAGUE  ", "American League", {"Oakland Athletics", "Seattle Mariners", "New York Yankees"}),
            ("American", "American League", {"Oakland Athletics", "Seattle Mariners", "New York Yankees"}),
            ("american", "American League", {"Oakland Athletics", "Seattle Mariners", "New York Yankees"}),
            ("AMERICAN", "American League", {"Oakland Athletics", "Seattle Mariners", "New York Yankees"}),
            ("  AMERICAN  ", "American League", {"Oakland Athletics", "Seattle Mariners", "New York Yankees"}),
            ("National", "National League", {"Los Angeles Dodgers", "San Francisco Giants", "New York Mets"}),
            ("national", "National League", {"Los Angeles Dodgers", "San Francisco Giants", "New York Mets"}),
            ("NATIONAL", "National League", {"Los Angeles Dodgers", "San Francisco Giants", "New York Mets"}),
            ("  NATIONAL  ", "National League", {"Los Angeles Dodgers", "San Francisco Giants", "New York Mets"}),
            (
                "  national league  ",
                "National League",
                {"Los Angeles Dodgers", "San Francisco Giants", "New York Mets"},
            ),
        ],
        ids=[
            "American League",
            "american league",
            "  AMERICAN LEAGUE  ",
            "American",
            "american",
            "AMERICAN",
            "  AMERICAN  ",
            "National",
            "national",
            "NATIONAL",
            "  NATIONAL  ",
            "  national league  ",
        ],
    )
    def test_list_teams_by_league(self, integration_client, populated_test_db, league, expected_league, expected_teams):
        # When
        response = integration_client.get(f"/api/v1/teams?league={league}")

        # Then
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 3

        for team in data["data"]:
            assert expected_league in team["league"]

        team_names = {team["name"] for team in data["data"]}
        assert team_names == expected_teams

    @pytest.mark.parametrize(
        "division, expected_division, expected_teams",
        [
            ("West", "West", {"Oakland Athletics", "Seattle Mariners", "Los Angeles Dodgers", "San Francisco Giants"}),
            ("west", "West", {"Oakland Athletics", "Seattle Mariners", "Los Angeles Dodgers", "San Francisco Giants"}),
            ("WEST", "West", {"Oakland Athletics", "Seattle Mariners", "Los Angeles Dodgers", "San Francisco Giants"}),
            (
                "  WEST  ",
                "West",
                {"Oakland Athletics", "Seattle Mariners", "Los Angeles Dodgers", "San Francisco Giants"},
            ),
            ("East", "East", {"New York Yankees", "New York Mets"}),
            ("east", "East", {"New York Yankees", "New York Mets"}),
            ("central", "Central", set()),
            ("  CENTRAL  ", "Central", set()),
        ],
        ids=["West", "west", "WEST", "  WEST  ", "East", "east", "central", "  CENTRAL  "],
    )
    def test_list_teams_by_division(
        self, integration_client, populated_test_db, division, expected_division, expected_teams
    ):
        # When
        response = integration_client.get(f"/api/v1/teams?division={division}")

        # Then
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == len(expected_teams)
        for team in data["data"]:
            assert expected_division in team["division"]

        team_names = {team["name"] for team in data["data"]}
        assert team_names == expected_teams

    @pytest.mark.parametrize(
        "query,expected_names,expected_count,expected_legue,expected_division",
        [
            (
                "/api/v1/teams?league=American&division=West",
                {"Oakland Athletics", "Seattle Mariners"},
                2,
                "American League",
                "West",
            ),
            (
                "api/v1/teams?league=%20%20%20%20american%20league%20%20%20%20&division=West",
                {"Oakland Athletics", "Seattle Mariners"},
                2,
                "American League",
                "West",
            ),
            ("/api/v1/teams?league=National&division=East", {"New York Mets"}, 1, "National League", "East"),
        ],
        ids=[
            "League=American and Division=West",
            "League=`    american league    ` and Division=West",
            "League=National and Division=East",
        ],
    )
    def test_list_teams_with_combined_filters(
        self,
        integration_client,
        populated_test_db,
        query,
        expected_names,
        expected_count,
        expected_legue,
        expected_division,
    ):
        # When
        response = integration_client.get(query)

        # Then
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == expected_count
        team_names = {team["name"] for team in data["data"]}
        assert team_names == expected_names
        for team in data["data"]:
            assert expected_legue in team["league"]
            assert expected_division in team["division"]

    @pytest.mark.parametrize(
        "query, expected_message",
        [
            ("/api/v1/teams?league=Invalid", "Invalid data provided"),
            ("/api/v1/teams?division=Invalid", "Invalid data provided"),
        ],
        ids=["Invalid league filter", "Invalid division filter"],
    )
    def test_list_teams_with_invalid_filters(self, integration_client, populated_test_db, query, expected_message):
        response = integration_client.get(query)

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["status"] == "error"
        assert expected_message in data["message"]

    def test_get_team_by_id(self, integration_client, populated_test_db):
        # Given
        team_id = populated_test_db[0].id

        # When
        response = integration_client.get(f"/api/v1/teams/{team_id}")

        # Then
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["code"] == HTTP_200_OK
        assert data["data"]["id"] == team_id
        assert data["data"]["name"] == "Oakland Athletics"
        assert data["data"]["league"] == "American League"

    @pytest.mark.parametrize(
        "team_id, expected_status, expected_message",
        [
            (9999, HTTP_404_NOT_FOUND, "Resource not found"),
            (0, HTTP_400_BAD_REQUEST, "Invalid data provided"),
        ],
        ids=["Non-existent team ID (404)", "Invalid team ID (400)"],
    )
    def test_get_team_by_id_errors(
        self,
        integration_client,
        populated_test_db,
        team_id,
        expected_status,
        expected_message,
    ):
        response = integration_client.get(f"/api/v1/teams/{team_id}")

        assert response.status_code == expected_status
        data = response.json()
        assert data["status"] == "error"
        assert expected_message in data["message"]

    @patch("application.use_cases.team_use_cases.IngestTeamsUseCase.execute")
    def test_ingest_teams_with_mocked_external_api(self, mock_execute, integration_client, test_teams_data):
        # Given
        mock_teams = [
            Team.create(
                mlb_id=team_data["mlb_id"],
                name=team_data["name"],
                abbreviation=team_data["abbreviation"],
                city=team_data["city"],
                division=team_data["division"],
                league=team_data["league"],
                venue_name=team_data["venue_name"],
            )
            for team_data in test_teams_data
        ]
        mock_execute.return_value = mock_teams

        # When
        response = integration_client.post("/api/v1/data/ingest/teams")

        # Then
        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "success"
        assert data["code"] == HTTP_201_CREATED
        assert "ingestion_summary" in data["data"]
        assert data["data"]["ingestion_summary"]["operation"] == "team_ingestion"
        assert data["data"]["ingestion_summary"]["records_processed"] == 6
        assert "sample_teams" in data["data"]
        assert len(data["data"]["sample_teams"]) == 6

    @patch("application.use_cases.team_use_cases.IngestTeamsUseCase.execute")
    def test_ingest_teams_external_service_error(self, mock_execute, integration_client):
        # Given
        mock_execute.side_effect = Exception("MLB API connection error")

        # When
        response = integration_client.post("/api/v1/data/ingest/teams")

        # Then
        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "error"
        assert "Service temporarily unavailable" in data["message"]
