from sqlmodel import Session, select

from app.models import Holding


class HoldingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, holding: Holding) -> Holding:
        self.session.add(holding)
        self.session.commit()
        self.session.refresh(holding)
        return holding

    def list(self, owner_id: str) -> list[Holding]:
        statement = select(Holding).where(Holding.owner_id == owner_id)
        return list(self.session.exec(statement).all())
