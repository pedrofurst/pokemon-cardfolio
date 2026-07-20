from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_collection_service
from app.providers.base import CardResult
from app.routers.schemas import CardPayload
from app.services.collection_service import CollectionService

router = APIRouter(prefix="/holdings", tags=["holdings"])


class AddHoldingRequest(BaseModel):
    card: CardPayload
    condition: str = "raw"
    is_graded: bool = False
    acquisition_cost: float = 0.0
    quantity: int = 1
    notes: str = ""
    variant: str = "normal"


@router.post("")
def add_holding(body: AddHoldingRequest,
                service: CollectionService = Depends(get_collection_service)) -> dict:
    result = CardResult(**body.card.model_dump())
    holding = service.add_holding_from_result(
        result, condition=body.condition, is_graded=body.is_graded,
        acquisition_cost=body.acquisition_cost, quantity=body.quantity, notes=body.notes,
        variant=body.variant,
    )
    return holding.model_dump()


@router.get("")
def list_holdings(archived: bool = False,
                  service: CollectionService = Depends(get_collection_service)) -> dict:
    views = service.list_collection(archived=archived)
    summary = service.summarize(views)
    return {
        "summary": summary.__dict__,
        "items": [
            {
                "holding": v.holding.model_dump(),
                "card": v.card.model_dump() if v.card else None,
                "current_price": v.current_price,
                "pnl": v.pnl,
            }
            for v in views
        ],
    }


@router.patch("/{holding_id}/archive")
def archive_holding(holding_id: str,
                    service: CollectionService = Depends(get_collection_service)) -> dict:
    return service.archive_holding(holding_id).model_dump()


@router.patch("/{holding_id}/restore")
def restore_holding(holding_id: str,
                    service: CollectionService = Depends(get_collection_service)) -> dict:
    return service.restore_holding(holding_id).model_dump()
