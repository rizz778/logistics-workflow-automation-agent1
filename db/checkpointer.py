import logging
import os
import socket
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("agent_worker.checkpointer")

def is_socket_reachable(host: str, port: int, timeout: float = 0.2) -> bool:
    """Fast non-blocking socket probe to prevent hanging if host/port is unreachable.
    Normalizes 'localhost' to '127.0.0.1' to avoid Windows DNS resolution delays.
    """
    target_host = "127.0.0.1" if host in ("localhost", "127.0.0.1") else host
    try:
        with socket.create_connection((target_host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

class CheckpointerManager:
    """Manages connection pooling and table migrations for LangGraph checkpoint persistence."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/nova_pipeline"
        )
        parsed = urlparse(self.db_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 5432

    @asynccontextmanager
    async def get_checkpointer(self) -> AsyncIterator[AsyncPostgresSaver]:
        """Provides an active, migrated AsyncPostgresSaver checkpointer instance.
        If PostgreSQL is unreachable, immediately falls back to MemorySaver to allow seamless local execution.
        """
        if not is_socket_reachable(self.host, self.port):
            logger.info("PostgreSQL unreachable at %s:%s. Using in-memory MemorySaver.", self.host, self.port)
            fallback = MemorySaver()
            yield fallback
            return

        try:
            async with AsyncPostgresSaver.from_conn_string(self.db_url) as checkpointer:
                await checkpointer.setup()
                yield checkpointer
        except Exception as e:
            logger.warning("Failed to initialize PostgreSQL checkpointer (%s). Using MemorySaver.", e)
            fallback = MemorySaver()
            yield fallback

checkpointer_manager = CheckpointerManager()
