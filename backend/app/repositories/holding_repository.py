from datetime import datetime, timezone

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

    def list(self, owner_id: str, archived: bool = False) -> list[Holding]:
        statement = select(Holding).where(Holding.owner_id == owner_id)
        if archived:
            statement = statement.where(Holding.archived_at.is_not(None))
        else:
            statement = statement.where(Holding.archived_at.is_(None))
        return list(self.session.exec(statement).all())

    def set_archived(self, holding_id: str, archived: bool) -> Holding | None:
        holding = self.session.get(Holding, holding_id)
        if holding is None:
            return None
        holding.archived_at = datetime.now(timezone.utc) if archived else None
        self.session.add(holding)
        self.session.commit()
        self.session.refresh(holding)
        return holding

    def get(self, holding_id: str) -> Holding | None:
        return self.session.get(Holding, holding_id)

    def update(self, holding: Holding) -> Holding:
        self.session.add(holding)
        self.session.commit()
        self.session.refresh(holding)
        return holding

    def delete(self, holding_id: str) -> bool:
        holding = self.session.get(Holding, holding_id)
        if holding is None:
            return False
        self.session.delete(holding)
        self.session.commit()
        return True
