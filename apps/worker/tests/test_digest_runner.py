"""Tests for the concrete ``DailyDigestRunner`` (worker-side).

These tests use a tiny in-memory storage stub so we can assert the
runner: (1) gracefully degrades when data is missing,
(2) joins positions with market-data snapshots for PnL,
(3) gates the email send on the operator's preferences.

The real SMTP path is exercised by ``test_email_sender.py``; here we
just verify the gating decisions return the expected audit dict.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from portfolio_outlook_worker.config import (
    NotificationSettings,
    StorageSettings,
)
from portfolio_outlook_worker.digest_runner import DailyDigestRunner

_NOW = datetime(2026, 5, 31, 17, 45, tzinfo=UTC)
_TODAY = _NOW.date()


@dataclass
class _Position:
    conid: str
    symbol: str
    currency: str
    quantity: Decimal | None
    average_cost: Decimal | None


@dataclass
class _MarketDataSnapshot:
    ibkr_conid: str
    last_price: Decimal | None
    close_price: Decimal | None


@dataclass
class _Suggestion:
    action_label_nl: str
    confidence_label: str = "medium"


@dataclass
class _ActionDraft:
    status: str
    created_at: datetime


@dataclass
class _Nav:
    nav_value: Decimal
    recorded_at: datetime
    base_currency: str = "EUR"


@dataclass
class _ListResult:
    records: tuple[Any, ...]


@dataclass
class _LatestSyncRun:
    sync_run_id: str = "sync-x"


class _FakeIbkrRepo:
    def __init__(
        self,
        *,
        positions: list[_Position],
        nav_snapshots: list[_Nav],
        latest_run: _LatestSyncRun | None = None,
    ) -> None:
        self._positions = positions
        self._nav_snapshots = nav_snapshots
        self._latest_run = latest_run if latest_run is not None else _LatestSyncRun()

    def get_latest_ibkr_sync_run(self):
        return self._latest_run

    def list_ibkr_position_snapshots(self, _id: str):
        return list(self._positions)

    def list_ibkr_nav_snapshots_since(self, *, ibkr_account_id: str, since: datetime):
        return list(self._nav_snapshots)


class _FakeMarketDataRepo:
    def __init__(self, *, snapshots: list[_MarketDataSnapshot]) -> None:
        self._snapshots = snapshots

    def list_latest_market_data_snapshots_by_conids(self, _conids):
        return _ListResult(tuple(self._snapshots))


class _FakeSuggestionRepo:
    def __init__(self, *, suggestions: list[_Suggestion]) -> None:
        self._suggestions = suggestions

    def list_latest_asset_suggestions_by_conids(self, _conids):
        return _ListResult(tuple(self._suggestions))


class _FakeDraftRepo:
    def __init__(self, *, drafts: list[_ActionDraft]) -> None:
        self._drafts = drafts

    def list_latest_asset_action_drafts_by_conids(self, _conids):
        return _ListResult(tuple(self._drafts))


class _CapturingDigestRepo:
    def __init__(self) -> None:
        self.saved: list[Any] = []

    def upsert_daily_digest(self, record):
        self.saved.append(record)


def _patch_storage(
    monkeypatch: pytest.MonkeyPatch,
    *,
    positions: list[_Position],
    market_snapshots: list[_MarketDataSnapshot],
    suggestions: list[_Suggestion],
    drafts: list[_ActionDraft],
    nav_snapshots: list[_Nav],
) -> _CapturingDigestRepo:
    digest_repo = _CapturingDigestRepo()
    ibkr_repo = _FakeIbkrRepo(positions=positions, nav_snapshots=nav_snapshots)
    market_repo = _FakeMarketDataRepo(snapshots=market_snapshots)
    suggestion_repo = _FakeSuggestionRepo(suggestions=suggestions)
    draft_repo = _FakeDraftRepo(drafts=drafts)

    from portfolio_outlook_worker import digest_runner as module

    class _MockConn:
        def commit(self) -> None:
            pass

    class _Connection:
        connection = _MockConn()
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _Provider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    monkeypatch.setattr(module, "StorageConnectionProvider", _Provider)
    monkeypatch.setattr(
        module, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        module, "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: ibkr_repo,
    )
    monkeypatch.setattr(
        module, "SqlAlchemyMarketDataSnapshotRepository",
        lambda *a, **k: market_repo,
    )
    monkeypatch.setattr(
        module, "SqlAlchemyAssetSuggestionRepository",
        lambda *a, **k: suggestion_repo,
    )
    monkeypatch.setattr(
        module, "SqlAlchemyAssetActionDraftRepository",
        lambda *a, **k: draft_repo,
    )
    monkeypatch.setattr(
        module, "SqlAlchemyDailyDigestRepository",
        lambda *a, **k: digest_repo,
    )
    return digest_repo


def _build_runner(
    notifications: NotificationSettings | None = None,
) -> DailyDigestRunner:
    storage_settings = StorageSettings(
        enabled=True,
        database_url="postgresql://fake",
        writes_enabled=True,
    )
    return DailyDigestRunner(
        storage_settings=storage_settings,
        notifications=notifications or NotificationSettings(),
        now_provider=lambda: _NOW,
    )


def test_returns_storage_unavailable_when_writes_disabled() -> None:
    runner = DailyDigestRunner(
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        notifications=NotificationSettings(),
    )
    result = runner.run(
        ibkr_account_id="DU1",
        market_code="EURONEXT",
        scheduled_run_id="run-1",
    )
    assert result["sent_email"] is False
    assert result["persisted_digest"] is False
    assert result["reason"] == "storage_unavailable"


def test_persists_digest_with_pnl_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    positions = [
        _Position(
            conid="aapl",
            symbol="AAPL",
            currency="USD",
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
        ),
        _Position(
            conid="msft",
            symbol="MSFT",
            currency="USD",
            quantity=Decimal("5"),
            average_cost=Decimal("200"),
        ),
    ]
    snapshots = [
        _MarketDataSnapshot(
            ibkr_conid="aapl",
            last_price=Decimal("110"),
            close_price=Decimal("108"),
        ),
        _MarketDataSnapshot(
            ibkr_conid="msft",
            last_price=None,
            close_price=Decimal("190"),
        ),
    ]
    nav = [
        _Nav(
            nav_value=Decimal("100000"),
            recorded_at=datetime(2026, 5, 30, 17, 45, tzinfo=UTC),
        ),
        _Nav(
            nav_value=Decimal("100500"),
            recorded_at=datetime(2026, 5, 31, 17, 45, tzinfo=UTC),
        ),
    ]
    digest_repo = _patch_storage(
        monkeypatch,
        positions=positions,
        market_snapshots=snapshots,
        suggestions=[],
        drafts=[],
        nav_snapshots=nav,
    )

    runner = _build_runner()
    result = runner.run(
        ibkr_account_id="DU1",
        market_code="EURONEXT",
        scheduled_run_id="run-1",
    )
    assert result["persisted_digest"] is True
    assert digest_repo.saved, "expected a digest row to be upserted"

    saved = digest_repo.saved[0]
    # NAV delta = +500 / 100000 = +0.50%
    assert saved.nav_summary_json["delta_pct"] == "0.50"
    positions_summary = saved.positions_summary_json
    assert positions_summary["position_count"] == 2
    # AAPL: +10/100 = +10.00%. MSFT: (190-200)/200 = -5.00%.
    winners = positions_summary["top_winners"]
    losers = positions_summary["top_losers"]
    assert winners[0]["symbol"] == "AAPL"
    assert winners[0]["pnl_pct"] == "10.00"
    assert losers[0]["symbol"] == "MSFT"
    assert losers[0]["pnl_pct"] == "-5.00"


def test_email_skipped_when_master_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # NAV drop of 2.5% will produce a nav_drop alert; the master
    # notifications switch is off, so the email is skipped.
    nav = [
        _Nav(
            nav_value=Decimal("100000"),
            recorded_at=datetime(2026, 5, 30, 17, 45, tzinfo=UTC),
        ),
        _Nav(
            nav_value=Decimal("97500"),
            recorded_at=datetime(2026, 5, 31, 17, 45, tzinfo=UTC),
        ),
    ]
    _patch_storage(
        monkeypatch,
        positions=[],
        market_snapshots=[],
        suggestions=[],
        drafts=[],
        nav_snapshots=nav,
    )

    runner = _build_runner(NotificationSettings(email_enabled=False))
    result = runner.run(
        ibkr_account_id="DU1",
        market_code="EURONEXT",
        scheduled_run_id="run-1",
    )
    assert result["email"]["sent"] is False
    assert result["email"]["reason"] == "email_disabled"


def test_email_skipped_when_no_alerts_fired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Tiny NAV bump → no nav_drop alert. Master switch on but nothing
    # to email about.
    nav = [
        _Nav(
            nav_value=Decimal("100000"),
            recorded_at=datetime(2026, 5, 30, 17, 45, tzinfo=UTC),
        ),
        _Nav(
            nav_value=Decimal("100050"),
            recorded_at=datetime(2026, 5, 31, 17, 45, tzinfo=UTC),
        ),
    ]
    _patch_storage(
        monkeypatch,
        positions=[],
        market_snapshots=[],
        suggestions=[],
        drafts=[],
        nav_snapshots=nav,
    )

    runner = _build_runner(NotificationSettings(email_enabled=True))
    result = runner.run(
        ibkr_account_id="DU1",
        market_code="EURONEXT",
        scheduled_run_id="run-1",
    )
    assert result["email"]["sent"] is False
    assert result["email"]["reason"] == "no_alerts"


def test_email_skipped_when_specific_trigger_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nav = [
        _Nav(
            nav_value=Decimal("100000"),
            recorded_at=datetime(2026, 5, 30, 17, 45, tzinfo=UTC),
        ),
        _Nav(
            nav_value=Decimal("97500"),
            recorded_at=datetime(2026, 5, 31, 17, 45, tzinfo=UTC),
        ),
    ]
    _patch_storage(
        monkeypatch,
        positions=[],
        market_snapshots=[],
        suggestions=[],
        drafts=[],
        nav_snapshots=nav,
    )

    # Master on, but the operator opted out of nav_drop emails.
    runner = _build_runner(
        NotificationSettings(
            email_enabled=True,
            send_on_nav_drop=False,
            send_on_position_drop=False,
            send_on_high_confidence_sell=False,
        )
    )
    result = runner.run(
        ibkr_account_id="DU1",
        market_code="EURONEXT",
        scheduled_run_id="run-1",
    )
    assert result["email"]["sent"] is False
    assert result["email"]["reason"] == "all_alerts_disabled_by_preference"


def test_email_stubbed_when_master_on_but_smtp_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nav = [
        _Nav(
            nav_value=Decimal("100000"),
            recorded_at=datetime(2026, 5, 30, 17, 45, tzinfo=UTC),
        ),
        _Nav(
            nav_value=Decimal("97500"),
            recorded_at=datetime(2026, 5, 31, 17, 45, tzinfo=UTC),
        ),
    ]
    _patch_storage(
        monkeypatch,
        positions=[],
        market_snapshots=[],
        suggestions=[],
        drafts=[],
        nav_snapshots=nav,
    )

    runner = _build_runner(
        NotificationSettings(
            email_enabled=True,
            # smtp_host / smtp_from / smtp_to all None — incomplete.
        )
    )
    result = runner.run(
        ibkr_account_id="DU1",
        market_code="EURONEXT",
        scheduled_run_id="run-1",
    )
    assert result["email"]["sent"] is False
    assert result["email"]["reason"] == "smtp_config_incomplete"


def test_action_drafts_filtered_to_today(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yesterday = datetime(2026, 5, 30, 14, 0, tzinfo=UTC)
    today = datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
    # Drafts are fetched per-conid; supply one position so the
    # runner's conid set is non-empty and the draft repo is queried.
    positions = [
        _Position(
            conid="aapl",
            symbol="AAPL",
            currency="USD",
            quantity=Decimal("1"),
            average_cost=Decimal("100"),
        ),
    ]
    drafts = [
        _ActionDraft(status="draft", created_at=yesterday),
        _ActionDraft(status="approved", created_at=today),
        _ActionDraft(status="submitted_to_broker", created_at=today),
    ]
    digest_repo = _patch_storage(
        monkeypatch,
        positions=positions,
        market_snapshots=[],
        suggestions=[],
        drafts=drafts,
        nav_snapshots=[],
    )

    runner = _build_runner()
    runner.run(
        ibkr_account_id="DU1",
        market_code="EURONEXT",
        scheduled_run_id="run-1",
    )
    saved = digest_repo.saved[0]
    summary = saved.action_drafts_summary_json
    # Yesterday's draft is excluded; only today's two are counted.
    assert summary["approved_today"] == 1
    assert summary["submitted_today"] == 1
    assert summary["created_today"] == 0


# ---- AI summary header ------------------------------------------------


def test_render_email_bodies_prepends_ai_summary_when_provided() -> None:
    from datetime import date

    from portfolio_outlook_worker.digest_runner import _render_email_bodies

    @dataclass
    class _Digest:
        market_code: str = "EURONEXT"
        briefing_date: date = date(2026, 5, 31)
        nav_summary_json: dict[str, object] = None  # type: ignore[assignment]
        suggestions_summary_json: dict[str, object] = None  # type: ignore[assignment]
        action_drafts_summary_json: dict[str, object] = None  # type: ignore[assignment]
        alerts_json: list[dict[str, object]] = None  # type: ignore[assignment]

    digest = _Digest(
        nav_summary_json={"delta_pct": "0.50", "currency": "EUR"},
        suggestions_summary_json={"total": 3},
        action_drafts_summary_json={"created_today": 1},
        alerts_json=[],
    )
    subject, plain, html = _render_email_bodies(
        digest=digest,  # type: ignore[arg-type]
        sendable_alerts=[
            {
                "severity_nl": "Hoog",
                "title_nl": "NAV-daling",
                "body_nl": "Portfolio NAV daalde met 2.5%.",
            }
        ],
        ai_summary_nl="Vandaag een matige sessie met enkele aandachtspunten.",
    )
    assert "AI-samenvatting" in plain
    assert "Vandaag een matige sessie" in plain
    assert "AI-samenvatting" in html
    assert "EURONEXT" in subject


def test_render_email_bodies_omits_ai_summary_header_when_none() -> None:
    from datetime import date

    from portfolio_outlook_worker.digest_runner import _render_email_bodies

    @dataclass
    class _Digest:
        market_code: str = "EURONEXT"
        briefing_date: date = date(2026, 5, 31)
        nav_summary_json: dict[str, object] = None  # type: ignore[assignment]
        suggestions_summary_json: dict[str, object] = None  # type: ignore[assignment]
        action_drafts_summary_json: dict[str, object] = None  # type: ignore[assignment]
        alerts_json: list[dict[str, object]] = None  # type: ignore[assignment]

    digest = _Digest(
        nav_summary_json={},
        suggestions_summary_json={"total": 0},
        action_drafts_summary_json={"created_today": 0},
        alerts_json=[],
    )
    _, plain, html = _render_email_bodies(
        digest=digest,  # type: ignore[arg-type]
        sendable_alerts=[
            {"severity_nl": "Hoog", "title_nl": "T", "body_nl": "B"}
        ],
        ai_summary_nl=None,
    )
    assert "AI-samenvatting" not in plain
    assert "AI-samenvatting" not in html


def test_maybe_compose_ai_summary_returns_none_when_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from portfolio_outlook_worker import digest_runner as module

    called: list[object] = []

    def _stub_compose(**kw):
        called.append(kw)
        return None

    monkeypatch.setattr(module, "compose_alert_summary", _stub_compose)
    result = module._maybe_compose_ai_summary(
        digest=object(),  # type: ignore[arg-type]
        sendable_alerts=[{"severity_nl": "x", "title_nl": "t", "body_nl": "b"}],
        api_base_url="http://api:8000",
        api_request_timeout_seconds=1.0,
        notifications=NotificationSettings(ai_email_summary_enabled=False),
    )
    assert result is None
    assert called == []  # HTTP call never made


def test_maybe_compose_ai_summary_returns_summary_on_generated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import date

    from portfolio_outlook_worker import digest_runner as module

    captured: dict[str, object] = {}

    def _stub_compose(**kw):
        captured.update(kw)
        return {
            "status": "generated",
            "summary_nl": "Vandaag matig.",
            "blocking_reason": None,
            "hallucinated_numbers": [],
            "safe_for_orders": False,
        }

    monkeypatch.setattr(module, "compose_alert_summary", _stub_compose)

    @dataclass
    class _Digest:
        market_code: str = "EURONEXT"
        briefing_date: date = date(2026, 5, 31)
        nav_summary_json: dict[str, object] = None  # type: ignore[assignment]
        suggestions_summary_json: dict[str, object] = None  # type: ignore[assignment]
        action_drafts_summary_json: dict[str, object] = None  # type: ignore[assignment]
        alerts_json: list[dict[str, object]] = None  # type: ignore[assignment]

    digest = _Digest(
        nav_summary_json={"delta_pct": "0.50", "currency": "EUR"},
        suggestions_summary_json={"total": 3},
        action_drafts_summary_json={"created_today": 1},
        alerts_json=[],
    )
    result = module._maybe_compose_ai_summary(
        digest=digest,  # type: ignore[arg-type]
        sendable_alerts=[
            {"severity_nl": "Hoog", "title_nl": "T", "body_nl": "B"}
        ],
        api_base_url="http://api:8000",
        api_request_timeout_seconds=2.5,
        notifications=NotificationSettings(ai_email_summary_enabled=True),
    )
    assert result == "Vandaag matig."
    assert captured["kind"] == "digest"
    assert captured["base_url"] == "http://api:8000"
    # The deterministic context block carries the market + NAV numbers.
    assert "EURONEXT" in str(captured["context_text"])
    assert "0.50%" in str(captured["context_text"])


def _digest_stub():
    from datetime import date

    @dataclass
    class _D:
        market_code: str = "EURONEXT"
        briefing_date: date = date(2026, 5, 31)
        nav_summary_json: dict[str, object] = None  # type: ignore[assignment]
        suggestions_summary_json: dict[str, object] = None  # type: ignore[assignment]
        action_drafts_summary_json: dict[str, object] = None  # type: ignore[assignment]
        alerts_json: list[dict[str, object]] = None  # type: ignore[assignment]

    return _D(
        nav_summary_json={"delta_pct": "0.50", "currency": "EUR"},
        suggestions_summary_json={"total": 0},
        action_drafts_summary_json={"created_today": 0},
        alerts_json=[],
    )


def test_maybe_compose_ai_summary_returns_none_when_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from portfolio_outlook_worker import digest_runner as module

    monkeypatch.setattr(
        module,
        "compose_alert_summary",
        lambda **_: {
            "status": "provider_unavailable",
            "summary_nl": None,
            "blocking_reason": "budget_exceeded",
        },
    )
    result = module._maybe_compose_ai_summary(
        digest=_digest_stub(),  # type: ignore[arg-type]
        sendable_alerts=[{"severity_nl": "x", "title_nl": "t", "body_nl": "b"}],
        api_base_url="http://api:8000",
        api_request_timeout_seconds=1.0,
        notifications=NotificationSettings(ai_email_summary_enabled=True),
    )
    assert result is None


def test_maybe_compose_ai_summary_returns_none_on_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the HTTP call fails (compose returns None) the runner must
    fall through to template-only — never crash, never block sending."""

    from portfolio_outlook_worker import digest_runner as module

    monkeypatch.setattr(module, "compose_alert_summary", lambda **_: None)
    result = module._maybe_compose_ai_summary(
        digest=_digest_stub(),  # type: ignore[arg-type]
        sendable_alerts=[{"severity_nl": "x", "title_nl": "t", "body_nl": "b"}],
        api_base_url="http://api:8000",
        api_request_timeout_seconds=1.0,
        notifications=NotificationSettings(ai_email_summary_enabled=True),
    )
    assert result is None
