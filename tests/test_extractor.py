import os
import sys

# Ensure backend folder is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import fitz # PyMuPDF
from agents.extractor import extract_agent

def ensure_sample_pdf(output_path: str):
    """Generates a mock invoice PDF if it doesn't exist."""
    if os.path.exists(output_path):
        return
        
    print(f"Generating mock clean PDF invoice at {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4
    
    # Title
    page.insert_text((50, 50), "COMMERCIAL INVOICE", fontsize=18, fontname="helvetica-bold")
    
    # Invoice details
    page.insert_text((50, 100), "Invoice Number: INV-2026-9901", fontsize=11, fontname="helvetica")
    page.insert_text((50, 120), "Date: June 18, 2026", fontsize=11, fontname="helvetica")
    
    # Consignee
    page.insert_text((50, 160), "Consignee Details:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 180), "Nova Logistics Ltd", fontsize=11, fontname="helvetica")
    page.insert_text((50, 200), "123 Port Road, Shipping Hub", fontsize=11, fontname="helvetica")
    page.insert_text((50, 220), "Singapore 098765", fontsize=11, fontname="helvetica")
    
    # Shipment Details
    page.insert_text((300, 160), "Shipment Route & Terms:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((300, 180), "Port of Loading: Port of Shanghai, China", fontsize=11, fontname="helvetica")
    page.insert_text((300, 200), "Port of Discharge: Port of Singapore, Singapore", fontsize=11, fontname="helvetica")
    page.insert_text((300, 220), "Incoterms: FOB (Free On Board)", fontsize=11, fontname="helvetica")
    
    # Cargo Table Header
    page.insert_text((50, 280), "Description of Goods", fontsize=11, fontname="helvetica-bold")
    page.insert_text((350, 280), "HS Code", fontsize=11, fontname="helvetica-bold")
    page.insert_text((450, 280), "Gross Weight", fontsize=11, fontname="helvetica-bold")
    
    # Draw horizontal line
    page.draw_line((50, 290), (550, 290), width=1)
    
    # Cargo Table Data
    page.insert_text((50, 315), "Automotive Parts (Brake Pads & Rotor Assemblies)", fontsize=10, fontname="helvetica")
    page.insert_text((350, 315), "8708.29.90", fontsize=10, fontname="helvetica")
    page.insert_text((450, 315), "1,250.50 kg", fontsize=10, fontname="helvetica")
    
    doc.save(output_path)
    print("Mock PDF generated successfully.")

def run_test():
    sample_file = "backend/sample_docs/clean_invoice.pdf"
    ensure_sample_pdf(sample_file)
    
    print(f"\nRunning Extractor Agent test on {sample_file}...")
    
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
    
    # Run the agent
    result = extract_agent(initial_state)
    
    print("\n--- EXTRACTED DATA RESULT ---")
    import json
    print(json.dumps(result["extracted_data"], indent=2))
    
    print("\n--- RUN LOGS ---")
    for log in result["logs"]:
        print(log)

if __name__ == "__main__":
    run_test()
