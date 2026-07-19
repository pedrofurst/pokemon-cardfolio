from fastapi import APIRouter, Depends, Query

from app.deps import get_opportunity_service
from app.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("")
def get_opportunities(mover_pct: float = Query(10.0, gt=0),
                       deal_pct: float = Query(15.0, gt=0, le=100),
                       service: OpportunityService = Depends(get_opportunity_service)) -> dict:
    result = service.all(mover_pct=mover_pct, deal_pct=deal_pct)
    return {kind: [signal.__dict__ for signal in signals] for kind, signals in result.items()}
