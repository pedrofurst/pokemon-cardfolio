from dataclasses import dataclass

from app.errors import CardNotFoundError, PriceProviderError
from app.providers.base import PriceProvider
from app.repositories.price_repository import PriceRepository


@dataclass
class PriceCheckResult:
    card_id: str
    offer: float
    market: float
    low: float | None
    direct_low: float | None
    verdict: str
    delta_pct: float
    detail: str


class PriceCheckService:
    def __init__(self, provider: PriceProvider, price_repo: PriceRepository) -> None:
        self.provider = provider
        self.price_repo = price_repo

    def check(self, card_id: str, offer_price: float) -> PriceCheckResult:
        market, low, direct_low = self._resolve_price(card_id)
        if market <= 0:
            raise PriceProviderError(f"No usable market price for card {card_id}")

        delta_pct = (offer_price - market) / market * 100.0
        verdict = self._verdict_for(offer_price, market, direct_low, delta_pct)
        detail = self._detail_for(verdict, market, delta_pct)

        return PriceCheckResult(
            card_id=card_id, offer=offer_price, market=market, low=low,
            direct_low=direct_low, verdict=verdict, delta_pct=delta_pct, detail=detail,
        )

    def _resolve_price(self, card_id: str) -> tuple[float, float | None, float | None]:
        try:
            price = self.provider.get_price(card_id)
        except (PriceProviderError, CardNotFoundError):
            snapshot = self.price_repo.latest_for(card_id)
            if snapshot is None:
                raise
            return snapshot.market_price, snapshot.low, snapshot.direct_low
        return price.market_price, price.low, price.direct_low

    def _verdict_for(self, offer_price: float, market: float,
                      direct_low: float | None, delta_pct: float) -> str:
        floor = direct_low if direct_low is not None else market
        if offer_price <= floor * 0.9 or delta_pct <= -15:
            return "great_deal"
        if abs(delta_pct) <= 10:
            return "fair"
        if delta_pct >= 15:
            return "overpriced"
        if delta_pct > 0:
            return "slightly_high"
        return "slightly_low"

    def _detail_for(self, verdict: str, market: float, delta_pct: float) -> str:
        direction = "above" if delta_pct > 0 else "below"
        base = f"Offer is {abs(delta_pct):.0f}% {direction} the ${market:.2f} market."
        if verdict == "great_deal":
            return f"Great deal — {base}"
        if verdict == "overpriced":
            return f"Overpriced — {base}"
        return base
