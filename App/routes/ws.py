from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_user_from_token
from app.core.connection_manager import manager 

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(None), 
    db: Session = Depends(get_db)
):
    # Respingem dacă nu există token
    if token is None or token == "undefined":
        await websocket.close(code=1008)
        return

    # Validăm utilizatorul
    user = get_user_from_token(token, db)
    if user is None:
        await websocket.close(code=1008)
        return

    # Înregistrăm conexiunea în manager
    await manager.connect(websocket, user.id)
    
    try:
        while True:
            # Așteptăm pachete JSON de la Frontend
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            # 1. Menținem statusul de Online
            if msg_type == "presence_ping":
                await manager.send_personal_message({"type": "presence_pong", "from_user_id": user.id}, user.id)
            
            # 2. RUTAREA MAGICĂ A APELURILOR (Fix-ul problemei!)
            elif msg_type in ["call_invite", "call_accept", "call_reject", "call_hangup", "webrtc_offer", "webrtc_answer", "webrtc_ice", "chat_read"]:
                to_user_id = data.get("to_user_id")
                
                if to_user_id:
                    # FOARTE IMPORTANT: Serverul atașează ID-ul celui care sună, 
                    # ca destinatarul să știe de unde vine apelul
                    data["from_user_id"] = user.id 
                    
                    # Trimitem apelul (sau datele video) mai departe către destinatar
                    await manager.send_personal_message(data, int(to_user_id))

    except WebSocketDisconnect:
        manager.disconnect(user.id)
    except Exception as e:
        print(f"Eroare WebSocket neașteptată: {e}")
        manager.disconnect(user.id)