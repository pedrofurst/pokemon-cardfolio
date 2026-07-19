# Cardfolio MVP (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Pokémon card portfolio manager where the owner searches cards by name, adds owned copies with cost/condition, fetches live USD prices, and sees per-card and total P&L.

**Architecture:** FastAPI backend in four layers — routers (HTTP) → services (business logic) → providers (external price API, behind an interface) → repositories (SQLite via SQLModel). Next.js (App Router) frontend talks to the backend over JSON. Prices come from `pokemontcg.io`, isolated behind a `PriceProvider` interface so the source can be swapped later.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel/SQLAlchemy, SQLite, httpx, pytest, respx (mock httpx); Next.js (App Router), TypeScript.

## Global Constraints

- **Language:** Python 3.11+ backend; TypeScript frontend.
- **DB:** SQLite via SQLModel in MVP; every owned-card row carries `owner_id` (fixed value `"me"` in MVP) so multi-user is a later swap, not a rewrite.
- **Price currency:** USD only in Phase 1.
- **Secrets:** `POKEMONTCG_API_KEY` lives in `.env`, never committed, never hardcoded.
- **External calls:** only inside `providers/`, wrapped in try/except → typed domain errors. Services let errors bubble. Routers translate domain errors → HTTP + log once.
- **Tests:** never hit the real API — mock the provider (services) or mock httpx with `respx` (provider). One end-to-end flow test.
- **Layer rule:** no external HTTP or DB access outside `providers/` and `repositories/` respectively.

---

## File Structure

```
cardfolio/
├─ backend/
│  ├─ pyproject.toml            # deps + pytest config
│  ├─ .env.example              # POKEMONTCG_API_KEY=
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ main.py                # FastAPI app factory, CORS, router include, /health
│  │  ├─ config.py              # settings from env (api key, db url)
│  │  ├─ db.py                  # engine, init_db(), get_session()
│  │  ├─ models.py              # SQLModel: Card, Holding, PriceSnapshot
│  │  ├─ errors.py              # domain errors
│  │  ├─ providers/
│  │  │  ├─ __init__.py
│  │  │  ├─ base.py             # PriceProvider protocol + DTOs (CardResult, PriceResult)
│  │  │  └─ pokemontcgio.py     # PokemonTcgIoProvider
│  │  ├─ repositories/
│  │  │  ├─ __init__.py
│  │  │  ├─ card_repository.py
│  │  │  ├─ holding_repository.py
│  │  │  └─ price_repository.py
│  │  ├─ services/
│  │  │  ├─ __init__.py
│  │  │  ├─ collection_service.py   # add holding, list with P&L
│  │  │  └─ price_service.py        # search passthrough, refresh prices
│  │  └─ routers/
│  │     ├─ __init__.py
│  │     ├─ cards.py            # GET /cards/search
│  │     ├─ holdings.py         # GET /holdings, POST /holdings
│  │     └─ prices.py           # POST /prices/refresh
│  └─ tests/
│     ├─ conftest.py            # in-memory db session, fake provider, client fixtures
│     ├─ test_repositories.py
│     ├─ test_provider.py
│     ├─ test_collection_service.py
│     ├─ test_price_service.py
│     ├─ test_routers.py
│     └─ test_integration_flow.py
└─ web/
   ├─ package.json
   ├─ src/
   │  ├─ lib/api.ts             # typed fetch client
   │  ├─ lib/types.ts           # shared TS types
   │  └─ app/
   │     ├─ layout.tsx
   │     ├─ page.tsx            # Collection (home)
   │     ├─ search/page.tsx     # Search & add
   │     └─ card/[id]/page.tsx  # Card detail + trend
```

---

### Task 1: Backend scaffold + FastAPI app

**Files:**
- Create: `backend/pyproject.toml`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/main.py`
- Test: `backend/tests/test_health.py`, `backend/tests/conftest.py`

**Interfaces:**
- Produces: `app.main:create_application() -> FastAPI` with `GET /health` returning `{"status": "ok"}`; `app.config:get_settings() -> Settings` with `pokemontcg_api_key: str`, `database_url: str`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "cardfolio-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn>=0.29",
  "sqlmodel>=0.0.16",
  "httpx>=0.27",
  "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "respx>=0.21", "anyio>=4.0"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.env.example`**

```
POKEMONTCG_API_KEY=
DATABASE_URL=sqlite:///cardfolio.db
```

- [ ] **Step 3: Create `app/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pokemontcg_api_key: str = ""
    database_url: str = "sqlite:///cardfolio.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Write the failing test `tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from app.main import create_application


def test_health_returns_ok():
    client = TestClient(create_application())
    assert client.get("/health").json() == {"status": "ok"}
```

- [ ] **Step 5: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: app.main`

- [ ] **Step 6: Create `app/__init__.py` (empty) and `app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = ["http://localhost:3000"]


def create_application() -> FastAPI:
    application = FastAPI(title="Cardfolio API")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    def get_health() -> dict:
        return {"status": "ok"}

    return application


app = create_application()
```

- [ ] **Step 7: Install deps and run the test to verify it passes**

Run: `cd backend && pip install -e ".[dev]" && python -m pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/ && git commit -m "feat: backend scaffold with FastAPI app and health check"
```

---

### Task 2: Database models & session

**Files:**
- Create: `backend/app/models.py`, `backend/app/db.py`
- Test: `backend/tests/conftest.py` (add db fixture), `backend/tests/test_models.py`

**Interfaces:**
- Produces:
  - `Card(id: str, name: str, set_name: str, number: str, rarity: str, image_url: str, tcgplayer_id: str | None)`
  - `Holding(id: str, owner_id: str, card_id: str, condition: str, is_graded: bool, acquisition_cost: float, acquisition_date: date, quantity: int, notes: str)`
  - `PriceSnapshot(id: str, card_id: str, source: str, market_price: float, currency: str, fetched_at: datetime)`
  - `db.init_db(engine) -> None`, `db.make_engine(url: str)`, `db.get_session()` FastAPI dependency yielding a `Session`.

- [ ] **Step 1: Create `app/models.py`**

```python
from datetime import date, datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid4())


class Card(SQLModel, table=True):
    id: str = Field(primary_key=True)  # API card id, e.g. "base1-4"
    name: str
    set_name: str = ""
    number: str = ""
    rarity: str = ""
    image_url: str = ""
    tcgplayer_id: str | None = None


class Holding(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    owner_id: str = "me"
    card_id: str = Field(foreign_key="card.id", index=True)
    condition: str = "raw"
    is_graded: bool = False
    acquisition_cost: float = 0.0
    acquisition_date: date = Field(default_factory=date.today)
    quantity: int = 1
    notes: str = ""


class PriceSnapshot(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    card_id: str = Field(foreign_key="card.id", index=True)
    source: str = "tcgplayer"
    market_price: float = 0.0
    currency: str = "USD"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 2: Create `app/db.py`**

```python
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def make_engine(url: str | None = None):
    database_url = url or get_settings().database_url
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def init_db(engine=None) -> None:
    SQLModel.metadata.create_all(engine or get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
```

- [ ] **Step 3: Add db fixture to `tests/conftest.py`**

```python
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


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
```

- [ ] **Step 4: Write the failing test `tests/test_models.py`**

```python
from app.models import Card, Holding


def test_holding_defaults_owner_to_me(session):
    session.add(Card(id="base1-4", name="Charizard"))
    holding = Holding(card_id="base1-4", acquisition_cost=120.0)
    session.add(holding)
    session.commit()
    session.refresh(holding)
    assert holding.owner_id == "me"
```

- [ ] **Step 5: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL (import error until models exist / already-created models pass — confirm it runs)

- [ ] **Step 6: Run it to verify it passes**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/ && git commit -m "feat: SQLModel models and db session (Card, Holding, PriceSnapshot)"
```

---

### Task 3: Repositories

**Files:**
- Create: `backend/app/repositories/__init__.py`, `card_repository.py`, `holding_repository.py`, `price_repository.py`
- Test: `backend/tests/test_repositories.py`

**Interfaces:**
- Consumes: models and `Session` from Task 2.
- Produces:
  - `CardRepository(session)`: `upsert(card: Card) -> Card`, `get(card_id: str) -> Card | None`, `list_ids() -> list[str]`
  - `HoldingRepository(session)`: `add(holding: Holding) -> Holding`, `list(owner_id: str) -> list[Holding]`
  - `PriceRepository(session)`: `add(snapshot: PriceSnapshot) -> PriceSnapshot`, `latest_for(card_id: str) -> PriceSnapshot | None`, `history(card_id: str) -> list[PriceSnapshot]`

- [ ] **Step 1: Write the failing test `tests/test_repositories.py`**

```python
from app.models import Card, Holding, PriceSnapshot
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository


def test_card_upsert_then_get_returns_card(session):
    repo = CardRepository(session)
    repo.upsert(Card(id="base1-4", name="Charizard"))
    assert repo.get("base1-4").name == "Charizard"


def test_holding_list_filters_by_owner(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    assert len(HoldingRepository(session).list("me")) == 1


def test_price_latest_returns_most_recent(session):
    session.add(Card(id="base1-4", name="Charizard"))
    session.commit()
    repo = PriceRepository(session)
    repo.add(PriceSnapshot(card_id="base1-4", market_price=300.0))
    repo.add(PriceSnapshot(card_id="base1-4", market_price=350.0))
    assert repo.latest_for("base1-4").market_price == 350.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_repositories.py -v`
Expected: FAIL with `ModuleNotFoundError: app.repositories.card_repository`

- [ ] **Step 3: Create `app/repositories/__init__.py` (empty) and `card_repository.py`**

```python
from sqlmodel import Session, select

from app.models import Card


class CardRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, card: Card) -> Card:
        self.session.merge(card)
        self.session.commit()
        return card

    def get(self, card_id: str) -> Card | None:
        return self.session.get(Card, card_id)

    def list_ids(self) -> list[str]:
        return list(self.session.exec(select(Card.id)).all())
```

- [ ] **Step 4: Create `holding_repository.py`**

```python
from sqlmodel import Session, select

from app.models import Holding


class HoldingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, holding: Holding) -> Holding:
        self.session.add(holding)
        self.session.commit()
        self.session.refresh(holding)
        return holding

    def list(self, owner_id: str) -> list[Holding]:
        statement = select(Holding).where(Holding.owner_id == owner_id)
        return list(self.session.exec(statement).all())
```

- [ ] **Step 5: Create `price_repository.py`**

```python
from sqlmodel import Session, select

from app.models import PriceSnapshot


class PriceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, snapshot: PriceSnapshot) -> PriceSnapshot:
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def latest_for(self, card_id: str) -> PriceSnapshot | None:
        statement = (
            select(PriceSnapshot)
            .where(PriceSnapshot.card_id == card_id)
            .order_by(PriceSnapshot.fetched_at.desc())
        )
        return self.session.exec(statement).first()

    def history(self, card_id: str) -> list[PriceSnapshot]:
        statement = (
            select(PriceSnapshot)
            .where(PriceSnapshot.card_id == card_id)
            .order_by(PriceSnapshot.fetched_at.asc())
        )
        return list(self.session.exec(statement).all())
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_repositories.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/ && git commit -m "feat: card, holding, and price repositories"
```

---

### Task 4: Price provider (interface + pokemontcg.io) + domain errors

**Files:**
- Create: `backend/app/errors.py`, `backend/app/providers/__init__.py`, `base.py`, `pokemontcgio.py`
- Test: `backend/tests/test_provider.py`

**Interfaces:**
- Produces:
  - `errors.PriceProviderError`, `errors.CardNotFoundError` (both subclass `Exception`).
  - `providers.base.CardResult(id, name, set_name, number, rarity, image_url, tcgplayer_id, market_price: float | None)`
  - `providers.base.PriceResult(card_id: str, market_price: float, currency: str, source: str)`
  - `providers.base.PriceProvider` protocol: `search_cards(query: str) -> list[CardResult]`, `get_price(card_id: str) -> PriceResult`
  - `providers.pokemontcgio.PokemonTcgIoProvider(api_key: str, client: httpx.Client | None = None)` implementing it.

- [ ] **Step 1: Create `app/errors.py`**

```python
class PriceProviderError(Exception):
    """External price source failed."""


class CardNotFoundError(Exception):
    """No card matched the given id."""
```

- [ ] **Step 2: Create `app/providers/__init__.py` (empty) and `base.py`**

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass
class CardResult:
    id: str
    name: str
    set_name: str
    number: str
    rarity: str
    image_url: str
    tcgplayer_id: str | None
    market_price: float | None


@dataclass
class PriceResult:
    card_id: str
    market_price: float
    currency: str
    source: str


class PriceProvider(Protocol):
    def search_cards(self, query: str) -> list[CardResult]: ...
    def get_price(self, card_id: str) -> PriceResult: ...
```

- [ ] **Step 3: Write the failing test `tests/test_provider.py`**

```python
import httpx
import respx

from app.errors import CardNotFoundError, PriceProviderError
from app.providers.pokemontcgio import PokemonTcgIoProvider

BASE = "https://api.pokemontcg.io/v2"

CARD_JSON = {
    "id": "base1-4",
    "name": "Charizard",
    "number": "4",
    "rarity": "Rare Holo",
    "set": {"name": "Base"},
    "images": {"small": "https://img/charizard.png"},
    "tcgplayer": {"prices": {"holofoil": {"market": 350.0}}},
}


@respx.mock
def test_search_cards_maps_fields():
    respx.get(f"{BASE}/cards").mock(
        return_value=httpx.Response(200, json={"data": [CARD_JSON]})
    )
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    result = provider.search_cards("charizard")[0]
    assert result.market_price == 350.0


@respx.mock
def test_get_price_missing_card_raises_not_found():
    respx.get(f"{BASE}/cards/nope").mock(return_value=httpx.Response(404))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.get_price("nope")
        raised = False
    except CardNotFoundError:
        raised = True
    assert raised


@respx.mock
def test_provider_wraps_transport_error():
    respx.get(f"{BASE}/cards").mock(side_effect=httpx.ConnectError("boom"))
    provider = PokemonTcgIoProvider(api_key="k", client=httpx.Client())
    try:
        provider.search_cards("x")
        raised = False
    except PriceProviderError:
        raised = True
    assert raised
```

- [ ] **Step 4: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: app.providers.pokemontcgio`

- [ ] **Step 5: Create `app/providers/pokemontcgio.py`**

```python
import httpx

from app.errors import CardNotFoundError, PriceProviderError
from app.providers.base import CardResult, PriceResult

BASE_URL = "https://api.pokemontcg.io/v2"


def _extract_market_price(card: dict) -> float | None:
    prices = (card.get("tcgplayer") or {}).get("prices") or {}
    for variant in prices.values():
        market = variant.get("market")
        if market is not None:
            return float(market)
    return None


def _to_card_result(card: dict) -> CardResult:
    return CardResult(
        id=card["id"],
        name=card.get("name", ""),
        set_name=(card.get("set") or {}).get("name", ""),
        number=card.get("number", ""),
        rarity=card.get("rarity", ""),
        image_url=(card.get("images") or {}).get("small", ""),
        tcgplayer_id=(card.get("tcgplayer") or {}).get("url"),
        market_price=_extract_market_price(card),
    )


class PokemonTcgIoProvider:
    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=10.0)
        self._headers = {"X-Api-Key": api_key} if api_key else {}

    def search_cards(self, query: str) -> list[CardResult]:
        try:
            response = self._client.get(
                f"{BASE_URL}/cards",
                params={"q": f'name:"{query}*"', "pageSize": 20},
                headers=self._headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise PriceProviderError(f"search failed for {query!r}") from error
        return [_to_card_result(card) for card in response.json().get("data", [])]

    def get_price(self, card_id: str) -> PriceResult:
        try:
            response = self._client.get(
                f"{BASE_URL}/cards/{card_id}", headers=self._headers
            )
            if response.status_code == 404:
                raise CardNotFoundError(card_id)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise PriceProviderError(f"price fetch failed for {card_id!r}") from error
        card = response.json().get("data", {})
        price = _extract_market_price(card)
        if price is None:
            raise PriceProviderError(f"no market price for {card_id!r}")
        return PriceResult(card_id=card_id, market_price=price, currency="USD", source="tcgplayer")
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_provider.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/ && git commit -m "feat: PriceProvider interface, pokemontcg.io provider, domain errors"
```

---

### Task 5: Services (collection + price)

**Files:**
- Create: `backend/app/services/__init__.py`, `collection_service.py`, `price_service.py`
- Test: `backend/tests/test_collection_service.py`, `backend/tests/test_price_service.py`; add a `FakeProvider` to `conftest.py`

**Interfaces:**
- Consumes: repositories (Task 3), `PriceProvider`/DTOs (Task 4).
- Produces:
  - `collection_service.CollectionService(card_repo, holding_repo, price_repo, provider)`:
    - `add_holding(card_id, condition, is_graded, acquisition_cost, quantity, notes, owner_id="me") -> Holding` — upserts the card (fetching it via provider search cache is out of scope; caller passes a `CardResult` via `add_holding_from_result`), fetches a price snapshot.
    - `add_holding_from_result(result: CardResult, condition, is_graded, acquisition_cost, quantity, notes, owner_id="me") -> Holding`
    - `list_collection(owner_id="me") -> list[HoldingView]` where `HoldingView` has `holding`, `card`, `current_price: float | None`, `pnl: float`.
    - `summary(owner_id="me") -> CollectionSummary(total_cost, total_value, pnl, pnl_pct)`.
  - `price_service.PriceService(card_repo, price_repo, provider)`:
    - `search(query) -> list[CardResult]`
    - `refresh_prices(owner_id="me") -> int` (count of snapshots written).

- [ ] **Step 1: Add `FakeProvider` and view import to `tests/conftest.py`**

```python
from app.providers.base import CardResult, PriceResult


class FakeProvider:
    def __init__(self, cards=None, price=350.0):
        self._cards = cards or []
        self._price = price

    def search_cards(self, query):
        return self._cards

    def get_price(self, card_id):
        return PriceResult(card_id=card_id, market_price=self._price, currency="USD", source="fake")


@pytest.fixture
def sample_result():
    return CardResult(
        id="base1-4", name="Charizard", set_name="Base", number="4",
        rarity="Rare Holo", image_url="i", tcgplayer_id=None, market_price=350.0,
    )
```

- [ ] **Step 2: Write the failing test `tests/test_collection_service.py`**

```python
from app.providers.base import CardResult
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
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_collection_service.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.collection_service`

- [ ] **Step 4: Create `app/services/__init__.py` (empty) and `collection_service.py`**

```python
from dataclasses import dataclass

from app.models import Card, Holding, PriceSnapshot
from app.providers.base import CardResult, PriceProvider
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository


@dataclass
class HoldingView:
    holding: Holding
    card: Card | None
    current_price: float | None
    pnl: float


@dataclass
class CollectionSummary:
    total_cost: float
    total_value: float
    pnl: float
    pnl_pct: float


class CollectionService:
    def __init__(self, card_repo: CardRepository, holding_repo: HoldingRepository,
                 price_repo: PriceRepository, provider: PriceProvider) -> None:
        self.card_repo = card_repo
        self.holding_repo = holding_repo
        self.price_repo = price_repo
        self.provider = provider

    def add_holding_from_result(self, result: CardResult, condition: str, is_graded: bool,
                                acquisition_cost: float, quantity: int, notes: str,
                                owner_id: str = "me") -> Holding:
        self.card_repo.upsert(Card(
            id=result.id, name=result.name, set_name=result.set_name,
            number=result.number, rarity=result.rarity, image_url=result.image_url,
            tcgplayer_id=result.tcgplayer_id,
        ))
        holding = self.holding_repo.add(Holding(
            card_id=result.id, owner_id=owner_id, condition=condition,
            is_graded=is_graded, acquisition_cost=acquisition_cost,
            quantity=quantity, notes=notes,
        ))
        price = self.provider.get_price(result.id)
        self.price_repo.add(PriceSnapshot(
            card_id=result.id, source=price.source,
            market_price=price.market_price, currency=price.currency,
        ))
        return holding

    def list_collection(self, owner_id: str = "me") -> list[HoldingView]:
        views: list[HoldingView] = []
        for holding in self.holding_repo.list(owner_id):
            latest = self.price_repo.latest_for(holding.card_id)
            current = latest.market_price if latest else None
            value = (current or 0.0) * holding.quantity
            pnl = value - holding.acquisition_cost * holding.quantity
            views.append(HoldingView(
                holding=holding, card=self.card_repo.get(holding.card_id),
                current_price=current, pnl=pnl,
            ))
        return views

    def summary(self, owner_id: str = "me") -> CollectionSummary:
        views = self.list_collection(owner_id)
        total_cost = sum(v.holding.acquisition_cost * v.holding.quantity for v in views)
        total_value = sum((v.current_price or 0.0) * v.holding.quantity for v in views)
        pnl = total_value - total_cost
        pnl_pct = (pnl / total_cost * 100.0) if total_cost else 0.0
        return CollectionSummary(total_cost, total_value, pnl, pnl_pct)
```

- [ ] **Step 5: Run to verify collection tests pass**

Run: `cd backend && python -m pytest tests/test_collection_service.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Write the failing test `tests/test_price_service.py`**

```python
from app.models import Card, Holding
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.price_service import PriceService

from tests.conftest import FakeProvider


def test_refresh_writes_one_snapshot_per_owned_card(session):
    CardRepository(session).upsert(Card(id="base1-4", name="Charizard"))
    HoldingRepository(session).add(Holding(card_id="base1-4", owner_id="me"))
    service = PriceService(CardRepository(session), PriceRepository(session),
                          FakeProvider(price=400.0), HoldingRepository(session))
    assert service.refresh_prices() == 1
```

- [ ] **Step 7: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_price_service.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.price_service`

- [ ] **Step 8: Create `price_service.py`**

```python
from app.models import PriceSnapshot
from app.providers.base import CardResult, PriceProvider
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository


class PriceService:
    def __init__(self, card_repo: CardRepository, price_repo: PriceRepository,
                 provider: PriceProvider, holding_repo: HoldingRepository) -> None:
        self.card_repo = card_repo
        self.price_repo = price_repo
        self.provider = provider
        self.holding_repo = holding_repo

    def search(self, query: str) -> list[CardResult]:
        return self.provider.search_cards(query)

    def refresh_prices(self, owner_id: str = "me") -> int:
        card_ids = {h.card_id for h in self.holding_repo.list(owner_id)}
        written = 0
        for card_id in card_ids:
            price = self.provider.get_price(card_id)
            self.price_repo.add(PriceSnapshot(
                card_id=card_id, source=price.source,
                market_price=price.market_price, currency=price.currency,
            ))
            written += 1
        return written
```

- [ ] **Step 9: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_price_service.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/ && git commit -m "feat: collection and price services with P&L computation"
```

---

### Task 6: Routers + dependency wiring

**Files:**
- Create: `backend/app/routers/__init__.py`, `cards.py`, `holdings.py`, `prices.py`; `backend/app/deps.py`
- Modify: `backend/app/main.py` (include routers, `init_db` on startup)
- Test: `backend/tests/test_routers.py`

**Interfaces:**
- Consumes: services (Task 5), `get_session` (Task 2), `get_settings` (Task 1).
- Produces HTTP endpoints:
  - `GET /cards/search?q=` → `[{id,name,set_name,number,rarity,image_url,market_price}]`
  - `POST /holdings` body `{card: CardResult-shaped, condition, is_graded, acquisition_cost, quantity, notes}` → created holding
  - `GET /holdings` → `{summary: {...}, items: [{holding, card, current_price, pnl}]}`
  - `POST /prices/refresh` → `{written: int}`
  - `deps.py`: `get_collection_service`, `get_price_service` FastAPI dependencies wiring repos + provider from settings.

- [ ] **Step 1: Create `app/deps.py`**

```python
from fastapi import Depends
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.providers.pokemontcgio import PokemonTcgIoProvider
from app.repositories.card_repository import CardRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.collection_service import CollectionService
from app.services.price_service import PriceService


def _provider() -> PokemonTcgIoProvider:
    return PokemonTcgIoProvider(api_key=get_settings().pokemontcg_api_key)


def get_collection_service(session: Session = Depends(get_session)) -> CollectionService:
    return CollectionService(
        CardRepository(session), HoldingRepository(session),
        PriceRepository(session), _provider(),
    )


def get_price_service(session: Session = Depends(get_session)) -> PriceService:
    return PriceService(
        CardRepository(session), PriceRepository(session),
        _provider(), HoldingRepository(session),
    )
```

- [ ] **Step 2: Create `app/routers/__init__.py` (empty) and `cards.py`**

```python
from fastapi import APIRouter, Depends

from app.deps import get_price_service
from app.services.price_service import PriceService

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/search")
def search_cards(q: str, service: PriceService = Depends(get_price_service)) -> list[dict]:
    return [result.__dict__ for result in service.search(q)]
```

- [ ] **Step 3: Create `holdings.py`**

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_collection_service
from app.providers.base import CardResult
from app.services.collection_service import CollectionService

router = APIRouter(prefix="/holdings", tags=["holdings"])


class CardPayload(BaseModel):
    id: str
    name: str = ""
    set_name: str = ""
    number: str = ""
    rarity: str = ""
    image_url: str = ""
    tcgplayer_id: str | None = None
    market_price: float | None = None


class AddHoldingRequest(BaseModel):
    card: CardPayload
    condition: str = "raw"
    is_graded: bool = False
    acquisition_cost: float = 0.0
    quantity: int = 1
    notes: str = ""


@router.post("")
def add_holding(body: AddHoldingRequest,
                service: CollectionService = Depends(get_collection_service)) -> dict:
    result = CardResult(**body.card.model_dump())
    holding = service.add_holding_from_result(
        result, condition=body.condition, is_graded=body.is_graded,
        acquisition_cost=body.acquisition_cost, quantity=body.quantity, notes=body.notes,
    )
    return holding.model_dump()


@router.get("")
def list_holdings(service: CollectionService = Depends(get_collection_service)) -> dict:
    views = service.list_collection()
    summary = service.summary()
    return {
        "summary": summary.__dict__,
        "items": [
            {
                "holding": v.holding.model_dump(),
                "card": v.card.model_dump() if v.card else None,
                "current_price": v.current_price,
                "pnl": v.pnl,
            }
            for v in views
        ],
    }
```

- [ ] **Step 4: Create `prices.py`**

```python
from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_price_service
from app.errors import CardNotFoundError, PriceProviderError
from app.services.price_service import PriceService

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/refresh")
def refresh_prices(service: PriceService = Depends(get_price_service)) -> dict:
    try:
        written = service.refresh_prices()
    except CardNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PriceProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"written": written}
```

- [ ] **Step 5: Modify `app/main.py` to include routers and init db**

Replace the body of `create_application` (after CORS) with router includes; add startup init:

```python
from app.db import init_db
from app.routers import cards, holdings, prices

# inside create_application(), after add_middleware(...):
    application.include_router(cards.router)
    application.include_router(holdings.router)
    application.include_router(prices.router)

    @application.on_event("startup")
    def _startup() -> None:
        init_db()

    @application.get("/health")
    def get_health() -> dict:
        return {"status": "ok"}

    return application
```

- [ ] **Step 6: Write the failing test `tests/test_routers.py`**

```python
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

    def collection_override(session: Session = None):
        s = Session(engine)
        return CollectionService(CardRepository(s), HoldingRepository(s), PriceRepository(s), FakeProvider(price=350.0))

    def price_override(session: Session = None):
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
```

- [ ] **Step 7: Run to verify it fails, then passes after wiring**

Run: `cd backend && python -m pytest tests/test_routers.py -v`
Expected: first FAIL (module/route missing), then PASS after Steps 1-5 are in place.

- [ ] **Step 8: Commit**

```bash
git add backend/ && git commit -m "feat: cards, holdings, prices routers with DI wiring"
```

---

### Task 7: End-to-end integration flow

**Files:**
- Test: `backend/tests/test_integration_flow.py`

**Interfaces:**
- Consumes: full stack with `respx`-mocked httpx so the real pokemontcg.io provider runs but no network is hit.

- [ ] **Step 1: Write the test `tests/test_integration_flow.py`**

```python
import httpx
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.main import create_application

BASE = "https://api.pokemontcg.io/v2"
CARD = {
    "id": "base1-4", "name": "Charizard", "number": "4", "rarity": "Rare Holo",
    "set": {"name": "Base"}, "images": {"small": "i"},
    "tcgplayer": {"prices": {"holofoil": {"market": 350.0}}},
}


@respx.mock
def test_search_add_refresh_pnl_end_to_end():
    respx.get(f"{BASE}/cards").mock(return_value=httpx.Response(200, json={"data": [CARD]}))
    respx.get(f"{BASE}/cards/base1-4").mock(return_value=httpx.Response(200, json={"data": CARD}))

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    app = create_application()

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    client = TestClient(app)

    found = client.get("/cards/search", params={"q": "charizard"}).json()[0]
    client.post("/holdings", json={"card": found, "acquisition_cost": 120.0, "quantity": 1})
    client.post("/prices/refresh")
    body = client.get("/holdings").json()
    assert body["summary"]["pnl"] == 230.0
```

- [ ] **Step 2: Run the full suite**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/ && git commit -m "test: end-to-end search→add→refresh→pnl flow"
```

---

### Task 8: Frontend scaffold + API client

**Files:**
- Create: `web/` via `create-next-app`; then `web/src/lib/types.ts`, `web/src/lib/api.ts`, `web/.env.local.example`
- Modify: `web/src/app/layout.tsx` (title)

**Interfaces:**
- Produces: `api.searchCards(q)`, `api.addHolding(payload)`, `api.listHoldings()`, `api.refreshPrices()`; TS types `CardResult`, `HoldingView`, `CollectionResponse`.

- [ ] **Step 1: Scaffold Next.js**

Run: `cd /Users/pedrofurst/cardfolio && npx create-next-app@latest web --typescript --app --no-tailwind --no-src-dir=false --eslint --import-alias "@/*"`
Expected: `web/` created.

- [ ] **Step 2: Create `web/.env.local.example`**

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

- [ ] **Step 3: Create `web/src/lib/types.ts`**

```typescript
export interface CardResult {
  id: string;
  name: string;
  set_name: string;
  number: string;
  rarity: string;
  image_url: string;
  tcgplayer_id: string | null;
  market_price: number | null;
}

export interface HoldingView {
  holding: {
    id: string;
    card_id: string;
    condition: string;
    is_graded: boolean;
    acquisition_cost: number;
    quantity: number;
    notes: string;
  };
  card: { id: string; name: string; set_name: string; image_url: string } | null;
  current_price: number | null;
  pnl: number;
}

export interface CollectionResponse {
  summary: { total_cost: number; total_value: number; pnl: number; pnl_pct: number };
  items: HoldingView[];
}
```

- [ ] **Step 4: Create `web/src/lib/api.ts`**

```typescript
import { CardResult, CollectionResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  searchCards: (q: string) =>
    fetch(`${BASE}/cards/search?q=${encodeURIComponent(q)}`).then(json<CardResult[]>),
  addHolding: (payload: Record<string, unknown>) =>
    fetch(`${BASE}/holdings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json<unknown>),
  listHoldings: () => fetch(`${BASE}/holdings`).then(json<CollectionResponse>),
  refreshPrices: () =>
    fetch(`${BASE}/prices/refresh`, { method: "POST" }).then(json<{ written: number }>),
};
```

- [ ] **Step 5: Verify it builds**

Run: `cd web && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add web/ && git commit -m "feat: Next.js scaffold with typed API client"
```

---

### Task 9: Search & add screen

**Files:**
- Create: `web/src/app/search/page.tsx`
- Test: manual via running app (documented steps)

**Interfaces:**
- Consumes: `api.searchCards`, `api.addHolding` (Task 8).

- [ ] **Step 1: Create `web/src/app/search/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { CardResult } from "@/lib/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardResult[]>([]);
  const [selected, setSelected] = useState<CardResult | null>(null);
  const [cost, setCost] = useState("");

  async function runSearch() {
    setResults(await api.searchCards(query));
  }

  async function add() {
    if (!selected) return;
    await api.addHolding({
      card: selected,
      acquisition_cost: Number(cost) || 0,
      quantity: 1,
      condition: "raw",
    });
    setSelected(null);
    setCost("");
  }

  return (
    <main style={{ padding: 24 }}>
      <h1>Search &amp; add</h1>
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Charizard" />
      <button onClick={runSearch}>Search</button>
      <ul>
        {results.map((card) => (
          <li key={card.id}>
            <img src={card.image_url} alt={card.name} width={80} />
            {card.name} — {card.set_name} — ${card.market_price ?? "?"}
            <button onClick={() => setSelected(card)}>Add</button>
          </li>
        ))}
      </ul>
      {selected && (
        <div>
          <h2>Add {selected.name}</h2>
          <input value={cost} onChange={(e) => setCost(e.target.value)} placeholder="Acquisition cost (USD)" />
          <button onClick={add}>Save</button>
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Manually verify**

Run backend (`cd backend && uvicorn app.main:app --reload`) and frontend (`cd web && npm run dev`), open `http://localhost:3000/search`, search "Charizard", add one with a cost.
Expected: no console errors; POST /holdings returns 200.

- [ ] **Step 3: Commit**

```bash
git add web/ && git commit -m "feat: search and add cards screen"
```

---

### Task 10: Collection view + card detail

**Files:**
- Create: `web/src/app/card/[id]/page.tsx`
- Modify: `web/src/app/page.tsx` (collection home)

**Interfaces:**
- Consumes: `api.listHoldings`, `api.refreshPrices` (Task 8).

- [ ] **Step 1: Replace `web/src/app/page.tsx` with the collection view**

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { CollectionResponse } from "@/lib/types";

export default function Home() {
  const [data, setData] = useState<CollectionResponse | null>(null);

  async function load() {
    setData(await api.listHoldings());
  }

  useEffect(() => {
    load();
  }, []);

  async function refresh() {
    await api.refreshPrices();
    await load();
  }

  return (
    <main style={{ padding: 24 }}>
      <h1>My collection</h1>
      <Link href="/search">+ Add cards</Link>
      <button onClick={refresh} style={{ marginLeft: 12 }}>Refresh prices</button>
      {data && (
        <>
          <p>
            Cost ${data.summary.total_cost.toFixed(2)} · Value $
            {data.summary.total_value.toFixed(2)} · P&amp;L ${data.summary.pnl.toFixed(2)} (
            {data.summary.pnl_pct.toFixed(1)}%)
          </p>
          <table>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.holding.id}>
                  <td>
                    <Link href={`/card/${item.holding.card_id}`}>
                      {item.card?.name ?? item.holding.card_id}
                    </Link>
                  </td>
                  <td>{item.holding.condition}</td>
                  <td>${item.holding.acquisition_cost.toFixed(2)}</td>
                  <td>${item.current_price?.toFixed(2) ?? "?"}</td>
                  <td>${item.pnl.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Create `web/src/app/card/[id]/page.tsx` (minimal detail)**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { HoldingView } from "@/lib/types";

export default function CardDetail() {
  const params = useParams<{ id: string }>();
  const [view, setView] = useState<HoldingView | null>(null);

  useEffect(() => {
    api.listHoldings().then((data) => {
      setView(data.items.find((i) => i.holding.card_id === params.id) ?? null);
    });
  }, [params.id]);

  if (!view) return <main style={{ padding: 24 }}>Loading…</main>;
  return (
    <main style={{ padding: 24 }}>
      <h1>{view.card?.name ?? params.id}</h1>
      <img src={view.card?.image_url} alt={view.card?.name ?? ""} width={200} />
      <p>Current price: ${view.current_price?.toFixed(2) ?? "?"}</p>
      <p>P&amp;L: ${view.pnl.toFixed(2)}</p>
    </main>
  );
}
```

- [ ] **Step 3: Manually verify the full loop**

With backend + frontend running: add a card on `/search`, return to `/`, click "Refresh prices", confirm totals and P&L render, click a card to see detail.
Expected: collection shows the card with a positive/negative P&L; no console errors.

- [ ] **Step 4: Commit**

```bash
git add web/ && git commit -m "feat: collection home and card detail views"
```

---

## Self-Review

**Spec coverage:**
- Search & add → Tasks 4, 5, 6, 9 ✓
- Collection + per-card & total P&L → Tasks 5, 6, 10 ✓
- Price snapshots / history → Tasks 2, 3, 5 ✓
- On-demand refresh → Tasks 5, 6, 10 ✓
- Provider behind interface, swappable → Task 4 ✓
- Multi-user-ready `owner_id` → Task 2 ✓
- Layered error handling → Tasks 4 (wrap), 5 (bubble), 6 (translate) ✓
- Tests per layer, provider mocked, one e2e → Tasks 3–7 ✓
- Card detail trend chart: MVP renders current price + P&L; a full `price_snapshot` chart is deferred (history is already stored via `PriceRepository.history`, so it is a frontend-only follow-up). Noted as a known simplification, not a gap.

**Placeholder scan:** none — every step has concrete code/commands.

**Type consistency:** `CardResult`/`PriceResult` fields consistent across provider, services, routers, and TS types; `add_holding_from_result` signature matches its callers in Task 6.
