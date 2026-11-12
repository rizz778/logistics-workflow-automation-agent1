import os
import fitz  # PyMuPDF

def generate_clean_pdf(output_path: str):
    """Generates a clean commercial invoice PDF that fully conforms to customer rules."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Title
    page.insert_text((50, 50), "COMMERCIAL INVOICE", fontsize=18, fontname="helvetica-bold")
    
    # Details
    page.insert_text((50, 100), "Invoice Number: INV-2026-9901", fontsize=11, fontname="helvetica")
    page.insert_text((50, 120), "Date: June 18, 2026", fontsize=11, fontname="helvetica")
    
    # Consignee
    page.insert_text((50, 160), "Consignee Details:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 180), "Nova Logistics Ltd", fontsize=11, fontname="helvetica")
    page.insert_text((50, 200), "123 Port Road, Shipping Hub", fontsize=11, fontname="helvetica")
    page.insert_text((50, 220), "Singapore 098765", fontsize=11, fontname="helvetica")
    
    # Shipment
    page.insert_text((300, 160), "Shipment Route & Terms:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((300, 180), "Port of Loading: Port of Shanghai, China", fontsize=11, fontname="helvetica")
    page.insert_text((300, 200), "Port of Discharge: Port of Singapore, Singapore", fontsize=11, fontname="helvetica")
    page.insert_text((300, 220), "Incoterms: FOB (Free On Board)", fontsize=11, fontname="helvetica")
    
    # Items
    page.insert_text((50, 280), "Description of Goods", fontsize=11, fontname="helvetica-bold")
    page.insert_text((350, 280), "HS Code", fontsize=11, fontname="helvetica-bold")
    page.insert_text((450, 280), "Gross Weight", fontsize=11, fontname="helvetica-bold")
    page.draw_line((50, 290), (550, 290), width=1)
    
    page.insert_text((50, 315), "Automotive Parts (Brake Pads & Rotor Assemblies)", fontsize=10, fontname="helvetica")
    page.insert_text((350, 315), "8708.29.90", fontsize=10, fontname="helvetica")
    page.insert_text((450, 315), "1,250.50 kg", fontsize=10, fontname="helvetica")
    
    doc.save(output_path)
    print(f"Generated clean invoice PDF: {output_path}")

def generate_messy_pdf(output_path: str):
    """Generates a messy/invalid commercial invoice PDF violating customer rules."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Title
    page.insert_text((50, 50), "COMMERCL INVOIC (COPY)", fontsize=18, fontname="helvetica-bold")
    
    # Details (violates pattern)
    page.insert_text((50, 100), "Inv. No: I-2026-UNKNOWN", fontsize=11, fontname="helvetica")
    page.insert_text((50, 120), "Date: 18-06-2026", fontsize=11, fontname="helvetica")
    
    # Consignee (violates exact match: spelling typo)
    page.insert_text((50, 160), "Consignee Details:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((50, 180), "N0va Logistx Ltd (Subsidiary)", fontsize=11, fontname="helvetica")
    
    # Shipment (violates discharge port rule: Rotterdam instead of Singapore)
    page.insert_text((300, 160), "Shipment Route & Terms:", fontsize=12, fontname="helvetica-bold")
    page.insert_text((300, 180), "Port of Loading: Port of Shanghai, China", fontsize=11, fontname="helvetica")
    page.insert_text((300, 200), "Port of Discharge: Port of Rotterdam, Netherlands", fontsize=11, fontname="helvetica")
    page.insert_text((300, 220), "Incoterms: FOB (Free On Board)", fontsize=11, fontname="helvetica")
    
    # Cargo Table (violates HS Code: Toys '9503' instead of Automotive '8708')
    page.insert_text((50, 315), "Plastic Toy Figures", fontsize=10, fontname="helvetica")
    page.insert_text((350, 315), "9503.00.00", fontsize=10, fontname="helvetica")
    page.insert_text((450, 315), "450 kg", fontsize=10, fontname="helvetica")
    
    doc.save(output_path)
    print(f"Generated messy invoice PDF: {output_path}")
