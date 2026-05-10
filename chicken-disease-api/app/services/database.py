"""
PostgreSQL database service
"""
from typing import Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = structlog.get_logger()


class DatabaseService:
    """PostgreSQL database service with async SQLAlchemy operations"""

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def _get_database_url(self) -> str:
        """Convert Render PostgreSQL URL to asyncpg-compatible SQLAlchemy URL"""
        database_url = settings.DATABASE_URL

        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1,
            )

        return database_url

    async def connect(self):
        """Connect to PostgreSQL"""
        logger.info("connecting_to_postgresql")

        self.engine = create_async_engine(
            self._get_database_url(),
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        await self._create_tables()

        logger.info("postgresql_connected")

    async def disconnect(self):
        """Disconnect from PostgreSQL"""
        if self.engine:
            await self.engine.dispose()
            logger.info("postgresql_disconnected")

    async def _create_tables(self):
        """Create basic tables if they do not exist"""
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS predictions (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255),
                        model_version VARCHAR(50),
                        prediction VARCHAR(255),
                        confidence FLOAT,
                        image_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS model_versions (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(50) UNIQUE NOT NULL,
                        is_active BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        hashed_password TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS logs (
                        id SERIAL PRIMARY KEY,
                        level VARCHAR(50),
                        message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

        logger.info("database_tables_created")

    def get_session(self) -> AsyncSession:
        """Get a database session"""
        if not self.session_factory:
            raise RuntimeError("Database is not connected")
        return self.session_factory()


db_service = DatabaseService()
