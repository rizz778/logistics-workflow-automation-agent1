import asyncio
import os
from typing import Dict, Any, List
from google.generativeai.types import GenerationConfig
from graph.state import PipelineState
from config.settings import settings
from schemas.extractor_schemas import TradeDocumentExtraction
from helpers.extractor_helper import extract_single_file, compute_confidence_scores
from helpers.common_helpers import get_gemini_client
from services.llm_limiter import llm_limiter, LlmSlotContext

async def extract_agent(state: PipelineState) -> PipelineState:
    """Multi-document extraction agent powered by Gemini Vision.
    - Bound by Tier 2 distributed concurrency limiter to prevent 429 quota exhaustion.
    - Tracks field-level confidence scores and triggers targeted retries up to 3 times.
    """
    logs = list(state.get("logs", []))
    filenames = state.get("filenames", [])
    file_bytes_map = state.get("file_bytes_map", {})
    file_paths = state.get("file_paths", [])
    retry_count = state.get("extraction_retry_count", 0)
    max_retries = state.get("max_extraction_retries", getattr(settings, "max_extraction_retries", 3))
    prev_low_fields = state.get("low_confidence_fields", [])

    logs.append(
        f"Extractor Agent: Starting extraction (Attempt {retry_count + 1}/{max_retries + 1}) "
        f"for {len(filenames)} documents..."
    )

    resolved_bytes: Dict[str, bytes] = {}
    for name in filenames:
        if name in file_bytes_map:
            resolved_bytes[name] = file_bytes_map[name]
        else:
            matched_path = next((p for p in file_paths if os.path.basename(p) == name or p.endswith(name)), None)
            if matched_path and os.path.exists(matched_path):
                with open(matched_path, "rb") as f:
                    resolved_bytes[name] = f.read()

    extracted_data = dict(state.get("extracted_data", {}))

    try:
        ai = get_gemini_client()
        model = ai.GenerativeModel(settings.gemini_model)
        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=TradeDocumentExtraction,
            temperature=0.1 if retry_count == 0 else 0.2
        )

        async def _extract_file_task(name: str, b_data: bytes):
            async with LlmSlotContext(llm_limiter):
                return await asyncio.to_thread(
                    extract_single_file,
                    b_data,
                    name,
                    model,
                    config,
                    retry_count,
                    prev_low_fields
                )

        tasks = [
            _extract_file_task(name, resolved_bytes[name])
            for name in filenames
            if name in resolved_bytes
        ]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logs.append(f"Extractor Agent: Task error ({res})")
                else:
                    doc_name, doc_data, log_msg = res
                    extracted_data[doc_name] = doc_data
                    logs.append(log_msg)

    except Exception as e:
        logs.append(f"Extractor Agent: Client initialization error ({str(e)})")

    avg_conf, low_fields = compute_confidence_scores(extracted_data)
    threshold = getattr(settings, "extraction_confidence_threshold", 0.70)

    is_low_confidence = (avg_conf < threshold) or (len(low_fields) > 0 and avg_conf < 0.80)
    can_retry = is_low_confidence and (retry_count < max_retries)
    needs_human = is_low_confidence and (retry_count >= max_retries)

    if can_retry:
        logs.append(
            f"Extractor Agent: Low confidence detected (avg: {avg_conf:.2f} < {threshold}). "
            f"Low fields: {low_fields}. Scheduling retry {retry_count + 1} of {max_retries}."
        )
        return {
            **state,
            "extracted_data": extracted_data,
            "avg_confidence": avg_conf,
            "low_confidence_fields": low_fields,
            "extraction_retry_count": retry_count + 1,
            "human_correction_required": False,
            "status": "extracting",
            "logs": logs
        }
    elif needs_human:
        logs.append(
            f"Extractor Agent: Maximum retries ({max_retries}) exhausted. "
            f"Average confidence is {avg_conf:.2f}. Triggering Human Correction node."
        )
        return {
            **state,
            "extracted_data": extracted_data,
            "avg_confidence": avg_conf,
            "low_confidence_fields": low_fields,
            "extraction_retry_count": retry_count,
            "human_correction_required": True,
            "status": "pending_correction",
            "logs": logs
        }
    else:
        logs.append(
            f"Extractor Agent: Extraction successful with high confidence ({avg_conf:.2f} >= {threshold}). "
            "Proceeding to validation."
        )
        return {
            **state,
            "extracted_data": extracted_data,
            "avg_confidence": avg_conf,
            "low_confidence_fields": low_fields,
            "extraction_retry_count": retry_count,
            "human_correction_required": False,
            "status": "validating",
            "logs": logs
        }

