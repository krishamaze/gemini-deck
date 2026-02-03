from fastapi import APIRouter

router = APIRouter()

@router.get("/history")
async def get_memory_history():
    return {"status": "memory_service_initialized", "entries": []}
