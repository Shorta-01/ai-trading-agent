"""Task 133 — supersede-check tests.

Locked rule (product lock §6): when a new Decision Package lands for
an asset that has a pending Action Draft, the draft is flagged
``superseded_by_decision_package_id`` — the draft itself is NOT
mutated. Already-dismissed / deleted / approved drafts are skipped.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    ActionDraftEntry,
    DecisionPackageEntry,
    EvidenceReference,
    GateOutcome,
    SqlAlchemyActionDraftRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)

from portfolio_outlook_worker.action_draft.supersede_check import (
    mark_superseded_drafts,
)

_BASE_TS = datetime(2026, 5, 26, 7, 0, tzinfo=UTC)


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0051_action_drafts_and_audit",
        database_revision_id="0051_action_drafts_and_audit",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _draft(
    *,
    draft_id: str,
    decision_package_id: str = "dp-1",
    status: str = "proposed",
    conid: str = "ASML.AS",
    account_id: str = "DU1234567",
    audit_trail_hash: str = "h-1",
) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id=draft_id,
        decision_package_id=decision_package_id,
        forecast_run_id="fcst-1",
        created_at=_BASE_TS,
        created_by="user",
        ibkr_account_id=account_id,
        conid=conid,
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        side="BUY",
        quantity=Decimal("10"),
        order_type="LMT",
        limit_price_local=Decimal("638.72"),
        time_in_force="DAY",
        notional_local=Decimal("6387.20"),
        notional_eur=Decimal("6387.20"),
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000"),
        held_quantity_at_creation=None,
        status=status,
        last_edited_at=None,
        user_approved_at=None,
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash=audit_trail_hash,
        previous_draft_hash=None,
        safe_for_submission=False,
    )


def _package(
    *,
    package_id: str = "dp-2",
    conid: str = "ASML.AS",
    account_id: str = "DU1234567",
) -> DecisionPackageEntry:
    return DecisionPackageEntry(
        decision_package_id=package_id,
        forecast_run_id="fcst-new",
        composed_at=_BASE_TS + timedelta(days=1),
        valid_until=_BASE_TS + timedelta(days=29),
        ibkr_account_id=account_id,
        conid=conid,
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        asset_class="STK",
        user_holds_position=False,
        held_quantity=None,
        held_avg_cost_local=None,
        current_price_local=Decimal("650.00"),
        current_price_eur=Decimal("650.00"),
        as_of_market_data_ts=_BASE_TS + timedelta(hours=12),
        freshness_state="fresh",
        data_age_trading_days=0,
        forecast_method="historical_bootstrap_v1",
        p10_log_return=Decimal("-0.05"),
        p50_log_return=Decimal("0.02"),
        p90_log_return=Decimal("0.08"),
        p10_price_eur=Decimal("615.00"),
        p50_price_eur=Decimal("663.00"),
        p90_price_eur=Decimal("703.00"),
        prob_positive=Decimal("0.65"),
        prob_loss_gt_5pct=Decimal("0.10"),
        expected_volatility_annualized=Decimal("0.22"),
        forecast_confidence_level="Hoog",
        suggested_action_label="Kopen",
        block_reason=None,
        gate_outcomes=(GateOutcome(gate_name="forecast_valid", passed=True, reason_nl=""),),
        evidence_references=(
            EvidenceReference(
                source_id="snap-1",
                source_type="market_data_snapshot",
                claim_summary="snap",
            ),
        ),
        deterministic_dutch_explanation="ex",
        audit_trail_hash="dp-hash-new",
        previous_package_hash=None,
        safe_for_action_drafts=False,
        safe_for_orders=False,
    )


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def test_marks_pending_drafts_superseded_by_new_package() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft(draft_id="d-prop"))
        result = mark_superseded_drafts(
            decision_packages=[_package()],
            action_draft_repo=repo,
            now=_BASE_TS + timedelta(days=1),
        )
        assert result.marked_count == 1
        assert result.skipped_count == 0
        assert result.error_count == 0
        fetched = repo.get_by_id("d-prop")
        assert fetched is not None
        assert fetched.superseded_by_decision_package_id == "dp-2"
        assert fetched.status == "proposed"


def test_skips_already_dismissed_draft() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft(draft_id="d-prop"))
        repo.append(
            _draft(
                draft_id="d-dism",
                status="dismissed",
                audit_trail_hash="h-2",
            )
        )
        result = mark_superseded_drafts(
            decision_packages=[_package()],
            action_draft_repo=repo,
            now=_BASE_TS + timedelta(days=1),
        )
        # Only the pending draft gets flagged.
        assert result.marked_count == 1
        fetched = repo.get_by_id("d-dism")
        assert fetched is not None
        assert fetched.superseded_by_decision_package_id is None
        assert fetched.status == "dismissed"


def test_skips_when_draft_already_references_the_new_package() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        # Draft already references dp-2 directly — it's the FRESH draft,
        # not a stale one. supersede_check must not mark itself.
        repo.append(
            _draft(
                draft_id="d-fresh",
                decision_package_id="dp-2",
            )
        )
        result = mark_superseded_drafts(
            decision_packages=[_package(package_id="dp-2")],
            action_draft_repo=repo,
            now=_BASE_TS + timedelta(days=1),
        )
        assert result.marked_count == 0
        assert result.skipped_count == 1


def test_idempotent_when_flag_already_set() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft(draft_id="d-prop"))
        mark_superseded_drafts(
            decision_packages=[_package()],
            action_draft_repo=repo,
            now=_BASE_TS + timedelta(days=1),
        )
        # Second pass with the same package should be a no-op.
        result = mark_superseded_drafts(
            decision_packages=[_package()],
            action_draft_repo=repo,
            now=_BASE_TS + timedelta(days=2),
        )
        assert result.marked_count == 0
        assert result.skipped_count == 1


def test_isolates_per_asset_to_correct_conid() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft(draft_id="d-asml", conid="ASML.AS"))
        repo.append(_draft(draft_id="d-shel", conid="SHEL.L", audit_trail_hash="h-2"))
        result = mark_superseded_drafts(
            decision_packages=[_package(conid="ASML.AS")],
            action_draft_repo=repo,
            now=_BASE_TS + timedelta(days=1),
        )
        assert result.marked_count == 1
        assert "d-asml" in result.marked_draft_ids

        shel_draft = repo.get_by_id("d-shel")
        assert shel_draft is not None
        assert shel_draft.superseded_by_decision_package_id is None
