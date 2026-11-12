import os
import sys
import json
from dotenv import load_dotenv

# Ensure we resolve imports relative to the backend directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.state import PipelineState
from agents.validator import validator_agent
from agents.router import router_agent
from services.storage import init_db

def run_tests():
    load_dotenv()
    init_db()
    
    # Test Case 1: Consistent documents (Matching consignee, weight, etc.)
    state_consistent: PipelineState = {
        "filenames": ["bol.pdf", "invoice.pdf"],
        "file_paths": ["data/uploads/bol.pdf", "data/uploads/invoice.pdf"],
        "raw_text": "",
        "extracted_data": {
            "bol.pdf": {
                "consignee_name": {"value": "Nova Logistics Ltd", "confidence": 0.95, "source_snippet": "Consignee: Nova Logistics Ltd"},
                "gross_weight": {"value": "1,250.50 kg", "confidence": 0.95, "source_snippet": "1,250.50 kg"},
                "hs_code": {"value": "8708.29.90", "confidence": 0.95, "source_snippet": "HS Code: 8708.29.90"},
                "incoterms": {"value": "FOB", "confidence": 0.90, "source_snippet": "FOB"},
                "invoice_number": {"value": "INV-2026-9901", "confidence": 0.90, "source_snippet": "INV-2026-9901"}
            },
            "invoice.pdf": {
                "consignee_name": {"value": "Nova Logistics Ltd", "confidence": 0.98, "source_snippet": "Nova Logistics Ltd"},
                "gross_weight": {"value": "1250.5 kg", "confidence": 0.98, "source_snippet": "Gross Weight: 1250.5"},
                "hs_code": {"value": "8708.29.90", "confidence": 0.98, "source_snippet": "8708.29.90"},
                "incoterms": {"value": "FOB", "confidence": 0.95, "source_snippet": "FOB"},
                "invoice_number": {"value": "INV-2026-9901", "confidence": 0.99, "source_snippet": "INV-2026-9901"}
            }
        },
        "validation_results": {},
        "cross_doc_results": {},
        "decision": "",
        "decision_reason": "",
        "amendment_draft": None,
        "logs": []
    }
    
    print("\n--- Running Test 1: Consistent Multi-Doc Shipment ---")
    val_state = validator_agent(state_consistent)
    print("Cross-Document Consistency Result:")
    print(json.dumps(val_state["cross_doc_results"], indent=2))
    assert val_state["cross_doc_results"]["is_consistent"] is True, "Expected documents to be consistent"
    
    route_state = router_agent(val_state)
    print(f"Workflow Decision: {route_state['decision']}")
    print(f"Reasoning:\n{route_state['decision_reason']}\n")
    
    # Test Case 2: Mismatched gross weights across documents
    state_weight_mismatch: PipelineState = {
        "filenames": ["bol.pdf", "invoice.pdf"],
        "file_paths": ["data/uploads/bol.pdf", "data/uploads/invoice.pdf"],
        "raw_text": "",
        "extracted_data": {
            "bol.pdf": {
                "consignee_name": {"value": "Nova Logistics Ltd", "confidence": 0.95, "source_snippet": "Consignee: Nova Logistics Ltd"},
                "gross_weight": {"value": "1,250.50 kg", "confidence": 0.95, "source_snippet": "1,250.50 kg"},
                "hs_code": {"value": "8708.29.90", "confidence": 0.95, "source_snippet": "HS Code: 8708.29.90"},
                "incoterms": {"value": "FOB", "confidence": 0.90, "source_snippet": "FOB"},
                "invoice_number": {"value": "INV-2026-9901", "confidence": 0.90, "source_snippet": "INV-2026-9901"}
            },
            "invoice.pdf": {
                "consignee_name": {"value": "Nova Logistics Ltd", "confidence": 0.98, "source_snippet": "Nova Logistics Ltd"},
                "gross_weight": {"value": "1,500.00 kg", "confidence": 0.98, "source_snippet": "Gross Weight: 1500.00 kg"},
                "hs_code": {"value": "8708.29.90", "confidence": 0.98, "source_snippet": "8708.29.90"},
                "incoterms": {"value": "FOB", "confidence": 0.95, "source_snippet": "FOB"},
                "invoice_number": {"value": "INV-2026-9901", "confidence": 0.99, "source_snippet": "INV-2026-9901"}
            }
        },
        "validation_results": {},
        "cross_doc_results": {},
        "decision": "",
        "decision_reason": "",
        "amendment_draft": None,
        "logs": []
    }
    
    print("\n--- Running Test 2: Mismatched Gross Weights ---")
    val_state2 = validator_agent(state_weight_mismatch)
    print("Cross-Document Consistency Result:")
    print(json.dumps(val_state2["cross_doc_results"], indent=2))
    assert val_state2["cross_doc_results"]["is_consistent"] is False, "Expected weight discrepancy"
    
    route_state2 = router_agent(val_state2)
    print(f"Workflow Decision: {route_state2['decision']}")
    print(f"Reasoning:\n{route_state2['decision_reason']}")
    print(f"Amendment Email Draft:\n{route_state2['amendment_draft']}\n")

if __name__ == "__main__":
    run_tests()
