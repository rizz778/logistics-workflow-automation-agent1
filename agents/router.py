import json
from graph.state import PipelineState
from config.llm import get_llm
from schemas.router_schemas import RouterResponse
from prompts.router_prompts import ROUTER_SYSTEM_PROMPT
from helpers.router_agent import decide_lane

def router_agent(state: PipelineState) -> PipelineState:
    """Decoupled Router Agent:
    - Runs deterministic compliance lane selection (auto_approve, flag_review, amendment_request).
    - Invokes LLM to generate concise reasoning and draft amendment text.
    - Decoupled from human approval: leaves execution suspension to the dedicated human approval node.
    """
    logs = list(state.get("logs", []))
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
        return {
            **state,
            "decision": decision,
            "decision_reason": reasoning,
            "amendment_draft": None,
            "human_approval_required": False,
            "status": "approved",
            "logs": logs
        }

    # 3. For flag_review or amendment_request, invoke LLM to formulate clear reasoning and draft
    logs.append("Router Agent: Invoking LLM to formulate concise discrepancy reasoning and amendment draft...")
    llm = get_llm()
    reasoning = ""
    amendment_draft = ""

    prompt = f"""
    The pre-selected workflow decision is: {decision}

    Here is the field-by-field Validation Results:
    {json.dumps(validation_results, indent=2)}

    Here is the Cross-Document Consistency Results:
    {json.dumps(cross_doc_results, indent=2)}

    Write concise reasoning (2-3 sentences) and a concise draft message if required.
    Keep explanations direct and avoid unnecessary filler. If there are cross-document discrepancies, list them clearly.
    """

    try:
        structured_llm = llm.with_structured_output(RouterResponse)
        router_result = structured_llm.invoke([
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])
        reasoning = router_result.reasoning
        amendment_draft = router_result.amendment_draft
    except Exception as e:
        logs.append(f"Router Agent: Structured output failed ({str(e)}). Running fallback JSON prompt...")
        fallback_prompt = f"""{ROUTER_SYSTEM_PROMPT}
        You must output a raw JSON object matching this schema exactly:
        {{
            "reasoning": "string",
            "amendment_draft": "string"
        }}
        Do not include markdown wrappers (like ```json), just output raw JSON.

        Decision: {decision}
        Validation Results:
        {json.dumps(validation_results, indent=2)}
        Cross-Document Consistency Results:
        {json.dumps(cross_doc_results, indent=2)}
        """
        try:
            response = llm.invoke([{"role": "user", "content": fallback_prompt}])
            content = response.content.strip()
            if content.startswith("```"):
                content = content.replace("```json", "", 1).replace("```", "").strip()
            res_dict = json.loads(content)
            reasoning = res_dict.get("reasoning", "Compliance discrepancy detected during validation.")
            amendment_draft = res_dict.get("amendment_draft", "")
        except Exception as e_fallback:
            logs.append(f"Router Agent: Fallback failed ({str(e_fallback)}). Setting default notes.")
            reasoning = f"Deterministic decision: {decision}. Compliance discrepancies require inspection."
            amendment_draft = "Please review the document discrepancies manually."

    logs.append(f"Router Agent: Finished lane '{decision}'. Routing to separate Human Approval Node.")

    return {
        **state,
        "decision": decision,
        "decision_reason": reasoning,
        "amendment_draft": amendment_draft,
        "human_approval_required": True,
        "status": "pending_approval",
        "logs": logs
    }
