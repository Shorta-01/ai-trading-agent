"""End-to-end orchestrator scoring CLI (V1.2 §AA).

A focused, one-shot integration that ties the V1.2 doctrine pieces
together against a real SQLAlchemy connection. Useful for:

* Local validation — "does the full chain actually work on real
  storage, or only in unit tests?"
* Manual smoke testing — operator can run the CLI against a paper
  database, then ``SELECT * FROM orchestrator_scoring_verdicts``
  to see what the doctrine produced.
* Documentation by example — the wiring here is the contract the
  morning-chain leg follows when it is promoted out of no-op
  status (V1.2 §Y stub).

Pipeline:

1. Open a writable connection via :class:`StorageConnectionProvider`.
2. Read the trading settings (or use a hand-supplied snapshot when
   the storage layer doesn't have a row yet).
3. Read the supplied (or seeded) forecasts, fundamentals snapshot,
   held positions.
4. Hand them to :func:`build_candidates` (V1.2 §Z) → list of
   :class:`CandidateScoringInput`.
5. Hand the candidates to :func:`run_orchestrator_scoring` (V1.2 §X)
   with a verdict writer closure over
   :class:`SqlAlchemyOrchestratorScoringVerdictRepository`.

The CLI is intentionally non-interactive and parameter-light: you
hand it pre-fetched dataclasses, it persists verdicts, it returns
the summary. The "fetch from real repos" path lives in the morning-
chain wire-up; this module is the boundary that proves the
*write* side works end-to-end.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ai_trading_agent_storage import (
    SaveOrchestratorScoringVerdictRequest,
    SqlAlchemyOrchestratorScoringVerdictRepository,
)
from ai_trading_agent_storage.migration_readiness import MigrationReadinessReport

from portfolio_outlook_worker.forecasting.orchestrator_candidate_provider import (
    CandidateProviderInputs,
    build_candidates,
)
from portfolio_outlook_worker.forecasting.orchestrator_scoring_runner import (
    OrchestratorScoringRun,
    run_orchestrator_scoring,
)


@dataclass(frozen=True)
class ScoringCliRun:
    """Summary returned by :func:`run_scoring_pipeline`."""

    candidates_built: int
    skipped_provider_count: int
    scoring: OrchestratorScoringRun


def run_scoring_pipeline(
    *,
    connection: Any,
    readiness_report: MigrationReadinessReport,
    inputs: CandidateProviderInputs,
    generated_at: datetime,
) -> ScoringCliRun:
    """Run the doctrine end-to-end against a real connection.

    Args:
        connection: A live SQLAlchemy ``Connection`` (typically
            obtained via
            :func:`StorageConnectionProvider.checked_connection` with
            ``require_writable=True``).
        readiness_report: The migration-readiness report the
            connection was opened with. Forwarded to the repository
            so its writes go through the standard
            persistence-allowed gate.
        inputs: Pre-assembled provider inputs (forecasts,
            fundamentals, held positions, settings, macro
            placeholders). The caller is responsible for fetching
            this from the real repos or seeding it in tests.
        generated_at: Timestamp stamped on every verdict row.

    Returns:
        A :class:`ScoringCliRun` summarising provider + runner.
    """

    provider_result = build_candidates(inputs)
    repo = SqlAlchemyOrchestratorScoringVerdictRepository(
        connection, readiness_report
    )

    def _verdict_writer(request: SaveOrchestratorScoringVerdictRequest) -> None:
        repo.upsert_verdict(request)

    scoring = run_orchestrator_scoring(
        candidates=provider_result.candidates,
        ibkr_account_ref=inputs.ibkr_account_ref,
        generated_at=generated_at,
        verdict_writer=_verdict_writer,
    )
    return ScoringCliRun(
        candidates_built=len(provider_result.candidates),
        skipped_provider_count=provider_result.skipped_count,
        scoring=scoring,
    )


def format_run_summary(run: ScoringCliRun) -> Sequence[str]:
    """Return a list of human-readable summary lines for the CLI."""

    return (
        f"Provider built {run.candidates_built} candidates.",
        f"Provider skipped {run.skipped_provider_count} forecasts "
        f"(missing fundamentals or bars).",
        f"Scoring succeeded for {run.scoring.succeeded_count} "
        f"of {run.scoring.candidate_count} candidates.",
        f"Scoring failed for {run.scoring.failed_count} candidates "
        f"(first 10 reasons: {list(run.scoring.failure_reasons)}).",
    )


__all__ = [
    "ScoringCliRun",
    "format_run_summary",
    "run_scoring_pipeline",
]
