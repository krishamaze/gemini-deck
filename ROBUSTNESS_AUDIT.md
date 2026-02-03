# Robustness Audit & Roadmap (2026 Standards)

## Executive Summary
This document outlines the gap analysis between our current MVP implementation and the 2026 industry best practices for AI Agent Systems and Production Python Services.

## 1. Security & Safety (Priority: Critical)

### Current State
- [x] Basic process isolation (CLI runs as subprocess).
- [ ] **Identity:** Agent shares the host OS user's full permissions.
- [x] **Input Sanitization:** Basic heuristic middleware implemented (SecurityService).

### 2026 Best Practices Gap
- **Identity-First Controls:** The agent should run as a restricted system user (`gemini-agent`), not the root/admin user.
- **Prompt Injection Defense:** Implement a "Firewall" layer that scans prompts for jailbreak attempts before they reach the model.
- **Approval Gates:** High-risk tool usage (file system writes, shell execution) must require explicit human confirmation via the UI.

### Roadmap
1. Create a `security_middleware.py` in the backend (Done).
2. Implement a "Human-in-the-loop" approval flow for the WebSocket stream.

## 2. Observability (Priority: High)

### Current State
- [x] Basic logging to stdout.
- [x] Persistent memory storage (ChromaDB) for interaction history.
- [ ] **Tracing:** No visibility into internal thought processes or tool execution times.

### 2026 Best Practices Gap
- **OpenTelemetry Tracing:** We need to trace every request.
    - `Span: User Request` -> `Span: Memory Retrieval` -> `Span: LLM Generation` -> `Span: Tool Execution`.
- **Replayability:** If the agent fails, we should be able to "replay" the exact state from the logs.

### Roadmap
1. Integrate `opentelemetry-instrumentation-fastapi`.
2. Add a `trace_id` to every WebSocket message.

## 3. Architecture & Code Quality (Priority: Medium)

### Current State
- [x] **Dependency Injection:** Refactored `MemoryStore` to use FastAPI's DI system (Completed).
- [ ] **Type Safety:** Python backend is typed, but Frontend/Backend contract is loose (JSON blobs).
- [x] **Process Management:** Dockerfile and docker-compose.yml created.

### 2026 Best Practices Gap
- **End-to-End Type Safety:** Use Pydantic models to generate TypeScript interfaces automatically for the Frontend.
- **Process Management:** Currently using a shell script (`run_backend.sh`). Production should use `systemd` or `docker-compose`.

### Roadmap
1. Generate `openapi.json` and use `openapi-typescript` to generate frontend types.
2. Create a `docker-compose.yml` for the entire stack (Done).
