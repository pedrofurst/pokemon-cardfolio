from fastapi import APIRouter, Depends

from app.deps import get_price_service
from app.services.price_service import PriceService

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/search")
def search_cards(q: str, service: PriceService = Depends(get_price_service)) -> list[dict]:
    return [result.__dict__ for result in service.search(q)]
