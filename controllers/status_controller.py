from fastapi import HTTPException
from services.storage import update_run_status

async def handle_update_status(run_id: int, payload: dict) -> dict:
    status = payload.get("status")
    edited_data = payload.get("edited_data")
    amendment_draft = payload.get("amendment_draft")
    
    if not status:
        raise HTTPException(status_code=400, detail="Missing required 'status' field.")
        
    try:
        success = update_run_status(run_id, status, edited_data, amendment_draft)
        if not success:
            raise HTTPException(status_code=404, detail="Run ID not found.")
        return {"status": "success", "message": f"Run {run_id} updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update run: {str(e)}")
