import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.db.models import Base
from infrastructure.db.repositories.team_stats_repository import TeamStatsRepository


@pytest.fixture(scope="function")
def db_session():
    """Create a temporary in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def team_stats_repo(db_session):
    """Fixture to provide a TeamStatsRepository instance."""
    return TeamStatsRepository(db_session)
