from datetime import datetime

from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from src.infrastructure.db.models import GameModel, TeamModel


def _create_team(test_db_session, mlb_id: int, name: str, abbreviation: str) -> TeamModel:
    team = TeamModel(
        mlb_id=mlb_id,
        name=name,
        abbreviation=abbreviation,
        city=name,
        division="American League West",
        league="American League",
        venue_name=f"{name} Park",
    )
    test_db_session.add(team)
    test_db_session.flush()
    return team


def _create_game(test_db_session, home_team: TeamModel, away_team: TeamModel) -> GameModel:
    game = GameModel(
        mlb_game_id=831526,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        game_date=datetime(2026, 2, 28, 18, 5, 0),
        status="scheduled",
        scheduled_innings=9,
        home_score=None,
        away_score=None,
        winning_team_id=None,
    )
    test_db_session.add(game)
    test_db_session.commit()
    test_db_session.refresh(game)
    return game


class TestGameRoutesIntegration:
    def test_get_game_by_id_returns_typed_payload(self, integration_client, test_db_session):
        # Given
        home_team = _create_team(test_db_session, 133, "Oakland Athletics", "OAK")
        away_team = _create_team(test_db_session, 136, "Seattle Mariners", "SEA")
        game = _create_game(test_db_session, home_team, away_team)

        # When
        response = integration_client.get(f"/api/v1/games/{game.id}")

        # Then
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["status"] == "success"
        assert body["code"] == HTTP_200_OK
        assert body["data"]["id"] == game.id
        assert body["data"]["mlb_game_id"] == 831526
        assert body["data"]["home_team_id"] == home_team.id
        assert body["data"]["away_team_id"] == away_team.id

    def test_get_game_by_id_returns_not_found_when_game_does_not_exist(self, integration_client):
        # Given
        missing_game_id = 999999

        # When
        response = integration_client.get(f"/api/v1/games/{missing_game_id}")

        # Then
        assert response.status_code == HTTP_404_NOT_FOUND
        body = response.json()
        assert body["status"] == "error"
        assert body["message"] == "Resource not found"
