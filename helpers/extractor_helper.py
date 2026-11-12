import json
from typing import Tuple, Dict, Any, List, Optional
from prompts.extractor_prompts import EXTRACTOR_SYSTEM_PROMPT

FIELDS_TO_EXTRACT = [
    "consignee_name", "hs_code", "port_of_loading", "port_of_discharge",
    "incoterms", "description_of_goods", "gross_weight", "invoice_number"
]

def extract_single_file(
    file_bytes: bytes,
    filename: str,
    model,
    config,
    retry_count: int = 0,
    focus_fields: Optional[List[str]] = None
) -> Tuple[str, Dict[str, Any], str]:
    """Helper function to run Gemini Vision extraction on document bytes."""
    try:
        mime_type = "application/pdf"
        lower_name = filename.lower()
        if lower_name.endswith(".png"):
            mime_type = "image/png"
        elif lower_name.endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"

        prompt_text = EXTRACTOR_SYSTEM_PROMPT
        if retry_count > 0 and focus_fields:
            prompt_text += (
                f"\n\n[RETRY ATTEMPT {retry_count}] "
                f"Previous extraction scored low confidence on: {', '.join(focus_fields)}. "
                "Examine document headers, footers, stamps, and tabular sections carefully "
                "to find reliable values with higher confidence."
            )

        response = model.generate_content(
            [
                {"mime_type": mime_type, "data": file_bytes},
                prompt_text
            ],
            generation_config=config
        )

        content = response.text.strip()
        if content.startswith("```"):
            content = content.replace("```json", "", 1).replace("```", "").strip()

        file_data = json.loads(content)
        return filename, file_data, f"Extractor Agent: Extraction succeeded for {filename} (Attempt {retry_count + 1})."
    except Exception as e:
        fallback = {
            f: {"value": None, "confidence": 0.0, "source_snippet": None}
            for f in FIELDS_TO_EXTRACT
        }
        fallback["extraction_warnings"] = [f"Extraction failed: {str(e)}"]
        return filename, fallback, f"Extractor Agent: Extraction failed for {filename} ({str(e)})."

def compute_confidence_scores(
    extracted_data: Dict[str, Any]
) -> Tuple[float, List[str]]:
    """Calculates average confidence score and identifies low-confidence fields across all documents."""
    total_score = 0.0
    field_count = 0
    low_confidence_fields = set()

    for doc_name, doc_fields in extracted_data.items():
        for field in FIELDS_TO_EXTRACT:
            f_data = doc_fields.get(field) or {}
            conf = float(f_data.get("confidence", 0.0))
            val = f_data.get("value")

            total_score += conf
            field_count += 1

            if conf < 0.70 or val is None:
                low_confidence_fields.add(field)

    avg_conf = (total_score / field_count) if field_count > 0 else 0.0
    return round(avg_conf, 3), sorted(list(low_confidence_fields))
