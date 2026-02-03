"""
AI Accounts router for Gemini Command Deck.
Handles multi-account management with quota tracking and auto-rotation.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import os

from app.services.database import get_db_connection
from app.routers.auth import get_current_user_id

router = APIRouter(prefix="/api/accounts", tags=["AI Accounts"])


# Pydantic models
class AddAPIKeyRequest(BaseModel):
    name: str
    api_key: str
    provider: str = "gemini_api_key"  # gemini_api_key, openai, anthropic
    daily_limit: int = 250


class AIAccountResponse(BaseModel):
    id: int
    name: str
    provider: str
    daily_limit: int
    daily_used: int
    quota_remaining: int
    is_active: bool
    created_at: str


class QuotaStatus(BaseModel):
    total_accounts: int
    active_accounts: int
    total_daily_limit: int
    total_daily_used: int
    total_remaining: int
    best_account_id: Optional[int]


# Helper functions
def reset_daily_quotas_if_needed():
    """Reset daily quotas if it's a new day."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("""
        UPDATE ai_accounts 
        SET daily_used = 0, last_reset = ? 
        WHERE date(last_reset) < date(?)
    """, (today, today))
    conn.commit()
    conn.close()


def get_best_account(user_id: int) -> Optional[dict]:
    """Get the account with the most remaining quota."""
    reset_daily_quotas_if_needed()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM ai_accounts 
        WHERE user_id = ? AND is_active = 1 AND (daily_limit - daily_used) > 0
        ORDER BY (daily_limit - daily_used) DESC
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def increment_usage(account_id: int):
    """Increment usage count for an account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE ai_accounts SET daily_used = daily_used + 1 WHERE id = ?
    """, (account_id,))
    conn.commit()
    conn.close()


def mark_account_error(account_id: int, error_type: str = "429"):
    """Handle account errors (e.g., rate limits)."""
    if error_type == "429":
        # On 429, max out the daily usage to skip this account
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ai_accounts SET daily_used = daily_limit WHERE id = ?
        """, (account_id,))
        conn.commit()
        conn.close()


# API Endpoints
@router.get("", response_model=List[AIAccountResponse])
async def list_accounts(user_id: int = Depends(get_current_user_id)):
    """List all AI accounts for the current user."""
    reset_daily_quotas_if_needed()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, provider, daily_limit, daily_used, is_active, created_at
        FROM ai_accounts WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        AIAccountResponse(
            id=row["id"],
            name=row["name"],
            provider=row["provider"],
            daily_limit=row["daily_limit"],
            daily_used=row["daily_used"],
            quota_remaining=row["daily_limit"] - row["daily_used"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"]
        )
        for row in rows
    ]


@router.post("/add-api-key", response_model=AIAccountResponse)
async def add_api_key(request: AddAPIKeyRequest, user_id: int = Depends(get_current_user_id)):
    """Add a new API key account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO ai_accounts (user_id, name, provider, api_key, daily_limit)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, request.name, request.provider, request.api_key, request.daily_limit))
    
    account_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM ai_accounts WHERE id = ?", (account_id,))
    row = cursor.fetchone()
    conn.close()
    
    return AIAccountResponse(
        id=row["id"],
        name=row["name"],
        provider=row["provider"],
        daily_limit=row["daily_limit"],
        daily_used=row["daily_used"],
        quota_remaining=row["daily_limit"] - row["daily_used"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"]
    )


@router.delete("/{account_id}")
async def delete_account(account_id: int, user_id: int = Depends(get_current_user_id)):
    """Delete an AI account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify ownership
    cursor.execute("SELECT id FROM ai_accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Account not found")
    
    cursor.execute("DELETE FROM ai_accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Account deleted"}


@router.patch("/{account_id}/toggle")
async def toggle_account(account_id: int, user_id: int = Depends(get_current_user_id)):
    """Toggle account active status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE ai_accounts SET is_active = NOT is_active 
        WHERE id = ? AND user_id = ?
    """, (account_id, user_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Account not found")
    
    cursor.execute("SELECT is_active FROM ai_accounts WHERE id = ?", (account_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    
    return {"status": "success", "is_active": bool(row["is_active"])}


@router.get("/quota", response_model=QuotaStatus)
async def get_quota_status(user_id: int = Depends(get_current_user_id)):
    """Get aggregate quota status across all accounts."""
    reset_daily_quotas_if_needed()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
            SUM(daily_limit) as total_limit,
            SUM(daily_used) as total_used
        FROM ai_accounts WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    
    best = get_best_account(user_id)
    conn.close()
    
    total_limit = row["total_limit"] or 0
    total_used = row["total_used"] or 0
    
    return QuotaStatus(
        total_accounts=row["total"] or 0,
        active_accounts=row["active"] or 0,
        total_daily_limit=total_limit,
        total_daily_used=total_used,
        total_remaining=total_limit - total_used,
        best_account_id=best["id"] if best else None
    )


# Export helper functions for use by other modules
__all__ = ["get_best_account", "increment_usage", "mark_account_error"]
