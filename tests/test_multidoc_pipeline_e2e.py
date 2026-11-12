import os
import sys
import json
import fitz # PyMuPDF
from dotenv import load_dotenv

# Ensure we resolve imports relative to the backend directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.graph import pipeline_graph
from services.storage import init_db

def generate_clean_packing_list(output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Title
    page.insert_text((50, 50), "PACKING LIST", fontsize=18, fontname="helvetica-bold")
    
    # Details
    page.insert_text((50, 100), "Associated Invoice: INV-2026-9901", fontsize=11, fontname="helvetica")
    
    # Consignee
    page.insert_text((50, 160), "Consignee:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 180), "Nova Logistics Ltd", fontsize=11, fontname="helvetica")
    
    # Shipment
    page.insert_text((300, 160), "Shipment Details:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((300, 180), "Port of Loading: Port of Shanghai, China", fontsize=11, fontname="helvetica")
    page.insert_text((300, 200), "Port of Discharge: Port of Singapore, Singapore", fontsize=11, fontname="helvetica")
    
    # Weight
    page.insert_text((50, 280), "Item Description", fontsize=11, fontname="helvetica-bold")
    page.insert_text((350, 280), "HS Code", fontsize=11, fontname="helvetica-bold")
    page.insert_text((450, 280), "Weight", fontsize=11, fontname="helvetica-bold")
    page.draw_line((50, 290), (550, 290), width=1)
    
    page.insert_text((50, 315), "Automotive Parts (Brake Pads & Rotors)", fontsize=10, fontname="helvetica")
    page.insert_text((350, 315), "8708.29.90", fontsize=10, fontname="helvetica")
    page.insert_text((450, 315), "1,250.50 kg", fontsize=10, fontname="helvetica")
    
    doc.save(output_path)
    print(f"Generated clean packing list PDF: {output_path}")

def generate_mismatched_packing_list(output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Title
    page.insert_text((50, 50), "PACKING LIST", fontsize=18, fontname="helvetica-bold")
    
    # Details
    page.insert_text((50, 100), "Associated Invoice: INV-2026-9901", fontsize=11, fontname="helvetica")
    
    # Consignee
    page.insert_text((50, 160), "Consignee:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 180), "Nova Logistics Ltd", fontsize=11, fontname="helvetica")
    
    # Shipment
    page.insert_text((300, 160), "Shipment Details:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((300, 180), "Port of Loading: Port of Shanghai, China", fontsize=11, fontname="helvetica")
    page.insert_text((300, 200), "Port of Discharge: Port of Singapore, Singapore", fontsize=11, fontname="helvetica")
    
    # Weight
    page.insert_text((50, 280), "Item Description", fontsize=11, fontname="helvetica-bold")
    page.insert_text((350, 280), "HS Code", fontsize=11, fontname="helvetica-bold")
    page.insert_text((450, 280), "Weight", fontsize=11, fontname="helvetica-bold")
    page.draw_line((50, 290), (550, 290), width=1)
    
    page.insert_text((50, 315), "Automotive Parts (Brake Pads & Rotors)", fontsize=10, fontname="helvetica")
    page.insert_text((350, 315), "8708.29.90", fontsize=10, fontname="helvetica")
    page.insert_text((450, 315), "1,800.00 kg", fontsize=10, fontname="helvetica") # Mismatch weight!
    
    doc.save(output_path)
    print(f"Generated mismatched packing list PDF: {output_path}")

def run_e2e_tests():
    load_dotenv()
    init_db()
    
    from utils.generate_samples import generate_clean_pdf
    
    clean_invoice = "sample_docs/clean_invoice.pdf"
    clean_packing_list = "sample_docs/clean_packing_list.pdf"
    mismatched_packing_list = "sample_docs/mismatched_packing_list.pdf"
    
    generate_clean_pdf(clean_invoice)
    generate_clean_packing_list(clean_packing_list)
    generate_mismatched_packing_list(mismatched_packing_list)
    
    # Run 1: Clean multi-doc shipment (Invoice + Packing List matching)
    clean_state = {
        "filenames": ["invoice.pdf", "packing_list.pdf"],
        "file_paths": [clean_invoice, clean_packing_list],
        "raw_text": "",
        "extracted_data": {},
        "validation_results": {},
        "cross_doc_results": {},
        "decision": "",
        "decision_reason": "",
        "amendment_draft": None,
        "logs": []
    }
    
    print("\n==========================================")
    print("      RUN 1: CLEAN MULTI-DOC PIPELINE     ")
    print("==========================================")
    
    final_clean = pipeline_graph.invoke(clean_state)
    print(f"Decision Outcome: {final_clean['decision']}")
    print(f"Reasoning:\n{final_clean['decision_reason']}\n")
    print("Cross-Document Consistency:")
    print(json.dumps(final_clean.get("cross_doc_results"), indent=2))
    
    # Run 2: Messy/Mismatched weight shipment
    messy_state = {
        "filenames": ["invoice.pdf", "mismatched_packing_list.pdf"],
        "file_paths": [clean_invoice, mismatched_packing_list],
        "raw_text": "",
        "extracted_data": {},
        "validation_results": {},
        "decision": "",
        "decision_reason": "",
        "amendment_draft": None,
        "logs": []
    }
    
    print("\n==========================================")
    print("     RUN 2: MISMATCHED MULTI-DOC PIPELINE ")
    print("==========================================")
    
    final_messy = pipeline_graph.invoke(messy_state)
    print(f"Decision Outcome: {final_messy['decision']}")
    print(f"Reasoning:\n{final_messy['decision_reason']}\n")
    if final_messy['amendment_draft']:
        print(f"Draft Message:\n{final_messy['amendment_draft']}\n")
    print("Cross-Document Consistency:")
    print(json.dumps(final_messy.get("cross_doc_results"), indent=2))

if __name__ == "__main__":
    run_e2e_tests()
