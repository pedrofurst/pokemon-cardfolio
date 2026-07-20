"""A PriceProvider that caches card searches.

Wraps another provider rather than caching inside PokemonTcgIoProvider, so the
HTTP client stays free of cache concerns and the decorator can be dropped in or
left out at wiring time.

Only search_cards is cached. get_price passes straight through: prices are what
the portfolio's numbers are built from, and serving a stale one to a refresh
would write a stale snapshot to the database.
"""

import json
import logging
from dataclasses import asdict

from app.cache import Cache
from app.providers.base import CardResult, PriceProvider, PriceResult

logger = logging.getLogger(__name__)

_KEY_PREFIX = "search:"


def _cache_key(query: str) -> str:
    return f"{_KEY_PREFIX}{query.strip().lower()}"


class CachedPriceProvider:
    def __init__(self, inner: PriceProvider, cache: Cache, ttl_seconds: int) -> None:
        self.inner = inner
        self.cache = cache
        self.ttl_seconds = ttl_seconds

    def search_cards(self, query: str) -> list[CardResult]:
        key = _cache_key(query)
        cached = self.cache.get(key)
        if cached is not None:
            try:
                return [CardResult(**item) for item in json.loads(cached)]
            except (TypeError, ValueError):
                # A malformed or stale-shaped entry (say, after CardResult gains
                # a field) must not break search — fall through to a live fetch.
                logger.warning("Discarding unreadable cache entry %s", key, exc_info=True)

        results = self.inner.search_cards(query)
        # Never cache an empty result. pokemontcg.io intermittently returns a
        # degraded response, and caching one turns a momentary blip into ten
        # minutes of a wrong answer. A genuine no-match search is cheap to
        # repeat; a poisoned cache entry is not.
        if results:
            self.cache.set(
                key, json.dumps([asdict(result) for result in results]), self.ttl_seconds
            )
        return results

    def get_price(self, card_id: str) -> PriceResult:
        return self.inner.get_price(card_id)
