from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Per V1 §21.1 the health response no longer hard-codes a 'paper-only'
    mode; the IBKR account decides paper/live and the dashboard surfaces it."""

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "name": "Portfolio Outlook Manager API",
        "version": "0.1.0",
    }
