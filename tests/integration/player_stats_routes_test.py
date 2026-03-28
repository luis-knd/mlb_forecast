import json
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from application.use_cases.player_stats_ingestion_use_cases import (
    IngestPlayerSeasonStatsUseCase,
    IngestPlayerStatsHistoryUseCase,
)
from application.use_cases.player_stats_read_use_cases import (
    GetPersistedPlayerCareerStatsUseCase,
    GetPersistedPlayerGameLogsUseCase,
    GetPersistedPlayerSeasonStatsUseCase,
    GetPersistedPlayerStatSplitsUseCase,
    GetPersistedPlayerYearByYearStatsUseCase,
)
from infrastructure.db.models import PlayerModel, TeamModel
from infrastructure.db.player_stats_models import PlayerGameLogModel, PlayerHittingStatsModel
from infrastructure.db.repositories.player_repository import PlayerRepository
from infrastructure.db.repositories.player_stats_repository import PlayerStatsRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from interface.rest import player_stats_routes
from tests.integration.conftest import IntegrationGetPlayerUseCase


class _IntegrationCache:
    async def get(self, key, default=None):
        return default

    async def set(self, key, value, ttl=None):
        return True

    async def delete(self, key):
        return True

    async def delete_pattern(self, pattern):
        return 0

    async def exists(self, key):
        return False

    async def clear(self, pattern=None):
        return 0

    async def get_many(self, keys):
        return {}

    async def set_many(self, mapping, ttl=None):
        return True

    async def delete_many(self, keys):
        return 0

    async def increment(self, key, amount=1):
        return amount

    async def decrement(self, key, amount=1):
        return -amount

    async def get_stats(self):
        return {}


def _decode_response(response) -> dict:
    return json.loads(response.body.decode())


def _build_use_cases(db_session) -> dict:
    cache = _IntegrationCache()
    player_repository = PlayerRepository(db_session)
    team_repository = TeamRepository(db_session)
    player_stats_repository = PlayerStatsRepository(db_session)
    mlb_api = AsyncMock()
    return {
        "get_player": IntegrationGetPlayerUseCase(),
        "get_season_stats": GetPersistedPlayerSeasonStatsUseCase(player_stats_repository, cache),
        "get_career_stats": GetPersistedPlayerCareerStatsUseCase(player_stats_repository, cache),
        "get_year_by_year_stats": GetPersistedPlayerYearByYearStatsUseCase(player_stats_repository, cache),
        "get_game_logs": GetPersistedPlayerGameLogsUseCase(player_stats_repository, cache),
        "get_stat_splits": GetPersistedPlayerStatSplitsUseCase(player_stats_repository, cache),
        "ingest_season_stats": IngestPlayerSeasonStatsUseCase(
            player_repository,
            team_repository,
            player_stats_repository,
            mlb_api,
            cache,
        ),
        "ingest_history_stats": IngestPlayerStatsHistoryUseCase(
            player_repository,
            team_repository,
            player_stats_repository,
            mlb_api,
            cache,
        ),
    }


@pytest.fixture
def populated_player_stats_db(test_db_session):
    team = TeamModel(
        mlb_id=119,
        name="Los Angeles Dodgers",
        abbreviation="LAD",
        city="Los Angeles",
        division="National League West",
        league="National League",
        venue_name="Dodger Stadium",
    )
    test_db_session.add(team)
    test_db_session.flush()

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
    test_db_session.add(player)
    test_db_session.flush()

    test_db_session.add(
        PlayerHittingStatsModel(
            player_id=player.id,
            team_id=team.id,
            season=2025,
            game_type="R",
            source="statsapi",
            hits=12,
            plate_appearances=40,
            batting_average=0.3,
        )
    )
    test_db_session.add(
        PlayerGameLogModel(
            player_id=player.id,
            team_id=team.id,
            season=2025,
            game_type="R",
            stat_group="hitting",
            external_reference="123",
            event_date=datetime(2025, 3, 20),
            payload={"hits": 2},
            source="statsapi",
        )
    )
    test_db_session.commit()
    return {"team": team, "player": player}


class TestPlayerStatsRoutesIntegration:
    @pytest.mark.asyncio
    async def test_get_persisted_player_season_stats(self, test_db_session, populated_player_stats_db):
        # Given
        use_cases = _build_use_cases(test_db_session)
        internal_player_id = populated_player_stats_db["player"].id

        # When
        response = await player_stats_routes.get_persisted_player_season_stats(
            player_id=internal_player_id,
            season=2025,
            group="hitting",
            game_type="R",
            use_cases=use_cases,
        )

        # Then
        assert response.status_code == HTTP_200_OK
        body = _decode_response(response)
        assert body["status"] == "success"
        assert body["data"]["stats"] == "season"
        assert body["data"]["records"][0]["metrics"]["hits"] == 12

    @pytest.mark.asyncio
    async def test_get_persisted_player_game_logs(self, test_db_session, populated_player_stats_db):
        # Given
        use_cases = _build_use_cases(test_db_session)
        internal_player_id = populated_player_stats_db["player"].id

        # When
        response = await player_stats_routes.get_persisted_player_game_logs(
            player_id=internal_player_id,
            season=2025,
            group="hitting",
            game_type="R",
            days_back=None,
            limit=None,
            use_cases=use_cases,
        )

        # Then
        assert response.status_code == HTTP_200_OK
        body = _decode_response(response)
        assert body["status"] == "success"
        assert body["data"]["stats"] == "gameLog"
        assert body["data"]["records"][0]["external_reference"] == "123"

    @pytest.mark.asyncio
    async def test_get_persisted_player_season_stats_returns_not_found_for_unknown_player(self, test_db_session):
        # Given
        use_cases = _build_use_cases(test_db_session)

        # When / Then
        with pytest.raises(player_stats_routes.DomainExceptions.PlayerNotFoundError):
            await player_stats_routes.get_persisted_player_season_stats(
                player_id=999999,
                season=2025,
                group="hitting",
                game_type="R",
                use_cases=use_cases,
            )

    @pytest.mark.asyncio
    async def test_ingest_persisted_player_season_stats(self, test_db_session):
        # Given
        use_cases = _build_use_cases(test_db_session)
        use_cases["ingest_season_stats"] = AsyncMock()
        use_cases["ingest_season_stats"].execute.return_value = {
            "operation": "player_stats_seasonal_ingestion",
            "players_processed": 1,
        }

        # When
        response = await player_stats_routes.ingest_persisted_player_season_stats(
            season=2025,
            group="all",
            game_type="R",
            player_id=7,
            team_id=None,
            force_refresh=False,
            use_cases=use_cases,
        )

        # Then
        assert response.status_code == HTTP_201_CREATED
        body = _decode_response(response)
        assert body["status"] == "success"
        assert body["data"]["operation"] == "player_stats_seasonal_ingestion"
