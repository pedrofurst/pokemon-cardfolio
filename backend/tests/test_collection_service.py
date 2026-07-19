from app.providers.base import CardResult
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.collection_service import CollectionService


def _service(session):
    return CollectionService(
        CardRepository(session), HoldingRepository(session), PriceRepository(session),
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
