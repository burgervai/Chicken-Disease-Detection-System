"""
API module
"""
from app.api.endpoints import router
from app.api.router import router as websocket_router

__all__ = ["router", "websocket_router"]
