from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.cache.cache_provider import get_cache_adapter
from infrastructure.db.database import Base, get_db
from infrastructure.db.models import TeamModel
from interface.rest.main import app

db_dir = Path(__file__).resolve().parents[1] / "database"
db_dir.mkdir(parents=True, exist_ok=True)
db_path = db_dir / "test.db"
TEST_DATABASE_URL = f"sqlite:///{db_path}"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_database():
    """Setup and teardown test database for each test."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Drop all tables after test
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
    # Override database dependency
    with ExitStack():
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_cache_adapter] = lambda: mock_cache_for_integration

        # Override lifespan to prevent startup logic (DB connection, Cache, ML load)
        @asynccontextmanager
        async def dummy_lifespan(app):
            yield

        original_lifespan = app.router.lifespan_context
        app.router.lifespan_context = dummy_lifespan

        try:
            with TestClient(app) as test_client:
                yield test_client
        finally:
            app.router.lifespan_context = original_lifespan

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
