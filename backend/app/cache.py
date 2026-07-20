"""Cache backends for expensive upstream lookups.

The cache is always optional. pokemontcg.io is slow and erratic (measured
1-30s for the same query), so caching is a real win — but a missing or broken
Redis must never take the app down with it. Every failure path here degrades to
"no caching" rather than raising, and `make_cache` falls back to NullCache when
Redis can't be reached at startup.
"""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class Cache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class NullCache:
    """Does nothing. Used when Redis isn't configured or isn't reachable."""

    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None


class RedisCache:
    def __init__(self, client) -> None:
        self.client = client

    def get(self, key: str) -> str | None:
        try:
            value = self.client.get(key)
        except Exception:
            logger.warning("Cache read failed for %s", key, exc_info=True)
            return None
        return value.decode("utf-8") if isinstance(value, bytes) else value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self.client.set(key, value, ex=ttl_seconds)
        except Exception:
            logger.warning("Cache write failed for %s", key, exc_info=True)


def make_cache(redis_url: str) -> Cache:
    """Build a Redis-backed cache, or a NullCache if Redis is unavailable.

    The connection is verified with a PING here so an unreachable Redis costs
    one failed connect at startup rather than a timeout on every request.
    """
    if not redis_url:
        return NullCache()

    try:
        import redis

        client = redis.Redis.from_url(
            redis_url, socket_connect_timeout=2, socket_timeout=2
        )
        client.ping()
    except Exception:
        logger.warning(
            "Redis unavailable at %s — continuing without a cache", redis_url,
            exc_info=True,
        )
        return NullCache()

    logger.info("Redis cache connected at %s", redis_url)
    return RedisCache(client)
