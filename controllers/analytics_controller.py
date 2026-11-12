from fastapi import HTTPException
from services.storage import get_analytics

async def get_run_analytics() -> dict:
    try:
        return get_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analytics: {str(e)}")
