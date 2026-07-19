from app.errors import PriceProviderError
from app.models import Card, Holding, WatchItem
from app.providers.base import PriceResult
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository
from app.services.price_service import PriceService

from tests.conftest import FakeProvider


class PartiallyFailingProvider:
    """Fake provider that raises for one specific card id and succeeds for others."""

    def __init__(self, failing_card_id, price=400.0):
        self._failing_card_id = failing_card_id
        self._price = price

    def search_cards(self, query):
        return []

    def get_price(self, card_id):
        if card_id == self._failing_card_id:
            raise PriceProviderError("provider down")
        return PriceResult(card_id=card_id, market_price=self._price, currency="USD", source="fake")


def test_refresh_writes_one_snapshot_per_owned_card(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    service = PriceService(CardRepository(session), PriceRepository(session),
                          FakeProvider(price=400.0), HoldingRepository(session),
                          WatchRepository(session))
    assert service.refresh_prices() == {"written": 1, "failed": 0}


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
    assert service.refresh_prices() == {"written": 1, "failed": 0}


def test_refresh_reports_failed_card_and_still_writes_good_ones(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    CardRepository(session).upsert(Card(id="base1-5", name="Blastoise"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    HoldingRepository(session).add(Holding(card_id="base1-5", owner_id="me"))
    price_repo = PriceRepository(session)
    service = PriceService(CardRepository(session), price_repo,
                          PartiallyFailingProvider(failing_card_id="base1-4"),
                          HoldingRepository(session), WatchRepository(session))
    result = service.refresh_prices()
    assert result == {"written": 1, "failed": 1}


def test_refresh_still_writes_snapshot_for_the_good_card_when_one_fails(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    CardRepository(session).upsert(Card(id="base1-5", name="Blastoise"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    HoldingRepository(session).add(Holding(card_id="base1-5", owner_id="me"))
    price_repo = PriceRepository(session)
    service = PriceService(CardRepository(session), price_repo,
                          PartiallyFailingProvider(failing_card_id="base1-4"),
                          HoldingRepository(session), WatchRepository(session))
    service.refresh_prices()
    assert price_repo.latest_for("base1-5").market_price == 400.0
