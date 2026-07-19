from app.models import Card, Holding, PriceSnapshot, WatchItem
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository


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


def test_watch_add_then_list_returns_it(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = WatchRepository(session)
    repo.add(WatchItem(card_id="base1-4", owner_id="me"))
    assert len(repo.list("me")) == 1


def test_watch_delete_returns_true_when_found(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = WatchRepository(session)
    item = repo.add(WatchItem(card_id="base1-4", owner_id="me"))
    assert repo.delete(item.id) is True


def test_watch_delete_returns_false_when_missing(session):
    repo = WatchRepository(session)
    assert repo.delete("nonexistent-id") is False


def test_watch_card_ids_returns_watched_set(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.add(Card(id="base1-5", name="Blastoise"))
    session.commit()
    repo = WatchRepository(session)
    repo.add(WatchItem(card_id="base1-4", owner_id="me"))
    repo.add(WatchItem(card_id="base1-5", owner_id="me"))
    assert repo.card_ids("me") == {"base1-4", "base1-5"}
