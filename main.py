from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List

app = FastAPI()

# Клас для керування з'єднаннями
class ConnectionManager:
    def __init__(self):
        # Структура: {room_id: [список_websocket_обєктів]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Ліміти кімнат: {room_id: max_participants}
        self.room_limits: Dict[str, int] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        
        # Перевірка ліміту (якщо кімната вже існує)
        if room_id in self.active_connections:
            limit = self.room_limits.get(room_id, 10) # 10 за замовчуванням
            if len(self.active_connections[room_id]) >= limit:
                await websocket.send_text("Помилка: Кімната заповнена!")
                await websocket.close()
                return False
        
        # Додавання до кімнати
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        return True

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_text(message)

manager = ConnectionManager()

@app.post("/create_room/{room_id}")
async def create_room(room_id: str, max_participants: int):
    # Встановлюємо ліміт для кімнати
    manager.room_limits[room_id] = max_participants
    return {"status": "Кімнату створено", "room_id": room_id, "limit": max_participants}

@app.websocket("/ws/{room_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, client_id: str):
    # Спроба підключення
    success = await manager.connect(websocket, room_id)
    if not success:
        return

    try:
        await manager.broadcast(f"Користувач #{client_id} приєднався до чату", room_id)
        while True:
            # Очікування повідомлення від клієнта
            data = await websocket.receive_text()
            await manager.broadcast(f"Клієнт #{client_id}: {data}", room_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast(f"Користувач #{client_id} покинув чат", room_id)