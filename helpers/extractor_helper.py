import json
import logging
from typing import Tuple, Dict, Any, List, Optional

from google import genai
from google.genai import types
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)

from prompts.extractor_prompts import EXTRACTOR_SYSTEM_PROMPT
from schemas.extractor_schemas import TradeDocumentExtraction

logger = logging.getLogger("agent_worker.extractor_helper")

FIELDS_TO_EXTRACT = [
    "consignee_name", "hs_code", "port_of_loading", "port_of_discharge",
    "incoterms", "description_of_goods", "gross_weight", "invoice_number"
]


def _is_retryable(exc: BaseException) -> bool:
    """Retry on 503 (overloaded) and 429 (rate limit) from Gemini."""
    msg = str(exc).lower()
    return any(code in msg for code in ("503", "429", "unavailable", "resource_exhausted", "rate"))


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(4),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_gemini(
    client: genai.Client,
    model_name: str,
    file_bytes: bytes,
    mime_type: str,
    prompt_text: str,
    temperature: float,
) -> str:
    """Makes the Gemini API call with automatic retry on transient errors."""
    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            prompt_text,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TradeDocumentExtraction,
            temperature=temperature,
        ),
    )
    return response.text.strip()


def extract_single_file(
    file_bytes: bytes,
    filename: str,
    client: genai.Client,
    model_name: str,
    retry_count: int = 0,
    focus_fields: Optional[List[str]] = None,
) -> Tuple[str, Dict[str, Any], str]:
    """Gemini Vision extraction with tenacity retry on 503/429 errors."""
    try:
        mime_type = "application/pdf"
        lower = filename.lower()
        if lower.endswith(".png"):
            mime_type = "image/png"
        elif lower.endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"

        prompt_text = EXTRACTOR_SYSTEM_PROMPT
        if retry_count > 0 and focus_fields:
            prompt_text += (
                f"\n\n[RETRY ATTEMPT {retry_count}] "
                f"Previous extraction scored low confidence on: {', '.join(focus_fields)}. "
                "Examine headers, footers, stamps, and tabular sections carefully for these fields."
            )

        temperature = 0.1 if retry_count == 0 else 0.2
        logger.info("Extractor: Sending '%s' to Gemini (attempt %d)...", filename, retry_count + 1)

        content = _call_gemini(client, model_name, file_bytes, mime_type, prompt_text, temperature)

        if content.startswith("```"):
            content = content.replace("```json", "", 1).replace("```", "").strip()

        file_data = json.loads(content)
        return (
            filename,
            file_data,
            f"Extractor Agent: Extraction succeeded for {filename} (Attempt {retry_count + 1}).",
        )

    except Exception as e:
        logger.error(
            "Extraction failed for '%s' (attempt %d): %s",
            filename, retry_count + 1, e, exc_info=True,
        )
        fallback = {
            f: {"value": None, "confidence": 0.0, "source_snippet": None}
            for f in FIELDS_TO_EXTRACT
        }
        fallback["extraction_warnings"] = [f"Extraction failed: {str(e)}"]
        return (
            filename,
            fallback,
            f"Extractor Agent: Extraction FAILED for {filename} — {type(e).__name__}: {str(e)}",
        )


def compute_confidence_scores(
    extracted_data: Dict[str, Any],
) -> Tuple[float, List[str]]:
    """Calculates average confidence and identifies low-confidence fields across all documents."""
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
