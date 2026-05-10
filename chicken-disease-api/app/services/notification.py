"""
WebSocket notification service for real-time updates
"""
from typing import Dict, Set, Optional
from datetime import datetime
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and store a WebSocket connection"""
        await websocket.accept()

        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()

        self.active_connections[client_id].add(websocket)
        logger.info("websocket_connected", client_id=client_id)

    def disconnect(self, websocket: WebSocket, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info("websocket_disconnected", client_id=client_id)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("websocket_send_failed", error=str(e))

    async def broadcast(self, message: dict, client_ids: Optional[Set[str]] = None):
        """Broadcast message to all or specific clients"""
        targets = (
            {cid: conns for cid, conns in self.active_connections.items() if cid in client_ids}
            if client_ids
            else self.active_connections
        )

        disconnected = []

        for client_id, connections in targets.items():
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append((websocket, client_id))

        # Clean up disconnected clients
        for websocket, client_id in disconnected:
            self.disconnect(websocket, client_id)


class NotificationService:
    """Service for managing real-time notifications"""

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self._running = False

    async def start(self):
        """Start the notification service"""
        self._running = True
        logger.info("notification_service_started")

    async def stop(self):
        """Stop the notification service"""
        self._running = False
        # Close all connections
        for client_id, connections in list(self.connection_manager.active_connections.items()):
            for websocket in connections:
                try:
                    await websocket.close()
                except Exception:
                    pass
        self.connection_manager.active_connections.clear()
        logger.info("notification_service_stopped")

    async def send_prediction_notification(
        self,
        client_id: str,
        prediction_id: str,
        result: dict,
        model_version: str,
        processing_time_ms: float,
    ):
        """Send prediction result notification"""
        message = {
            "type": "prediction_complete",
            "data": {
                "prediction_id": prediction_id,
                "result": result,
                "model_version": model_version,
                "processing_time_ms": processing_time_ms,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if client_id in self.connection_manager.active_connections:
            for websocket in self.connection_manager.active_connections[client_id]:
                await self.connection_manager.send_personal_message(message, websocket)

    async def send_model_update_notification(self, model_version: str, status: str):
        """Send model update notification to all connected clients"""
        message = {
            "type": "model_updated",
            "data": {
                "model_version": model_version,
                "status": status,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.connection_manager.broadcast(message)

    async def send_error_notification(self, client_id: str, error: str, code: str):
        """Send error notification"""
        message = {
            "type": "error",
            "data": {
                "error": error,
                "code": code,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if client_id in self.connection_manager.active_connections:
            for websocket in self.connection_manager.active_connections[client_id]:
                await self.connection_manager.send_personal_message(message, websocket)

    async def broadcast_notification(self, title: str, message_text: str, notification_type: str = "info"):
        """Broadcast a notification to all connected clients"""
        message = {
            "type": "notification",
            "data": {
                "title": title,
                "message": message_text,
                "notification_type": notification_type,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.connection_manager.broadcast(message)


# Global notification service instance
notification_service = NotificationService()
