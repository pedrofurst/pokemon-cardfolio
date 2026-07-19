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

        # holding_repo and sale_repo are constructed from the same SQLModel
        # Session (see deps.py and the `session` test fixture). We bypass
        # their individual add/update/delete methods here and operate on the
        # shared session directly so the holding mutation and the new Sale
        # row commit together in a single transaction: either both persist
        # or, if the commit fails, neither does. Two separate commits (one
        # per repo call) would risk reducing/deleting the holding while the
        # Sale row silently fails to be written.
        session = self.sale_repo.session

        sale = Sale(
            card_id=card_id, owner_id=owner_id, quantity=quantity,
            sale_price=sale_price, fee=fee, cost_basis=cost_basis,
        )
        session.add(sale)

        holding.quantity -= quantity
        if holding.quantity == 0:
            session.delete(holding)
        else:
            session.add(holding)

        session.commit()
        session.refresh(sale)
        return sale

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
