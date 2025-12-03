"""
Team repository implementation.
This module implements the TeamRepositoryPort interface using SQLAlchemy.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.application.ports.team_repository import TeamRepositoryPort
from src.domain.entities.team import Team
from src.infrastructure.db.models import TeamModel


class TeamRepository(TeamRepositoryPort):
    """Implementation of the TeamRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, team_id: int) -> Optional[Team]:
        """Get a team by its ID."""
        team_model = self.session.query(TeamModel).filter(TeamModel.id == team_id).first()
        if not team_model:
            return None
        return self._model_to_entity(team_model)

    async def get_by_mlb_id(self, mlb_id: int) -> Optional[Team]:
        """Get a team by its MLB ID."""
        team_model = self.session.query(TeamModel).filter(TeamModel.mlb_id == mlb_id).first()
        if not team_model:
            return None
        return self._model_to_entity(team_model)

    async def list_all(self) -> List[Team]:
        """List all teams."""
        team_models = self.session.query(TeamModel).all()
        return [self._model_to_entity(team_model) for team_model in team_models]

    async def list_by_league(self, league: str) -> List[Team]:
        """List teams by league."""
        team_models = self.session.query(TeamModel).filter(TeamModel.league.ilike(f"%{league}%")).all()
        return [self._model_to_entity(team_model) for team_model in team_models]

    async def list_by_division(self, division: str) -> List[Team]:
        """List teams by division."""
        team_models = self.session.query(TeamModel).filter(TeamModel.division.ilike(f"%{division}%")).all()
        return [self._model_to_entity(team_model) for team_model in team_models]

    async def list_by_league_and_division(self, league: str, division: str) -> List[Team]:
        """List teams by league and division."""
        team_models = (
            self.session.query(TeamModel)
            .filter(TeamModel.league.ilike(f"%{league}%"), TeamModel.division.ilike(f"%{division}%"))
            .all()
        )
        return [self._model_to_entity(team_model) for team_model in team_models]

    async def save(self, team: Team) -> Team:
        """Save a team (create or update)."""
        # Check if team already exists
        if team.id:
            team_model = self.session.query(TeamModel).filter(TeamModel.id == team.id).first()
            if team_model:
                # Update existing team
                team_model.mlb_id = team.mlb_id
                team_model.name = team.name
                team_model.abbreviation = team.abbreviation
                team_model.city = team.city
                team_model.division = team.division
                team_model.league = team.league
                team_model.venue_name = team.venue_name
                self.session.commit()
                return self._model_to_entity(team_model)

        # Check if team exists by MLB ID
        team_model = self.session.query(TeamModel).filter(TeamModel.mlb_id == team.mlb_id).first()
        if team_model:
            # Update existing team
            team_model.name = team.name
            team_model.abbreviation = team.abbreviation
            team_model.city = team.city
            team_model.division = team.division
            team_model.league = team.league
            team_model.venue_name = team.venue_name
            self.session.commit()
            return self._model_to_entity(team_model)

        # Create new team
        team_model = TeamModel(
            mlb_id=team.mlb_id,
            name=team.name,
            abbreviation=team.abbreviation,
            city=team.city,
            division=team.division,
            league=team.league,
            venue_name=team.venue_name,
        )
        self.session.add(team_model)
        self.session.commit()
        self.session.refresh(team_model)
        return self._model_to_entity(team_model)

    async def delete(self, team_id: int) -> bool:
        """Delete a team by its ID."""
        team_model = self.session.query(TeamModel).filter(TeamModel.id == team_id).first()
        if not team_model:
            return False
        self.session.delete(team_model)
        self.session.commit()
        return True

    def _model_to_entity(self, model: TeamModel) -> Team:
        """Convert a TeamModel to a Team entity."""
        return Team(
            id=model.id,
            mlb_id=model.mlb_id,
            name=model.name,
            abbreviation=model.abbreviation,
            city=model.city,
            division=model.division,
            league=model.league,
            venue_name=model.venue_name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
