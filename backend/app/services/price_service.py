from app.models import PriceSnapshot
from app.providers.base import CardResult, PriceProvider
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository


class PriceService:
    def __init__(self, card_repo: CardRepository, price_repo: PriceRepository,
                 provider: PriceProvider, holding_repo: HoldingRepository) -> None:
        self.card_repo = card_repo
        self.price_repo = price_repo
        self.provider = provider
        self.holding_repo = holding_repo

    def search(self, query: str) -> list[CardResult]:
        return self.provider.search_cards(query)

    def refresh_prices(self, owner_id: str = "me") -> int:
        card_ids = {h.card_id for h in self.holding_repo.list(owner_id)}
        written = 0
        for card_id in card_ids:
            price = self.provider.get_price(card_id)
            self.price_repo.add(PriceSnapshot(
                card_id=card_id, source=price.source,
                market_price=price.market_price, currency=price.currency,
            ))
            written += 1
        return written
