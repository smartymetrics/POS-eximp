from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # ticket_id -> list of active websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, ticket_id: str):
        await websocket.accept()
        if ticket_id not in self.active_connections:
            self.active_connections[ticket_id] = []
        self.active_connections[ticket_id].append(websocket)

    def disconnect(self, websocket: WebSocket, ticket_id: str):
        if ticket_id in self.active_connections:
            self.active_connections[ticket_id].remove(websocket)
            if not self.active_connections[ticket_id]:
                del self.active_connections[ticket_id]

    async def broadcast(self, message: dict, ticket_id: str, exclude: WebSocket = None):
        if ticket_id in self.active_connections:
            for connection in self.active_connections[ticket_id]:
                if connection != exclude:
                    await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/support/{ticket_id}")
async def support_websocket_endpoint(websocket: WebSocket, ticket_id: str):
    await manager.connect(websocket, ticket_id)
    try:
        while True:
            # Wait for data from the client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Broadcast the signal (new message, typing indicator, etc.)
            # We add ticket_id to ensure the signal is scoped
            await manager.broadcast(message, ticket_id, exclude=websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, ticket_id)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(websocket, ticket_id)
