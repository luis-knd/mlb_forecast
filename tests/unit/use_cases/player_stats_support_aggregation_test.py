from datetime import datetime

import pytest

from application.use_cases.player_stats_support import (
    aggregate_metrics,
    build_aggregated_group_record,
    build_career_group_record,
    build_group_record,
    group_records_by_season,
)
from tests.unit.use_cases.player_stats_test_support_test import AGGREGATE_METRICS_CASES
from tests.unit.use_cases.player_stats_test_support_test import build_group_record as make_group_record


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
    assert career_record.raw_payload is None


@pytest.mark.parametrize(
    ("stat_group", "weight_field", "float_field", "expected_games_played", "expected_float"),
    AGGREGATE_METRICS_CASES,
)
def test_aggregate_metrics_uses_expected_weight_field(
    stat_group,
    weight_field,
    float_field,
    expected_games_played,
    expected_float,
):
    # Given
    first_record = make_group_record(stat_group, 2025, 1, {"games_played": 2, "hits": 4})
    second_record = make_group_record(stat_group, 2025, 2, {"games_played": 3, "hits": 6})
    first_record.metrics[weight_field] = 2
    second_record.metrics[weight_field] = 6
    first_record.metrics[float_field] = 0.9
    second_record.metrics[float_field] = 0.0

    # When
    aggregated_metrics = aggregate_metrics([first_record, second_record], stat_group)

    # Then
    assert aggregated_metrics["games_played"] == expected_games_played
    assert aggregated_metrics[float_field] == expected_float


def test_aggregate_metrics_handles_zero_weight_and_empty_records():
    # Given
    zero_weight_records = [
        make_group_record("hitting", 2025, 1, {"hits": 1, "plate_appearances": 0, "batting_average": 0.5}),
        make_group_record("hitting", 2025, 2, {"hits": 2, "plate_appearances": 0, "batting_average": 0.3}),
    ]

    # When
    aggregated_metrics = aggregate_metrics(zero_weight_records, "hitting")

    # Then
    assert aggregated_metrics["hits"] == 3
    assert aggregated_metrics["batting_average"] == 0.0
    assert aggregate_metrics([], "hitting") == {}


def test_group_records_by_season_preserves_each_record_in_its_bucket():
    # Given
    records = [
        make_group_record("hitting", 2024, 1, {"hits": 100, "plate_appearances": 400}),
        make_group_record("hitting", 2024, 2, {"hits": 50, "plate_appearances": 200}),
        make_group_record("hitting", 2025, 3, {"hits": 40, "plate_appearances": 120}),
    ]

    # When
    grouped_records = group_records_by_season(records)

    # Then
    assert set(grouped_records) == {2024, 2025}
    assert [record.team_id for record in grouped_records[2024]] == [1, 2]
    assert [record.team_id for record in grouped_records[2025]] == [3]


def test_build_aggregated_group_record_sets_expected_metadata():
    # Given
    first_record = make_group_record(
        "hitting", 2024, 1, {"hits": 100, "plate_appearances": 400, "batting_average": 0.25}
    )
    second_record = make_group_record(
        "hitting", 2024, 2, {"hits": 50, "plate_appearances": 200, "batting_average": 0.35}
    )
    source_updated_at = datetime(2025, 3, 20, 13, 0, 0)
    first_ingested_at = datetime(2025, 3, 20, 14, 0, 0)
    second_ingested_at = datetime(2025, 3, 20, 15, 0, 0)
    created_at = datetime(2025, 3, 20, 9, 0, 0)
    second_created_at = datetime(2025, 3, 20, 10, 0, 0)
    first_updated_at = datetime(2025, 3, 20, 11, 0, 0)
    updated_at = datetime(2025, 3, 20, 16, 0, 0)
    first_record.source_updated_at = source_updated_at
    first_record.ingested_at = first_ingested_at
    second_record.ingested_at = second_ingested_at
    first_record.created_at = created_at
    second_record.created_at = second_created_at
    first_record.updated_at = first_updated_at
    second_record.updated_at = updated_at

    # When
    aggregated_record = build_aggregated_group_record(7, 2024, "R", "hitting", [first_record, second_record])

    # Then
    assert aggregated_record.season == 2024
    assert aggregated_record.team_id is None
    assert aggregated_record.source == "derived"
    assert aggregated_record.source_updated_at == source_updated_at
    assert aggregated_record.ingested_at == second_ingested_at
    assert aggregated_record.created_at == created_at
    assert aggregated_record.updated_at == updated_at
    assert aggregated_record.metrics["hits"] == 150
    assert aggregated_record.metrics["batting_average"] == 0.283333
