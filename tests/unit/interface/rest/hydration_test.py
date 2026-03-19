from datetime import datetime

import pytest

from domain.entities.game import Game
from domain.entities.player import Player
from domain.entities.team import Team
from interface.rest.adapters.hydration import (
    GAME_ALLOWED_INCLUDES,
    PLAYER_ALLOWED_INCLUDES,
    parse_include_selection,
    to_game_response_payload,
    to_game_response_payload_list,
    to_player_response_payload,
    to_player_response_payload_list,
)
from interface.rest.exception_handlers import DomainExceptions


def _build_team(team_id: int = 11, mlb_id: int = 119, name: str = "Los Angeles Dodgers") -> Team:
    return Team(
        id=team_id,
        mlb_id=mlb_id,
        name=name,
        abbreviation="LAD",
        city="Los Angeles",
        division="National League West",
        league="National League",
        venue_name="Dodger Stadium",
        created_at=datetime(2026, 3, 18, 10, 0, 0),
        updated_at=datetime(2026, 3, 18, 10, 5, 0),
    )


def _build_player(team: Team | None = None) -> Player:
    return Player(
        id=7,
        mlb_id=660271,
        first_name="Shohei",
        last_name="Ohtani",
        position="DH",
        bats="L",
        throws="R",
        birth_date=datetime(1994, 7, 5),
        active=True,
        current_team_id=team.id if team else None,
        created_at=datetime(2026, 3, 18, 9, 0, 0),
        updated_at=datetime(2026, 3, 18, 9, 5, 0),
        current_team=team,
    )


def _build_game(home_team: Team, away_team: Team, winning_team: Team | None = None) -> Game:
    return Game(
        id=21,
        mlb_game_id=831526,
        home_team_id=home_team.id or 0,
        away_team_id=away_team.id or 0,
        game_date=datetime(2026, 3, 18, 18, 5, 0),
        status="completed",
        scheduled_innings=9,
        home_score=6,
        away_score=4,
        winning_team_id=winning_team.id if winning_team else None,
        created_at=datetime(2026, 3, 18, 8, 0, 0),
        updated_at=datetime(2026, 3, 18, 22, 0, 0),
        home_team=home_team,
        away_team=away_team,
        winning_team=winning_team,
    )


def test_parse_include_selection_returns_empty_tree_when_query_is_missing():
    # Given
    include_query = None

    # When
    selection = parse_include_selection(include_query, PLAYER_ALLOWED_INCLUDES)

    # Then
    assert selection.tree == {}
    assert selection.full_relations == frozenset()
    assert selection.includes("current_team") is False


def test_parse_include_selection_merges_comma_separated_and_nested_paths():
    # Given
    include_query = [" current_team.venue_name , current_team ", "current_team.league"]

    # When
    selection = parse_include_selection(include_query, PLAYER_ALLOWED_INCLUDES)

    # Then
    assert selection.includes("current_team") is True
    assert selection.includes_full_relation("current_team") is True
    assert selection.tree == {"current_team": {"venue_name": {}, "league": {}}}


def test_parse_include_selection_ignores_blank_and_duplicate_values():
    # Given
    include_query = [" current_team , , current_team ", "current_team"]

    # When
    selection = parse_include_selection(include_query, PLAYER_ALLOWED_INCLUDES)

    # Then
    assert selection.tree == {"current_team": {}}
    assert selection.includes_full_relation("current_team") is True


def test_parse_include_selection_rejects_unknown_paths():
    # Given
    include_query = "current_team.coach"

    # When / Then
    with pytest.raises(DomainExceptions.InvalidDataError, match="Invalid include path 'current_team.coach'"):
        parse_include_selection(include_query, PLAYER_ALLOWED_INCLUDES)


def test_to_player_response_payload_omits_current_team_when_not_requested():
    # Given
    player = _build_player(team=_build_team())
    selection = parse_include_selection(None, PLAYER_ALLOWED_INCLUDES)

    # When
    payload = to_player_response_payload(player, selection)

    # Then
    assert payload["mlb_id"] == 660271
    assert "current_team" not in payload


def test_to_player_response_payload_includes_null_relation_when_requested_but_missing():
    # Given
    player = _build_player(team=None)
    selection = parse_include_selection("current_team", PLAYER_ALLOWED_INCLUDES)

    # When
    payload = to_player_response_payload(player, selection)

    # Then
    assert "current_team" in payload
    assert payload["current_team"] is None


def test_to_player_response_payload_list_includes_full_current_team_when_root_is_requested():
    # Given
    team = _build_team()
    players = [_build_player(team=team)]
    selection = parse_include_selection("current_team", PLAYER_ALLOWED_INCLUDES)

    # When
    payload = to_player_response_payload_list(players, selection)

    # Then
    assert payload[0]["current_team"]["mlb_id"] == 119
    assert payload[0]["current_team"]["venue_name"] == "Dodger Stadium"
    assert payload[0]["current_team"]["league"] == "National League"


def test_to_player_response_payload_projects_only_requested_nested_current_team_fields():
    # Given
    player = _build_player(team=_build_team())
    selection = parse_include_selection("current_team.venue_name", PLAYER_ALLOWED_INCLUDES)

    # When
    payload = to_player_response_payload(player, selection)

    # Then
    assert payload["current_team"] == {"venue_name": "Dodger Stadium"}


def test_to_player_response_payload_returns_full_current_team_when_root_and_nested_paths_are_combined():
    # Given
    player = _build_player(team=_build_team())
    selection = parse_include_selection(["current_team", "current_team.venue_name"], PLAYER_ALLOWED_INCLUDES)

    # When
    payload = to_player_response_payload(player, selection)

    # Then
    assert payload["current_team"]["mlb_id"] == 119
    assert payload["current_team"]["venue_name"] == "Dodger Stadium"
    assert payload["current_team"]["league"] == "National League"


def test_to_game_response_payload_list_projects_nested_relations_and_keeps_full_root_relations():
    # Given
    home_team = _build_team(team_id=11, mlb_id=119, name="Los Angeles Dodgers")
    away_team = _build_team(team_id=12, mlb_id=121, name="New York Mets")
    game = _build_game(home_team=home_team, away_team=away_team, winning_team=home_team)
    selection = parse_include_selection(
        ["home_team.venue_name", "winning_team", "away_team.city"],
        GAME_ALLOWED_INCLUDES,
    )

    # When
    payload = to_game_response_payload_list([game], selection)

    # Then
    assert payload[0]["home_team"] == {"venue_name": "Dodger Stadium"}
    assert payload[0]["away_team"] == {"city": "Los Angeles"}
    assert payload[0]["winning_team"]["mlb_id"] == 119
    assert payload[0]["winning_team"]["name"] == "Los Angeles Dodgers"


def test_to_game_response_payload_omits_relations_when_not_requested():
    # Given
    home_team = _build_team(team_id=11, mlb_id=119, name="Los Angeles Dodgers")
    away_team = _build_team(team_id=12, mlb_id=121, name="New York Mets")
    game = _build_game(home_team=home_team, away_team=away_team, winning_team=home_team)
    selection = parse_include_selection(None, GAME_ALLOWED_INCLUDES)

    # When
    payload = to_game_response_payload(game, selection)

    # Then
    assert payload["mlb_game_id"] == 831526
    assert "home_team" not in payload
    assert "away_team" not in payload
    assert "winning_team" not in payload
