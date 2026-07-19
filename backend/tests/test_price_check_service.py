import pytest

from app.errors import PriceProviderError
from app.models import PriceSnapshot
from app.repositories.price_repository import PriceRepository
from app.services.price_check_service import PriceCheckService

from tests.conftest import FakeProvider


class RaisingProvider:
    """Fake provider whose get_price always raises a configured domain error."""

    def __init__(self, exception_to_raise):
        self._exception_to_raise = exception_to_raise

    def search_cards(self, query):
        return []

    def get_price(self, card_id):
        raise self._exception_to_raise


def test_great_deal_verdict_when_offer_is_far_below_market(session):
    service = PriceCheckService(FakeProvider(price=100.0, direct_low=70.0), PriceRepository(session))
    result = service.check("base1-4", 60.0)
    assert result.verdict == "great_deal"


def test_fair_verdict_when_offer_matches_market(session):
    service = PriceCheckService(FakeProvider(price=100.0, direct_low=70.0), PriceRepository(session))
    result = service.check("base1-4", 100.0)
    assert result.verdict == "fair"


def test_overpriced_verdict_when_offer_is_far_above_market(session):
    service = PriceCheckService(FakeProvider(price=100.0, direct_low=70.0), PriceRepository(session))
    result = service.check("base1-4", 130.0)
    assert result.verdict == "overpriced"


def test_slightly_high_verdict_when_offer_is_a_bit_above_market(session):
    service = PriceCheckService(FakeProvider(price=100.0, direct_low=70.0), PriceRepository(session))
    result = service.check("base1-4", 112.0)
    assert result.verdict == "slightly_high"


def test_slightly_low_verdict_when_offer_is_a_bit_below_market(session):
    service = PriceCheckService(FakeProvider(price=100.0, direct_low=50.0), PriceRepository(session))
    result = service.check("base1-4", 89.0)
    assert result.verdict == "slightly_low"


def test_delta_pct_is_computed_against_market_price(session):
    service = PriceCheckService(FakeProvider(price=100.0, direct_low=70.0), PriceRepository(session))
    result = service.check("base1-4", 130.0)
    assert result.delta_pct == 30.0


def test_falls_back_to_stored_snapshot_when_provider_raises(session):
    price_repo = PriceRepository(session)
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=100.0, direct_low=70.0))
    service = PriceCheckService(RaisingProvider(PriceProviderError("provider down")), price_repo)
    result = service.check("base1-4", 60.0)
    assert result.verdict == "great_deal"


def test_fallback_uses_snapshot_market_price_as_market(session):
    price_repo = PriceRepository(session)
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=200.0))
    service = PriceCheckService(RaisingProvider(PriceProviderError("provider down")), price_repo)
    result = service.check("base1-4", 200.0)
    assert result.market == 200.0


def test_reraises_domain_error_when_no_snapshot_available(session):
    service = PriceCheckService(
        RaisingProvider(PriceProviderError("provider down")), PriceRepository(session),
    )
    with pytest.raises(PriceProviderError):
        service.check("base1-4", 60.0)
