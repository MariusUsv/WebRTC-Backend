from typing import Dict, Any
from fastapi import WebSocket
from sqlalchemy.orm import Session
from app.models import Message

active_connections: Dict[int, WebSocket] = {}

async def ws_send(user_id: int, payload: Dict[str, Any]):
    ws = active_connections.get(user_id)
    if ws:
        await ws.send_json(payload)

async def handle_chat_message(db: Session, sender_id: int, to_user_id: int, text: str):
    msg = Message(sender_id=sender_id, receiver_id=to_user_id, text=text)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    await ws_send(to_user_id, {
        "type": "chat_receive",
        "from_user_id": sender_id,
        "text": text,
        "message_id": msg.id,
        "created_at": msg.created_at.isoformat(),
    })
