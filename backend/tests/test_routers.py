from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.deps import get_collection_service, get_price_service
from app.errors import CardNotFoundError, PriceProviderError
from app.main import create_application
from app.providers.base import CardResult
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.collection_service import CollectionService
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
        return CollectionService(CardRepository(s), HoldingRepository(s), PriceRepository(s), FakeProvider(price=350.0))

    def price_override():
        s = Session(engine)
        return PriceService(CardRepository(s), PriceRepository(s), provider, HoldingRepository(s))

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_collection_service] = collection_override
    app.dependency_overrides[get_price_service] = price_override
    return TestClient(app)


def _add_sample_holding(client):
    payload = {"card": {"id": "base1-4", "name": "Charizard"}, "acquisition_cost": 120.0, "quantity": 1}
    client.post("/holdings", json=payload)


def test_add_then_list_returns_pnl():
    client = _client()
    payload = {"card": {"id": "base1-4", "name": "Charizard"}, "acquisition_cost": 120.0, "quantity": 1}
    client.post("/holdings", json=payload)
    body = client.get("/holdings").json()
    assert body["items"][0]["pnl"] == 230.0


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
    assert response.json() == {"written": 1}


def test_refresh_prices_translates_price_provider_error_to_502():
    client = _client(price_provider=RaisingProvider(PriceProviderError("provider down")))
    _add_sample_holding(client)
    response = client.post("/prices/refresh")
    assert response.status_code == 502


def test_refresh_prices_translates_card_not_found_error_to_404():
    client = _client(price_provider=RaisingProvider(CardNotFoundError("base1-4")))
    _add_sample_holding(client)
    response = client.post("/prices/refresh")
    assert response.status_code == 404
