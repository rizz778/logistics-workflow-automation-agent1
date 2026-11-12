from graph.state import PipelineState
from helpers.common_helpers import load_rules
from helpers.validator_agent import validate_field, validate_cross_document_consistency
from services.event_publisher import event_publisher

async def validator_agent(state: PipelineState) -> PipelineState:
    """Deterministic, rule-based validator agent.
    - Evaluates fields against business compliance rules.
    - Checks cross-document consistency across files.
    - Ingests human-corrected fields with 100% confidence.
    """
    logs = list(state.get("logs", []))
    logs.append("Validator Agent: Starting deterministic validation...")

    extracted_data = dict(state.get("extracted_data", {}))
    rules = load_rules()
    validation_results = {}

    # 1. Merge human overrides if operator corrected any fields
    human_edits = state.get("human_correction_data") or {}
    if human_edits:
        logs.append(f"Validator Agent: Merging human-corrected fields: {list(human_edits.keys())}.")
        for doc_name, doc_dict in extracted_data.items():
            for field, override_val in human_edits.items():
                if field in doc_dict:
                    doc_dict[field] = {
                        "value": override_val,
                        "confidence": 1.0,
                        "source_snippet": "Human Auditor Override"
                    }

    filenames = state.get("filenames", [])
    if not filenames:
        filenames = ["document.pdf"]

    is_multidoc = False
    if extracted_data:
        first_key = list(extracted_data.keys())[0]
        if first_key in filenames or first_key.endswith((".pdf", ".png", ".jpg", ".jpeg")):
            is_multidoc = True

    fields = [
        "consignee_name", "hs_code", "port_of_loading", "port_of_discharge",
        "incoterms", "description_of_goods", "gross_weight", "invoice_number"
    ]

    # 2. Individual document field validation
    if is_multidoc:
        for doc_name, doc_data in extracted_data.items():
            doc_results = {}
            for field in fields:
                field_data = doc_data.get(field) or {"value": None, "confidence": 0.0}
                value = field_data.get("value")
                confidence = field_data.get("confidence", 1.0)
                rule = rules.get(field)

                result, expected, found, reason = validate_field(field, rule, value)

                if confidence < 0.70 and result != "skipped":
                    result = "uncertain"
                    reason = f"Extraction confidence too low to trust ({confidence:.2f}). " + (reason or "")

                doc_results[field] = {
                    "result": result,
                    "expected_value": expected,
                    "found_value": found,
                    "reason": reason
                }
            validation_results[doc_name] = doc_results
            logs.append(f"Validator Agent: Completed individual validation for {doc_name}.")

        # 3. Cross-document consistency verification
        cross_doc_results = validate_cross_document_consistency(extracted_data, logs)
    else:
        for field in fields:
            field_data = extracted_data.get(field) or {"value": None, "confidence": 0.0}
            value = field_data.get("value")
            confidence = field_data.get("confidence", 1.0)
            rule = rules.get(field)

            result, expected, found, reason = validate_field(field, rule, value)

            if confidence < 0.70 and result != "skipped":
                result = "uncertain"
                reason = f"Extraction confidence too low to trust ({confidence:.2f}). " + (reason or "")

            validation_results[field] = {
                "result": result,
                "expected_value": expected,
                "found_value": found,
                "reason": reason
            }
        logs.append("Validator Agent: Completed validation for single document.")
        cross_doc_results = {
            "is_consistent": True,
            "discrepancies": []
        }

    # 4. Shipment-level check for required missing fields
    for field in fields:
        rule = rules.get(field)
        if not rule:
            continue

        if is_multidoc:
            all_skipped = True
            for doc_name, doc_results in validation_results.items():
                if doc_results[field]["result"] != "skipped":
                    all_skipped = False
                    break

            if all_skipped:
                for doc_name in validation_results.keys():
                    validation_results[doc_name][field]["result"] = "mismatch"
                    validation_results[doc_name][field]["reason"] = f"Required field '{field}' was not found in any document in the shipment."
        else:
            if validation_results[field]["result"] == "skipped":
                validation_results[field]["result"] = "mismatch"
                validation_results[field]["reason"] = f"Required field '{field}' was not found in the document."

    shipment_id = state.get("shipment_id", "unknown")
    run_id = state.get("run_id")

    await event_publisher.publish(
        shipment_id=shipment_id,
        step="validate_complete",
        status="routing",
        message="Deterministic validation completed. Proceeding to router agent...",
        run_id=run_id,
        data={
            "is_consistent": cross_doc_results.get("is_consistent", True),
            "discrepancies": cross_doc_results.get("discrepancies", [])
        }
    )

    logs.append("Validator Agent: Validation completed.")
    return {
        **state,
        "extracted_data": extracted_data,
        "validation_results": validation_results,
        "cross_doc_results": cross_doc_results,
        "status": "validating",
        "logs": logs
    }
