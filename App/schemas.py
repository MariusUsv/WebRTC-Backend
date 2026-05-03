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

class ContactOut(BaseModel):
    user_id: int
    phone: str
    full_name: str