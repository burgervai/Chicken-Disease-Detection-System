"""
MongoDB database service
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class DatabaseService:
    """MongoDB database service with async operations"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self):
        """Connect to MongoDB"""
        logger.info("connecting_to_mongodb", url=settings.MONGODB_URL)
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB_NAME]

        # Create indexes
        await self._create_indexes()
        logger.info("mongodb_connected", database=settings.MONGODB_DB_NAME)

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("mongodb_disconnected")

    async def _create_indexes(self):
        """Create database indexes for optimized queries"""
        # Predictions collection indexes
        await self.db.predictions.create_index("created_at")
        await self.db.predictions.create_index("model_version")
        await self.db.predictions.create_index("user_id")
        await self.db.predictions.create_index([("user_id", 1), ("created_at", -1)])

        # Model versions collection indexes
        await self.db.model_versions.create_index("version", unique=True)
        await self.db.model_versions.create_index("is_active")

        # Users collection indexes
        await self.db.users.create_index("email", unique=True)

        logger.info("database_indexes_created")

    @property
    def predictions(self):
        """Get predictions collection"""
        return self.db.predictions

    @property
    def model_versions(self):
        """Get model_versions collection"""
        return self.db.model_versions

    @property
    def users(self):
        """Get users collection"""
        return self.db.users

    @property
    def logs(self):
        """Get logs collection"""
        return self.db.logs


# Global database service instance
db_service = DatabaseService()
