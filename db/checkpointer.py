import logging
import os
import socket
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from config.settings import settings

logger = logging.getLogger("agent_worker.checkpointer")

def is_socket_reachable(host: str, port: int, timeout: float = 2.5) -> bool:
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
    """Manages connection pooling and table migrations for LangGraph checkpoint persistence.
    Runs setup() ONCE at startup to avoid per-task migration overhead (~2min latency).
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.database_url
        parsed = urlparse(self.db_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 5432
        self._cm = None
        self._checkpointer: Optional[AsyncPostgresSaver] = None
        self._setup_done: bool = False
        self._use_memory: bool = False

    async def initialize(self) -> None:
        """Call once at worker startup to run DB migrations and warm the connection pool."""
        try:
            self._cm = AsyncPostgresSaver.from_conn_string(self.db_url)
            self._checkpointer = await self._cm.__aenter__()
            await self._checkpointer.setup()
            self._setup_done = True
            logger.info("LangGraph PostgreSQL checkpointer initialized and schema migrated.")
        except Exception as e:
            logger.warning("Failed to initialize PostgreSQL checkpointer (%s). Using MemorySaver.", e)
            self._checkpointer = None
            self._use_memory = True

    @asynccontextmanager
    async def get_checkpointer(self) -> AsyncIterator:
        """Returns the pre-initialized checkpointer (no setup overhead per task)."""
        if self._use_memory or not self._setup_done or self._checkpointer is None:
            yield MemorySaver()
        else:
            yield self._checkpointer

    async def close(self) -> None:
        """Gracefully close the checkpointer connection on worker shutdown."""
        if self._cm is not None:
            try:
                await self._cm.__aexit__(None, None, None)
                logger.info("LangGraph checkpointer connection closed.")
            except Exception:
                pass

checkpointer_manager = CheckpointerManager()
