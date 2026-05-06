Markdown
# 🚀 WebRTC & WebSocket Backend - LINKO Chat

Acesta este serverul central al aplicației de mesagerie **LINKO**, dezvoltat folosind **FastAPI**. Proiectul gestionează comunicarea în timp real, apelurile video și autentificarea securizată a utilizatorilor.

## ✨ Funcționalități Implementate

*   **Mesagerie în Timp Real:** Expedierea și primirea mesajelor prin WebSockets pentru o latență minimă.
*   **Semnalizare WebRTC:** Logica completă pentru schimbul de oferte/răspunsuri SDP și candidați ICE necesari apelurilor video[cite: 1].
*   **Indicator de Tastare (Typing):** Notificări instantanee când un partener de chat scrie un mesaj[cite: 1].
*   **Sistem de Prezență:** Monitorizarea stării Online/Offline pentru lista de contacte[cite: 1].
*   **Autentificare JWT:** Înregistrare și conectare securizată folosind token-uri de acces[cite: 2].
*   **Gestionare Media:** Suport pentru încărcarea imaginilor și fișierelor prin rute API dedicate[cite: 1].

## 🛠️ Stack Tehnologic

*   **Framework:** FastAPI (v0.115.0)
*   **Bază de Date:** PostgreSQL / SQLite (via SQLAlchemy 2.0)[cite: 5]
*   **Securitate:** Passlib (Bcrypt pentru hash-uirea parolelor) și Python-jose (JWT)[cite: 5]
*   **Server ASGI:** Uvicorn[cite: 5]

## 📦 Instalare și Pornire Rapidă

1. **Clonarea proiectului:**
   ```bash
   git clone [https://github.com/MariusUsv/WebRTC-Backend.git](https://github.com/MariusUsv/WebRTC-Backend.git)
   cd WebRTC-Backend
Configurarea mediului virtual:

Bash
python -m venv venv
# Activare Windows:
venv\Scripts\activate
# Activare Mac/Linux:
source venv/bin/activate
Instalarea librăriilor:

Bash
pip install -r requirements.txt
Rularea serverului:

Bash
uvicorn main:app --reload
📋 Structura Fișierelor
main.py: Conține rutele API și gestionarea conexiunilor WebSocket[cite: 1].

models.py: Definirea structurii bazei de date (Utilizatori, Mesaje, Apeluri).

database.py: Configurarea sesiunilor și a motorului SQL.

requirements.txt: Lista dependințelor Python[cite: 5].

Dezvoltat de MariusUsv
