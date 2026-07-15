import json
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("kavach.core.pubsub")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Total active connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Create a copy of the list to avoid modifying during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending message to WebSocket client: {e}")
                self.disconnect(connection)

# Singleton connection manager instance
pubsub_manager = ConnectionManager()
