import os
import shutil
from fastapi import UploadFile, HTTPException
from config.settings import settings
from graph.graph import pipeline_graph

async def process_upload(files: list[UploadFile]) -> dict:
    
    # 1. Validate file extensions
    allowed_extensions = (".pdf", ".png", ".jpg", ".jpeg")
    for file in files:
        if not file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not allowed. Only PDF and Image files are allowed.")
        
    # 2. Save all files locally
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_paths = []
    filenames = []
    
    try:
        for file in files:
            path = os.path.join(settings.upload_dir, file.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(path)
            filenames.append(file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {str(e)}")
        
    # 3. Invoke LangGraph pipeline
    try:
        initial_state = {
            "filenames": filenames,
            "file_paths": file_paths,
            "raw_text": "",
            "extracted_data": {},
            "validation_results": {},
            "cross_doc_results": {},
            "decision": "",
            "decision_reason": "",
            "amendment_draft": None,
            "logs": ["Upload Node: Saved all uploaded documents successfully."]
        }
        
        final_state = pipeline_graph.invoke(initial_state)
        
        # Parse the assigned SQLite database ID from logs to return to client
        db_log = [log for log in final_state["logs"] if "DB ID:" in log]
        run_id = None
        if db_log:
            try:
                run_id = int(db_log[0].split("DB ID:")[-1].strip())
            except Exception:
                pass
                
        return {
            "run_id": run_id,
            "id": run_id,
            "filenames": final_state.get("filenames", filenames),
            "filename": ", ".join(final_state.get("filenames", filenames)),
            "extracted_data": final_state["extracted_data"],
            "validation_results": final_state["validation_results"],
            "cross_doc_results": final_state.get("cross_doc_results", {"is_consistent": True, "discrepancies": []}),
            "decision": final_state["decision"],
            "decision_reason": final_state["decision_reason"],
            "amendment_draft": final_state["amendment_draft"],
            "logs": final_state["logs"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")
