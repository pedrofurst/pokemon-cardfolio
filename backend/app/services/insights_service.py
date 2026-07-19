from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository


class InsightsService:
    def __init__(self, card_repo: CardRepository, holding_repo: HoldingRepository,
                 price_repo: PriceRepository) -> None:
        self.card_repo = card_repo
        self.holding_repo = holding_repo
        self.price_repo = price_repo

    def set_progress(self, owner_id: str = "me") -> list[dict]:
        owned_card_ids_by_set: dict[str, set[str]] = {}
        set_name_by_set: dict[str, str] = {}
        set_total_by_set: dict[str, int | None] = {}
        for holding in self.holding_repo.list(owner_id):
            card = self.card_repo.get(holding.card_id)
            if card is None or card.set_id == "":
                continue
            owned_card_ids_by_set.setdefault(card.set_id, set()).add(card.id)
            set_name_by_set[card.set_id] = card.set_name
            set_total_by_set[card.set_id] = card.set_total

        rows = []
        for set_id, owned_card_ids in owned_card_ids_by_set.items():
            owned = len(owned_card_ids)
            total = set_total_by_set[set_id]
            pct = (owned / total * 100.0) if total else None
            rows.append({
                "set_id": set_id,
                "set_name": set_name_by_set[set_id],
                "owned": owned,
                "total": total,
                "pct": pct,
            })
        rows.sort(key=lambda row: (row["pct"] is None, -(row["pct"] or 0.0)))
        return rows

    def allocation(self, owner_id: str = "me") -> dict:
        value_by_set: dict[str, float] = {}
        value_by_rarity: dict[str, float] = {}
        value_by_card: dict[str, float] = {}
        name_by_card: dict[str, str] = {}
        total_value = 0.0

        for holding in self.holding_repo.list(owner_id):
            latest = self.price_repo.latest_for(holding.card_id)
            current_price = latest.market_price if latest else 0.0
            value = (current_price or 0.0) * holding.quantity
            total_value += value

            card = self.card_repo.get(holding.card_id)
            set_name = card.set_name if card else ""
            rarity = (card.rarity if card else "") or "Unknown"
            name = card.name if card else holding.card_id

            value_by_set[set_name] = value_by_set.get(set_name, 0.0) + value
            value_by_rarity[rarity] = value_by_rarity.get(rarity, 0.0) + value
            value_by_card[holding.card_id] = value_by_card.get(holding.card_id, 0.0) + value
            name_by_card[holding.card_id] = name

        def to_pct(value: float) -> float:
            return (value / total_value * 100.0) if total_value else 0.0

        by_set = sorted(
            ({"name": name, "value": value, "pct": to_pct(value)}
             for name, value in value_by_set.items()),
            key=lambda row: row["value"], reverse=True,
        )
        by_rarity = sorted(
            ({"rarity": rarity, "value": value, "pct": to_pct(value)}
             for rarity, value in value_by_rarity.items()),
            key=lambda row: row["value"], reverse=True,
        )
        top_cards = sorted(
            ({"card_id": card_id, "name": name_by_card[card_id], "value": value}
             for card_id, value in value_by_card.items()),
            key=lambda row: row["value"], reverse=True,
        )[:5]

        return {
            "total_value": total_value,
            "by_set": by_set,
            "by_rarity": by_rarity,
            "top_cards": top_cards,
        }

    def build(self, owner_id: str = "me") -> dict:
        return {
            "sets": self.set_progress(owner_id),
            "allocation": self.allocation(owner_id),
        }
