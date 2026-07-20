import time

import httpx

from app.errors import CardNotFoundError, PriceProviderError
from app.providers.query import build_search_query
from app.providers.base import CardResult, PriceResult, SetInfo

BASE_URL = "https://api.pokemontcg.io/v2"

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (0.6, 1.2)


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
) -> httpx.Response:
    """GET with a small retry-with-backoff for transient upstream failures.

    Retries on a 429/5xx status or a transport-level error (connect/read
    timeout). Any other 4xx status is returned immediately without retry.
    """
    last_transport_error: httpx.TransportError | None = None
    last_bad_response: httpx.Response | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = client.get(url, params=params, headers=headers)
        except httpx.TransportError as error:
            last_transport_error = error
        else:
            if not _is_retryable_status(response.status_code):
                return response
            last_bad_response = response

        is_last_attempt = attempt == _MAX_ATTEMPTS - 1
        if not is_last_attempt:
            time.sleep(_RETRY_BACKOFF_SECONDS[attempt])

    if last_transport_error is not None:
        raise last_transport_error
    assert last_bad_response is not None
    return last_bad_response


def _extract_market_price(card: dict) -> float | None:
    prices = (card.get("tcgplayer") or {}).get("prices") or {}
    for variant in prices.values():
        market = variant.get("market")
        if market is not None:
            return float(market)
    return None


def _extract_prices(card: dict) -> dict:
    prices = (card.get("tcgplayer") or {}).get("prices") or {}
    for variant in prices.values():
        market = variant.get("market")
        if market is not None:
            return {
                "market": float(market),
                "low": _to_optional_float(variant.get("low")),
                "mid": _to_optional_float(variant.get("mid")),
                "high": _to_optional_float(variant.get("high")),
                "direct_low": _to_optional_float(variant.get("directLow")),
            }
    return {"market": None, "low": None, "mid": None, "high": None, "direct_low": None}


def _to_optional_float(value: float | int | None) -> float | None:
    return float(value) if value is not None else None


def _to_set_info(set_data: dict) -> SetInfo:
    return SetInfo(
        id=set_data.get("id", ""),
        name=set_data.get("name", ""),
        series=set_data.get("series", ""),
        total=set_data.get("total"),
        release_date=set_data.get("releaseDate", ""),
        logo_url=(set_data.get("images") or {}).get("logo", ""),
    )


def _to_card_result(card: dict) -> CardResult:
    set_info = card.get("set") or {}
    return CardResult(
        id=card["id"],
        name=card.get("name", ""),
        set_name=set_info.get("name", ""),
        number=card.get("number", ""),
        rarity=card.get("rarity", ""),
        image_url=(card.get("images") or {}).get("small", ""),
        tcgplayer_id=(card.get("tcgplayer") or {}).get("url"),
        market_price=_extract_market_price(card),
        set_id=set_info.get("id", ""),
        set_total=set_info.get("total") or set_info.get("printedTotal"),
    )


class PokemonTcgIoProvider:
    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=10.0)
        self._headers = {"X-Api-Key": api_key} if api_key else {}

    def search_cards(self, query: str) -> list[CardResult]:
        try:
            response = _get_with_retry(
                self._client,
                f"{BASE_URL}/cards",
                params={"q": build_search_query(query), "pageSize": 20},
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
            response = _get_with_retry(
                self._client, f"{BASE_URL}/cards/{card_id}", headers=self._headers
            )
            if response.status_code == 404:
                raise CardNotFoundError(card_id)
            response.raise_for_status()
            card = response.json().get("data", {})
        except httpx.HTTPError as error:
            raise PriceProviderError(f"price fetch failed for {card_id!r}") from error
        except ValueError as error:
            raise PriceProviderError(f"price fetch failed for {card_id!r}") from error
        prices = _extract_prices(card)
        if prices["market"] is None:
            raise PriceProviderError(f"no market price for {card_id!r}")
        return PriceResult(
            card_id=card_id, market_price=prices["market"], currency="USD", source="tcgplayer",
            low=prices["low"], mid=prices["mid"], high=prices["high"], direct_low=prices["direct_low"],
        )

    def list_sets(self, limit: int = 12) -> list[SetInfo]:
        try:
            response = _get_with_retry(
                self._client,
                f"{BASE_URL}/sets",
                params={"orderBy": "-releaseDate", "pageSize": limit},
                headers=self._headers,
            )
            response.raise_for_status()
            sets = response.json().get("data", [])
        except httpx.HTTPError as error:
            raise PriceProviderError("list_sets failed") from error
        except ValueError as error:
            raise PriceProviderError("list_sets failed") from error
        return [_to_set_info(set_data) for set_data in sets]

    def get_set_cards(self, set_id: str) -> list[CardResult]:
        try:
            response = _get_with_retry(
                self._client,
                f"{BASE_URL}/cards",
                params={"q": f"set.id:{set_id}", "pageSize": 250},
                headers=self._headers,
            )
            response.raise_for_status()
            cards = response.json().get("data", [])
        except httpx.HTTPError as error:
            raise PriceProviderError(f"get_set_cards failed for {set_id!r}") from error
        except ValueError as error:
            raise PriceProviderError(f"get_set_cards failed for {set_id!r}") from error
        return [_to_card_result(card) for card in cards]
