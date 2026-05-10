"""
WebSocket endpoint for real-time notifications
"""
from fastapi import WebSocket, WebSocketDisconnect
import uuid
import json
import structlog

from app.services.notification import notification_service

logger = structlog.get_logger()


async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """
    WebSocket endpoint for real-time notifications.

    Connect to: ws://host/ws?client_id=<your_client_id>

    Message types:
    - prediction_complete: Prediction result notification
    - model_updated: Model status update notification
    - error: Error notification
    - notification: General notification
    """
    if not client_id:
        client_id = str(uuid.uuid4())

    await notification_service.connection_manager.connect(websocket, client_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp"),
                    })

                elif msg_type == "subscribe":
                    # Subscribe to specific notifications
                    subscriptions = message.get("subscriptions", [])
                    logger.info("client_subscribed", client_id=client_id, subscriptions=subscriptions)

                elif msg_type == "prediction_request":
                    # Handle prediction request via WebSocket
                    prediction_id = message.get("prediction_id")
                    if prediction_id:
                        # Send notification that prediction is being processed
                        await websocket.send_json({
                            "type": "prediction_started",
                            "data": {"prediction_id": prediction_id},
                        })

                else:
                    logger.warning("unknown_message_type", client_id=client_id, type=msg_type)

            except json.JSONDecodeError:
                logger.warning("invalid_json_received", client_id=client_id)
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": "Invalid JSON format"},
                })

    except WebSocketDisconnect:
        notification_service.connection_manager.disconnect(websocket, client_id)
        logger.info("websocket_disconnected", client_id=client_id)

    except Exception as e:
        logger.error("websocket_error", client_id=client_id, error=str(e))
        notification_service.connection_manager.disconnect(websocket, client_id)
