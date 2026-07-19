from dataclasses import dataclass

from app.models import Card, WatchItem
from app.providers.base import CardResult
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository


@dataclass
class Signal:
    kind: str  # "mover" | "deal" | "target"
    card_id: str
    card_name: str
    detail: str
    current_price: float | None
    reference_price: float | None
    change_pct: float | None


class OpportunityService:
    def __init__(self, card_repo: CardRepository, price_repo: PriceRepository,
                 holding_repo: HoldingRepository, watch_repo: WatchRepository) -> None:
        self.card_repo = card_repo
        self.price_repo = price_repo
        self.holding_repo = holding_repo
        self.watch_repo = watch_repo

    def _relevant_card_ids(self, owner_id: str) -> set[str]:
        holding_card_ids = {holding.card_id for holding in self.holding_repo.list(owner_id)}
        return holding_card_ids | self.watch_repo.card_ids(owner_id)

    def _card_name(self, card_id: str) -> str:
        card = self.card_repo.get(card_id)
        return card.name if card is not None else card_id

    def movers(self, owner_id: str = "me", threshold_pct: float = 10.0) -> list[Signal]:
        signals = []
        for card_id in self._relevant_card_ids(owner_id):
            snapshots = self.price_repo.latest_two(card_id)
            if len(snapshots) < 2:
                continue
            latest, previous = snapshots[0], snapshots[1]
            if previous.market_price == 0:
                continue
            change_pct = (latest.market_price - previous.market_price) / previous.market_price * 100
            if abs(change_pct) >= threshold_pct:
                signals.append(Signal(
                    kind="mover",
                    card_id=card_id,
                    card_name=self._card_name(card_id),
                    detail=f"{change_pct:+.1f}% since previous refresh",
                    current_price=latest.market_price,
                    reference_price=previous.market_price,
                    change_pct=round(change_pct, 1),
                ))
        return signals

    def deals(self, owner_id: str = "me", threshold_pct: float = 15.0) -> list[Signal]:
        signals = []
        for card_id in self._relevant_card_ids(owner_id):
            snapshot = self.price_repo.latest_for(card_id)
            if snapshot is None:
                continue
            if snapshot.direct_low is None or snapshot.market_price <= 0:
                continue
            if snapshot.direct_low <= snapshot.market_price * (1 - threshold_pct / 100):
                discount = (snapshot.market_price - snapshot.direct_low) / snapshot.market_price * 100
                signals.append(Signal(
                    kind="deal",
                    card_id=card_id,
                    card_name=self._card_name(card_id),
                    detail=f"cheapest listing {discount:.0f}% under market",
                    current_price=snapshot.direct_low,
                    reference_price=snapshot.market_price,
                    change_pct=round(discount, 1),
                ))
        return signals

    def target_hits(self, owner_id: str = "me") -> list[Signal]:
        signals = []
        for watch_item in self.watch_repo.list(owner_id):
            if watch_item.target_price is None:
                continue
            snapshot = self.price_repo.latest_for(watch_item.card_id)
            if snapshot is None:
                continue
            if snapshot.market_price <= watch_item.target_price:
                signals.append(Signal(
                    kind="target",
                    card_id=watch_item.card_id,
                    card_name=self._card_name(watch_item.card_id),
                    detail=f"hit target ${watch_item.target_price:.2f}",
                    current_price=snapshot.market_price,
                    reference_price=watch_item.target_price,
                    change_pct=None,
                ))
        return signals

    def all(self, owner_id: str = "me", mover_pct: float = 10.0, deal_pct: float = 15.0) -> dict:
        return {
            "movers": self.movers(owner_id, mover_pct),
            "deals": self.deals(owner_id, deal_pct),
            "target_hits": self.target_hits(owner_id),
        }

    def add_watch(self, result: CardResult, target_price: float | None,
                  owner_id: str = "me") -> WatchItem:
        self.card_repo.upsert(Card(
            id=result.id, name=result.name, set_name=result.set_name,
            set_id=result.set_id, set_total=result.set_total,
            number=result.number, rarity=result.rarity, image_url=result.image_url,
            tcgplayer_id=result.tcgplayer_id,
        ))
        existing_watch_item = self.watch_repo.get_by_card(owner_id, result.id)
        if existing_watch_item is not None:
            existing_watch_item.target_price = target_price
            return self.watch_repo.update(existing_watch_item)
        return self.watch_repo.add(WatchItem(
            card_id=result.id, owner_id=owner_id, target_price=target_price,
        ))

    def list_watch(self, owner_id: str = "me") -> list[tuple[WatchItem, Card | None]]:
        return [(item, self.card_repo.get(item.card_id)) for item in self.watch_repo.list(owner_id)]

    def remove_watch(self, item_id: str) -> bool:
        return self.watch_repo.delete(item_id)
