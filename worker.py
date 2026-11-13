"""Entry point for the Trade Document Agent Worker service.
Listens to Redis Streams and executes the multi-agent LangGraph compliance pipeline.
Includes a lightweight health server to satisfy cloud platform requirements (e.g. Koyeb Free Tier).
"""
import os
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

async def start_health_server(port: int = 8000) -> None:
    """Lightweight zero-dependency HTTP server to satisfy cloud platform health checks."""
    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await reader.read(1024)
            response = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 15\r\nConnection: close\r\n\r\n{\"status\":\"ok\"}"
            writer.write(response)
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    try:
        server = await asyncio.start_server(handle_client, "0.0.0.0", port)
        logger.info("Health check server listening on http://0.0.0.0:%d (for Koyeb/Cloud platforms)", port)
        await server.serve_forever()
    except Exception as e:
        logger.warning("Could not start health check server on port %d: %s", port, e)

async def run_services() -> None:
    port = int(os.getenv("PORT", "8000"))
    daemon = TradeDocWorkerDaemon()
    await asyncio.gather(
        start_health_server(port=port),
        daemon.start()
    )

def main() -> None:
    """Instantiates and starts the Trade Document Worker daemon."""
    try:
        asyncio.run(run_services())
    except KeyboardInterrupt:
        logger.info("Worker daemon terminated by operator.")

if __name__ == "__main__":
    main()
