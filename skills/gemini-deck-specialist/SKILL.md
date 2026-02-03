---
name: gemini-deck-specialist
description: Specialized expert for maintaining and extending the Gemini Command Deck (Mission Control) system. Use when modifying the FastAPI backend, managing Xvfb/VNC display services, or implementing agentic memory workflows for the gemini-deck project.
---

# Gemini Command Deck Specialist

This skill provides the authoritative guidance for maintaining the Gemini Command Deck architecture.

## Core Architecture

- **Backend:** FastAPI (Python 3.11+) on port 8000.
- **Display:** Xvfb (:99) -> x11vnc (5900) -> websockify (6080).
- **Memory:** ChromaDB (Semantic) + JSON (Recent logs).
- **Communication:** WebSocket streaming for real-time chat and system events.

## Workflows

### 1. Extending Backend Services
When adding new routers:
- Use Dependency Injection (`Depends(get_memory_store)`, `Depends(get_security_service)`).
- Register routes in `main.py`.
- Adhere to the `BASELINE.md` standards.

### 2. Managing the Virtual Display
- **Start:** Use `scripts/start_display.sh`.
- **Verify:** Check `websockify` logs for port 6080 binding.
- **Auto-Scale:** Ensure the display resolution matches the UI container (Default: 1280x720).

### 3. Implementing Agentic Autonomy ("Auto Mode")
When implementing the autonomous loop:
1. **Plan:** LLM generates a sequence of commands.
2. **Review:** Present plan to user via `{"type": "plan", "steps": [...]}` message.
3. **Execute:** Run commands sequentially.
4. **Observe:** Capture screen/terminal output and update state.

## 2026 Standards (Robustness)

- **Security:** Always run `analyze_prompt` before any LLM execution.
- **Observability:** Every WebSocket event should include a `trace_id` for debugging.
- **Memory:** Interactions MUST be "meta-fied" (summarized) before permanent storage to optimize retrieval.

## Project Structure
- `/backend`: Core FastAPI app.
- `/scripts`: Service management scripts.
- `/skills`: This skill and others.
- `docker-compose.yml`: Primary orchestration.