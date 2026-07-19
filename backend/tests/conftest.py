import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.providers.base import CardResult, PriceResult


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class FakeProvider:
    def __init__(self, cards=None, price=350.0):
        self._cards = cards or []
        self._price = price

    def search_cards(self, query):
        return self._cards

    def get_price(self, card_id):
        return PriceResult(card_id=card_id, market_price=self._price, currency="USD", source="fake")


@pytest.fixture
def sample_result():
    return CardResult(
        id="base1-4", name="Charizard", set_name="Base", number="4",
        rarity="Rare Holo", image_url="i", tcgplayer_id=None, market_price=350.0,
    )
