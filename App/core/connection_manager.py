from fastapi import WebSocket
from typing import Dict, Set

class ConnectionManager:
    """
    Manager pentru conexiunile WebSocket.

    Suportă MULTIPLE socketuri per user (necesar pentru:
      - reconectare temporară când vechiul socket se închide cu lag
      - același user logat în mai multe tab-uri / device-uri
      - StrictMode în React dev care face double-mount)
    """

    def __init__(self):
        # user_id -> set de WebSocket-uri active
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Scoate DOAR socketul precizat, nu pe toate ale user-ului."""
        sockets = self.active_connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            del self.active_connections[user_id]

    def is_online(self, user_id: int) -> bool:
        return bool(self.active_connections.get(user_id))

    async def send_personal_message(self, message: dict, user_id: int):
        """Trimite mesajul la TOATE socketurile active ale user-ului."""
        sockets = self.active_connections.get(user_id)
        if not sockets:
            return
        stale = []
        # iteram pe o copie pentru a evita modificare in timp ce iteram
        for ws in list(sockets):
            try:
                await ws.send_json(message)
            except Exception:
                # Dacă trimiterea eșuează, adăugăm la lista de curățare
                stale.append(ws)
                
        for ws in stale:
            self.disconnect(ws, user_id)

    async def broadcast(self, message: dict):
        # Facem o copie a cheilor pentru a evita erori de dimensiune dicționar în timpul iterației
        for u_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, u_id)

manager = ConnectionManager()