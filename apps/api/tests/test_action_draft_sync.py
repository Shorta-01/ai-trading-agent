"""Tests for the action-draft orchestrator.

The math is exhaustively covered in
``packages/portfolio/tests/test_action_draft_safety.py``. Here we focus on:
how the orchestrator decides which Decision Packages produce drafts, how it
classifies skips vs persisted vs failed, and that the persisted record
keeps every safety boolean False.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetActionDraftRecord,
    AssetDecisionPackageRecord,
)

from portfolio_outlook_api.action_draft_sync import (
    generate_action_drafts,
    serialize_action_draft_for_response,
)

_NOW = datetime(2025, 5, 24, tzinfo=UTC)


def _package(
    *,
    conid: str = "1",
    symbol: str = "AAPL",
    action_label: str = "Kopen",
    status: str = "ready",
    market_last_price: str | None = "180",
    position_quantity: str = "0",
    cash_amount: str | None = "10000",
    cash_currency: str | None = "USD",
    currency: str = "USD",
    fx_pair: str | None = None,
    fx_rate: str | None = None,
    fx_freshness_status: str | None = None,
) -> AssetDecisionPackageRecord:
    return AssetDecisionPackageRecord(
        decision_package_id=f"dp_{conid}",
        content_hash=f"hash_{conid}",
        ibkr_conid=conid,
        symbol=symbol,
        currency=currency,
        risk_profile="Gebalanceerd",
        generated_at=_NOW,
        valid_until=_NOW,
        position_snapshot_id="pos-1" if Decimal(position_quantity) > 0 else None,
        position_quantity=Decimal(position_quantity),
        position_average_cost=None,
        cash_snapshot_id="cash-1" if cash_amount is not None else None,
        cash_base_currency=cash_currency,
        cash_amount=Decimal(cash_amount) if cash_amount is not None else None,
        market_snapshot_id="md-1",
        market_last_price=Decimal(market_last_price) if market_last_price is not None else None,
        market_freshness_status="fresh",
        market_provider_code="eodhd",
        market_provider_as_of=_NOW,
        fx_pair=fx_pair,
        fx_rate=Decimal(fx_rate) if fx_rate is not None else None,
        fx_freshness_status=fx_freshness_status,
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
        forecast_confidence_score=Decimal("0.85"),
        suggestion_id="suggestion-1",
        suggestion_model_code="baseline_label_translator",
        suggestion_action_label=action_label,
        suggestion_action_label_nl=action_label,
        suggestion_confidence_label="Hoog",
        suggestion_confidence_label_nl="Hoog",
        suggestion_status=status,
        has_position=Decimal(position_quantity) > 0,
        gate_outcomes_json=("market_data:fresh", "forecast:ready"),
        evidence_links_json=None,
        audit_links_json=None,
        rationale_nl="rationale",
        explanation_nl="explanation",
        status="ready" if status == "ready" else status,
        blocking_reason=None,
    )


class FakeRepo:
    def __init__(self) -> None:
        self.saved: list[AssetActionDraftRecord] = []

    def save_asset_action_draft(self, record: AssetActionDraftRecord) -> object:
        self.saved.append(record)
        return None


class RaisingRepo:
    def save_asset_action_draft(self, record: AssetActionDraftRecord) -> object:
        raise RuntimeError("boom")


def test_kopen_package_produces_one_draft_persisted_with_dry_run_passed() -> None:
    repo = FakeRepo()

    report = generate_action_drafts(
        decision_packages=[_package(action_label="Kopen")],
        repo=repo,
        expected_account_mode="paper",
        total_portfolio_value=Decimal("100000"),
        base_currency="USD",
        default_buy_value=Decimal("1000"),
        top_up_pct=Decimal("0.25"),
        reduce_pct=Decimal("0.25"),
        position_exchange_by_conid={"1": ("SMART", "NASDAQ")},
    )

    assert report.draft_total == 1
    assert report.draft_persisted == 1
    assert report.dry_run_passed == 1
    assert report.dry_run_failed == 0
    record = repo.saved[0]
    assert record.action_side == "BUY"
    assert record.quantity == Decimal("5")
    assert record.order_type == "LMT"
    assert record.tif == "DAY"
    assert record.dry_run_status == "passed"
    assert record.status == "dry_run_passed"
    assert record.safe_for_submission is False
    assert record.safe_for_orders is False
    assert record.safe_for_broker_submission is False


def test_verkopen_package_produces_sell_draft_for_full_held_quantity() -> None:
    repo = FakeRepo()

    report = generate_action_drafts(
        decision_packages=[_package(action_label="Verkopen", position_quantity="15")],
        repo=repo,
        expected_account_mode="paper",
        total_portfolio_value=Decimal("100000"),
        base_currency="USD",
        default_buy_value=Decimal("1000"),
        top_up_pct=Decimal("0.25"),
        reduce_pct=Decimal("0.25"),
        position_exchange_by_conid={"1": ("SMART", "NASDAQ")},
    )

    assert report.draft_persisted == 1
    record = repo.saved[0]
    assert record.action_side == "SELL"
    assert record.quantity == Decimal("15")
    assert record.dry_run_status == "passed"


def test_non_actionable_label_is_skipped_and_classified() -> None:
    repo = FakeRepo()

    report = generate_action_drafts(
        decision_packages=[_package(action_label="Houden")],
        repo=repo,
        expected_account_mode="paper",
        total_portfolio_value=Decimal("10000"),
        base_currency="USD",
        default_buy_value=Decimal("1000"),
        top_up_pct=Decimal("0.25"),
        reduce_pct=Decimal("0.25"),
    )

    assert report.draft_total == 1
    assert report.draft_persisted == 0
    assert report.draft_skipped_non_actionable == 1
    assert any(f["reason"] == "non_actionable_label" for f in report.failures)


def test_blocked_decision_package_skips_with_recorded_reason() -> None:
    repo = FakeRepo()

    report = generate_action_drafts(
        decision_packages=[_package(action_label="Geblokkeerd", status="blocked")],
        repo=repo,
        expected_account_mode="paper",
        total_portfolio_value=Decimal("10000"),
        base_currency="USD",
        default_buy_value=Decimal("1000"),
        top_up_pct=Decimal("0.25"),
        reduce_pct=Decimal("0.25"),
    )

    assert report.draft_persisted == 0
    assert report.draft_skipped_non_actionable == 1
    assert any(f["reason"] == "decision_package_not_ready" for f in report.failures)


def test_sizing_blocked_when_market_price_missing() -> None:
    repo = FakeRepo()

    report = generate_action_drafts(
        decision_packages=[
            _package(action_label="Kopen", market_last_price=None)
        ],
        repo=repo,
        expected_account_mode="paper",
        total_portfolio_value=Decimal("10000"),
        base_currency="USD",
        default_buy_value=Decimal("1000"),
        top_up_pct=Decimal("0.25"),
        reduce_pct=Decimal("0.25"),
        position_exchange_by_conid={"1": ("SMART", "NASDAQ")},
    )

    assert report.draft_persisted == 0
    assert report.draft_skipped_sizing_blocked == 1
    assert any(f["reason"] == "missing_market_price" for f in report.failures)


def test_persistence_failure_is_classified_as_failed() -> None:
    report = generate_action_drafts(
        decision_packages=[_package(action_label="Kopen")],
        repo=RaisingRepo(),
        expected_account_mode="paper",
        total_portfolio_value=Decimal("10000"),
        base_currency="USD",
        default_buy_value=Decimal("1000"),
        top_up_pct=Decimal("0.25"),
        reduce_pct=Decimal("0.25"),
        position_exchange_by_conid={"1": ("SMART", "NASDAQ")},
    )

    assert report.draft_persisted == 0
    assert report.draft_failed == 1
    assert any(f["reason"] == "persistence_error" for f in report.failures)


def test_dry_run_fails_when_buy_exceeds_cash() -> None:
    """Even when the dry-run fails, the orchestrator still persists the
    draft so the user can edit and re-run."""

    repo = FakeRepo()

    report = generate_action_drafts(
        decision_packages=[_package(action_label="Kopen", cash_amount="100")],
        repo=repo,
        expected_account_mode="paper",
        total_portfolio_value=Decimal("100"),
        base_currency="USD",
        default_buy_value=Decimal("1000"),
        top_up_pct=Decimal("0.25"),
        reduce_pct=Decimal("0.25"),
        position_exchange_by_conid={"1": ("SMART", "NASDAQ")},
    )

    assert report.draft_persisted == 1
    assert report.dry_run_failed == 1
    record = repo.saved[0]
    assert record.dry_run_status == "failed"
    assert record.dry_run_failures_json is not None
    assert "buy_value_exceeds_usable_cash" in record.dry_run_failures_json


def test_serializer_renders_decimals_as_strings_and_strips_safety_flags() -> None:
    repo = FakeRepo()
    generate_action_drafts(
        decision_packages=[_package(action_label="Kopen")],
        repo=repo,
        expected_account_mode="paper",
        total_portfolio_value=Decimal("10000"),
        base_currency="USD",
        default_buy_value=Decimal("1000"),
        top_up_pct=Decimal("0.25"),
        reduce_pct=Decimal("0.25"),
        position_exchange_by_conid={"1": ("SMART", "NASDAQ")},
    )

    rendered = serialize_action_draft_for_response(repo.saved[0])
    for key in ("quantity", "limit_price", "estimated_order_value"):
        assert isinstance(rendered[key], str)
    assert rendered["safe_for_submission"] is False
    assert rendered["safe_for_orders"] is False
    assert rendered["safe_for_broker_submission"] is False
    assert isinstance(rendered["dry_run_failures"], list)
