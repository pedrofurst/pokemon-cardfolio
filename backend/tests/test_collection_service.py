from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.collection_service import CollectionService

from tests.conftest import FakeProvider


def _service(session, price=350.0):
    return CollectionService(
        CardRepository(session), HoldingRepository(session),
        PriceRepository(session), FakeProvider(price=price),
    )


def test_add_holding_persists_card_and_pnl_is_positive(session, sample_result):
    service = _service(session, price=350.0)
    service.add_holding_from_result(sample_result, condition="NM", is_graded=False,
                                    acquisition_cost=120.0, quantity=1, notes="")
    view = service.list_collection()[0]
    assert view.pnl == 230.0


def test_summary_totals_across_holdings(session, sample_result):
    service = _service(session, price=350.0)
    service.add_holding_from_result(sample_result, condition="NM", is_graded=False,
                                    acquisition_cost=120.0, quantity=2, notes="")
    assert service.summary().total_value == 700.0
