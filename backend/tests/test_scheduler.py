from fastapi.testclient import TestClient

import app.main as main_module
from app.config import get_settings
from app.main import create_application


def test_settings_enable_scheduler_is_false_in_test_env():
    assert get_settings().enable_scheduler is False


def test_settings_warm_store_on_startup_is_false_in_test_env():
    assert get_settings().warm_store_on_startup is False


def test_app_starts_and_serves_requests_with_scheduler_disabled():
    with TestClient(create_application()) as client:
        response = client.get("/health")
        assert response.status_code == 200


def test_app_startup_does_not_spawn_a_store_warm_thread_under_tests(monkeypatch):
    def _fail_if_called():
        raise AssertionError("store warm thread must not start while warm_store_on_startup=False")

    monkeypatch.setattr(main_module, "_start_store_warm_thread_if_needed", _fail_if_called)
    with TestClient(create_application()) as client:
        response = client.get("/health")
    assert response.status_code == 200
