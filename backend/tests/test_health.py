from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == get_settings().app_name