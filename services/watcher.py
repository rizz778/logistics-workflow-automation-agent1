import os
import sys
import json
import shutil
import asyncio
from graph.graph import pipeline_graph
from config.settings import settings

# Setup paths relative to backend directory
def get_absolute_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.abspath(os.path.join(backend_dir, path))

INBOX_DIR = get_absolute_path(settings.inbox_dir)
PROCESSED_DIR = get_absolute_path(settings.processed_dir)

async def watch_inbox_loop():
    """Asynchronous background loop to check the inbox/ directory for new folders."""
    os.makedirs(INBOX_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    print(f"Inbox Watcher: Polling for folders in: {INBOX_DIR}")
    
    while True:
        try:
            # List all subfolders in the inbox directory
            for folder_name in os.listdir(INBOX_DIR):
                folder_path = os.path.join(INBOX_DIR, folder_name)
                if not os.path.isdir(folder_path):
                    continue
                
                # Check for manifest.json as the completion trigger
                manifest_path = os.path.join(folder_path, "manifest.json")
                if os.path.exists(manifest_path):
                    print(f"Inbox Watcher: Found trigger manifest in '{folder_name}'...")
                    
                    # Wait briefly to ensure files are fully flushed to disk
                    await asyncio.sleep(1.5)
                    
                    # Read manifest
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            manifest = json.load(f)
                    except Exception as e:
                        print(f"Inbox Watcher: Error parsing manifest.json in {folder_name}: {e}")
                        continue
                    
                    # Collect attachments (PDFs/Images)
                    allowed_ext = (".pdf", ".png", ".jpg", ".jpeg")
                    doc_files = [
                        f for f in os.listdir(folder_path)
                        if f.lower().endswith(allowed_ext)
                    ]
                    
                    if not doc_files:
                        print(f"Inbox Watcher: No documents found in '{folder_name}'. Archiving metadata only.")
                    
                    file_paths = [os.path.join(folder_path, name) for name in doc_files]
                    
                    # Construct initial state with email trigger details
                    initial_state = {
                        "filenames": doc_files,
                        "file_paths": file_paths,
                        "raw_text": "",
                        "extracted_data": {},
                        "validation_results": {},
                        "cross_doc_results": {},
                        "decision": "",
                        "decision_reason": "",
                        "amendment_draft": None,
                        "logs": [f"Inbox Watcher: Detected simulated email drop for '{folder_name}'."],
                        "source": "inbox",
                        "email_sender": manifest.get("sender", "unknown@supplier.com"),
                        "email_subject": manifest.get("subject", "No Subject"),
                        "email_body": manifest.get("email_body", ""),
                        "received_at": manifest.get("received_at", "")
                    }
                    
                    # Execute Graph Pipeline asynchronously in thread pool to avoid blocking event loop
                    loop = asyncio.get_running_loop()
                    print(f"Inbox Watcher: Executing graph pipeline for shipment '{folder_name}'...")
                    final_state = await loop.run_in_executor(None, pipeline_graph.invoke, initial_state)
                    print(f"Inbox Watcher: Completed shipment '{folder_name}'. Decision: {final_state['decision']}")
                    
                    # Move folder to /processed/ to clear the queue
                    target_processed = os.path.join(PROCESSED_DIR, folder_name)
                    if os.path.exists(target_processed):
                        shutil.rmtree(target_processed)
                    
                    try:
                        shutil.move(folder_path, PROCESSED_DIR)
                        print(f"Inbox Watcher: Folder '{folder_name}' archived to processed/.")
                    except Exception as move_err:
                        print(f"Inbox Watcher: Failed to move folder to processed: {move_err}")
                        
        except Exception as loop_ex:
            print(f"Inbox Watcher: Error in watcher loop: {loop_ex}")
            
        await asyncio.sleep(3)

def start_watcher(app):
    """Registers watcher loop as a background task on startup."""
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(watch_inbox_loop())
