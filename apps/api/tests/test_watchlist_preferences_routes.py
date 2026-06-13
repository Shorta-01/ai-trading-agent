"""Tests for the watchlist-preferences API endpoints (V1.2 §AU)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app

_BASE_TS = datetime(2026, 6, 13, 9, 0, tzinfo=UTC)


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "prefs.sqlite")
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0073_watchlist_preferences')"
            )
        )
    engine.dispose()
    return db_url


def _insert_preference(
    db_url: str,
    *,
    pref_id: str,
    symbol: str,
    kind: str,
    account_ref: str = "default",
    note: str | None = None,
    created_at: datetime = _BASE_TS,
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO watchlist_preferences ("
                "watchlist_preference_id, ibkr_account_ref, symbol, "
                "kind, note, created_at) VALUES ("
                ":pid, :acc, :sym, :kind, :note, :ts)"
            ),
            {
                "pid": pref_id,
                "acc": account_ref,
                "sym": symbol,
                "kind": kind,
                "note": note,
                "ts": created_at.isoformat(),
            },
        )
    engine.dispose()


def _insert_verdict(
    db_url: str,
    *,
    verdict_id: str,
    symbol: str,
    decision: str = "suggest",
    blocking_reason: str | None = None,
    summary_nl: str = "Test summary",
    confidence: float | None = 0.85,
    generated_at: datetime = _BASE_TS,
    account_ref: str = "default",
) -> None:
    engine = create_engine(db_url, future=True)
    details: dict[str, object] = {"macro": {"favorable": True}}
    if confidence is not None:
        details["confidence"] = confidence
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO orchestrator_scoring_verdicts ("
                "verdict_id, ibkr_account_ref, symbol, ibkr_conid, "
                "forecast_id, generated_at, decision, blocking_reason, "
                "details_json, summary_nl) VALUES ("
                ":vid, :acc, :sym, 1, :fid, :gen, :dec, :br, :dj, :nl)"
            ),
            {
                "vid": verdict_id,
                "acc": account_ref,
                "sym": symbol,
                "fid": f"fc-{verdict_id}",
                "gen": generated_at.isoformat(),
                "dec": decision,
                "br": blocking_reason,
                "dj": json.dumps(details),
                "nl": summary_nl,
            },
        )
    engine.dispose()


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


# ---- favorieten list ------------------------------------------------


def test_favorieten_storage_disabled_returns_503() -> None:
    _disable_storage()
    client = TestClient(app)
    response = client.get("/watchlist-preferences/favorieten")
    assert response.status_code == 503


def test_favorieten_empty_listing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/watchlist-preferences/favorieten")
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == "default"
    assert body["items"] == []
    assert "favoriet" in body["help_nl"].lower()


def test_favorieten_lists_symbols_with_latest_verdict(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_preference(db_url, pref_id="p1", symbol="AAPL", kind="favorite")
    _insert_preference(
        db_url, pref_id="p2", symbol="ASML.AS", kind="favorite",
        note="Euronext favoriet",
    )
    _insert_verdict(
        db_url,
        verdict_id="v1",
        symbol="AAPL",
        decision="suggest",
        summary_nl="AAPL haalt de drempel",
        confidence=0.91,
    )
    # No verdict for ASML.AS — UI should render the row anyway.
    client = _client(db_url)
    body = client.get("/watchlist-preferences/favorieten").json()
    items = {item["symbol"]: item for item in body["items"]}
    assert set(items) == {"AAPL", "ASML.AS"}
    assert items["AAPL"]["latest_decision"] == "suggest"
    assert items["AAPL"]["latest_confidence"] == 0.91
    assert items["AAPL"]["latest_summary_nl"] == "AAPL haalt de drempel"
    assert items["ASML.AS"]["latest_decision"] is None
    assert items["ASML.AS"]["latest_confidence"] is None
    assert items["ASML.AS"]["note"] == "Euronext favoriet"


def test_favorieten_picks_newest_verdict_per_symbol(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_preference(db_url, pref_id="p1", symbol="AAPL", kind="favorite")
    older = _BASE_TS.replace(hour=8)
    newer = _BASE_TS.replace(hour=10)
    _insert_verdict(
        db_url, verdict_id="vold", symbol="AAPL", decision="skip_macro_regime",
        confidence=0.4, generated_at=older,
    )
    _insert_verdict(
        db_url, verdict_id="vnew", symbol="AAPL", decision="suggest",
        confidence=0.88, generated_at=newer,
    )
    client = _client(db_url)
    items = client.get("/watchlist-preferences/favorieten").json()["items"]
    assert len(items) == 1
    assert items[0]["latest_decision"] == "suggest"
    assert items[0]["latest_confidence"] == 0.88


def test_favorieten_scoped_per_account(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_preference(
        db_url, pref_id="p1", symbol="AAPL", kind="favorite",
        account_ref="account-a",
    )
    _insert_preference(
        db_url, pref_id="p2", symbol="MSFT", kind="favorite",
        account_ref="account-b",
    )
    client = _client(db_url)
    a_items = client.get(
        "/watchlist-preferences/favorieten?account_id=account-a"
    ).json()["items"]
    assert [it["symbol"] for it in a_items] == ["AAPL"]


# ---- uitsluitingen list ----------------------------------------------


def test_uitsluitingen_lists_excluded_only(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_preference(db_url, pref_id="p1", symbol="TSLA", kind="excluded")
    _insert_preference(db_url, pref_id="p2", symbol="AAPL", kind="favorite")
    client = _client(db_url)
    body = client.get("/watchlist-preferences/uitsluitingen").json()
    assert [it["symbol"] for it in body["items"]] == ["TSLA"]


def test_uitsluitingen_empty_listing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/watchlist-preferences/uitsluitingen")
    assert response.status_code == 200
    assert response.json()["items"] == []


# ---- POST save preference --------------------------------------------


def test_post_creates_favorite(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.post(
        "/watchlist-preferences",
        json={
            "account_id": "default",
            "symbol": "aapl",  # lowercased — server uppercases.
            "kind": "favorite",
            "note": "broer's tip",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["accepted"] is True
    listed = client.get("/watchlist-preferences/favorieten").json()
    assert listed["items"][0]["symbol"] == "AAPL"
    assert listed["items"][0]["note"] == "broer's tip"


def test_post_is_idempotent_on_account_symbol_kind(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    payload = {"symbol": "AAPL", "kind": "favorite", "note": "v1"}
    client.post("/watchlist-preferences", json=payload)
    client.post(
        "/watchlist-preferences", json={**payload, "note": "v2"}
    )
    listed = client.get("/watchlist-preferences/favorieten").json()
    assert len(listed["items"]) == 1
    assert listed["items"][0]["note"] == "v2"


def test_post_rejects_invalid_kind(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.post(
        "/watchlist-preferences",
        json={"symbol": "AAPL", "kind": "watch"},
    )
    assert response.status_code == 400


def test_post_rejects_empty_symbol(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.post(
        "/watchlist-preferences",
        json={"symbol": "   ", "kind": "favorite"},
    )
    assert response.status_code == 400


def test_post_storage_disabled_returns_503() -> None:
    _disable_storage()
    client = TestClient(app)
    response = client.post(
        "/watchlist-preferences",
        json={"symbol": "AAPL", "kind": "favorite"},
    )
    assert response.status_code == 503


# ---- DELETE preference -----------------------------------------------


def test_delete_removes_preference(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _insert_preference(db_url, pref_id="p1", symbol="TSLA", kind="excluded")
    client = _client(db_url)
    response = client.delete(
        "/watchlist-preferences?symbol=TSLA&kind=excluded"
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    listed = client.get("/watchlist-preferences/uitsluitingen").json()
    assert listed["items"] == []


def test_delete_is_idempotent(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    # Delete a row that was never inserted — still 200.
    response = client.delete(
        "/watchlist-preferences?symbol=NEVER&kind=favorite"
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_delete_rejects_invalid_kind(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.delete(
        "/watchlist-preferences?symbol=AAPL&kind=bogus"
    )
    assert response.status_code == 400
