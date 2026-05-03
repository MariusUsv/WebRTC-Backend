from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models import Contact, Message, User
from app.schemas import ContactAddIn, ContactUpdateIn, ContactOut, LoginIn, RegisterIn, TokenOut
from app.auth import ALGORITHM, SECRET_KEY, hash_password, verify_password

app = FastAPI(title="Linko Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
active_connections: Dict[int, WebSocket] = {}

def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.phone),
        "name": user.full_name,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def token_to_user(db: Session, token: str) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.phone == str(sub)).first()
    if user is None:
        try:
            user = db.query(User).filter(User.phone == int(str(sub))).first()
        except Exception:
            pass

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return user

def me_from_auth_header(db: Session, authorization: Optional[str]) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ", 1)[1].strip()
    return token_to_user(db, token)

@app.get("/health")
def health() -> Dict[str, bool]:
    return {"ok": True}

@app.post("/auth/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    phone = str(data.phone).strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone required")

    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(phone=phone, full_name=data.full_name, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    phone = str(data.phone).strip()
    user = db.query(User).filter(User.phone == phone).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/logout")
def logout_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    me = me_from_auth_header(db, authorization)
    return {"ok": True}

@app.get("/contacts", response_model=list[ContactOut])
def list_contacts(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    me = me_from_auth_header(db, authorization)
    rows = (
        db.query(Contact, User)
        .join(User, User.id == Contact.contact_user_id)
        .filter(Contact.owner_id == me.id)
        .order_by(Contact.contact_name.asc())
        .all()
    )
    return [
        {
            "id": c.id,
            "user_id": u.id,
            "phone": u.phone,
            "contact_name": c.contact_name,
            "is_online": u.id in active_connections
        } 
        for c, u in rows
    ]

@app.post("/contacts", response_model=ContactOut)
def add_contact(data: ContactAddIn, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    me = me_from_auth_header(db, authorization)
    phone = str(data.phone).strip()
    
    other = db.query(User).filter(User.phone == phone).first()
    if not other:
        raise HTTPException(status_code=404, detail="User not found")
    if other.id == me.id:
        raise HTTPException(status_code=400, detail="You cannot add yourself")

    existing = db.query(Contact).filter(Contact.owner_id == me.id, Contact.contact_user_id == other.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Contact already exists")

    c = Contact(owner_id=me.id, contact_user_id=other.id, contact_name=data.contact_name.strip())
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "user_id": other.id, "phone": other.phone, "contact_name": c.contact_name, "is_online": other.id in active_connections}

@app.put("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, data: ContactUpdateIn, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    me = me_from_auth_header(db, authorization)
    c = db.get(Contact, contact_id)
    if not c or c.owner_id != me.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    c.contact_name = data.contact_name.strip()
    db.commit()
    
    other = db.get(User, c.contact_user_id)
    return {"id": c.id, "user_id": other.id, "phone": other.phone, "contact_name": c.contact_name, "is_online": other.id in active_connections}

@app.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    me = me_from_auth_header(db, authorization)
    c = db.get(Contact, contact_id)
    if not c or c.owner_id != me.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    db.delete(c)
    db.commit()
    return {"ok": True}

@app.get("/messages/{other_user_id}")
def get_messages(other_user_id: int, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    me = me_from_auth_header(db, authorization)
    msgs = (
        db.query(Message)
        .filter(
            ((Message.sender_id == me.id) & (Message.receiver_id == other_user_id))
            | ((Message.sender_id == other_user_id) & (Message.receiver_id == me.id))
        )
        .order_by(Message.created_at.asc())
        .all()
    )
    return [
        {
            "message_id": m.id,
            "from_user_id": m.sender_id,
            "to_user_id": m.receiver_id,
            "text": m.text,
            "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None,
        }
        for m in msgs
    ]

@app.delete("/messages/{message_id}")
def delete_message(message_id: int, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    me = me_from_auth_header(db, authorization)
    msg = db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.sender_id != me.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    other_id = msg.receiver_id
    db.delete(msg)
    db.commit()

    try:
        import anyio
        async def _notify():
            await ws_send(other_id, {"type": "chat_delete", "from_user_id": me.id, "message_id": message_id})
        anyio.from_thread.run(_notify)
    except Exception:
        pass

    return {"ok": True}

async def ws_send(user_id: int, payload: Dict[str, Any]) -> None:
    ws = active_connections.get(user_id)
    if not ws:
        return
    try:
        await ws.send_json(payload)
    except Exception:
        if active_connections.get(user_id) is ws:
            active_connections.pop(user_id, None)

FORWARD_TYPES: Set[str] = {
    "typing", "presence_ping", "call_invite", "call_accept", 
    "call_reject", "call_hangup", "webrtc_offer", "webrtc_answer", "webrtc_ice"
}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str, db: Session = Depends(get_db)):
    try:
        me = token_to_user(db, token)
    except HTTPException:
        try:
            await ws.close(code=1008)
        except Exception:
            pass
        return

    user_id = me.id
    await ws.accept()
    active_connections[user_id] = ws

    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "chat_send":
                to_user_id = int(msg["to_user_id"])
                text = str(msg.get("text", ""))

                m = Message(sender_id=user_id, receiver_id=to_user_id, text=text)
                db.add(m)
                db.commit()
                db.refresh(m)

                payload = {
                    "type": "chat_message",
                    "message_id": m.id,
                    "from_user_id": user_id,
                    "to_user_id": to_user_id,
                    "text": m.text,
                    "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None,
                }
                await ws_send(to_user_id, payload)
                await ws_send(user_id, payload)
                continue

            if mtype == "presence_ping":
                to_user_id = msg.get("to_user_id")
                if to_user_id is None:
                    try:
                        await ws.send_json({"type": "presence_pong", "from_user_id": user_id})
                    except Exception:
                        pass
                    continue
                try:
                    to_user_id = int(to_user_id)
                except Exception:
                    continue

                if to_user_id in active_connections:
                    await ws_send(user_id, {"type": "presence_pong", "from_user_id": to_user_id})
                    await ws_send(to_user_id, {"type": "presence_ping", "from_user_id": user_id})
                continue

            if mtype in FORWARD_TYPES:
                to_user_id = msg.get("to_user_id")
                if to_user_id is None:
                    continue
                try:
                    to_user_id = int(to_user_id)
                except Exception:
                    continue
                forward = dict(msg)
                forward["from_user_id"] = user_id
                await ws_send(to_user_id, forward)
                continue

            await ws.send_json({"type": "error", "detail": "Unknown message type"})

    except WebSocketDisconnect:
        pass
    finally:
        if active_connections.get(user_id) is ws:
            active_connections.pop(user_id, None)