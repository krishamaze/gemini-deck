from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.memory_store import get_memory_store, MemoryStore

router = APIRouter()

class Interaction(BaseModel):
    user_prompt: str
    ai_response: str

@router.get("/history")
async def get_memory_history(store: MemoryStore = Depends(get_memory_store)):
    """Retrieve recent memory entries."""
    data = store.get_recent(limit=20)
    return {
        "count": len(data['ids']),
        "ids": data['ids'],
        "metadatas": data['metadatas']
    }

@router.post("/add")
async def add_memory(interaction: Interaction, store: MemoryStore = Depends(get_memory_store)):
    """Manually add an interaction to memory."""
    try:
        doc_id = store.add_interaction(interaction.user_prompt, interaction.ai_response)
        return {"status": "success", "id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_memory(query: str, store: MemoryStore = Depends(get_memory_store)):
    """Semantic search for context."""
    results = store.retrieve_context(query)
    return {"results": results}