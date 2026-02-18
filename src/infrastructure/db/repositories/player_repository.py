"""
Player repository implementation.
This module implements the PlayerRepositoryPort interface using SQLAlchemy.
"""

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from src.application.ports.player_repository import PlayerRepositoryPort
from src.domain.entities.player import Player
from src.domain.entities.team import Team
from src.infrastructure.db.models import PlayerModel, TeamModel


class PlayerRepository(PlayerRepositoryPort):
    """Implementation of the PlayerRepositoryPort interface using SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, player_id: int) -> Optional[Player]:
        """Get a player by its ID."""
        player_model = (
            self.session.query(PlayerModel)
            .options(joinedload(PlayerModel.current_team))
            .filter(PlayerModel.id == player_id)
            .first()
        )
        if not player_model:
            return None
        return self._model_to_entity(player_model)

    async def get_by_mlb_id(self, mlb_id: int) -> Optional[Player]:
        """Get a player by its MLB ID."""
        player_model = (
            self.session.query(PlayerModel)
            .options(joinedload(PlayerModel.current_team))
            .filter(PlayerModel.mlb_id == mlb_id)
            .first()
        )
        if not player_model:
            return None
        return self._model_to_entity(player_model)

    async def list_by_team(self, team_id: int) -> List[Player]:
        """List players by team."""
        player_models = (
            self.session.query(PlayerModel)
            .options(joinedload(PlayerModel.current_team))
            .filter(PlayerModel.current_team_id == team_id)
            .all()
        )
        return [self._model_to_entity(model) for model in player_models]

    async def list_by_position(self, position: str) -> List[Player]:
        """List players by position."""
        player_models = (
            self.session.query(PlayerModel)
            .options(joinedload(PlayerModel.current_team))
            .filter(PlayerModel.position == position)
            .all()
        )
        return [self._model_to_entity(model) for model in player_models]

    async def list_active_players(self) -> List[Player]:
        """List all active players."""
        player_models = (
            self.session.query(PlayerModel)
            .options(joinedload(PlayerModel.current_team))
            .filter(PlayerModel.active)
            .all()
        )
        return [self._model_to_entity(model) for model in player_models]

    async def list_players(
        self,
        team_id: Optional[int] = None,
        position: Optional[str] = None,
        name: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Player]:
        """List players applying optional filters and deterministic pagination."""
        query = self.session.query(PlayerModel).options(joinedload(PlayerModel.current_team))

        if team_id is not None:
            query = query.filter(PlayerModel.current_team_id == team_id)

        if position:
            query = query.filter(PlayerModel.position.ilike(position.strip()))

        if active is not None:
            query = query.filter(PlayerModel.active == active)

        if name:
            normalized_name = name.strip()
            search_terms = normalized_name.split()
            if len(search_terms) == 1:
                search_term = f"%{search_terms[0]}%"
                query = query.filter(
                    or_(
                        PlayerModel.first_name.ilike(search_term),
                        PlayerModel.last_name.ilike(search_term),
                    )
                )
            else:
                first_name_term = f"%{search_terms[0]}%"
                last_name_term = f"%{' '.join(search_terms[1:])}%"
                query = query.filter(
                    PlayerModel.first_name.ilike(first_name_term),
                    PlayerModel.last_name.ilike(last_name_term),
                )

        player_models = query.order_by(PlayerModel.id.asc()).offset(offset).limit(limit).all()
        return [self._model_to_entity(model) for model in player_models]

    async def search_by_name(self, name: str) -> List[Player]:
        """Search players by name."""
        # Split the name to search in both first and last name
        search_terms = name.split()

        if len(search_terms) == 1:
            # Search in both first and last name
            search_term = f"%{search_terms[0]}%"
            player_models = (
                self.session.query(PlayerModel)
                .options(joinedload(PlayerModel.current_team))
                .filter(
                    or_(
                        PlayerModel.first_name.ilike(search_term),
                        PlayerModel.last_name.ilike(search_term),
                    )
                )
                .all()
            )
        else:
            # Try to match first and last name
            first_name_term = f"%{search_terms[0]}%"
            last_name_term = f"%{' '.join(search_terms[1:])}%"
            player_models = (
                self.session.query(PlayerModel)
                .options(joinedload(PlayerModel.current_team))
                .filter(
                    PlayerModel.first_name.ilike(first_name_term),
                    PlayerModel.last_name.ilike(last_name_term),
                )
                .all()
            )

        return [self._model_to_entity(model) for model in player_models]

    async def save(self, player: Player) -> Player:
        """Save a player (create or update)."""
        # Check if player already exists
        if player.id:
            player_model = self.session.query(PlayerModel).filter(PlayerModel.id == player.id).first()
            if player_model:
                # Update existing player
                self._update_player_model(player_model, player)
                self.session.commit()
                return await self.get_by_id(player_model.id)

        # Check if player exists by MLB ID
        player_model = self.session.query(PlayerModel).filter(PlayerModel.mlb_id == player.mlb_id).first()
        if player_model:
            # Update existing player
            self._update_player_model(player_model, player)
            self.session.commit()
            return await self.get_by_id(player_model.id)

        # Create new player
        player_model = PlayerModel(
            mlb_id=player.mlb_id,
            first_name=player.first_name,
            last_name=player.last_name,
            position=player.position,
            bats=player.bats,
            throws=player.throws,
            birth_date=player.birth_date,
            active=player.active,
            current_team_id=player.current_team_id,
        )
        self.session.add(player_model)
        self.session.commit()
        self.session.refresh(player_model)
        return await self.get_by_id(player_model.id)

    async def update_team(self, player_id: int, team_id: Optional[int]) -> Optional[Player]:
        """Update a player's team."""
        player_model = self.session.query(PlayerModel).filter(PlayerModel.id == player_id).first()
        if not player_model:
            return None

        player_model.current_team_id = team_id
        self.session.commit()
        return await self.get_by_id(player_id)

    async def delete(self, player_id: int) -> bool:
        """Delete a player by its ID."""
        player_model = self.session.query(PlayerModel).filter(PlayerModel.id == player_id).first()
        if not player_model:
            return False
        self.session.delete(player_model)
        self.session.commit()
        return True

    def _update_player_model(self, model: PlayerModel, entity: Player) -> None:
        """Update a PlayerModel with values from a Player entity."""
        model.mlb_id = entity.mlb_id
        model.first_name = entity.first_name
        model.last_name = entity.last_name
        model.position = entity.position
        model.bats = entity.bats
        model.throws = entity.throws
        model.birth_date = entity.birth_date
        model.active = entity.active
        model.current_team_id = entity.current_team_id

    def _model_to_entity(self, model: PlayerModel) -> Player:
        """Convert a PlayerModel to a Player entity."""
        player = Player(
            id=model.id,
            mlb_id=model.mlb_id,
            first_name=model.first_name,
            last_name=model.last_name,
            position=model.position,
            bats=model.bats,
            throws=model.throws,
            birth_date=model.birth_date,
            active=model.active,
            current_team_id=model.current_team_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

        # Set related team if loaded
        if hasattr(model, "current_team") and model.current_team:
            player.current_team = self._team_model_to_entity(model.current_team)

        return player

    def _team_model_to_entity(self, model: TeamModel) -> Team:
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
