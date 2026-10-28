"""Redis access that degrades gracefully.

`get_redis()` returns a `ResilientRedis`: it talks to Redis when it is reachable and transparently falls back to a
process-local in-memory store when it is not (or when REDIS_URL is empty). A Redis outage therefore never turns into
a 500 for login, registration or password reset. Caveat: the fallback is per-process, so with several instances and
Redis down, verification codes are only visible to the instance that issued them. Use a managed Redis (e.g. Upstash)
for serverless deployments.
"""
import logging
import time
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

log = logging.getLogger("redis")
RETRY_AFTER_SECONDS = 30


class MemoryStore:
    """Minimal async subset of the Redis API with TTL support."""

    def __init__(self) -> None:
        self._d: dict[str, tuple[str, float | None]] = {}

    def _live(self, key: str) -> tuple[str, float | None] | None:
        item = self._d.get(key)
        if item and item[1] is not None and item[1] <= time.time():
            self._d.pop(key, None)
            return None
        return item

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        item = self._live(key)
        return item[0] if item else None

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        self._d[key] = (str(value), time.time() + ex if ex else None)
        return True

    async def exists(self, *keys: str) -> int:
        return sum(1 for k in keys if self._live(k))

    async def ttl(self, key: str) -> int:
        item = self._live(key)
        if not item:
            return -2
        return -1 if item[1] is None else max(int(item[1] - time.time()), 0)

    async def delete(self, *keys: str) -> int:
        return sum(1 for k in keys if self._d.pop(k, None) is not None)

    async def incr(self, key: str) -> int:
        item = self._live(key)
        val = int(item[0]) + 1 if item else 1
        self._d[key] = (str(val), item[1] if item else None)
        return val

    async def expire(self, key: str, seconds: int) -> bool:
        item = self._live(key)
        if not item:
            return False
        self._d[key] = (item[0], time.time() + seconds)
        return True

    async def aclose(self) -> None:
        return None


class ResilientRedis:
    def __init__(self, primary: Any | None) -> None:
        self._primary = primary
        self._memory = MemoryStore()
        self._down_until = 0.0

    @property
    def using_fallback(self) -> bool:
        return self._primary is None or time.time() < self._down_until

    async def _call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if self._primary is not None and time.time() >= self._down_until:
            try:
                return await getattr(self._primary, name)(*args, **kwargs)
            except Exception as exc:  # connection refused, timeout, auth, DNS … never bubble up to the request
                self._down_until = time.time() + RETRY_AFTER_SECONDS
                log.warning("Redis unavailable (%s) — using in-memory fallback for %ss", exc.__class__.__name__, RETRY_AFTER_SECONDS)
        return await getattr(self._memory, name)(*args, **kwargs)

    async def ping(self) -> bool:
        return not self.using_fallback and bool(await self._call("ping"))

    async def get(self, key: str) -> str | None: return await self._call("get", key)
    async def set(self, key: str, value: Any, ex: int | None = None) -> bool: return await self._call("set", key, value, ex=ex)
    async def exists(self, *keys: str) -> int: return await self._call("exists", *keys)
    async def ttl(self, key: str) -> int: return await self._call("ttl", key)
    async def delete(self, *keys: str) -> int: return await self._call("delete", *keys)
    async def incr(self, key: str) -> int: return await self._call("incr", key)
    async def expire(self, key: str, seconds: int) -> bool: return await self._call("expire", key, seconds)

    async def aclose(self) -> None:
        if self._primary is not None:
            try:
                await self._primary.aclose()
            except Exception:  # pragma: no cover
                pass


_redis: ResilientRedis | None = None


def get_redis() -> ResilientRedis:
    global _redis
    if _redis is None:
        client = None
        if settings.REDIS_URL:
            try:
                client = Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2, health_check_interval=30)
            except Exception as exc:
                log.warning("Invalid REDIS_URL (%s) — using in-memory fallback", exc.__class__.__name__)
        _redis = ResilientRedis(client)
    return _redis


def set_redis(client: Any | None) -> None:
    """Override (used by tests)."""
    global _redis
    _redis = ResilientRedis(client) if client is not None else None


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
