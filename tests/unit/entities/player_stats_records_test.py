from datetime import datetime

import pytest

from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord


def test_player_stats_group_record_create_normalizes_values_and_builds_cache_key():
    # Given / When
    record = PlayerStatsGroupRecord.create(
        player_id=7,
        team_id=11,
        season=2025,
        game_type="r",
        stat_group="HITTING",
        metrics={"hits": 10},
        raw_payload={"sample": True},
    )

    # Then
    assert record.player_id == 7
    assert record.team_id == 11
    assert record.game_type == "R"
    assert record.stat_group == "hitting"
    assert record.metrics == {"hits": 10}
    assert record.raw_payload == {"sample": True}
    assert record.created_at is not None
    assert record.updated_at is not None
    assert record.cache_key() == "player_stats:aggregate:player=7:season=2025:gameType=R:group=hitting"


def test_player_stats_group_record_create_rejects_unknown_group():
    # Given / When / Then
    with pytest.raises(ValueError, match="stat_group must be one of"):
        PlayerStatsGroupRecord.create(
            player_id=7,
            team_id=11,
            season=2025,
            game_type="R",
            stat_group="unknown",
            metrics={},
        )


def test_player_stats_history_record_create_normalizes_values_and_builds_cache_key():
    # Given
    event_date = datetime(2025, 3, 20, 12, 0, 0)

    # When
    record = PlayerStatsHistoryRecord.create(
        player_id=7,
        team_id=11,
        season=2025,
        game_type="r",
        stat_group="Pitching",
        stat_type="gameLog",
        external_reference="123",
        payload={"outs": 9},
        event_date=event_date,
        context_key="home",
        context_value="yes",
        context_label="Home split",
    )

    # Then
    assert record.player_id == 7
    assert record.team_id == 11
    assert record.game_type == "R"
    assert record.stat_group == "pitching"
    assert record.stat_type == "gameLog"
    assert record.event_date == event_date
    assert record.payload == {"outs": 9}
    assert record.context_key == "home"
    assert record.context_value == "yes"
    assert record.context_label == "Home split"
    assert record.cache_key() == "player_stats:history:player=7:season=2025:gameType=R:group=pitching:type=gameLog"


def test_player_stats_history_record_create_rejects_unknown_type():
    # Given / When / Then
    with pytest.raises(ValueError, match="stat_type must be one of"):
        PlayerStatsHistoryRecord.create(
            player_id=7,
            team_id=11,
            season=2025,
            game_type="R",
            stat_group="running",
            stat_type="season",
            external_reference="123",
            payload={},
        )
