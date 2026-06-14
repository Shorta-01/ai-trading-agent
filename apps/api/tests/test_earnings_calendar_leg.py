"""Tests for ``build_real_earnings_calendar_leg`` (V1.2 §AK)."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from ai_trading_agent_storage.metadata import metadata
from sqlalchemy import create_engine, text

from portfolio_outlook_api.earnings_calendar_leg import (
    build_real_earnings_calendar_leg,
)
from portfolio_outlook_api.eodhd_client import EodhdEarningsEvent
from portfolio_outlook_api.morning_chain import (
    LEG_EARNINGS_CALENDAR_SYNC,
    LEG_STATUS_FAILED,
    LEG_STATUS_SKIPPED,
    LEG_STATUS_SUCCEEDED,
)


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "earnings_leg.sqlite")
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
                "('0076_dividend_events')"
            )
        )
    engine.dispose()
    return db_url


def _seed_sync_run_and_positions(
    db_url: str,
    *,
    sync_run_id: str = "sr-1",
    positions: list[tuple[str, str | None, str]] | None = None,
) -> None:
    """Insert one ``ibkr_sync_runs`` row + the supplied position rows.

    ``positions`` is a list of ``(symbol, primary_exchange, quantity)``.
    """

    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ibkr_sync_runs ("
                "sync_run_id, started_at, provider_code, "
                "provider_environment, account_mode, status, "
                "account_summary_status, positions_status, "
                "open_orders_status, executions_status, "
                "stored_at) VALUES "
                "(:sid, '2026-06-12T05:00:00Z', 'ibkr', 'paper', "
                "'paper', 'success', 'ok', 'ok', 'ok', 'ok', "
                "'2026-06-12T05:00:00Z')"
            ),
            {"sid": sync_run_id},
        )
        for symbol, primary_exchange, quantity in positions or []:
            conn.execute(
                text(
                    "INSERT INTO ibkr_position_snapshots ("
                    "snapshot_id, sync_run_id, symbol, security_type, "
                    "currency, primary_exchange, quantity, "
                    "received_at, stored_at) VALUES ("
                    ":sid, :sr, :sym, 'STK', 'USD', :pex, :qty, "
                    "'2026-06-12T05:00:00Z', '2026-06-12T05:00:00Z')"
                ),
                {
                    "sid": f"snap-{symbol}",
                    "sr": sync_run_id,
                    "sym": symbol,
                    "pex": primary_exchange,
                    "qty": quantity,
                },
            )
    engine.dispose()


class _StubClient:
    """Captures the call args + returns fixed events."""

    def __init__(self, events: list[EodhdEarningsEvent]) -> None:
        self.events = events
        self.calls: list[tuple[str, tuple[str, ...], date, date]] = []

    @classmethod
    def factory(cls, events: list[EodhdEarningsEvent]):
        def _make(*args, **kwargs):
            instance = cls(events)
            # First positional or keyword "api_key" is the trigger
            # — store it so tests can assert it was forwarded.
            key = kwargs.get("api_key") or (args[0] if args else None)
            instance.api_key = key
            return instance

        return _make

    def fetch_earnings_calendar(
        self,
        *,
        symbols: tuple[str, ...],
        from_date: date,
        to_date: date,
    ) -> list[EodhdEarningsEvent]:
        self.calls.append(
            (getattr(self, "api_key", ""), symbols, from_date, to_date)
        )
        return list(self.events)


def _settings(
    *,
    db_url: str | None = None,
    enabled: bool = True,
    api_key: str | None = "test-key",
) -> SimpleNamespace:
    """A minimal settings stand-in. The real leg uses ``getattr`` so a
    SimpleNamespace is enough; we don't need the full pydantic
    settings type."""

    storage = SimpleNamespace(
        enabled=db_url is not None,
        database_url=db_url,
        writes_enabled=True,
    )
    return SimpleNamespace(
        earnings_calendar_sync_enabled=enabled,
        storage=storage,
        eodhd_api_key=api_key,
    )


# ---- skip paths ------------------------------------------------------


def test_leg_skipped_when_flag_off() -> None:
    leg = build_real_earnings_calendar_leg(_settings(enabled=False))
    outcome = leg()
    assert outcome.leg_name == LEG_EARNINGS_CALENDAR_SYNC
    assert outcome.status == LEG_STATUS_SKIPPED
    assert "earnings_calendar_sync_enabled" in outcome.detail_nl


def test_leg_skipped_when_storage_disabled() -> None:
    leg = build_real_earnings_calendar_leg(_settings(db_url=None))
    outcome = leg()
    assert outcome.status == LEG_STATUS_SKIPPED
    assert "opslag" in outcome.detail_nl.lower()


def test_leg_skipped_when_eodhd_key_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    leg = build_real_earnings_calendar_leg(
        _settings(db_url=db_url, api_key=None)
    )
    outcome = leg()
    assert outcome.status == LEG_STATUS_SKIPPED
    assert "EODHD" in outcome.detail_nl


# ---- happy paths -----------------------------------------------------


def test_leg_no_positions_succeeds_without_calling_provider(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    stub = _StubClient([])
    leg = build_real_earnings_calendar_leg(
        _settings(db_url=db_url),
        provider_factory=_StubClient.factory([]),
    )
    outcome = leg()
    assert outcome.status == LEG_STATUS_SUCCEEDED
    assert "niets te verversen" in outcome.detail_nl
    assert stub.calls == []  # provider was never invoked


def test_leg_gathers_positions_and_upserts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _seed_sync_run_and_positions(
        db_url,
        positions=[
            ("AAPL", "NASDAQ", "10"),
            ("MSFT", "NASDAQ", "5"),
            ("ZERO", "NASDAQ", "0"),  # closed → skipped
            ("UNKNOWN", "UNMAPPED", "3"),  # bad exchange → skipped
        ],
    )
    captured: dict[str, _StubClient] = {}

    def _factory(*args, **kwargs):
        # ``build_real_earnings_calendar_leg`` calls
        # ``factory(api_key=api_key)`` when factory is EodhdClient
        # and ``factory()`` otherwise. Since we're passing in our
        # stub it goes via the else-branch — no kwargs.
        client = _StubClient(
            [
                EodhdEarningsEvent(
                    symbol="AAPL.US",
                    event_date=date(2026, 7, 30),
                    status="confirmed",
                    raw_payload={"eps_estimate": "1.50"},
                ),
                EodhdEarningsEvent(
                    symbol="MSFT.US",
                    event_date=date(2026, 7, 22),
                    status="estimated",
                    raw_payload={},
                ),
            ]
        )
        captured["client"] = client
        return client

    leg = build_real_earnings_calendar_leg(
        _settings(db_url=db_url), provider_factory=_factory  # type: ignore[arg-type]
    )
    outcome = leg()
    assert outcome.status == LEG_STATUS_SUCCEEDED
    assert "2 symbolen aangevraagd" in outcome.detail_nl
    assert "2 events opgehaald" in outcome.detail_nl
    assert "2 weggeschreven" in outcome.detail_nl

    # The provider saw exactly the two mappable, non-zero positions.
    call_symbols = captured["client"].calls[0][1]
    assert sorted(call_symbols) == ["AAPL.US", "MSFT.US"]


def test_leg_marks_failed_on_provider_error_text(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    _seed_sync_run_and_positions(
        db_url, positions=[("AAPL", "NASDAQ", "10")]
    )

    class _RaisingProvider:
        def fetch_earnings_calendar(self, **_kwargs):
            raise RuntimeError("eodhd_down")

    leg = build_real_earnings_calendar_leg(
        _settings(db_url=db_url),
        provider_factory=lambda *a, **k: _RaisingProvider(),  # type: ignore[arg-type]
    )
    outcome = leg()
    assert outcome.status == LEG_STATUS_FAILED
    assert outcome.failure_code == "earnings_calendar_provider_error"
    assert "eodhd_down" in outcome.detail_nl
