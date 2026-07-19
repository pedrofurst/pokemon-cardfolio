import httpx

from app.errors import PriceProviderError

BASE_URL = "https://open.er-api.com/v6/latest/USD"


class FxProvider:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=10.0)

    def get_usd_brl(self) -> float:
        try:
            response = self._client.get(BASE_URL)
            response.raise_for_status()
            data = response.json()
            return float(data["rates"]["BRL"])
        except httpx.HTTPError as error:
            raise PriceProviderError("FX fetch failed") from error
        except (ValueError, KeyError, TypeError) as error:
            raise PriceProviderError("FX fetch failed") from error
