from datetime import UTC, datetime, timedelta

import pytest

from application.use_cases.player_stats_support import (
    aggregate_metrics,
    build_aggregated_group_record,
    build_career_group_record,
    build_external_reference,
    build_group_record,
    build_history_context,
    build_history_record,
    group_records_by_season,
    iter_response_splits,
    limit_recent_history,
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
from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord


def _build_group_record(stat_group: str, season: int, team_id: int, metrics: dict) -> PlayerStatsGroupRecord:
    return PlayerStatsGroupRecord.create(
        player_id=7,
        team_id=team_id,
        season=season,
        game_type="R",
        stat_group=stat_group,
        metrics=metrics,
    )


def test_numeric_and_normalization_helpers_cover_edge_cases():
    # Given / When / Then
    assert normalize_stat_group("HITTING") == "hitting"
    assert normalize_game_type(None) == "R"
    assert resolve_requested_groups("all") == ("hitting", "pitching", "fielding", "catching", "running")
    assert safe_int("8") == 8
    assert safe_int("bad") == 0
    assert safe_float("1.5") == 1.5
    assert safe_float("bad") == 0.0
    assert parse_datetime_candidate("2025-03-20T10:00:00Z") == datetime(2025, 3, 20, 10, 0, tzinfo=UTC)
    existing_datetime = datetime(2025, 3, 20, 10, 0)
    assert parse_datetime_candidate(existing_datetime) is existing_datetime
    assert parse_datetime_candidate("bad-date") is None


def test_normalize_helpers_reject_invalid_values():
    # Given / When / Then
    with pytest.raises(ValueError, match="group must be one of"):
        normalize_stat_group("unknown")

    with pytest.raises(ValueError, match="gameType must be one of"):
        normalize_game_type("X")


def test_normalize_aggregate_metrics_and_merge_metrics_use_expected_field_mapping():
    # Given
    season_payload = {
        "gamesPlayed": "10",
        "hits": "12",
        "avg": "0.300",
        "plateAppearances": "40",
        "obp": "0.400",
    }
    advanced_payload = {
        "hits": "0",
        "avg": "0.350",
        "ops": "0.900",
    }

    # When
    base_metrics = normalize_aggregate_metrics("hitting", season_payload)
    merged_metrics = merge_metrics(base_metrics, normalize_aggregate_metrics("hitting", advanced_payload))

    # Then
    assert base_metrics["games_played"] == 10
    assert base_metrics["hits"] == 12
    assert base_metrics["batting_average"] == 0.3
    assert base_metrics["intentional_walks"] == 0
    assert merged_metrics["hits"] == 12
    assert merged_metrics["batting_average"] == 0.35
    assert merged_metrics["ops"] == 0.9


def test_merge_metrics_overrides_non_float_truthy_values():
    # Given
    base_metrics = {"games_played": 10, "position": "RF"}
    incoming_metrics = {"games_played": 12, "position": "CF"}

    # When
    merged_metrics = merge_metrics(base_metrics, incoming_metrics)

    # Then
    assert merged_metrics["games_played"] == 12
    assert merged_metrics["position"] == "CF"


def test_team_and_history_context_helpers_extract_expected_values():
    # Given
    split_payload = {
        "team": {"id": 119},
        "split": {"code": "home", "value": "Y", "description": "Home"},
        "date": "2025-03-20",
        "game": {"gamePk": 12345},
        "stat": {"hits": 2},
    }

    # When
    history_record = build_history_record(
        player_id=7,
        team_id=11,
        season=2025,
        game_type="R",
        stat_group="hitting",
        stat_type="gameLog",
        split_payload=split_payload,
        index=0,
    )

    # Then
    assert resolve_team_mlb_id(split_payload) == 119
    assert build_external_reference("gameLog", split_payload, 0) == "12345"
    assert build_history_context(split_payload) == ("home", "Y", "Home")
    assert history_record.external_reference == "12345"
    assert history_record.event_date == datetime(2025, 3, 20)


def test_build_external_reference_hashes_split_payload_when_no_game_identifier_exists():
    # Given
    split_payload = {"split": {"code": "vsL"}, "stat": {"hits": 2}}

    # When
    external_reference = build_external_reference("statSplits", split_payload, 3)

    # Then
    assert external_reference.startswith("statSplits-3-")


def test_iter_response_splits_and_external_reference_prioritize_game_identifiers():
    # Given
    stats_response = {
        "stats_data": [
            {"splits": [{"game": {"gamePk": 111}, "date": "2025-03-20"}]},
            {"splits": [{"gamePk": 222, "date": "2025-03-21"}]},
        ]
    }

    # When
    splits = list(iter_response_splits(stats_response))
    game_reference = build_external_reference("gameLog", {"game": {"gamePk": 111}, "gamePk": 222, "date": "x"}, 0)
    dated_reference = build_external_reference("gameLog", {"date": "2025-03-20"}, 1)

    # Then
    assert len(splits) == 2
    assert splits[0]["game"]["gamePk"] == 111
    assert splits[1]["gamePk"] == 222
    assert game_reference == "111"
    assert dated_reference == "2025-03-20"


def test_history_context_uses_fallback_fields_and_strips_blank_values():
    # Given
    split_payload = {"split": {"id": "vsLeft", "value": "", "code": "L", "displayName": " Lefties "}}

    # When
    context = build_history_context(split_payload)
    missing_context = build_history_context({"split": "invalid"})

    # Then
    assert context == ("L", "L", "Lefties")
    assert missing_context == (None, None, None)


def test_build_group_and_career_records_preserve_metadata_and_derive_aggregate_source():
    # Given
    source_updated_at = datetime(2025, 3, 20, 10, 0, 0)
    first_record = build_group_record(
        player_id=7,
        team_id=1,
        season=2025,
        game_type="R",
        stat_group="hitting",
        metrics={"hits": 10, "plate_appearances": 40, "batting_average": 0.25},
        raw_payload={"source": "season"},
        source_updated_at=source_updated_at,
    )
    second_record = build_group_record(
        player_id=7,
        team_id=2,
        season=2025,
        game_type="R",
        stat_group="hitting",
        metrics={"hits": 6, "plate_appearances": 20, "batting_average": 0.4},
        raw_payload={"source": "seasonAdvanced"},
    )
    first_record.updated_at = datetime(2025, 3, 20, 11, 0, 0)
    second_record.created_at = datetime(2025, 3, 20, 9, 0, 0)
    second_record.updated_at = datetime(2025, 3, 20, 12, 0, 0)

    # When
    career_record = build_career_group_record(7, "R", "hitting", [first_record, second_record])

    # Then
    assert first_record.raw_payload == {"source": "season"}
    assert first_record.source_updated_at == source_updated_at
    assert career_record.source == "derived"
    assert career_record.team_id is None
    assert career_record.season == 0
    assert career_record.metrics["hits"] == 16
    assert career_record.created_at == second_record.created_at
    assert career_record.updated_at == second_record.updated_at


def test_aggregate_metrics_handles_zero_weight_and_recent_history_without_window():
    # Given
    zero_weight_records = [
        _build_group_record("hitting", 2025, 1, {"hits": 1, "plate_appearances": 0, "batting_average": 0.5}),
        _build_group_record("hitting", 2025, 2, {"hits": 2, "plate_appearances": 0, "batting_average": 0.3}),
    ]
    records = [
        PlayerStatsHistoryRecord.create(
            player_id=7,
            team_id=1,
            season=2025,
            game_type="R",
            stat_group="hitting",
            stat_type="gameLog",
            external_reference="aware",
            payload={},
            event_date=datetime.now(UTC) - timedelta(hours=1),
        )
    ]

    # When
    aggregated_metrics = aggregate_metrics(zero_weight_records, "hitting")
    unchanged_records = limit_recent_history(records, None)
    recent_records = limit_recent_history(records, 1)

    # Then
    assert aggregated_metrics["hits"] == 3
    assert aggregated_metrics["batting_average"] == 0.0
    assert unchanged_records is records
    assert [record.external_reference for record in recent_records] == ["aware"]


def test_aggregate_metrics_grouping_and_recent_history_filters_are_deterministic():
    # Given
    hitting_records = [
        _build_group_record("hitting", 2024, 1, {"hits": 100, "plate_appearances": 400, "batting_average": 0.25}),
        _build_group_record("hitting", 2024, 2, {"hits": 50, "plate_appearances": 200, "batting_average": 0.35}),
        _build_group_record("hitting", 2025, 3, {"hits": 40, "plate_appearances": 120, "batting_average": 0.2}),
    ]
    now = datetime.now(UTC)
    history_records = [
        PlayerStatsHistoryRecord.create(
            player_id=7,
            team_id=1,
            season=2025,
            game_type="R",
            stat_group="hitting",
            stat_type="gameLog",
            external_reference="old",
            payload={},
            event_date=(now - timedelta(days=10)).replace(tzinfo=None),
        ),
        PlayerStatsHistoryRecord.create(
            player_id=7,
            team_id=1,
            season=2025,
            game_type="R",
            stat_group="hitting",
            stat_type="gameLog",
            external_reference="new",
            payload={},
            event_date=(now - timedelta(days=2)).replace(tzinfo=None),
        ),
    ]

    # When
    aggregated_metrics = aggregate_metrics(hitting_records[:2], "hitting")
    grouped_records = group_records_by_season(hitting_records)
    aggregated_record = build_aggregated_group_record(7, 2024, "R", "hitting", hitting_records[:2])
    recent_history = limit_recent_history(history_records, 5)
    empty_aggregate = aggregate_metrics([], "hitting")
    records_with_missing_date = limit_recent_history(
        history_records
        + [
            PlayerStatsHistoryRecord.create(
                player_id=7,
                team_id=1,
                season=2025,
                game_type="R",
                stat_group="hitting",
                stat_type="gameLog",
                external_reference="missing",
                payload={},
                event_date=None,
            )
        ],
        5,
    )

    # Then
    assert aggregated_metrics["hits"] == 150
    assert aggregated_metrics["batting_average"] == 0.283333
    assert set(grouped_records) == {2024, 2025}
    assert aggregated_record.season == 2024
    assert aggregated_record.team_id is None
    assert aggregated_record.metrics["hits"] == 150
    assert [record.external_reference for record in recent_history] == ["new"]
    assert empty_aggregate == {}
    assert [record.external_reference for record in records_with_missing_date] == ["new"]
