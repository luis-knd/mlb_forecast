from datetime import UTC, datetime

import pytest

from application.use_cases.player_stats_support import (
    iter_response_splits,
    merge_metrics,
    normalize_aggregate_metrics,
    normalize_game_type,
    normalize_stat_group,
    parse_datetime_candidate,
    resolve_requested_groups,
    resolve_team_mlb_id,
    safe_float,
    safe_int,
)
from tests.unit.use_cases.player_stats_test_support_test import NORMALIZE_AGGREGATE_CASES


@pytest.mark.parametrize(
    ("raw_group", "expected_group"),
    [
        ("HITTING", "hitting"),
        (" pitching ", "pitching"),
        ("Fielding", "fielding"),
        ("CATCHING", "catching"),
        (" running ", "running"),
        ("all", "all"),
    ],
)
def test_normalize_stat_group_accepts_supported_values(raw_group, expected_group):
    # Given / When / Then
    assert normalize_stat_group(raw_group) == expected_group


@pytest.mark.parametrize("raw_group", ["", "unknown", " post-season "])
def test_normalize_stat_group_rejects_invalid_values(raw_group):
    # Given / When / Then
    with pytest.raises(ValueError, match="group must be one of"):
        normalize_stat_group(raw_group)


@pytest.mark.parametrize(
    ("raw_game_type", "expected_game_type"),
    [
        (None, "R"),
        ("r", "R"),
        (" s ", "S"),
        ("P", "P"),
        ("w", "W"),
        (" a ", "A"),
        ("D", "D"),
        ("f", "F"),
        ("L", "L"),
    ],
)
def test_normalize_game_type_accepts_supported_values(raw_game_type, expected_game_type):
    # Given / When / Then
    assert normalize_game_type(raw_game_type) == expected_game_type


@pytest.mark.parametrize("raw_game_type", [" ", "X", " regular "])
def test_normalize_game_type_rejects_invalid_values(raw_game_type):
    # Given / When / Then
    with pytest.raises(ValueError, match="gameType must be one of"):
        normalize_game_type(raw_game_type)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, 0),
        ("", 0),
        ("8", 8),
        (7, 7),
        ("bad", 0),
    ],
)
def test_safe_int_normalizes_expected_values(value, expected):
    # Given / When / Then
    assert safe_int(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, 0.0),
        ("", 0.0),
        ("1.5", 1.5),
        (2, 2.0),
        ("bad", 0.0),
    ],
)
def test_safe_float_normalizes_expected_values(value, expected):
    # Given / When / Then
    assert safe_float(value) == expected


def test_parse_datetime_candidate_supports_strings_and_datetimes():
    # Given
    existing_datetime = datetime(2025, 3, 20, 10, 0)

    # When / Then
    assert parse_datetime_candidate("2025-03-20T10:00:00Z") == datetime(2025, 3, 20, 10, 0, tzinfo=UTC)
    assert parse_datetime_candidate(existing_datetime) is existing_datetime
    assert parse_datetime_candidate(None) is None
    assert parse_datetime_candidate("") is None
    assert parse_datetime_candidate("bad-date") is None


def test_iter_response_splits_yields_known_splits_and_ignores_missing_blocks():
    # Given
    stats_response = {
        "stats_data": [
            {"splits": [{"game": {"gamePk": 111}, "date": "2025-03-20"}]},
            {},
            {"splits": [{"gamePk": 222, "date": "2025-03-21"}]},
        ]
    }

    # When
    splits = list(iter_response_splits(stats_response))

    # Then
    assert len(splits) == 2
    assert splits[0]["game"]["gamePk"] == 111
    assert splits[1]["gamePk"] == 222
    assert list(iter_response_splits({})) == []


def test_resolve_requested_groups_returns_expected_sequence():
    # Given / When / Then
    assert resolve_requested_groups("all") == ("hitting", "pitching", "fielding", "catching", "running")
    assert resolve_requested_groups("pitching") == ("pitching",)


@pytest.mark.parametrize(("stat_group", "payload", "expected"), NORMALIZE_AGGREGATE_CASES)
def test_normalize_aggregate_metrics_maps_each_supported_group(stat_group, payload, expected):
    # Given / When
    metrics = normalize_aggregate_metrics(stat_group, payload)

    # Then
    assert metrics == expected


def test_normalize_aggregate_metrics_defaults_missing_values_to_zero():
    # Given / When
    metrics = normalize_aggregate_metrics("hitting", {"hits": None, "avg": "", "obp": "bad"})

    # Then
    assert metrics["hits"] == 0
    assert metrics["batting_average"] == 0.0
    assert metrics["on_base_percentage"] == 0.0


@pytest.mark.parametrize(
    ("incoming_metrics", "expected"),
    [
        (
            {"games_played": 12, "position": "CF"},
            {"games_played": 12, "position": "CF", "batting_average": 0.25},
        ),
        (
            {"games_played": 0, "position": ""},
            {"games_played": 10, "position": "RF", "batting_average": 0.25},
        ),
        ({"batting_average": 0.0}, {"games_played": 10, "position": "RF", "batting_average": 0.25}),
        ({"batting_average": 0.35}, {"games_played": 10, "position": "RF", "batting_average": 0.35}),
    ],
)
def test_merge_metrics_only_overrides_meaningful_values(incoming_metrics, expected):
    # Given
    base_metrics = {"games_played": 10, "position": "RF", "batting_average": 0.25}

    # When
    merged_metrics = merge_metrics(base_metrics, incoming_metrics)

    # Then
    assert merged_metrics == expected


@pytest.mark.parametrize(
    ("team_payload", "expected_team_id"),
    [
        ({"team": {"id": 119}}, 119),
        ({"team": {"id": "147"}}, 147),
        ({}, None),
        ({"team": {"id": ""}}, None),
        ({"team": {"id": "bad"}}, None),
    ],
)
def test_resolve_team_mlb_id_handles_missing_and_invalid_values(team_payload, expected_team_id):
    # Given / When / Then
    assert resolve_team_mlb_id(team_payload) == expected_team_id
