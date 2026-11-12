import json
from typing import List, Optional
from helpers.common_helpers import get_db_connection, map_row_to_run, map_rows_to_runs

def init_db_schema() -> None:
    """Initializes the SQLite schema for tracking audit runs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Create runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                extracted_data TEXT NOT NULL,
                validation_results TEXT NOT NULL,
                decision TEXT NOT NULL,
                decision_reason TEXT NOT NULL,
                amendment_draft TEXT,
                status TEXT NOT NULL,
                edited_data TEXT
            )
        """)
        
        # Dynamically alter table to add columns if they don't exist
        try:
            cursor.execute("ALTER TABLE pipeline_runs ADD COLUMN cross_doc_results TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE pipeline_runs ADD COLUMN source TEXT DEFAULT 'manual_upload'")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE pipeline_runs ADD COLUMN email_sender TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE pipeline_runs ADD COLUMN email_metadata_json TEXT")
        except Exception:
            pass

def save_run_db(
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
    from datetime import datetime
    upload_time = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pipeline_runs (
                filename, upload_time, extracted_data, validation_results, 
                decision, decision_reason, amendment_draft, status, 
                cross_doc_results, source, email_sender, email_metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            upload_time,
            json.dumps(extracted_data),
            json.dumps(validation_results),
            decision,
            decision_reason,
            amendment_draft,
            status,
            json.dumps(cross_doc_results or {"is_consistent": True, "discrepancies": []}),
            source,
            email_sender,
            email_metadata_json
        ))
        run_id = cursor.lastrowid
        
    return run_id

def get_run_db(run_id: int) -> Optional[dict]:
    """Retrieves a single run log by its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        
    return map_row_to_run(row)

def get_all_runs_db() -> List[dict]:
    """Retrieves all pipeline run logs in descending order."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pipeline_runs ORDER BY id DESC")
        rows = cursor.fetchall()
        
    return map_rows_to_runs(rows)

def get_incoming_runs_db() -> List[dict]:
    """Retrieves all unprocessed inbox runs (status = 'pending_review', source = 'inbox')."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pipeline_runs WHERE source = 'inbox' AND status = 'pending_review' ORDER BY id DESC")
        rows = cursor.fetchall()
        
    return map_rows_to_runs(rows)

def get_processed_runs_db() -> List[dict]:
    """Retrieves all processed/resolved inbox runs (status != 'pending_review', source = 'inbox')."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pipeline_runs WHERE source = 'inbox' AND status != 'pending_review' ORDER BY id DESC")
        rows = cursor.fetchall()
        
    return map_rows_to_runs(rows)

def update_status_db(
    run_id: int,
    status: str,
    edited_data: Optional[dict] = None,
    amendment_draft: Optional[str] = None
) -> bool:
    """Updates the status or fields of a historical pipeline run."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if edited_data is not None and amendment_draft is not None:
            cursor.execute("""
                UPDATE pipeline_runs 
                SET status = ?, edited_data = ?, amendment_draft = ?
                WHERE id = ?
            """, (status, json.dumps(edited_data), amendment_draft, run_id))
        elif edited_data is not None:
            cursor.execute("""
                UPDATE pipeline_runs 
                SET status = ?, edited_data = ?
                WHERE id = ?
            """, (status, json.dumps(edited_data), run_id))
        elif amendment_draft is not None:
            cursor.execute("""
                UPDATE pipeline_runs 
                SET status = ?, amendment_draft = ?
                WHERE id = ?
            """, (status, amendment_draft, run_id))
        else:
            cursor.execute("""
                UPDATE pipeline_runs 
                SET status = ?
                WHERE id = ?
            """, (status, run_id))
            
        updated = cursor.rowcount > 0
        
    return updated

def get_analytics_db() -> dict:
    """Returns total counts for analytics metrics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pipeline_runs")
        total_runs = cursor.fetchone()[0]
        
        cursor.execute("SELECT decision, COUNT(*) FROM pipeline_runs GROUP BY decision")
        decision_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT status, COUNT(*) FROM pipeline_runs GROUP BY status")
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
    return {
        "total_runs": total_runs,
        "decisions": {
            "auto_approve": decision_counts.get("auto_approve", 0),
            "flag_review": decision_counts.get("flag_review", 0),
            "amendment_request": decision_counts.get("amendment_request", 0)
        },
        "statuses": {
            "pending_review": status_counts.get("pending_review", 0),
            "approved": status_counts.get("approved", 0),
            "amended": status_counts.get("amended", 0)
        }
    }
