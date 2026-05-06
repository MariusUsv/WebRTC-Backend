from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=4)
    password: str = Field(..., min_length=4)

class UserLogin(BaseModel):
    phone: str
    password: str

class ContactAddIn(BaseModel):
    phone: str
    contact_name: str

class ContactOut(BaseModel):
    id: int
    user_id: int
    phone: str
    contact_name: str
    is_online: bool
    last_seen_at: Optional[str] = None # REPARAT: Acum este opțional[cite: 11]

class CallLogOut(BaseModel):
    id: int
    caller_id: int
    receiver_id: int
    status: str
    duration: int
    created_at: str
    other_party_name: str