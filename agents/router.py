import asyncio
import json
from graph.state import PipelineState
from config.llm import get_llm
from schemas.router_schemas import RouterResponse
from prompts.router_prompts import ROUTER_SYSTEM_PROMPT
from helpers.router_agent import decide_lane
from services.event_publisher import event_publisher

async def router_agent(state: PipelineState) -> PipelineState:
    """Decoupled Router Agent:
    - Runs deterministic compliance lane selection (auto_approve, flag_review, amendment_request).
    - Formulates concise reasoning and draft amendment text with fast deterministic fallback.
    - Decoupled from human approval: leaves execution suspension to the dedicated human approval node.
    - Broadcasts decision events to Redis Pub/Sub for real-time UI tracking.
    """
    logs = list(state.get("logs", []))
    shipment_id = state.get("shipment_id", "unknown")
    run_id = state.get("run_id")

    logs.append("Router Agent: Evaluating compliance validation results...")

    validation_results = state.get("validation_results", {})
    cross_doc_results = state.get("cross_doc_results", {})

    # 1. Deterministic Lane Decision
    decision = decide_lane(validation_results, cross_doc_results)
    logs.append(f"Router Agent: Decided lane '{decision}' based on deterministic rules.")

    # 2. If auto_approved, no amendment drafting is needed
    if decision == "auto_approve":
        reasoning = "All trade documents comply with customer rules and cross-document consistency checks."
        logs.append("Router Agent: Auto-approval granted. No amendment draft needed.")

        await event_publisher.publish(
            shipment_id=shipment_id,
            step="route_complete",
            status="approved",
            message="Router granted auto-approval. Proceeding to completion.",
            run_id=run_id,
            data={"decision": decision, "reasoning": reasoning}
        )

        return {
            **state,
            "decision": decision,
            "decision_reason": reasoning,
            "amendment_draft": None,
            "human_approval_required": False,
            "status": "approved",
            "logs": logs
        }

    # 3. Formulate instant deterministic reasoning & draft fallback
    discrepancies = cross_doc_results.get("discrepancies", [])
    discrepancy_desc = "; ".join([
        f"{d.get('field', 'field')} mismatch: {', '.join(map(str, d.get('values', [])))}"
        for d in discrepancies
    ])

    rule_issues = []
    for doc, fields_res in validation_results.items():
        if isinstance(fields_res, dict):
            for f, r in fields_res.items():
                if isinstance(r, dict) and r.get("result") == "mismatch":
                    rule_issues.append(f"{f} ({r.get('reason', 'rule violation')})")

    rule_desc = "; ".join(rule_issues)

    if decision == "amendment_request":
        reasoning = f"Cross-document discrepancy detected: {discrepancy_desc or 'Document values do not match across files.'}"
        amendment_draft = f"Dear Shipper,\n\nPlease issue an amended document packet correcting the following discrepancy: {discrepancy_desc or 'conflicting field values'}.\n\nThank you,\nTrade Compliance Team"
    else:
        reasoning = f"Policy violation detected: {rule_desc or 'Field values conflict with customer compliance rules.'}"
        amendment_draft = f"Dear Shipper,\n\nThe following items do not comply with shipping policy: {rule_desc or 'unauthorized values'}.\n\nThank you,\nTrade Compliance Team"

    # Optional fast LLM enhancement (bounded by 2-second timeout to prevent API hangs)
    try:
        llm = get_llm()
        prompt = f"""
        Pre-selected decision: {decision}
        Validation Results: {json.dumps(validation_results, indent=2)}
        Cross-Doc Results: {json.dumps(cross_doc_results, indent=2)}
        Write concise reasoning and amendment draft. Output JSON: {{"reasoning": "...", "amendment_draft": "..."}}
        """
        async def _call_llm():
            res = await asyncio.to_thread(llm.invoke, [{"role": "user", "content": prompt}])
            content = res.content.strip()
            if content.startswith("```"):
                content = content.replace("```json", "", 1).replace("```", "").strip()
            return json.loads(content)

        parsed_llm = await asyncio.wait_for(_call_llm(), timeout=2.5)
        reasoning = parsed_llm.get("reasoning", reasoning)
        amendment_draft = parsed_llm.get("amendment_draft", amendment_draft)
        logs.append("Router Agent: LLM formulated enhanced reasoning.")
    except Exception as e_llm:
        logs.append(f"Router Agent: Using deterministic draft ({type(e_llm).__name__}).")

    logs.append(f"Router Agent: Finished lane '{decision}'. Routing to separate Human Approval Node.")

    await event_publisher.publish(
        shipment_id=shipment_id,
        step="route_complete",
        status="pending_approval",
        message=f"Router selected lane '{decision}'. Routing to Human Approval node.",
        run_id=run_id,
        data={
            "decision": decision,
            "decision_reason": reasoning,
            "amendment_draft": amendment_draft
        }
    )

    return {
        **state,
        "decision": decision,
        "decision_reason": reasoning,
        "amendment_draft": amendment_draft,
        "human_approval_required": True,
        "status": "pending_approval",
        "logs": logs
    }
