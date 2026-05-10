"""
Unit tests for prediction endpoint
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self):
        """Test health endpoint returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data


class TestPredictionEndpoint:
    """Test prediction endpoint"""

    def test_predict_no_file(self):
        """Test prediction with no file returns error"""
        response = client.post("/api/v1/predict")
        assert response.status_code == 422  # Validation error

    def test_predict_invalid_file_type(self):
        """Test prediction with invalid file type"""
        # Create a test file with invalid extension
        files = {"image": ("test.txt", b"not an image", "text/plain")}
        response = client.post("/api/v1/predict", files=files)
        assert response.status_code == 400


class TestModelsEndpoint:
    """Test models endpoint"""

    def test_list_models(self):
        """Test listing all available models"""
        response = client.get("/api/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_active_model(self):
        """Test getting active model info"""
        response = client.get("/api/v1/models/active")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "name" in data
