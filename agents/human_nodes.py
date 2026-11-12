import logging
from typing import Dict, Any
from langgraph.types import interrupt
from graph.state import PipelineState

logger = logging.getLogger("agent_worker.human_nodes")

def human_correction_node(state: PipelineState) -> PipelineState:
    """Human-in-the-Loop Node for document field extraction correction.
    Triggered when extraction confidence is low across retries.
    Interrupts execution until the operator supplies corrected field values.
    """
    logs = list(state.get("logs", []))
    shipment_id = state.get("shipment_id", "unknown_shipment")
    low_fields = state.get("low_confidence_fields", [])
    extracted_data = state.get("extracted_data", {})

    logs.append(
        f"Human Correction Node: Low extraction confidence on {low_fields}. "
        "Interrupting workflow for human operator correction..."
    )

    # Suspend execution and persist state checkpoint
    human_input = interrupt({
        "type": "human_correction",
        "shipment_id": shipment_id,
        "low_confidence_fields": low_fields,
        "extracted_data": extracted_data,
        "message": "Please review and correct extracted fields with low confidence."
    })

    # Resumed by operator with corrected field values
    human_edits = human_input if isinstance(human_input, dict) else {}
    logs.append(
        f"Human Correction Node: Received human overrides for fields: {list(human_edits.keys())}. "
        "Resuming workflow into validator agent..."
    )

    return {
        **state,
        "human_correction_data": human_edits,
        "human_correction_required": False,
        "status": "validating",
        "logs": logs
    }

def human_approval_node(state: PipelineState) -> PipelineState:
    """Human-in-the-Loop Node for compliance review and amendment sign-off.
    Decoupled from the router agent: triggered only for non-auto-approved runs.
    Interrupts execution until an auditor approves, modifies, or signs off.
    """
    logs = list(state.get("logs", []))
    shipment_id = state.get("shipment_id", "unknown_shipment")
    decision = state.get("decision", "flag_review")
    reason = state.get("decision_reason", "")
    draft = state.get("amendment_draft")

    logs.append(
        f"Human Approval Node: Pipeline decision is '{decision}'. "
        "Interrupting workflow for auditor sign-off..."
    )

    # Suspend execution and persist state checkpoint
    approval_input = interrupt({
        "type": "human_approval",
        "shipment_id": shipment_id,
        "decision": decision,
        "decision_reason": reason,
        "amendment_draft": draft,
        "message": f"Review required. Current lane: '{decision}'."
    })

    # Resumed by auditor with approval sign-off payload
    approval_data = approval_input if isinstance(approval_input, dict) else {}
    final_status = "approved" if approval_data.get("approved") else "amended"

    logs.append(
        f"Human Approval Node: Auditor sign-off received. Final status set to '{final_status}'."
    )

    return {
        **state,
        "human_approval_data": approval_data,
        "human_approval_required": False,
        "status": final_status,
        "logs": logs
    }

def complete_run_node(state: PipelineState) -> PipelineState:
    """Finalization node marking the pipeline run as completed."""
    logs = list(state.get("logs", []))
    decision = state.get("decision", "auto_approve")
    current_status = state.get("status")

    if decision == "auto_approve":
        final_status = "approved"
    else:
        final_status = current_status or "approved"

    logs.append(f"Completion Node: Run completed. Decision: '{decision}', Status: '{final_status}'.")

    return {
        **state,
        "status": final_status,
        "logs": logs
    }

