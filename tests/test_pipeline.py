import os
import sys
import json

# Ensure backend folder is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.graph import pipeline_graph
from utils.generate_samples import generate_messy_pdf
from services.storage import init_db, get_pipeline_run

def run_pipeline_test():
    # 1. Initialize the database
    init_db()
    
    sample_file = "backend/sample_docs/messy_invoice.pdf"
    
    # Generate the messy PDF using the utils function
    generate_messy_pdf(sample_file)
    
    print(f"\nInvoking Multi-Agent Pipeline Graph on: {sample_file}...")
    
    initial_state = {
        "filename": os.path.basename(sample_file),
        "file_path": sample_file,
        "raw_text": "",
        "extracted_data": {},
        "validation_results": {},
        "decision": "",
        "decision_reason": "",
        "amendment_draft": None,
        "logs": []
    }
    
    try:
        final_state = pipeline_graph.invoke(initial_state)
    except Exception as e:
        print(f"\nExecution Failed: {e}")
        return

    print("\n==========================================")
    print("        PIPELINE RUN COMPLETED           ")
    print("==========================================")
    print(f"File Name: {final_state['filename']}")
    print(f"Decision Outcome: {final_state['decision']}")
    print(f"Reasoning:\n{final_state['decision_reason']}\n")
    
    if final_state['amendment_draft']:
        print(f"Draft Message/Notes:\n{final_state['amendment_draft']}\n")
        
    print("Field-by-Field Validation Results:")
    print(json.dumps(final_state['validation_results'], indent=2))
    
    print("\nOrchestrator Execution Logs:")
    for log in final_state['logs']:
        print(f"- {log}")
        
    # 2. Verify Database Storage
    # Extract the last DB ID from the logs
    db_log = [log for log in final_state['logs'] if "DB ID:" in log]
    if db_log:
        try:
            db_id = int(db_log[0].split("DB ID:")[-1].strip())
            saved_run = get_pipeline_run(db_id)
            print("\n==========================================")
            print("         DATABASE VERIFICATION            ")
            print("==========================================")
            print(f"Successfully loaded DB Row ID: {saved_run['id']}")
            print(f"Stored Filename: {saved_run['filename']}")
            print(f"Stored Decision: {saved_run['decision']}")
            print(f"Stored Status: {saved_run['status']}")
            print(f"Stored Consignee (from DB JSON): {saved_run['extracted_data']['consignee_name']['value']}")
        except Exception as e_db:
            print(f"\n[Database Check] Failed to read database entry: {e_db}")

if __name__ == "__main__":
    run_pipeline_test()
