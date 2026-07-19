import pytest
from fastapi.testclient import TestClient

from app.deps import get_store_service
from app.main import create_application
from app.services.store_service import StoreService, clear_store_cache

from tests.test_store_service import FakeStoreProvider


@pytest.fixture(autouse=True)
def _reset_store_cache():
    clear_store_cache()
    yield
    clear_store_cache()


def _client():
    app = create_application()

    def store_service_override():
        return StoreService(FakeStoreProvider())

    app.dependency_overrides[get_store_service] = store_service_override
    return TestClient(app)


def test_get_store_returns_boosters_key():
    client = _client()
    response = client.get("/store")
    assert "boosters" in response.json()


def test_get_store_returns_only_boosters_with_priced_cards():
    client = _client()
    response = client.get("/store")
    boosters = response.json()["boosters"]
    assert [booster["set_id"] for booster in boosters] == ["set-a"]
