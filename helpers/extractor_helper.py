
import json
from config.settings import settings
from prompts.extractor_prompts import EXTRACTOR_SYSTEM_PROMPT




def extract_single_file(file_path: str, filename: str, model, config) -> tuple[str, dict, str]:
    """Helper function to run extraction on a single file (executed in thread pool)"""
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        mime_type = "application/pdf" if file_path.lower().endswith(".pdf") else "image/jpeg"
        if file_path.lower().endswith(".png"):
            mime_type = "image/png"
            
        response = model.generate_content(
            [
                {"mime_type": mime_type, "data": file_bytes},
                EXTRACTOR_SYSTEM_PROMPT
            ],
            generation_config=config
        )
        
        file_data = json.loads(response.text)
        return filename, file_data, f"Extractor Agent: Extraction completed for {filename}."
    except Exception as e:
        # Fallback values structure
        fields = [
            "consignee_name", "hs_code", "port_of_loading", "port_of_discharge",
            "incoterms", "description_of_goods", "gross_weight", "invoice_number"
        ]
        fallback = {
            f: {"value": None, "confidence": 0.0, "source_snippet": None}
            for f in fields
        }
        fallback["extraction_warnings"] = [f"Extraction failed: {str(e)}"]
        return filename, fallback, f"Extractor Agent: Extraction failed for {filename} ({str(e)})."
