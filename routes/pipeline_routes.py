from fastapi import APIRouter, UploadFile, File
from controllers.upload_controller import process_upload
from controllers.rules_controller import get_rules
from controllers.history_controller import get_history
from controllers.analytics_controller import get_run_analytics
from controllers.status_controller import handle_update_status
from controllers.query_controller import handle_database_query
from pydantic import BaseModel
from typing import Optional, Dict

router = APIRouter()

class UpdateStatusRequest(BaseModel):
    status: str
    edited_data: Optional[Dict] = None
    amendment_draft: Optional[str] = None

class QueryRequest(BaseModel):
    query: str

#endpoint for uploading user doc for checking

@router.post("/upload")
async def upload_document(file: list[UploadFile] = File(...)):
    return await process_upload(file)

#endpoint for fetching rules required on audit page 
@router.get("/rules")
async def fetch_rules():
    return await get_rules()

#endpoint for fetching doc upload history required for showing table to the cg
@router.get("/history")
async def fetch_history():
    return await get_history()

#endpoint fetches data shows analytics to cg
@router.get("/analytics")
async def fetch_analytics():
    return await get_run_analytics()

#endpoint for updating data incase some fieeld extraction goes wrong through gemini
@router.post("/update-status/{run_id}")
async def update_status(run_id: int, request: UpdateStatusRequest):
    return await handle_update_status(run_id, request.dict(exclude_unset=True))

#endpoint for processing user's natural language query query
@router.post("/query")
async def query_pipeline(request: QueryRequest):
    return await handle_database_query(request.dict())

