import os
import sys
import json
from dotenv import load_dotenv

# Ensure we resolve imports relative to the backend directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.state import PipelineState
from agents.extractor import extract_agent

def test_multidoc_extraction():
    load_dotenv()
    
    clean_path = os.path.join("sample_docs", "clean_invoice.pdf")
    if not os.path.exists(clean_path):
        print(f"Error: Sample file not found at {clean_path}")
        return
        
    # Mock a pipeline state containing two files
    state: PipelineState = {
        "filenames": ["invoice_1.pdf", "invoice_2.pdf"],
        "file_paths": [clean_path, clean_path],
        "raw_text": "",
        "extracted_data": {},
        "validation_results": {},
        "cross_doc_results": {},
        "decision": "",
        "decision_reason": "",
        "amendment_draft": None,
        "logs": []
    }
    
    print("Triggering concurrent multi-document extraction test...")
    final_state = extract_agent(state)
    
    print("\n--- Agent Output Logs ---")
    for log in final_state["logs"]:
        print(f"  {log}")
        
    print("\n--- Extracted Data Dict Keys ---")
    print(f"  {list(final_state['extracted_data'].keys())}")
    
    print("\n--- invoice_1.pdf Sample Output ---")
    print(json.dumps(final_state["extracted_data"].get("invoice_1.pdf"), indent=2))

if __name__ == "__main__":
    test_multidoc_extraction()
