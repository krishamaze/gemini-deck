# Gemini Command Deck - Immutable Baseline
# Date: 2026-02-03
# Architecture: FastAPI Backend + Next.js Frontend + Xvfb/VNC Visualization

[Core Components]
1. Backend (Python/FastAPI)
   - Interface: REST API + WebSockets
   - Port: 8000
   - Location: /backend

2. Frontend (Next.js/React)
   - Interface: Web UI (Chat, Control, VNC)
   - Port: 3000
   - Location: /frontend

3. Display System
   - Xvfb Display: :99
   - VNC Port: 5900
   - Websockify Port: 6080

[Data Flow]
User Input -> UI -> Backend (API) -> Memory Injection -> Gemini CLI -> Backend (Stream) -> UI
Gemini GUI Action -> Xvfb -> x11vnc -> Websockify -> UI (VNC Viewer)

[Memory Standard]
- Storage: Local ChromaDB (Persistent)
- schema: { user_id, timestamp, prompt, response, meta_summary }
