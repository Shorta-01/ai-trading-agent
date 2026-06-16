"""Dividenden API (V1.2 §BA / CLAUDE.md §12 follow-up).

V1 heeft geen broker-dividend-feed. Tot die er is, logt de operator
dividenden manueel. Endpoints:

* ``GET /dividenden?year=N`` — lijst van dividenden voor een jaar
  (default: huidige jaar) + KPIs (totaal bruto, totaal bronbelasting,
  totaal netto) per valuta.
* ``POST /dividenden`` — voegt een dividend toe.
* ``DELETE /dividenden/{dividend_event_id}`` — verwijdert.

Verdrag-tarieven worden als default voorgesteld (US 15 %, NL 15 %,
FR 12,8 %, BE 0 %) maar operator kan overschrijven.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from ai_trading_agent_storage import (
    WITHHOLDING_DEFAULTS_BY_COUNTRY,
    SaveDividendEventRequest,
    SqlAlchemyDividendEventRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_CENT = Decimal("0.01")


class DividendOut(BaseModel):
    dividend_event_id: str
    symbol: str
    isin: str | None
    pay_date: str
    currency_local: str
    gross_local: str
    withholding_pct: str
    withholding_local: str
    net_local: str
    country_code: str | None
    note: str | None
    # V1.2 audit-correctie 2026-06-16: Belgische 30% RV regularisatie
    # auto-berekend per CLAUDE.md §12. Belgische bewoner is netto
    # 30% RV verschuldigd; ingehouden bronbelasting telt mee, dus
    # tekort = ``max(30 - withholding_pct, 0)``. ``rv_shortfall_local``
    # is ``gross_local * shortfall_pct / 100`` zodat de accountant
    # direct ziet hoeveel extra in de aangifte moet worden opgenomen.
    rv_shortfall_pct: str = "0"
    rv_shortfall_local: str = "0"


class DividendKpisOut(BaseModel):
    gross_by_currency: dict[str, str]
    withholding_by_currency: dict[str, str]
    net_by_currency: dict[str, str]
    count: int


class DividendListResponse(BaseModel):
    title_nl: str
    help_nl: str
    year: int
    items: list[DividendOut]
    totals: DividendKpisOut
    treaty_defaults_pct_by_country: dict[str, str]


class CreateDividendRequest(BaseModel):
    symbol: str
    pay_date: str
    currency_local: str
    gross_local: str
    withholding_pct: str | None = None
    country_code: str | None = None
    isin: str | None = None
    note: str | None = None


class DividendMutationResponse(BaseModel):
    accepted: bool
    record_id: str | None
    explanation_nl: str


_HELP_NL = (
    "Operator-getrackt dividenden-register. V1 heeft geen "
    "broker-feed; je voert ze hier handmatig in en de /belasting "
    "pagina rolt ze door naar het jaaroverzicht. Belgische 30 % "
    "roerende voorheffing wordt op rapportniveau berekend; hier "
    "voer je enkel de bronbelasting van het bron-land in."
)


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        )
    assert storage.database_url is not None
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _account_ref() -> str:
    return "default"


def _parse_decimal(raw: str, *, field: str) -> Decimal:
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{field} moet een decimaal getal zijn.",
        ) from exc


def _parse_date(raw: str, *, field: str) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"{field} moet YYYY-MM-DD zijn."
        ) from exc


# V1.2 audit-correctie 2026-06-16: Belgische roerende voorheffing
# is 30%. Bronbelasting ingehouden door buitenlands rechtsgebied
# telt mee; het tekort = ``max(30 - withholding_pct, 0)`` moet de
# operator nog declareren in zijn aangifte (RV-aanvulling).
_BELGIAN_RV_RATE_PCT: Decimal = Decimal("30")


def _compute_rv_shortfall(
    *,
    gross_local: Decimal,
    withholding_pct: Decimal,
) -> tuple[Decimal, Decimal]:
    """Returnt (shortfall_pct, shortfall_local) per CLAUDE.md §12.

    Voorbeeld: US dividend $100 met 15% bronbelasting →
    shortfall_pct = 15%, shortfall_local = $15. Operator moet die
    $15 extra in aangifte opnemen om de Belgische 30% RV te halen.

    Wanneer bronbelasting al ≥ 30% is (theoretische edge case) is
    er geen tekort en wordt 0 geretourneerd.
    """

    shortfall_pct = max(_BELGIAN_RV_RATE_PCT - withholding_pct, Decimal(0))
    shortfall_local = (gross_local * shortfall_pct / Decimal(100)).quantize(
        Decimal("0.01")
    )
    return shortfall_pct, shortfall_local


def _default_withholding(country_code: str | None) -> Decimal:
    if country_code is None:
        return Decimal(0)
    return WITHHOLDING_DEFAULTS_BY_COUNTRY.get(
        country_code.upper(), Decimal(0)
    )


def _kpis(records) -> DividendKpisOut:  # type: ignore[no-untyped-def]
    gross: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    wh: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    net: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for r in records:
        gross[r.currency_local] += r.gross_local
        wh[r.currency_local] += r.withholding_local
        net[r.currency_local] += r.net_local
    return DividendKpisOut(
        gross_by_currency={
            ccy: f"{value.quantize(_CENT)}" for ccy, value in gross.items()
        },
        withholding_by_currency={
            ccy: f"{value.quantize(_CENT)}" for ccy, value in wh.items()
        },
        net_by_currency={
            ccy: f"{value.quantize(_CENT)}" for ccy, value in net.items()
        },
        count=len(records),
    )


def _empty_response(year: int) -> DividendListResponse:
    return DividendListResponse(
        title_nl=f"Dividenden {year}",
        help_nl=_HELP_NL,
        year=year,
        items=[],
        totals=DividendKpisOut(
            gross_by_currency={},
            withholding_by_currency={},
            net_by_currency={},
            count=0,
        ),
        treaty_defaults_pct_by_country={
            ccy: str(pct) for ccy, pct in WITHHOLDING_DEFAULTS_BY_COUNTRY.items()
        },
    )


@router.get("/dividenden", response_model=DividendListResponse)
def list_dividenden(
    year: int = Query(None, description="Default: huidige jaar."),
) -> DividendListResponse:
    resolved = year if year is not None else datetime.now(UTC).year
    if resolved < 2000 or resolved > 2100:
        raise HTTPException(
            status_code=400, detail="year moet tussen 2000 en 2100 liggen"
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty_response(resolved)
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyDividendEventRepository(
                checked.connection, checked.readiness
            )
            listed = repo.list_for_account(
                ibkr_account_ref=_account_ref(), year=resolved
            )
    except StorageConnectionError as exc:
        logger.warning("dividenden list storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    items = []
    for r in listed.records:
        rv_shortfall_pct, rv_shortfall_local = _compute_rv_shortfall(
            gross_local=r.gross_local,
            withholding_pct=r.withholding_pct,
        )
        items.append(
            DividendOut(
                dividend_event_id=r.dividend_event_id,
                symbol=r.symbol,
                isin=r.isin,
                pay_date=r.pay_date.isoformat(),
                currency_local=r.currency_local,
                gross_local=str(r.gross_local),
                withholding_pct=str(r.withholding_pct),
                withholding_local=str(r.withholding_local),
                net_local=str(r.net_local),
                country_code=r.country_code,
                note=r.note,
                rv_shortfall_pct=str(rv_shortfall_pct),
                rv_shortfall_local=str(rv_shortfall_local),
            )
        )
    return DividendListResponse(
        title_nl=f"Dividenden {resolved}",
        help_nl=_HELP_NL,
        year=resolved,
        items=items,
        totals=_kpis(listed.records),
        treaty_defaults_pct_by_country={
            ccy: str(pct) for ccy, pct in WITHHOLDING_DEFAULTS_BY_COUNTRY.items()
        },
    )


@router.post(
    "/dividenden",
    response_model=DividendMutationResponse,
    status_code=201,
)
def create_dividend(payload: CreateDividendRequest) -> DividendMutationResponse:
    if not payload.symbol.strip():
        raise HTTPException(status_code=400, detail="symbol mag niet leeg zijn.")
    if not payload.currency_local.strip():
        raise HTTPException(
            status_code=400, detail="currency_local mag niet leeg zijn."
        )
    pay_date = _parse_date(payload.pay_date, field="pay_date")
    gross = _parse_decimal(payload.gross_local, field="gross_local")
    if gross < 0:
        raise HTTPException(
            status_code=400, detail="gross_local moet >= 0 zijn."
        )
    if payload.withholding_pct is not None:
        pct = _parse_decimal(payload.withholding_pct, field="withholding_pct")
    else:
        pct = _default_withholding(payload.country_code)
    if not (Decimal(0) <= pct <= Decimal(100)):
        raise HTTPException(
            status_code=400,
            detail="withholding_pct moet tussen 0 en 100 liggen.",
        )
    withholding = (gross * pct / Decimal(100)).quantize(_CENT)
    net = (gross - withholding).quantize(_CENT)

    request = SaveDividendEventRequest(
        dividend_event_id=str(uuid4()),
        ibkr_account_ref=_account_ref(),
        symbol=payload.symbol.strip().upper(),
        isin=payload.isin,
        pay_date=pay_date,
        currency_local=payload.currency_local.strip().upper(),
        gross_local=gross,
        withholding_pct=pct,
        withholding_local=withholding,
        net_local=net,
        country_code=(
            payload.country_code.upper() if payload.country_code else None
        ),
        note=payload.note,
        created_at=datetime.now(UTC),
    )

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyDividendEventRepository(
                checked.connection, checked.readiness
            )
            result = repo.save_dividend(request)
            checked.connection.commit()
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("dividend create storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return DividendMutationResponse(
        accepted=result.accepted,
        record_id=result.record_id,
        explanation_nl=result.explanation_nl,
    )


@router.delete(
    "/dividenden/{dividend_event_id}",
    response_model=DividendMutationResponse,
)
def delete_dividend(dividend_event_id: str) -> DividendMutationResponse:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyDividendEventRepository(
                checked.connection, checked.readiness
            )
            result = repo.delete_dividend(dividend_event_id=dividend_event_id)
            checked.connection.commit()
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("dividend delete storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return DividendMutationResponse(
        accepted=result.accepted,
        record_id=result.record_id,
        explanation_nl=result.explanation_nl,
    )


__all__ = ["router"]
