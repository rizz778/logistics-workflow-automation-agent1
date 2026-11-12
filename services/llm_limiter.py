import asyncio
import time
import logging
import socket
from urllib.parse import urlparse
from typing import Optional
import redis.asyncio as aioredis
from config.settings import settings

logger = logging.getLogger("agent_worker.llm_limiter")

def is_socket_reachable(host: str, port: int, timeout: float = 0.2) -> bool:
    """Fast non-blocking probe to avoid connection hangs if Redis is offline."""
    target_host = "127.0.0.1" if host in ("localhost", "127.0.0.1") else host
    try:
        with socket.create_connection((target_host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

ACQUIRE_SEMAPHORE_LUA = """
local key = KEYS[1]
local max_slots = tonumber(ARGV[1])
local token = ARGV[2]
local ttl = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

redis.call('ZREMRANGEBYSCORE', key, 0, now - ttl)
local current_count = redis.call('ZCARD', key)

if current_count < max_slots then
    redis.call('ZADD', key, now, token)
    return 1
else
    return 0
end
"""

RELEASE_SEMAPHORE_LUA = """
local key = KEYS[1]
local token = ARGV[1]
redis.call('ZREM', key, token)
return 1
"""

class DistributedLlmLimiter:
    """Controls in-flight concurrent LLM calls to prevent provider 429 quota exhaustion.
    Uses a distributed Redis sorted set semaphore with auto-expiry.
    Falls back to a local asyncio.Semaphore if Redis is unreachable.
    """

    def __init__(self, max_concurrent: int = 5, ttl_seconds: int = 60):
        self.max_concurrent = max_concurrent
        self.ttl_seconds = ttl_seconds
        self.redis_key = "limiter:gemini_inflight"
        self._local_semaphore = asyncio.Semaphore(max_concurrent)
        self._redis: Optional[aioredis.Redis] = None

        parsed = urlparse(settings.redis_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 6379

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        if not is_socket_reachable(self.host, self.port):
            return None

        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.warning("Could not connect to Redis for LLM limiter (%s). Using local semaphore.", e)
                self._redis = None
        return self._redis

    async def acquire(self, timeout: float = 30.0) -> str:
        token = f"{time.time()}_{id(self)}_{asyncio.current_task().get_name() if asyncio.current_task() else 't'}"
        start_time = time.time()

        await self._local_semaphore.acquire()

        redis = await self._get_redis()
        if not redis:
            return token

        while time.time() - start_time < timeout:
            try:
                now = time.time()
                res = await redis.eval(
                    ACQUIRE_SEMAPHORE_LUA,
                    1,
                    self.redis_key,
                    str(self.max_concurrent),
                    token,
                    str(self.ttl_seconds),
                    str(now)
                )
                if int(res) == 1:
                    return token
            except Exception as e:
                logger.warning("Redis semaphore check failed (%s). Proceeding with local lock.", e)
                return token

            await asyncio.sleep(0.2)

        self._local_semaphore.release()
        raise TimeoutError(f"Timed out waiting for an available LLM slot after {timeout}s.")

    async def release(self, token: str) -> None:
        self._local_semaphore.release()

        redis = await self._get_redis()
        if redis:
            try:
                await redis.eval(RELEASE_SEMAPHORE_LUA, 1, self.redis_key, token)
            except Exception as e:
                logger.debug("Failed to release Redis semaphore token %s: %s", token, e)

class LlmSlotContext:
    def __init__(self, limiter: DistributedLlmLimiter, timeout: float = 30.0):
        self.limiter = limiter
        self.timeout = timeout
        self.token: Optional[str] = None

    async def __aenter__(self):
        self.token = await self.limiter.acquire(timeout=self.timeout)
        return self.token

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            await self.limiter.release(self.token)

llm_limiter = DistributedLlmLimiter(
    max_concurrent=settings.max_inflight_llm_calls,
    ttl_seconds=60
)

