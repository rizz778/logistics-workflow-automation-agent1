import sqlite3
from typing import Optional
from google import genai
from config.settings import settings
import os
import json

def get_gemini_client() -> genai.Client:
    """Creates and returns a google.genai Client instance."""
    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=api_key)

    return Mistral(api_key=api_key)

def load_rules() -> dict:
    """Loads rules from config or falls back to defaults."""
    if os.path.exists(settings.rules_path):
        try:
            with open(settings.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("rules", {})
        except Exception as e:
            print(f"Error loading rules.json: {e}")
            
    # Default fallback rules
    return {
        "consignee_name": {"type": "exact_match", "expected": "Nova Logistics Ltd"},
        "hs_code": {"type": "prefix_match", "expected_prefixes": ["8708"]},
        "incoterms": {"type": "allow_list", "expected": ["FOB", "CIF"]}
    }

def get_db_connection():
    """Establishes a connection to the SQLite database.
    Creates any missing parent directories dynamically.
    """
    db_dir = os.path.dirname(settings.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn

def map_row_to_run(row) -> Optional[dict]:
    """Helper to safely serialize an SQLite Row into a dictionary matching PipelineRun model."""
    if not row:
        return None
        
    def get_col(r, key, default=None):
        try:
            return r[key]
        except (IndexError, KeyError):
            return default
            
    cross_doc_raw = get_col(row, "cross_doc_results")
    source_val = get_col(row, "source", "manual_upload")
    email_sender_val = get_col(row, "email_sender")
    email_meta_raw = get_col(row, "email_metadata_json")
    
    meta = json.loads(email_meta_raw) if email_meta_raw else {}
    
    return {
        "id": row["id"],
        "filename": row["filename"],
        "upload_time": row["upload_time"],
        "extracted_data": json.loads(row["extracted_data"]),
        "validation_results": json.loads(row["validation_results"]),
        "decision": row["decision"],
        "decision_reason": row["decision_reason"],
        "amendment_draft": row["amendment_draft"],
        "status": row["status"],
        "edited_data": json.loads(row["edited_data"]) if row["edited_data"] else None,
        "cross_doc_results": json.loads(cross_doc_raw) if cross_doc_raw else {"is_consistent": True, "discrepancies": []},
        "source": source_val,
        "email_sender": email_sender_val,
        "email_subject": meta.get("subject"),
        "email_body": meta.get("email_body"),
        "received_at": meta.get("received_at")
    }

def map_rows_to_runs(rows) -> list[dict]:
    """Maps a list of SQLite Rows into a list of PipelineRun dictionaries."""
    return [map_row_to_run(row) for row in rows]

