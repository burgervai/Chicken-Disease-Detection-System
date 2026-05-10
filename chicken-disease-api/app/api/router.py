"""
WebSocket API routes
"""
from fastapi import APIRouter, WebSocket, Query
from app.api.websocket import websocket_endpoint

router = APIRouter()


@router.websocket("/")
async def websocket_client(
    websocket: WebSocket,
    client_id: str = Query(default=None),
):
    """
    WebSocket endpoint for real-time notifications.

    Query parameters:
    - **client_id**: Optional client identifier (auto-generated if not provided)
    """
    await websocket_endpoint(websocket, client_id)
