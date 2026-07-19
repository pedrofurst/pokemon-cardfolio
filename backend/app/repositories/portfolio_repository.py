from sqlmodel import Session, select

from app.models import PortfolioSnapshot


class PortfolioRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def history(self, owner_id: str) -> list[PortfolioSnapshot]:
        statement = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.owner_id == owner_id)
            .order_by(PortfolioSnapshot.fetched_at.asc(), PortfolioSnapshot.id.asc())
        )
        return list(self.session.exec(statement).all())

    def latest(self, owner_id: str) -> PortfolioSnapshot | None:
        statement = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.owner_id == owner_id)
            .order_by(PortfolioSnapshot.fetched_at.desc(), PortfolioSnapshot.id.desc())
        )
        return self.session.exec(statement).first()
