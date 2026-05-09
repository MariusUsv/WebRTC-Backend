from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    phone = Column(String, unique=True, index=True)
    hashed_password = Column(String)  # Parola criptată
    is_online = Column(Boolean, default=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    # E2EE: cheia publică ECDH (jwk JSON serializat) — trimisă de client la primul login
    public_key = Column(Text, nullable=True)

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    contact_user_id = Column(Integer, ForeignKey("users.id"))
    contact_name = Column(String)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    # text stochează ciphertext-ul E2EE (format "e2ee:v1:iv:ct") sau plaintext legacy
    text = Column(Text)
    file_url = Column(String, nullable=True)
    is_file = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    caller_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String)  # Ex: "accepted", "rejected", "missed"
    duration = Column(Integer, default=0)  # în secunde
    created_at = Column(DateTime, default=datetime.utcnow)

class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("message_id", "user_id", "emoji", name="uq_reaction"),)

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    emoji = Column(String(16))
    created_at = Column(DateTime, default=datetime.utcnow)