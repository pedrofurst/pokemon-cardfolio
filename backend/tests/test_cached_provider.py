import json

from app.cache import NullCache
from app.providers.base import CardResult, PriceResult
from app.providers.cached import CachedPriceProvider


class DictCache:
    """In-memory stand-in for Redis; records TTLs so they can be asserted."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl_seconds):
        self.store[key] = value
        self.ttls[key] = ttl_seconds


class CountingProvider:
    def __init__(self) -> None:
        self.search_calls = 0
        self.price_calls = 0

    def search_cards(self, query):
        self.search_calls += 1
        return [CardResult(
            id="base1-4", name="Charizard", set_name="Base", number="4",
            rarity="Rare Holo", image_url="i", tcgplayer_id=None, market_price=350.0,
        )]

    def get_price(self, card_id):
        self.price_calls += 1
        return PriceResult(card_id=card_id, market_price=1.0, currency="USD", source="fake")


def test_first_search_hits_the_upstream_provider():
    inner = CountingProvider()
    CachedPriceProvider(inner, DictCache(), 600).search_cards("charizard")
    assert inner.search_calls == 1


def test_repeated_search_does_not_hit_the_upstream_provider_again():
    inner = CountingProvider()
    provider = CachedPriceProvider(inner, DictCache(), 600)
    provider.search_cards("charizard")
    provider.search_cards("charizard")
    assert inner.search_calls == 1


def test_cached_search_returns_the_same_cards():
    provider = CachedPriceProvider(CountingProvider(), DictCache(), 600)
    first = provider.search_cards("charizard")
    assert provider.search_cards("charizard") == first


def test_search_cache_key_ignores_case_and_surrounding_space():
    inner = CountingProvider()
    provider = CachedPriceProvider(inner, DictCache(), 600)
    provider.search_cards("Charizard")
    provider.search_cards("  charizard ")
    assert inner.search_calls == 1


def test_different_queries_are_cached_separately():
    inner = CountingProvider()
    provider = CachedPriceProvider(inner, DictCache(), 600)
    provider.search_cards("charizard")
    provider.search_cards("pikachu")
    assert inner.search_calls == 2


def test_search_is_written_with_the_configured_ttl():
    cache = DictCache()
    CachedPriceProvider(CountingProvider(), cache, 600).search_cards("charizard")
    assert cache.ttls["search:charizard"] == 600


def test_unreadable_cache_entry_falls_back_to_a_live_search():
    cache = DictCache()
    cache.store["search:charizard"] = "{not valid json"
    inner = CountingProvider()
    assert CachedPriceProvider(inner, cache, 600).search_cards("charizard")[0].name == "Charizard"


def test_cache_entry_with_an_unexpected_shape_falls_back_to_a_live_search():
    cache = DictCache()
    cache.store["search:charizard"] = json.dumps([{"unexpected": "shape"}])
    inner = CountingProvider()
    CachedPriceProvider(inner, cache, 600).search_cards("charizard")
    assert inner.search_calls == 1


def test_null_cache_means_every_search_hits_upstream():
    inner = CountingProvider()
    provider = CachedPriceProvider(inner, NullCache(), 600)
    provider.search_cards("charizard")
    provider.search_cards("charizard")
    assert inner.search_calls == 2


def test_get_price_is_not_cached():
    inner = CountingProvider()
    provider = CachedPriceProvider(inner, DictCache(), 600)
    provider.get_price("base1-4")
    provider.get_price("base1-4")
    assert inner.price_calls == 2


class EmptyResultProvider:
    def __init__(self) -> None:
        self.search_calls = 0

    def search_cards(self, query):
        self.search_calls += 1
        return []

    def get_price(self, card_id):
        raise NotImplementedError


def test_empty_results_are_not_cached():
    cache = DictCache()
    CachedPriceProvider(EmptyResultProvider(), cache, 600).search_cards("zzzz")
    assert cache.store == {}


def test_empty_results_are_refetched_rather_than_served_from_cache():
    inner = EmptyResultProvider()
    provider = CachedPriceProvider(inner, DictCache(), 600)
    provider.search_cards("zzzz")
    provider.search_cards("zzzz")
    assert inner.search_calls == 2
