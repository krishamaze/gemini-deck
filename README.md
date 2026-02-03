# Gemini Command Deck

> "It's not just a chatbot."

## Quick Start

```bash
cd backend
pip install -r requirements.txt
python main.py
```

## Architecture

```
Frontend (Next.js)  →  Backend (FastAPI)  →  Gemini API
     ↓                      ↓
   VNC Display          ChromaDB Memory
```

## API Endpoints

| Endpoint | Type | Description |
|----------|------|-------------|
| `/api/chat/stream` | WS | Chat with AI (supports `?api_key=`) |
| `/api/auth/google` | GET | Start OAuth |
| `/api/accounts/*` | REST | Manage API keys |
| `/api/memory/*` | REST | Memory storage |
| `/api/sandbox/*` | REST | VM connections |

## Environment

```env
GEMINI_API_KEY=your_key_here
JWT_SECRET=your_secret
GOOGLE_CLIENT_ID=optional
GOOGLE_CLIENT_SECRET=optional
```

## Repos

| Repo | Purpose |
|------|---------|
| `gemini-deck` | Backend (FastAPI) |
| `gemini-deck-ui` | Frontend (Next.js) |

## Status

- ✅ Backend: Complete
- ⏳ Frontend: API key config needed

---

*Docs live in `gemini-deck-ui/docs/`*
