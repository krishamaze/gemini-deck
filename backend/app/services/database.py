"""
Database models and initialization for Gemini Command Deck.
Using SQLite for development, can migrate to PostgreSQL later.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
import os

# Database path - use environment variable or default
DB_PATH = os.environ.get("GEMINI_DECK_DB", ".gemini_deck.db")


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with all required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            picture TEXT,
            google_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # AI Accounts table (multi-key support)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,  -- 'gemini_oauth', 'gemini_api_key', 'openai', etc.
            name TEXT,               -- User-friendly name like "Personal Gemini"
            token TEXT,              -- OAuth access token (encrypted in production)
            refresh_token TEXT,      -- OAuth refresh token
            api_key TEXT,            -- API key (encrypted in production)
            daily_limit INTEGER DEFAULT 1000,
            daily_used INTEGER DEFAULT 0,
            last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Memories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            type TEXT DEFAULT 'general',  -- 'thought', 'observation', 'decision', 'action', 'skill'
            metadata TEXT,  -- JSON string for additional data
            embedding_id TEXT,  -- Reference to ChromaDB if using vector search
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Skills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            definition TEXT NOT NULL,  -- JSON or code defining the skill
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Sandboxes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sandboxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,  -- 'docker', 'daytona', 'local'
            name TEXT,
            connection_url TEXT,
            vnc_url TEXT,
            status TEXT DEFAULT 'disconnected',  -- 'connected', 'disconnected', 'error'
            specs TEXT,  -- JSON with CPU, RAM, etc.
            last_heartbeat TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Sessions table (for JWT refresh tokens)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            refresh_token TEXT UNIQUE NOT NULL,
            device_info TEXT,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")


# User operations
def create_user(email: str, name: str = None, picture: str = None, google_id: str = None) -> int:
    """Create a new user and return their ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (email, name, picture, google_id)
        VALUES (?, ?, ?, ?)
    """, (email, name, picture, google_id))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str) -> Optional[dict]:
    """Get a user by email."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_google_id(google_id: str) -> Optional[dict]:
    """Get a user by Google ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_or_create_user(email: str, name: str = None, picture: str = None, google_id: str = None) -> dict:
    """Get existing user or create new one."""
    user = get_user_by_google_id(google_id) if google_id else get_user_by_email(email)
    if user:
        return user
    user_id = create_user(email, name, picture, google_id)
    return {"id": user_id, "email": email, "name": name, "picture": picture, "google_id": google_id}


# Initialize on import if running as main
if __name__ == "__main__":
    init_db()
