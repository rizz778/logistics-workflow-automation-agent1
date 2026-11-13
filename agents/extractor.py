import asyncio
import logging
import os
from typing import Dict, Any, List
from graph.state import PipelineState
from config.settings import settings
from helpers.extractor_helper import extract_single_file, compute_confidence_scores
from helpers.common_helpers import get_gemini_client
from services.llm_limiter import llm_limiter, LlmSlotContext
from services.event_publisher import event_publisher

logger = logging.getLogger("agent_worker.extractor")

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
    max_retries = state.get("max_extraction_retries", settings.max_extraction_retries)
    prev_low_fields = state.get("low_confidence_fields", [])

    logs.append(
        f"Extractor Agent: Starting extraction (Attempt {retry_count + 1}/{max_retries + 1}) "
        f"for {len(filenames)} documents..."
    )

    # 1. Resolve file bytes (from in-memory bytes map or local paths)
    resolved_bytes: Dict[str, bytes] = {}
    for name in filenames:
        if name in file_bytes_map:
            resolved_bytes[name] = file_bytes_map[name]
        else:
            # Check local file paths
            matched_path = next((p for p in file_paths if os.path.basename(p) == name or p.endswith(name)), None)
            if matched_path and os.path.exists(matched_path):
                with open(matched_path, "rb") as f:
                    resolved_bytes[name] = f.read()

    extracted_data = dict(state.get("extracted_data", {}))

    try:
        client = get_gemini_client()

        # 2. Extract each document under the Tier 2 distributed LLM concurrency limiter
        async def _extract_file_task(name: str, b_data: bytes):
            async with LlmSlotContext(llm_limiter):
                return await asyncio.to_thread(
                    extract_single_file,
                    b_data,
                    name,
                    client,
                    settings.gemini_model,
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
                    logger.error("Extractor task raised an unhandled exception: %s", res, exc_info=res)
                    logs.append(f"Extractor Agent: Task error ({res})")
                else:
                    doc_name, doc_data, log_msg = res
                    extracted_data[doc_name] = doc_data
                    if "FAILED" in log_msg:
                        logger.warning("Extractor Agent: %s", log_msg)
                    logs.append(log_msg)

    except Exception as e:
        logger.error("Extractor Agent: Gemini client initialization error: %s", e, exc_info=True)
        logs.append(f"Extractor Agent: Client initialization error ({str(e)})")

    # 3. Compute extraction confidence metrics
    avg_conf, low_fields = compute_confidence_scores(extracted_data)
    threshold = settings.extraction_confidence_threshold

    is_low_confidence = (avg_conf < threshold) or (len(low_fields) > 0 and avg_conf < 0.80)
    can_retry = is_low_confidence and (retry_count < max_retries)
    needs_human = is_low_confidence and (retry_count >= max_retries)

    shipment_id = state.get("shipment_id", "unknown")
    run_id = state.get("run_id")

    if can_retry:
        logs.append(
            f"Extractor Agent: Low confidence detected (avg: {avg_conf:.2f} < {threshold}). "
            f"Low fields: {low_fields}. Scheduling retry {retry_count + 1} of {max_retries}."
        )
        await event_publisher.publish(
            shipment_id=shipment_id,
            step="extract_retry",
            status="extracting",
            message=f"Low extraction confidence ({avg_conf:.2f} < {threshold}) on {low_fields}. Scheduling OCR retry {retry_count + 1}/{max_retries}...",
            run_id=run_id,
            data={"avg_confidence": avg_conf, "low_confidence_fields": low_fields, "retry_count": retry_count + 1}
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
        await event_publisher.publish(
            shipment_id=shipment_id,
            step="extract_exhausted",
            status="pending_correction",
            message=f"OCR retries ({max_retries}) exhausted with confidence {avg_conf:.2f}. Routing to Human Correction node.",
            run_id=run_id,
            data={"avg_confidence": avg_conf, "low_confidence_fields": low_fields}
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
        await event_publisher.publish(
            shipment_id=shipment_id,
            step="extract_complete",
            status="validating",
            message=f"Document extraction completed with high confidence ({avg_conf:.2f}). Proceeding to validation.",
            run_id=run_id,
            data={"avg_confidence": avg_conf}
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
