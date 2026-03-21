from datetime import datetime

from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord
from interface.rest.adapters.player_stats_mappers import (
    to_group_collection_payload,
    to_group_record_payload,
    to_history_collection_payload,
    to_history_record_payload,
)


def test_group_record_mapper_builds_expected_payload():
    # Given
    record = PlayerStatsGroupRecord.create(
        player_id=7,
        team_id=11,
        season=2025,
        game_type="R",
        stat_group="hitting",
        metrics={"hits": 5},
    )

    # When
    payload = to_group_record_payload(record)

    # Then
    assert payload["player_id"] == 7
    assert payload["team_id"] == 11
    assert payload["metrics"] == {"hits": 5}


def test_history_record_mapper_builds_expected_payload():
    # Given
    record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=11,
        season=2025,
        game_type="R",
        stat_group="hitting",
        stat_type="gameLog",
        external_reference="123",
        payload={"hits": 2},
        event_date=datetime(2025, 3, 20),
        context_key="home",
    )

    # When
    payload = to_history_record_payload(record)

    # Then
    assert payload["external_reference"] == "123"
    assert payload["payload"] == {"hits": 2}
    assert payload["context_key"] == "home"


def test_collection_mappers_wrap_records_with_query_context():
    # Given
    group_record = PlayerStatsGroupRecord.create(7, 11, 2025, "R", "hitting", {"hits": 5})
    history_record = PlayerStatsHistoryRecord.create(7, 11, 2025, "R", "hitting", "gameLog", "123", {"hits": 2})

    # When
    aggregate_payload = to_group_collection_payload(
        player_id=7,
        stats="season",
        group="hitting",
        season=2025,
        game_type="R",
        records=[group_record],
    )
    history_payload = to_history_collection_payload(
        player_id=7,
        stats="gameLog",
        group="hitting",
        season=2025,
        game_type="R",
        records=[history_record],
        days_back=7,
    )

    # Then
    assert aggregate_payload["stats"] == "season"
    assert aggregate_payload["records"][0]["metrics"]["hits"] == 5
    assert history_payload["stats"] == "gameLog"
    assert history_payload["days_back"] == 7
    assert history_payload["records"][0]["external_reference"] == "123"
