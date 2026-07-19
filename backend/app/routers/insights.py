from fastapi import APIRouter, Depends

from app.deps import get_insights_service
from app.services.insights_service import InsightsService

router = APIRouter(tags=["insights"])


@router.get("/insights")
def get_insights(service: InsightsService = Depends(get_insights_service)) -> dict:
    return service.build()
