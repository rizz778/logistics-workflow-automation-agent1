import os
import fitz # PyMuPDF

def generate_invoice(path: str, invoice_number: str, consignee_name: str, incoterms: str, weight: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Title
    page.insert_text((50, 50), "COMMERCIAL INVOICE", fontsize=18, fontname="helvetica-bold")
    
    # Details
    page.insert_text((50, 100), f"Invoice Number: {invoice_number}", fontsize=11, fontname="helvetica")
    page.insert_text((50, 120), "Date: June 20, 2026", fontsize=11, fontname="helvetica")
    
    # Consignee
    page.insert_text((50, 160), "Consignee Details:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 180), consignee_name, fontsize=11, fontname="helvetica")
    
    # Incoterms & weight
    page.insert_text((300, 160), "Shipment details:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((300, 180), f"Incoterms: {incoterms}", fontsize=11, fontname="helvetica")
    page.insert_text((300, 200), f"Gross Weight: {weight}", fontsize=11, fontname="helvetica")
    
    page.insert_text((50, 280), "Description of Goods", fontsize=11, fontname="helvetica-bold")
    page.draw_line((50, 290), (550, 290), width=1)
    page.insert_text((50, 315), "Automotive Parts (Brake Pads & Rotors)", fontsize=10, fontname="helvetica")
    
    doc.save(path)
    print(f"Generated invoice PDF: {path}")

def generate_bill_of_lading(path: str, consignee_name: str, port_loading: str, port_discharge: str, weight: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Title
    page.insert_text((50, 50), "BILL OF LADING", fontsize=18, fontname="helvetica-bold")
    
    # Consignee
    page.insert_text((50, 120), "Consignee:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 140), consignee_name, fontsize=11, fontname="helvetica")
    
    # Shipment Ports
    page.insert_text((50, 200), "Port of Loading:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 220), port_loading, fontsize=11, fontname="helvetica")
    page.insert_text((50, 250), "Port of Discharge:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 270), port_discharge, fontsize=11, fontname="helvetica")
    
    # Weight
    page.insert_text((300, 200), "Total Gross Weight:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((300, 220), weight, fontsize=11, fontname="helvetica")
    
    doc.save(path)
    print(f"Generated Bill of Lading PDF: {path}")

def generate_co(path: str, consignee_name: str, hs_code: str, weight: str, is_blurry: bool = False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Title
    page.insert_text((50, 50), "CERTIFICATE OF ORIGIN", fontsize=18, fontname="helvetica-bold")
    
    # Consignee
    page.insert_text((50, 120), "Consignee / Consigned To:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 140), consignee_name, fontsize=11, fontname="helvetica")
    
    # HS Code & Weight
    if is_blurry:
        page.insert_text((50, 200), "[SIMULATED BLURRY/ILLEGIBLE PRINT - CONFIDENCE WILL BE LOW]", fontsize=12, fontname="helvetica-bold")
        page.insert_text((50, 220), "HS Code: 8708.29.90 (highly faint, smudged print)", fontsize=11, fontname="helvetica")
    else:
        page.insert_text((50, 200), "HS Code:", fontsize=12, fontname="helvetica-bold")
        page.insert_text((50, 220), hs_code, fontsize=11, fontname="helvetica")
        
    page.insert_text((300, 200), "Gross Weight:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((300, 220), weight, fontsize=11, fontname="helvetica")
    
    doc.save(path)
    print(f"Generated Certificate of Origin PDF: {path}")

def generate_all_sets():
    base_dir = "sample_docs"
    
    # Set 1: Auto Approve
    print("\nGenerating Set 1: Auto Approve...")
    generate_invoice(
        path=os.path.join(base_dir, "auto_approve", "invoice.pdf"),
        invoice_number="INV-2026-1001",
        consignee_name="Nova Logistics Ltd",
        incoterms="FOB",
        weight="1,200.00 kg"
    )
    generate_bill_of_lading(
        path=os.path.join(base_dir, "auto_approve", "bill_of_lading.pdf"),
        consignee_name="Nova Logistics Ltd",
        port_loading="Port of Shanghai, China",
        port_discharge="Port of Singapore, Singapore",
        weight="1,200.00 kg"
    )
    generate_co(
        path=os.path.join(base_dir, "auto_approve", "co.pdf"),
        consignee_name="Nova Logistics Ltd",
        hs_code="8708.29.90",
        weight="1,200.00 kg"
    )
    
    # Set 2: Flag Review
    print("\nGenerating Set 2: Flag Review...")
    generate_invoice(
        path=os.path.join(base_dir, "flag_review", "invoice.pdf"),
        invoice_number="INV-2026-1002",
        consignee_name="Nova Logistics Ltd",
        incoterms="FOB",
        weight="1,200.00 kg"
    )
    generate_bill_of_lading(
        path=os.path.join(base_dir, "flag_review", "bill_of_lading.pdf"),
        consignee_name="Nova Logistics Ltd",
        port_loading="Port of Shanghai, China",
        port_discharge="Port of Singapore, Singapore",
        weight="1,200.00 kg"
    )
    generate_co(
        path=os.path.join(base_dir, "flag_review", "co_blurry.pdf"),
        consignee_name="Nova Logistics Ltd",
        hs_code="8708.29.90",
        weight="1,200.00 kg",
        is_blurry=True
    )
    
    # Set 3: Amendment Required
    print("\nGenerating Set 3: Amendment Required...")
    generate_invoice(
        path=os.path.join(base_dir, "amendment_required", "invoice.pdf"),
        invoice_number="INV-2026-1003",
        consignee_name="Nova Logistics Ltd",
        incoterms="FOB",
        weight="1,200.00 kg"
    )
    generate_bill_of_lading(
        path=os.path.join(base_dir, "amendment_required", "bill_of_lading.pdf"),
        consignee_name="Nova Logistics Ltd",
        port_loading="Port of Shanghai, China",
        port_discharge="Port of Singapore, Singapore",
        weight="1,850.00 kg" # Mismatched weight!
    )
    generate_co(
        path=os.path.join(base_dir, "amendment_required", "co.pdf"),
        consignee_name="Mismatched Consignee Ltd", # Mismatched consignee!
        hs_code="8708.29.90",
        weight="1,200.00 kg"
    )
    
    print("\nAll test sets generated successfully.")

if __name__ == "__main__":
    generate_all_sets()
