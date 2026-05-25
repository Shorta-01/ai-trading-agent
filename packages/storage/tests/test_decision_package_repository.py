"""Task 132 — Decision Package repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    DecisionPackageEntry,
    EvidenceReference,
    GateOutcome,
    SqlAlchemyDecisionPackageRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
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
        latest_expected_revision_id="0050_decision_packages",
        database_revision_id=(
            "0050_decision_packages" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


_BASE_TS = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


def _gate(name: str, passed: bool = True, reason: str = "") -> GateOutcome:
    return GateOutcome(
        gate_name=name,
        passed=passed,
        reason_nl=reason if not passed else "",
    )


def _evidence(idx: int = 1) -> EvidenceReference:
    return EvidenceReference(
        source_id=f"snap-{idx}",
        source_type="market_data_snapshot",
        claim_summary=f"Snapshot {idx}",
    )


def _package(
    *,
    package_id: str = "dp-1",
    forecast_run_id: str = "fcst-1",
    conid: str = "ASML.AS",
    account_id: str = "DU1234567",
    composed_at: datetime | None = None,
    audit_trail_hash: str = "hash-1",
    previous_package_hash: str | None = None,
    label: str = "Bekijken",
    safe_for_action_drafts: bool = False,
    safe_for_orders: bool = False,
) -> DecisionPackageEntry:
    ts = composed_at or _BASE_TS
    return DecisionPackageEntry(
        decision_package_id=package_id,
        forecast_run_id=forecast_run_id,
        composed_at=ts,
        valid_until=ts + timedelta(days=28),
        ibkr_account_id=account_id,
        conid=conid,
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        asset_class="STK",
        user_holds_position=False,
        held_quantity=None,
        held_avg_cost_local=None,
        current_price_local=Decimal("640.000000"),
        current_price_eur=Decimal("640.000000"),
        as_of_market_data_ts=ts - timedelta(hours=12),
        freshness_state="fresh",
        data_age_trading_days=0,
        forecast_method="historical_bootstrap_v1",
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        p10_price_eur=Decimal("608.769000"),
        p50_price_eur=Decimal("652.929000"),
        p90_price_eur=Decimal("693.282000"),
        prob_positive=Decimal("0.62"),
        prob_loss_gt_5pct=Decimal("0.12"),
        expected_volatility_annualized=Decimal("0.25"),
        forecast_confidence_level="Hoog",
        suggested_action_label=label,
        block_reason=None,
        gate_outcomes=(
            _gate("forecast_valid"),
            _gate("data_fresh"),
        ),
        evidence_references=(_evidence(1),),
        deterministic_dutch_explanation=(
            "Voorspelling voor ASML met label Bekijken; geldig tot "
            "22 juni 2026."
        ),
        audit_trail_hash=audit_trail_hash,
        previous_package_hash=previous_package_hash,
        safe_for_action_drafts=safe_for_action_drafts,
        safe_for_orders=safe_for_orders,
    )


# ---- happy path ----------------------------------------------------


def test_append_and_get_by_id_roundtrips_record() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        record = _package()
        result = repo.append(record)
        assert result.accepted is True
        fetched = repo.get_by_id("dp-1")
        assert fetched is not None
        assert fetched.decision_package_id == "dp-1"
        assert fetched.suggested_action_label == "Bekijken"
        assert fetched.audit_trail_hash == "hash-1"
        # Round-trip preserves the gate/evidence structure.
        assert len(fetched.gate_outcomes) == 2
        assert fetched.gate_outcomes[0].gate_name == "forecast_valid"
        assert len(fetched.evidence_references) == 1
        # Decimal preserved end-to-end.
        assert fetched.current_price_eur == Decimal("640.000000")
        assert fetched.p50_price_eur == Decimal("652.929000")


def test_get_by_id_returns_none_when_missing() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        assert repo.get_by_id("does-not-exist") is None


def test_get_latest_for_account_conid_returns_most_recent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        repo.append(
            _package(
                package_id="dp-1",
                audit_trail_hash="h-1",
                composed_at=_BASE_TS - timedelta(days=2),
            )
        )
        repo.append(
            _package(
                package_id="dp-2",
                audit_trail_hash="h-2",
                previous_package_hash="h-1",
                composed_at=_BASE_TS,
            )
        )
        latest = repo.get_latest_for_account_conid(
            ibkr_account_id="DU1234567", conid="ASML.AS"
        )
        assert latest is not None
        assert latest.decision_package_id == "dp-2"
        assert latest.previous_package_hash == "h-1"


def test_get_latest_filters_by_account_and_conid() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        repo.append(
            _package(
                package_id="dp-asml",
                conid="ASML.AS",
                audit_trail_hash="h-asml",
            )
        )
        repo.append(
            _package(
                package_id="dp-sap",
                conid="SAP.DE",
                audit_trail_hash="h-sap",
            )
        )
        asml = repo.get_latest_for_account_conid(
            ibkr_account_id="DU1234567", conid="ASML.AS"
        )
        sap = repo.get_latest_for_account_conid(
            ibkr_account_id="DU1234567", conid="SAP.DE"
        )
        assert asml is not None and asml.conid == "ASML.AS"
        assert sap is not None and sap.conid == "SAP.DE"
        # Different account isolation.
        other_account = repo.get_latest_for_account_conid(
            ibkr_account_id="DU9999999", conid="ASML.AS"
        )
        assert other_account is None


def test_list_chain_returns_packages_newest_first() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        for i in range(3):
            repo.append(
                _package(
                    package_id=f"dp-{i}",
                    audit_trail_hash=f"h-{i}",
                    previous_package_hash=f"h-{i - 1}" if i > 0 else None,
                    composed_at=_BASE_TS + timedelta(hours=i),
                )
            )
        chain = repo.list_chain(
            ibkr_account_id="DU1234567", conid="ASML.AS", limit=10
        )
        ids = [p.decision_package_id for p in chain.records]
        assert ids == ["dp-2", "dp-1", "dp-0"]


def test_list_chain_respects_limit() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        for i in range(5):
            repo.append(
                _package(
                    package_id=f"dp-{i}",
                    audit_trail_hash=f"h-{i}",
                    composed_at=_BASE_TS + timedelta(hours=i),
                )
            )
        chain = repo.list_chain(
            ibkr_account_id="DU1234567", conid="ASML.AS", limit=2
        )
        assert len(chain.records) == 2


# ---- hash chain integrity ----------------------------------------


def test_hash_chain_links_consecutive_packages() -> None:
    """Second package's previous_package_hash matches first's hash."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        repo.append(
            _package(package_id="dp-1", audit_trail_hash="hash-first")
        )
        repo.append(
            _package(
                package_id="dp-2",
                audit_trail_hash="hash-second",
                previous_package_hash="hash-first",
                composed_at=_BASE_TS + timedelta(hours=1),
            )
        )
        chain = repo.list_chain(
            ibkr_account_id="DU1234567", conid="ASML.AS", limit=10
        )
        latest, prior = chain.records
        assert latest.previous_package_hash == prior.audit_trail_hash


# ---- safety boolean enforcement ----------------------------------


def test_dataclass_rejects_true_safe_for_action_drafts() -> None:
    with pytest.raises(ValueError, match="safe_for_action_drafts"):
        _package(safe_for_action_drafts=True)


def test_dataclass_rejects_true_safe_for_orders() -> None:
    with pytest.raises(ValueError, match="safe_for_orders"):
        _package(safe_for_orders=True)


def test_dataclass_rejects_geblokkeerd_label() -> None:
    with pytest.raises(ValueError, match="suggested_action_label"):
        _package(label="Geblokkeerd")


def test_repository_rejects_true_safety_flags_at_append_time() -> None:
    """Defense in depth — caller may have forged a record with
    ``object.__setattr__`` past the dataclass guard. The repo enforces
    the same invariant before the DB ever sees the row.
    """

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyDecisionPackageRepository(conn, _report(True))
        record = _package()
        object.__setattr__(record, "safe_for_action_drafts", True)
        with pytest.raises(ValueError, match="safe_for_action_drafts"):
            repo.append(record)


# ---- immutability surface -----------------------------------------


def test_repository_has_no_update_or_delete_methods() -> None:
    """Task 132 product lock §4 — Decision Packages are append-only.

    Future contributors who add an ``update`` or ``delete`` method
    must read the lock before doing so. This test fails loudly to
    surface the violation in code review.
    """

    forbidden = {"update", "delete", "update_by_id", "delete_by_id"}
    public = {
        name
        for name in dir(SqlAlchemyDecisionPackageRepository)
        if not name.startswith("_")
    }
    assert (
        public & forbidden == set()
    ), f"Decision Package repo grew a forbidden mutation method: {public & forbidden}"
