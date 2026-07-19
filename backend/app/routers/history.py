from fastapi import APIRouter, Depends

from app.deps import get_portfolio_repository, get_price_repository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.price_repository import PriceRepository

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/portfolio")
def get_portfolio_history(
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
) -> list[dict]:
    return [
        {
            "fetched_at": snapshot.fetched_at.isoformat(),
            "total_value": snapshot.total_value,
            "total_cost": snapshot.total_cost,
            "pnl": snapshot.pnl,
        }
        for snapshot in portfolio_repo.history("me")
    ]


@router.get("/card/{card_id}")
def get_card_history(
    card_id: str, price_repo: PriceRepository = Depends(get_price_repository),
) -> list[dict]:
    return [
        {"fetched_at": snapshot.fetched_at.isoformat(), "market_price": snapshot.market_price}
        for snapshot in price_repo.history(card_id)
    ]
