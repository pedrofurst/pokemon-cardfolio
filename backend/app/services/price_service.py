from app.errors import CardNotFoundError, PriceProviderError
from app.models import PriceSnapshot
from app.providers.base import CardResult, PriceProvider
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository


class PriceService:
    def __init__(self, card_repo: CardRepository, price_repo: PriceRepository,
                 provider: PriceProvider, holding_repo: HoldingRepository,
                 watch_repo: WatchRepository) -> None:
        self.card_repo = card_repo
        self.price_repo = price_repo
        self.provider = provider
        self.holding_repo = holding_repo
        self.watch_repo = watch_repo

    def search(self, query: str) -> list[CardResult]:
        return self.provider.search_cards(query)

    def refresh_prices(self, owner_id: str = "me") -> dict:
        card_ids = {h.card_id for h in self.holding_repo.list(owner_id)} | self.watch_repo.card_ids(owner_id)
        written = 0
        failed = 0
        for card_id in card_ids:
            # A scheduled batch refresh must not abort on one bad card: isolate
            # each card's failure so the rest of the batch still gets written.
            try:
                price = self.provider.get_price(card_id)
            except (PriceProviderError, CardNotFoundError):
                failed += 1
                continue
            self.price_repo.add(PriceSnapshot(
                card_id=card_id, source=price.source,
                market_price=price.market_price, currency=price.currency,
                low=price.low, mid=price.mid, high=price.high, direct_low=price.direct_low,
            ))
            written += 1
        return {"written": written, "failed": failed}
