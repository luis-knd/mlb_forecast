from datetime import datetime

from domain.entities.game import Game


def test_game_get_winner_paths():
    # Given
    game = Game.create(
        mlb_game_id=1,
        home_team_id=10,
        away_team_id=20,
        game_date=datetime(2026, 1, 1),
        status="completed",
        home_score=5,
        away_score=3,
    )

    # When / Then
    assert game.is_completed() is True
    assert game.get_winner() == 10

    game.away_score = 8
    assert game.get_winner() == 20

    game.away_score = 5
    assert game.get_winner() is None

    game.status = "scheduled"
    assert game.get_winner() is None

    game.status = "completed"
    game.home_score = None
    assert game.get_winner() is None
