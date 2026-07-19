from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_application


def test_settings_enable_scheduler_is_false_in_test_env():
    assert get_settings().enable_scheduler is False


def test_app_starts_and_serves_requests_with_scheduler_disabled():
    with TestClient(create_application()) as client:
        response = client.get("/health")
        assert response.status_code == 200
