import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from application.use_cases.player_stats_support import (
    build_external_reference,
    build_history_context,
    build_history_entry_key,
    build_history_record,
    deduplicate_history_records,
    limit_recent_history,
)
from domain.entities.player_stats_records import PlayerStatsHistoryRecord


@pytest.mark.parametrize(
    ("split_payload", "expected_reference"),
    [
        ({"game": {"gamePk": 111}, "gamePk": 222, "gameId": 333, "date": "2025-03-20"}, "111"),
        ({"gamePk": 222, "gameId": 333, "date": "2025-03-20"}, "222"),
        ({"gameId": 333, "date": "2025-03-20"}, "333"),
        ({"date": "2025-03-20"}, "2025-03-20"),
    ],
)
def test_build_external_reference_prioritizes_game_log_identifiers(split_payload, expected_reference):
    # Given / When / Then
    assert build_external_reference("gameLog", split_payload, 0) == expected_reference


def test_build_external_reference_hashes_non_game_log_payloads():
    # Given
    split_payload = {"split": {"code": "vsL"}, "stat": {"hits": 2}}
    expected_digest = hashlib.sha1(json.dumps(split_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[
        :16
    ]

    # When
    first_reference = build_external_reference("statSplits", split_payload, 3)
    second_reference = build_external_reference("statSplits", split_payload, 3)

    # Then
    assert first_reference == f"statSplits-3-{expected_digest}"
    assert first_reference == second_reference


def test_build_external_reference_hashes_game_logs_without_identifiers():
    # Given
    split_payload = {"stat": {"hits": 2}}
    expected_digest = hashlib.sha1(json.dumps(split_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[
        :16
    ]

    # When
    external_reference = build_external_reference("gameLog", split_payload, 2)

    # Then
    assert external_reference == f"gameLog-2-{expected_digest}"


@pytest.mark.parametrize(
    ("split_payload", "expected"),
    [
        (
            {"split": {"code": "home", "value": "Y", "description": "Home"}},
            ("home", "Y", "Home"),
        ),
        (
            {"split": {"id": "vsLeft", "value": "", "code": "L", "displayName": " Lefties "}},
            ("L", "L", "Lefties"),
        ),
        (
            {"split": {"id": "month", "name": " March "}},
            ("month", None, "March"),
        ),
        ({"split": "invalid"}, (None, None, None)),
    ],
)
def test_build_history_context_uses_fallback_fields(split_payload, expected):
    # Given / When / Then
    assert build_history_context(split_payload) == expected


def test_build_history_record_uses_context_and_datetime_parsing():
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
    assert history_record.team_id == 11
    assert history_record.external_reference == "12345"
    assert history_record.history_entry_key.startswith("gameLog|12345|home|Y|")
    assert history_record.event_date == datetime(2025, 3, 20)
    assert history_record.context_key == "home"
    assert history_record.context_value == "Y"
    assert history_record.context_label == "Home"


def test_build_history_entry_key_distinguishes_same_game_log_by_payload():
    # Given
    first_payload = {"game": {"gamePk": 822839}, "stat": {"gamesStarted": 1, "putOuts": 3}}
    second_payload = {"game": {"gamePk": 822839}, "stat": {"gamesStarted": 0, "putOuts": 0}}

    # When
    first_entry_key = build_history_entry_key("gameLog", "822839", first_payload, None, None)
    second_entry_key = build_history_entry_key("gameLog", "822839", second_payload, None, None)

    # Then
    assert first_entry_key != second_entry_key


def test_build_history_entry_key_distinguishes_same_payload_by_context():
    # Given
    split_payload = {"stat": {"hits": 2}}

    # When
    home_entry_key = build_history_entry_key("statSplits", "abc", split_payload, "home", "Y")
    away_entry_key = build_history_entry_key("statSplits", "abc", split_payload, "away", "N")

    # Then
    assert home_entry_key != away_entry_key


def test_build_history_entry_key_is_stable_for_equivalent_payload_orderings():
    # Given
    first_payload = {"split": {"code": "home"}, "stat": {"hits": 2, "runs": 1}}
    second_payload = {"stat": {"runs": 1, "hits": 2}, "split": {"code": "home"}}
    expected_digest = hashlib.sha1(
        json.dumps(first_payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()[:16]

    # When
    first_entry_key = build_history_entry_key("statSplits", "split-ref", first_payload, None, None)
    second_entry_key = build_history_entry_key("statSplits", "split-ref", second_payload, None, None)

    # Then
    assert first_entry_key == f"statSplits|split-ref|-|-|{expected_digest}"
    assert second_entry_key == first_entry_key


def test_build_history_record_uses_hashed_reference_for_stat_splits():
    # Given
    split_payload = {
        "split": {"code": "away", "value": "N", "description": "Away"},
        "stat": {"hits": 2},
    }

    # When
    history_record = build_history_record(
        player_id=7,
        team_id=11,
        season=2025,
        game_type="R",
        stat_group="hitting",
        stat_type="statSplits",
        split_payload=split_payload,
        index=3,
    )

    # Then
    assert history_record.external_reference.startswith("statSplits-3-")
    assert history_record.history_entry_key.startswith(f"statSplits|{history_record.external_reference}|away|N|")


def test_deduplicate_history_records_keeps_first_exact_duplicate():
    # Given
    first_record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=1,
        season=2025,
        game_type="R",
        stat_group="fielding",
        stat_type="gameLog",
        external_reference="822839",
        history_entry_key="gameLog|822839|-|-|abcd1234",
        payload={"game": {"gamePk": 822839}, "stat": {"putOuts": 3}},
    )
    duplicate_record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=1,
        season=2025,
        game_type="R",
        stat_group="fielding",
        stat_type="gameLog",
        external_reference="822839",
        history_entry_key="gameLog|822839|-|-|abcd1234",
        payload={"game": {"gamePk": 822839}, "stat": {"putOuts": 3}},
    )

    # When
    deduplicated_records = deduplicate_history_records([first_record, duplicate_record])

    # Then
    assert deduplicated_records == [first_record]


def test_deduplicate_history_records_keeps_distinct_rows_with_same_external_reference():
    # Given
    first_record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=1,
        season=2025,
        game_type="R",
        stat_group="fielding",
        stat_type="gameLog",
        external_reference="822839",
        history_entry_key="gameLog|822839|-|-|firstpayloadhash",
        payload={"game": {"gamePk": 822839}, "stat": {"putOuts": 3}},
    )
    second_record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=1,
        season=2025,
        game_type="R",
        stat_group="fielding",
        stat_type="gameLog",
        external_reference="822839",
        history_entry_key="gameLog|822839|-|-|secondpayloadhas",
        payload={"game": {"gamePk": 822839}, "stat": {"putOuts": 0}},
    )

    # When
    deduplicated_records = deduplicate_history_records([first_record, second_record])

    # Then
    assert deduplicated_records == [first_record, second_record]


def test_deduplicate_history_records_keeps_following_records_after_skipping_duplicate():
    # Given
    first_record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=1,
        season=2025,
        game_type="R",
        stat_group="fielding",
        stat_type="gameLog",
        external_reference="822839",
        history_entry_key="gameLog|822839|-|-|firstpayloadhash",
        payload={"game": {"gamePk": 822839}, "stat": {"putOuts": 3}},
    )
    duplicate_record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=1,
        season=2025,
        game_type="R",
        stat_group="fielding",
        stat_type="gameLog",
        external_reference="822839",
        history_entry_key="gameLog|822839|-|-|firstpayloadhash",
        payload={"game": {"gamePk": 822839}, "stat": {"putOuts": 3}},
    )
    trailing_record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=1,
        season=2025,
        game_type="R",
        stat_group="fielding",
        stat_type="gameLog",
        external_reference="822840",
        history_entry_key="gameLog|822840|-|-|trailingpayloadha",
        payload={"game": {"gamePk": 822840}, "stat": {"putOuts": 1}},
    )

    # When
    deduplicated_records = deduplicate_history_records([first_record, duplicate_record, trailing_record])

    # Then
    assert deduplicated_records == [first_record, trailing_record]


def test_limit_recent_history_filters_records_using_days_back_and_timezone_awareness():
    # Given
    now = datetime.now(UTC)
    records = [
        PlayerStatsHistoryRecord.create(
            player_id=7,
            team_id=1,
            season=2025,
            game_type="R",
            stat_group="hitting",
            stat_type="gameLog",
            external_reference="recent-aware",
            payload={},
            event_date=now - timedelta(hours=12),
        ),
        PlayerStatsHistoryRecord.create(
            player_id=7,
            team_id=1,
            season=2025,
            game_type="R",
            stat_group="hitting",
            stat_type="gameLog",
            external_reference="recent-naive",
            payload={},
            event_date=(now - timedelta(days=1)).replace(tzinfo=None),
        ),
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
            external_reference="missing-date",
            payload={},
            event_date=None,
        ),
    ]

    # When
    unchanged_records = limit_recent_history(records, None)
    limited_records = limit_recent_history(records, 2)
    same_day_records = limit_recent_history(records, 0)

    # Then
    assert unchanged_records is records
    assert [record.external_reference for record in limited_records] == ["recent-aware", "recent-naive"]
    assert [record.external_reference for record in same_day_records] == ["recent-aware"]
