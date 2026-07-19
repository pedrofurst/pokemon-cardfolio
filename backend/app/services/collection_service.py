from dataclasses import dataclass

from app.models import Card, Holding, PortfolioSnapshot, PriceSnapshot
from app.providers.base import CardResult
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.price_repository import PriceRepository


@dataclass
class HoldingView:
    holding: Holding
    card: Card | None
    current_price: float | None
    pnl: float


@dataclass
class CollectionSummary:
    total_cost: float
    total_value: float
    pnl: float
    pnl_pct: float


class CollectionService:
    def __init__(self, card_repo: CardRepository, holding_repo: HoldingRepository,
                 price_repo: PriceRepository, portfolio_repo: PortfolioRepository) -> None:
        self.card_repo = card_repo
        self.holding_repo = holding_repo
        self.price_repo = price_repo
        self.portfolio_repo = portfolio_repo

    def add_holding_from_result(self, result: CardResult, condition: str, is_graded: bool,
                                acquisition_cost: float, quantity: int, notes: str,
                                owner_id: str = "me") -> Holding:
        self.card_repo.upsert(Card(
            id=result.id, name=result.name, set_name=result.set_name,
            number=result.number, rarity=result.rarity, image_url=result.image_url,
            tcgplayer_id=result.tcgplayer_id,
        ))
        holding = self.holding_repo.add(Holding(
            card_id=result.id, owner_id=owner_id, condition=condition,
            is_graded=is_graded, acquisition_cost=acquisition_cost,
            quantity=quantity, notes=notes,
        ))
        if result.market_price is not None:
            self.price_repo.add(PriceSnapshot(
                card_id=result.id, source="tcgplayer",
                market_price=result.market_price, currency="USD",
            ))
        return holding

    def list_collection(self, owner_id: str = "me") -> list[HoldingView]:
        views: list[HoldingView] = []
        for holding in self.holding_repo.list(owner_id):
            latest = self.price_repo.latest_for(holding.card_id)
            current = latest.market_price if latest else None
            value = (current or 0.0) * holding.quantity
            pnl = value - holding.acquisition_cost * holding.quantity
            views.append(HoldingView(
                holding=holding, card=self.card_repo.get(holding.card_id),
                current_price=current, pnl=pnl,
            ))
        return views

    def summarize(self, views: list[HoldingView]) -> CollectionSummary:
        total_cost = sum(v.holding.acquisition_cost * v.holding.quantity for v in views)
        total_value = sum((v.current_price or 0.0) * v.holding.quantity for v in views)
        pnl = total_value - total_cost
        pnl_pct = (pnl / total_cost * 100.0) if total_cost else 0.0
        return CollectionSummary(total_cost, total_value, pnl, pnl_pct)

    def summary(self, owner_id: str = "me") -> CollectionSummary:
        return self.summarize(self.list_collection(owner_id))

    def record_portfolio_snapshot(self, owner_id: str = "me") -> PortfolioSnapshot:
        summary = self.summary(owner_id)
        return self.portfolio_repo.add(PortfolioSnapshot(
            owner_id=owner_id, total_cost=summary.total_cost,
            total_value=summary.total_value, pnl=summary.pnl,
        ))
