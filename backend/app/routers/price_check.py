from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.deps import get_price_check_service
from app.services.price_check_service import PriceCheckService

router = APIRouter(prefix="/price-check", tags=["price-check"])


class PriceCheckRequest(BaseModel):
    card_id: str
    offer_price: float = Field(ge=0)


@router.post("")
def check_price(
    body: PriceCheckRequest,
    service: PriceCheckService = Depends(get_price_check_service),
) -> dict:
    result = service.check(body.card_id, body.offer_price)
    return result.__dict__
