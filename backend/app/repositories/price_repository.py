from sqlmodel import Session, select

from app.models import PriceSnapshot


class PriceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, snapshot: PriceSnapshot) -> PriceSnapshot:
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def latest_for(self, card_id: str) -> PriceSnapshot | None:
        statement = (
            select(PriceSnapshot)
            .where(PriceSnapshot.card_id == card_id)
            .order_by(PriceSnapshot.fetched_at.desc())
        )
        return self.session.exec(statement).first()

    def history(self, card_id: str) -> list[PriceSnapshot]:
        statement = (
            select(PriceSnapshot)
            .where(PriceSnapshot.card_id == card_id)
            .order_by(PriceSnapshot.fetched_at.asc())
        )
        return list(self.session.exec(statement).all())
