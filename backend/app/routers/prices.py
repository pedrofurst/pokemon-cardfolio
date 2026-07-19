import logging

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_price_service
from app.errors import CardNotFoundError, PriceProviderError
from app.services.price_service import PriceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/refresh")
def refresh_prices(service: PriceService = Depends(get_price_service)) -> dict:
    try:
        written = service.refresh_prices()
    except CardNotFoundError as error:
        logger.warning("Card not found while refreshing prices: %s", error)
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PriceProviderError as error:
        logger.error("Price provider failed while refreshing prices: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"written": written}
