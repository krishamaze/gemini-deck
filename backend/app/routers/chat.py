from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.services.gemini_client import gemini_client
from app.services.memory_store import get_memory_store, MemoryStore
from app.services.security import get_security_service, SecurityService
import json
import uuid

router = APIRouter()

@router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket, 
    store: MemoryStore = Depends(get_memory_store),
    security: SecurityService = Depends(get_security_service)
):
    await websocket.accept()
    try:
        while True:
            # Receive input from client
            data_json = await websocket.receive_text()
            data = json.loads(data_json)
            user_prompt = data.get("prompt")
            
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
            
            # 2. Stream Response
            full_response_text = ""
            
            # Send start event
            await websocket.send_json({
                "type": "start", 
                "context_used": len(relevant_memories),
                "trace_id": trace_id
            })

            async for chunk in gemini_client.stream_chat(user_prompt, relevant_memories):
                # Try to parse if it's JSON from CLI, otherwise treat as raw text
                try:
                    chunk_data = json.loads(chunk)
                    text_chunk = chunk_data.get("text", "") 
                except:
                    text_chunk = chunk

                full_response_text += text_chunk
                await websocket.send_json({
                    "type": "chunk", 
                    "content": text_chunk,
                    "trace_id": trace_id
                })

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
        print(f"Error: {e}")
        await websocket.close()