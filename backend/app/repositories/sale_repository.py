from sqlmodel import Session, select

from app.models import Sale


class SaleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, sale: Sale) -> Sale:
        self.session.add(sale)
        self.session.commit()
        self.session.refresh(sale)
        return sale

    def list(self, owner_id: str) -> list[Sale]:
        statement = (
            select(Sale)
            .where(Sale.owner_id == owner_id)
            .order_by(Sale.sold_at.desc(), Sale.id.desc())
        )
        return list(self.session.exec(statement).all())
