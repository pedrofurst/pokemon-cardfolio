from app.models import Card, Holding, PriceSnapshot
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.sale_repository import SaleRepository
from app.repositories.watch_repository import WatchRepository
from app.services.collection_service import CollectionService
from app.services.digest_service import DigestService
from app.services.opportunity_service import OpportunityService
from app.services.sale_service import SaleService


def _make_service(session) -> DigestService:
    card_repo = CardRepository(session)
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)
    portfolio_repo = PortfolioRepository(session)
    watch_repo = WatchRepository(session)
    sale_repo = SaleRepository(session)
    return DigestService(
        CollectionService(card_repo, holding_repo, price_repo, portfolio_repo),
        OpportunityService(card_repo, price_repo, holding_repo, watch_repo),
        SaleService(holding_repo, sale_repo, card_repo),
        portfolio_repo,
    )


def _seed_gaining_and_losing_holdings(session) -> None:
    card_repo = CardRepository(session)
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)
    card_repo.upsert(Card(id="base1-4", name="Charizard"))
    card_repo.upsert(Card(id="base1-2", name="Blastoise"))
    holding_repo.add(Holding(card_id="base1-4", owner_id="me", quantity=1, acquisition_cost=50.0))
    holding_repo.add(Holding(card_id="base1-2", owner_id="me", quantity=1, acquisition_cost=200.0))
    price_repo.add(PriceSnapshot(card_id="base1-4", market_price=350.0))
    price_repo.add(PriceSnapshot(card_id="base1-2", market_price=50.0))


def _seed_mover(session) -> None:
    card_repo = CardRepository(session)
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)
    card_repo.upsert(Card(id="base1-9", name="Venusaur"))
    holding_repo.add(Holding(card_id="base1-9", owner_id="me", quantity=1, acquisition_cost=10.0))
    price_repo.add(PriceSnapshot(card_id="base1-9", market_price=100.0))
    price_repo.add(PriceSnapshot(card_id="base1-9", market_price=130.0))


def _seed_sale(session) -> None:
    holding_repo = HoldingRepository(session)
    CardRepository(session).upsert(Card(id="base1-15", name="Alakazam"))
    holding = holding_repo.add(
        Holding(card_id="base1-15", owner_id="me", quantity=1, acquisition_cost=10.0),
    )
    sale_service = SaleService(holding_repo, SaleRepository(session), CardRepository(session))
    sale_service.record_sale(holding.id, quantity=1, sale_price=100.0)


def test_build_returns_a_summary(session):
    _seed_gaining_and_losing_holdings(session)
    service = _make_service(session)

    digest = service.build()

    assert digest["summary"]["total_cost"] == 250.0


def test_build_realized_pnl_reflects_a_sale(session):
    _seed_gaining_and_losing_holdings(session)
    _seed_sale(session)
    service = _make_service(session)

    digest = service.build()

    assert digest["realized"]["realized_pnl"] == 90.0


def test_build_top_gainer_is_the_holding_with_the_highest_pnl(session):
    _seed_gaining_and_losing_holdings(session)
    service = _make_service(session)

    digest = service.build()

    assert digest["top_gainer"]["card_id"] == "base1-4"


def test_build_movers_is_non_empty_when_a_card_swings(session):
    _seed_mover(session)
    service = _make_service(session)

    digest = service.build()

    assert len(digest["movers"]) > 0


def test_build_with_empty_collection_returns_null_top_gainer(session):
    service = _make_service(session)

    digest = service.build()

    assert digest["top_gainer"] is None


def test_build_with_empty_collection_returns_zeroed_summary(session):
    service = _make_service(session)

    digest = service.build()

    assert digest["summary"] == {"total_cost": 0.0, "total_value": 0.0, "pnl": 0.0, "pnl_pct": 0.0}
