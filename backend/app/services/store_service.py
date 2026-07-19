import time
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from app.errors import PriceProviderError
from app.providers.base import CardResult, SetInfo, StoreProvider

HIT_THRESHOLD_USD = 15.0
_NON_HIT_RARITIES = {"", "Common", "Uncommon"}
_CACHE_TTL_SECONDS = 21600.0
_SETS_WINDOW = 40
MAX_SETS_SCANNED = 25

_cache: dict[int, tuple[float, list["Booster"]]] = {}


@dataclass
class ChaseCard:
    id: str
    name: str
    image_url: str
    price: float | None
    rarity: str
    buy_url: str


@dataclass
class Booster:
    set_id: str
    set_name: str
    series: str
    release_date: str
    logo_url: str
    total: int | None
    chase_cards: list[ChaseCard] = field(default_factory=list)
    good_count: int = 0
    hit_pool: int = 0
    est_hit_pct: float | None = None
    one_in: int | None = None
    top_chase_value: float | None = None
    booster_links: dict[str, str] = field(default_factory=dict)


def clear_store_cache() -> None:
    _cache.clear()


def _is_hit_slot_rarity(rarity: str) -> bool:
    return (rarity or "") not in _NON_HIT_RARITIES


def _tcgplayer_search(query: str) -> str:
    return (
        "https://www.tcgplayer.com/search/pokemon/product"
        f"?productLineName=pokemon&q={quote_plus(query)}"
    )


def _ebay_search(query: str) -> str:
    return f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}"


def _buy_url_for(card: CardResult) -> str:
    if card.tcgplayer_id and card.tcgplayer_id.startswith("http"):
        return card.tcgplayer_id
    return _tcgplayer_search(card.name)


def _to_chase_card(card: CardResult) -> ChaseCard:
    return ChaseCard(
        id=card.id, name=card.name, image_url=card.image_url,
        price=card.market_price, rarity=card.rarity, buy_url=_buy_url_for(card),
    )


class StoreService:
    def __init__(self, provider: StoreProvider) -> None:
        self.provider = provider

    def build(self, featured: int = 6) -> list[Booster]:
        cached = _cache.get(featured)
        if cached is not None:
            expires_at, boosters = cached
            if time.monotonic() < expires_at:
                return boosters

        boosters = self._build_boosters(featured)
        if boosters:
            # Only cache a successful, non-empty result. An empty result usually
            # means the scan window landed on unpriced sets or hit per-set errors;
            # caching that for 6h would keep the store empty until the TTL expires.
            _cache[featured] = (time.monotonic() + _CACHE_TTL_SECONDS, boosters)
        return boosters

    def _build_boosters(self, featured: int) -> list[Booster]:
        sets = self.provider.list_sets(limit=_SETS_WINDOW)
        boosters: list[Booster] = []
        scanned = 0
        for set_info in sets:
            if len(boosters) >= featured:
                break
            if scanned >= MAX_SETS_SCANNED:
                break
            scanned += 1
            booster = self._build_booster(set_info)
            if booster is not None:
                boosters.append(booster)
        return boosters

    def _build_booster(self, set_info: SetInfo) -> Booster | None:
        try:
            # Batch aggregation must tolerate per-set upstream failures — a
            # transient rate-limit/502 on one set must not abort the whole
            # store (same resilience pattern as PriceService.refresh_prices).
            cards = self.provider.get_set_cards(set_info.id)
        except PriceProviderError:
            return None
        priced = [card for card in cards if card.market_price is not None]
        if len(priced) == 0:
            return None

        chase = sorted(priced, key=lambda card: card.market_price, reverse=True)[:5]
        chase_cards = [_to_chase_card(card) for card in chase]

        hit_pool_cards = [card for card in cards if _is_hit_slot_rarity(card.rarity)]
        good_cards = [
            card for card in hit_pool_cards if (card.market_price or 0) >= HIT_THRESHOLD_USD
        ]

        hit_pool = len(hit_pool_cards)
        good_count = len(good_cards)
        est_hit_pct = round(good_count / hit_pool * 100, 1) if hit_pool else None
        one_in = round(hit_pool / good_count) if good_count else None

        return Booster(
            set_id=set_info.id,
            set_name=set_info.name,
            series=set_info.series,
            release_date=set_info.release_date,
            logo_url=set_info.logo_url,
            total=set_info.total,
            chase_cards=chase_cards,
            good_count=good_count,
            hit_pool=hit_pool,
            est_hit_pct=est_hit_pct,
            one_in=one_in,
            top_chase_value=chase_cards[0].price if chase_cards else None,
            booster_links={
                "tcgplayer": _tcgplayer_search(f"{set_info.name} booster"),
                "ebay": _ebay_search(f"{set_info.name} booster box"),
            },
        )
