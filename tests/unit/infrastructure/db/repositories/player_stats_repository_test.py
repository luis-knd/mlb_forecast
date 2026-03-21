from datetime import datetime

import pytest

from domain.entities.player_stats_records import PlayerStatsGroupRecord, PlayerStatsHistoryRecord
from infrastructure.db.models import PlayerModel, TeamModel
from infrastructure.db.repositories.player_stats_repository import PlayerStatsRepository


async def _seed_team_and_player(db_session) -> tuple[TeamModel, PlayerModel]:
    team = TeamModel(
        mlb_id=119,
        name="Los Angeles Dodgers",
        abbreviation="LAD",
        city="Los Angeles",
        division="National League West",
        league="National League",
        venue_name="Dodger Stadium",
    )
    db_session.add(team)
    db_session.flush()
    player = PlayerModel(
        mlb_id=660271,
        first_name="Shohei",
        last_name="Ohtani",
        position="DH",
        bats="L",
        throws="R",
        birth_date=datetime(1994, 7, 5),
        active=True,
        current_team_id=team.id,
    )
    db_session.add(player)
    db_session.commit()
    return team, player


@pytest.mark.asyncio
async def test_replace_group_records_persists_multi_team_aggregate_data(db_session):
    # Given
    repository = PlayerStatsRepository(db_session)
    team, player = await _seed_team_and_player(db_session)
    records = [
        PlayerStatsGroupRecord.create(player.id, team.id, 2025, "R", "hitting", {"hits": 3, "plate_appearances": 10}),
        PlayerStatsGroupRecord.create(player.id, team.id, 2024, "R", "hitting", {"hits": 5, "plate_appearances": 20}),
    ]

    # When
    persisted_records = await repository.replace_group_records(player.id, 2025, "R", "hitting", [records[0]])
    listed_records = await repository.list_group_records(player.id, game_type="R", stat_group="hitting")
    await repository.upsert_group_record(records[1])

    # Then
    assert len(persisted_records) == 1
    assert persisted_records[0].metrics["hits"] == 3
    assert [record.season for record in listed_records] == [2025]
    updated_records = await repository.list_group_records(player.id, game_type="R", stat_group="hitting")
    assert [record.season for record in updated_records] == [2025, 2024]


@pytest.mark.asyncio
async def test_replace_history_records_replaces_and_filters_history_entries(db_session):
    # Given
    repository = PlayerStatsRepository(db_session)
    team, player = await _seed_team_and_player(db_session)
    first_record = PlayerStatsHistoryRecord.create(
        player_id=player.id,
        team_id=team.id,
        season=2025,
        game_type="R",
        stat_group="hitting",
        stat_type="gameLog",
        external_reference="1",
        payload={"hits": 2},
        event_date=datetime(2025, 3, 20),
    )
    second_record = PlayerStatsHistoryRecord.create(
        player_id=player.id,
        team_id=team.id,
        season=2025,
        game_type="R",
        stat_group="hitting",
        stat_type="gameLog",
        external_reference="2",
        payload={"hits": 1},
        event_date=datetime(2025, 3, 21),
    )

    # When
    persisted_records = await repository.replace_history_records(
        player.id,
        2025,
        "R",
        "hitting",
        "gameLog",
        [first_record, second_record],
    )
    listed_records = await repository.list_history_records(
        player_id=player.id,
        stat_type="gameLog",
        season=2025,
        game_type="R",
        stat_group="hitting",
        limit=1,
    )

    # Then
    assert len(persisted_records) == 2
    assert persisted_records[0].payload["hits"] == 2
    assert len(listed_records) == 1
    assert listed_records[0].external_reference == "2"
