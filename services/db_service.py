import json
import logging
import socket
from urllib.parse import urlparse
from typing import Dict, Any, Optional
import psycopg
from psycopg.rows import dict_row
from config.settings import settings
from interfaces.queries import (
    UPDATE_RUN_OUTCOMES_SQL,
    UPDATE_RUN_STATUS_SQL,
    GET_RUN_SQL
)

logger = logging.getLogger("agent_worker.db_service")

def is_socket_reachable(host: str, port: int, timeout: float = 2.5) -> bool:
    """Fast non-blocking probe to avoid connection hangs if PostgreSQL is offline."""
    target_host = "127.0.0.1" if host in ("localhost", "127.0.0.1") else host
    try:
        with socket.create_connection((target_host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

class WorkerDatabaseService:
    """Persists pipeline graph outcomes and execution status transitions to PostgreSQL."""

    def __init__(self):
        self.db_url = settings.database_url
        parsed = urlparse(self.db_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 5432

    def _is_db_ready(self) -> bool:
        return True

    async def update_run_outcomes(
        self,
        shipment_id: str,
        extracted_data: Dict[str, Any],
        validation_results: Dict[str, Any],
        decision: str,
        decision_reason: str,
        amendment_draft: Optional[str],
        status: str,
        cross_doc_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Atomically saves final LangGraph execution artifacts to PostgreSQL."""
        if not self._is_db_ready():
            logger.info("PostgreSQL offline at %s:%s. Skipping DB outcome persistence.", self.host, self.port)
            return False

        try:
            async with await psycopg.AsyncConnection.connect(self.db_url, autocommit=True) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        UPDATE_RUN_OUTCOMES_SQL,
                        (
                            json.dumps(extracted_data),
                            json.dumps(validation_results),
                            json.dumps(cross_doc_results or {}),
                            decision,
                            decision_reason,
                            amendment_draft,
                            status,
                            shipment_id
                        )
                    )
                    logger.info("Successfully persisted run outcomes to PostgreSQL for %s.", shipment_id)
                    return True
        except Exception as e:
            logger.error("Failed to update pipeline run outcomes in PostgreSQL for %s: %s", shipment_id, e)
            return False

    async def update_run_status(self, shipment_id: str, status: str) -> bool:
        """Updates pipeline run status (e.g. 'pending_correction', 'processing', 'failed')."""
        if not self._is_db_ready():
            return False

        try:
            async with await psycopg.AsyncConnection.connect(self.db_url, autocommit=True) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(UPDATE_RUN_STATUS_SQL, (status, shipment_id))
                    logger.info("Updated status to '%s' for shipment %s.", status, shipment_id)
                    return True
        except Exception as e:
            logger.error("Failed to update status for %s: %s", shipment_id, e)
            return False

    async def get_run(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single pipeline run row by shipment_id."""
        if not self._is_db_ready():
            return None

        try:
            async with await psycopg.AsyncConnection.connect(self.db_url, row_factory=dict_row) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(GET_RUN_SQL, (shipment_id,))
                    return await cur.fetchone()
        except Exception as e:
            logger.error("Failed to get run %s from DB: %s", shipment_id, e)
            return None

db_service = WorkerDatabaseService()
