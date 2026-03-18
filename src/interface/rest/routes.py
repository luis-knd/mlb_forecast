from fastapi import APIRouter

from interface.rest.data_ingestion_routes import router as data_ingestion_router
from interface.rest.game_routes import router as game_router
from interface.rest.player_routes import router as player_router
from interface.rest.prediction_routes import router as prediction_router
from interface.rest.system_routes import router as system_router
from interface.rest.team_routes import router as team_router
from interface.rest.team_stats_retrieval_routes import router as team_stats_retrieval_router
from interface.rest.team_stats_routes import router as team_stats_ingestion_router

router = APIRouter()
router.include_router(team_router, tags=["Teams"])
router.include_router(team_stats_retrieval_router, tags=["Teams", "Stats"])
router.include_router(game_router, tags=["Games"])
router.include_router(player_router, tags=["Players"])
router.include_router(prediction_router, tags=["Predictions"])
router.include_router(system_router, tags=["System"])
router.include_router(data_ingestion_router, tags=["Data Ingestion"])
router.include_router(team_stats_ingestion_router, tags=["Teams", "Stats", "Data Ingestion"])
