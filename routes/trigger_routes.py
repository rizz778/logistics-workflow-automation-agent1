from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict
from controllers.trigger_controller import (
    process_email_trigger,
    get_incoming_emails_controller,
    get_processed_emails_controller,
    resolve_processed_email_controller
)

router = APIRouter()

class ProcessedEmailRequest(BaseModel):
    run_id: int
    status: str
    edited_data: Optional[Dict] = None
    amendment_draft: Optional[str] = None

# @router.post("/trigger-email")
# async def trigger_email(
#     sender: str = Form(...),
#     subject: str = Form(...),
#     email_body: str = Form(...),
#     file: list[UploadFile] = File(...)
# ):
#     """Endpoint simulating an incoming supplier email.
    
#     Accepts sender, subject, body, and attachment files.
#     """
#     return await process_email_trigger(sender, subject, email_body, file)

@router.post("/incoming")
async def trigger_incoming_email(
    sender: str = Form(...),
    subject: str = Form(...),
    email_body: str = Form(...),
    file: list[UploadFile] = File(...)
):
    """Endpoint simulating an incoming supplier email via /incoming."""
    return await process_email_trigger(sender, subject, email_body, file)

@router.get("/incoming")
async def fetch_incoming_emails():
    """Retrieve all unprocessed/pending runs from incoming emails."""
    return await get_incoming_emails_controller()

@router.get("/processed")
async def fetch_processed_emails():
    """Retrieve all processed/resolved runs from incoming emails."""
    return await get_processed_emails_controller()

@router.post("/processed")
async def resolve_processed_email(request: ProcessedEmailRequest):
    """Resolve/process an incoming email run by updating its status."""
    return await resolve_processed_email_controller(
        run_id=request.run_id,
        status=request.status,
        edited_data=request.edited_data,
        amendment_draft=request.amendment_draft
    )

