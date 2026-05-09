import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text as sql_text

from app.database import Base, engine
from app.routes import auth, api, ws

# Creează folderul uploads dacă nu există
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Asigură-te că tabelele există
Base.metadata.create_all(bind=engine)

# Mini-migrare pentru DB existent: adăugăm public_key dacă lipsește
def _light_migrate():
    try:
        with engine.connect() as conn:
            cols = conn.execute(sql_text("PRAGMA table_info(users)")).fetchall()
            names = {row[1] for row in cols}
            if "public_key" not in names:
                conn.execute(sql_text("ALTER TABLE users ADD COLUMN public_key TEXT"))
                conn.commit()
    except Exception as e:
        print(f"[migrate] skip: {e}")

_light_migrate()

# Inițializare App
app = FastAPI(title="Linko Pro API", description="E2EE + Real-time Chat 🔐 | Arhitectură de producție 🚀")

# Securitate / CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder pentru poze și atașamente
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ==========================================
# MAGIA AICI SE ÎNTÂMPLĂ: Încărcăm Rutele!
# ==========================================
app.include_router(auth.router, prefix="/auth")  # <-- AICI AM ADĂUGAT PREFIXUL
app.include_router(api.router)   # Restul rutelor API (Contacte, Chat, Call-uri)
app.include_router(ws.router)    # Conexiunea în timp real

@app.get("/health", tags=["System"])
def health():
    return {
        "status": "Sunt viu și gata de producție! 😎",
        "e2ee": True
    }