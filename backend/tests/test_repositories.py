from app.models import Card, Holding, PortfolioSnapshot, PriceSnapshot, Sale, WatchItem
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.sale_repository import SaleRepository
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


def test_holding_get_returns_the_holding_when_found(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    assert repo.get(holding.id).id == holding.id


def test_holding_get_returns_none_when_missing(session):
    repo = HoldingRepository(session)
    assert repo.get("nonexistent-id") is None


def test_holding_update_persists_field_changes(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me", quantity=3))
    holding.quantity = 2
    repo.update(holding)
    assert repo.get(holding.id).quantity == 2


def test_holding_delete_returns_true_when_found(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = HoldingRepository(session)
    holding = repo.add(Holding(card_id="base1-4", owner_id="me"))
    assert repo.delete(holding.id) is True


def test_holding_delete_returns_false_when_missing(session):
    repo = HoldingRepository(session)
    assert repo.delete("nonexistent-id") is False


def test_sale_add_then_list_returns_it(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = SaleRepository(session)
    repo.add(Sale(card_id="base1-4", owner_id="me", quantity=1, sale_price=100.0, cost_basis=50.0))
    assert len(repo.list("me")) == 1


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


def test_portfolio_history_returns_snapshots_in_ascending_order(session):
    repo = PortfolioRepository(session)
    repo.add(PortfolioSnapshot(owner_id="me", total_value=100.0))
    repo.add(PortfolioSnapshot(owner_id="me", total_value=200.0))
    history = repo.history("me")
    assert [snapshot.total_value for snapshot in history] == [100.0, 200.0]


def test_portfolio_latest_returns_most_recent(session):
    repo = PortfolioRepository(session)
    repo.add(PortfolioSnapshot(owner_id="me", total_value=100.0))
    repo.add(PortfolioSnapshot(owner_id="me", total_value=200.0))
    assert repo.latest("me").total_value == 200.0


def test_portfolio_latest_returns_none_when_empty(session):
    repo = PortfolioRepository(session)
    assert repo.latest("me") is None
