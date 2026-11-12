import os
import sys
import json
import shutil
import time
from dotenv import load_dotenv

# Ensure we resolve imports relative to the backend directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage import init_db, get_all_runs

def test_watcher_trigger():
    load_dotenv()
    init_db()
    
    # Paths
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inbox_dir = os.path.join(backend_dir, "inbox")
    processed_dir = os.path.join(backend_dir, "processed")
    shipment_folder = os.path.join(inbox_dir, "shipment_test_inbox")
    
    # Ensure cleanup first
    if os.path.exists(shipment_folder):
        shutil.rmtree(shipment_folder)
    processed_folder = os.path.join(processed_dir, "shipment_test_inbox")
    if os.path.exists(processed_folder):
        shutil.rmtree(processed_folder)
        
    os.makedirs(shipment_folder, exist_ok=True)
    
    # Copy documents
    src_invoice = os.path.join(backend_dir, "sample_docs", "clean_invoice.pdf")
    src_packing = os.path.join(backend_dir, "sample_docs", "clean_packing_list.pdf")
    
    if not os.path.exists(src_invoice) or not os.path.exists(src_packing):
        print("Error: clean_invoice.pdf or clean_packing_list.pdf missing in sample_docs/. Run test_multidoc_pipeline_e2e.py first.")
        return
        
    shutil.copy(src_invoice, os.path.join(shipment_folder, "invoice.pdf"))
    shutil.copy(src_packing, os.path.join(shipment_folder, "packing_list.pdf"))
    
    # Write manifest.json last to trigger watcher
    manifest = {
        "sender": "su@northwindshipping.com",
        "customer_name": "Northwind Apparel Imports",
        "subject": "Shipment docs - PO#4521",
        "email_body": "Hi, attaching the BOL, invoice, and packing list for the latest shipment. Let us know if anything's missing.",
        "received_at": "2026-06-19T14:30:00Z"
    }
    
    print("\n[Simulator] Writing manifest.json to trigger watcher...")
    with open(os.path.join(shipment_folder, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    # Wait for watcher to pick up and process
    print("[Simulator] Waiting 15 seconds for watcher background task to complete...")
    time.sleep(15)
    
    # Assert folder has been moved
    if not os.path.exists(processed_folder):
        print("FAIL: Shipment folder was not processed and moved to /processed/")
        return
    print("SUCCESS: Folder moved to /processed/.")
    
    # Verify in DB
    runs = get_all_runs()
    target_run = None
    for run in runs:
        if "invoice.pdf" in run["filename"] and "packing_list.pdf" in run["filename"]:
            target_run = run
            break
            
    if not target_run:
        print("FAIL: Run not found in database registry.")
        return
        
    print("\nSUCCESS: Run found in database.")
    print(f"  Run ID: {target_run['id']}")
    print(f"  Source: {target_run['source']}")
    print(f"  Email Sender: {target_run['email_sender']}")
    print(f"  Email Subject: {target_run['email_subject']}")
    print(f"  Email Body: {target_run['email_body']}")
    print(f"  Received At: {target_run['received_at']}")
    print(f"  Decision: {target_run['decision']}")
    
    assert target_run["source"] == "inbox"
    assert target_run["email_sender"] == "su@northwindshipping.com"
    assert target_run["email_subject"] == "Shipment docs - PO#4521"
    assert "attaching the BOL" in target_run["email_body"]
    
    print("\nALL INBOX TRIGGER WATCHER TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == "__main__":
    test_watcher_trigger()
