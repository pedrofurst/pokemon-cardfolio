from app.repositories.portfolio_repository import PortfolioRepository
from app.services.collection_service import CollectionService, HoldingView
from app.services.opportunity_service import OpportunityService
from app.services.sale_service import SaleService


class DigestService:
    def __init__(self, collection_service: CollectionService, opportunity_service: OpportunityService,
                 sale_service: SaleService, portfolio_repo: PortfolioRepository) -> None:
        self.collection_service = collection_service
        self.opportunity_service = opportunity_service
        self.sale_service = sale_service
        self.portfolio_repo = portfolio_repo

    def build(self, owner_id: str = "me") -> dict:
        views = self.collection_service.list_collection(owner_id)
        summary = self.collection_service.summarize(views)
        top_gainer = self._to_highlight(max(views, key=lambda view: view.pnl)) if views else None
        top_loser = self._to_highlight(min(views, key=lambda view: view.pnl)) if views else None

        opportunities = self.opportunity_service.all(owner_id)
        realized = self.sale_service.realized_summary(owner_id)
        latest_snapshot = self.portfolio_repo.latest(owner_id)

        return {
            "summary": summary.__dict__,
            "realized": realized.__dict__,
            "top_gainer": top_gainer,
            "top_loser": top_loser,
            "movers": [signal.__dict__ for signal in opportunities["movers"][:3]],
            "deals": [signal.__dict__ for signal in opportunities["deals"][:3]],
            "target_hits": [signal.__dict__ for signal in opportunities["target_hits"][:3]],
            "last_refresh": latest_snapshot.fetched_at.isoformat() if latest_snapshot else None,
        }

    @staticmethod
    def _to_highlight(view: HoldingView) -> dict:
        return {
            "card_id": view.holding.card_id,
            "card_name": view.card.name if view.card else view.holding.card_id,
            "image_url": view.card.image_url if view.card else None,
            "pnl": view.pnl,
            "current_price": view.current_price,
        }
