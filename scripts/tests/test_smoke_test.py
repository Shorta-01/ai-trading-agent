"""Tests for the cold-start smoke-test CLI.

The script reads only from existing HTTP endpoints; the tests stub
httpx.Client + the JSON each endpoint returns so we exercise the
verdict logic without any live API.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# scripts/ isn't installed as a package; import the script module directly.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import smoke_test  # noqa: E402


class _StubResponse:
    def __init__(self, *, status_code: int = 200, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = str(self._payload)

    def json(self) -> Any:
        return self._payload


class _StubClient:
    def __init__(self, *, responses: dict[str, _StubResponse]) -> None:
        self._responses = responses
        self.calls: list[str] = []

    def get(self, path: str) -> _StubResponse:
        self.calls.append(path)
        if path not in self._responses:
            raise RuntimeError(f"unexpected path in test: {path}")
        return self._responses[path]


def _client(responses: dict[str, _StubResponse]) -> _StubClient:
    return _StubClient(responses=responses)


# ---- per-check happy paths ------------------------------------------------


def test_check_api_health_ok() -> None:
    client = _client(
        {"/health": _StubResponse(payload={"status": "ok", "service": "api"})}
    )
    result = smoke_test.check_api_health(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_OK
    assert "API bereikbaar" in result.summary_nl


def test_check_storage_all_green() -> None:
    client = _client(
        {
            "/storage/status/online": _StubResponse(
                payload={
                    "configured": True,
                    "connected": True,
                    "safe_to_write": True,
                    "writes_status_nl": "ok",
                }
            )
        }
    )
    result = smoke_test.check_storage(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_OK


def test_check_scheduler_ok_when_enabled_and_no_error() -> None:
    client = _client(
        {
            "/scheduler/v127/status": _StubResponse(
                payload={
                    "enabled": True,
                    "last_run_at": "2026-05-31T06:00:00Z",
                    "last_run_type": "pre_briefing",
                    "last_outcome": "success",
                    "next_runs": ["2026-06-01T06:00:00Z"],
                }
            )
        }
    )
    result = smoke_test.check_scheduler(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_OK
    assert "Scheduler actief" in result.summary_nl


def test_check_ibkr_sync_ok_when_completed() -> None:
    client = _client(
        {
            "/ibkr/sync/status": _StubResponse(
                payload={
                    "configured": True,
                    "status": "completed",
                    "positions_count": 7,
                    "account_mode": "paper",
                }
            )
        }
    )
    result = smoke_test.check_ibkr_sync(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_OK
    assert "7 posities" in result.summary_nl


def test_check_system_events_ok_when_none_active() -> None:
    client = _client(
        {
            "/system/events/active": _StubResponse(
                payload={"active_count": 0, "events": []}
            )
        }
    )
    result = smoke_test.check_system_events(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_OK


# ---- failure / warn paths -------------------------------------------------


def test_check_api_health_fail_on_transport_error() -> None:
    class _Boom:
        def get(self, _path):
            raise RuntimeError("connection refused")

    result = smoke_test.check_api_health(_Boom())  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_FAIL
    assert "niet bereikbaar" in result.summary_nl


def test_check_storage_fail_when_connected_but_not_writable() -> None:
    client = _client(
        {
            "/storage/status/online": _StubResponse(
                payload={
                    "configured": True,
                    "connected": True,
                    "safe_to_write": False,
                    "writes_status_nl": "migrations behind",
                }
            )
        }
    )
    result = smoke_test.check_storage(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_FAIL
    assert "geblokkeerd" in result.summary_nl


def test_check_storage_warn_when_not_configured() -> None:
    client = _client(
        {
            "/storage/status/online": _StubResponse(
                payload={
                    "configured": False,
                    "connected": False,
                    "safe_to_write": False,
                }
            )
        }
    )
    result = smoke_test.check_storage(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_WARN


def test_check_scheduler_warn_when_no_heartbeat_yet() -> None:
    client = _client(
        {
            "/scheduler/v127/status": _StubResponse(
                payload={"enabled": False, "next_runs": []}
            )
        }
    )
    result = smoke_test.check_scheduler(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_WARN


def test_check_scheduler_fail_when_last_outcome_is_error() -> None:
    client = _client(
        {
            "/scheduler/v127/status": _StubResponse(
                payload={
                    "enabled": True,
                    "last_run_type": "pre_briefing",
                    "last_outcome": "error",
                }
            )
        }
    )
    result = smoke_test.check_scheduler(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_FAIL


def test_check_ibkr_sync_warn_when_not_configured() -> None:
    client = _client(
        {"/ibkr/sync/status": _StubResponse(payload={"configured": False})}
    )
    result = smoke_test.check_ibkr_sync(client)  # type: ignore[arg-type]
    # IBKR-not-configured is a warn, not a fail — a non-IBKR install is
    # legitimate (e.g. operator just trialling the dashboard).
    assert result.status == smoke_test.STATUS_WARN


def test_check_system_events_fail_when_blocking_event_active() -> None:
    client = _client(
        {
            "/system/events/active": _StubResponse(
                payload={
                    "active_count": 1,
                    "events": [
                        {
                            "system_event_id": "evt-1",
                            "blocks_writes": True,
                            "title_nl": "Storage write blocked",
                        }
                    ],
                }
            )
        }
    )
    result = smoke_test.check_system_events(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_FAIL
    assert "blokkerend" in result.summary_nl


def test_check_system_events_warn_when_non_blocking_event() -> None:
    client = _client(
        {
            "/system/events/active": _StubResponse(
                payload={
                    "active_count": 1,
                    "events": [
                        {
                            "system_event_id": "evt-2",
                            "blocks_writes": False,
                            "blocks_suggestions": False,
                            "blocks_ai_explanation": False,
                            "title_nl": "Heads-up",
                        }
                    ],
                }
            )
        }
    )
    result = smoke_test.check_system_events(client)  # type: ignore[arg-type]
    assert result.status == smoke_test.STATUS_WARN


# ---- overall verdict logic ------------------------------------------------


def _all_green_responses() -> dict[str, _StubResponse]:
    return {
        "/health": _StubResponse(payload={"status": "ok", "service": "api"}),
        "/storage/status/online": _StubResponse(
            payload={
                "configured": True,
                "connected": True,
                "safe_to_write": True,
            }
        ),
        "/scheduler/v127/status": _StubResponse(
            payload={
                "enabled": True,
                "last_outcome": "success",
                "next_runs": [],
            }
        ),
        "/ibkr/sync/status": _StubResponse(
            payload={
                "configured": True,
                "status": "completed",
                "account_mode": "paper",
                "positions_count": 0,
            }
        ),
        "/system/events/active": _StubResponse(
            payload={"active_count": 0, "events": []}
        ),
    }


def test_run_smoke_test_returns_zero_when_all_green(monkeypatch, capsys) -> None:
    responses = _all_green_responses()

    class _CMClient:
        def __init__(self, *_a, **_k):
            self._inner = _StubClient(responses=responses)

        def __enter__(self):
            return self._inner

        def __exit__(self, *_):
            return None

    monkeypatch.setattr(smoke_test.httpx, "Client", _CMClient)
    code = smoke_test.run_smoke_test(
        api_url="http://test",
        skip_ibkr=False,
        skip_events=False,
        timeout_seconds=1.0,
        use_colour=False,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "OK — install gezond" in out


def test_run_smoke_test_returns_two_on_critical_failure(monkeypatch) -> None:
    responses = _all_green_responses()
    responses["/storage/status/online"] = _StubResponse(
        payload={
            "configured": True,
            "connected": True,
            "safe_to_write": False,
            "writes_status_nl": "migrations behind",
        }
    )

    class _CMClient:
        def __init__(self, *_a, **_k):
            self._inner = _StubClient(responses=responses)

        def __enter__(self):
            return self._inner

        def __exit__(self, *_):
            return None

    monkeypatch.setattr(smoke_test.httpx, "Client", _CMClient)
    code = smoke_test.run_smoke_test(
        api_url="http://test",
        skip_ibkr=False,
        skip_events=False,
        timeout_seconds=1.0,
        use_colour=False,
    )
    assert code == 2


def test_run_smoke_test_returns_one_on_warn_only(monkeypatch) -> None:
    responses = _all_green_responses()
    responses["/ibkr/sync/status"] = _StubResponse(
        payload={"configured": False}
    )

    class _CMClient:
        def __init__(self, *_a, **_k):
            self._inner = _StubClient(responses=responses)

        def __enter__(self):
            return self._inner

        def __exit__(self, *_):
            return None

    monkeypatch.setattr(smoke_test.httpx, "Client", _CMClient)
    code = smoke_test.run_smoke_test(
        api_url="http://test",
        skip_ibkr=False,
        skip_events=False,
        timeout_seconds=1.0,
        use_colour=False,
    )
    assert code == 1


def test_skip_flags_omit_their_checks(monkeypatch) -> None:
    """``--skip-ibkr`` + ``--skip-events`` mean those endpoints are
    never hit. The CLI then can't WARN on them, so the overall verdict
    drops to OK when nothing else is wrong."""

    responses = {
        "/health": _StubResponse(payload={"status": "ok", "service": "api"}),
        "/storage/status/online": _StubResponse(
            payload={
                "configured": True,
                "connected": True,
                "safe_to_write": True,
            }
        ),
        "/scheduler/v127/status": _StubResponse(
            payload={"enabled": True, "last_outcome": "success", "next_runs": []}
        ),
    }
    captured_paths: list[str] = []

    class _CMClient:
        def __init__(self, *_a, **_k):
            self._inner = _StubClient(responses=responses)

        def __enter__(self):
            return self._inner

        def __exit__(self, *_):
            captured_paths.extend(self._inner.calls)
            return None

    monkeypatch.setattr(smoke_test.httpx, "Client", _CMClient)
    code = smoke_test.run_smoke_test(
        api_url="http://test",
        skip_ibkr=True,
        skip_events=True,
        timeout_seconds=1.0,
        use_colour=False,
    )
    assert code == 0
    assert "/ibkr/sync/status" not in captured_paths
    assert "/system/events/active" not in captured_paths
