from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_opportunity_service
from app.providers.base import CardResult
from app.routers.schemas import CardPayload
from app.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class AddWatchRequest(BaseModel):
    card: CardPayload
    target_price: float | None = None


@router.post("")
def add_watch(body: AddWatchRequest,
              service: OpportunityService = Depends(get_opportunity_service)) -> dict:
    result = CardResult(**body.card.model_dump())
    watch_item = service.add_watch(result, body.target_price)
    return watch_item.model_dump()


@router.get("")
def list_watch(service: OpportunityService = Depends(get_opportunity_service)) -> list[dict]:
    return [
        {"item": item.model_dump(), "card": card.model_dump() if card else None}
        for item, card in service.list_watch()
    ]


@router.delete("/{item_id}")
def remove_watch(item_id: str,
                  service: OpportunityService = Depends(get_opportunity_service)) -> dict:
    return {"deleted": service.remove_watch(item_id)}
