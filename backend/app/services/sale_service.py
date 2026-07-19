from dataclasses import dataclass

from app.models import Card, Sale
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.sale_repository import SaleRepository


@dataclass
class RealizedSummary:
    total_proceeds: float
    total_cost: float
    realized_pnl: float
    sales_count: int


class SaleService:
    def __init__(self, holding_repo: HoldingRepository, sale_repo: SaleRepository,
                 card_repo: CardRepository) -> None:
        self.holding_repo = holding_repo
        self.sale_repo = sale_repo
        self.card_repo = card_repo

    def record_sale(self, holding_id: str, quantity: int, sale_price: float,
                     fee: float = 0.0, owner_id: str = "me") -> Sale:
        holding = self.holding_repo.get(holding_id)
        if holding is None or holding.owner_id != owner_id:
            raise ValueError("holding not found")
        if not (1 <= quantity <= holding.quantity):
            raise ValueError("invalid quantity")

        card_id = holding.card_id
        cost_basis = holding.acquisition_cost

        holding.quantity -= quantity
        if holding.quantity == 0:
            self.holding_repo.delete(holding.id)
        else:
            self.holding_repo.update(holding)

        # Create (and commit/refresh) the Sale last so it isn't left expired
        # by the holding's own commit above (SQLAlchemy expires all
        # in-session instances on commit by default).
        return self.sale_repo.add(Sale(
            card_id=card_id, owner_id=owner_id, quantity=quantity,
            sale_price=sale_price, fee=fee, cost_basis=cost_basis,
        ))

    def realized_summary(self, owner_id: str = "me") -> RealizedSummary:
        sales = self.sale_repo.list(owner_id)
        total_proceeds = sum(sale.sale_price * sale.quantity - sale.fee for sale in sales)
        total_cost = sum(sale.cost_basis * sale.quantity for sale in sales)
        realized_pnl = total_proceeds - total_cost
        return RealizedSummary(
            total_proceeds=total_proceeds, total_cost=total_cost,
            realized_pnl=realized_pnl, sales_count=len(sales),
        )

    def history(self, owner_id: str = "me") -> list[tuple[Sale, Card | None]]:
        return [(sale, self.card_repo.get(sale.card_id)) for sale in self.sale_repo.list(owner_id)]
