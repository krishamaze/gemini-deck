from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_system_status():
    return {
        "xvfb": "unknown",
        "vnc": "unknown",
        "gemini_cli": "detected"
    }
