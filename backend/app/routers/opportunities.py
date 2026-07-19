from fastapi import APIRouter, Depends

from app.deps import get_opportunity_service
from app.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("")
def get_opportunities(mover_pct: float = 10.0, deal_pct: float = 15.0,
                       service: OpportunityService = Depends(get_opportunity_service)) -> dict:
    result = service.all(mover_pct=mover_pct, deal_pct=deal_pct)
    return {kind: [signal.__dict__ for signal in signals] for kind, signals in result.items()}
