from langgraph.graph import StateGraph, START, END
from graph.state import  PipelineState

from agents.extractor import extract_agent
from agents.validator import validator_agent
from agents.router import router_agent
from services.storage import save_pipeline_run


def db_saver_node(state: PipelineState) -> PipelineState:
    """Graph node to persist final pipeline outcomes to the SQLite database."""
    import json
    logs = list(state.get("logs", []))
    logs.append("Storage Node: Saving pipeline results to SQLite database...")
    
    # Extract filenames representation
    filenames = state.get("filenames", [])
    if not filenames:
        filenames = [state.get("filename", "document.pdf")]
    db_filename = ", ".join(filenames)
    
    # Bundle email metadata if present
    email_meta_str = None
    email_subj = state.get("email_subject")
    email_body = state.get("email_body")
    recv_at = state.get("received_at")
    
    if email_subj or email_body or recv_at:
        email_meta_str = json.dumps({
            "subject": email_subj,
            "email_body": email_body,
            "received_at": recv_at
        })
    
    # Save to SQLite
    run_id = save_pipeline_run(
        filename=db_filename,
        extracted_data=state["extracted_data"],
        validation_results=state["validation_results"],
        decision=state["decision"],
        decision_reason=state["decision_reason"],
        amendment_draft=state["amendment_draft"],
        status="approved" if state["decision"] == "auto_approve" else "pending_review",
        cross_doc_results=state.get("cross_doc_results"),
        source=state.get("source", "manual_upload"),
        email_sender=state.get("email_sender"),
        email_metadata_json=email_meta_str
    )
    
    logs.append(f"Storage Node: Run saved successfully. DB ID: {run_id}")
    return {
        **state,
        "logs": logs
    }


# minimalistic graph  construction extract-> validate -> route -> save to db


pipeline_builder = StateGraph(PipelineState)
pipeline_builder.add_node("extract", extract_agent)
pipeline_builder.add_node("validate", validator_agent)
pipeline_builder.add_node("route", router_agent)
pipeline_builder.add_node("save", db_saver_node)

pipeline_builder.add_edge(START, "extract")
pipeline_builder.add_edge("extract", "validate")
pipeline_builder.add_edge("validate", "route")
pipeline_builder.add_edge("route", "save")
pipeline_builder.add_edge("save", END)

pipeline_graph = pipeline_builder.compile()
