"""Predictor performance summary — dashboard "best models this month".

``GET /predictors/performance?lookback_days=30&limit=200`` aggregates
the per-(predictor x diary entry) contribution rows into a leaderboard
keyed by ``model_code``. The dashboard widget renders the top entry
("Best deze maand: GBM, n=18, Brier=0.21").

Pure aggregation read-only — never authorises an order. Mirrors the
auto-weighted ensemble strategy's data path (Slice 26 already reads
the same rolling Brier from these rows), so what the operator sees on
the dashboard matches what the combiner uses internally.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    PredictionDiaryPredictorContributionRecord,
    SqlAlchemyPredictionDiaryPredictorContributionRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_LOOKBACK_DAYS = 30
_MAX_LOOKBACK_DAYS = 365
_DEFAULT_PULL_LIMIT = 500
_MAX_PULL_LIMIT = 2000


class PredictorPerformanceEntry(BaseModel):
    """One predictor's aggregated performance over the window."""

    model_code: str
    model_version: str
    sample_count: int
    realised_sample_count: int
    mean_brier_score: str | None
    mean_return_spread_pct: str | None
    mean_realised_return_pct: str | None


class PredictorPerformanceResponse(BaseModel):
    status: str
    status_nl: str
    help_nl: str
    lookback_days: int
    total_contributions_considered: int
    predictors: list[PredictorPerformanceEntry]
    best_model_code: str | None
    safe_for_orders: bool
    safe_for_action_drafts: bool


_HELP_NL = (
    "Per-predictor rolling performance over de gekozen periode. "
    "Brier-score is een lager-is-beter probabiliteits-fout. "
    "``return_spread_pct`` is het verschil tussen voorspelde en "
    "gerealiseerde return; ``realised_return_pct`` is de gemiddelde "
    "marktoutcome. Pure aggregatie — geen advies, geen order-trigger."
)


def _empty(
    status: str, status_nl: str, lookback_days: int
) -> PredictorPerformanceResponse:
    return PredictorPerformanceResponse(
        status=status,
        status_nl=status_nl,
        help_nl=_HELP_NL,
        lookback_days=lookback_days,
        total_contributions_considered=0,
        predictors=[],
        best_model_code=None,
        safe_for_orders=False,
        safe_for_action_drafts=False,
    )


def _mean(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    total = sum(values, Decimal("0"))
    return total / Decimal(len(values))


def _aggregate(
    records: list[PredictionDiaryPredictorContributionRecord],
    *,
    since: datetime,
) -> list[PredictorPerformanceEntry]:
    """Group + aggregate; sort best-first by mean Brier score.

    Predictors with NO realised outcomes are still listed (so the
    operator can see "this predictor is active but no data yet")
    but they sort after those with realised data.
    """

    in_window = [r for r in records if r.created_at >= since]

    grouped: dict[
        tuple[str, str], list[PredictionDiaryPredictorContributionRecord]
    ] = defaultdict(list)
    for r in in_window:
        grouped[(r.model_code, r.model_version)].append(r)

    entries: list[PredictorPerformanceEntry] = []
    for (model_code, model_version), rows in grouped.items():
        brier_values = [r.brier_score for r in rows if r.brier_score is not None]
        spread_values = [
            r.return_spread_pct for r in rows if r.return_spread_pct is not None
        ]
        realised_values = [
            r.realised_return_pct
            for r in rows
            if r.realised_return_pct is not None
        ]
        mean_brier = _mean(brier_values)
        mean_spread = _mean(spread_values)
        mean_realised = _mean(realised_values)
        entries.append(
            PredictorPerformanceEntry(
                model_code=model_code,
                model_version=model_version,
                sample_count=len(rows),
                realised_sample_count=len(realised_values),
                mean_brier_score=(
                    f"{mean_brier:.4f}" if mean_brier is not None else None
                ),
                mean_return_spread_pct=(
                    f"{mean_spread:.4f}" if mean_spread is not None else None
                ),
                mean_realised_return_pct=(
                    f"{mean_realised:.4f}"
                    if mean_realised is not None
                    else None
                ),
            )
        )

    # Sort: predictors WITH a Brier score first (lowest = best);
    # then predictors with NO Brier sorted by sample_count desc.
    def _sort_key(
        e: PredictorPerformanceEntry,
    ) -> tuple[int, float, int]:
        has_brier = 0 if e.mean_brier_score is not None else 1
        brier = (
            float(e.mean_brier_score)
            if e.mean_brier_score is not None
            else 0.0
        )
        return (has_brier, brier, -e.sample_count)

    entries.sort(key=_sort_key)
    return entries


@router.get(
    "/predictors/performance",
    response_model=PredictorPerformanceResponse,
)
def read_predictor_performance(
    lookback_days: int = Query(
        default=_DEFAULT_LOOKBACK_DAYS, ge=1, le=_MAX_LOOKBACK_DAYS
    ),
    limit: int = Query(
        default=_DEFAULT_PULL_LIMIT, ge=1, le=_MAX_PULL_LIMIT
    ),
) -> PredictorPerformanceResponse:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty(
            "not_configured",
            "Opslag niet geconfigureerd; geen predictor-performance.",
            lookback_days,
        )

    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = (
                SqlAlchemyPredictionDiaryPredictorContributionRepository(
                    checked.connection, checked.readiness
                )
            )
            result = repo.list_recent_contributions(limit=limit)
            records = list(result.records)
    except StorageConnectionError as exc:
        logger.warning("predictor-performance storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    since = datetime.now(UTC) - timedelta(days=lookback_days)
    entries = _aggregate(records, since=since)
    in_window_count = sum(e.sample_count for e in entries)
    best_model_code = entries[0].model_code if entries else None
    status_nl = (
        f"{len(entries)} predictors actief in de laatste "
        f"{lookback_days} dagen."
        if entries
        else "Nog geen predictor-contributies in de gekozen periode."
    )
    return PredictorPerformanceResponse(
        status="ok" if entries else "no_data",
        status_nl=status_nl,
        help_nl=_HELP_NL,
        lookback_days=lookback_days,
        total_contributions_considered=in_window_count,
        predictors=entries,
        best_model_code=best_model_code,
        safe_for_orders=False,
        safe_for_action_drafts=False,
    )


__all__ = [
    "PredictorPerformanceEntry",
    "PredictorPerformanceResponse",
    "router",
]
