from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
import json
import asyncio
import shlex
from app.services.gemini_client import gemini_client
from app.services.memory_store import get_memory_store, MemoryStore

router = APIRouter()

class PlanRequest(BaseModel):
    goal: str

class PlanStep(BaseModel):
    id: int
    action: str
    description: str
    tool: str

class PlanResponse(BaseModel):
    goal: str
    steps: List[PlanStep]

@router.post("/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest, store: MemoryStore = Depends(get_memory_store)):
    """Generates a structured plan."""
    context = store.retrieve_context(request.goal)
    system_instruction = """
    You are an autonomous planner. Break down the user's goal into a logical sequence of steps.
    Output strictly valid JSON with this structure:
    {
        "goal": "rewritten goal",
        "steps": [
            {"id": 1, "action": "ls -la", "description": "list files", "tool": "shell"},
            {"id": 2, "action": "echo 'done'", "description": "finalize", "tool": "shell"}
        ]
    }
    """
    prompt = f"{system_instruction}\n\nUser Goal: {request.goal}"
    try:
        raw_response = await gemini_client.generate_text(prompt, context)
        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")

@router.websocket("/execute")
async def execute_plan_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") != "execute_plan":
                continue

            steps = data.get("steps", [])
            for step in steps:
                step_id = step.get("id")
                cmd = step.get("action")
                tool = step.get("tool")

                await websocket.send_json({"type": "step_start", "id": step_id})

                if tool == "shell":
                    try:
                        proc = await asyncio.create_subprocess_shell(
                            cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )

                        # Stream output
                        async def stream_pipe(pipe):
                            while True:
                                line = await pipe.readline()
                                if not line: break
                                await websocket.send_json({
                                    "type": "step_output", 
                                    "id": step_id, 
                                    "output": line.decode()
                                })

                        await asyncio.gather(
                            stream_pipe(proc.stdout),
                            stream_pipe(proc.stderr)
                        )
                        
                        return_code = await proc.wait()
                        status = "success" if return_code == 0 else "failed"
                        await websocket.send_json({"type": "step_complete", "id": step_id, "status": status})
                        
                        if status == "failed":
                            break # Stop plan on failure

                    except Exception as e:
                        await websocket.send_json({"type": "step_error", "id": step_id, "error": str(e)})
                        break
                else:
                    await websocket.send_json({"type": "step_complete", "id": step_id, "status": "skipped", "reason": "unsupported tool"})

            await websocket.send_json({"type": "plan_done"})

    except WebSocketDisconnect:
        print("Agent disconnected")
    except Exception as e:
        print(f"Agent Error: {e}")

