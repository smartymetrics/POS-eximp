import os

with open("routers/ws_support.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add dataclass and new imports
if "from dataclasses import dataclass" not in content:
    content = content.replace("from typing import Dict, List", "from typing import Dict, List, Optional\nfrom dataclasses import dataclass\nimport jwt\nfrom database import get_db, db_execute")

chat_ws_code = """

@dataclass
class ConnectionInfo:
    websocket: WebSocket
    participant_id: str
    display_name: str
    participant_type: str
    admin_id: Optional[str]

class ChatConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[ConnectionInfo]] = {}

    async def connect(self, conn: ConnectionInfo, room_id: str):
        await conn.websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(conn)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id] = [c for c in self.active_connections[room_id] if c.websocket != websocket]
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: dict, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.websocket.send_json(message)
                except:
                    pass
                    
    def get_connected_participant_ids(self, room_id: str) -> List[str]:
        if room_id in self.active_connections:
            return [c.participant_id for c in self.active_connections[room_id]]
        return []

chat_manager = ChatConnectionManager()

async def chat_ping_loop(websocket: WebSocket):
    try:
        while True:
            await asyncio.sleep(25)
            await websocket.send_json({"type": "ping"})
    except:
        pass

@router.websocket("/ws/chat/{room_id}")
async def chat_websocket_endpoint(websocket: WebSocket, room_id: str, token: str):
    db = get_db()
    
    participant_id = None
    admin_id = None
    
    # 1. Validate token
    try:
        # A token could be either a valid admin JWT or a session_token string.
        # We will decode it.
        payload = jwt.decode(token, os.getenv("JWT_SECRET", "super-secret"), algorithms=["HS256"], options={"verify_exp": False})
        
        if payload.get("type") == "external_chat":
            # Session token
            if payload.get("room_id") != room_id:
                await websocket.close(code=4001)
                return
            participant_id = payload.get("sub")
        else:
            # Admin JWT
            admin_id = payload.get("sub")
    except Exception as e:
        await websocket.close(code=4001)
        return
        
    # 2. Confirm participant is accepted in this room
    if admin_id:
        res = await db_execute(lambda: db.table("chat_participants").select("*").eq("room_id", room_id).eq("admin_id", admin_id).eq("status", "accepted").execute())
    else:
        res = await db_execute(lambda: db.table("chat_participants").select("*").eq("id", participant_id).eq("room_id", room_id).eq("status", "accepted").execute())
        
    if not res.data:
        await websocket.close(code=4001)
        return
        
    part = res.data[0]
    participant_id = part["id"]
    display_name = part["external_name"] if part["participant_type"] == "external" else "Admin"
    
    if part["participant_type"] == "internal":
        admin_res = await db_execute(lambda: db.table("admins").select("full_name").eq("id", admin_id).execute())
        if admin_res.data: display_name = admin_res.data[0]["full_name"]

    conn_info = ConnectionInfo(
        websocket=websocket,
        participant_id=participant_id,
        display_name=display_name,
        participant_type=part["participant_type"],
        admin_id=admin_id
    )

    await chat_manager.connect(conn_info, room_id)
    
    # Broadcast Presence Join
    await chat_manager.broadcast({
        "type": "presence", "event": "joined", "participant_id": participant_id, "display_name": display_name
    }, room_id)

    ping_task = asyncio.create_task(chat_ping_loop(websocket))
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "pong":
                    continue
                # Actual messages are saved via HTTP POST /message, this WS only receives pongs/presence from clients
                # Broadcasting of messages is done by the POST endpoint calling chat_manager.broadcast
            except:
                pass
    except WebSocketDisconnect:
        ping_task.cancel()
        chat_manager.disconnect(websocket, room_id)
        await chat_manager.broadcast({
            "type": "presence", "event": "left", "participant_id": participant_id, "display_name": display_name
        }, room_id)
"""

if "ChatConnectionManager" not in content:
    with open("routers/ws_support.py", "w", encoding="utf-8") as f:
        f.write(content + chat_ws_code)
        print("ws_support router updated successfully.")
else:
    print("ws_support router already contains chat endpoints.")
