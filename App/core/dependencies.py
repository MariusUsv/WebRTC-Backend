from fastapi import Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional
from jose import JWTError, jwt
from app.database import get_db
from app.models import User
from app.core.security import SECRET_KEY, ALGORITHM

def validate_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Token invalid")
        
        user = db.query(User).filter(User.phone == str(sub)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User inexistent")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Sesiune expirată")

def get_current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Lipsește token-ul de acces")
    
    token = authorization.split(" ", 1)[1].strip()
    return validate_token(token, db)

def get_user_from_token(token: str, db: Session) -> User:
    try:
        return validate_token(token, db)
    except Exception:
        return None