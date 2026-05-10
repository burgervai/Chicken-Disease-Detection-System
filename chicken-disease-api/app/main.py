"""
Production-ready FastAPI application for Chicken Disease Classification
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.endpoints import router as api_router
from app.api.websocket import router as websocket_router
from app.services.database import db_service
from app.services.model_registry import model_registry
from app.services.notification import notification_service


structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("application_starting", app_name=settings.APP_NAME, version=settings.APP_VERSION)

    await db_service.connect()
    await model_registry.initialize()
    await notification_service.start()

    logger.info("application_ready")

    yield

    logger.info("application_shutting_down")
    await notification_service.stop()
    await db_service.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready API for Chicken Disease Classification with multi-model support",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/ws")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "models_loaded": model_registry.get_loaded_models_count(),
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Chicken Disease Classification API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
