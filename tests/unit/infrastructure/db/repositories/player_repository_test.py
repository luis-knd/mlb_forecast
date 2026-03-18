from datetime import datetime

import pytest

from domain.entities.player import Player
from infrastructure.db.repositories.player_repository import PlayerRepository


class TestPlayerRepository:
    @pytest.mark.asyncio
    async def test_save_preserves_existing_profile_fields_when_incoming_values_are_missing(self, db_session):
        # Given
        repository = PlayerRepository(db_session)
        saved_player = await repository.save(
            Player.create(
                mlb_id=660271,
                first_name="Shohei",
                last_name="Ohtani",
                position="DH",
                bats="L",
                throws="R",
                birth_date=datetime(1994, 7, 5),
                active=True,
            )
        )

        # When
        updated_player = await repository.save(
            Player.create(
                mlb_id=saved_player.mlb_id,
                first_name="Shohei",
                last_name="Ohtani",
                position="   ",
                bats=None,
                throws="",
                birth_date=None,
                active=True,
            )
        )

        # Then
        assert updated_player is not None
        assert updated_player.position == "DH"
        assert updated_player.bats == "L"
        assert updated_player.throws == "R"
        assert updated_player.birth_date == datetime(1994, 7, 5)

    @pytest.mark.asyncio
    async def test_save_updates_profile_fields_when_incoming_values_are_present(self, db_session):
        # Given
        repository = PlayerRepository(db_session)
        saved_player = await repository.save(
            Player.create(
                mlb_id=700000,
                first_name="Player",
                last_name="One",
                position="SS",
                bats="R",
                throws="R",
                birth_date=datetime(1990, 1, 1),
                active=True,
            )
        )

        # When
        updated_player = await repository.save(
            Player.create(
                mlb_id=saved_player.mlb_id,
                first_name="Player",
                last_name="One",
                position="OF",
                bats="S",
                throws="L",
                birth_date=datetime(1991, 2, 2),
                active=True,
            )
        )

        # Then
        assert updated_player is not None
        assert updated_player.position == "OF"
        assert updated_player.bats == "S"
        assert updated_player.throws == "L"
        assert updated_player.birth_date == datetime(1991, 2, 2)
