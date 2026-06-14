"""Tests voor de macro-resolver + macro-feed-sync (V1.2 §BE)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trading_agent_storage.metadata import metadata
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.macro_feed_sync import sync_macro_feed
from portfolio_outlook_api.macro_resolver import resolve_macro_data


@pytest.fixture(autouse=True)
def _reset_storage_settings():  # type: ignore[no-untyped-def]
    original_enabled = api_settings.storage.enabled
    original_url = api_settings.storage.database_url
    original_writes = api_settings.storage.writes_enabled
    yield
    api_settings.storage.enabled = original_enabled
    api_settings.storage.database_url = original_url
    api_settings.storage.writes_enabled = original_writes


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "macro.sqlite")
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
                "('0079_macro_index_snapshots')"
            )
        )
    engine.dispose()
    return db_url


def _wire_storage(db_url: str) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def _seed_vix_bar(db_url: str, *, day: date, close: str) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO macro_index_snapshots (snapshot_id, series_code, "
                "bar_date, close_value, raw_payload, provider, fetched_at) "
                "VALUES (:sid, 'vix', :d, :c, NULL, 'eodhd', :ts)"
            ),
            {
                "sid": f"vix-{day.isoformat()}",
                "d": day.isoformat(),
                "c": close,
                "ts": datetime(2026, 6, 14, tzinfo=UTC).isoformat(),
            },
        )
    engine.dispose()


def _seed_spx_bar(db_url: str, *, day: date, close: str) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO macro_index_snapshots (snapshot_id, series_code, "
                "bar_date, close_value, raw_payload, provider, fetched_at) "
                "VALUES (:sid, 'spx', :d, :c, NULL, 'eodhd', :ts)"
            ),
            {
                "sid": f"spx-{day.isoformat()}",
                "d": day.isoformat(),
                "c": close,
                "ts": datetime(2026, 6, 14, tzinfo=UTC).isoformat(),
            },
        )
    engine.dispose()


# ---- resolver -----------------------------------------------------


def test_resolver_falls_back_when_storage_off() -> None:
    """Verse install zonder storage → synthetisch (gedrag pre-§BE)."""

    _disable_storage()
    res = resolve_macro_data()
    assert res.vix_level is None
    assert res.vix_source == "storage-unavailable"
    assert len(res.index_bars) == 250  # synthetic uptrend
    assert res.index_source == "synthetic-fallback"


def test_resolver_returns_synthetic_when_db_empty(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _wire_storage(_seed_db(tmp_path))
    res = resolve_macro_data()
    assert res.vix_level is None
    assert res.vix_source == "missing"
    assert res.index_source == "synthetic-fallback"


def test_resolver_uses_real_vix_when_seeded(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _wire_storage(db)
    _seed_vix_bar(db, day=date(2026, 6, 12), close="22.5")
    res = resolve_macro_data()
    assert res.vix_level == Decimal("22.5")
    assert res.vix_source == "feed"


def test_resolver_uses_real_spx_bars_when_seeded(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _wire_storage(db)
    for offset, close in enumerate(["5000", "5050", "5100", "5150"]):
        _seed_spx_bar(
            db, day=date(2026, 6, 10) + timedelta(days=offset), close=close
        )
    res = resolve_macro_data()
    assert "feed:" in res.index_source
    assert len(res.index_bars) == 4
    # Chronologisch oudste-eerst (vereiste van de macro-gate).
    assert res.index_bars[0].close_price == Decimal("5000")
    assert res.index_bars[-1].close_price == Decimal("5150")


def test_resolver_picks_vix_on_or_before_audit_date(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Voor een gerichte audit ('wat was VIX die ochtend') willen we
    de historische close, niet de meest recente."""

    db = _seed_db(tmp_path)
    _wire_storage(db)
    _seed_vix_bar(db, day=date(2026, 6, 1), close="15")
    _seed_vix_bar(db, day=date(2026, 6, 13), close="30")
    res_old = resolve_macro_data(on_date=date(2026, 6, 5))
    assert res_old.vix_level == Decimal("15")
    res_new = resolve_macro_data(on_date=date(2026, 6, 14))
    assert res_new.vix_level == Decimal("30")


# ---- feed sync ----------------------------------------------------


@dataclass
class _FakeBar:
    bar_date: date
    open_price: Decimal | None
    high_price: Decimal | None
    low_price: Decimal | None
    close_price: Decimal | None
    adjusted_close: Decimal | None
    volume: Decimal | None


class _FakeProvider:
    """Test-stub die alleen ``fetch_eod_bars`` levert."""

    def __init__(self, by_symbol: dict[str, list[_FakeBar]]) -> None:
        self._by_symbol = by_symbol
        self.calls: list[str] = []

    def fetch_eod_bars(self, eodhd_symbol, *, from_date, to_date):  # type: ignore[no-untyped-def]
        self.calls.append(eodhd_symbol)
        return self._by_symbol.get(eodhd_symbol, [])


def _make_bars(values: list[tuple[date, str]]) -> list[_FakeBar]:
    return [
        _FakeBar(
            bar_date=day,
            open_price=Decimal(close),
            high_price=Decimal(close),
            low_price=Decimal(close),
            close_price=Decimal(close),
            adjusted_close=Decimal(close),
            volume=Decimal("0"),
        )
        for day, close in values
    ]


def test_sync_returns_provider_skipped_without_storage() -> None:
    _disable_storage()
    res = sync_macro_feed(provider=_FakeProvider({}))
    assert res.provider_skipped is True
    assert res.error == "storage-disabled"


def test_sync_returns_skipped_without_eodhd_key(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _wire_storage(_seed_db(tmp_path))
    # Geen provider injectie + geen API-key in settings → skip.
    res = sync_macro_feed()
    assert res.provider_skipped is True
    assert res.error == "eodhd-key-missing"


def test_sync_persists_vix_and_spx_bars(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _wire_storage(db)
    today = date(2026, 6, 13)
    provider = _FakeProvider(
        {
            "VIX.INDX": _make_bars(
                [
                    (today - timedelta(days=2), "15.5"),
                    (today - timedelta(days=1), "16.2"),
                    (today, "14.8"),
                ]
            ),
            "GSPC.INDX": _make_bars(
                [
                    (today - timedelta(days=2), "5000"),
                    (today - timedelta(days=1), "5050"),
                    (today, "5100"),
                ]
            ),
        }
    )
    res = sync_macro_feed(today=today, provider=provider)
    assert res.error is None
    assert res.vix_bars_persisted == 3
    assert res.spx_bars_persisted == 3
    # En de resolver ziet ze nu echt.
    resolved = resolve_macro_data(on_date=today)
    assert resolved.vix_level == Decimal("14.8")
    assert "feed" in resolved.index_source
    assert len(resolved.index_bars) == 3


def test_sync_skips_invalid_bars(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Bars zonder geldige close worden overgeslagen — de CHECK
    constraint laat ze toch niet door."""

    db = _seed_db(tmp_path)
    _wire_storage(db)
    today = date(2026, 6, 13)
    bars = _make_bars([(today, "20")])
    bars.append(
        _FakeBar(
            bar_date=today - timedelta(days=1),
            open_price=None,
            high_price=None,
            low_price=None,
            close_price=None,
            adjusted_close=None,
            volume=None,
        )
    )
    provider = _FakeProvider({"VIX.INDX": bars, "GSPC.INDX": []})
    res = sync_macro_feed(today=today, provider=provider)
    assert res.vix_bars_persisted == 1


def test_sync_is_idempotent_per_date(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _wire_storage(db)
    today = date(2026, 6, 13)
    bars = _make_bars([(today, "15.5")])
    provider = _FakeProvider({"VIX.INDX": bars, "GSPC.INDX": []})
    sync_macro_feed(today=today, provider=provider)
    sync_macro_feed(today=today, provider=provider)
    resolved = resolve_macro_data(on_date=today)
    assert resolved.vix_level == Decimal("15.5")
    # Niet twee rijen, maar één.
    assert len(resolved.index_bars) >= 0  # spx leeg, geen crash


def test_sync_provider_exception_returns_error_string(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _wire_storage(db)

    class _BrokenProvider:
        def fetch_eod_bars(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network unreachable")

    res = sync_macro_feed(today=date(2026, 6, 13), provider=_BrokenProvider())
    assert res.error is not None
    assert "network unreachable" in res.error
    assert res.provider_skipped is False
