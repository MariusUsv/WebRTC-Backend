from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app import schemas
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.dependencies import get_current_user # Asigură-te că ai asta pentru rutele protejate

router = APIRouter()

# ==========================================
# 1. RUTA DE ÎNREGISTRARE (Care acum te și loghează automat)
# ==========================================
@router.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    print(f"DEBUG: Încercare înregistrare - Nume: {user.full_name}, Telefon: {user.phone}")

    if not user.phone or len(user.phone) < 4:
        raise HTTPException(status_code=400, detail="Numărul de telefon este invalid.")

    existing_user = db.query(User).filter(User.phone == str(user.phone)).first()
    
    if existing_user is not None:
        raise HTTPException(status_code=400, detail="Numărul de telefon este deja înregistrat.")

    try:
        # AICI E MODIFICAREA: Adăugăm [:72] pentru a trunchia parola dacă e prea lungă
        truncated_password = user.password[:72]
        
        # Creăm utilizatorul
        new_user = User(
            phone=user.phone,
            full_name=user.full_name,
            hashed_password=get_password_hash(truncated_password)
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Generăm token-ul ca să logăm userul pe loc!
        token = create_access_token({"sub": new_user.phone, "name": new_user.full_name})
        
        print(f"DEBUG: Succes! Utilizator {user.full_name} creat și logat.")
        
        # Returnăm exact ce așteaptă React-ul (useAuth.js)
        return {
            "access_token": token, 
            "token_type": "bearer", 
            "user_name": new_user.full_name
        }
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Eroare internă la înregistrare: {str(e)}")
        raise HTTPException(status_code=500, detail="Eroare internă la salvarea contului.")


# ==========================================
# 2. RUTA DE LOGIN
# ==========================================
@router.post("/login")
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == user_credentials.phone).first()
    
    # AICI E MODIFICAREA: Adăugăm [:72] ca să comparăm exact aceleași caractere
    truncated_password_attempt = user_credentials.password[:72]
    
    if not user or not verify_password(truncated_password_attempt, user.hashed_password):
        raise HTTPException(status_code=401, detail="Telefon sau parolă incorectă")
    
    token = create_access_token({"sub": user.phone, "name": user.full_name})
    
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "user_name": user.full_name
    }


# ==========================================
# 3. RUTA DE LOGOUT
# ==========================================
@router.post("/logout")
def logout():
    return {"message": "Deconectare reușită"}


# ==========================================
# 4. RUTE PENTRU E2EE (CHEI PUBLICE)
# ==========================================
@router.put("/users/me/public_key")
def update_my_public_key(payload: schemas.PublicKeyIn, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Clientul apelează asta după login pentru a-și urca public key-ul (JWK serializat)."""
    me.public_key = payload.public_key
    db.commit()
    return {"ok": True}

@router.get("/users/{user_id}/public_key", response_model=schemas.PublicKeyOut)
def get_user_public_key(user_id: int, db: Session = Depends(get_db)):
    """Clientul apelează asta înainte de a trimite un mesaj cuiva pentru a deriva Shared Secret-ul."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.id, "public_key": user.public_key}
