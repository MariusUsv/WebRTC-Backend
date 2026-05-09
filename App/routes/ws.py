import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.core.dependencies import get_user_from_token
from app.core.connection_manager import manager
from app.models import CallLog, Message, Reaction

router = APIRouter()

async def _persist_chat_message(sender_id: int, receiver_id: int, text: str) -> tuple[int, str] | None:
    """Salvează mesajul în DB în background fără să blocheze WebSocket-ul (anti-lag)."""
    def _save():
        db = SessionLocal()
        try:
            m = Message(sender_id=sender_id, receiver_id=receiver_id, text=text, is_read=False)
            db.add(m)
            db.commit()
            db.refresh(m)
            return m.id, m.created_at.isoformat()
        finally:
            db.close()
            
    try:
        return await asyncio.to_thread(_save)
    except Exception as e:
        print(f"[persist_chat_message] eroare: {e}")
        return None

async def _persist_call_log(caller_id: int, receiver_id: int, status: str):
    """Salvează log-ul apelului în DB asincron."""
    def _save():
        db = SessionLocal()
        try:
            db.add(CallLog(caller_id=caller_id, receiver_id=receiver_id, status=status))
            db.commit()
        finally:
            db.close()
            
    try:
        await asyncio.to_thread(_save)
    except Exception as e:
        print(f"[persist_call_log] eroare: {e}")

async def _toggle_reaction(message_id: int, user_id: int, emoji: str) -> tuple[bool, list[dict]]:
    """Toggle: dacă reacția există → o șterge, altfel → o adaugă. Întoarce (added, all_reactions)."""
    def _do():
        db = SessionLocal()
        try:
            existing = db.query(Reaction).filter(
                Reaction.message_id == message_id,
                Reaction.user_id == user_id,
                Reaction.emoji == emoji,
            ).first()
            
            if existing:
                db.delete(existing)
                db.commit()
                added = False
            else:
                db.add(Reaction(message_id=message_id, user_id=user_id, emoji=emoji))
                db.commit()
                added = True
                
            rs = db.query(Reaction).filter(Reaction.message_id == message_id).all()
            return added, [{"user_id": r.user_id, "emoji": r.emoji} for r in rs]
        finally:
            db.close()
            
    return await asyncio.to_thread(_do)

def _get_message_parties(message_id: int) -> tuple[int, int] | None:
    """Extrage ID-urile participanților la un mesaj."""
    db = SessionLocal()
    try:
        m = db.get(Message, message_id)
        if not m: return None
        return m.sender_id, m.receiver_id
    finally:
        db.close()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    if token is None or token == "undefined":
        await websocket.close(code=1008)
        return

    user = get_user_from_token(token, db)
    if user is None:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user.id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            # 1. Heartbeat
            if msg_type == "presence_ping":
                try:
                    await websocket.send_json({"type": "presence_pong"})
                except Exception:
                    break

            # 2. Typing
            elif msg_type == "typing":
                to_user_id = data.get("to_user_id")
                if to_user_id:
                    await manager.send_personal_message(
                        {"type": "typing", "from_user_id": user.id},
                        int(to_user_id),
                    )

            # 3. ★ CHAT MESSAGE prin WS direct (ZERO LAG)
            elif msg_type == "chat_message":
                to_user_id = data.get("to_user_id")
                text = data.get("text") or ""
                client_id = data.get("client_id")  # token de idempotency
                
                if not to_user_id or not text:
                    continue
                    
                to_user_id_int = int(to_user_id)

                # PRIMUL hop: forward instant către destinatar și expeditor
                forward_payload = {
                    "type": "chat_message",
                    "client_id": client_id,
                    "message_id": client_id,   # id temporar
                    "from_user_id": user.id,
                    "to_user_id": to_user_id_int,
                    "text": text,
                    "is_file": False,
                    "is_read": False,
                    "created_at": None,
                    "reactions": [],
                    "pending": True,
                }
                await manager.send_personal_message(forward_payload, to_user_id_int)
                await manager.send_personal_message(forward_payload, user.id)

                # AL DOILEA hop: salvare în DB asincron + confirmare
                async def _persist_and_confirm():
                    res = await _persist_chat_message(user.id, to_user_id_int, text)
                    if not res: return
                    new_id, created_iso = res
                    
                    confirm = {
                        "type": "chat_message_saved",
                        "client_id": client_id,
                        "message_id": new_id,
                        "from_user_id": user.id,
                        "to_user_id": to_user_id_int,
                        "created_at": created_iso,
                    }
                    await manager.send_personal_message(confirm, to_user_id_int)
                    await manager.send_personal_message(confirm, user.id)

                asyncio.create_task(_persist_and_confirm())

            # 4. ★ Reacții emoji E2EE
            elif msg_type == "reaction_toggle":
                message_id = data.get("message_id")
                emoji = data.get("emoji")
                
                if not message_id or not emoji:
                    continue
                    
                try:
                    message_id_int = int(message_id)
                except (TypeError, ValueError):
                    continue

                parties = _get_message_parties(message_id_int)
                if not parties:
                    continue
                    
                sender_id, receiver_id = parties
                
                # Doar participanții pot reacționa
                if user.id not in (sender_id, receiver_id):
                    continue

                added, all_reactions = await _toggle_reaction(message_id_int, user.id, emoji)
                
                payload = {
                    "type": "reaction_update",
                    "message_id": message_id_int,
                    "reactions": all_reactions,
                    "by_user_id": user.id,
                    "emoji": emoji,
                    "added": added,
                }
                
                await manager.send_personal_message(payload, sender_id)
                if receiver_id != sender_id:
                    await manager.send_personal_message(payload, receiver_id)

            # 5. Rutare WebRTC + chat_read
            elif msg_type in [
                "call_invite", "call_accept", "call_reject", "call_hangup",
                "webrtc_offer", "webrtc_answer", "webrtc_ice", "chat_read",
            ]:
                to_user_id = data.get("to_user_id")
                
                if to_user_id:
                    to_user_id_int = int(to_user_id)
                    data["from_user_id"] = user.id

                    if msg_type == "call_invite":
                        data["caller_name"] = user.full_name or user.phone

                    await manager.send_personal_message(data, to_user_id_int)

                    if msg_type == "call_reject":
                        asyncio.create_task(_persist_call_log(to_user_id_int, user.id, "rejected"))
                    elif msg_type == "call_hangup":
                        asyncio.create_task(_persist_call_log(user.id, to_user_id_int, "accepted"))

                    if msg_type in ("call_hangup", "call_reject"):
                        await manager.send_personal_message(data, user.id)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
    except Exception as e:
        print(f"Eroare WebSocket neașteptată: {e}")
        manager.disconnect(websocket, user.id)