"""Tests for the worker-side orchestrator scoring runner (V1.2 §X)."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trading_agent_storage import SaveOrchestratorScoringVerdictRequest
from portfolio_outlook_portfolio import (
    HistoricalBar,
    OrchestratorInputs,
    TobSecurityClass,
)

from portfolio_outlook_worker.forecasting.orchestrator_scoring_runner import (
    CandidateScoringInput,
    OrchestratorScoringRun,
    run_orchestrator_scoring,
)

_GENERATED_AT = datetime(2026, 6, 12, 9, 0, tzinfo=UTC)


def _trending_up_bars(count: int = 250) -> tuple[HistoricalBar, ...]:
    base = date(2025, 1, 1)
    return tuple(
        HistoricalBar(
            bar_date=base + timedelta(days=i),
            close_price=Decimal(repr(round(100.0 + i * 0.5, 4))),
        )
        for i in range(count)
    )


def _moderate_vol_bars(count: int = 120) -> tuple[HistoricalBar, ...]:
    base = date(2025, 1, 1)
    price = 100.0
    bars = []
    for i in range(count):
        noise = math.sin(i * 17) * 0.015
        price *= math.exp(noise)
        bars.append(
            HistoricalBar(
                bar_date=base + timedelta(days=i),
                close_price=Decimal(repr(round(price, 4))),
            )
        )
    return tuple(bars)


def _inputs(
    *,
    ticker: str = "AAPL",
    market_cap_eur: Decimal | None = Decimal("3000000000000"),
    median_forecast_price: Decimal = Decimal("115"),
) -> OrchestratorInputs:
    return OrchestratorInputs(
        ticker=ticker,
        instrument_name=f"{ticker} Inc.",
        sector="technology",
        market_cap_eur=market_cap_eur,
        security_class=TobSecurityClass.STANDARD_STOCK,
        candidate_bars=_moderate_vol_bars(),
        current_price=Decimal("100"),
        median_forecast_price=median_forecast_price,
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        confidence_pct=Decimal("85"),
        vix_level=Decimal("15"),
        index_bars=_trending_up_bars(),
        existing_sector_allocations=(),
        today=date(2026, 6, 12),
        next_earnings_date=None,
        target_net_pct=Decimal("4"),
        confidence_threshold_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
        total_budget_eur=Decimal("1000000"),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
        max_sector_pct=Decimal("25"),
    )


# ---- happy path ------------------------------------------------------


def test_empty_batch_returns_zero_counts() -> None:
    sink: list[SaveOrchestratorScoringVerdictRequest] = []
    summary = run_orchestrator_scoring(
        candidates=[],
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=sink.append,
    )
    assert summary.candidate_count == 0
    assert summary.succeeded_count == 0
    assert summary.failed_count == 0
    assert summary.failure_reasons == ()
    assert sink == []


def test_single_candidate_persisted_with_suggest_decision() -> None:
    sink: list[SaveOrchestratorScoringVerdictRequest] = []
    candidate = CandidateScoringInput(
        orchestrator_inputs=_inputs(),
        forecast_id="fc-001",
        ibkr_conid=265598,
    )
    summary = run_orchestrator_scoring(
        candidates=[candidate],
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=sink.append,
    )
    assert isinstance(summary, OrchestratorScoringRun)
    assert summary.succeeded_count == 1
    assert summary.failed_count == 0
    assert len(sink) == 1
    request = sink[0]
    assert request.ibkr_account_ref == "DU1234567"
    assert request.symbol == "AAPL"
    assert request.ibkr_conid == 265598
    assert request.forecast_id == "fc-001"
    assert request.decision == "suggest"
    assert request.blocking_reason is None
    assert "AAPL" in request.summary_nl
    # Details blob populated for the gates that ran.
    assert request.details_json["macro"] is not None
    assert request.details_json["risk_universe"] is not None
    assert request.details_json["confidence"] is not None
    assert request.details_json["pair_build"] is not None


def test_skip_candidate_persisted_with_blocking_reason() -> None:
    sink: list[SaveOrchestratorScoringVerdictRequest] = []
    # Small-cap forces a risk-universe skip.
    candidate = CandidateScoringInput(
        orchestrator_inputs=_inputs(market_cap_eur=Decimal("1000000000")),
        forecast_id="fc-002",
        ibkr_conid=1,
    )
    summary = run_orchestrator_scoring(
        candidates=[candidate],
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=sink.append,
    )
    assert summary.succeeded_count == 1
    request = sink[0]
    assert request.decision == "skip_risk_universe"
    assert request.blocking_reason == "below_min_market_cap"
    # Gates that ran are populated; later gates are None.
    assert request.details_json["risk_universe"] is not None
    assert request.details_json["confidence"] is None


def test_decimal_values_stringified_in_details_blob() -> None:
    sink: list[SaveOrchestratorScoringVerdictRequest] = []
    candidate = CandidateScoringInput(
        orchestrator_inputs=_inputs(),
        forecast_id="fc-001",
        ibkr_conid=265598,
    )
    run_orchestrator_scoring(
        candidates=[candidate],
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=sink.append,
    )
    # Spot-check: confidence diagnostics have a stringified
    # target_price (Decimal → str).
    target = sink[0].details_json["confidence"]["target_price"]  # type: ignore[index]
    assert isinstance(target, str)
    assert target == "104.7300"


# ---- multi-candidate -------------------------------------------------


def test_multiple_candidates_persisted_in_order() -> None:
    sink: list[SaveOrchestratorScoringVerdictRequest] = []
    candidates = [
        CandidateScoringInput(
            orchestrator_inputs=_inputs(ticker="AAPL"),
            forecast_id="fc-aapl",
            ibkr_conid=1,
        ),
        CandidateScoringInput(
            orchestrator_inputs=_inputs(ticker="MSFT"),
            forecast_id="fc-msft",
            ibkr_conid=2,
        ),
    ]
    summary = run_orchestrator_scoring(
        candidates=candidates,
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=sink.append,
    )
    assert summary.candidate_count == 2
    assert summary.succeeded_count == 2
    assert [r.symbol for r in sink] == ["AAPL", "MSFT"]


def test_failure_in_one_candidate_does_not_stop_batch() -> None:
    sink: list[SaveOrchestratorScoringVerdictRequest] = []
    # First candidate writes fine; second writer raises.
    raise_count = [0]

    def _writer(req: SaveOrchestratorScoringVerdictRequest) -> None:
        if req.symbol == "BAD":
            raise_count[0] += 1
            raise RuntimeError("simulated DB outage")
        sink.append(req)

    candidates = [
        CandidateScoringInput(
            orchestrator_inputs=_inputs(ticker="AAPL"),
            forecast_id="fc-aapl",
            ibkr_conid=1,
        ),
        CandidateScoringInput(
            orchestrator_inputs=_inputs(ticker="BAD"),
            forecast_id="fc-bad",
            ibkr_conid=2,
        ),
        CandidateScoringInput(
            orchestrator_inputs=_inputs(ticker="MSFT"),
            forecast_id="fc-msft",
            ibkr_conid=3,
        ),
    ]
    summary = run_orchestrator_scoring(
        candidates=candidates,
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=_writer,
    )
    assert summary.candidate_count == 3
    assert summary.succeeded_count == 2
    assert summary.failed_count == 1
    assert len(summary.failure_reasons) == 1
    assert "BAD" in summary.failure_reasons[0]
    assert "persist_error" in summary.failure_reasons[0]
    assert [r.symbol for r in sink] == ["AAPL", "MSFT"]


def test_failure_reasons_capped_at_ten() -> None:
    def _writer(req: SaveOrchestratorScoringVerdictRequest) -> None:
        raise RuntimeError(f"fail-{req.symbol}")

    candidates = [
        CandidateScoringInput(
            orchestrator_inputs=_inputs(ticker=f"T{i:02d}"),
            forecast_id=f"fc-{i:02d}",
            ibkr_conid=i,
        )
        for i in range(15)
    ]
    summary = run_orchestrator_scoring(
        candidates=candidates,
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=_writer,
    )
    assert summary.failed_count == 15
    # Locked cap at 10 reasons; the runner drops the rest.
    assert len(summary.failure_reasons) == 10


# ---- determinism -----------------------------------------------------


def test_verdict_id_is_deterministic_per_candidate_and_timestamp() -> None:
    sink_a: list[SaveOrchestratorScoringVerdictRequest] = []
    sink_b: list[SaveOrchestratorScoringVerdictRequest] = []
    candidate = CandidateScoringInput(
        orchestrator_inputs=_inputs(),
        forecast_id="fc-001",
        ibkr_conid=1,
    )
    run_orchestrator_scoring(
        candidates=[candidate],
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=sink_a.append,
    )
    run_orchestrator_scoring(
        candidates=[candidate],
        ibkr_account_ref="DU1234567",
        generated_at=_GENERATED_AT,
        verdict_writer=sink_b.append,
    )
    assert sink_a[0].verdict_id == sink_b[0].verdict_id


# ---- input validation ------------------------------------------------


def test_empty_account_ref_rejected() -> None:
    with pytest.raises(ValueError):
        run_orchestrator_scoring(
            candidates=[],
            ibkr_account_ref="",
            generated_at=_GENERATED_AT,
            verdict_writer=lambda _r: None,
        )
