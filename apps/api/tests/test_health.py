from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api", "mode": "paper-only"}


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "name": "Portfolio Outlook Manager API",
        "version": "0.1.0",
        "mode": "paper-only",
    }
