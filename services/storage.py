from typing import List, Optional
from interfaces.repository import PipelineRunRepository

# Re-export get_db_connection for backward compatibility (e.g. services/query.py)
from helpers.common_helpers import get_db_connection

from helpers.db_helpers import (
    init_db_schema,
    save_run_db,
    get_run_db,
    get_all_runs_db,
    get_incoming_runs_db,
    get_processed_runs_db,
    update_status_db,
    get_analytics_db
)

class SQLitePipelineRunRepository(PipelineRunRepository):
    def init_db(self) -> None:
        """Initializes the SQLite schema for tracking audit runs."""
        init_db_schema()

    def save_run(
        self,
        filename: str,
        extracted_data: dict,
        validation_results: dict,
        decision: str,
        decision_reason: str,
        amendment_draft: Optional[str],
        status: str = "pending_review",
        cross_doc_results: Optional[dict] = None,
        source: str = "manual_upload",
        email_sender: Optional[str] = None,
        email_metadata_json: Optional[str] = None
    ) -> int:
        """Saves a run log to the SQLite table and returns the row ID."""
        return save_run_db(
            filename=filename,
            extracted_data=extracted_data,
            validation_results=validation_results,
            decision=decision,
            decision_reason=decision_reason,
            amendment_draft=amendment_draft,
            status=status,
            cross_doc_results=cross_doc_results,
            source=source,
            email_sender=email_sender,
            email_metadata_json=email_metadata_json
        )

    def get_run(self, run_id: int) -> Optional[dict]:
        """Retrieves a single run log by its ID."""
        return get_run_db(run_id)

    def get_all(self) -> List[dict]:
        """Retrieves all pipeline run logs in descending order."""
        return get_all_runs_db()

    def get_incoming(self) -> List[dict]:
        """Retrieves all unprocessed inbox runs (status = 'pending_review', source = 'inbox')."""
        return get_incoming_runs_db()

    def get_processed(self) -> List[dict]:
        """Retrieves all processed/resolved inbox runs (status != 'pending_review', source = 'inbox')."""
        return get_processed_runs_db()

    def update_status(
        self,
        run_id: int,
        status: str,
        edited_data: Optional[dict] = None,
        amendment_draft: Optional[str] = None
    ) -> bool:
        """Updates the status or fields of a historical pipeline run."""
        return update_status_db(
            run_id=run_id,
            status=status,
            edited_data=edited_data,
            amendment_draft=amendment_draft
        )

    def get_analytics(self) -> dict:
        """Returns total counts for analytics metrics."""
        return get_analytics_db()

# Singleton shared instance
db = SQLitePipelineRunRepository()


def init_db() -> None:
    db.init_db()

def save_pipeline_run(
    filename: str,
    extracted_data: dict,
    validation_results: dict,
    decision: str,
    decision_reason: str,
    amendment_draft: Optional[str],
    status: str = "pending_review",
    cross_doc_results: Optional[dict] = None,
    source: str = "manual_upload",
    email_sender: Optional[str] = None,
    email_metadata_json: Optional[str] = None
) -> int:
    return db.save_run(
        filename=filename,
        extracted_data=extracted_data,
        validation_results=validation_results,
        decision=decision,
        decision_reason=decision_reason,
        amendment_draft=amendment_draft,
        status=status,
        cross_doc_results=cross_doc_results,
        source=source,
        email_sender=email_sender,
        email_metadata_json=email_metadata_json
    )

def get_pipeline_run(run_id: int) -> Optional[dict]:
    return db.get_run(run_id)

def get_all_runs() -> List[dict]:
    return db.get_all()

def get_incoming_runs() -> List[dict]:
    return db.get_incoming()

def get_processed_runs() -> List[dict]:
    return db.get_processed()

def update_run_status(
    run_id: int,
    status: str,
    edited_data: Optional[dict] = None,
    amendment_draft: Optional[str] = None
) -> bool:
    return db.update_status(
        run_id=run_id,
        status=status,
        edited_data=edited_data,
        amendment_draft=amendment_draft
    )

def get_analytics() -> dict:
    return db.get_analytics()
