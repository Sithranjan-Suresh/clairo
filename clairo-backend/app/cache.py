"""Small cache abstraction: Redis when REDIS_URL is set, in-process TTL dict
otherwise. A Redis failure degrades to a cache miss — it never breaks a request.
"""
import functools
import hashlib
import json
import logging
import threading
import time
from typing import Any, Callable, Optional

from app.config import REDIS_URL
from app.observability import CACHE_EVENTS

logger = logging.getLogger(__name__)

_MAX_MEMORY_ITEMS = 2048


class _MemoryBackend:
    def __init__(self) -> None:
        self._data: dict = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if expires < time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            if len(self._data) >= _MAX_MEMORY_ITEMS:
                now = time.monotonic()
                for k in [k for k, (exp, _) in self._data.items() if exp < now]:
                    del self._data[k]
                if len(self._data) >= _MAX_MEMORY_ITEMS:
                    self._data.pop(next(iter(self._data)))  # oldest insertion
            self._data[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class _RedisBackend:
    def __init__(self, url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(
            url, socket_timeout=0.5, socket_connect_timeout=0.5, decode_responses=True
        )

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: int) -> None:
        self._client.set(key, value, ex=ttl)

    def clear(self) -> None:
        self._client.flushdb()


class Cache:
    def __init__(self) -> None:
        self._memory = _MemoryBackend()
        self._redis: Optional[_RedisBackend] = None
        if REDIS_URL:
            try:
                self._redis = _RedisBackend(REDIS_URL)
            except Exception:
                logger.exception("Redis unavailable at startup; using in-memory cache")

    @property
    def backend(self) -> str:
        return "redis" if self._redis else "memory"

    def get(self, namespace: str, key: str) -> Any:
        full = f"clairo:{namespace}:{key}"
        raw = None
        if self._redis:
            try:
                raw = self._redis.get(full)
            except Exception:
                logger.warning("Redis get failed; treating as miss", exc_info=True)
        else:
            raw = self._memory.get(full)
        if raw is None:
            CACHE_EVENTS.labels(namespace, "miss").inc()
            return None
        CACHE_EVENTS.labels(namespace, "hit").inc()
        return json.loads(raw)

    def set(self, namespace: str, key: str, value: Any, ttl: int) -> None:
        full = f"clairo:{namespace}:{key}"
        raw = json.dumps(value, default=str)
        if self._redis:
            try:
                self._redis.set(full, raw, ttl)
            except Exception:
                logger.warning("Redis set failed; skipping cache write", exc_info=True)
        else:
            self._memory.set(full, raw, ttl)

    def clear(self) -> None:
        self._memory.clear()
        if self._redis:
            try:
                self._redis.clear()
            except Exception:
                logger.warning("Redis clear failed", exc_info=True)


cache = Cache()


def cached(namespace: str, ttl: int) -> Callable:
    """Memoize a function with JSON-serialisable args/results."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            digest = hashlib.sha256(
                json.dumps([args, kwargs], sort_keys=True, default=str).encode()
            ).hexdigest()
            hit = cache.get(namespace, digest)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            cache.set(namespace, digest, result, ttl)
            return result

        wrapper.__wrapped__ = fn
        return wrapper

    return decorator
