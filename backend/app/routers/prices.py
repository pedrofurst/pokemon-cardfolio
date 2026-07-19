import logging

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_collection_service, get_portfolio_repository, get_price_service
from app.errors import CardNotFoundError, PriceProviderError
from app.repositories.portfolio_repository import PortfolioRepository
from app.services.collection_service import CollectionService
from app.services.price_service import PriceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/refresh")
def refresh_prices(price_service: PriceService = Depends(get_price_service),
                    collection_service: CollectionService = Depends(get_collection_service)) -> dict:
    try:
        result = price_service.refresh_prices()
    except CardNotFoundError as error:
        logger.warning("Card not found while refreshing prices: %s", error)
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PriceProviderError as error:
        logger.error("Price provider failed while refreshing prices: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    collection_service.record_portfolio_snapshot()
    return result


@router.get("/status")
def get_price_status(portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository)) -> dict:
    latest = portfolio_repo.latest("me")
    return {"last_refresh": latest.fetched_at.isoformat() if latest else None}
