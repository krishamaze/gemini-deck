"""
Sandbox router for Gemini Command Deck.
Allows users to connect their own VMs (Docker, Daytona, or custom VNC).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import httpx

from app.services.database import get_db_connection
from app.routers.auth import get_current_user_id

router = APIRouter(prefix="/api/sandbox", tags=["Sandbox"])


# Pydantic models
class AddSandboxRequest(BaseModel):
    name: str
    type: str = "docker"  # docker, daytona, custom
    connection_url: str   # ws://user-machine:6080 or daytona URL
    vnc_url: Optional[str] = None  # Optional separate VNC URL
    specs: Optional[dict] = None   # {"cpu": "4 cores", "ram": "8GB"}


class SandboxResponse(BaseModel):
    id: int
    name: str
    type: str
    connection_url: str
    vnc_url: Optional[str]
    status: str
    specs: Optional[dict]
    last_heartbeat: Optional[str]
    created_at: str


class HealthCheckResponse(BaseModel):
    id: int
    name: str
    status: str  # connected, disconnected, error
    latency_ms: Optional[int]
    message: Optional[str]


# API Endpoints
@router.get("", response_model=List[SandboxResponse])
async def list_sandboxes(user_id: int = Depends(get_current_user_id)):
    """List all sandboxes for the current user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, type, connection_url, vnc_url, status, specs, last_heartbeat, created_at
        FROM sandboxes WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        specs = None
        if row["specs"]:
            import json
            try:
                specs = json.loads(row["specs"])
            except:
                pass
        
        result.append(SandboxResponse(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            connection_url=row["connection_url"],
            vnc_url=row["vnc_url"],
            status=row["status"],
            specs=specs,
            last_heartbeat=row["last_heartbeat"],
            created_at=row["created_at"]
        ))
    
    return result


@router.post("/connect", response_model=SandboxResponse)
async def add_sandbox(request: AddSandboxRequest, user_id: int = Depends(get_current_user_id)):
    """Add a new sandbox connection."""
    import json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    specs_json = json.dumps(request.specs) if request.specs else None
    
    cursor.execute("""
        INSERT INTO sandboxes (user_id, name, type, connection_url, vnc_url, specs, status)
        VALUES (?, ?, ?, ?, ?, ?, 'disconnected')
    """, (user_id, request.name, request.type, request.connection_url, request.vnc_url, specs_json))
    
    sandbox_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM sandboxes WHERE id = ?", (sandbox_id,))
    row = cursor.fetchone()
    conn.close()
    
    specs = None
    if row["specs"]:
        try:
            specs = json.loads(row["specs"])
        except:
            pass
    
    return SandboxResponse(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        connection_url=row["connection_url"],
        vnc_url=row["vnc_url"],
        status=row["status"],
        specs=specs,
        last_heartbeat=row["last_heartbeat"],
        created_at=row["created_at"]
    )


@router.delete("/{sandbox_id}")
async def delete_sandbox(sandbox_id: int, user_id: int = Depends(get_current_user_id)):
    """Delete a sandbox."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM sandboxes WHERE id = ? AND user_id = ?", (sandbox_id, user_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    cursor.execute("DELETE FROM sandboxes WHERE id = ?", (sandbox_id,))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Sandbox deleted"}


@router.post("/{sandbox_id}/check", response_model=HealthCheckResponse)
async def check_sandbox_health(sandbox_id: int, user_id: int = Depends(get_current_user_id)):
    """Check if a sandbox is reachable."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sandboxes WHERE id = ? AND user_id = ?", (sandbox_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    # Try to reach the sandbox
    url = row["connection_url"]
    status = "disconnected"
    latency_ms = None
    message = None
    
    try:
        # Convert ws:// to http:// for health check
        check_url = url.replace("ws://", "http://").replace("wss://", "https://")
        
        import time
        start = time.time()
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(check_url)
            latency_ms = int((time.time() - start) * 1000)
            
            if response.status_code < 500:
                status = "connected"
                message = f"Reachable (HTTP {response.status_code})"
            else:
                status = "error"
                message = f"Server error (HTTP {response.status_code})"
                
    except httpx.ConnectError:
        status = "disconnected"
        message = "Connection refused - is the sandbox running?"
    except httpx.TimeoutException:
        status = "disconnected"
        message = "Connection timeout after 5 seconds"
    except Exception as e:
        status = "error"
        message = str(e)
    
    # Update status in database
    cursor.execute("""
        UPDATE sandboxes SET status = ?, last_heartbeat = ?
        WHERE id = ?
    """, (status, datetime.utcnow().isoformat(), sandbox_id))
    conn.commit()
    conn.close()
    
    return HealthCheckResponse(
        id=sandbox_id,
        name=row["name"],
        status=status,
        latency_ms=latency_ms,
        message=message
    )


@router.get("/active", response_model=Optional[SandboxResponse])
async def get_active_sandbox(user_id: int = Depends(get_current_user_id)):
    """Get the user's most recently connected sandbox."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM sandboxes 
        WHERE user_id = ? AND status = 'connected'
        ORDER BY last_heartbeat DESC
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    import json
    specs = None
    if row["specs"]:
        try:
            specs = json.loads(row["specs"])
        except:
            pass
    
    return SandboxResponse(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        connection_url=row["connection_url"],
        vnc_url=row["vnc_url"],
        status=row["status"],
        specs=specs,
        last_heartbeat=row["last_heartbeat"],
        created_at=row["created_at"]
    )
