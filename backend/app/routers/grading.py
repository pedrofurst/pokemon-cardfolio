from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_session
from app.deps import get_grading_service
from app.repositories.price_repository import PriceRepository
from app.services.grading_service import GradingInput, GradingService

router = APIRouter(prefix="/grading", tags=["grading"])


class GradingRequest(BaseModel):
    card_id: str | None = None
    raw_price: float | None = None
    psa10_price: float | None = None
    psa9_price: float | None = None
    grading_cost: float = Field(25.0, ge=0)
    selling_fees_pct: float = Field(13.0, ge=0, lt=100)
    prob_psa10: float = Field(0.5, ge=0, le=1)


@router.post("/evaluate")
def evaluate_grading(
    body: GradingRequest,
    service: GradingService = Depends(get_grading_service),
    session: Session = Depends(get_session),
) -> dict:
    raw = body.raw_price
    if raw is None and body.card_id:
        snapshot = PriceRepository(session).latest_for(body.card_id)
        raw = snapshot.market_price if snapshot else None

    if raw is None:
        raise HTTPException(
            status_code=400, detail="raw_price required (or a card_id with a stored price)",
        )

    result = service.evaluate(
        GradingInput(
            raw_price=raw,
            psa10_price=body.psa10_price,
            psa9_price=body.psa9_price,
            grading_cost=body.grading_cost,
            selling_fees_pct=body.selling_fees_pct,
            prob_psa10=body.prob_psa10,
        ),
    )
    return result.__dict__
