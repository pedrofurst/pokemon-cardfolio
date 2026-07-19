import pytest

from app.errors import PriceProviderError
from app.providers.base import CardResult, SetInfo
from app.services.store_service import StoreService, clear_store_cache

SET_ALPHA = SetInfo(
    id="set-a", name="Set Alpha", series="Alpha", total=100,
    release_date="2024-01-01", logo_url="logo-a",
)
SET_BETA = SetInfo(
    id="set-b", name="Set Beta", series="Beta", total=50,
    release_date="2024-02-01", logo_url="logo-b",
)
SET_GAMMA = SetInfo(
    id="set-g", name="Set Gamma", series="Gamma", total=80,
    release_date="2026-05-01", logo_url="logo-g",
)
SET_DELTA = SetInfo(
    id="set-d", name="Set Delta", series="Delta", total=90,
    release_date="2026-06-01", logo_url="logo-d",
)
SET_ERROR = SetInfo(
    id="set-e", name="Set Error", series="Error", total=60,
    release_date="2026-04-01", logo_url="logo-e",
)


def _card(id, name, price, rarity, tcgplayer_id=None):
    return CardResult(
        id=id, name=name, set_name="Set Alpha", number="1", rarity=rarity,
        image_url="img", tcgplayer_id=tcgplayer_id, market_price=price,
    )


ALPHA_CARDS = [
    _card("a1", "Alpha One", 50.0, "Rare Holo", tcgplayer_id="https://tcgplayer.com/product/123"),
    _card("a2", "Alpha Two", 40.0, "Rare Holo"),
    _card("a3", "Alpha Three", 30.0, "Rare"),
    _card("a4", "Alpha Four", 20.0, "Rare"),
    _card("a5", "Alpha Five", 10.0, "Rare"),
    _card("a6", "Alpha Six", 5.0, "Rare"),
    _card("a7", "Alpha Seven", None, "Rare"),
    _card("a8", "Alpha Common", 3.0, "Common"),
    _card("a9", "Alpha Uncommon", 8.0, "Uncommon"),
]

BETA_CARDS = [
    _card("b1", "Beta One", None, "Rare Holo"),
    _card("b2", "Beta Two", None, "Common"),
]


class FakeStoreProvider:
    def __init__(self, sets=None, cards_by_set=None, error_set_ids=None):
        self.sets = sets if sets is not None else [SET_ALPHA, SET_BETA]
        self.cards_by_set = cards_by_set or {"set-a": ALPHA_CARDS, "set-b": BETA_CARDS}
        self.error_set_ids = error_set_ids or set()
        self.list_sets_call_count = 0
        self.get_set_cards_call_count = 0

    def list_sets(self, limit=12):
        self.list_sets_call_count += 1
        return self.sets

    def get_set_cards(self, set_id):
        self.get_set_cards_call_count += 1
        if set_id in self.error_set_ids:
            raise PriceProviderError(f"get_set_cards failed for {set_id!r}")
        return self.cards_by_set.get(set_id, [])


@pytest.fixture(autouse=True)
def _reset_store_cache():
    clear_store_cache()
    yield
    clear_store_cache()


def test_build_returns_one_booster_per_set_with_priced_cards():
    service = StoreService(FakeStoreProvider())
    boosters = service.build()
    assert [booster.set_id for booster in boosters] == ["set-a"]


def test_set_with_zero_priced_cards_is_skipped():
    service = StoreService(FakeStoreProvider())
    boosters = service.build()
    assert all(booster.set_id != "set-b" for booster in boosters)


def test_chase_cards_are_sorted_by_price_descending():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    prices = [card.price for card in booster.chase_cards]
    assert prices == sorted(prices, reverse=True)


def test_chase_cards_are_capped_at_five():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    assert len(booster.chase_cards) <= 5


def test_hit_pool_excludes_common_and_uncommon_cards():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    assert booster.hit_pool == 7


def test_good_count_only_includes_hit_pool_cards_at_or_above_threshold():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    assert booster.good_count == 4


def test_est_hit_pct_matches_good_over_hit_pool():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    assert booster.est_hit_pct == round(4 / 7 * 100, 1)


def test_one_in_matches_hit_pool_over_good():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    assert booster.one_in == round(7 / 4)


def test_top_chase_value_is_price_of_top_chase_card():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    assert booster.top_chase_value == 50.0


def test_buy_url_uses_tcgplayer_id_when_it_is_a_url():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    top_card = booster.chase_cards[0]
    assert top_card.buy_url == "https://tcgplayer.com/product/123"


def test_buy_url_falls_back_to_tcgplayer_search_for_non_url_id():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    second_card = booster.chase_cards[1]
    assert second_card.buy_url.startswith("https://www.tcgplayer.com/search/pokemon/product")


def test_booster_links_tcgplayer_contains_url_encoded_set_name():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    assert "Set+Alpha" in booster.booster_links["tcgplayer"]


def test_booster_links_ebay_contains_url_encoded_set_name():
    service = StoreService(FakeStoreProvider())
    booster = service.build()[0]
    assert "Set+Alpha" in booster.booster_links["ebay"]


def test_build_uses_cache_on_second_call():
    provider = FakeStoreProvider()
    service = StoreService(provider)
    service.build()
    service.build()
    assert provider.list_sets_call_count == 1


def test_clear_store_cache_forces_a_rebuild():
    provider = FakeStoreProvider()
    service = StoreService(provider)
    service.build()
    clear_store_cache()
    service.build()
    assert provider.list_sets_call_count == 2


def test_build_skips_leading_unpriced_sets_and_uses_later_priced_ones():
    provider = FakeStoreProvider(
        sets=[SET_GAMMA, SET_DELTA, SET_ALPHA, SET_BETA],
        cards_by_set={
            "set-g": [],
            "set-d": [_card("d1", "Delta One", None, "Rare Holo")],
            "set-a": ALPHA_CARDS,
            "set-b": BETA_CARDS,
        },
    )
    service = StoreService(provider)
    boosters = service.build()
    assert [booster.set_id for booster in boosters] == ["set-a"]


def test_build_skips_a_set_whose_get_set_cards_errors_but_returns_others():
    provider = FakeStoreProvider(
        sets=[SET_ERROR, SET_ALPHA],
        cards_by_set={"set-a": ALPHA_CARDS},
        error_set_ids={"set-e"},
    )
    service = StoreService(provider)
    boosters = service.build()
    assert [booster.set_id for booster in boosters] == ["set-a"]


def test_build_result_still_respects_featured_count_after_skipping_sets():
    provider = FakeStoreProvider(
        sets=[SET_GAMMA, SET_ALPHA, SET_BETA, SET_DELTA],
        cards_by_set={
            "set-g": [],
            "set-a": ALPHA_CARDS,
            "set-b": BETA_CARDS,
            "set-d": ALPHA_CARDS,
        },
    )
    service = StoreService(provider)
    boosters = service.build(featured=1)
    assert len(boosters) == 1


def test_build_does_not_cache_an_empty_result():
    provider = FakeStoreProvider(sets=[SET_GAMMA], cards_by_set={"set-g": []})
    service = StoreService(provider)
    boosters = service.build()
    assert boosters == []
    service.build()
    assert provider.list_sets_call_count == 2
