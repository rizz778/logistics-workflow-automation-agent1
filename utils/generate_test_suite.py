import os
import sys

# Add backend folder to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.generate_samples import generate_clean_pdf, generate_messy_pdf
from tests.test_multidoc_pipeline_e2e import generate_clean_packing_list, generate_mismatched_packing_list

def main():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples_dir = os.path.join(backend_dir, "sample_docs")
    os.makedirs(samples_dir, exist_ok=True)
    
    clean_invoice_path = os.path.join(samples_dir, "clean_invoice.pdf")
    clean_packing_list_path = os.path.join(samples_dir, "clean_packing_list.pdf")
    mismatched_packing_list_path = os.path.join(samples_dir, "mismatched_packing_list.pdf")
    messy_invoice_path = os.path.join(samples_dir, "messy_invoice.pdf")
    
    print("Generating Commercial Invoice and Packing List test suite...")
    
    generate_clean_pdf(clean_invoice_path)
    generate_clean_packing_list(clean_packing_list_path)
    generate_mismatched_packing_list(mismatched_packing_list_path)
    generate_messy_pdf(messy_invoice_path)
    
    print("\nTest suite generation complete!")
    print(f"Generated files in: {samples_dir}")
    print("  1. clean_invoice.pdf")
    print("  2. clean_packing_list.pdf")
    print("  3. mismatched_packing_list.pdf (disagrees on Gross Weight)")
    print("  4. messy_invoice.pdf (violates consignee names/HS code/port rules)")

if __name__ == "__main__":
    main()
