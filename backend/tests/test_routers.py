from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.deps import (
    get_collection_service,
    get_grading_service,
    get_opportunity_service,
    get_price_service,
)
from app.errors import CardNotFoundError, PriceProviderError
from app.main import create_application
from app.models import Card, PriceSnapshot
from app.providers.base import CardResult
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.watch_repository import WatchRepository
from app.services.collection_service import CollectionService
from app.services.grading_service import GradingService
from app.services.opportunity_service import OpportunityService
from app.services.price_service import PriceService

from tests.conftest import FakeProvider


class RaisingProvider:
    """Fake provider whose get_price always raises a configured exception."""

    def __init__(self, exception_to_raise):
        self._exception_to_raise = exception_to_raise

    def search_cards(self, query):
        return []

    def get_price(self, card_id):
        raise self._exception_to_raise


def _client(price_provider=None):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    app = create_application()
    provider = price_provider or FakeProvider(price=350.0)

    def session_override():
        with Session(engine) as session:
            yield session

    def collection_override():
        s = Session(engine)
        return CollectionService(CardRepository(s), HoldingRepository(s), PriceRepository(s),
                                  PortfolioRepository(s))

    def price_override():
        s = Session(engine)
        return PriceService(CardRepository(s), PriceRepository(s), provider, HoldingRepository(s),
                             WatchRepository(s))

    def opportunity_override():
        s = Session(engine)
        return OpportunityService(CardRepository(s), PriceRepository(s), HoldingRepository(s),
                                   WatchRepository(s))

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_collection_service] = collection_override
    app.dependency_overrides[get_price_service] = price_override
    app.dependency_overrides[get_opportunity_service] = opportunity_override
    app.dependency_overrides[get_grading_service] = lambda: GradingService()
    client = TestClient(app)
    client.test_engine = engine
    return client


def _add_sample_holding(client):
    payload = {"card": {"id": "base1-4", "name": "Charizard"}, "acquisition_cost": 120.0, "quantity": 1}
    client.post("/holdings", json=payload)


def test_add_then_list_returns_pnl():
    client = _client()
    payload = {
        "card": {"id": "base1-4", "name": "Charizard", "market_price": 350.0},
        "acquisition_cost": 120.0, "quantity": 1,
    }
    client.post("/holdings", json=payload)
    body = client.get("/holdings").json()
    assert body["items"][0]["pnl"] == 230.0


def test_add_holding_with_no_market_price_does_not_500():
    client = _client()
    payload = {"card": {"id": "base1-4", "name": "Charizard"}, "acquisition_cost": 120.0, "quantity": 1}
    response = client.post("/holdings", json=payload)
    assert response.status_code == 200


def test_search_cards_returns_mapped_card():
    sample_result = CardResult(
        id="base1-4", name="Charizard", set_name="Base", number="4",
        rarity="Rare Holo", image_url="i", tcgplayer_id=None, market_price=350.0,
    )
    client = _client(price_provider=FakeProvider(cards=[sample_result]))
    response = client.get("/cards/search", params={"q": "Charizard"})
    body = response.json()
    assert body[0]["id"] == "base1-4"


def test_refresh_prices_returns_written_count():
    client = _client()
    _add_sample_holding(client)
    response = client.post("/prices/refresh")
    assert response.json() == {"written": 1, "failed": 0}


def test_refresh_prices_records_a_portfolio_snapshot():
    client = _client()
    _add_sample_holding(client)
    client.post("/prices/refresh")
    with Session(client.test_engine) as session:
        latest = PortfolioRepository(session).latest("me")
    assert latest is not None


def test_prices_status_is_null_before_any_refresh():
    client = _client()
    response = client.get("/prices/status")
    assert response.json() == {"last_refresh": None}


def test_prices_status_returns_iso_timestamp_after_refresh():
    client = _client()
    _add_sample_holding(client)
    client.post("/prices/refresh")
    response = client.get("/prices/status")
    assert response.json()["last_refresh"] is not None


def test_history_portfolio_returns_seeded_series():
    client = _client()
    _add_sample_holding(client)
    client.post("/prices/refresh")
    client.post("/prices/refresh")
    response = client.get("/history/portfolio")
    assert len(response.json()) == 2


def test_history_card_returns_seeded_series():
    client = _client()
    with Session(client.test_engine) as session:
        card_repo = CardRepository(session)
        price_repo = PriceRepository(session)
        card_repo.upsert(Card(id="base1-4", name="Charizard"))
        price_repo.add(PriceSnapshot(card_id="base1-4", market_price=100.0))
        price_repo.add(PriceSnapshot(card_id="base1-4", market_price=130.0))
    response = client.get("/history/card/base1-4")
    body = response.json()
    assert [point["market_price"] for point in body] == [100.0, 130.0]


def test_refresh_prices_with_failing_provider_does_not_500():
    client = _client(price_provider=RaisingProvider(PriceProviderError("provider down")))
    _add_sample_holding(client)
    response = client.post("/prices/refresh")
    assert response.status_code == 200


def test_refresh_prices_with_failing_provider_reports_failed_count():
    client = _client(price_provider=RaisingProvider(PriceProviderError("provider down")))
    _add_sample_holding(client)
    response = client.post("/prices/refresh")
    assert response.json() == {"written": 0, "failed": 1}


def test_refresh_prices_with_card_not_found_provider_reports_failed_count():
    client = _client(price_provider=RaisingProvider(CardNotFoundError("base1-4")))
    _add_sample_holding(client)
    response = client.post("/prices/refresh")
    assert response.json() == {"written": 0, "failed": 1}


def test_add_watch_then_list_watch_returns_it():
    client = _client()
    payload = {"card": {"id": "base1-4", "name": "Charizard"}, "target_price": 200.0}
    client.post("/watchlist", json=payload)
    body = client.get("/watchlist").json()
    assert body[0]["card"]["id"] == "base1-4"


def test_delete_watch_returns_deleted_true():
    client = _client()
    payload = {"card": {"id": "base1-4", "name": "Charizard"}, "target_price": 200.0}
    added = client.post("/watchlist", json=payload).json()
    response = client.delete(f"/watchlist/{added['id']}")
    assert response.json() == {"deleted": True}


def test_opportunities_returns_three_keys_with_mover():
    client = _client()
    payload = {"card": {"id": "base1-4", "name": "Charizard"}, "target_price": None}
    client.post("/watchlist", json=payload)

    with Session(client.test_engine) as session:
        card_repo = CardRepository(session)
        price_repo = PriceRepository(session)
        card_repo.upsert(Card(id="base1-4", name="Charizard"))
        price_repo.add(PriceSnapshot(card_id="base1-4", market_price=100.0))
        price_repo.add(PriceSnapshot(card_id="base1-4", market_price=130.0))

    body = client.get("/opportunities").json()
    assert set(body.keys()) == {"movers", "deals", "target_hits"}
    assert body["movers"][0]["card_id"] == "base1-4"


def test_grading_evaluate_with_explicit_raw_price_returns_recommendation():
    client = _client()
    payload = {"raw_price": 50.0, "psa10_price": 300.0, "psa9_price": 120.0}
    response = client.post("/grading/evaluate", json=payload)
    assert response.status_code == 200
    assert "recommendation" in response.json()


def test_grading_evaluate_auto_fills_raw_price_from_seeded_snapshot():
    client = _client()
    with Session(client.test_engine) as session:
        card_repo = CardRepository(session)
        price_repo = PriceRepository(session)
        card_repo.upsert(Card(id="base1-4", name="Charizard"))
        price_repo.add(PriceSnapshot(card_id="base1-4", market_price=50.0))

    payload = {"card_id": "base1-4", "raw_price": None, "psa10_price": 300.0}
    response = client.post("/grading/evaluate", json=payload)
    body = response.json()
    assert response.status_code == 200
    assert body["raw_net"] == 50.0 * (1 - 0.13)


def test_grading_evaluate_without_raw_price_or_card_id_returns_400():
    client = _client()
    response = client.post("/grading/evaluate", json={})
    assert response.status_code == 400


def test_grading_evaluate_with_out_of_range_prob_psa10_returns_422():
    client = _client()
    payload = {"raw_price": 50.0, "psa10_price": 300.0, "prob_psa10": 1.5}
    response = client.post("/grading/evaluate", json=payload)
    assert response.status_code == 422


def test_grading_evaluate_with_negative_psa10_price_returns_422():
    client = _client()
    payload = {"raw_price": 50.0, "psa10_price": -300.0}
    response = client.post("/grading/evaluate", json=payload)
    assert response.status_code == 422
