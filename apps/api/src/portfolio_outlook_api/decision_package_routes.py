"""Task 132: Decision Package API surface (three read-only routes).

* ``GET /decision-package/{id}`` — full package by primary key.
* ``GET /decision-package/latest?conid=&account_id=`` — most recent
  package for the (account, conid) pair.
* ``GET /decision-package/chain?conid=&account_id=&limit=`` — newest-first
  chain (max 50 entries).

All routes:

* Pydantic v2 typed responses.
* Decimal-as-string on the wire (no float).
* HTTP 404 when the requested package doesn't exist.
* HTTP 503 + locked Dutch body when storage is unavailable.
* ``safe_for_action_drafts`` + ``safe_for_orders`` hard-False in every
  response — they only flip when the Action Center + approval workflows
  ship in future tasks.
"""

from __future__ import annotations

from typing import Any, Literal

from ai_trading_agent_storage import (
    DecisionPackageEntry,
    SqlAlchemyAssetFundamentalsSnapshotRepository,
    SqlAlchemyDecisionPackageRepository,
    SqlAlchemyDividendEventRepository,
    SqlAlchemyEarningsEventRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from portfolio_outlook_api.config import settings

router = APIRouter()

STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."


class GateOutcomeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_name: str
    passed: bool
    reason_nl: str


class EvidenceReferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_type: str
    claim_summary: str


class DecisionPackageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_package_id: str
    forecast_run_id: str
    composed_at: str
    valid_until: str
    ibkr_account_id: str
    conid: str
    symbol: str
    exchange: str | None
    currency_local: str
    asset_class: str | None
    user_holds_position: bool
    held_quantity: str | None
    held_avg_cost_local: str | None
    current_price_local: str
    current_price_eur: str
    as_of_market_data_ts: str
    freshness_state: Literal["fresh", "stale", "unavailable"]
    data_age_trading_days: int
    forecast_method: str
    p10_log_return: str
    p50_log_return: str
    p90_log_return: str
    p10_price_eur: str
    p50_price_eur: str
    p90_price_eur: str
    prob_positive: str
    prob_loss_gt_5pct: str
    expected_volatility_annualized: str
    forecast_confidence_level: Literal["Laag", "Gemiddeld", "Hoog"]
    suggested_action_label: Literal[
        "Kopen", "Verminderen", "Verkopen", "Houden", "Bekijken"
    ]
    block_reason: str | None
    gate_outcomes: list[GateOutcomeResponse]
    evidence_references: list[EvidenceReferenceResponse]
    deterministic_dutch_explanation: str
    audit_trail_hash: str
    previous_package_hash: str | None
    # V1.2 §BK / GAPS.md P0-5 — Decision Package §9 compliance:
    # de operator-doctrine vereist een volledig dossier. Onderstaande
    # velden worden via aparte storage lookups gepopulateerd (sector +
    # market_cap + P/E + momentum uit asset_fundamentals_snapshots;
    # earnings-datum uit earnings_events; verwachte dividenden uit
    # dividend_events). Wanneer een lookup geen rij geeft blijft het
    # veld ``None`` zodat de UI een neutrale "—" kan tonen — geen
    # verzonnen getallen (CLAUDE.md §15).
    sector: str | None = None
    market_cap_eur: str | None = None
    pe_ratio: str | None = None
    momentum_6m_pct: str | None = None
    momentum_12m_pct: str | None = None
    dividend_yield_pct: str | None = None
    next_earnings_date: str | None = None
    next_earnings_status: str | None = None
    expected_dividend_gross_local: str | None = None
    expected_dividend_currency: str | None = None
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class DecisionPackageChainResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    conid: str
    packages: list[DecisionPackageResponse]
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _enrich_with_fundamentals_earnings_dividends(
    entry: DecisionPackageEntry,
    connection: Any,
    readiness: Any,
) -> dict[str, object]:
    """V1.2 §BK / GAPS.md P0-5 — extra doctrine-§9 velden.

    Drie storage-lookups die de Decision Package response aanvullen
    met sector + market_cap + P/E + momentum (asset_fundamentals_
    snapshots), next_earnings_date (earnings_events), en verwachte
    dividenden (dividend_events). Wanneer een lookup geen rij geeft
    blijft het veld ``None`` zodat de UI een neutrale "—" toont —
    CLAUDE.md §15 verbiedt verzonnen getallen.
    """

    enrichment: dict[str, object] = {
        "sector": None,
        "market_cap_eur": None,
        "pe_ratio": None,
        "momentum_6m_pct": None,
        "momentum_12m_pct": None,
        "dividend_yield_pct": None,
        "next_earnings_date": None,
        "next_earnings_status": None,
        "expected_dividend_gross_local": None,
        "expected_dividend_currency": None,
    }

    # Fundamentals — probeer een paar gangbare EODHD-symbol-varianten
    # zodat we ook werken voor US (.US suffix) zonder dat de exchange
    # column 100% gepopulateerd hoeft te zijn.
    try:
        fundamentals_repo = SqlAlchemyAssetFundamentalsSnapshotRepository(
            connection, readiness
        )
        candidates = (
            f"{entry.symbol}.{entry.exchange}" if entry.exchange else None,
            f"{entry.symbol}.US",
            entry.symbol,
        )
        snapshot = None
        for candidate in candidates:
            if candidate is None:
                continue
            result = fundamentals_repo.get_latest_snapshot_for_symbol(candidate)
            if result.found and result.record is not None:
                snapshot = result.record
                break
        if snapshot is not None:
            enrichment["sector"] = snapshot.sector
            enrichment["market_cap_eur"] = (
                str(snapshot.market_cap) if snapshot.market_cap is not None else None
            )
            enrichment["pe_ratio"] = (
                str(snapshot.pe_ratio) if snapshot.pe_ratio is not None else None
            )
            enrichment["momentum_6m_pct"] = (
                str(snapshot.return_6m_pct)
                if snapshot.return_6m_pct is not None
                else None
            )
            enrichment["momentum_12m_pct"] = (
                str(snapshot.return_12m_pct)
                if snapshot.return_12m_pct is not None
                else None
            )
            enrichment["dividend_yield_pct"] = (
                str(snapshot.dividend_yield_pct)
                if snapshot.dividend_yield_pct is not None
                else None
            )
    except Exception:  # noqa: BLE001 — enrichment is best-effort
        pass

    # Earnings — volgende earnings-event voor dit symbool.
    try:
        from datetime import UTC, datetime

        earnings_repo = SqlAlchemyEarningsEventRepository(connection, readiness)
        next_earnings = earnings_repo.get_next_for_symbols(
            symbols=(entry.symbol,), today=datetime.now(UTC).date()
        )
        event_date = next_earnings.get(entry.symbol)
        if event_date is not None:
            enrichment["next_earnings_date"] = event_date.isoformat()
            # ``get_next_for_symbols`` filtert al op confirmed/estimated;
            # de exacte status komt uit een aparte lookup als we ooit
            # die uitsplitsen — voor §BK is "next" voldoende.
            enrichment["next_earnings_status"] = "upcoming"
    except Exception:  # noqa: BLE001
        pass

    # Dividends — laatst bekende dividend per symbol als referentie
    # voor "wat krijg je als je hold-periode een dividend bevat".
    try:
        dividend_repo = SqlAlchemyDividendEventRepository(connection, readiness)
        dividends = dividend_repo.list_for_account(
            ibkr_account_ref=entry.ibkr_account_id
        )
        for div in reversed(dividends.records):
            if div.symbol == entry.symbol:
                enrichment["expected_dividend_gross_local"] = str(div.gross_local)
                enrichment["expected_dividend_currency"] = div.currency_local
                break
    except Exception:  # noqa: BLE001
        pass

    return enrichment


def _serialize_package(entry: DecisionPackageEntry) -> dict[str, object]:
    return {
        "decision_package_id": entry.decision_package_id,
        "forecast_run_id": entry.forecast_run_id,
        "composed_at": entry.composed_at.isoformat(),
        "valid_until": entry.valid_until.isoformat(),
        "ibkr_account_id": entry.ibkr_account_id,
        "conid": entry.conid,
        "symbol": entry.symbol,
        "exchange": entry.exchange,
        "currency_local": entry.currency_local,
        "asset_class": entry.asset_class,
        "user_holds_position": entry.user_holds_position,
        "held_quantity": (
            str(entry.held_quantity) if entry.held_quantity is not None else None
        ),
        "held_avg_cost_local": (
            str(entry.held_avg_cost_local)
            if entry.held_avg_cost_local is not None
            else None
        ),
        "current_price_local": str(entry.current_price_local),
        "current_price_eur": str(entry.current_price_eur),
        "as_of_market_data_ts": entry.as_of_market_data_ts.isoformat(),
        "freshness_state": entry.freshness_state,
        "data_age_trading_days": entry.data_age_trading_days,
        "forecast_method": entry.forecast_method,
        "p10_log_return": str(entry.p10_log_return),
        "p50_log_return": str(entry.p50_log_return),
        "p90_log_return": str(entry.p90_log_return),
        "p10_price_eur": str(entry.p10_price_eur),
        "p50_price_eur": str(entry.p50_price_eur),
        "p90_price_eur": str(entry.p90_price_eur),
        "prob_positive": str(entry.prob_positive),
        "prob_loss_gt_5pct": str(entry.prob_loss_gt_5pct),
        "expected_volatility_annualized": str(
            entry.expected_volatility_annualized
        ),
        "forecast_confidence_level": entry.forecast_confidence_level,
        "suggested_action_label": entry.suggested_action_label,
        "block_reason": entry.block_reason,
        "gate_outcomes": [
            {
                "gate_name": g.gate_name,
                "passed": g.passed,
                "reason_nl": g.reason_nl,
            }
            for g in entry.gate_outcomes
        ],
        "evidence_references": [
            {
                "source_id": ev.source_id,
                "source_type": ev.source_type,
                "claim_summary": ev.claim_summary,
            }
            for ev in entry.evidence_references
        ],
        "deterministic_dutch_explanation": entry.deterministic_dutch_explanation,
        "audit_trail_hash": entry.audit_trail_hash,
        "previous_package_hash": entry.previous_package_hash,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


# NOTE: route order matters — the `/latest` and `/chain` paths must be
# registered BEFORE the `/{decision_package_id}` catch-all, otherwise
# FastAPI matches "latest" / "chain" as the path-param and returns 404.
def _configured_account_id() -> str | None:
    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return None
    text = str(hint).strip()
    return text or None


@router.get(
    "/decision-package/latest", response_model=DecisionPackageResponse
)
def read_latest_decision_package(
    conid: str = Query(..., min_length=1),
    account_id: str | None = Query(default=None),
) -> dict[str, object]:
    """Latest Decision Package for (account, conid).

    ``account_id`` is optional — when omitted the configured
    ``IBKR_ACCOUNT_ID_HINT`` is used, mirroring the
    ``/forecast/by-account`` convention. The UI never has to plumb
    the account ID through every component this way.
    """

    effective_account = account_id or _configured_account_id()
    if effective_account is None:
        raise HTTPException(
            status_code=404,
            detail="Geen Decision Package voor deze rekening/asset.",
        )

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            entry = repo.get_latest_for_account_conid(
                ibkr_account_id=effective_account, conid=conid
            )
            if entry is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Geen Decision Package voor deze rekening/asset."
                    ),
                )
            base = _serialize_package(entry)
            enrichment = _enrich_with_fundamentals_earnings_dividends(
                entry, checked.connection, checked.readiness
            )
            return {**base, **enrichment}
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.get(
    "/decision-package/chain", response_model=DecisionPackageChainResponse
)
def read_decision_package_chain(
    conid: str = Query(..., min_length=1),
    account_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict[str, object]:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    packages: list[dict[str, object]] = []
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            chain = repo.list_chain(
                ibkr_account_id=account_id, conid=conid, limit=limit
            )
            packages = [_serialize_package(entry) for entry in chain.records]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": account_id,
        "conid": conid,
        "packages": packages,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get(
    "/decision-package/{decision_package_id}",
    response_model=DecisionPackageResponse,
)
def read_decision_package(decision_package_id: str) -> dict[str, object]:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            entry = repo.get_by_id(decision_package_id)
            if entry is None:
                raise HTTPException(
                    status_code=404,
                    detail="Decision Package niet gevonden.",
                )
            base = _serialize_package(entry)
            enrichment = _enrich_with_fundamentals_earnings_dividends(
                entry, checked.connection, checked.readiness
            )
            return {**base, **enrichment}
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


__all__ = [
    "DecisionPackageChainResponse",
    "DecisionPackageResponse",
    "router",
]
