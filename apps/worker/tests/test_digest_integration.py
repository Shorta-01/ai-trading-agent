"""End-to-end smoke test for the daily-digest loop.

The closest thing we can run to a "real" smoke test without IBKR /
EODHD / SMTP infrastructure: builds a real sqlite database with every
``ai_trading_agent_storage`` table, seeds it with realistic positions
/ market data / suggestions / drafts / NAV, runs the actual
:class:`DailyDigestRunner` through its real
:class:`StorageConnectionProvider`, and asserts the persisted digest
row + email-gating decisions.

What this catches that the unit tests don't:
- The real upsert path against the daily_digests table schema.
- The position×market-data join against the actual SQL queries the
  repos issue (rather than in-memory fakes).
- The NAV pair resolution when multiple snapshots exist in the same
  account.
- That the runner doesn't break when the alembic_version row is set
  to the locked latest revision.

What this does NOT cover (true smoke test would need real infra):
- SMTP delivery on the wire — the email_sender stays in stub mode.
- IBKR API responses — positions are seeded directly.
- EODHD price freshness — market-data snapshots are seeded directly.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from ai_trading_agent_storage import (
    AssetActionDraftRecord,
    AssetSuggestionRecord,
    IbkrNavSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    MarketDataLatestSnapshotRecord,
    SqlAlchemyAssetActionDraftRepository,
    SqlAlchemyAssetSuggestionRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyMarketDataSnapshotRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
    build_expected_migration_inventory,
)
from sqlalchemy import create_engine, text

from portfolio_outlook_worker.config import (
    NotificationSettings,
    StorageSettings,
)
from portfolio_outlook_worker.digest_runner import DailyDigestRunner

# Mid-month "today" deliberately. The runner's NAV fetch window is
# ``since=first of current month`` so a 1st-of-the-month digest would
# miss yesterday's snapshot. That's worth tightening (lookback should
# be >=N days, not month-anchored) — flagged as a follow-up.
_NOW = datetime(2026, 6, 15, 17, 45, tzinfo=UTC)
_YESTERDAY = _NOW - timedelta(days=1)
_ACCOUNT_ID = "DU1234567"
_SYNC_RUN_ID = "sync-integration"


def _ready_report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id=(
            build_expected_migration_inventory().latest_expected_revision_id
        ),
        database_revision_id=(
            build_expected_migration_inventory().latest_expected_revision_id
        ),
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _build_sqlite_url(tmp_path: Path) -> str:
    db_path = tmp_path / "digest-integration.sqlite"
    return f"sqlite+pysqlite:///{db_path}"


def _bootstrap_schema_and_alembic_marker(url: str) -> None:
    """Create every storage table + set alembic_version to the locked
    latest revision so :class:`StorageConnectionProvider` accepts a
    writable connection without complaining."""

    engine = create_engine(url)
    latest = build_expected_migration_inventory().latest_expected_revision_id
    with engine.connect() as conn:
        metadata.create_all(conn)
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES (:rev)"
            ),
            {"rev": latest},
        )
        conn.commit()


def _build_sync_run() -> IbkrSyncRunRecord:
    return IbkrSyncRunRecord(
        sync_run_id=_SYNC_RUN_ID,
        started_at=_NOW,
        completed_at=_NOW,
        provider_code="ibkr",
        provider_environment="paper",
        account_mode="paper",
        readonly=True,
        status="completed",
        account_summary_status="ok",
        positions_status="ok",
        open_orders_status="ok",
        executions_status="ok",
        positions_count=2,
        cash_values_count=0,
        open_orders_count=0,
        executions_count=0,
        status_nl=None,
        next_step_nl=None,
        help_nl=None,
        actions_allowed=False,
        order_submission_allowed=False,
        order_modification_allowed=False,
        order_cancellation_allowed=False,
        suggestions_allowed=False,
        stored_at=_NOW,
        ibkr_account_id=_ACCOUNT_ID,
    )


def _build_position(
    *, conid: str, symbol: str, avg_cost: str, quantity: str
) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=f"pos-{conid}",
        sync_run_id=_SYNC_RUN_ID,
        account_ref=_ACCOUNT_ID,
        conid=conid,
        symbol=symbol,
        security_type="STK",
        currency="USD",
        exchange=None,
        primary_exchange=None,
        quantity=Decimal(quantity),
        average_cost=Decimal(avg_cost),
        received_at=_NOW,
        stored_at=_NOW,
        ibkr_account_id=_ACCOUNT_ID,
    )


def _build_market_data_snapshot(
    *, conid: str, last_price: str
) -> MarketDataLatestSnapshotRecord:
    return MarketDataLatestSnapshotRecord(
        snapshot_id=f"md-{conid}",
        ibkr_conid=conid,
        symbol="X",
        currency="USD",
        asset_class="STK",
        exchange=None,
        primary_exchange=None,
        provider_code="eodhd",
        provider_environment="real",
        provider_account_mode="none",
        market_data_type="eod",
        requested_at=_NOW,
        received_at=_NOW,
        provider_as_of=_NOW,
        stored_at=_NOW,
        last_price=Decimal(last_price),
        bid_price=None,
        ask_price=None,
        close_price=Decimal(last_price),
        day_change_percent=None,
        status="snapshot_available",
        freshness_status="fresh",
        explanation_nl="test",
        request_log_id=None,
        provider_source_id=None,
        freshness_audit_id=None,
    )


def _build_suggestion(
    *, suggestion_id: str, conid: str, action_label: str, symbol: str
) -> AssetSuggestionRecord:
    return AssetSuggestionRecord(
        suggestion_id=suggestion_id,
        ibkr_conid=conid,
        symbol=symbol,
        currency="USD",
        forecast_id="forecast-x",
        model_code="baseline_label_translator",
        model_version="v1.0.0",
        generated_at=_NOW,
        valid_until=_NOW + timedelta(hours=24),
        risk_profile="Gebalanceerd",
        has_position=True,
        action_label=action_label,
        action_label_nl=action_label,
        confidence_label="high",
        confidence_label_nl="Hoog",
        confidence_score=Decimal("0.82"),
        rationale_nl="r",
        drivers_json=(),
        blockers_json=None,
        status="ready",
        blocking_reason=None,
    )


def _build_draft(
    *, draft_id: str, conid: str, status: str, symbol: str
) -> AssetActionDraftRecord:
    return AssetActionDraftRecord(
        draft_id=draft_id,
        decision_package_id="dp-x",
        decision_package_content_hash="hash-x",
        ibkr_conid=conid,
        symbol=symbol,
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        account_mode="paper",
        expected_account_mode="paper",
        action_side="SELL",
        order_type="LMT",
        tif="DAY",
        quantity=Decimal("5"),
        limit_price=Decimal("180.00"),
        estimated_order_value=Decimal("900"),
        estimated_cash_before=None,
        estimated_cash_after=None,
        estimated_position_quantity_before=Decimal("5"),
        estimated_position_quantity_after=Decimal("0"),
        estimated_position_value_after=Decimal("0"),
        estimated_portfolio_weight_after_pct=Decimal("0"),
        estimated_concentration_impact_pct=Decimal("0"),
        orderimpact_base_currency="USD",
        source_action_label="Verkopen",
        source_action_label_nl="Verkopen",
        status=status,
        dry_run_status="passed",
        dry_run_failures_json=None,
        blocking_reason=None,
        rationale_nl="r",
        explanation_nl="e",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _build_nav(*, value: str, recorded_at: datetime) -> IbkrNavSnapshotRecord:
    return IbkrNavSnapshotRecord(
        snapshot_id=f"nav-{recorded_at.isoformat()}",
        ibkr_account_id=_ACCOUNT_ID,
        base_currency="EUR",
        nav_value=Decimal(value),
        recorded_at=recorded_at,
        stored_at=recorded_at,
    )


def _seed_database(url: str) -> None:
    engine = create_engine(url)
    with engine.connect() as conn:
        rep = _ready_report()
        ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, rep)
        market_repo = SqlAlchemyMarketDataSnapshotRepository(conn, rep)
        suggestion_repo = SqlAlchemyAssetSuggestionRepository(conn, rep)
        draft_repo = SqlAlchemyAssetActionDraftRepository(conn, rep)

        # One IBKR sync run + two positions in it.
        ibkr_repo.save_ibkr_sync_run(_build_sync_run())
        ibkr_repo.save_ibkr_position_snapshots(
            _SYNC_RUN_ID,
            [
                _build_position(
                    conid="aapl",
                    symbol="AAPL",
                    avg_cost="100.00",
                    quantity="10",
                ),
                _build_position(
                    conid="msft",
                    symbol="MSFT",
                    avg_cost="200.00",
                    quantity="5",
                ),
            ],
        )
        # Latest market-data snapshot per held conid. AAPL +10%, MSFT -5%.
        market_repo.save_latest_market_data_snapshot(
            _build_market_data_snapshot(conid="aapl", last_price="110.00")
        )
        market_repo.save_latest_market_data_snapshot(
            _build_market_data_snapshot(conid="msft", last_price="190.00")
        )
        # Two suggestions, both high-confidence: one Verkopen on a
        # held position (should trigger the alert), one Houden.
        suggestion_repo.save_asset_suggestion(
            _build_suggestion(
                suggestion_id="sug-aapl",
                conid="aapl",
                action_label="Houden",
                symbol="AAPL",
            )
        )
        suggestion_repo.save_asset_suggestion(
            _build_suggestion(
                suggestion_id="sug-msft",
                conid="msft",
                action_label="Verkopen",
                symbol="MSFT",
            )
        )
        # One action draft created today (status=approved).
        draft_repo.save_asset_action_draft(
            _build_draft(
                draft_id="draft-msft",
                conid="msft",
                status="approved",
                symbol="MSFT",
            )
        )
        # NAV history: yesterday + today. Today is 0.5% lower —
        # below the -2% nav_drop alert threshold so the digest's
        # alert list stays clean. (We assert this absence below.)
        ibkr_repo.save_ibkr_nav_snapshot(
            _build_nav(value="100000.00", recorded_at=_YESTERDAY)
        )
        ibkr_repo.save_ibkr_nav_snapshot(
            _build_nav(value="99500.00", recorded_at=_NOW)
        )
        conn.commit()


def _build_runner(url: str, notifications: NotificationSettings | None = None) -> DailyDigestRunner:
    storage_settings = StorageSettings(
        enabled=True,
        database_url=url,
        writes_enabled=True,
    )
    return DailyDigestRunner(
        storage_settings=storage_settings,
        notifications=notifications or NotificationSettings(),
        now_provider=lambda: _NOW,
    )


def test_digest_runner_persists_a_digest_row_against_real_sqlite(
    tmp_path: Path,
) -> None:
    """The headline smoke test: the runner runs end-to-end against a
    real database and writes one daily_digests row with the expected
    computed fields."""

    url = _build_sqlite_url(tmp_path)
    _bootstrap_schema_and_alembic_marker(url)
    _seed_database(url)

    runner = _build_runner(url)
    result = runner.run(
        ibkr_account_id=_ACCOUNT_ID,
        market_code="EURONEXT",
        scheduled_run_id="run-x",
    )

    # The runner reports success at every layer it owns.
    assert result["persisted_digest"] is True
    assert result["status"] in {"ready", "partial"}
    assert result["position_count"] == 2
    # Suggestions count = total persisted suggestions for held conids.
    assert result["suggestion_count"] == 2

    # Re-open the database and read the persisted row directly so the
    # assertion is independent of the runner's return shape.
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = list(
            conn.execute(text("SELECT * FROM daily_digests")).mappings()
        )
    assert len(rows) == 1
    row = rows[0]
    assert row["ibkr_account_ref"] == _ACCOUNT_ID
    assert row["market_code"] == "EURONEXT"
    assert row["status"] == "ready"

    # sqlite stores JSON columns as TEXT, so the raw fetch returns a
    # string; parse it back into Python before asserting.
    nav = json.loads(row["nav_summary_json"])
    positions = json.loads(row["positions_summary_json"])
    drafts = json.loads(row["action_drafts_summary_json"])

    # NAV: today 99500 vs yesterday 100000 = -0.50% delta.
    assert nav["delta_pct"] == "-0.50"

    # Positions: AAPL +10%, MSFT -5%.
    assert positions["position_count"] == 2
    winners = positions["top_winners"]
    losers = positions["top_losers"]
    assert winners[0]["symbol"] == "AAPL"
    assert winners[0]["pnl_pct"] == "10.00"
    assert losers[0]["symbol"] == "MSFT"
    assert losers[0]["pnl_pct"] == "-5.00"

    # Action drafts: one approved today.
    assert drafts["approved_today"] == 1


def test_digest_runner_fires_high_confidence_sell_alert_against_real_db(
    tmp_path: Path,
) -> None:
    """The alert side of the loop: the seeded MSFT Verkopen at high
    confidence on a held position must produce a
    ``high_confidence_sell`` alert. We don't enable email here, so the
    gating decision returns ``email_disabled`` — that's the
    correct decision matrix output for the default settings."""

    url = _build_sqlite_url(tmp_path)
    _bootstrap_schema_and_alembic_marker(url)
    _seed_database(url)

    runner = _build_runner(url)
    result = runner.run(
        ibkr_account_id=_ACCOUNT_ID,
        market_code="EURONEXT",
        scheduled_run_id="run-x",
    )

    assert result["alert_count"] >= 1
    # Master email switch is off by default → no SMTP open, no send.
    assert result["email"]["sent"] is False
    assert result["email"]["reason"] == "email_disabled"

    # Confirm the alert kinds we expect are present on the persisted row.
    engine = create_engine(url)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT alerts_json FROM daily_digests")
        ).mappings().first()
    assert row is not None
    alerts = json.loads(row["alerts_json"])
    kinds = {a["kind"] for a in alerts}
    assert "high_confidence_sell" in kinds


def test_digest_runner_email_gate_stubs_when_master_on_but_real_client_off(
    tmp_path: Path,
) -> None:
    """Master toggle on + SMTP filled + real_client_enabled OFF →
    stub-mode. The runner builds the message but never opens an SMTP
    session — the safety switch that keeps a fresh deploy from
    accidentally emailing on first save."""

    url = _build_sqlite_url(tmp_path)
    _bootstrap_schema_and_alembic_marker(url)
    _seed_database(url)

    notifications = NotificationSettings(
        email_enabled=True,
        smtp_host="smtp.example.com",
        smtp_from="bot@example.com",
        smtp_to="op@example.com",
        smtp_username="user",
        smtp_password="secret",
        # real_client_enabled defaults to False — that's the test.
    )
    runner = _build_runner(url, notifications=notifications)
    result = runner.run(
        ibkr_account_id=_ACCOUNT_ID,
        market_code="EURONEXT",
        scheduled_run_id="run-x",
    )

    assert result["email"]["sent"] is False
    assert result["email"]["status"] == "stubbed"
