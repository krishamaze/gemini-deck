from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat, system, memory, agent
import uvicorn
import os

# IMMUTABLE CONFIGURATION
API_VERSION = "v1"
PROJECT_NAME = "Gemini Command Deck"

app = FastAPI(title=PROJECT_NAME, version=API_VERSION)

# CORS - Allow Frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router Registration
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])

@app.get("/")
async def root():
    return {"status": "online", "system": "Gemini Command Deck Gateway"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
