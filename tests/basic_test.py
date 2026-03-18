"""
Pruebas básicas para verificar la funcionalidad del sistema.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.config.settings import settings
from infrastructure.db.database import Base, get_db
from interface.rest.main import app

db_dir = Path(__file__).resolve().parent / "database"
db_dir.mkdir(parents=True, exist_ok=True)
db_path = db_dir / "test.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override para la base de datos de pruebas."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def setup_database():
    """Setup de la base de datos de pruebas."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(setup_database):
    """Cliente de pruebas FastAPI."""
    return TestClient(app)


class TestBasicEndpoints:
    """Pruebas básicas de endpoints."""

    def test_root_endpoint(self, client):
        """Prueba endpoint raíz."""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint(self, client):
        """Prueba endpoint de salud."""
        response = client.get("/api/v1/health")
        # Puede fallar por dependencias externas, pero no debe dar 500
        assert response.status_code in [200, 503]


class TestConfiguration:
    """Pruebas de configuración."""

    def test_settings_load(self):
        """Prueba que la configuración se carga correctamente."""
        assert settings.APP_NAME is not None
        assert settings.DATABASE_URL is not None
        assert settings.REDIS_URL is not None


class TestModelsImport:
    """Pruebas de importación de modelos."""

    def test_database_models_import(self):
        """Prueba que los modelos de base de datos se importen correctamente."""
        from infrastructure.db.models import (
            CatchingStatsModel,
            FieldingStatsModel,
            GameModel,
            HittingStatsModel,
            PitchingStatsModel,
            PlayerModel,
            PredictionModel,
            TeamModel,
        )

        # Verificar que las clases existen
        assert TeamModel is not None
        assert GameModel is not None
        assert HittingStatsModel is not None
        assert PitchingStatsModel is not None
        assert FieldingStatsModel is not None
        assert CatchingStatsModel is not None
        assert PlayerModel is not None
        assert PredictionModel is not None


# Funciones de utilidad para pruebas
def create_test_team():
    """Crea un equipo de prueba."""
    return {
        "mlb_id": 123,
        "name": "Test Team",
        "abbreviation": "TST",
        "city": "Test City",
        "division": "Test Division",
        "league": "Test League",
    }


def create_test_game():
    """Crea un juego de prueba."""
    from datetime import datetime

    return {
        "mlb_game_id": 456,
        "home_team_id": 1,
        "away_team_id": 2,
        "game_date": datetime.now(),
        "status": "scheduled",
    }


if __name__ == "__main__":
    # Ejecutar pruebas básicas
    pytest.main([__file__, "-v"])
