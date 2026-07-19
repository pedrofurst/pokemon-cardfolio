from dataclasses import dataclass
from typing import Protocol


@dataclass
class CardResult:
    id: str
    name: str
    set_name: str
    number: str
    rarity: str
    image_url: str
    tcgplayer_id: str | None
    market_price: float | None


@dataclass
class PriceResult:
    card_id: str
    market_price: float
    currency: str
    source: str


class PriceProvider(Protocol):
    def search_cards(self, query: str) -> list[CardResult]: ...
    def get_price(self, card_id: str) -> PriceResult: ...
