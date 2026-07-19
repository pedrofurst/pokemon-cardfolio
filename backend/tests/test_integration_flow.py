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
