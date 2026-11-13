"""Entry point for the Trade Document Agent Worker service.
Listens to Redis Streams and executes the multi-agent LangGraph compliance pipeline.
"""
import sys
import asyncio
import logging

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from services.worker_daemon import TradeDocWorkerDaemon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("worker_entry")

def main() -> None:
    """Instantiates and starts the Trade Document Worker daemon."""
    daemon = TradeDocWorkerDaemon()
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("Worker daemon terminated by operator.")

if __name__ == "__main__":
    main()
