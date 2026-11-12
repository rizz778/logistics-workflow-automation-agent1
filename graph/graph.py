from langgraph.graph import StateGraph, START, END
from graph.state import PipelineState

from agents.extractor import extract_agent
from agents.validator import validator_agent
from agents.router import router_agent
from agents.human_nodes import (
    human_correction_node,
    human_approval_node,
    complete_run_node
)

def route_after_extract(state: PipelineState) -> str:
    """Evaluates extraction results:
    - If retries exhausted and confidence is low -> routes to 'human_correction'.
    - If confidence is low and retries remain -> routes back to 'extract' for auto-retry.
    - If confidence is acceptable -> proceeds to deterministic 'validate'.
    """
    if state.get("human_correction_required"):
        return "human_correction"
    if state.get("status") == "extracting":
        return "extract"
    return "validate"

def route_after_router(state: PipelineState) -> str:
    """Evaluates router decision:
    - If 'auto_approve' -> proceeds directly to 'complete_run'.
    - If 'flag_review' or 'amendment_request' -> routes to separate 'human_approval' node.
    """
    if state.get("decision") == "auto_approve":
        return "complete_run"
    return "human_approval"

pipeline_builder = StateGraph(PipelineState)

pipeline_builder.add_node("extract", extract_agent)
pipeline_builder.add_node("human_correction", human_correction_node)
pipeline_builder.add_node("validate", validator_agent)
pipeline_builder.add_node("route", router_agent)
pipeline_builder.add_node("human_approval", human_approval_node)
pipeline_builder.add_node("complete_run", complete_run_node)

pipeline_builder.add_edge(START, "extract")

pipeline_builder.add_conditional_edges(
    "extract",
    route_after_extract,
    {
        "extract": "extract",
        "human_correction": "human_correction",
        "validate": "validate"
    }
)

pipeline_builder.add_edge("human_correction", "validate")
pipeline_builder.add_edge("validate", "route")

pipeline_builder.add_conditional_edges(
    "route",
    route_after_router,
    {
        "complete_run": "complete_run",
        "human_approval": "human_approval"
    }
)

pipeline_builder.add_edge("human_approval", "complete_run")
pipeline_builder.add_edge("complete_run", END)

def create_pipeline(checkpointer=None):
    """Compiles the pipeline graph with an optional persistent checkpointer (e.g. PostgresSaver)."""
    return pipeline_builder.compile(checkpointer=checkpointer)

pipeline_graph = pipeline_builder.compile()
