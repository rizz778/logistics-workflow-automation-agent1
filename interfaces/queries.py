# Centralized SQL query constants for the Agent Worker Service

UPDATE_RUN_OUTCOMES_SQL = """
UPDATE pipeline_runs
SET extracted_data = %s::jsonb,
    validation_results = %s::jsonb,
    cross_doc_results = %s::jsonb,
    decision = %s,
    decision_reason = %s,
    amendment_draft = %s,
    status = %s
WHERE shipment_id = %s;
"""

UPDATE_RUN_STATUS_SQL = """
UPDATE pipeline_runs
SET status = %s
WHERE shipment_id = %s;
"""

GET_RUN_SQL = """
SELECT id, shipment_id, filename, status, extracted_data, validation_results,
       cross_doc_results, decision, decision_reason, amendment_draft, edited_data
FROM pipeline_runs
WHERE shipment_id = %s;
"""

