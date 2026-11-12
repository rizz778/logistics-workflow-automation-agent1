from typing import TypedDict, Optional, List, Dict, Any

class PipelineState(TypedDict, total=False):
    """Unified state for the multi-agent trade document compliance pipeline."""

    # 1. Shipment & Run Identifiers
    shipment_id: str                                  # Unique shipment ID (thread_id for LangGraph checkpoints)
    run_id: Optional[int]                             # Primary key in PostgreSQL pipeline_runs

    # 2. Document Inputs
    filenames: List[str]                              # List of document filenames (e.g. ["bol.pdf", "invoice.pdf"])
    file_paths: Optional[List[str]]                   # Local paths on server (for local dev / eval runner)
    files: Optional[List[Dict[str, Any]]]             # S3 file descriptors: [{"filename": ..., "s3_key": ...}]
    file_bytes_map: Optional[Dict[str, bytes]]        # In-memory document bytes keyed by filename

    # 3. Extractor State & Confidence Scoring
    extracted_data: Dict[str, Any]                    # Map of filename -> extracted JSON dictionary
    avg_confidence: float                             # Average extraction confidence score (0.0 to 1.0)
    low_confidence_fields: List[str]                  # Fields scoring below threshold or missing
    extraction_retry_count: int                       # Current retry attempt count (0, 1, 2, 3)
    max_extraction_retries: int                       # Maximum allowed retries (default 3) before HitL

    # 4. Human-in-the-Loop: Field Correction (Low Confidence Interrupt)
    human_correction_required: bool                   # True when low confidence requires operator intervention
    human_correction_data: Optional[Dict[str, Any]]   # Corrected field values provided by human operator

    # 5. Deterministic Validator State
    validation_results: Dict[str, Any]                # Map of filename -> field validation results
    cross_doc_results: Dict[str, Any]                 # Cross-document consistency discrepancies

    # 6. Router State & Amendment Drafting
    decision: str                                     # 'auto_approve' | 'flag_review' | 'amendment_request'
    decision_reason: str                              # Concise explanation of the decision
    amendment_draft: Optional[str]                    # Generated email/letter draft if amendment is required

    # 7. Human-in-the-Loop: Final Approval / Sign-Off
    human_approval_required: bool                     # True if decision != auto_approve
    human_approval_data: Optional[Dict[str, Any]]     # Auditor sign-off metadata (approved/rejected/modified)

    # 8. Execution Status, Logs & Ingestion Metadata
    status: str                                       # 'extracting' | 'pending_correction' | 'validating' | 'pending_approval' | 'approved' | 'amended'
    logs: List[str]                                   # Execution trace logs accumulated across nodes
    source: str                                       # 'manual_upload' | 'inbox'
    email_sender: Optional[str]                       # Supplier email address if received via email
    email_subject: Optional[str]                      # Email subject line
    email_body: Optional[str]                         # Email body content
    received_at: Optional[str]                        # Ingestion timestamp
