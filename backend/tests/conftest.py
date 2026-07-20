import os

# Must run before `app.config` (and anything importing it) is loaded, so the
# very first Settings() built during the test session already has the
# scheduler disabled — no background thread, no network, ever, in tests.
os.environ["ENABLE_SCHEDULER"] = "0"
# Same reasoning for the store cache warm-up thread: never spawn it, never
# touch the network, during tests.
os.environ["WARM_STORE_ON_STARTUP"] = "0"
# Never let tests reach a real Redis. deps.py builds its cache at import time,
# so a developer with Redis running would otherwise get cached search results
# served past the respx mocks — tests that pass or fail depending on whether a
# container happens to be up.
os.environ["REDIS_URL"] = ""
# Keep any real (non-overridden) lifespan/db access confined to memory so
# tests never write a stray cardfolio.db file to disk.
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.config import get_settings
from app.providers.base import CardResult, PriceResult
from app.services import store_service as store_service_module

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _isolate_store_disk_cache(tmp_path, monkeypatch):
    # Every test gets its own throwaway disk-cache path so no test ever
    # reads or writes the real backend/.store_cache.json file.
    monkeypatch.setattr(
        store_service_module, "_CACHE_FILE_PATH", tmp_path / "store_cache.json"
    )


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class FakeProvider:
    def __init__(self, cards=None, price=350.0, direct_low=300.0):
        self._cards = cards or []
        self._price = price
        self._direct_low = direct_low

    def search_cards(self, query):
        return self._cards

    def get_price(self, card_id):
        return PriceResult(
            card_id=card_id, market_price=self._price, currency="USD", source="fake",
            direct_low=self._direct_low,
        )


@pytest.fixture
def sample_result():
    return CardResult(
        id="base1-4", name="Charizard", set_name="Base", number="4",
        rarity="Rare Holo", image_url="i", tcgplayer_id=None, market_price=350.0,
    )
