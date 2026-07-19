from datetime import date, datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid4())


class Card(SQLModel, table=True):
    id: str = Field(primary_key=True)  # API card id, e.g. "base1-4"
    name: str
    set_name: str = ""
    set_id: str = ""
    set_total: int | None = None
    number: str = ""
    rarity: str = ""
    image_url: str = ""
    tcgplayer_id: str | None = None


class Holding(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    owner_id: str = "me"
    card_id: str = Field(foreign_key="card.id", index=True)
    condition: str = "raw"
    is_graded: bool = False
    acquisition_cost: float = 0.0
    acquisition_date: date = Field(default_factory=date.today)
    quantity: int = 1
    notes: str = ""


class WatchItem(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    owner_id: str = "me"
    card_id: str = Field(foreign_key="card.id", index=True)
    target_price: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PriceSnapshot(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    card_id: str = Field(foreign_key="card.id", index=True)
    source: str = "tcgplayer"
    market_price: float = 0.0
    currency: str = "USD"
    low: float | None = None
    mid: float | None = None
    high: float | None = None
    direct_low: float | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Sale(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    owner_id: str = "me"
    card_id: str = Field(foreign_key="card.id", index=True)
    quantity: int = 1
    sale_price: float = 0.0
    fee: float = 0.0
    cost_basis: float = 0.0
    sold_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioSnapshot(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    owner_id: str = "me"
    total_cost: float = 0.0
    total_value: float = 0.0
    pnl: float = 0.0
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
