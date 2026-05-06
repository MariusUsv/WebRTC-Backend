from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
import os, shutil
from uuid import uuid4
from app.database import get_db
from app.models import Contact, Message, User, CallLog
from app import schemas
from app.core.dependencies import get_current_user
from app.core.connection_manager import manager

router = APIRouter()

@router.get("/contacts", response_model=list[schemas.ContactOut])
def list_contacts(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Contact, User).join(User, User.id == Contact.contact_user_id).filter(Contact.owner_id == me.id).all()
    return [{"id": c.id, "user_id": u.id, "phone": u.phone, "contact_name": c.contact_name, "is_online": u.id in manager.active_connections, "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None} for c, u in rows]

@router.post("/contacts", response_model=schemas.ContactOut)
def add_contact(data: schemas.ContactAddIn, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    other = db.query(User).filter(User.phone == str(data.phone).strip()).first()
    if not other: raise HTTPException(status_code=404, detail="Utilizatorul nu există")
    if other.id == me.id: raise HTTPException(status_code=400, detail="Nu te poți adăuga pe tine")
    if db.query(Contact).filter(Contact.owner_id == me.id, Contact.contact_user_id == other.id).first(): raise HTTPException(status_code=400, detail="Contactul există deja")
    
    c = Contact(owner_id=me.id, contact_user_id=other.id, contact_name=data.contact_name.strip())
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "user_id": other.id, "phone": other.phone, "contact_name": c.contact_name, "is_online": other.id in manager.active_connections, "last_seen_at": other.last_seen_at.isoformat() if other.last_seen_at else None}

@router.get("/calls", response_model=list[schemas.CallLogOut])
def get_calls(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(CallLog).filter((CallLog.caller_id == me.id) | (CallLog.receiver_id == me.id)).order_by(CallLog.created_at.desc()).limit(30).all()
    result = []
    for log in logs:
        other_id = log.receiver_id if log.caller_id == me.id else log.caller_id
        other_user = db.get(User, other_id)
        contact = db.query(Contact).filter(Contact.owner_id == me.id, Contact.contact_user_id == other_id).first()
        name = contact.contact_name if contact else (other_user.full_name if other_user else "Unknown")
        result.append({"id": log.id, "caller_id": log.caller_id, "receiver_id": log.receiver_id, "status": log.status, "duration": log.duration, "created_at": log.created_at.isoformat(), "other_party_name": name})
    return result

@router.get("/messages/{other_user_id}")
def get_messages(other_user_id: int, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(((Message.sender_id == me.id) & (Message.receiver_id == other_user_id)) | ((Message.sender_id == other_user_id) & (Message.receiver_id == me.id))).order_by(Message.created_at.asc()).all()
    return [{"message_id": m.id, "from_user_id": m.sender_id, "to_user_id": m.receiver_id, "text": m.text, "file_url": getattr(m, 'file_url', None), "is_file": getattr(m, 'is_file', False), "is_read": m.is_read, "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None} for m in msgs]

@router.post("/chat/upload")
async def upload_file(to_user_id: int, file: UploadFile = File(...), me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not os.path.exists("uploads"): os.makedirs("uploads")
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f"{uuid4()}{file_ext}"
    with open(os.path.join("uploads", file_name), "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    file_url = f"/uploads/{file_name}"
    m = Message(sender_id=me.id, receiver_id=to_user_id, text=file.filename, file_url=file_url, is_file=True, is_read=False)
    db.add(m); db.commit(); db.refresh(m)
    
    return {"type": "chat_message", "message_id": m.id, "from_user_id": me.id, "to_user_id": to_user_id, "text": m.text, "file_url": m.file_url, "is_file": True, "is_read": False, "created_at": m.created_at.isoformat()}

@router.delete("/messages/{message_id}")
async def delete_message(message_id: int, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msg = db.get(Message, message_id)
    if msg and msg.sender_id == me.id: db.delete(msg); db.commit()
    return {"ok": True}

@router.post("/chat/send")
async def send_message_fallback(payload: dict, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    to_user_id = payload.get("to_user_id")
    text = payload.get("text")
    if not to_user_id or not text: raise HTTPException(status_code=400)
    
    m = Message(sender_id=me.id, receiver_id=to_user_id, text=text, is_read=False)
    db.add(m); db.commit(); db.refresh(m)
    
    return {"type": "chat_message", "message_id": m.id, "from_user_id": me.id, "to_user_id": to_user_id, "text": m.text, "is_file": False, "is_read": False, "created_at": m.created_at.isoformat()}