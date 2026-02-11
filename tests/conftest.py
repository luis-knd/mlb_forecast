import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models import Base
from src.infrastructure.db.repositories.team_stats_repository import TeamStatsRepository


@pytest.fixture(scope="function")
def db_session():
    """Create a temporary in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def team_stats_repo(db_session):
    """Fixture to provide a TeamStatsRepository instance."""
    return TeamStatsRepository(db_session)
