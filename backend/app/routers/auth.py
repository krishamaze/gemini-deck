"""
Authentication router for Gemini Command Deck.
Handles Google OAuth login and JWT token management.
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import os
import secrets
import httpx
from jose import jwt, JWTError

from app.services.database import get_or_create_user, get_db_connection

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Configuration - use environment variables in production
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/callback")

# Frontend URL for redirect after login
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserInfo(BaseModel):
    id: int
    email: str
    name: Optional[str]
    picture: Optional[str]


def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


@router.get("/google")
async def google_login():
    """
    Initiate Google OAuth login.
    Redirects user to Google's OAuth consent screen.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID environment variable.")
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Google OAuth URL
    oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        f"state={state}&"
        "access_type=offline&"
        "prompt=consent"
    )
    
    return RedirectResponse(url=oauth_url)


@router.get("/callback")
async def google_callback(code: str = None, state: str = None, error: str = None):
    """
    Handle Google OAuth callback.
    Exchanges code for tokens, creates/updates user, and returns JWT.
    """
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error={error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        # Get user info from Google
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        userinfo = userinfo_response.json()
    
    # Create or get user
    user = get_or_create_user(
        email=userinfo.get("email"),
        name=userinfo.get("name"),
        picture=userinfo.get("picture"),
        google_id=userinfo.get("id")
    )
    
    # Create JWT token
    jwt_token = create_access_token(user["id"], user["email"])
    
    # Redirect to frontend with token
    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={jwt_token}"
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(request: Request):
    """
    Get current authenticated user info.
    Requires Authorization header with Bearer token.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = int(payload.get("sub"))
    
    # Get full user info from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, picture FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserInfo(**dict(row))


@router.post("/logout")
async def logout(request: Request):
    """
    Logout user.
    For JWT-based auth, this is mostly client-side (delete token).
    We can also invalidate refresh tokens here if implemented.
    """
    return {"status": "success", "message": "Logged out"}


# Dependency for protected routes
async def get_current_user_id(request: Request) -> int:
    """
    FastAPI dependency to get current user ID from JWT token.
    Use as: current_user_id: int = Depends(get_current_user_id)
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return int(payload.get("sub"))
