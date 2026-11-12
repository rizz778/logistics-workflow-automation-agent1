import asyncio
import json
import logging
import time
import socket
from urllib.parse import urlparse
from typing import Dict, Any, Optional

import redis.asyncio as aioredis
from config.settings import settings

logger = logging.getLogger("agent_worker.event_publisher")


def is_socket_reachable(host: str, port: int, timeout: float = 0.2) -> bool:
    """Fast non-blocking probe to avoid connection hangs if Redis is offline."""
    target_host = "127.0.0.1" if host in ("localhost", "127.0.0.1") else host
    try:
        with socket.create_connection((target_host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


class EventPublisher:
    """Broadcasts real-time pipeline lifecycle events across Redis Pub/Sub.
    Channels:
      - `run_events:{shipment_id}` : Specific to a single shipment run (consumed by Gateway SSE).
      - `run_events:global`        : Broadcast channel for fleet-wide audit dashboards.
    """

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self._redis = redis_client
        parsed = urlparse(settings.redis_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 6379

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        if self._redis is not None:
            return self._redis

        if not is_socket_reachable(self.host, self.port):
            return None

        try:
            self._redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2.0
            )
            return self._redis
        except Exception as e:
            logger.debug("Redis Pub/Sub connection failed (%s). Continuing in headless mode.", e)
            return None

    async def publish(
        self,
        shipment_id: str,
        step: str,
        status: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        run_id: Optional[int] = None
    ) -> bool:
        """Publishes an event to both the shipment-specific and global channels."""
        event_payload = {
            "shipment_id": str(shipment_id),
            "run_id": run_id,
            "step": step,
            "status": status,
            "message": message,
            "data": data or {},
            "timestamp": time.time()
        }

        raw_json = json.dumps(event_payload)
        logger.info("[Event Pub/Sub] %s | %s -> %s: %s", shipment_id, step, status, message)

        redis = await self._get_redis()
        if not redis:
            return False

        try:
            # 1. Publish to shipment-specific channel (subscribed by Gateway SSE for that run)
            shipment_channel = f"run_events:{shipment_id}"
            await redis.publish(shipment_channel, raw_json)

            # 2. Publish to global stream channel for fleet monitors
            await redis.publish("run_events:global", raw_json)
            return True
        except Exception as e:
            logger.warning("Failed to publish event to Redis Pub/Sub for shipment '%s': %s", shipment_id, e)
            return False


# Shared default singleton
event_publisher = EventPublisher()

