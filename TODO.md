# Gemini Command Deck - TODO

> Last Updated: 2026-02-03T05:19:27Z

---

## 🔴 Priority 1: Critical Fixes (Backend Breaking)

### 1.1 Fix Gemini CLI Command Syntax
**File:** `backend/app/services/gemini_client.py`
**Issue:** Uses deprecated `--headless` flag
**Fix:**
```python
# Line 8 - Change:
self.command = ["gemini", "--headless"]
# To:
self.command = ["gemini", "-o", "stream-json"]
```

### 1.2 Fix Prompt Argument
**File:** `backend/app/services/gemini_client.py`
**Issue:** Uses `--prompt` instead of `-p`
**Fix:**
```python
# Lines 20, 58 - Change "--prompt" to "-p"
```

---

## 🟡 Priority 2: Recommended Improvements

### 2.1 Add GEMINI.md Context Loading
Load persistent system instructions from `~/.gemini/GEMINI.md` or `~/GEMINI.md`
- Prepend to every prompt for consistent behavior

### 2.2 Add Retry Logic with Exponential Backoff
Handle 429 rate limit errors gracefully
- Retry up to 3 times with exponential delay

### 2.3 Add Metadata Filtering to Memory
ChromaDB queries should support:
- Timestamp filtering (last 24h, last week)
- Topic/category filtering

### 2.4 Memory Summarization (Meta-fy)
Before storing interactions, summarize long responses
- Reduces token usage on retrieval
- Improves semantic search quality

---

## 🟢 Priority 3: UI/UX Enhancements

### 3.1 Add STOP Button for Agent
Allow user to interrupt autonomous agent execution

### 3.2 Add Diff View for File Changes
Show before/after when agent modifies files

### 3.3 Add Thought Logs Panel
Display agent's reasoning process in real-time

---

## ✅ Completed
- [x] Frontend components synced (2026-02-03)
- [x] Gemini CLI v0.26.0 confirmed working
- [x] ChromaDB memory store implemented
- [x] Security middleware implemented

---
