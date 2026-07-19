from fastapi.testclient import TestClient

from app.main import create_application


def test_health_returns_ok():
    client = TestClient(create_application())
    assert client.get("/health").json() == {"status": "ok"}
