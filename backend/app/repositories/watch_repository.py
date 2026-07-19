from sqlmodel import Session, select

from app.models import WatchItem


class WatchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, item: WatchItem) -> WatchItem:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list(self, owner_id: str) -> list[WatchItem]:
        statement = select(WatchItem).where(WatchItem.owner_id == owner_id)
        return list(self.session.exec(statement).all())

    def get(self, item_id: str) -> WatchItem | None:
        return self.session.get(WatchItem, item_id)

    def delete(self, item_id: str) -> bool:
        item = self.session.get(WatchItem, item_id)
        if item is None:
            return False
        self.session.delete(item)
        self.session.commit()
        return True

    def card_ids(self, owner_id: str) -> set[str]:
        return {item.card_id for item in self.list(owner_id)}
