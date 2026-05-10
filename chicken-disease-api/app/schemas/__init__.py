"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DiseaseClass(str, Enum):
    """Disease classification classes"""
    HEALTHY = "healthy"
    COCCIDIOSIS = "coccidiosis"
    SALMONELLOSIS = "salmonellosis"
    NEWCASTLE_DISEASE = "newcastle_disease"
    BIRD_FLU = "bird_flu"
    UNKNOWN = "unknown"


class ModelStatus(str, Enum):
    """Model loading status"""
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    UNLOADED = "unloaded"




class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """User response schema"""
    id: str
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True




class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse




class PredictionRequest(BaseModel):
    """Prediction request schema"""
    image: str = Field(..., description="Base64 encoded image")
    model_version: Optional[str] = Field(None, description="Specific model version to use")
    threshold: float = Field(0.5, ge=0.0, le=1.0, description="Confidence threshold")


class PredictionResult(BaseModel):
    """Single prediction result"""
    disease: DiseaseClass
    confidence: float = Field(..., ge=0.0, le=1.0)
    probabilities: dict = Field(default_factory=dict)


class PredictionResponse(BaseModel):
    """Prediction response schema"""
    id: str
    result: PredictionResult
    model_version: str
    processing_time_ms: float
    created_at: datetime


class PredictionHistoryResponse(BaseModel):
    """Prediction history response"""
    predictions: List[PredictionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int



class ModelInfo(BaseModel):
    """Model information schema"""
    version: str
    name: str
    description: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_date: datetime
    dataset_size: int
    classes: List[str]
    is_active: bool
    status: ModelStatus


class ModelUploadResponse(BaseModel):
    """Model upload response"""
    version: str
    message: str
    metrics: Optional[dict] = None


# ============ WebSocket Schemas ============

class WebSocketMessage(BaseModel):
    """WebSocket message schema"""
    type: str  # prediction_complete, model_updated, error
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NotificationPayload(BaseModel):
    """Notification payload"""
    title: str
    message: str
    type: str = "info"  # info, success, warning, error
    prediction_id: Optional[str] = None



class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    code: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    app_name: str
    version: str
    models_loaded: int
    mongodb_connected: bool = True
