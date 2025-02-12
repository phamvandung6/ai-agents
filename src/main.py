import logging
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core._api import LangChainBetaWarning
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.agents import get_agent, get_all_agent_info
from src.api.v1 import api_router
from src.core.logging import setup_logging
from src.core.settings import settings
from src.database import DATABASE_URL
from src.database.connection import engine
from src.database.models import Base

# Suppress warnings
warnings.filterwarnings("ignore", category=LangChainBetaWarning)
logger = logging.getLogger(__name__)

# Convert SQLAlchemy URL to PostgreSQL URL
# From: postgresql+asyncpg://user:pass@host:port/dbname
# To:   postgresql://user:pass@host:port/dbname
POSTGRES_URL = DATABASE_URL.replace("+asyncpg", "")

# Postgres connection settings
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up...")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Initialize connection pool for agent checkpoints
    async with AsyncConnectionPool(
        conninfo=POSTGRES_URL,
        max_size=20,
        kwargs=connection_kwargs,
    ) as pool:
        # Initialize checkpointer
        checkpointer = AsyncPostgresSaver(pool)

        # Setup checkpointer tables if not exists
        await checkpointer.setup()
        logger.info("Agent checkpointer tables initialized")

        # Initialize agents with checkpointer
        agents = get_all_agent_info()
        for a in agents:
            agent = get_agent(a.key)
            agent.checkpointer = checkpointer
        logger.info("Agent checkpointers configured")

        yield

    # Shutdown
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title="AI Agent API",
        description="AI Agent API with Authentication",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.MODE == "dev",
        reload_dirs=["/app/src"],
        reload_includes=["*.py"],
        reload_excludes=["*.pyc", "__pycache__"],
        log_level="info",
    )
