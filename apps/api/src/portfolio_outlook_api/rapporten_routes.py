"""Maandrapport API (V1.2 §AX / CLAUDE.md §13).

``GET /rapporten/maand?year=N&month=M`` — geeft de live maand-snapshot
voor de /rapporten pagina terug.

Buiten scope voor deze PR:
* Auto-PDF generatie elke 1e van de maand — V1 ship't geen PDF-
  library; opvolg-PR voegt ``weasyprint`` of ``reportlab`` toe en
  een scheduled job die de file in ``/rapporten/archief`` legt.

Read-only; storage-failures → 503.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from ai_trading_agent_storage import (
    SaveMonthlyReportArchiveRequest,
    SqlAlchemyMonthlyReportArchiveRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from ai_trading_agent_storage.metadata import (
    action_drafts,
    ibkr_executions,
    ibkr_position_snapshots,
    ibkr_sync_runs,
    orchestrator_scoring_verdicts,
)
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.monthly_report import (
    ActionDraftSnapshot,
    MonthlyReport,
    VerdictSnapshot,
    build_monthly_report,
)
from portfolio_outlook_api.pdf_export import render_monthly_report_pdf
from portfolio_outlook_api.profit_target import get_profit_target_pct
from portfolio_outlook_api.tax_report import ExecutionRow

logger = logging.getLogger(__name__)

router = APIRouter()


# ----------------------------------------------------------------------
# Response models.
# ----------------------------------------------------------------------


class ExecutiveSummaryOut(BaseModel):
    headline_nl: str
    net_local_by_currency: dict[str, str]
    vs_baseline_eur: str | None
    trade_count: int
    hit_rate_pct: float


class ActionDraftActivityOut(BaseModel):
    proposed: int
    user_approved: int
    submitted: int
    filled: int
    dismissed: int


class VerdictActivityOut(BaseModel):
    total: int
    by_decision: dict[str, int]


class IncomeBreakdownOut(BaseModel):
    capital_gains_local_by_currency: dict[str, str]
    tob_local_by_currency: dict[str, str]
    net_local_by_currency: dict[str, str]
    ytd_net_local_by_currency: dict[str, str]


class SoftwarePerformanceOut(BaseModel):
    hit_rate_pct: float
    average_hold_days: int
    confidence_distribution_pct: dict[str, float]
    proposals_vs_approved: list[int]


class RealisedTradeOut(BaseModel):
    symbol: str
    currency_local: str
    quantity: str
    buy_date: str
    sell_date: str
    gross_local: str
    net_local: str
    hold_days: int
    net_pct_on_cost: str


class MonthlyReportResponse(BaseModel):
    title_nl: str
    help_nl: str
    year: int
    month: int
    executive_summary: ExecutiveSummaryOut
    open_positions_count: int
    action_draft_activity: ActionDraftActivityOut
    verdict_activity: VerdictActivityOut
    income: IncomeBreakdownOut
    software_performance: SoftwarePerformanceOut
    realised_trades: list[RealisedTradeOut]
    notes_nl: list[str]


_HELP_NL = (
    "Maandelijks rapport — netto winst van de maand, vergelijking "
    "met de termijnrekening-baseline, action-draft-activiteit en "
    "orchestrator-output. CLAUDE.md §13 voorziet ook een auto-PDF "
    "archief; dat lands in een opvolg-PR."
)


def _current_year_month() -> tuple[int, int]:
    now = datetime.now(tz=UTC)
    return now.year, now.month


def _resolve(year: int | None, month: int | None) -> tuple[int, int]:
    y, m = _current_year_month()
    return year if year is not None else y, month if month is not None else m


def _to_response(report: MonthlyReport) -> MonthlyReportResponse:
    return MonthlyReportResponse(
        title_nl=f"Maandrapport {report.year:04d}-{report.month:02d}",
        help_nl=_HELP_NL,
        year=report.year,
        month=report.month,
        executive_summary=ExecutiveSummaryOut(
            headline_nl=report.executive_summary.headline_nl,
            net_local_by_currency=report.executive_summary.net_local_by_currency,
            vs_baseline_eur=report.executive_summary.vs_baseline_eur,
            trade_count=report.executive_summary.trade_count,
            hit_rate_pct=report.executive_summary.hit_rate_pct,
        ),
        open_positions_count=report.open_positions_count,
        action_draft_activity=ActionDraftActivityOut(
            proposed=report.action_draft_activity.proposed,
            user_approved=report.action_draft_activity.user_approved,
            submitted=report.action_draft_activity.submitted,
            filled=report.action_draft_activity.filled,
            dismissed=report.action_draft_activity.dismissed,
        ),
        verdict_activity=VerdictActivityOut(
            total=report.verdict_activity.total,
            by_decision=report.verdict_activity.by_decision,
        ),
        income=IncomeBreakdownOut(
            capital_gains_local_by_currency=(
                report.income.capital_gains_local_by_currency
            ),
            tob_local_by_currency=report.income.tob_local_by_currency,
            net_local_by_currency=report.income.net_local_by_currency,
            ytd_net_local_by_currency=report.income.ytd_net_local_by_currency,
        ),
        software_performance=SoftwarePerformanceOut(
            hit_rate_pct=report.software_performance.hit_rate_pct,
            average_hold_days=report.software_performance.average_hold_days,
            confidence_distribution_pct=(
                report.software_performance.confidence_distribution_pct
            ),
            proposals_vs_approved=list(
                report.software_performance.proposals_vs_approved
            ),
        ),
        realised_trades=[
            RealisedTradeOut(
                symbol=t.symbol,
                currency_local=t.currency_local,
                quantity=str(t.quantity),
                buy_date=t.buy_date.isoformat(),
                sell_date=t.sell_date.isoformat(),
                gross_local=str(t.gross_local),
                net_local=str(t.net_local),
                hold_days=t.hold_days,
                net_pct_on_cost=str(t.net_pct_on_cost),
            )
            for t in report.realised_trades
        ],
        notes_nl=list(report.notes_nl),
    )


def _fetch_executions(
    connection: Connection, year: int, month: int
) -> list[ExecutionRow]:
    """Fetch every fill up to and including the requested month.

    BUY-side fills uit eerdere maanden / jaren blijven nodig zodat de
    FIFO-matcher de juiste lot kan vinden voor een SELL in deze maand.
    """

    rows = (
        connection.execute(
            select(
                ibkr_executions.c.ibkr_exec_id,
                ibkr_executions.c.account_id,
                ibkr_executions.c.conid,
                ibkr_executions.c.side,
                ibkr_executions.c.fill_price_local,
                ibkr_executions.c.fill_quantity,
                ibkr_executions.c.fill_time,
                ibkr_executions.c.commission,
                ibkr_executions.c.commission_currency,
                ibkr_executions.c.action_draft_id,
            )
        )
        .mappings()
        .all()
    )
    out: list[ExecutionRow] = []
    for row in rows:
        fill_time = row["fill_time"]
        if fill_time is None:
            continue
        # Drop fills strictly after the requested month — they could
        # never close a lot in the report.
        if (fill_time.year, fill_time.month) > (year, month):
            continue
        out.append(
            ExecutionRow(
                ibkr_exec_id=str(row["ibkr_exec_id"]),
                account_id=str(row["account_id"]),
                symbol=str(row["conid"]),
                side=str(row["side"]),
                fill_price_local=Decimal(row["fill_price_local"]),
                fill_quantity=Decimal(row["fill_quantity"]),
                fill_time=fill_time,
                commission=Decimal(row["commission"]),
                commission_currency=str(row["commission_currency"]),
                action_draft_id=(
                    str(row["action_draft_id"])
                    if row["action_draft_id"] is not None
                    else None
                ),
            )
        )
    return out


def _fetch_action_drafts(connection: Connection) -> list[ActionDraftSnapshot]:
    rows = (
        connection.execute(
            select(
                action_drafts.c.action_draft_id,
                action_drafts.c.status,
                action_drafts.c.created_at,
                action_drafts.c.user_approved_at,
                action_drafts.c.submission_started_at,
                action_drafts.c.terminal_state_at,
                action_drafts.c.dismissed_at,
            )
        )
        .mappings()
        .all()
    )
    return [
        ActionDraftSnapshot(
            action_draft_id=str(row["action_draft_id"]),
            status=str(row["status"]),
            created_at=row["created_at"],
            user_approved_at=row["user_approved_at"],
            submission_started_at=row["submission_started_at"],
            terminal_state_at=row["terminal_state_at"],
            dismissed_at=row["dismissed_at"],
        )
        for row in rows
        if row["created_at"] is not None
    ]


def _fetch_verdicts(connection: Connection) -> list[VerdictSnapshot]:
    """Read every verdict; the engine filters to the requested month.

    We extract ``confidence`` out of ``details_json`` only if present;
    otherwise ``confidence_score_pct=None`` so the confidence
    distribution bucket lands in ``onbekend``.
    """

    rows = (
        connection.execute(
            select(
                orchestrator_scoring_verdicts.c.decision,
                orchestrator_scoring_verdicts.c.generated_at,
                orchestrator_scoring_verdicts.c.details_json,
            )
        )
        .mappings()
        .all()
    )
    out: list[VerdictSnapshot] = []
    for row in rows:
        details = row["details_json"] if isinstance(row["details_json"], dict) else {}
        confidence_raw = details.get("boosted_confidence_pct") or details.get(
            "confidence"
        )
        confidence: float | None = None
        if confidence_raw is not None:
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = None
        out.append(
            VerdictSnapshot(
                decision=str(row["decision"]),
                generated_at=row["generated_at"],
                confidence_score_pct=confidence,
            )
        )
    return out


def _count_open_positions(connection: Connection) -> int:
    """Count non-zero positions in the latest sync run."""

    latest_run = (
        connection.execute(
            select(ibkr_sync_runs.c.sync_run_id)
            .order_by(ibkr_sync_runs.c.started_at.desc())
            .limit(1)
        )
        .first()
    )
    if latest_run is None:
        return 0
    sync_run_id = str(latest_run[0])
    rows = (
        connection.execute(
            select(ibkr_position_snapshots.c.quantity).where(
                ibkr_position_snapshots.c.sync_run_id == sync_run_id
            )
        )
        .all()
    )
    return sum(1 for (qty,) in rows if qty is not None and Decimal(qty) != 0)


def _empty_response(year: int, month: int) -> MonthlyReportResponse:
    return _to_response(
        build_monthly_report(
            year=year, month=month,
            executions=(),
            action_drafts=(),
            verdicts=(),
            open_positions_count=0,
        )
    )


def _build_report(year: int, month: int) -> MonthlyReport:
    """Common build path used by JSON + PDF endpoints."""

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return build_monthly_report(
            year=year, month=month, executions=(),
            action_drafts=(), verdicts=(), open_positions_count=0,
        )
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            executions = _fetch_executions(checked.connection, year, month)
            drafts = _fetch_action_drafts(checked.connection)
            verdicts = _fetch_verdicts(checked.connection)
            open_count = _count_open_positions(checked.connection)
    except StorageConnectionError as exc:
        logger.warning("rapporten build storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return build_monthly_report(
        year=year, month=month, executions=executions,
        action_drafts=drafts, verdicts=verdicts,
        open_positions_count=open_count,
        profit_target_pct=get_profit_target_pct(),
    )


@router.get("/rapporten/maand", response_model=MonthlyReportResponse)
def get_maandrapport(
    year: int | None = None, month: int | None = None
) -> MonthlyReportResponse:
    resolved_year, resolved_month = _resolve(year, month)
    if resolved_year < 2000 or resolved_year > 2100:
        raise HTTPException(
            status_code=400, detail="year moet tussen 2000 en 2100 liggen"
        )
    if resolved_month < 1 or resolved_month > 12:
        raise HTTPException(
            status_code=400, detail="month moet tussen 1 en 12 liggen"
        )

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty_response(resolved_year, resolved_month)

    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            executions = _fetch_executions(
                checked.connection, resolved_year, resolved_month
            )
            drafts = _fetch_action_drafts(checked.connection)
            verdicts = _fetch_verdicts(checked.connection)
            open_count = _count_open_positions(checked.connection)
    except StorageConnectionError as exc:
        logger.warning("rapporten storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    report = build_monthly_report(
        year=resolved_year,
        month=resolved_month,
        executions=executions,
        action_drafts=drafts,
        verdicts=verdicts,
        open_positions_count=open_count,
        profit_target_pct=get_profit_target_pct(),
    )
    return _to_response(report)


@router.get("/rapporten/maand.pdf")
def get_maandrapport_pdf(
    year: int | None = None, month: int | None = None
) -> Response:
    """Render één maandrapport naar PDF (V1.2 §BC)."""

    resolved_year, resolved_month = _resolve(year, month)
    if resolved_year < 2000 or resolved_year > 2100:
        raise HTTPException(
            status_code=400, detail="year moet tussen 2000 en 2100 liggen"
        )
    if resolved_month < 1 or resolved_month > 12:
        raise HTTPException(
            status_code=400, detail="month moet tussen 1 en 12 liggen"
        )
    report = _build_report(resolved_year, resolved_month)
    pdf_bytes = render_monthly_report_pdf(report)
    filename = f"maandrapport-{resolved_year:04d}-{resolved_month:02d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---- Archief --------------------------------------------------------


class ArchiveEntryOut(BaseModel):
    archive_id: str
    year: int
    month: int
    pdf_size_bytes: int
    generated_at: str
    source: str


class ArchiveListResponse(BaseModel):
    title_nl: str
    help_nl: str
    items: list[ArchiveEntryOut]


_ARCHIVE_HELP_NL = (
    "Maandrapport-PDF-archief. Bouwt elke 1e van de maand automatisch "
    "een PDF voor de vorige maand en bewaart die hier. Operator kan "
    "ook handmatig regenereren via POST /rapporten/archief/generate."
)


def _account_ref() -> str:
    return "default"


@router.get("/rapporten/archief", response_model=ArchiveListResponse)
def list_archive() -> ArchiveListResponse:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return ArchiveListResponse(
            title_nl="Maandrapport-archief",
            help_nl=_ARCHIVE_HELP_NL,
            items=[],
        )
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyMonthlyReportArchiveRepository(
                checked.connection, checked.readiness
            )
            listed = repo.list_for_account(ibkr_account_ref=_account_ref())
    except StorageConnectionError as exc:
        logger.warning("archief list storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    items = [
        ArchiveEntryOut(
            archive_id=r.archive_id,
            year=r.year,
            month=r.month,
            pdf_size_bytes=r.pdf_size_bytes,
            generated_at=r.generated_at.isoformat(),
            source=r.source,
        )
        for r in listed.records
    ]
    return ArchiveListResponse(
        title_nl="Maandrapport-archief",
        help_nl=_ARCHIVE_HELP_NL,
        items=items,
    )


@router.get("/rapporten/archief/{year}/{month}")
def get_archive_pdf(year: int, month: int) -> Response:
    if not (1 <= month <= 12):
        raise HTTPException(
            status_code=400, detail="month moet tussen 1 en 12 liggen"
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(status_code=404, detail="Geen archief beschikbaar.")
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyMonthlyReportArchiveRepository(
                checked.connection, checked.readiness
            )
            record = repo.get(
                ibkr_account_ref=_account_ref(),
                year=year,
                month=month,
            )
    except StorageConnectionError as exc:
        logger.warning("archief get storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Geen archief voor deze maand. Roep "
            "POST /rapporten/archief/generate aan.",
        )
    filename = f"maandrapport-{year:04d}-{month:02d}.pdf"
    return Response(
        content=record.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


class GenerateArchiveRequest(BaseModel):
    year: int
    month: int


class GenerateArchiveResponse(BaseModel):
    accepted: bool
    archive_id: str
    pdf_size_bytes: int


@router.post(
    "/rapporten/archief/generate",
    response_model=GenerateArchiveResponse,
    status_code=201,
)
def generate_archive(payload: GenerateArchiveRequest) -> GenerateArchiveResponse:
    """Genereer (of regenereer) een PDF-archief voor één (year, month)."""

    if not (2000 <= payload.year <= 2100):
        raise HTTPException(
            status_code=400, detail="year moet tussen 2000 en 2100 liggen"
        )
    if not (1 <= payload.month <= 12):
        raise HTTPException(
            status_code=400, detail="month moet tussen 1 en 12 liggen"
        )
    report = _build_report(payload.year, payload.month)
    pdf_bytes = render_monthly_report_pdf(report)
    archive_id = str(uuid4())
    request = SaveMonthlyReportArchiveRequest(
        archive_id=archive_id,
        ibkr_account_ref=_account_ref(),
        year=payload.year,
        month=payload.month,
        pdf_bytes=pdf_bytes,
        pdf_size_bytes=len(pdf_bytes),
        generated_at=datetime.now(UTC),
        source="operator-manual",
    )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        )
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyMonthlyReportArchiveRepository(
                checked.connection, checked.readiness
            )
            repo.upsert(request)
            checked.connection.commit()
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("archive generate storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return GenerateArchiveResponse(
        accepted=True,
        archive_id=archive_id,
        pdf_size_bytes=len(pdf_bytes),
    )


class AutoGenerateArchiveResponse(BaseModel):
    """Antwoord op de auto-trigger — bedoeld voor de worker cron
    (V1.2 §BN / CLAUDE.md §13)."""

    accepted: bool
    year: int
    month: int
    archive_id: str | None
    pdf_size_bytes: int | None
    status_nl: str


def _previous_calendar_month(today: date) -> tuple[int, int]:
    """Return (year, month) van de vorige kalendermaand.

    Op de 1e van januari → (vorig jaar, 12). Anders → (zelfde jaar,
    huidige maand - 1).
    """

    if today.month == 1:
        return (today.year - 1, 12)
    return (today.year, today.month - 1)


@router.post(
    "/rapporten/archief/auto-generate",
    response_model=AutoGenerateArchiveResponse,
)
def auto_generate_archive() -> AutoGenerateArchiveResponse:
    """V1.2 §BN — auto-trigger voor de maand-PDF.

    CLAUDE.md §13: "elke 1e van de maand wordt een PDF gegenereerd
    en opgeslagen in /rapporten/archief". Deze endpoint wordt
    aangeroepen door de worker cron-job zonder year/month payload —
    we berekenen zelf de vorige maand, zodat de cron generic blijft.

    Idempotent: als de PDF voor (vorige maand) al bestaat wordt
    hij overschreven (consistent met de operator-handmatige
    generate_archive die ook upsert).
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return AutoGenerateArchiveResponse(
            accepted=False,
            year=0,
            month=0,
            archive_id=None,
            pdf_size_bytes=None,
            status_nl="Opslag uitgeschakeld; auto-archief overgeslagen.",
        )

    today = datetime.now(UTC).date()
    target_year, target_month = _previous_calendar_month(today)
    report = _build_report(target_year, target_month)
    pdf_bytes = render_monthly_report_pdf(report)
    archive_id = str(uuid4())
    request = SaveMonthlyReportArchiveRequest(
        archive_id=archive_id,
        ibkr_account_ref=_account_ref(),
        year=target_year,
        month=target_month,
        pdf_bytes=pdf_bytes,
        pdf_size_bytes=len(pdf_bytes),
        generated_at=datetime.now(UTC),
        source="auto-cron",
    )
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyMonthlyReportArchiveRepository(
                checked.connection, checked.readiness
            )
            repo.upsert(request)
            checked.connection.commit()
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("archive auto-generate storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return AutoGenerateArchiveResponse(
        accepted=True,
        year=target_year,
        month=target_month,
        archive_id=archive_id,
        pdf_size_bytes=len(pdf_bytes),
        status_nl=(
            f"PDF voor {target_month:02d}/{target_year} opgeslagen "
            f"({len(pdf_bytes)} bytes)."
        ),
    )


__all__ = ["router"]
