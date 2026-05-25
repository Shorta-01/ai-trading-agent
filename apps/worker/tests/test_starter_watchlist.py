"""Task 128 — starter-watchlist seed function tests.

Covers the locked starter-set length, the partial-failure path, the
idempotency guarantee, and the state-machine transitions the seed
writes alongside the watchlist rows.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyColdStartSeedAuditRepository,
    SqlAlchemyWatchlistConfirmationAuditRepository,
    SqlAlchemyWatchlistConfirmationStateRepository,
    SqlAlchemyWatchlistItemSeedRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.starter_watchlist import (
    SEED_VERSION,
    STARTER_WATCHLIST_V1,
    seed_starter_watchlist,
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
        latest_expected_revision_id="0047_cold_start_and_watchlist_confirmation",
        database_revision_id=(
            "0047_cold_start_and_watchlist_confirmation"
            if allowed
            else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


class _AlwaysResolveListing:
    """Returns a fake AssetListing for every starter symbol."""

    def find_listing(
        self,
        *,
        symbol: str,
        exchange: str,  # noqa: ARG002
        currency: str,  # noqa: ARG002
    ) -> Any:
        return type("_FakeListing", (), {"asset_id": f"asset-{symbol}"})()


class _AlwaysMissingListing:
    """Returns ``None`` so every starter symbol is logged as failed."""

    def find_listing(
        self,
        *,
        symbol: str,  # noqa: ARG002
        exchange: str,  # noqa: ARG002
        currency: str,  # noqa: ARG002
    ) -> Any:
        return None


class _PartialResolver:
    """Resolves all but the locked-set ``missing_symbols``."""

    def __init__(self, missing_symbols: set[str]) -> None:
        self._missing = missing_symbols

    def find_listing(
        self,
        *,
        symbol: str,
        exchange: str,  # noqa: ARG002
        currency: str,  # noqa: ARG002
    ) -> Any:
        if symbol in self._missing:
            return None
        return type("_FakeListing", (), {"asset_id": f"asset-{symbol}"})()


def _build_repos(conn: Any) -> tuple[
    SqlAlchemyColdStartSeedAuditRepository,
    SqlAlchemyWatchlistItemSeedRepository,
    SqlAlchemyWatchlistConfirmationStateRepository,
    SqlAlchemyWatchlistConfirmationAuditRepository,
]:
    report = _report(True)
    return (
        SqlAlchemyColdStartSeedAuditRepository(conn, report),
        SqlAlchemyWatchlistItemSeedRepository(conn, report),
        SqlAlchemyWatchlistConfirmationStateRepository(conn, report),
        SqlAlchemyWatchlistConfirmationAuditRepository(conn, report),
    )


# ---- locked-set length -------------------------------------------


def test_starter_watchlist_v1_has_locked_count_of_12() -> None:
    assert len(STARTER_WATCHLIST_V1) == 12


def test_starter_watchlist_v1_contains_expected_symbols() -> None:
    symbols = {asset.symbol for asset in STARTER_WATCHLIST_V1}
    expected = {
        "SXR8", "VWCE", "EQQQ", "EXSA", "AGGH",
        "ASML", "MC", "NOVO-B", "SAP", "SHEL",
        "WTEC", "IS3N",
    }
    assert symbols == expected


# ---- happy path --------------------------------------------------


def test_seed_writes_12_rows_with_resolver_returning_listings() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        seed_audit, wl_seed, state_repo, audit_repo = _build_repos(conn)

        result = seed_starter_watchlist(
            ibkr_account_id="DU1234567",
            seed_audit_repo=seed_audit,
            watchlist_seed_repo=wl_seed,
            confirmation_state_repo=state_repo,
            confirmation_audit_repo=audit_repo,
            listing_resolver=_AlwaysResolveListing(),
            now_provider=lambda: _BASE,
        )

        assert result.already_seeded is False
        assert result.seeded_count == 12
        assert result.failed_symbols == ()

        # 12 rows in watchlist_items.
        assert wl_seed.count_active_for_account("DU1234567") == 12

        # Seed audit row recorded.
        audit = seed_audit.find_by_account_id("DU1234567")
        assert audit is not None
        assert audit.seeded_count == 12
        assert audit.seed_version == SEED_VERSION
        assert json.loads(audit.failed_conids_json) == []

        # Confirmation state is unconfirmed.
        state = state_repo.get_by_account_id("DU1234567")
        assert state is not None
        assert state.state == "unconfirmed"

        # First state transition logged.
        transitions = audit_repo.list_by_account_id(
            ibkr_account_id="DU1234567"
        )
        assert len(transitions.records) == 1
        assert transitions.records[0].from_state == "absent"
        assert transitions.records[0].to_state == "unconfirmed"
        assert transitions.records[0].actor == "system"
        assert transitions.records[0].row_count_at_event == 12


def test_seed_writes_starter_seed_rows_only_for_passed_account() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        seed_audit, wl_seed, state_repo, audit_repo = _build_repos(conn)
        seed_starter_watchlist(
            ibkr_account_id="DU1111111",
            seed_audit_repo=seed_audit,
            watchlist_seed_repo=wl_seed,
            confirmation_state_repo=state_repo,
            confirmation_audit_repo=audit_repo,
            listing_resolver=_AlwaysResolveListing(),
            now_provider=lambda: _BASE,
        )
        assert wl_seed.count_active_for_account("DU1111111") == 12
        assert wl_seed.count_active_for_account("DU2222222") == 0


# ---- partial failure --------------------------------------------


def test_seed_partial_failure_logs_failed_symbols_in_audit() -> None:
    missing = {"NOVO-B", "WTEC"}
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        seed_audit, wl_seed, state_repo, audit_repo = _build_repos(conn)
        result = seed_starter_watchlist(
            ibkr_account_id="DU1234567",
            seed_audit_repo=seed_audit,
            watchlist_seed_repo=wl_seed,
            confirmation_state_repo=state_repo,
            confirmation_audit_repo=audit_repo,
            listing_resolver=_PartialResolver(missing),
            now_provider=lambda: _BASE,
        )

        assert result.seeded_count == 10
        assert set(result.failed_symbols) == missing

        audit = seed_audit.find_by_account_id("DU1234567")
        assert audit is not None
        assert audit.seeded_count == 10
        assert set(json.loads(audit.failed_conids_json)) == missing


def test_seed_all_failures_still_records_audit_row_with_zero_count() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        seed_audit, wl_seed, state_repo, audit_repo = _build_repos(conn)
        result = seed_starter_watchlist(
            ibkr_account_id="DU1234567",
            seed_audit_repo=seed_audit,
            watchlist_seed_repo=wl_seed,
            confirmation_state_repo=state_repo,
            confirmation_audit_repo=audit_repo,
            listing_resolver=_AlwaysMissingListing(),
            now_provider=lambda: _BASE,
        )
        assert result.seeded_count == 0
        assert len(result.failed_symbols) == 12
        assert wl_seed.count_active_for_account("DU1234567") == 0
        # Audit row still written so the orchestrator's idempotency
        # gate kicks in next fire.
        assert seed_audit.find_by_account_id("DU1234567") is not None


# ---- idempotency -------------------------------------------------


def test_second_seed_call_returns_early_already_seeded_true() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        seed_audit, wl_seed, state_repo, audit_repo = _build_repos(conn)
        seed_starter_watchlist(
            ibkr_account_id="DU1234567",
            seed_audit_repo=seed_audit,
            watchlist_seed_repo=wl_seed,
            confirmation_state_repo=state_repo,
            confirmation_audit_repo=audit_repo,
            listing_resolver=_AlwaysResolveListing(),
            now_provider=lambda: _BASE,
        )
        assert wl_seed.count_active_for_account("DU1234567") == 12

        result = seed_starter_watchlist(
            ibkr_account_id="DU1234567",
            seed_audit_repo=seed_audit,
            watchlist_seed_repo=wl_seed,
            confirmation_state_repo=state_repo,
            confirmation_audit_repo=audit_repo,
            listing_resolver=_AlwaysResolveListing(),
            now_provider=lambda: _BASE,
        )
        assert result.already_seeded is True
        # No duplicate watchlist rows.
        assert wl_seed.count_active_for_account("DU1234567") == 12
