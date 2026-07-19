from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_price_service
from app.errors import CardNotFoundError, PriceProviderError
from app.services.price_service import PriceService

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/refresh")
def refresh_prices(service: PriceService = Depends(get_price_service)) -> dict:
    try:
        written = service.refresh_prices()
    except CardNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PriceProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"written": written}
