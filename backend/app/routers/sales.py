import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import get_sale_service
from app.services.sale_service import SaleService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales"])


class SellRequest(BaseModel):
    quantity: int = Field(ge=1)
    sale_price: float = Field(ge=0)
    fee: float = Field(0, ge=0)


@router.post("/holdings/{holding_id}/sell")
def sell_holding(holding_id: str, body: SellRequest,
                  service: SaleService = Depends(get_sale_service)) -> dict:
    try:
        sale = service.record_sale(
            holding_id, quantity=body.quantity, sale_price=body.sale_price, fee=body.fee,
        )
    except ValueError as error:
        logger.warning("Failed to record sale for holding %s: %s", holding_id, error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    return sale.model_dump()


@router.get("/sales")
def list_sales(service: SaleService = Depends(get_sale_service)) -> dict:
    summary = service.realized_summary()
    return {
        "summary": summary.__dict__,
        "items": [
            {"sale": sale.model_dump(), "card": card.model_dump() if card else None}
            for sale, card in service.history()
        ],
    }
