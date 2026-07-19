from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.deps import get_price_check_service
from app.errors import PriceProviderError
from app.main import create_application
from app.models import PriceSnapshot
from app.repositories.price_repository import PriceRepository
from app.services.price_check_service import PriceCheckService

from tests.conftest import FakeProvider
from tests.test_price_check_service import RaisingProvider


def _client(price_provider=None):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    app = create_application()
    provider = price_provider or FakeProvider(price=100.0, direct_low=70.0)

    def session_override():
        with Session(engine) as session:
            yield session

    def price_check_override():
        s = Session(engine)
        return PriceCheckService(provider, PriceRepository(s))

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_price_check_service] = price_check_override
    client = TestClient(app)
    client.test_engine = engine
    return client


def test_price_check_endpoint_returns_great_deal_verdict():
    client = _client()
    response = client.post("/price-check", json={"card_id": "base1-4", "offer_price": 60.0})
    assert response.json()["verdict"] == "great_deal"


def test_price_check_endpoint_returns_fair_verdict():
    client = _client()
    response = client.post("/price-check", json={"card_id": "base1-4", "offer_price": 100.0})
    assert response.json()["verdict"] == "fair"


def test_price_check_endpoint_returns_overpriced_verdict():
    client = _client()
    response = client.post("/price-check", json={"card_id": "base1-4", "offer_price": 130.0})
    assert response.json()["verdict"] == "overpriced"


def test_price_check_endpoint_falls_back_to_snapshot_when_provider_fails():
    client = _client(price_provider=RaisingProvider(PriceProviderError("provider down")))
    with Session(client.test_engine) as session:
        PriceRepository(session).add(PriceSnapshot(card_id="base1-4", market_price=100.0, direct_low=70.0))
    response = client.post("/price-check", json={"card_id": "base1-4", "offer_price": 60.0})
    assert response.json()["verdict"] == "great_deal"


def test_price_check_endpoint_returns_502_when_provider_fails_with_no_snapshot():
    client = _client(price_provider=RaisingProvider(PriceProviderError("provider down")))
    response = client.post("/price-check", json={"card_id": "base1-4", "offer_price": 60.0})
    assert response.status_code == 502


def test_price_check_endpoint_returns_422_for_negative_offer_price():
    client = _client()
    response = client.post("/price-check", json={"card_id": "base1-4", "offer_price": -10.0})
    assert response.status_code == 422
