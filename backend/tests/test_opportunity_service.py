from datetime import datetime, timedelta, timezone

from app.models import Card, PriceSnapshot, WatchItem
from app.providers.base import CardResult
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


def _card_result(card_id: str = "base1-4") -> CardResult:
    return CardResult(
        id=card_id, name="Charizard", set_name="Base", number="4",
        rarity="Rare Holo", image_url="https://img/charizard.png",
        tcgplayer_id=None, market_price=100.0,
    )


def test_add_watch_twice_for_same_card_creates_only_one_watch_item(session):
    service = _make_service(session)
    service.add_watch(_card_result(), target_price=50.0)
    service.add_watch(_card_result(), target_price=75.0)

    watch_items = WatchRepository(session).list("me")

    assert len(watch_items) == 1


def test_add_watch_twice_for_same_card_updates_target_price_to_latest_call(session):
    service = _make_service(session)
    service.add_watch(_card_result(), target_price=50.0)
    service.add_watch(_card_result(), target_price=75.0)

    watch_items = WatchRepository(session).list("me")

    assert watch_items[0].target_price == 75.0


def test_deals_ignore_archived_holdings(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    holding_repo = HoldingRepository(session)
    holding = holding_repo.add(Holding(card_id="base1-4", owner_id="me"))
    holding_repo.set_archived(holding.id, True)
    PriceRepository(session).add(PriceSnapshot(card_id="base1-4", market_price=100.0, direct_low=70.0))

    signals = _make_service(session).deals()

    assert signals == []
