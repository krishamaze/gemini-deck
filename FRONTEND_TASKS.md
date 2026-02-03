# Frontend Development Guide - Gemini Command Deck

## Overview
You are responsible for the **Frontend (UI)** of the Gemini Command Deck.
The backend will be running locally on `http://localhost:8000`.

## Tech Stack
- **Framework:** Next.js 14+ (App Router)
- **Styling:** Tailwind CSS (Cyberpunk/Dark Mode theme)
- **State:** Zustand or React Context
- **Icons:** Lucide React

## Core Modules to Implement

### 1. Chat Console (`/components/ChatConsole`)
- **Status:** [TODO]
- **Requirements:**
  - WebSocket connection to `ws://localhost:8000/api/chat/stream`.
  - Display user messages vs. System/AI messages.
  - Support Markdown rendering for AI responses.
  - Auto-scroll to bottom.

### 2. Virtual Display (`/components/VirtualDisplay`)
- **Status:** [TODO]
- **Requirements:**
  - Use `novnc` or `react-vnc` library.
  - Connect to `ws://localhost:6080` (Websockify proxy).
  - Canvas scaling to fit container.

### 3. Memory Monitor (`/components/MemoryStream`)
- **Status:** [TODO]
- **Requirements:**
  - Poll `GET http://localhost:8000/api/memory/history`.
  - Display list of recent "Thoughts/Memories" stored by the system.

## API Contract
See `backend/main.py` (Swagger UI available at `/docs`).

## Development Workflow
1. I will update `BACKEND_CHANGELOG.md` when API changes.
2. You implement the UI components.
3. Push to the repo, and I will integrate.
