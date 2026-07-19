import pytest

from app.models import Card, Holding
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.sale_repository import SaleRepository
from app.services.sale_service import SaleService


def _make_service(session):
    return SaleService(HoldingRepository(session), SaleRepository(session), CardRepository(session))


def _seed_holding(session, quantity: int = 3, acquisition_cost: float = 50.0) -> Holding:
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    return HoldingRepository(session).add(
        Holding(card_id="base1-4", owner_id="me", quantity=quantity, acquisition_cost=acquisition_cost),
    )


def test_record_sale_reduces_holding_quantity(session):
    holding = _seed_holding(session, quantity=3)
    service = _make_service(session)

    service.record_sale(holding.id, quantity=1, sale_price=100.0)

    assert HoldingRepository(session).get(holding.id).quantity == 2


def test_record_sale_creates_sale_with_cost_basis_from_holding(session):
    holding = _seed_holding(session, quantity=3, acquisition_cost=42.0)
    service = _make_service(session)

    sale = service.record_sale(holding.id, quantity=1, sale_price=100.0)

    assert sale.cost_basis == 42.0


def test_record_sale_of_all_units_deletes_the_holding(session):
    holding = _seed_holding(session, quantity=1)
    service = _make_service(session)

    service.record_sale(holding.id, quantity=1, sale_price=100.0)

    assert HoldingRepository(session).get(holding.id) is None


def test_record_sale_of_partial_units_keeps_the_holding(session):
    holding = _seed_holding(session, quantity=3)
    service = _make_service(session)

    service.record_sale(holding.id, quantity=1, sale_price=100.0)

    assert HoldingRepository(session).get(holding.id) is not None


def test_record_sale_with_quantity_above_holding_raises_value_error(session):
    holding = _seed_holding(session, quantity=1)
    service = _make_service(session)

    with pytest.raises(ValueError):
        service.record_sale(holding.id, quantity=2, sale_price=100.0)


def test_record_sale_for_unknown_holding_raises_value_error(session):
    service = _make_service(session)

    with pytest.raises(ValueError):
        service.record_sale("nonexistent-id", quantity=1, sale_price=100.0)


def test_realized_summary_total_proceeds_nets_out_fees(session):
    holding = _seed_holding(session, quantity=3, acquisition_cost=50.0)
    service = _make_service(session)
    service.record_sale(holding.id, quantity=2, sale_price=100.0, fee=10.0)

    summary = service.realized_summary()

    assert summary.total_proceeds == 190.0


def test_realized_summary_total_cost_uses_cost_basis_times_quantity(session):
    holding = _seed_holding(session, quantity=3, acquisition_cost=50.0)
    service = _make_service(session)
    service.record_sale(holding.id, quantity=2, sale_price=100.0, fee=10.0)

    summary = service.realized_summary()

    assert summary.total_cost == 100.0


def test_realized_summary_realized_pnl_is_proceeds_minus_cost(session):
    holding = _seed_holding(session, quantity=3, acquisition_cost=50.0)
    service = _make_service(session)
    service.record_sale(holding.id, quantity=2, sale_price=100.0, fee=10.0)

    summary = service.realized_summary()

    assert summary.realized_pnl == 90.0


def test_realized_summary_sales_count_reflects_number_of_sale_rows(session):
    holding = _seed_holding(session, quantity=3, acquisition_cost=50.0)
    service = _make_service(session)
    service.record_sale(holding.id, quantity=1, sale_price=100.0)
    service.record_sale(holding.id, quantity=1, sale_price=110.0)

    summary = service.realized_summary()

    assert summary.sales_count == 2


def test_history_returns_sale_paired_with_its_card(session):
    holding = _seed_holding(session, quantity=1)
    service = _make_service(session)
    service.record_sale(holding.id, quantity=1, sale_price=100.0)

    history = service.history()

    assert history[0][1].id == "base1-4"
