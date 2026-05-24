from datetime import UTC, datetime
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

        listed = repo.list_latest_asset_decision_packages_by_conids(("265598", "272093"))
        assert {r.decision_package_id for r in listed.records} == {"dp-2", "dp-3"}


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
