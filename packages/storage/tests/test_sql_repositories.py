from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from ai_trading_agent_storage.repository_contracts import (
    BrokerAccountRecord,
    BrokerSyncRunRecord,
    CreatePaperPortfolioSetupRequest,
    CreateSystemEventRequest,
    FxRateSnapshotRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrExecutionSnapshotRecord,
    IbkrOpenOrderSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    SaveTradingSettingsRequest,
)
from ai_trading_agent_storage.sql_repositories import (
    SqlAlchemyBrokerAccountRepository,
    SqlAlchemyBrokerStorageUnitOfWork,
    SqlAlchemyBrokerSyncRunRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyPaperPortfolioSetupRepository,
    SqlAlchemySystemEventRepository,
    SqlAlchemyTradingSettingsRepository,
    StoragePersistenceBlockedError,
    ensure_persistence_allowed,
)


def _report(allowed: bool) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=(
            MigrationReadinessStatus.MIGRATIONS_CURRENT
            if allowed
            else MigrationReadinessStatus.NOT_CONNECTED
        ),
        database_connected=allowed,
        migrations_checked_against_database=allowed,
        offline_inventory_valid=True,
        latest_expected_revision_id="0011",
        database_revision_id="0011" if allowed else None,
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


def test_guard_blocks_when_not_allowed() -> None:
    with pytest.raises(StoragePersistenceBlockedError):
        ensure_persistence_allowed(_report(False))


def test_account_and_sync_roundtrip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        account_repo = SqlAlchemyBrokerAccountRepository(conn, _report(True))
        account = BrokerAccountRecord(
            "a1",
            "ibkr",
            None,
            "main",
            "paper",
            "connected",
            True,
            True,
            False,
            "broker",
            datetime.now(UTC),
            None,
            "ok",
        )
        account_repo.save_account(account)
        assert account_repo.get_by_id("a1").found
        assert len(account_repo.list_accounts().records) == 1

        sync_repo = SqlAlchemyBrokerSyncRunRepository(conn, _report(True))
        run = BrokerSyncRunRecord(
            "r1",
            "a1",
            "ibkr",
            "manual",
            "done",
            datetime.now(UTC),
            None,
            ("positions",),
            ("ibkr",),
            False,
            False,
            False,
            "sam",
            "help",
            None,
            None,
        )
        sync_repo.save_sync_run(run)
        assert sync_repo.get_by_id("r1").found
        assert sync_repo.list_for_account("a1").records[0].planned_data_kinds_json == ("positions",)


def test_write_blocked() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        account_repo = SqlAlchemyBrokerAccountRepository(conn, _report(False))
        account = BrokerAccountRecord(
            "a2",
            "ibkr",
            None,
            "main",
            "paper",
            "connected",
            True,
            True,
            False,
            "broker",
            datetime.now(UTC),
            None,
            "ok",
        )
        with pytest.raises(StoragePersistenceBlockedError):
            account_repo.save_account(account)


def test_uow_health_and_noop_transaction_methods() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        uow = SqlAlchemyBrokerStorageUnitOfWork(conn, _report(True))
        assert uow.health().available
        uow.commit()
        uow.rollback()


def test_paper_setup_roundtrip_decimal_and_latest() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(True))
        request = CreatePaperPortfolioSetupRequest(
            setup_id="setup-1",
            portfolio_name="Paper Start",
            base_currency="eur",
            starting_cash_amount=Decimal("1500.250000"),
            status="active",
            created_at=datetime.now(UTC),
            explanation_nl="Eerste papieren portfolio-opzet.",
        )

        write_result = repo.create_setup(request)
        assert write_result.accepted
        by_id_result = repo.get_by_id("setup-1")
        assert by_id_result.found
        assert by_id_result.record is not None
        assert isinstance(by_id_result.record.starting_cash_amount, Decimal)
        assert by_id_result.record.starting_cash_amount == Decimal("1500.250000")

        latest = repo.get_latest()
        assert latest.found
        assert latest.record is not None
        assert latest.record.setup_id == "setup-1"


def test_paper_setup_missing_record_returns_not_found() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(True))
        assert repo.get_by_id("missing").found is False
        assert repo.get_latest().found is False


def test_paper_setup_write_blocked_and_allowed_by_readiness() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        blocked = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(False))
        request = CreatePaperPortfolioSetupRequest(
            setup_id="setup-blocked",
            portfolio_name="Blocked",
            base_currency="eur",
            starting_cash_amount=Decimal("100.00"),
            status="active",
            created_at=datetime.now(UTC),
            explanation_nl="Geblokkeerde schrijfactie test.",
        )
        with pytest.raises(StoragePersistenceBlockedError):
            blocked.create_setup(request)

        allowed = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(True))
        result = allowed.create_setup(request)
        assert result.accepted is True


def test_paper_setup_duplicate_and_invalid_writes_surface() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(True))
        base_request = CreatePaperPortfolioSetupRequest(
            setup_id="setup-dup",
            portfolio_name="Dup",
            base_currency="eur",
            starting_cash_amount=Decimal("100.00"),
            status="active",
            created_at=datetime.now(UTC),
            explanation_nl="Duplicaat test.",
        )
        repo.create_setup(base_request)
        with pytest.raises(IntegrityError):
            repo.create_setup(base_request)

        invalid_currency = CreatePaperPortfolioSetupRequest(
            setup_id="setup-invalid",
            portfolio_name="Invalid",
            base_currency="usd",
            starting_cash_amount=Decimal("100.00"),
            status="active",
            created_at=datetime.now(UTC),
            explanation_nl="Constraint test.",
        )
        with pytest.raises(IntegrityError):
            repo.create_setup(invalid_currency)


def test_system_event_create_read_list_and_flags() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemySystemEventRepository(conn, _report(True))
        request = CreateSystemEventRequest(
            system_event_id="se-1",
            created_at=datetime.now(UTC),
            severity="error",
            category="storage",
            source_service="api",
            source_component="startup",
            event_code="storage_blocked",
            title_nl="Opslag geblokkeerd",
            message_nl="Schrijven is geblokkeerd.",
            help_nl="Controleer migraties.",
            technical_summary="alembic mismatch",
            redacted_details_json={"database_url": "***"},
            stack_trace_redacted="trace",
            related_entity_type="migration",
            related_entity_id="0007",
            blocks_suggestions=True,
            blocks_writes=True,
            blocks_ai_explanation=False,
            status="open",
            explanation_nl="Systeemmelding geregistreerd.",
        )
        repo.create_event(request)
        by_id = repo.get_by_id("se-1")
        assert by_id.found
        assert by_id.record is not None
        assert by_id.record.severity == "error"
        assert by_id.record.category == "storage"
        assert by_id.record.status == "open"
        assert by_id.record.blocks_suggestions is True
        assert by_id.record.blocks_writes is True
        assert by_id.record.redacted_details_json == {"database_url": "***"}

        second = CreateSystemEventRequest(
            **{**request.__dict__, "system_event_id": "se-2", "status": "resolved"}
        )
        repo.create_event(second)
        open_events = repo.list_open_events()
        assert [item.system_event_id for item in open_events.records] == ["se-1"]


def test_system_event_write_blocked_and_missing_and_no_delete() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        blocked_repo = SqlAlchemySystemEventRepository(conn, _report(False))
        request = CreateSystemEventRequest(
            system_event_id="se-blocked",
            created_at=datetime.now(UTC),
            severity="warning",
            category="api",
            source_service="api",
            source_component="guard",
            event_code="blocked",
            title_nl="Geblokkeerd",
            message_nl="Geen write",
            help_nl="Wacht",
            technical_summary=None,
            redacted_details_json=None,
            stack_trace_redacted=None,
            related_entity_type=None,
            related_entity_id=None,
            blocks_suggestions=False,
            blocks_writes=False,
            blocks_ai_explanation=False,
            status="open",
            explanation_nl="Test",
        )
        with pytest.raises(StoragePersistenceBlockedError):
            blocked_repo.create_event(request)

        allowed_repo = SqlAlchemySystemEventRepository(conn, _report(True))
        assert allowed_repo.get_by_id("missing").found is False
        assert allowed_repo.mark_resolved("missing").accepted is False
        assert allowed_repo.mark_archived("missing").accepted is False
        assert hasattr(allowed_repo, "delete") is False


def test_system_event_resolve_and_archive_hide_from_open_list() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemySystemEventRepository(conn, _report(True))
        create = CreateSystemEventRequest(
            system_event_id="se-open",
            created_at=datetime.now(UTC),
            severity="warning",
            category="api",
            source_service="api",
            source_component="events",
            event_code="open_event",
            title_nl="Open event",
            message_nl="Open event message",
            help_nl="Help",
            technical_summary=None,
            redacted_details_json=None,
            stack_trace_redacted=None,
            related_entity_type=None,
            related_entity_id=None,
            blocks_suggestions=False,
            blocks_writes=False,
            blocks_ai_explanation=False,
            status="open",
            explanation_nl="Open",
        )
        repo.create_event(create)
        assert [item.system_event_id for item in repo.list_open_events().records] == ["se-open"]

        resolved = repo.mark_resolved("se-open", reason_nl="Handmatig opgelost")
        assert resolved.accepted is True
        after_resolve = repo.get_by_id("se-open")
        assert after_resolve.record is not None
        assert after_resolve.record.status == "resolved"
        assert after_resolve.record.resolved_at is not None
        assert repo.list_open_events().records == ()

        second = CreateSystemEventRequest(**{**create.__dict__, "system_event_id": "se-open-2"})
        repo.create_event(second)
        archived = repo.mark_archived("se-open-2", reason_nl="Niet meer relevant")
        assert archived.accepted is True
        after_archive = repo.get_by_id("se-open-2")
        assert after_archive.record is not None
        assert after_archive.record.status == "archived"
        assert after_archive.record.archived_at is not None
        assert repo.list_open_events().records == ()


def test_ibkr_sync_repository_roundtrip_and_lists() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    now = datetime.now(UTC)
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, _report(True))
        run = IbkrSyncRunRecord(
            sync_run_id="sync-1",
            started_at=now,
            completed_at=now,
            provider_code="ibkr",
            provider_environment="paper",
            account_mode="paper",
            readonly=True,
            status="completed",
            account_summary_status="ok",
            positions_status="ok",
            open_orders_status="ok",
            executions_status="ok",
            positions_count=1,
            cash_values_count=1,
            open_orders_count=1,
            executions_count=1,
            status_nl=None,
            next_step_nl=None,
            help_nl=None,
            actions_allowed=False,
            order_submission_allowed=False,
            order_modification_allowed=False,
            order_cancellation_allowed=False,
            suggestions_allowed=False,
            stored_at=now,
        )
        repo.save_ibkr_sync_run(run)
        loaded_run = repo.get_ibkr_sync_run("sync-1")
        assert loaded_run is not None
        assert loaded_run.sync_run_id == run.sync_run_id
        assert loaded_run.actions_allowed is False
        assert repo.get_ibkr_sync_run("missing") is None
        latest_run = repo.get_latest_ibkr_sync_run()
        assert latest_run is not None
        assert latest_run.sync_run_id == run.sync_run_id
        assert len(repo.list_ibkr_sync_runs(limit=5)) == 1

        cash = IbkrAccountCashSnapshotRecord(
            "c1", "sync-1", None, "EUR", Decimal("1.2"), None, None, now, now
        )
        pos = IbkrPositionSnapshotRecord(
            "p1",
            "sync-1",
            None,
            None,
            "AAPL",
            "STK",
            "USD",
            None,
            None,
            Decimal("2"),
            None,
            now,
            now,
        )
        order = IbkrOpenOrderSnapshotRecord(
            "o1", "sync-1", None, 1, None, None, None, "AAPL", "STK", "USD",
            None, None, "BUY", "LMT", Decimal("1"), None, None, None, "Submitted",
            Decimal("0"), Decimal("1"), None, None, None, now, now
        )
        exe = IbkrExecutionSnapshotRecord(
            "e1", "sync-1", None, "exec-1", None, None, "AAPL", "STK", "USD",
            None, None, "BUY", Decimal("1"), Decimal("10"), now, None, None,
            None, None, now, now
        )

        repo.save_ibkr_account_cash_snapshots("sync-1", [cash])
        repo.save_ibkr_position_snapshots("sync-1", [pos])
        repo.save_ibkr_open_order_snapshots("sync-1", [order])
        repo.save_ibkr_execution_snapshots("sync-1", [exe])

        loaded_cash = repo.list_ibkr_account_cash_snapshots("sync-1")
        loaded_positions = repo.list_ibkr_position_snapshots("sync-1")
        loaded_orders = repo.list_ibkr_open_order_snapshots("sync-1")
        loaded_executions = repo.list_ibkr_execution_snapshots("sync-1")
        assert loaded_cash[0].snapshot_id == "c1"
        assert isinstance(loaded_cash[0].cash, Decimal)
        assert loaded_cash[0].available_funds is None
        assert loaded_positions[0].snapshot_id == "p1"
        assert isinstance(loaded_positions[0].quantity, Decimal)
        assert loaded_orders[0].snapshot_id == "o1"
        assert isinstance(loaded_orders[0].quantity, Decimal)
        assert loaded_executions[0].snapshot_id == "e1"
        assert isinstance(loaded_executions[0].price, Decimal)


def test_trading_settings_save_read_update_and_not_found() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyTradingSettingsRepository(conn, _report(True))
        missing = repo.get_settings("missing")
        assert missing.found is False

        first = SaveTradingSettingsRequest(
            settings_id="default",
            allowed_universe={"max_pct_per_sector": "10"},
            user_strategy={"max_pct_per_positie": "5"},
            source="instellingen",
            status="actief",
            explanation_nl="Eerste instellingen opgeslagen.",
            updated_at=datetime.now(UTC),
        )
        repo.save_settings(first)
        saved = repo.get_settings()
        assert saved.found is True
        assert saved.record is not None
        assert saved.record.version == 1
        assert saved.record.allowed_universe["max_pct_per_sector"] == "10"
        assert saved.record.user_strategy["max_pct_per_positie"] == "5"

        second = SaveTradingSettingsRequest(
            settings_id="default",
            allowed_universe={"max_pct_per_sector": "15"},
            user_strategy={"max_pct_per_positie": "6"},
            source="instellingen",
            status="actief",
            explanation_nl="Instellingen bijgewerkt.",
            updated_at=datetime.now(UTC),
        )
        repo.save_settings(second)
        updated = repo.get_settings()
        assert updated.record is not None
        assert updated.record.version == 2
        assert updated.record.allowed_universe["max_pct_per_sector"] == "15"


def test_trading_settings_write_blocked_until_readiness_safe() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        blocked = SqlAlchemyTradingSettingsRepository(conn, _report(False))
        with pytest.raises(StoragePersistenceBlockedError):
            blocked.save_settings(
                SaveTradingSettingsRequest(
                    settings_id="default",
                    allowed_universe={"a": "10"},
                    user_strategy={"b": "5"},
                    source="instellingen",
                    status="actief",
                    explanation_nl="Geblokkeerd.",
                    updated_at=datetime.now(UTC),
                )
            )


def test_fx_rate_snapshot_roundtrip_and_latest_lookup() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    now = datetime.now(UTC)
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, _report(True))
        older = FxRateSnapshotRecord(
            snapshot_id="fx-1",
            provider="ecb",
            source="daily",
            base_currency="eur",
            quote_currency="usd",
            pair="eur/usd",
            rate=Decimal("1.08765"),
            rate_type="reference",
            as_of=now,
            received_at=now,
            stored_at=now,
            freshness_status="fresh",
            validation_status="valid",
            reason_code="ok",
            metadata_json={"batch": "a"},
        )
        newer = FxRateSnapshotRecord(
            snapshot_id="fx-2",
            provider="ecb",
            source="daily",
            base_currency="EUR",
            quote_currency="USD",
            pair="EUR/USD",
            rate=Decimal("1.09765"),
            rate_type="reference",
            as_of=now.replace(year=now.year),
            received_at=now.replace(year=now.year),
            stored_at=now.replace(year=now.year),
            freshness_status="stale",
            validation_status="invalid",
            reason_code="old",
            metadata_json=None,
        )
        repo.save_fx_rate_snapshot(older)
        repo.save_fx_rate_snapshot(newer)
        loaded = repo.get_fx_rate_snapshot("fx-1")
        assert loaded is not None
        assert loaded.base_currency == "EUR"
        assert loaded.quote_currency == "USD"
        assert loaded.pair == "EUR/USD"
        assert isinstance(loaded.rate, Decimal)
        assert loaded.rate == Decimal("1.08765")
        latest = repo.get_latest_fx_rate_snapshot("eur", "usd")
        assert latest is not None
        assert latest.snapshot_id == "fx-2"
        by_pairs = repo.list_latest_fx_rate_snapshots_by_pairs(("EUR/USD", "GBP/USD"))
        assert len(by_pairs) == 1
        assert by_pairs[0].snapshot_id == "fx-2"


def test_market_data_bars_save_and_list_returns_chronological() -> None:
    from datetime import date

    from ai_trading_agent_storage.repository_contracts import MarketDataBarRecord
    from ai_trading_agent_storage.sql_repositories import SqlAlchemyMarketDataBarRepository

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyMarketDataBarRepository(conn, _report(True))
        now = datetime(2025, 5, 24, 10, 0, tzinfo=UTC)

        def _bar(bar_id: str, day: int, close: str) -> MarketDataBarRecord:
            return MarketDataBarRecord(
                bar_id=bar_id,
                ibkr_conid="265598",
                symbol="AAPL",
                currency="USD",
                exchange="SMART",
                primary_exchange="NASDAQ",
                provider_code="eodhd",
                bar_date=date(2025, 5, day),
                interval_code="1day",
                open_price=Decimal("100"),
                high_price=Decimal("105"),
                low_price=Decimal("99"),
                close_price=Decimal(close),
                adjusted_close_price=Decimal(close),
                volume=Decimal("1000000"),
                provider_as_of=now,
                received_at=now,
                stored_at=now,
                source_type="eodhd_eod",
                explanation_nl="test",
            )

        repo.save_market_data_bars(
            [_bar("b1", 21, "180"), _bar("b2", 22, "182"), _bar("b3", 23, "181")]
        )

        bars = repo.list_market_data_bars_by_conid("265598")
        assert len(bars.records) == 3
        # Chronological (asc by bar_date)
        assert [r.bar_id for r in bars.records] == ["b1", "b2", "b3"]
        assert bars.records[-1].close_price == Decimal("181")


def test_asset_forecast_save_get_and_list_returns_latest_per_conid() -> None:
    from datetime import date

    from ai_trading_agent_storage.repository_contracts import AssetForecastRecord
    from ai_trading_agent_storage.sql_repositories import SqlAlchemyAssetForecastRepository

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyAssetForecastRepository(conn, _report(True))

        def _forecast(forecast_id: str, conid: str, generated_hour: int) -> AssetForecastRecord:
            return AssetForecastRecord(
                forecast_id=forecast_id,
                ibkr_conid=conid,
                symbol="AAPL",
                currency="USD",
                model_code="baseline_gbm",
                model_version="v1",
                horizon_days=21,
                generated_at=datetime(2025, 5, 24, generated_hour, 0, tzinfo=UTC),
                valid_until=datetime(2025, 6, 14, generated_hour, 0, tzinfo=UTC),
                data_points_used=200,
                history_first_bar_date=date(2024, 8, 1),
                history_last_bar_date=date(2025, 5, 23),
                current_price=Decimal("180"),
                expected_return_pct=Decimal("0.5"),
                p10_price=Decimal("170"),
                p50_price=Decimal("181"),
                p90_price=Decimal("192"),
                prob_gain=Decimal("0.55"),
                prob_loss=Decimal("0.45"),
                prob_loss_gt_5pct=Decimal("0.20"),
                prob_loss_gt_10pct=Decimal("0.05"),
                prob_gain_gt_5pct=Decimal("0.25"),
                prob_gain_gt_10pct=Decimal("0.08"),
                expected_volatility_annual=Decimal("0.22"),
                downside_risk_score=Decimal("0.10"),
                confidence_score=Decimal("0.85"),
                direction_label="slight_up",
                direction_label_nl="Lichte stijging verwacht",
                explanation_nl="baseline gbm",
                status="ready",
                blocking_reason=None,
            )

        repo.save_asset_forecast(_forecast("f1", "265598", 9))
        repo.save_asset_forecast(_forecast("f2", "265598", 10))  # newer for same conid
        repo.save_asset_forecast(_forecast("f3", "272093", 9))

        latest = repo.get_latest_asset_forecast_by_conid("265598")
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.forecast_id == "f2"

        listed = repo.list_latest_asset_forecasts_by_conids(("265598", "272093", "999"))
        assert len(listed.records) == 2
        ids = {r.forecast_id for r in listed.records}
        assert ids == {"f2", "f3"}


def test_asset_forecast_record_rejects_safe_flags_true() -> None:
    from datetime import date

    from ai_trading_agent_storage.repository_contracts import AssetForecastRecord

    with pytest.raises(ValueError):
        AssetForecastRecord(
            forecast_id="x",
            ibkr_conid="1",
            symbol="X",
            currency="USD",
            model_code="baseline_gbm",
            model_version="v1",
            horizon_days=21,
            generated_at=datetime.now(UTC),
            valid_until=datetime.now(UTC),
            data_points_used=100,
            history_first_bar_date=date(2024, 1, 1),
            history_last_bar_date=date(2025, 1, 1),
            current_price=Decimal("100"),
            expected_return_pct=Decimal("0"),
            p10_price=Decimal("90"),
            p50_price=Decimal("100"),
            p90_price=Decimal("110"),
            prob_gain=Decimal("0.5"),
            prob_loss=Decimal("0.5"),
            prob_loss_gt_5pct=Decimal("0.1"),
            prob_loss_gt_10pct=Decimal("0.0"),
            prob_gain_gt_5pct=Decimal("0.1"),
            prob_gain_gt_10pct=Decimal("0.0"),
            expected_volatility_annual=Decimal("0.2"),
            downside_risk_score=Decimal("0.1"),
            confidence_score=Decimal("0.8"),
            direction_label="neutral",
            direction_label_nl="Neutraal",
            explanation_nl="test",
            status="ready",
            blocking_reason=None,
            safe_for_analysis=True,
        )


def test_asset_suggestion_repository_persists_and_returns_latest_per_conid() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetSuggestionRecord
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyAssetSuggestionRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyAssetSuggestionRepository(conn, _report(True))

        def _record(suggestion_id: str, conid: str, generated_hour: int) -> AssetSuggestionRecord:
            return AssetSuggestionRecord(
                suggestion_id=suggestion_id,
                ibkr_conid=conid,
                symbol="AAPL",
                currency="USD",
                forecast_id="forecast-x",
                model_code="baseline_label_translator",
                model_version="v1.0.0",
                generated_at=datetime(2025, 5, 24, generated_hour, 0, tzinfo=UTC),
                valid_until=datetime(2025, 6, 14, generated_hour, 0, tzinfo=UTC),
                risk_profile="Gebalanceerd",
                has_position=True,
                action_label="Houden",
                action_label_nl="Houden",
                confidence_label="Hoog",
                confidence_label_nl="Hoog",
                confidence_score=Decimal("0.82"),
                rationale_nl="test rationale",
                drivers_json=("direction_label=neutral", "prob_gain=0.5"),
                blockers_json=None,
                status="ready",
                blocking_reason=None,
            )

        repo.save_asset_suggestion(_record("s1", "265598", 9))
        repo.save_asset_suggestion(_record("s2", "265598", 11))  # newer
        repo.save_asset_suggestion(_record("s3", "272093", 9))

        latest = repo.get_latest_asset_suggestion_by_conid("265598")
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.suggestion_id == "s2"
        assert latest.record.drivers_json == ("direction_label=neutral", "prob_gain=0.5")

        listed = repo.list_latest_asset_suggestions_by_conids(("265598", "272093", "999"))
        assert {r.suggestion_id for r in listed.records} == {"s2", "s3"}


def test_asset_suggestion_record_rejects_safety_flags_true() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetSuggestionRecord

    with pytest.raises(ValueError):
        AssetSuggestionRecord(
            suggestion_id="x",
            ibkr_conid="1",
            symbol="X",
            currency="USD",
            forecast_id=None,
            model_code="baseline_label_translator",
            model_version="v1",
            generated_at=datetime.now(UTC),
            valid_until=datetime.now(UTC),
            risk_profile="Gebalanceerd",
            has_position=False,
            action_label="Kopen",
            action_label_nl="Kopen",
            confidence_label="Hoog",
            confidence_label_nl="Hoog",
            confidence_score=Decimal("0.8"),
            rationale_nl="test",
            drivers_json=None,
            blockers_json=None,
            status="ready",
            blocking_reason=None,
            safe_for_orders=True,
        )


def test_asset_decision_package_repository_persists_and_returns_latest() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetDecisionPackageRecord
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyAssetDecisionPackageRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyAssetDecisionPackageRepository(conn, _report(True))

        def _pkg(pkg_id: str, conid: str, hour: int) -> AssetDecisionPackageRecord:
            return AssetDecisionPackageRecord(
                decision_package_id=pkg_id,
                content_hash=f"hash-{pkg_id}",
                ibkr_conid=conid,
                symbol="AAPL",
                currency="USD",
                risk_profile="Gebalanceerd",
                generated_at=datetime(2025, 5, 24, hour, 0, tzinfo=UTC),
                valid_until=datetime(2025, 6, 14, hour, 0, tzinfo=UTC),
                position_snapshot_id="pos-1",
                position_quantity=Decimal("10"),
                position_average_cost=Decimal("150.0"),
                cash_snapshot_id="cash-1",
                cash_base_currency="USD",
                cash_amount=Decimal("5000"),
                market_snapshot_id="md-1",
                market_last_price=Decimal("180"),
                market_freshness_status="fresh",
                market_provider_code="eodhd",
                market_provider_as_of=datetime(2025, 5, 23, tzinfo=UTC),
                fx_pair=None,
                fx_rate=None,
                fx_freshness_status=None,
                forecast_id="forecast-1",
                forecast_model_code="baseline_gbm",
                forecast_model_version="v1.0.0",
                forecast_horizon_days=21,
                forecast_p10_price=Decimal("170"),
                forecast_p50_price=Decimal("182"),
                forecast_p90_price=Decimal("194"),
                forecast_prob_gain=Decimal("0.6"),
                forecast_prob_loss=Decimal("0.4"),
                forecast_expected_return_pct=Decimal("1.1"),
                forecast_expected_volatility_annual=Decimal("0.22"),
                forecast_downside_risk_score=Decimal("5.5"),
                forecast_confidence_score=Decimal("0.82"),
                suggestion_id="suggestion-1",
                suggestion_model_code="baseline_label_translator",
                suggestion_action_label="Houden",
                suggestion_action_label_nl="Houden",
                suggestion_confidence_label="Hoog",
                suggestion_confidence_label_nl="Hoog",
                suggestion_status="ready",
                has_position=True,
                gate_outcomes_json=("market_data_fresh", "forecast_ready"),
                evidence_links_json=None,
                audit_links_json=("ibkr-sync-run:abc", "market-data-sync-run:def"),
                rationale_nl="Test rationale.",
                explanation_nl="Test explanation.",
                status="ready",
                blocking_reason=None,
            )

        repo.save_asset_decision_package(_pkg("dp-1", "265598", 9))
        repo.save_asset_decision_package(_pkg("dp-2", "265598", 11))  # newer
        repo.save_asset_decision_package(_pkg("dp-3", "272093", 9))

        latest = repo.get_latest_asset_decision_package_by_conid("265598")
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.decision_package_id == "dp-2"
        assert latest.record.gate_outcomes_json == ("market_data_fresh", "forecast_ready")
        assert latest.record.audit_links_json == (
            "ibkr-sync-run:abc",
            "market-data-sync-run:def",
        )
        # Research evidence columns default to the "no_research" baseline
        # when the record is built without explicit research summary.
        assert latest.record.research_evidence_count == 0
        assert latest.record.research_credibility_summary is None
        assert latest.record.research_freshness_status is None
        assert latest.record.research_blocking_reason is None
        assert latest.record.research_snippet_nl is None

        listed = repo.list_latest_asset_decision_packages_by_conids(("265598", "272093"))
        assert {r.decision_package_id for r in listed.records} == {"dp-2", "dp-3"}


def test_asset_decision_package_repository_persists_research_evidence_fields() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetDecisionPackageRecord
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyAssetDecisionPackageRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyAssetDecisionPackageRepository(conn, _report(True))

        record = AssetDecisionPackageRecord(
            decision_package_id="dp-research-1",
            content_hash="hash-research-1",
            ibkr_conid="265598",
            symbol="AAPL",
            currency="USD",
            risk_profile="Gebalanceerd",
            generated_at=datetime(2025, 5, 24, 9, 0, tzinfo=UTC),
            valid_until=datetime(2025, 6, 14, 9, 0, tzinfo=UTC),
            position_snapshot_id=None,
            position_quantity=None,
            position_average_cost=None,
            cash_snapshot_id=None,
            cash_base_currency=None,
            cash_amount=None,
            market_snapshot_id=None,
            market_last_price=None,
            market_freshness_status=None,
            market_provider_code=None,
            market_provider_as_of=None,
            fx_pair=None,
            fx_rate=None,
            fx_freshness_status=None,
            forecast_id=None,
            forecast_model_code=None,
            forecast_model_version=None,
            forecast_horizon_days=None,
            forecast_p10_price=None,
            forecast_p50_price=None,
            forecast_p90_price=None,
            forecast_prob_gain=None,
            forecast_prob_loss=None,
            forecast_expected_return_pct=None,
            forecast_expected_volatility_annual=None,
            forecast_downside_risk_score=None,
            forecast_confidence_score=None,
            suggestion_id="suggestion-1",
            suggestion_model_code="baseline_label_translator",
            suggestion_action_label="Bekijken",
            suggestion_action_label_nl="Bekijken",
            suggestion_confidence_label="Laag",
            suggestion_confidence_label_nl="Laag",
            suggestion_status="control_needed",
            has_position=False,
            gate_outcomes_json=None,
            evidence_links_json=None,
            audit_links_json=None,
            rationale_nl="Test rationale.",
            explanation_nl="Test explanation.",
            status="control_needed",
            blocking_reason=None,
            research_evidence_count=2,
            research_credibility_summary="high",
            research_freshness_status="fresh",
            research_blocking_reason=None,
            research_snippet_nl="2 onderzoeksbron(nen) gekoppeld; hoge credibility, vers.",
        )
        repo.save_asset_decision_package(record)
        latest = repo.get_latest_asset_decision_package_by_conid("265598")
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.research_evidence_count == 2
        assert latest.record.research_credibility_summary == "high"
        assert latest.record.research_freshness_status == "fresh"
        assert latest.record.research_blocking_reason is None
        assert "hoge credibility" in (latest.record.research_snippet_nl or "")


def test_asset_decision_package_rejects_negative_research_evidence_count() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetDecisionPackageRecord

    with pytest.raises(ValueError, match="non-negative"):
        AssetDecisionPackageRecord(
            decision_package_id="dp-x",
            content_hash="hash-x",
            ibkr_conid="265598",
            symbol="AAPL",
            currency="USD",
            risk_profile="Gebalanceerd",
            generated_at=datetime(2025, 5, 24, tzinfo=UTC),
            valid_until=datetime(2025, 6, 14, tzinfo=UTC),
            position_snapshot_id=None,
            position_quantity=None,
            position_average_cost=None,
            cash_snapshot_id=None,
            cash_base_currency=None,
            cash_amount=None,
            market_snapshot_id=None,
            market_last_price=None,
            market_freshness_status=None,
            market_provider_code=None,
            market_provider_as_of=None,
            fx_pair=None,
            fx_rate=None,
            fx_freshness_status=None,
            forecast_id=None,
            forecast_model_code=None,
            forecast_model_version=None,
            forecast_horizon_days=None,
            forecast_p10_price=None,
            forecast_p50_price=None,
            forecast_p90_price=None,
            forecast_prob_gain=None,
            forecast_prob_loss=None,
            forecast_expected_return_pct=None,
            forecast_expected_volatility_annual=None,
            forecast_downside_risk_score=None,
            forecast_confidence_score=None,
            suggestion_id=None,
            suggestion_model_code=None,
            suggestion_action_label="Houden",
            suggestion_action_label_nl="Houden",
            suggestion_confidence_label="Hoog",
            suggestion_confidence_label_nl="Hoog",
            suggestion_status="ready",
            has_position=False,
            gate_outcomes_json=None,
            evidence_links_json=None,
            audit_links_json=None,
            rationale_nl="ok",
            explanation_nl="ok",
            status="ready",
            blocking_reason=None,
            research_evidence_count=-1,
        )


def test_asset_decision_package_rejects_safety_flags_true() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetDecisionPackageRecord

    with pytest.raises(ValueError):
        AssetDecisionPackageRecord(
            decision_package_id="dp",
            content_hash="hash",
            ibkr_conid="1",
            symbol="X",
            currency="USD",
            risk_profile="Gebalanceerd",
            generated_at=datetime.now(UTC),
            valid_until=datetime.now(UTC),
            position_snapshot_id=None,
            position_quantity=None,
            position_average_cost=None,
            cash_snapshot_id=None,
            cash_base_currency=None,
            cash_amount=None,
            market_snapshot_id=None,
            market_last_price=None,
            market_freshness_status=None,
            market_provider_code=None,
            market_provider_as_of=None,
            fx_pair=None,
            fx_rate=None,
            fx_freshness_status=None,
            forecast_id=None,
            forecast_model_code=None,
            forecast_model_version=None,
            forecast_horizon_days=None,
            forecast_p10_price=None,
            forecast_p50_price=None,
            forecast_p90_price=None,
            forecast_prob_gain=None,
            forecast_prob_loss=None,
            forecast_expected_return_pct=None,
            forecast_expected_volatility_annual=None,
            forecast_downside_risk_score=None,
            forecast_confidence_score=None,
            suggestion_id=None,
            suggestion_model_code=None,
            suggestion_action_label="Houden",
            suggestion_action_label_nl="Houden",
            suggestion_confidence_label="Middel",
            suggestion_confidence_label_nl="Middel",
            suggestion_status="ready",
            has_position=False,
            gate_outcomes_json=None,
            evidence_links_json=None,
            audit_links_json=None,
            rationale_nl="r",
            explanation_nl="e",
            status="ready",
            blocking_reason=None,
            safe_for_action_drafts=True,  # invalid
        )


def test_asset_action_draft_repository_roundtrip() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetActionDraftRecord
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyAssetActionDraftRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyAssetActionDraftRepository(conn, _report(True))

        def _draft(draft_id: str, conid: str, hour: int) -> AssetActionDraftRecord:
            return AssetActionDraftRecord(
                draft_id=draft_id,
                decision_package_id="dp-1",
                decision_package_content_hash="hash-1",
                ibkr_conid=conid,
                symbol="AAPL",
                currency="USD",
                exchange="SMART",
                primary_exchange="NASDAQ",
                account_mode="paper",
                expected_account_mode="paper",
                action_side="BUY",
                order_type="LMT",
                tif="DAY",
                quantity=Decimal("5"),
                limit_price=Decimal("180.00"),
                estimated_order_value=Decimal("900"),
                estimated_cash_before=Decimal("10000"),
                estimated_cash_after=Decimal("9100"),
                estimated_position_quantity_before=Decimal("0"),
                estimated_position_quantity_after=Decimal("5"),
                estimated_position_value_after=Decimal("900"),
                estimated_portfolio_weight_after_pct=Decimal("9.0"),
                estimated_concentration_impact_pct=Decimal("9.0"),
                orderimpact_base_currency="USD",
                estimated_belgian_tob=Decimal("3.15"),
                belgian_tob_security_class="standard_stock",
                source_action_label="Kopen",
                source_action_label_nl="Kopen",
                status="dry_run_passed",
                dry_run_status="passed",
                dry_run_failures_json=None,
                blocking_reason=None,
                rationale_nl="r",
                explanation_nl="e",
                created_at=datetime(2025, 5, 24, hour, 0, tzinfo=UTC),
                updated_at=datetime(2025, 5, 24, hour, 0, tzinfo=UTC),
            )

        repo.save_asset_action_draft(_draft("d1", "265598", 9))
        repo.save_asset_action_draft(_draft("d2", "265598", 11))  # newer for same conid
        repo.save_asset_action_draft(_draft("d3", "272093", 9))

        latest = repo.list_latest_asset_action_drafts_by_conids(("265598", "272093"))
        assert {r.draft_id for r in latest.records} == {"d2", "d3"}

        loaded = repo.get_asset_action_draft_by_id("d2")
        assert loaded.found is True
        assert loaded.record is not None
        assert loaded.record.quantity == Decimal("5")
        assert loaded.record.action_side == "BUY"
        assert loaded.record.estimated_belgian_tob == Decimal("3.15")
        assert loaded.record.belgian_tob_security_class == "standard_stock"


def test_asset_action_draft_rejects_negative_belgian_tob() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetActionDraftRecord

    now = datetime.now(UTC)
    base = dict(
        draft_id="d",
        decision_package_id="dp",
        decision_package_content_hash="hash",
        ibkr_conid="1",
        symbol="AAPL",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        account_mode="paper",
        expected_account_mode="paper",
        action_side="BUY",
        order_type="LMT",
        tif="DAY",
        quantity=Decimal("5"),
        limit_price=Decimal("180"),
        estimated_order_value=Decimal("900"),
        estimated_cash_before=None,
        estimated_cash_after=None,
        estimated_position_quantity_before=Decimal("0"),
        estimated_position_quantity_after=Decimal("5"),
        estimated_position_value_after=Decimal("900"),
        estimated_portfolio_weight_after_pct=None,
        estimated_concentration_impact_pct=None,
        orderimpact_base_currency="USD",
        source_action_label="Kopen",
        source_action_label_nl="Kopen",
        status="dry_run_passed",
        dry_run_status="passed",
        dry_run_failures_json=None,
        blocking_reason=None,
        rationale_nl="r",
        explanation_nl="e",
        created_at=now,
        updated_at=now,
    )
    with pytest.raises(ValueError, match="estimated_belgian_tob"):
        AssetActionDraftRecord(**{**base, "estimated_belgian_tob": Decimal("-1")})


def test_asset_action_draft_rejects_market_orders_and_unsafe_flags() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetActionDraftRecord

    now = datetime.now(UTC)
    base_kwargs = dict(
        draft_id="d",
        decision_package_id="dp",
        decision_package_content_hash="hash",
        ibkr_conid="1",
        symbol="X",
        currency="USD",
        exchange=None,
        primary_exchange=None,
        account_mode="paper",
        expected_account_mode="paper",
        action_side="BUY",
        order_type="LMT",
        tif="DAY",
        quantity=Decimal("1"),
        limit_price=Decimal("100"),
        estimated_order_value=None,
        estimated_cash_before=None,
        estimated_cash_after=None,
        estimated_position_quantity_before=None,
        estimated_position_quantity_after=None,
        estimated_position_value_after=None,
        estimated_portfolio_weight_after_pct=None,
        estimated_concentration_impact_pct=None,
        orderimpact_base_currency=None,
        source_action_label="Kopen",
        source_action_label_nl="Kopen",
        status="draft",
        dry_run_status="not_attempted",
        dry_run_failures_json=None,
        blocking_reason=None,
        rationale_nl="r",
        explanation_nl="e",
        created_at=now,
        updated_at=now,
    )

    # Slice 20: MKT is now in the locked set; an unknown order_type
    # still raises.
    with pytest.raises(ValueError, match="order_type"):
        AssetActionDraftRecord(**{**base_kwargs, "order_type": "GTD"})
    with pytest.raises(ValueError):
        AssetActionDraftRecord(**{**base_kwargs, "tif": "GTC"})
    with pytest.raises(ValueError):
        AssetActionDraftRecord(**{**base_kwargs, "action_side": "SHORT"})
    with pytest.raises(ValueError):
        AssetActionDraftRecord(**{**base_kwargs, "quantity": Decimal("0")})
    with pytest.raises(ValueError):
        AssetActionDraftRecord(**{**base_kwargs, "safe_for_submission": True})
    with pytest.raises(ValueError):
        AssetActionDraftRecord(**{**base_kwargs, "safe_for_broker_submission": True})


def test_asset_action_draft_submission_repository_upserts_by_draft_id() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        AssetActionDraftSubmissionRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyAssetActionDraftSubmissionRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyAssetActionDraftSubmissionRepository(conn, _report(True))

        def _sub(submission_id: str, state: str) -> AssetActionDraftSubmissionRecord:
            now = datetime(2025, 5, 24, tzinfo=UTC)
            return AssetActionDraftSubmissionRecord(
                submission_id=submission_id,
                draft_id="d1",
                state=state,
                approval_status="approved",
                approved_at=now,
                approved_by="owner",
                approval_dry_run_status="passed",
                approval_dry_run_failures_json=None,
                submitted_at=None,
                ibkr_order_id=None,
                ibkr_perm_id=None,
                ibkr_client_id=None,
                ibkr_status_text=None,
                filled_quantity=None,
                remaining_quantity=None,
                average_fill_price=None,
                cancelled_at=None,
                cancellation_reason=None,
                rejected_reason=None,
                reconciled_at=None,
                account_mode="paper",
                expected_account_mode="paper",
                provider_code="ibkr",
                created_at=now,
                updated_at=now,
                last_state_transition_at=now,
            )

        repo.upsert_asset_action_draft_submission(_sub("s1", "user_approved"))
        repo.upsert_asset_action_draft_submission(_sub("s2", "submitted"))

        latest = repo.get_submission_by_draft_id("d1")
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.submission_id == "s2"
        assert latest.record.state == "submitted"


def test_asset_action_draft_event_repository_lists_events_chronologically() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetActionDraftEventRecord
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyAssetActionDraftEventRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyAssetActionDraftEventRepository(conn, _report(True))

        def _ev(
            event_id: str, when_hour: int, severity: str = "info"
        ) -> AssetActionDraftEventRecord:
            return AssetActionDraftEventRecord(
                event_id=event_id,
                draft_id="d1",
                submission_id=None,
                event_type="state_transition",
                severity=severity,
                from_state="draft",
                to_state="safety_checked",
                occurred_at=datetime(2025, 5, 24, when_hour, 0, tzinfo=UTC),
                acknowledged_at=None,
                rationale_nl="test",
                details_json=None,
            )

        repo.save_asset_action_draft_event(_ev("e1", 11))
        repo.save_asset_action_draft_event(_ev("e2", 9))
        repo.save_asset_action_draft_event(_ev("e3", 10, severity="critical"))

        listed = repo.list_asset_action_draft_events("d1")
        assert [r.event_id for r in listed.records] == ["e2", "e3", "e1"]
        assert listed.records[1].severity == "critical"


def test_submission_record_rejects_safety_booleans_set_true() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        AssetActionDraftSubmissionRecord,
    )

    now = datetime.now(UTC)
    base = dict(
        submission_id="s",
        draft_id="d",
        state="user_approved",
        approval_status="approved",
        approved_at=now,
        approved_by="owner",
        approval_dry_run_status="passed",
        approval_dry_run_failures_json=None,
        submitted_at=None,
        ibkr_order_id=None,
        ibkr_perm_id=None,
        ibkr_client_id=None,
        ibkr_status_text=None,
        filled_quantity=None,
        remaining_quantity=None,
        average_fill_price=None,
        cancelled_at=None,
        cancellation_reason=None,
        rejected_reason=None,
        reconciled_at=None,
        account_mode="paper",
        expected_account_mode="paper",
        provider_code="ibkr",
        created_at=now,
        updated_at=now,
        last_state_transition_at=now,
    )
    with pytest.raises(ValueError):
        AssetActionDraftSubmissionRecord(**{**base, "safe_for_broker_submission": True})
    with pytest.raises(ValueError):
        AssetActionDraftSubmissionRecord(**{**base, "safe_for_orders": True})


def test_prediction_diary_repository_upserts_by_suggestion_id() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        PredictionDiaryEntryRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyPredictionDiaryRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPredictionDiaryRepository(conn, _report(True))

        def _entry(entry_id: str, suggestion_id: str) -> PredictionDiaryEntryRecord:
            now = datetime(2025, 5, 24, tzinfo=UTC)
            return PredictionDiaryEntryRecord(
                entry_id=entry_id,
                suggestion_id=suggestion_id,
                forecast_id="forecast-1",
                ibkr_conid="265598",
                symbol="AAPL",
                currency="USD",
                issued_at=now,
                issued_action_label="Houden",
                issued_action_label_nl="Houden",
                issued_confidence_label="Hoog",
                issued_horizon_days=21,
                issued_price=Decimal("180"),
                issued_p10_price=Decimal("170"),
                issued_p50_price=Decimal("182"),
                issued_p90_price=Decimal("194"),
                issued_prob_gain=Decimal("0.6"),
                issued_prob_loss=Decimal("0.4"),
                user_decision=None,
                realized_price_1d=Decimal("181"),
                realized_price_1w=None,
                realized_price_1m=None,
                realized_return_pct_1d=Decimal("0.55"),
                realized_return_pct_1w=None,
                realized_return_pct_1m=None,
                outcome_label_1d="inconclusive",
                outcome_label_1w=None,
                outcome_label_1m=None,
                outcome_explanation_nl="test",
                last_evaluated_at=now,
                created_at=now,
                updated_at=now,
            )

        repo.upsert_prediction_diary_entry(_entry("e1", "s1"))
        # Updating the same suggestion replaces the row
        repo.upsert_prediction_diary_entry(_entry("e2", "s1"))
        repo.upsert_prediction_diary_entry(_entry("e3", "s2"))

        listed = repo.list_prediction_diary_entries()
        assert {r.entry_id for r in listed.records} == {"e2", "e3"}

        loaded = repo.get_prediction_diary_entry_by_suggestion_id("s1")
        assert loaded.found is True
        assert loaded.record is not None
        assert loaded.record.entry_id == "e2"


def test_prediction_diary_record_rejects_safety_booleans_set_true() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        PredictionDiaryEntryRecord,
    )

    now = datetime(2025, 5, 24, tzinfo=UTC)
    base = dict(
        entry_id="e",
        suggestion_id="s",
        forecast_id=None,
        ibkr_conid="1",
        symbol="X",
        currency="USD",
        issued_at=now,
        issued_action_label="Houden",
        issued_action_label_nl="Houden",
        issued_confidence_label="Middel",
        issued_horizon_days=21,
        issued_price=Decimal("100"),
        issued_p10_price=Decimal("90"),
        issued_p50_price=Decimal("100"),
        issued_p90_price=Decimal("110"),
        issued_prob_gain=Decimal("0.5"),
        issued_prob_loss=Decimal("0.5"),
        user_decision=None,
        realized_price_1d=None,
        realized_price_1w=None,
        realized_price_1m=None,
        realized_return_pct_1d=None,
        realized_return_pct_1w=None,
        realized_return_pct_1m=None,
        outcome_label_1d=None,
        outcome_label_1w=None,
        outcome_label_1m=None,
        outcome_explanation_nl="test",
        last_evaluated_at=now,
        created_at=now,
        updated_at=now,
    )
    with pytest.raises(ValueError):
        PredictionDiaryEntryRecord(**{**base, "safe_for_self_learning": True})
    with pytest.raises(ValueError):
        PredictionDiaryEntryRecord(**{**base, "safe_for_model_retraining": True})


def test_decision_package_explanation_repository_roundtrip() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        DecisionPackageExplanationRecord,
        ExplanationEvidenceLedgerRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyDecisionPackageExplanationRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageExplanationRepository(conn, _report(True))
        now = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)

        explanation = DecisionPackageExplanationRecord(
            explanation_id="exp-1",
            decision_package_id="dp-1",
            decision_package_content_hash="hash-1",
            ibkr_conid="265598",
            symbol="AAPL",
            model_provider_code="stub",
            model_name="deterministic_paraphrase",
            model_version="v1",
            input_evidence_hash="in-hash",
            output_text_hash="out-hash",
            explanation_nl="Test uitleg.",
            risk_disclaimer_nl="Disclaimer.",
            status="generated",
            blocking_reason=None,
            hallucinated_numbers_json=None,
            generated_at=now,
            created_at=now,
        )
        repo.save_decision_package_explanation(explanation)
        repo.save_explanation_evidence_ledger_entry(
            ExplanationEvidenceLedgerRecord(
                ledger_id="led-1",
                explanation_id="exp-1",
                evidence_kind="decision_package",
                evidence_reference_id="dp-1",
                evidence_content_hash="hash-1",
                linked_at=now,
            )
        )

        latest = repo.get_latest_explanation_for_package("dp-1")
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.explanation_id == "exp-1"
        assert latest.record.status == "generated"
        assert latest.record.safe_for_self_learning is False
        assert latest.record.safe_for_action_drafts is False
        assert latest.record.safe_for_orders is False

        ledger = repo.list_evidence_ledger_for_explanation("exp-1")
        assert len(ledger.records) == 1
        assert ledger.records[0].evidence_kind == "decision_package"


def test_decision_package_explanation_rejects_safety_flags_true() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        DecisionPackageExplanationRecord,
    )

    now = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)
    base = dict(
        explanation_id="exp-x",
        decision_package_id="dp-1",
        decision_package_content_hash="hash-1",
        ibkr_conid="265598",
        symbol="AAPL",
        model_provider_code="stub",
        model_name="x",
        model_version="v1",
        input_evidence_hash="in",
        output_text_hash="out",
        explanation_nl="t",
        risk_disclaimer_nl="d",
        status="generated",
        blocking_reason=None,
        hallucinated_numbers_json=None,
        generated_at=now,
        created_at=now,
    )
    with pytest.raises(ValueError):
        DecisionPackageExplanationRecord(**{**base, "safe_for_self_learning": True})
    with pytest.raises(ValueError):
        DecisionPackageExplanationRecord(**{**base, "safe_for_action_drafts": True})
    with pytest.raises(ValueError):
        DecisionPackageExplanationRecord(**{**base, "safe_for_orders": True})


def test_explanation_evidence_ledger_rejects_safety_flags_true() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        ExplanationEvidenceLedgerRecord,
    )

    now = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)
    base = dict(
        ledger_id="led-x",
        explanation_id="exp-1",
        evidence_kind="decision_package",
        evidence_reference_id="dp-1",
        evidence_content_hash="hash-1",
        linked_at=now,
    )
    with pytest.raises(ValueError):
        ExplanationEvidenceLedgerRecord(**{**base, "safe_for_self_learning": True})
    with pytest.raises(ValueError):
        ExplanationEvidenceLedgerRecord(**{**base, "safe_for_model_retraining": True})


def test_explanation_can_persist_blocked_with_hallucinated_numbers() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        DecisionPackageExplanationRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyDecisionPackageExplanationRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageExplanationRepository(conn, _report(True))
        now = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)
        record = DecisionPackageExplanationRecord(
            explanation_id="exp-blocked",
            decision_package_id="dp-1",
            decision_package_content_hash="hash-1",
            ibkr_conid="265598",
            symbol="AAPL",
            model_provider_code="stub",
            model_name="x",
            model_version="v1",
            input_evidence_hash="in",
            output_text_hash="out",
            explanation_nl="Doelprijs 999.",
            risk_disclaimer_nl="d",
            status="blocked",
            blocking_reason="hallucinated_numbers",
            hallucinated_numbers_json=("999", "1000"),
            generated_at=now,
            created_at=now,
        )
        repo.save_decision_package_explanation(record)
        latest = repo.get_latest_explanation_for_package("dp-1")
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.status == "blocked"
        assert latest.record.hallucinated_numbers_json == ("999", "1000")


def test_daily_briefing_repository_upserts_by_date_and_lists_alerts() -> None:
    from datetime import date as _date

    from ai_trading_agent_storage.repository_contracts import (
        BriefingAlertRecord,
        DailyBriefingRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyDailyBriefingRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDailyBriefingRepository(conn, _report(True))
        now = datetime(2025, 5, 24, 9, 0, tzinfo=UTC)

        def _briefing(briefing_id: str, summary: str) -> DailyBriefingRecord:
            return DailyBriefingRecord(
                briefing_id=briefing_id,
                briefing_date=_date(2025, 5, 24),
                generated_at=now,
                lookback_started_at=now,
                position_count=0,
                base_currency=None,
                total_position_value=None,
                cash_total=None,
                fx_freshness_status=None,
                new_suggestion_count=0,
                new_decision_package_count=0,
                new_action_draft_count=0,
                diary_outcomes_closed_count=0,
                critical_event_count=0,
                alert_count=0,
                summary_nl=summary,
                help_nl="ok",
                status="ready",
                blocking_reason=None,
            )

        repo.upsert_daily_briefing(_briefing("brief-1", "eerste"))
        # Re-running for the same date replaces the row.
        repo.upsert_daily_briefing(_briefing("brief-2", "tweede"))
        latest = repo.get_latest_daily_briefing()
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.briefing_id == "brief-2"
        assert latest.record.summary_nl == "tweede"

        repo.save_briefing_alert(
            BriefingAlertRecord(
                alert_id="alrt-1",
                briefing_id="brief-2",
                alert_kind="new_suggestion",
                severity="info",
                reference_kind="suggestion",
                reference_id="sug-1",
                title_nl="t",
                body_nl="b",
                acknowledged_at=None,
                linked_at=now,
            )
        )
        alerts = repo.list_alerts_for_briefing("brief-2")
        assert len(alerts.records) == 1
        assert alerts.records[0].severity == "info"

        repo.delete_alerts_for_briefing("brief-2")
        alerts = repo.list_alerts_for_briefing("brief-2")
        assert len(alerts.records) == 0


def test_daily_briefing_rejects_safety_booleans_set_true() -> None:
    from datetime import date as _date

    from ai_trading_agent_storage.repository_contracts import (
        BriefingAlertRecord,
        DailyBriefingRecord,
    )

    now = datetime(2025, 5, 24, 9, 0, tzinfo=UTC)
    briefing_base = dict(
        briefing_id="b",
        briefing_date=_date(2025, 5, 24),
        generated_at=now,
        lookback_started_at=now,
        position_count=0,
        base_currency=None,
        total_position_value=None,
        cash_total=None,
        fx_freshness_status=None,
        new_suggestion_count=0,
        new_decision_package_count=0,
        new_action_draft_count=0,
        diary_outcomes_closed_count=0,
        critical_event_count=0,
        alert_count=0,
        summary_nl="t",
        help_nl="t",
        status="ready",
        blocking_reason=None,
    )
    with pytest.raises(ValueError):
        DailyBriefingRecord(**{**briefing_base, "safe_for_action_drafts": True})
    with pytest.raises(ValueError):
        DailyBriefingRecord(**{**briefing_base, "safe_for_orders": True})

    alert_base = dict(
        alert_id="a",
        briefing_id="b",
        alert_kind="new_suggestion",
        severity="info",
        reference_kind=None,
        reference_id=None,
        title_nl="t",
        body_nl="b",
        acknowledged_at=None,
        linked_at=now,
    )
    with pytest.raises(ValueError):
        BriefingAlertRecord(**{**alert_base, "safe_for_action_drafts": True})
    with pytest.raises(ValueError, match="severity"):
        BriefingAlertRecord(**{**alert_base, "severity": "unknown"})


def test_daily_briefing_rejects_negative_counts() -> None:
    from datetime import date as _date

    from ai_trading_agent_storage.repository_contracts import DailyBriefingRecord

    now = datetime(2025, 5, 24, 9, 0, tzinfo=UTC)
    base = dict(
        briefing_id="b",
        briefing_date=_date(2025, 5, 24),
        generated_at=now,
        lookback_started_at=now,
        position_count=0,
        base_currency=None,
        total_position_value=None,
        cash_total=None,
        fx_freshness_status=None,
        new_suggestion_count=0,
        new_decision_package_count=0,
        new_action_draft_count=0,
        diary_outcomes_closed_count=0,
        critical_event_count=0,
        alert_count=0,
        summary_nl="t",
        help_nl="t",
        status="ready",
        blocking_reason=None,
    )
    with pytest.raises(ValueError, match="non-negative"):
        DailyBriefingRecord(**{**base, "position_count": -1})


def test_scheduler_run_repository_save_update_and_latest() -> None:
    from ai_trading_agent_storage.repository_contracts import SchedulerRunRecord
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemySchedulerRunRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemySchedulerRunRepository(conn, _report(True))
        scheduled = datetime(2026, 6, 1, 6, 30, tzinfo=UTC)
        started = datetime(2026, 6, 1, 6, 30, 5, tzinfo=UTC)
        finished = datetime(2026, 6, 1, 6, 30, 12, tzinfo=UTC)

        running = SchedulerRunRecord(
            run_id="run-1",
            job_name="daily_briefing",
            scheduled_at=scheduled,
            started_at=started,
            finished_at=None,
            status="running",
            error_text=None,
            triggered_by="scheduler",
        )
        repo.save_scheduler_run(running)
        latest = repo.get_latest_scheduler_run()
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.status == "running"

        succeeded = SchedulerRunRecord(
            run_id="run-1",
            job_name="daily_briefing",
            scheduled_at=scheduled,
            started_at=started,
            finished_at=finished,
            status="succeeded",
            error_text=None,
            triggered_by="scheduler",
        )
        repo.update_scheduler_run(succeeded)
        latest = repo.get_latest_scheduler_run(job_name="daily_briefing")
        assert latest.record is not None
        assert latest.record.status == "succeeded"
        # SQLite strips tzinfo on read; compare naive components only.
        assert latest.record.finished_at is not None
        assert latest.record.finished_at.replace(tzinfo=None) == finished.replace(
            tzinfo=None
        )

        runs = repo.list_scheduler_runs()
        assert len(runs.records) == 1


def test_scheduler_run_record_invariants() -> None:
    from ai_trading_agent_storage.repository_contracts import SchedulerRunRecord

    now = datetime(2026, 6, 1, tzinfo=UTC)
    base = dict(
        run_id="r",
        job_name="daily_briefing",
        scheduled_at=now,
        started_at=now,
        finished_at=None,
        status="running",
        error_text=None,
        triggered_by="scheduler",
    )
    with pytest.raises(ValueError, match="status must"):
        SchedulerRunRecord(**{**base, "status": "bogus"})
    with pytest.raises(ValueError, match="triggered_by"):
        SchedulerRunRecord(**{**base, "triggered_by": "cron"})
    with pytest.raises(ValueError):
        SchedulerRunRecord(**{**base, "safe_for_action_drafts": True})
    with pytest.raises(ValueError):
        SchedulerRunRecord(**{**base, "safe_for_orders": True})


def test_predictor_backtest_run_repository_roundtrip() -> None:
    """V1.1 Slice 24: persist + read-back the predictor backtest audit row."""

    from ai_trading_agent_storage.repository_contracts import (
        PredictorBacktestRunRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyPredictorBacktestRunRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPredictorBacktestRunRepository(conn, _report(True))
        started = datetime(2026, 6, 1, 6, 30, tzinfo=UTC)
        finished = datetime(2026, 6, 1, 6, 31, tzinfo=UTC)

        running = PredictorBacktestRunRecord(
            run_id="bt-1",
            model_code="momentum_v1",
            model_version="v1.0.0",
            asset_symbol="AAPL",
            started_at=started,
            finished_at=None,
            status="running",
            window_days=90,
            bars_used=0,
            brier_score=None,
            hit_rate=None,
            sharpe_ratio=None,
            blocking_reason=None,
            explanation_nl=None,
        )
        repo.save_backtest_run(running)

        succeeded = PredictorBacktestRunRecord(
            run_id="bt-1",
            model_code="momentum_v1",
            model_version="v1.0.0",
            asset_symbol="AAPL",
            started_at=started,
            finished_at=finished,
            status="succeeded",
            window_days=90,
            bars_used=120,
            brier_score=Decimal("0.187200"),
            hit_rate=Decimal("0.563000"),
            sharpe_ratio=Decimal("1.230000"),
            blocking_reason=None,
            explanation_nl="Walk-forward 90d/Momentum v1 → Brier 0.19.",
        )
        repo.update_backtest_run(succeeded)

        rows = repo.list_recent_backtest_runs()
        assert len(rows.records) == 1
        row = rows.records[0]
        assert row.run_id == "bt-1"
        assert row.status == "succeeded"
        assert row.brier_score == Decimal("0.187200")
        assert row.hit_rate == Decimal("0.563000")

        # Filter by model_code + asset_symbol.
        filtered = repo.list_recent_backtest_runs(
            model_code="momentum_v1", asset_symbol="AAPL"
        )
        assert len(filtered.records) == 1
        empty = repo.list_recent_backtest_runs(model_code="missing_v1")
        assert empty.records == ()


def test_claude_ai_budget_usage_repository_roundtrip() -> None:
    """V1.1 Slice 29: Claude AI budget-usage audit roundtrip + total."""

    from ai_trading_agent_storage.repository_contracts import (
        ClaudeAiBudgetUsageRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyClaudeAiBudgetUsageRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyClaudeAiBudgetUsageRepository(conn, _report(True))
        now = datetime(2026, 6, 1, 7, 0, tzinfo=UTC)

        repo.save_usage(
            ClaudeAiBudgetUsageRecord(
                usage_id="clbu-1",
                budget_month="2026-06",
                provider_code="anthropic_claude",
                model_name="claude-haiku-4-5-20251001",
                called_at=now,
                input_units=1000,
                cached_input_units=500,
                output_units=200,
                cost_eur=Decimal("0.001640"),
                call_kind="explanation",
                explanation_nl="test call 1",
            )
        )
        repo.save_usage(
            ClaudeAiBudgetUsageRecord(
                usage_id="clbu-2",
                budget_month="2026-06",
                provider_code="anthropic_claude",
                model_name="claude-haiku-4-5-20251001",
                called_at=now,
                input_units=2000,
                cached_input_units=0,
                output_units=400,
                cost_eur=Decimal("0.003200"),
                call_kind="explanation",
                explanation_nl="test call 2",
            )
        )
        # Another month — should not be summed in.
        repo.save_usage(
            ClaudeAiBudgetUsageRecord(
                usage_id="clbu-3",
                budget_month="2026-05",
                provider_code="anthropic_claude",
                model_name="claude-haiku-4-5-20251001",
                called_at=now,
                input_units=1000,
                cached_input_units=0,
                output_units=200,
                cost_eur=Decimal("99.000000"),
                call_kind="explanation",
            )
        )

        june_total = repo.monthly_total_eur("2026-06")
        assert june_total == Decimal("0.004840")

        rows = repo.list_recent_usage(budget_month="2026-06")
        assert len(rows.records) == 2
        assert all(r.budget_month == "2026-06" for r in rows.records)


def test_claude_ai_budget_usage_record_invariants() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        ClaudeAiBudgetUsageRecord,
    )

    now = datetime(2026, 6, 1, tzinfo=UTC)
    base = dict(
        usage_id="clbu-1",
        budget_month="2026-06",
        provider_code="anthropic_claude",
        model_name="claude-haiku-4-5-20251001",
        called_at=now,
        input_units=100,
        cached_input_units=50,
        output_units=20,
        cost_eur=Decimal("0.001"),
        call_kind="explanation",
        explanation_nl=None,
    )
    # call_kind enforced.
    with pytest.raises(ValueError, match="call_kind"):
        ClaudeAiBudgetUsageRecord(**{**base, "call_kind": "bogus"})
    # budget_month must be YYYY-MM.
    with pytest.raises(ValueError, match="budget_month"):
        ClaudeAiBudgetUsageRecord(**{**base, "budget_month": "2026-6"})
    # Non-negative unit counts.
    with pytest.raises(ValueError, match="input_units"):
        ClaudeAiBudgetUsageRecord(**{**base, "input_units": -1})
    # Non-negative cost.
    with pytest.raises(ValueError, match="cost_eur"):
        ClaudeAiBudgetUsageRecord(**{**base, "cost_eur": Decimal("-0.01")})
    # Safety booleans hard-False.
    with pytest.raises(ValueError, match="safety booleans"):
        ClaudeAiBudgetUsageRecord(**{**base, "safe_for_action_drafts": True})


def test_prediction_diary_predictor_contribution_repository_roundtrip() -> None:
    """V1.1 Slice 26: per-(diary_entry, predictor) outcome row."""

    from ai_trading_agent_storage.repository_contracts import (
        PredictionDiaryPredictorContributionRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyPredictionDiaryPredictorContributionRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPredictionDiaryPredictorContributionRepository(
            conn, _report(True)
        )
        created = datetime(2026, 6, 1, 7, 0, tzinfo=UTC)

        rec_a = PredictionDiaryPredictorContributionRecord(
            contribution_id="c-1",
            diary_entry_id="entry-1",
            model_code="momentum_v1",
            model_version="v1.0.0",
            predicted_return_pct=Decimal("3.0"),
            predicted_prob_gain=Decimal("0.62"),
            predicted_direction="slight_up",
            realised_return_pct=Decimal("4.5"),
            realised_direction="slight_up",
            outcome_label="correct",
            brier_score=Decimal("0.144400"),
            return_spread_pct=Decimal("-1.5"),
            explanation_nl="momentum_v1 correct.",
            created_at=created,
        )
        rec_b = PredictionDiaryPredictorContributionRecord(
            contribution_id="c-2",
            diary_entry_id="entry-1",
            model_code="baseline_gbm",
            model_version="v1.0.0",
            predicted_return_pct=Decimal("1.0"),
            predicted_prob_gain=Decimal("0.55"),
            predicted_direction="flat",
            realised_return_pct=Decimal("4.5"),
            realised_direction="slight_up",
            outcome_label="wrong",
            brier_score=Decimal("0.202500"),
            return_spread_pct=Decimal("-3.5"),
            explanation_nl="baseline_gbm flat-bucket gemist.",
            created_at=created,
        )
        repo.save_contribution(rec_a)
        repo.save_contribution(rec_b)

        all_rows = repo.list_recent_contributions()
        assert len(all_rows.records) == 2

        by_entry = repo.list_recent_contributions(diary_entry_id="entry-1")
        assert len(by_entry.records) == 2

        by_model = repo.list_recent_contributions(model_code="momentum_v1")
        assert len(by_model.records) == 1
        assert by_model.records[0].outcome_label == "correct"


def test_prediction_diary_predictor_contribution_record_invariants() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        PredictionDiaryPredictorContributionRecord,
    )

    now = datetime(2026, 6, 1, tzinfo=UTC)
    base = dict(
        contribution_id="c-1",
        diary_entry_id="entry-1",
        model_code="momentum_v1",
        model_version="v1.0.0",
        predicted_return_pct=Decimal("3.0"),
        predicted_prob_gain=Decimal("0.62"),
        predicted_direction="slight_up",
        realised_return_pct=None,
        realised_direction=None,
        outcome_label=None,
        brier_score=None,
        return_spread_pct=None,
        explanation_nl=None,
        created_at=now,
    )
    # predicted_prob_gain bounded.
    with pytest.raises(ValueError, match="predicted_prob_gain"):
        PredictionDiaryPredictorContributionRecord(
            **{**base, "predicted_prob_gain": Decimal("1.2")}
        )
    # brier non-negative.
    with pytest.raises(ValueError, match="brier_score"):
        PredictionDiaryPredictorContributionRecord(
            **{**base, "brier_score": Decimal("-0.1")}
        )
    # Safety booleans hard-False.
    with pytest.raises(ValueError, match="safety booleans"):
        PredictionDiaryPredictorContributionRecord(
            **{**base, "safe_for_action_drafts": True}
        )
    with pytest.raises(ValueError, match="safety booleans"):
        PredictionDiaryPredictorContributionRecord(
            **{**base, "safe_for_orders": True}
        )


def test_predictor_backtest_run_record_invariants() -> None:
    """Per-field invariants on PredictorBacktestRunRecord."""

    from ai_trading_agent_storage.repository_contracts import (
        PredictorBacktestRunRecord,
    )

    now = datetime(2026, 6, 1, tzinfo=UTC)
    base = dict(
        run_id="bt-1",
        model_code="m",
        model_version="v",
        asset_symbol="AAPL",
        started_at=now,
        finished_at=None,
        status="running",
        window_days=90,
        bars_used=0,
        brier_score=None,
        hit_rate=None,
        sharpe_ratio=None,
        blocking_reason=None,
        explanation_nl=None,
    )
    # Status enforced.
    with pytest.raises(ValueError, match="status must"):
        PredictorBacktestRunRecord(**{**base, "status": "bogus"})
    # Positive window_days enforced.
    with pytest.raises(ValueError, match="window_days"):
        PredictorBacktestRunRecord(**{**base, "window_days": 0})
    # Non-negative bars_used.
    with pytest.raises(ValueError, match="bars_used"):
        PredictorBacktestRunRecord(**{**base, "bars_used": -1})
    # Hit rate bounded.
    with pytest.raises(ValueError, match="hit_rate"):
        PredictorBacktestRunRecord(**{**base, "hit_rate": Decimal("1.5")})
    # Brier non-negative.
    with pytest.raises(ValueError, match="brier_score"):
        PredictorBacktestRunRecord(**{**base, "brier_score": Decimal("-0.1")})
    # Safety booleans hard-False enforced.
    with pytest.raises(ValueError, match="safety booleans"):
        PredictorBacktestRunRecord(**{**base, "safe_for_action_drafts": True})
    with pytest.raises(ValueError, match="safety booleans"):
        PredictorBacktestRunRecord(**{**base, "safe_for_orders": True})


def test_asset_fundamentals_snapshot_repository_roundtrip() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        AssetFundamentalsSnapshotRecord,
    )
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyAssetFundamentalsSnapshotRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyAssetFundamentalsSnapshotRepository(conn, _report(True))
        now = datetime(2026, 6, 2, 8, 0, tzinfo=UTC)

        def _record(symbol: str, fetched_at: datetime) -> AssetFundamentalsSnapshotRecord:
            return AssetFundamentalsSnapshotRecord(
                snapshot_id=f"snap-{symbol}-{fetched_at.isoformat()}",
                ibkr_conid=None,
                eodhd_symbol=f"{symbol}.US",
                symbol=symbol,
                sector="Technology",
                currency="USD",
                market_cap=Decimal("1000000000"),
                pe_ratio=Decimal("20"),
                pb_ratio=Decimal("3"),
                ev_ebitda=Decimal("15"),
                roic_pct=Decimal("12"),
                gross_margin_pct=Decimal("45"),
                dividend_yield_pct=Decimal("1.5"),
                return_6m_pct=Decimal("8"),
                return_12m_pct=Decimal("20"),
                raw_payload_hash="hash",
                provider_code="eodhd",
                fetched_at=fetched_at,
                stored_at=now,
            )

        repo.save_snapshot(_record("AAPL", now - timedelta(days=2)))
        repo.save_snapshot(_record("AAPL", now))
        repo.save_snapshot(_record("MSFT", now))

        latest_aapl = repo.get_latest_snapshot_for_symbol("AAPL.US")
        assert latest_aapl.found is True
        assert latest_aapl.record is not None
        assert latest_aapl.record.symbol == "AAPL"

        universe = repo.list_latest_universe_snapshots()
        assert {r.symbol for r in universe.records} == {"AAPL", "MSFT"}

        # V1.1 Slice 31: ``min_factor_count`` filter. Each test row
        # has all 6 scored columns populated, so a filter of 6 keeps
        # them; a filter of 7 (impossible) keeps none.
        all_factors = repo.list_latest_universe_snapshots(min_factor_count=6)
        assert len(all_factors.records) == 2
        none_pass = repo.list_latest_universe_snapshots(min_factor_count=7)
        assert len(none_pass.records) == 0
        # ``limit`` paging surface — capping to 1 returns only one row.
        single = repo.list_latest_universe_snapshots(limit=1)
        assert len(single.records) == 1


def test_asset_fundamentals_snapshot_rejects_safety_flags_true() -> None:
    from ai_trading_agent_storage.repository_contracts import (
        AssetFundamentalsSnapshotRecord,
    )

    now = datetime(2026, 6, 2, tzinfo=UTC)
    base = dict(
        snapshot_id="s",
        ibkr_conid=None,
        eodhd_symbol="AAPL.US",
        symbol="AAPL",
        sector=None,
        currency=None,
        market_cap=None,
        pe_ratio=None,
        pb_ratio=None,
        ev_ebitda=None,
        roic_pct=None,
        gross_margin_pct=None,
        dividend_yield_pct=None,
        return_6m_pct=None,
        return_12m_pct=None,
        raw_payload_hash="hash",
        provider_code="eodhd",
        fetched_at=now,
        stored_at=now,
    )
    with pytest.raises(ValueError):
        AssetFundamentalsSnapshotRecord(**{**base, "safe_for_orders": True})
    with pytest.raises(ValueError):
        AssetFundamentalsSnapshotRecord(**{**base, "safe_for_action_drafts": True})


def test_universe_scan_run_repository_save_update_and_list() -> None:
    from ai_trading_agent_storage.repository_contracts import UniverseScanRunRecord
    from ai_trading_agent_storage.sql_repositories import (
        SqlAlchemyUniverseScanRunRepository,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyUniverseScanRunRepository(conn, _report(True))
        now = datetime(2026, 6, 3, 6, 30, tzinfo=UTC)

        running = UniverseScanRunRecord(
            run_id="usr-1",
            started_at=now,
            finished_at=None,
            status="running",
            triggered_by="manual",
            scanned_count=0,
            persisted_count=0,
            failed_count=0,
            ranked_count=0,
            universe_size=325,
            error_text=None,
        )
        repo.save_run(running)

        succeeded = UniverseScanRunRecord(
            run_id="usr-1",
            started_at=now,
            finished_at=now + timedelta(seconds=42),
            status="succeeded",
            triggered_by="manual",
            scanned_count=325,
            persisted_count=320,
            failed_count=5,
            ranked_count=200,
            universe_size=325,
            error_text=None,
        )
        repo.update_run(succeeded)

        latest = repo.get_latest_run()
        assert latest.found is True
        assert latest.record is not None
        assert latest.record.status == "succeeded"
        assert latest.record.scanned_count == 325
        assert latest.record.persisted_count == 320

        listed = repo.list_runs()
        assert len(listed.records) == 1


def test_universe_scan_run_record_invariants() -> None:
    from ai_trading_agent_storage.repository_contracts import UniverseScanRunRecord

    now = datetime(2026, 6, 3, tzinfo=UTC)
    base = dict(
        run_id="r",
        started_at=now,
        finished_at=None,
        status="running",
        triggered_by="manual",
        scanned_count=0,
        persisted_count=0,
        failed_count=0,
        ranked_count=0,
        universe_size=10,
        error_text=None,
    )
    with pytest.raises(ValueError, match="status must"):
        UniverseScanRunRecord(**{**base, "status": "bogus"})
    with pytest.raises(ValueError, match="triggered_by"):
        UniverseScanRunRecord(**{**base, "triggered_by": "cron"})
    with pytest.raises(ValueError, match="non-negative"):
        UniverseScanRunRecord(**{**base, "scanned_count": -1})
    with pytest.raises(ValueError):
        UniverseScanRunRecord(**{**base, "safe_for_action_drafts": True})
    with pytest.raises(ValueError):
        UniverseScanRunRecord(**{**base, "safe_for_orders": True})


def test_asset_action_draft_supports_full_order_vocabulary_per_type() -> None:
    """Per-type invariants for the §21.3 order-vocabulary expansion."""

    from ai_trading_agent_storage.repository_contracts import AssetActionDraftRecord

    now = datetime.now(UTC)
    base = dict(
        draft_id="d",
        decision_package_id="dp",
        decision_package_content_hash="hash",
        ibkr_conid="1",
        symbol="X",
        currency="USD",
        exchange=None,
        primary_exchange=None,
        account_mode="paper",
        expected_account_mode="paper",
        action_side="BUY",
        tif="DAY",
        quantity=Decimal("10"),
        estimated_order_value=None,
        estimated_cash_before=None,
        estimated_cash_after=None,
        estimated_position_quantity_before=None,
        estimated_position_quantity_after=None,
        estimated_position_value_after=None,
        estimated_portfolio_weight_after_pct=None,
        estimated_concentration_impact_pct=None,
        orderimpact_base_currency=None,
        source_action_label="Kopen",
        source_action_label_nl="Kopen",
        status="draft",
        dry_run_status="not_attempted",
        dry_run_failures_json=None,
        blocking_reason=None,
        rationale_nl="r",
        explanation_nl="e",
        created_at=now,
        updated_at=now,
    )

    # LMT — happy
    AssetActionDraftRecord(**{**base, "order_type": "LMT", "limit_price": Decimal("100")})

    # MKT — happy (limit_price allowed as 0 for MKT)
    AssetActionDraftRecord(**{**base, "order_type": "MKT", "limit_price": Decimal("0")})

    # STP — happy
    AssetActionDraftRecord(
        **{
            **base,
            "order_type": "STP",
            "limit_price": Decimal("0"),
            "stop_price": Decimal("95"),
        }
    )
    # STP — missing stop_price
    with pytest.raises(ValueError, match="stop_price"):
        AssetActionDraftRecord(
            **{**base, "order_type": "STP", "limit_price": Decimal("0")}
        )

    # STP_LMT — happy
    AssetActionDraftRecord(
        **{
            **base,
            "order_type": "STP_LMT",
            "limit_price": Decimal("96"),
            "stop_price": Decimal("95"),
        }
    )
    # STP_LMT — missing stop
    with pytest.raises(ValueError, match="stop_price"):
        AssetActionDraftRecord(
            **{**base, "order_type": "STP_LMT", "limit_price": Decimal("96")}
        )

    # TRAIL with amount — happy
    AssetActionDraftRecord(
        **{
            **base,
            "order_type": "TRAIL",
            "limit_price": Decimal("0"),
            "trail_amount": Decimal("2"),
        }
    )
    # TRAIL with percent — happy
    AssetActionDraftRecord(
        **{
            **base,
            "order_type": "TRAIL",
            "limit_price": Decimal("0"),
            "trail_percent": Decimal("3"),
        }
    )
    # TRAIL with both — rejected
    with pytest.raises(ValueError, match="exactly one"):
        AssetActionDraftRecord(
            **{
                **base,
                "order_type": "TRAIL",
                "limit_price": Decimal("0"),
                "trail_amount": Decimal("2"),
                "trail_percent": Decimal("3"),
            }
        )
    # TRAIL with neither — rejected
    with pytest.raises(ValueError, match="exactly one"):
        AssetActionDraftRecord(
            **{**base, "order_type": "TRAIL", "limit_price": Decimal("0")}
        )

    # TRAIL_LMT — needs limit_price too
    AssetActionDraftRecord(
        **{
            **base,
            "order_type": "TRAIL_LMT",
            "limit_price": Decimal("95"),
            "trail_percent": Decimal("3"),
        }
    )
    with pytest.raises(ValueError, match="limit_price"):
        AssetActionDraftRecord(
            **{
                **base,
                "order_type": "TRAIL_LMT",
                "limit_price": Decimal("0"),
                "trail_percent": Decimal("3"),
            }
        )

    # BRACKET BUY — tp > limit > sl
    AssetActionDraftRecord(
        **{
            **base,
            "order_type": "BRACKET",
            "limit_price": Decimal("100"),
            "bracket_take_profit_limit_price": Decimal("110"),
            "bracket_stop_loss_price": Decimal("95"),
        }
    )
    # BRACKET BUY — tp <= limit rejected
    with pytest.raises(ValueError, match="take-profit"):
        AssetActionDraftRecord(
            **{
                **base,
                "order_type": "BRACKET",
                "limit_price": Decimal("100"),
                "bracket_take_profit_limit_price": Decimal("100"),
                "bracket_stop_loss_price": Decimal("95"),
            }
        )
    # BRACKET BUY — sl >= limit rejected
    with pytest.raises(ValueError, match="stop-loss"):
        AssetActionDraftRecord(
            **{
                **base,
                "order_type": "BRACKET",
                "limit_price": Decimal("100"),
                "bracket_take_profit_limit_price": Decimal("110"),
                "bracket_stop_loss_price": Decimal("100"),
            }
        )

    # BRACKET SELL — tp < limit < sl
    AssetActionDraftRecord(
        **{
            **base,
            "action_side": "SELL",
            "order_type": "BRACKET",
            "limit_price": Decimal("100"),
            "bracket_take_profit_limit_price": Decimal("90"),
            "bracket_stop_loss_price": Decimal("105"),
        }
    )
    # BRACKET SELL — wrong ordering
    with pytest.raises(ValueError, match="take-profit"):
        AssetActionDraftRecord(
            **{
                **base,
                "action_side": "SELL",
                "order_type": "BRACKET",
                "limit_price": Decimal("100"),
                "bracket_take_profit_limit_price": Decimal("110"),
                "bracket_stop_loss_price": Decimal("105"),
            }
        )


def test_asset_action_draft_rejects_negative_extra_price_fields() -> None:
    from ai_trading_agent_storage.repository_contracts import AssetActionDraftRecord

    now = datetime.now(UTC)
    base = dict(
        draft_id="d",
        decision_package_id="dp",
        decision_package_content_hash="hash",
        ibkr_conid="1",
        symbol="X",
        currency="USD",
        exchange=None,
        primary_exchange=None,
        account_mode="paper",
        expected_account_mode="paper",
        action_side="BUY",
        order_type="LMT",
        tif="DAY",
        quantity=Decimal("1"),
        limit_price=Decimal("100"),
        estimated_order_value=None,
        estimated_cash_before=None,
        estimated_cash_after=None,
        estimated_position_quantity_before=None,
        estimated_position_quantity_after=None,
        estimated_position_value_after=None,
        estimated_portfolio_weight_after_pct=None,
        estimated_concentration_impact_pct=None,
        orderimpact_base_currency=None,
        source_action_label="Kopen",
        source_action_label_nl="Kopen",
        status="draft",
        dry_run_status="not_attempted",
        dry_run_failures_json=None,
        blocking_reason=None,
        rationale_nl="r",
        explanation_nl="e",
        created_at=now,
        updated_at=now,
    )
    for field in (
        "stop_price",
        "trail_amount",
        "trail_percent",
        "bracket_take_profit_limit_price",
        "bracket_stop_loss_price",
    ):
        with pytest.raises(ValueError, match="must be positive"):
            AssetActionDraftRecord(**{**base, field: Decimal("-1")})
