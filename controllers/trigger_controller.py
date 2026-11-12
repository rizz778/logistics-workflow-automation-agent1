import os
import json
import shutil
from datetime import datetime
from fastapi import UploadFile, HTTPException
from config.settings import settings
from services.storage import get_incoming_runs, get_processed_runs, update_run_status



async def process_email_trigger(
    sender: str,
    subject: str,
    email_body: str,
    files: list[UploadFile]
) -> dict:
    """Saves email attachments and manifest to watched inbox folder to trigger watcher."""
    # 1. Validate file extensions
    allowed_extensions = (".pdf", ".png", ".jpg", ".jpeg")
    for file in files:
        if not file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} is not allowed. Only PDF and Image files are allowed."
            )
            
    # 2. Setup directory paths
    def get_absolute_path(path: str) -> str:
        if os.path.isabs(path):
            return path
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.abspath(os.path.join(backend_dir, path))

    inbox_dir = get_absolute_path(settings.inbox_dir)
    
    # Create unique folder name using timestamp to prevent collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shipment_folder_name = f"shipment_{timestamp}"
    folder_path = os.path.join(inbox_dir, shipment_folder_name)
    
    os.makedirs(folder_path, exist_ok=True)
    
    try:
        # 3. Save attachment files first
        for file in files:
            file_path = os.path.join(folder_path, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
        # 4. Write manifest.json last to ensure atomic watcher pickup
        manifest = {
            "sender": sender,
            "customer_name": "Nova Enterprise Customer",
            "subject": subject,
            "email_body": email_body,
            "received_at": datetime.utcnow().isoformat() + "Z"
        }
        
        manifest_path = os.path.join(folder_path, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            
        return {
            "success": True,
            "message": f"Email queued successfully. Created inbox folder: {shipment_folder_name}"
        }
        
    except Exception as e:
        # Clean up directory if we failed mid-write
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        raise HTTPException(status_code=500, detail=f"Failed to trigger email queue: {str(e)}")




async def get_incoming_emails_controller() -> list[dict]:
    try:
        return get_incoming_runs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch incoming emails: {str(e)}")




async def get_processed_emails_controller() -> list[dict]:
    try:
        return get_processed_runs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch processed emails: {str(e)}")




async def resolve_processed_email_controller(
    run_id: int, 
    status: str, 
    edited_data: dict | None = None, 
    amendment_draft: str | None = None
) -> dict:
    try:
        success = update_run_status(run_id, status, edited_data, amendment_draft)
        if not success:
            raise HTTPException(status_code=404, detail="Run ID not found.")
        return {"status": "success", "message": f"Email run {run_id} resolved/processed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve email run: {str(e)}")

