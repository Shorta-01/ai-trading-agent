from portfolio_outlook_worker.health import get_worker_health


def test_worker_health() -> None:
    response = get_worker_health()
    assert response.model_dump() == {
        "status": "ok",
        "service": "worker",
        "mode": "paper-only",
    }
