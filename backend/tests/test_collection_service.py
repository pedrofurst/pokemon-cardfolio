import pytest

from app.errors import HoldingNotFoundError
from app.providers.base import CardResult
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.sale_repository import SaleRepository
from app.services.collection_service import CollectionService


def _service(session):
    return CollectionService(
        CardRepository(session), HoldingRepository(session), PriceRepository(session),
        PortfolioRepository(session),
    )


def test_add_holding_persists_card_and_pnl_is_positive(session, sample_result):
    service = _service(session)
    service.add_holding_from_result(sample_result, condition="NM", is_graded=False,
                                    acquisition_cost=120.0, quantity=1, notes="")
    view = service.list_collection()[0]
    assert view.pnl == 230.0


def test_summary_totals_across_holdings(session, sample_result):
    service = _service(session)
    service.add_holding_from_result(sample_result, condition="NM", is_graded=False,
                                    acquisition_cost=120.0, quantity=2, notes="")
    assert service.summary().total_value == 700.0


def test_add_holding_with_no_market_price_creates_no_snapshot(session):
    service = _service(session)
    result_without_price = CardResult(
        id="base1-4", name="Charizard", set_name="Base", number="4",
        rarity="Rare Holo", image_url="i", tcgplayer_id=None, market_price=None,
    )
    service.add_holding_from_result(result_without_price, condition="NM", is_graded=False,
                                    acquisition_cost=120.0, quantity=1, notes="")
    view = service.list_collection()[0]
    assert view.current_price is None


def test_add_holding_with_no_market_price_has_negative_pnl(session):
    service = _service(session)
    result_without_price = CardResult(
        id="base1-4", name="Charizard", set_name="Base", number="4",
        rarity="Rare Holo", image_url="i", tcgplayer_id=None, market_price=None,
    )
    service.add_holding_from_result(result_without_price, condition="NM", is_graded=False,
                                    acquisition_cost=120.0, quantity=1, notes="")
    view = service.list_collection()[0]
    assert view.pnl == -120.0


def test_record_portfolio_snapshot_writes_totals_matching_summary(session, sample_result):
    service = _service(session)
    service.add_holding_from_result(sample_result, condition="NM", is_graded=False,
                                    acquisition_cost=120.0, quantity=1, notes="")
    summary = service.summary()
    snapshot = service.record_portfolio_snapshot()
    assert (snapshot.total_cost, snapshot.total_value, snapshot.pnl) == (
        summary.total_cost, summary.total_value, summary.pnl,
    )


def test_archive_holding_removes_it_from_the_collection(session, sample_result):
    service = _service(session)
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    assert service.list_collection() == []


def test_archive_holding_drops_total_cost_to_zero(session, sample_result):
    service = _service(session)
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    assert service.summarize(service.list_collection()).total_cost == 0


def test_restore_holding_returns_it_to_the_collection(session, sample_result):
    service = _service(session)
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    service.restore_holding(holding.id)
    assert len(service.list_collection()) == 1


def test_list_collection_returns_archived_when_requested(session, sample_result):
    service = _service(session)
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    assert len(service.list_collection(archived=True)) == 1


def test_archive_holding_raises_when_missing(session):
    service = _service(session)
    with pytest.raises(HoldingNotFoundError):
        service.archive_holding("nonexistent-id")


def test_archive_holding_does_not_record_a_sale(session, sample_result):
    service = _service(session)
    holding = service.add_holding_from_result(sample_result, "raw", False, 100.0, 1, "")
    service.archive_holding(holding.id)
    assert SaleRepository(session).list("me") == []
