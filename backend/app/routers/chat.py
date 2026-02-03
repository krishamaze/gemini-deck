from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.services.gemini_client import GeminiAPIClient, MultiAccountGeminiClient, QuotaExceededError
from app.services.memory_store import get_memory_store, MemoryStore
from app.services.security import get_security_service, SecurityService
from app.routers.auth import verify_token
import json
import uuid
import os

router = APIRouter()


def get_user_id_from_token(token: str) -> int | None:
    """Extract user ID from JWT token."""
    if not token:
        return None
    payload = verify_token(token)
    if payload:
        return int(payload.get("sub"))
    return None


@router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(default=None),
    api_key: str = Query(default=None),
    store: MemoryStore = Depends(get_memory_store),
    security: SecurityService = Depends(get_security_service)
):
    """
    WebSocket endpoint for streaming chat with Gemini.
    
    Supports three modes:
    1. Authenticated: Uses multi-account system with auto-rotation (token param)
    2. Direct API key: Uses user-provided API key (api_key param)
    3. Environment fallback: Uses GEMINI_API_KEY environment variable
    
    Client should connect with:
    - ws://host/api/chat/stream?token=<jwt_token> (authenticated)
    - ws://host/api/chat/stream?api_key=<gemini_api_key> (BYOK)
    """
    await websocket.accept()
    
    # Determine which client to use (priority order)
    user_id = get_user_id_from_token(token)
    
    if user_id:
        # Authenticated user - use multi-account client
        client = MultiAccountGeminiClient(user_id)
    elif api_key:
        # User provided their own API key (BYOK)
        client = GeminiAPIClient(api_key)
    else:
        # Fallback to environment variable
        env_api_key = os.environ.get("GEMINI_API_KEY")
        if not env_api_key:
            await websocket.send_json({
                "type": "error",
                "content": "No API key configured. Click Settings to add your Gemini API key.",
                "trace_id": str(uuid.uuid4())
            })
            await websocket.close()
            return
        client = GeminiAPIClient(env_api_key)
    
    try:
        while True:
            # Receive input from client
            data_json = await websocket.receive_text()
            data = json.loads(data_json)
            user_prompt = data.get("prompt") or data.get("content") or data.get("message")
            
            if not user_prompt:
                continue
            
            trace_id = str(uuid.uuid4())

            # 0. Security Check
            is_safe, reason = security.analyze_prompt(user_prompt)
            if not is_safe:
                await websocket.send_json({"type": "error", "content": reason, "trace_id": trace_id})
                continue

            # 1. Retrieve Context
            relevant_memories = store.retrieve_context(user_prompt)
            context_list = [m.get("content", str(m)) for m in relevant_memories] if relevant_memories else []
            
            # 2. Stream Response
            full_response_text = ""
            
            # Send start event
            await websocket.send_json({
                "type": "start", 
                "context_used": len(relevant_memories),
                "trace_id": trace_id,
                "authenticated": user_id is not None
            })

            try:
                async for chunk in client.stream(user_prompt, context_list):
                    full_response_text += chunk
                    await websocket.send_json({
                        "type": "chunk", 
                        "content": chunk,
                        "trace_id": trace_id
                    })
                    
            except QuotaExceededError as e:
                await websocket.send_json({
                    "type": "error",
                    "content": "All API accounts have exceeded their quota. Please add more accounts or wait for quota reset.",
                    "trace_id": trace_id
                })
                continue
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "content": f"AI generation error: {str(e)}",
                    "trace_id": trace_id
                })
                continue

            # 3. Save to Memory
            store.add_interaction(user_prompt, full_response_text)
            
            # Send done event
            await websocket.send_json({
                "type": "done", 
                "full_text": full_response_text,
                "trace_id": trace_id
            })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass