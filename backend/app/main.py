from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.logger import get_logger
from app.api.router import api_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENV)

    # Initialise database — create tables (including pgvector extension check)
    from app.db.database import engine
    from app.db import models  # noqa: F401 — registers all ORM models with Base

    try:
        async with engine.begin() as conn:
            # Enable pgvector extension before creating tables
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("Database tables ready")
    except Exception as exc:
        logger.warning("DB init failed (is PostgreSQL running?): %s", exc)

    # Initialise Neo4j — graceful degradation if not running
    from app.graph.neo4j_client import neo4j_client
    try:
        await neo4j_client.connect()
    except Exception as exc:
        logger.warning("Neo4j unavailable (graph features disabled): %s", exc)

    yield

    logger.info("Shutting down %s", settings.APP_NAME)
    from app.db.database import engine as _engine
    await _engine.dispose()
    await neo4j_client.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered ontology-based knowledge graph builder",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routes registered under /api via central router
app.include_router(api_router, prefix="/api")
