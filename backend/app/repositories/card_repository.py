from sqlmodel import Session, select

from app.models import Card


class CardRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, card: Card) -> Card:
        self.session.merge(card)
        self.session.commit()
        return card

    def get(self, card_id: str) -> Card | None:
        return self.session.get(Card, card_id)

    def list_ids(self) -> list[str]:
        return list(self.session.exec(select(Card.id)).all())
