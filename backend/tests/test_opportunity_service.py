from datetime import datetime, timedelta, timezone

from app.models import Card, PriceSnapshot, WatchItem
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository
from app.services.opportunity_service import OpportunityService

from app.models import Holding


def _make_service(session):
    return OpportunityService(
        CardRepository(session),
        PriceRepository(session),
        HoldingRepository(session),
        WatchRepository(session),
    )


def test_mover_appears_when_price_jumps_above_threshold(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    price_repo = PriceRepository(session)
    now = datetime.now(timezone.utc)
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=100.0, fetched_at=now - timedelta(hours=1)))
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=130.0, fetched_at=now))

    signals = _make_service(session).movers()

    assert [signal.card_id for signal in signals] == ["base1-4"]


def test_mover_signal_has_expected_change_pct(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    price_repo = PriceRepository(session)
    now = datetime.now(timezone.utc)
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=100.0, fetched_at=now - timedelta(hours=1)))
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=130.0, fetched_at=now))

    signals = _make_service(session).movers()

    assert signals[0].change_pct == 30.0


def test_small_change_is_not_a_mover(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    price_repo = PriceRepository(session)
    now = datetime.now(timezone.utc)
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=100.0, fetched_at=now - timedelta(hours=1)))
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=103.0, fetched_at=now))

    signals = _make_service(session).movers()

    assert signals == []


def test_deal_appears_when_direct_low_far_under_market(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    PriceRepository(session).add(PriceSnapshot(card_id="base1-4", market_price=100.0, direct_low=70.0))

    signals = _make_service(session).deals()

    assert [signal.card_id for signal in signals] == ["base1-4"]


def test_small_discount_is_not_a_deal(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    PriceRepository(session).add(PriceSnapshot(card_id="base1-4", market_price=100.0, direct_low=95.0))

    signals = _make_service(session).deals()

    assert signals == []


def test_target_hit_appears_when_market_at_or_below_target(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    WatchRepository(session).add(WatchItem(card_id="base1-4", owner_id="me", target_price=50.0))
    PriceRepository(session).add(PriceSnapshot(card_id="base1-4", market_price=40.0))

    signals = _make_service(session).target_hits()

    assert [signal.card_id for signal in signals] == ["base1-4"]


def test_target_not_hit_when_market_above_target(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    WatchRepository(session).add(WatchItem(card_id="base1-4", owner_id="me", target_price=50.0))
    PriceRepository(session).add(PriceSnapshot(card_id="base1-4", market_price=60.0))

    signals = _make_service(session).target_hits()

    assert signals == []


def test_all_returns_the_three_signal_lists(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    PriceRepository(session).add(PriceSnapshot(card_id="base1-4", market_price=100.0))

    result = _make_service(session).all()

    assert set(result.keys()) == {"movers", "deals", "target_hits"}
