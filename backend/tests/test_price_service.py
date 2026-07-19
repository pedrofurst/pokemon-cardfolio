from app.models import Card, Holding, WatchItem
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository
from app.services.price_service import PriceService

from tests.conftest import FakeProvider


def test_refresh_writes_one_snapshot_per_owned_card(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    service = PriceService(CardRepository(session), PriceRepository(session),
                          FakeProvider(price=400.0), HoldingRepository(session),
                          WatchRepository(session))
    assert service.refresh_prices() == 1


def test_refresh_persists_direct_low_on_snapshot(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    price_repo = PriceRepository(session)
    service = PriceService(CardRepository(session), price_repo,
                          FakeProvider(price=400.0, direct_low=350.0), HoldingRepository(session),
                          WatchRepository(session))
    service.refresh_prices()
    snapshot = price_repo.latest_for("base1-4")
    assert snapshot.direct_low == 350.0


def test_refresh_writes_snapshot_for_watched_only_card(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    watch_repo = WatchRepository(session)
    watch_repo.add(WatchItem(card_id="base1-4", owner_id="me"))
    price_repo = PriceRepository(session)
    service = PriceService(CardRepository(session), price_repo,
                          FakeProvider(price=400.0), HoldingRepository(session),
                          watch_repo)
    service.refresh_prices()
    assert price_repo.latest_for("base1-4").market_price == 400.0


def test_refresh_counts_owned_and_watched_card_once(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    watch_repo = WatchRepository(session)
    watch_repo.add(WatchItem(card_id="base1-4", owner_id="me"))
    service = PriceService(CardRepository(session), PriceRepository(session),
                          FakeProvider(price=400.0), HoldingRepository(session),
                          watch_repo)
    assert service.refresh_prices() == 1
