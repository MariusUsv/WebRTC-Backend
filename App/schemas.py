from pydantic import BaseModel

class RegisterIn(BaseModel):
    full_name: str
    phone: str
    password: str

class LoginIn(BaseModel):
    phone: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ContactAddIn(BaseModel):
    phone: str
    contact_name: str

class ContactUpdateIn(BaseModel):
    contact_name: str

class ContactOut(BaseModel):
    id: int
    user_id: int
    phone: str
    contact_name: str
    is_online: bool