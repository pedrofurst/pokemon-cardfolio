from app.models import Card, Holding, PriceSnapshot
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository


def test_card_upsert_then_get_returns_card(session):
    repo = CardRepository(session)
    repo.upsert(Card(id="base1-4", name="Charizard"))
    assert repo.get("base1-4").name == "Charizard"


def test_holding_list_filters_by_owner(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    assert len(HoldingRepository(session).list("me")) == 1


def test_price_latest_returns_most_recent(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = PriceRepository(session)
    repo.add(PriceSnapshot(card_id="base1-4", market_price=300.0))
    repo.add(PriceSnapshot(card_id="base1-4", market_price=350.0))
    assert repo.latest_for("base1-4").market_price == 350.0
