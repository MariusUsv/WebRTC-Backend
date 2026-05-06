import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routes import auth, api, ws

# Creează folderul uploads dacă nu există
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Asigură-te că tabelele există
Base.metadata.create_all(bind=engine)

# Inițializare App
app = FastAPI(title="Linko Pro API", description="Arhitectură de producție 🚀")

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
    return {"status": "Sunt viu și gata de producție! 😎"}