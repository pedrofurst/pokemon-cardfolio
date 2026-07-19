from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.deps import get_collection_service, get_price_service
from app.main import create_application
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.collection_service import CollectionService
from app.services.price_service import PriceService

from tests.conftest import FakeProvider


def _client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    app = create_application()

    def session_override():
        with Session(engine) as session:
            yield session

    def collection_override():
        s = Session(engine)
        return CollectionService(CardRepository(s), HoldingRepository(s), PriceRepository(s), FakeProvider(price=350.0))

    def price_override():
        s = Session(engine)
        return PriceService(CardRepository(s), PriceRepository(s), FakeProvider(price=350.0), HoldingRepository(s))

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_collection_service] = collection_override
    app.dependency_overrides[get_price_service] = price_override
    return TestClient(app)


def test_add_then_list_returns_pnl():
    client = _client()
    payload = {"card": {"id": "base1-4", "name": "Charizard"}, "acquisition_cost": 120.0, "quantity": 1}
    client.post("/holdings", json=payload)
    body = client.get("/holdings").json()
    assert body["items"][0]["pnl"] == 230.0
