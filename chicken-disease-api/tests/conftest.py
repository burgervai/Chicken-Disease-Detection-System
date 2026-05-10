"""
Test configuration and fixtures
"""
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.database import db_service


@pytest.fixture
async def test_db():
    """Fixture for test database"""
    # Connect to test database
    db_service.client = AsyncIOMotorClient("mongodb://localhost:27017")
    db_service.db = db_service.client["test_chicken_disease"]

    yield db_service.db

    # Cleanup
    await db_service.db.drop_collection("predictions")
    await db_service.db.drop_collection("model_versions")
    db_service.client.close()


@pytest.fixture
def sample_prediction():
    """Fixture for sample prediction data"""
    return {
        "_id": "test_prediction_123",
        "image_hash": "abc123",
        "result": {
            "disease": "healthy",
            "confidence": 0.92,
            "probabilities": {
                "healthy": 0.92,
                "coccidiosis": 0.08,
            },
        },
        "model_version": "1.0.0",
        "processing_time_ms": 150.5,
        "threshold": 0.5,
        "created_at": None,
    }
