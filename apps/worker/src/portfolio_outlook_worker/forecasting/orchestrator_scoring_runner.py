"""Orchestrator scoring runner (V1.2 §X).

Worker-side scoring loop that runs the profit-harvest doctrine
orchestrator on a batch of pre-assembled candidates and writes one
verdict per candidate to ``orchestrator_scoring_verdicts``.

V1.2 §M built the orchestrator as a pure function. V1.2 §W shipped
the storage table + repository. This module is the bridge: a
runner that the morning chain (or a one-off CLI) can call once per
forecast cycle, iterates candidates, scores each, and persists the
verdict.

Design decisions:

* **Inputs are pre-assembled by the caller.** The runner does not
  fetch bars, forecasts, or news. The caller (the morning-chain
  leg or a CLI fixture) builds one ``CandidateScoringInput`` per
  candidate from whatever live data sources are available, then
  hands the list to ``run_orchestrator_scoring``. This keeps the
  runner pure and testable.
* **Errors per candidate do not stop the batch.** A bad input or
  orchestrator exception is captured as a ``failure_reasons``
  entry and the loop continues. Worst case: the batch reports a
  failure count but every successful candidate is persisted.
* **Verdict writer is injected.** Tests pass a fake collector; the
  morning-chain leg passes a closure over the SQL repository.
  Decouples the runner from the storage layer.

Pure Python; uses Decimal-only math through the orchestrator.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import Any, Final, cast

# Use SaveRequest from the storage package — the runner is allowed
# to depend on storage *types* (frozen dataclasses), just not on
# the connection layer. The writer is injected so the actual SQL
# call lives one layer up.
from ai_trading_agent_storage import SaveOrchestratorScoringVerdictRequest
from portfolio_outlook_portfolio import (
    OrchestratorInputs,
    OrchestratorResult,
    evaluate_profit_harvest_candidate,
    explain_decision,
)


@dataclass(frozen=True)
class CandidateScoringInput:
    """One pre-assembled candidate plus its provenance keys.

    ``orchestrator_inputs`` is the fully-built input for the
    doctrine orchestrator. ``forecast_id`` and ``ibkr_conid`` are
    carried alongside so the verdict row can cross-reference the
    forecast it scored against and the broker contract ID.
    """

    orchestrator_inputs: OrchestratorInputs
    forecast_id: str | None
    ibkr_conid: int | None


@dataclass(frozen=True)
class OrchestratorScoringRun:
    """Summary of one runner invocation.

    ``failure_reasons`` is intentionally a list of strings rather
    than typed exceptions — the morning-chain leg writes the count
    + a sample of reasons to its audit row, not the full traceback.
    """

    candidate_count: int
    succeeded_count: int
    failed_count: int
    failure_reasons: tuple[str, ...]


# Locked: maximum number of failure reasons we carry through the
# summary. Past this we drop the rest to keep the audit row bounded.
_MAX_FAILURE_REASONS: Final[int] = 10


def _verdict_id_for(candidate: CandidateScoringInput, generated_at: datetime) -> str:
    """Deterministic verdict_id derived from candidate + timestamp.

    Using a deterministic ID means re-running the same batch on the
    same forecast row upserts (the UNIQUE constraint handles the
    rest). Format: ``ovd_<symbol>_<forecast_id>_<unix_ts>``.
    """

    fc_part = candidate.forecast_id if candidate.forecast_id is not None else "nofc"
    ticker = candidate.orchestrator_inputs.ticker
    ts = int(generated_at.timestamp())
    return f"ovd_{ticker}_{fc_part}_{ts}"


def _result_to_save_request(
    *,
    candidate: CandidateScoringInput,
    result: OrchestratorResult,
    ibkr_account_ref: str,
    generated_at: datetime,
) -> SaveOrchestratorScoringVerdictRequest:
    """Pack an :class:`OrchestratorResult` into the storage shape.

    The diagnostics blob carries the gate outputs as plain dicts so
    the operator UI can render them without re-running the math.
    Decimal values stringify cleanly through ``asdict`` followed by
    ``str`` coercion — preserving precision through JSON.
    """

    def _gate_to_json(gate: object | None) -> object | None:
        if gate is None or not is_dataclass(gate) or isinstance(gate, type):
            return None
        return _stringify_decimals(asdict(cast(Any, gate)))

    details = {
        "macro": _gate_to_json(result.macro),
        "risk_universe": _gate_to_json(result.risk_universe),
        "earnings": _gate_to_json(result.earnings),
        "confidence": _gate_to_json(result.confidence),
        "news_sentiment": _gate_to_json(result.news_sentiment),
        "sector_concentration": _gate_to_json(result.sector_concentration),
        "pair_build": _gate_to_json(result.pair_build),
        "boosted_confidence_pct": (
            str(result.boosted_confidence_pct)
            if result.boosted_confidence_pct is not None
            else None
        ),
        "proposed_position_eur": (
            str(result.proposed_position_eur)
            if result.proposed_position_eur is not None
            else None
        ),
    }

    return SaveOrchestratorScoringVerdictRequest(
        verdict_id=_verdict_id_for(candidate, generated_at),
        ibkr_account_ref=ibkr_account_ref,
        symbol=candidate.orchestrator_inputs.ticker,
        ibkr_conid=candidate.ibkr_conid,
        forecast_id=candidate.forecast_id,
        generated_at=generated_at,
        decision=result.decision,
        blocking_reason=result.blocking_reason,
        details_json=details,
        summary_nl=explain_decision(result),
    )


def _stringify_decimals(obj: object) -> object:
    """Recurse a dict/list and coerce Decimal values to ``str``.

    JSON has no native Decimal; stringifying preserves precision
    end-to-end (the operator UI parses to ``BigNumber`` on read).
    """

    from decimal import Decimal

    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _stringify_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_stringify_decimals(v) for v in obj]
    return obj


def run_orchestrator_scoring(
    *,
    candidates: Sequence[CandidateScoringInput],
    ibkr_account_ref: str,
    generated_at: datetime,
    verdict_writer: Callable[[SaveOrchestratorScoringVerdictRequest], None],
) -> OrchestratorScoringRun:
    """Score a batch of candidates and persist verdicts.

    Per-candidate errors are caught and surfaced via
    ``failure_reasons`` rather than propagated, so one bad row
    cannot cancel the whole batch. The morning-chain leg reads the
    returned summary to decide whether to flag the run as
    succeeded / partial / failed.

    Args:
        candidates: Pre-assembled inputs, one per candidate.
        ibkr_account_ref: Account-scope key written on every
            verdict row.
        generated_at: Timestamp written on every verdict row;
            also used to derive deterministic verdict IDs so
            re-running upserts cleanly.
        verdict_writer: Callable that persists one
            :class:`SaveOrchestratorScoringVerdictRequest`. Tests
            inject a collector; the morning-chain leg injects a
            closure over the SQL repository's ``upsert_verdict``.

    Returns:
        :class:`OrchestratorScoringRun` summarising counts and a
        bounded list of failure reasons.
    """

    if not isinstance(ibkr_account_ref, str) or not ibkr_account_ref.strip():
        raise ValueError("ibkr_account_ref must be a non-empty string")

    succeeded = 0
    failed = 0
    reasons: list[str] = []
    for candidate in candidates:
        try:
            result = evaluate_profit_harvest_candidate(
                candidate.orchestrator_inputs
            )
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if len(reasons) < _MAX_FAILURE_REASONS:
                reasons.append(
                    f"{candidate.orchestrator_inputs.ticker}: orchestrator_error: {exc}"
                )
            continue
        try:
            request = _result_to_save_request(
                candidate=candidate,
                result=result,
                ibkr_account_ref=ibkr_account_ref,
                generated_at=generated_at,
            )
            verdict_writer(request)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if len(reasons) < _MAX_FAILURE_REASONS:
                reasons.append(
                    f"{candidate.orchestrator_inputs.ticker}: persist_error: {exc}"
                )
            continue
        succeeded += 1

    return OrchestratorScoringRun(
        candidate_count=len(candidates),
        succeeded_count=succeeded,
        failed_count=failed,
        failure_reasons=tuple(reasons),
    )


__all__ = [
    "CandidateScoringInput",
    "OrchestratorScoringRun",
    "run_orchestrator_scoring",
]
