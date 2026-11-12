import os
import sys
import json
from fastapi.testclient import TestClient

# Ensure we resolve imports relative to the backend directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.storage import init_db, get_all_runs, save_pipeline_run

client = TestClient(app)

def test_incoming_processed_endpoints():
    init_db()
    
    # 1. Verify GET /pipeline/incoming and GET /pipeline/processed work and return lists
    response = client.get("/pipeline/incoming")
    assert response.status_code == 200
    incoming_list = response.json()
    assert isinstance(incoming_list, list)

    response = client.get("/pipeline/processed")
    assert response.status_code == 200
    processed_list = response.json()
    assert isinstance(processed_list, list)

    # 2. Insert a mock run with source='inbox' and status='pending_review'
    run_id = save_pipeline_run(
        filename="invoice.pdf",
        extracted_data={"consignee_name": {"value": "Test Consignee", "confidence": 1.0, "source_snippet": None}},
        validation_results={},
        decision="flag_review",
        decision_reason="Test reason",
        amendment_draft="Draft email",
        status="pending_review",
        source="inbox",
        email_sender="sender@example.com",
        email_metadata_json=json.dumps({
            "subject": "Test Subject",
            "email_body": "Test Body",
            "received_at": "2026-06-19T10:00:00Z"
        })
    )

    # Verify it now appears in incoming
    response = client.get("/pipeline/incoming")
    assert response.status_code == 200
    incoming_list = response.json()
    assert any(run["id"] == run_id for run in incoming_list)

    # Verify it does NOT appear in processed
    response = client.get("/pipeline/processed")
    assert response.status_code == 200
    processed_list = response.json()
    assert not any(run["id"] == run_id for run in processed_list)

    # 3. Resolve the run using POST /pipeline/processed
    resolve_payload = {
        "run_id": run_id,
        "status": "approved",
        "edited_data": {
            "consignee_name": {"value": "Test Consignee Edited", "confidence": 1.0, "source_snippet": None}
        },
        "amendment_draft": "Draft email updated"
    }
    response = client.post("/pipeline/processed", json=resolve_payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"

    # Verify it now appears in processed and NOT in incoming
    response = client.get("/pipeline/incoming")
    assert response.status_code == 200
    incoming_list = response.json()
    assert not any(run["id"] == run_id for run in incoming_list)

    response = client.get("/pipeline/processed")
    assert response.status_code == 200
    processed_list = response.json()
    target_run = next((run for run in processed_list if run["id"] == run_id), None)
    assert target_run is not None
    assert target_run["status"] == "approved"
    assert target_run["edited_data"]["consignee_name"]["value"] == "Test Consignee Edited"
    assert target_run["amendment_draft"] == "Draft email updated"

    print("\nALL API ENDPOINT INTEGRATION TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == "__main__":
    test_incoming_processed_endpoints()
