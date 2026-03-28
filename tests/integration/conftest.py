from contextlib import ExitStack, asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from application.use_cases.game_use_cases import IngestGamesUseCase, ListUpcomingGamesUseCase
from application.use_cases.player_use_cases import IngestPlayersBySourceUseCase
from domain.entities.game import Game
from domain.entities.player import Player
from domain.entities.team import Team
from domain.exceptions import InvalidDataError, TeamNotFoundError
from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.db.database import Base, get_db
from infrastructure.db.models import GameModel, PlayerModel, TeamModel
from infrastructure.db.repositories.game_repository import GameRepository
from infrastructure.db.repositories.player_repository import PlayerRepository
from infrastructure.db.repositories.team_repository import TeamRepository
from infrastructure.mlb_api.adapter import MLBApiAdapter
from interface.rest.game_routes import get_game_use_cases
from interface.rest.main import app
from interface.rest.player_routes import get_player_use_cases

db_dir = Path(__file__).resolve().parents[1] / "database"
db_dir.mkdir(parents=True, exist_ok=True)
db_path = db_dir / "test.db"
TEST_DATABASE_URL = f"sqlite:///{db_path}"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _team_model_to_entity(team_model: TeamModel | None) -> Team | None:
    if team_model is None:
        return None

    return Team(
        id=team_model.id,
        mlb_id=team_model.mlb_id,
        name=team_model.name,
        abbreviation=team_model.abbreviation,
        city=team_model.city,
        division=team_model.division,
        league=team_model.league,
        venue_name=team_model.venue_name,
        created_at=team_model.created_at,
        updated_at=team_model.updated_at,
    )


def _player_model_to_entity(session, player_model: PlayerModel) -> Player:
    current_team = session.query(TeamModel).filter(TeamModel.id == player_model.current_team_id).first()

    return Player(
        id=player_model.id,
        mlb_id=player_model.mlb_id,
        first_name=player_model.first_name,
        last_name=player_model.last_name,
        position=player_model.position,
        bats=player_model.bats,
        throws=player_model.throws,
        birth_date=player_model.birth_date,
        active=player_model.active,
        current_team_id=player_model.current_team_id,
        created_at=player_model.created_at,
        updated_at=player_model.updated_at,
        current_team=_team_model_to_entity(current_team),
    )


def _game_model_to_entity(session, game_model: GameModel) -> Game:
    home_team = session.query(TeamModel).filter(TeamModel.id == game_model.home_team_id).first()
    away_team = session.query(TeamModel).filter(TeamModel.id == game_model.away_team_id).first()
    winning_team = None
    if game_model.winning_team_id is not None:
        winning_team = session.query(TeamModel).filter(TeamModel.id == game_model.winning_team_id).first()

    return Game(
        id=game_model.id,
        mlb_game_id=game_model.mlb_game_id,
        home_team_id=game_model.home_team_id,
        away_team_id=game_model.away_team_id,
        game_date=game_model.game_date,
        status=game_model.status,
        scheduled_innings=game_model.scheduled_innings,
        home_score=game_model.home_score,
        away_score=game_model.away_score,
        winning_team_id=game_model.winning_team_id,
        created_at=game_model.created_at,
        updated_at=game_model.updated_at,
        home_team=_team_model_to_entity(home_team),
        away_team=_team_model_to_entity(away_team),
        winning_team=_team_model_to_entity(winning_team),
    )


class IntegrationListPlayersUseCase:
    async def execute(
        self,
        team_id: int | None = None,
        position: str | None = None,
        name: str | None = None,
        active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Player]:
        session = TestSessionLocal()
        try:
            query = session.query(PlayerModel)

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
                    query = query.filter(
                        PlayerModel.first_name.ilike(f"%{search_terms[0]}%"),
                        PlayerModel.last_name.ilike(f"%{' '.join(search_terms[1:])}%"),
                    )

            player_models = query.order_by(PlayerModel.id.asc()).offset(offset).limit(limit).all()
            return [_player_model_to_entity(session, player_model) for player_model in player_models]
        finally:
            session.close()


class IntegrationGetPlayerUseCase:
    async def execute(self, player_id: int) -> Player | None:
        session = TestSessionLocal()
        try:
            player_model = session.query(PlayerModel).filter(PlayerModel.id == player_id).first()
            if player_model is None:
                return None
            return _player_model_to_entity(session, player_model)
        finally:
            session.close()


class IntegrationGetPlayerByMlbIdUseCase:
    async def execute(self, mlb_player_id: int) -> Player | None:
        session = TestSessionLocal()
        try:
            player_model = session.query(PlayerModel).filter(PlayerModel.mlb_id == mlb_player_id).first()
            if player_model is None:
                return None
            return _player_model_to_entity(session, player_model)
        finally:
            session.close()


class IntegrationGetTeamUseCase:
    async def execute(self, team_id: int) -> Team:
        if team_id <= 0:
            raise InvalidDataError("Invalid team ID. Must be a positive integer")

        session = TestSessionLocal()
        try:
            team_model = session.query(TeamModel).filter(TeamModel.id == team_id).first()
            if team_model is None:
                raise TeamNotFoundError(team_id)
            return _team_model_to_entity(team_model)
        finally:
            session.close()


class IntegrationListGamesUseCase:
    async def execute(
        self,
        game_date: date | None = None,
        team_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Game]:
        session = TestSessionLocal()
        try:
            query = session.query(GameModel)

            if game_date is not None:
                start_date = datetime.combine(game_date, datetime.min.time())
                end_date = datetime.combine(game_date, datetime.max.time())
                query = query.filter(GameModel.game_date.between(start_date, end_date))
            elif team_id is not None:
                query = query.filter(or_(GameModel.home_team_id == team_id, GameModel.away_team_id == team_id))
            elif status:
                query = query.filter(GameModel.status == status)
            else:
                today = datetime.now().date()
                end_date = today + timedelta(days=7)
                query = query.filter(
                    GameModel.game_date >= datetime.combine(today, datetime.min.time()),
                    GameModel.game_date <= datetime.combine(end_date, datetime.max.time()),
                    GameModel.status.in_(["scheduled", "in_progress"]),
                )

            game_models = query.order_by(GameModel.game_date.asc()).limit(limit).all()
            return [_game_model_to_entity(session, game_model) for game_model in game_models]
        finally:
            session.close()


class IntegrationGetGameUseCase:
    async def execute(self, game_id: int) -> Game | None:
        session = TestSessionLocal()
        try:
            game_model = session.query(GameModel).filter(GameModel.id == game_id).first()
            if game_model is None:
                return None
            return _game_model_to_entity(session, game_model)
        finally:
            session.close()


@pytest.fixture(autouse=True)
def setup_test_database():
    """Setup and teardown test database for each test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_db_session():
    """Create a test database session."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_cache_for_integration():
    """Mock cache adapter for integration tests."""
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None  # Always miss cache to test real logic
    mock_cache.set.return_value = None
    mock_cache.clear.return_value = None
    mock_cache.delete.return_value = None
    mock_cache.exists.return_value = False
    mock_cache.get_many.return_value = {}
    mock_cache.connect.return_value = None
    mock_cache.disconnect.return_value = None
    mock_cache.redis_client = object()
    mock_cache.connection_pool = None
    return mock_cache


def override_get_db():
    """Override the get_db dependency for testing."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def integration_client(mock_cache_for_integration):
    """Create a test client with real database for integration tests."""

    async def override_player_use_cases():
        db = TestSessionLocal()
        player_repository = PlayerRepository(db)
        team_repository = TeamRepository(db)
        mlb_api_adapter = MLBApiAdapter()

        return {
            "list_players": IntegrationListPlayersUseCase(),
            "get_player": IntegrationGetPlayerUseCase(),
            "get_team": IntegrationGetTeamUseCase(),
            "get_player_by_mlb_id": IntegrationGetPlayerByMlbIdUseCase(),
            "ingest_players_by_source": IngestPlayersBySourceUseCase(
                player_repository,
                team_repository,
                mlb_api_adapter,
                mock_cache_for_integration,
            ),
        }

    async def override_game_use_cases():
        db = TestSessionLocal()
        game_repository = GameRepository(db)
        team_repository = TeamRepository(db)
        mlb_api_adapter = MLBApiAdapter()

        return {
            "list_games": IntegrationListGamesUseCase(),
            "get_game": IntegrationGetGameUseCase(),
            "ingest_games": IngestGamesUseCase(
                game_repository,
                team_repository,
                mlb_api_adapter,
                mock_cache_for_integration,
            ),
            "list_upcoming_games": ListUpcomingGamesUseCase(game_repository, mock_cache_for_integration),
        }

    # Override database dependency
    with ExitStack():
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_cache_adapter] = lambda: mock_cache_for_integration
        app.dependency_overrides[get_player_use_cases] = override_player_use_cases
        app.dependency_overrides[get_game_use_cases] = override_game_use_cases

        # Override lifespan to prevent startup logic (DB connection, Cache, ML load)
        @asynccontextmanager
        async def dummy_lifespan(app):
            yield

        original_lifespan = app.router.lifespan_context
        app.router.lifespan_context = dummy_lifespan

        try:
            test_client = TestClient(app)
            yield test_client
        finally:
            app.router.lifespan_context = original_lifespan
            test_client.close()

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def test_teams_data():
    """
    Create strategic test team data that will expose the filtering bug.

    This data is designed to test edge cases in filtering:
    - Teams with similar league names but different exact matches
    - Teams that should match both league and division filters
    - Teams that should only match one filter
    """
    return [
        {
            "mlb_id": 133,
            "name": "Oakland Athletics",
            "abbreviation": "OAK",
            "city": "Oakland",
            "division": "American League West",
            "league": "American League",
            "venue_name": "Oakland Coliseum",
        },
        {
            "mlb_id": 136,
            "name": "Seattle Mariners",
            "abbreviation": "SEA",
            "city": "Seattle",
            "division": "American League West",
            "league": "American League",
            "venue_name": "T-Mobile Park",
        },
        {
            "mlb_id": 147,
            "name": "New York Yankees",
            "abbreviation": "NYY",
            "city": "New York",
            "division": "American League East",
            "league": "American League",
            "venue_name": "Yankee Stadium",
        },
        {
            "mlb_id": 119,
            "name": "Los Angeles Dodgers",
            "abbreviation": "LAD",
            "city": "Los Angeles",
            "division": "National League West",
            "league": "National League",
            "venue_name": "Dodger Stadium",
        },
        {
            "mlb_id": 137,
            "name": "San Francisco Giants",
            "abbreviation": "SF",
            "city": "San Francisco",
            "division": "National League West",
            "league": "National League",
            "venue_name": "Oracle Park",
        },
        {
            "mlb_id": 121,
            "name": "New York Mets",
            "abbreviation": "NYM",
            "city": "New York",
            "division": "National League East",
            "league": "National League",
            "venue_name": "Citi Field",
        },
    ]


@pytest.fixture
def populated_test_db(test_db_session, test_teams_data):
    """Populate test database with team data."""
    teams = []
    for team_data in test_teams_data:
        team_model = TeamModel(**team_data)
        test_db_session.add(team_model)
        teams.append(team_model)

    test_db_session.commit()

    # Refresh to get the assigned IDs
    for team in teams:
        test_db_session.refresh(team)

    return teams
