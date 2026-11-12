from fastapi import HTTPException
from services.storage import get_all_runs

async def get_history() -> list:
    try:
        return get_all_runs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve runs history: {str(e)}")
