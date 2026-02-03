from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import json
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
    """
    Generates a structured plan for a given goal.
    """
    # 1. Retrieve relevant skills/memory
    context = store.retrieve_context(request.goal)
    
    # 2. Construct Planning Prompt
    system_instruction = """
    You are an autonomous planner. Break down the user's goal into a logical sequence of steps.
    Output strictly valid JSON with this structure:
    {
        "goal": "rewritten goal",
        "steps": [
            {"id": 1, "action": "cmd_run", "description": "install dependencies", "tool": "shell"},
            {"id": 2, "action": "file_write", "description": "create config", "tool": "editor"}
        ]
    }
    Do not include markdown formatting like ```json.
    """
    
    prompt = f"{system_instruction}\n\nUser Goal: {request.goal}"
    
    # 3. Call Model
    try:
        raw_response = await gemini_client.generate_text(prompt, context)
        # Clean response (sometimes models add markdown)
        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        plan_data = json.loads(clean_json)
        return plan_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")

