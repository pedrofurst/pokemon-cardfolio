import httpx

from app.errors import CardNotFoundError, PriceProviderError
from app.providers.base import CardResult, PriceResult

BASE_URL = "https://api.pokemontcg.io/v2"


def _extract_market_price(card: dict) -> float | None:
    prices = (card.get("tcgplayer") or {}).get("prices") or {}
    for variant in prices.values():
        market = variant.get("market")
        if market is not None:
            return float(market)
    return None


def _to_card_result(card: dict) -> CardResult:
    return CardResult(
        id=card["id"],
        name=card.get("name", ""),
        set_name=(card.get("set") or {}).get("name", ""),
        number=card.get("number", ""),
        rarity=card.get("rarity", ""),
        image_url=(card.get("images") or {}).get("small", ""),
        tcgplayer_id=(card.get("tcgplayer") or {}).get("url"),
        market_price=_extract_market_price(card),
    )


class PokemonTcgIoProvider:
    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=10.0)
        self._headers = {"X-Api-Key": api_key} if api_key else {}

    def search_cards(self, query: str) -> list[CardResult]:
        try:
            response = self._client.get(
                f"{BASE_URL}/cards",
                params={"q": f'name:"{query}*"', "pageSize": 20},
                headers=self._headers,
            )
            response.raise_for_status()
            cards = response.json().get("data", [])
        except httpx.HTTPError as error:
            raise PriceProviderError(f"search failed for {query!r}") from error
        except ValueError as error:
            raise PriceProviderError(f"search failed for {query!r}") from error
        return [_to_card_result(card) for card in cards]

    def get_price(self, card_id: str) -> PriceResult:
        try:
            response = self._client.get(
                f"{BASE_URL}/cards/{card_id}", headers=self._headers
            )
            if response.status_code == 404:
                raise CardNotFoundError(card_id)
            response.raise_for_status()
            card = response.json().get("data", {})
        except httpx.HTTPError as error:
            raise PriceProviderError(f"price fetch failed for {card_id!r}") from error
        except ValueError as error:
            raise PriceProviderError(f"price fetch failed for {card_id!r}") from error
        price = _extract_market_price(card)
        if price is None:
            raise PriceProviderError(f"no market price for {card_id!r}")
        return PriceResult(card_id=card_id, market_price=price, currency="USD", source="tcgplayer")
