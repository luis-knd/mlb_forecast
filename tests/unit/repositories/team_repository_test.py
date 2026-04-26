from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from domain.entities.team import Team
from infrastructure.db.repositories.team_repository import TeamRepository


class TestTeamRepository:
    @pytest.fixture
    def session(self):
        return MagicMock()

    @pytest.fixture
    def repository(self, session):
        return TeamRepository(session)

    @staticmethod
    def _team_model(team_id: int, mlb_id: int, name: str = "Team") -> SimpleNamespace:
        now = datetime(2026, 1, 1)
        return SimpleNamespace(
            id=team_id,
            mlb_id=mlb_id,
            name=name,
            abbreviation="TST",
            city="City",
            division="Division",
            league="League",
            venue_name="Venue",
            created_at=now,
            updated_at=now,
        )

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(self, repository, session):
        # Given
        session.query.return_value.filter.return_value.first.return_value = None

        # When
        result = await repository.get_by_id(999)

        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_mlb_id_returns_entity(self, repository, session):
        # Given
        session.query.return_value.filter.return_value.first.return_value = self._team_model(1, 133, "Athletics")

        # When
        result = await repository.get_by_mlb_id(133)

        # Then
        assert result is not None
        assert result.name == "Athletics"

    @pytest.mark.asyncio
    async def test_list_methods_map_entities(self, repository, session):
        # Given
        teams = [self._team_model(1, 100), self._team_model(2, 200)]
        session.query.return_value.all.return_value = teams
        session.query.return_value.filter.return_value.all.return_value = teams

        # When
        all_teams = await repository.list_all()
        by_league = await repository.list_by_league("League")
        by_division = await repository.list_by_division("Division")
        by_both = await repository.list_by_league_and_division("League", "Division")

        # Then
        assert len(all_teams) == 2
        assert len(by_league) == 2
        assert len(by_division) == 2
        assert len(by_both) == 2

    @pytest.mark.asyncio
    async def test_save_updates_existing_team_by_id(self, repository, session):
        # Given
        model = self._team_model(1, 133, "Old")
        session.query.return_value.filter.return_value.first.side_effect = [model]
        entity = Team.create(133, "New", "NEW", "City", "Division", "League", "Venue")
        entity.id = 1

        # When
        result = await repository.save(entity)

        # Then
        assert result.name == "New"
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_updates_existing_team_by_mlb_id(self, repository, session):
        # Given
        model = self._team_model(1, 133, "Old")
        session.query.return_value.filter.return_value.first.side_effect = [None, model]
        entity = Team.create(133, "Updated", "UPD", "City", "Division", "League", "Venue")

        # When
        result = await repository.save(entity)

        # Then
        assert result.name == "Updated"
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_creates_new_team_when_not_existing(self, repository, session):
        # Given
        session.query.return_value.filter.return_value.first.side_effect = [None]
        entity = Team.create(133, "Create", "CRT", "City", "Division", "League", "Venue")

        # When
        result = await repository.save(entity)

        # Then
        assert result.mlb_id == 133
        session.add.assert_called_once()
        session.commit.assert_called_once()
        session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_returns_true_only_when_team_exists(self, repository, session):
        # Given
        model = self._team_model(1, 133)
        session.query.return_value.filter.return_value.first.side_effect = [model, None]

        # When
        deleted = await repository.delete(1)
        deleted_missing = await repository.delete(2)

        # Then
        assert deleted is True
        assert deleted_missing is False
        session.delete.assert_called_once_with(model)
