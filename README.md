# 🔒 Linko Pro — Secure Real-Time Backend

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Render](https://img.shields.io/badge/Render-%46E3B7.svg?style=for-the-badge&logo=render&logoColor=white)

Backend service for **Linko Pro**, a secure real-time communication platform supporting End-to-End Encrypted (E2EE) messaging and peer-to-peer video calls.

🟢 **Live API:** Deployed on Render

---

## 🚀 Core Features

* ⚡ **Real-Time Communication**
  - WebSockets for bidirectional messaging and WebRTC signaling
  - Low-latency event-driven architecture

* 🔐 **Authentication & Security**
  - JWT-based stateless authentication
  - Password hashing with bcrypt (`passlib`)
  - Input validation via Pydantic schemas

* 🎥 **WebRTC Signaling Server**
  - Handles SDP Offer/Answer exchange
  - ICE candidate routing
  - Zero media processing (pure signaling layer)

* 🔒 **End-to-End Encryption Support**
  - Public key exchange via REST API
  - Server routes only encrypted payloads (ciphertexts)
  - Zero-Knowledge architecture

* 🧱 **Modular API Design**
  - FastAPI routers
  - Dependency injection
  - Clean separation of concerns

---

## 🧱 Architecture

```text
app/
 ├── routes/     # API endpoints (auth, ws, users)
 ├── models/     # SQLAlchemy models
 ├── schemas/    # Pydantic validation
 ├── core/       # Security (JWT, hashing)
 └── main.py     # Entry point
System Role
REST API
Authentication
User management
Public key distribution
WebSocket Server
Routes encrypted messages
Handles WebRTC signaling
WebRTC Layer
Direct peer-to-peer media (audio/video)
Server is not involved in media transport
🔒 End-to-End Encryption (E2EE)
Public keys are generated client-side
Keys are exchanged via REST endpoints
Shared secrets are derived locally (Web Crypto API)
Messages are encrypted before transmission

➡️ Backend only processes ciphertexts, never plaintext

🎥 WebRTC Signaling Flow
Caller sends SDP Offer via WebSocket
Receiver responds with SDP Answer
ICE candidates are exchanged
Direct P2P connection is established
⚠️ Engineering Challenges
WebSocket reconnection & session recovery
WebRTC race conditions (offer/ICE timing)
Stateless auth across HTTP + WebSocket
Maintaining consistency in real-time flows
🛠️ Tech Stack
Backend: Python, FastAPI
Real-time: WebSockets
Database: SQLAlchemy (SQLite / PostgreSQL)
Security: JWT, bcrypt
Deployment: Render (Dockerized)
💻 Local Development
git clone https://github.com/MariusUsv/WebRTC-Backend.git
cd WebRTC-Backend

pip install -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 10000

📄 API Docs:

http://localhost:10000/docs
☁️ Deployment

Configured for Render using:

PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port $PORT
📌 Notes

This backend is designed as a pure signaling + routing layer, with:

zero media handling
zero plaintext access
full compatibility with secure client-side cryptography

⚡ Built with focus on real-time systems, security, and clean architecture.
