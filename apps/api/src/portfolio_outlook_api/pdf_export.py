"""PDF-rendering voor /belasting en /rapporten (V1.2 §BC).

Gebruikt ``reportlab`` (pure-Python). Twee public functies:

* ``render_tax_year_report_pdf(report)`` → bytes
* ``render_monthly_report_pdf(report)`` → bytes

De layout blijft sober — tabellen + headers — zodat de accountant
het document gewoon kan printen of bijvoegen.
"""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _make_table(rows: list[list[str]]) -> Table:
    """Maak een gestileerde tabel — header in donkergrijs, body zebra."""

    table = Table(rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
            ]
        )
    )
    return table


def render_tax_year_report_pdf(report: Any) -> bytes:
    """Render een tax-year report naar een PDF-bytes blob."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Belastingoverzicht {report.year}",
    )
    styles = getSampleStyleSheet()
    flow: list[Any] = []

    flow.append(Paragraph(f"Belastingoverzicht {report.year}", styles["Title"]))
    flow.append(Spacer(1, 6 * mm))
    flow.append(
        Paragraph(
            "FIFO-gematchte gerealiseerde kapitaalwinsten met "
            "Belgische TOB op beide kanten. Doctrine §6.1 winstdoel "
            "wordt gebruikt voor hit-rate-berekening.",
            styles["BodyText"],
        )
    )
    flow.append(Spacer(1, 4 * mm))

    # Year totals.
    yt = report.year_totals
    totals_rows = [
        ["Metric", "Waarde"],
        ["Aantal trades", str(yt.trade_count)],
        ["Bruto (lokaal)", ", ".join(
            f"{v} {ccy}" for ccy, v in yt.gross_local_by_currency.items()
        ) or "—"],
        ["TOB (lokaal)", ", ".join(
            f"{v} {ccy}" for ccy, v in yt.tob_local_by_currency.items()
        ) or "—"],
        ["Netto (lokaal)", ", ".join(
            f"{v} {ccy}" for ccy, v in yt.net_local_by_currency.items()
        ) or "—"],
        ["Gem. hold (dagen)", str(yt.average_hold_days)],
        ["Hit-rate", f"{yt.hit_rate_pct} %"],
    ]
    if yt.net_eur_total:
        totals_rows.append(
            ["Netto EUR (FX-conversie)", f"{yt.net_eur_total} EUR"]
        )
        totals_rows.append(
            ["FX-conversie dekking", f"{yt.eur_conversion_coverage_pct} %"]
        )
    flow.append(_make_table(totals_rows))
    flow.append(Spacer(1, 6 * mm))

    # Good householder.
    flow.append(Paragraph("\"Goed huisvader\"-bewijs", styles["Heading2"]))
    flow.append(Paragraph(report.good_householder.summary_nl, styles["BodyText"]))
    flow.append(Spacer(1, 6 * mm))

    # Realised trades.
    flow.append(Paragraph("Gerealiseerde trades", styles["Heading2"]))
    if report.realised_trades:
        trade_rows: list[list[str]] = [[
            "Symbool", "Aantal", "Aankoop", "Verkoop",
            "Bruto", "TOB", "Netto", "Hold", "%",
        ]]
        for t in report.realised_trades:
            trade_rows.append(
                [
                    t.symbol,
                    str(t.quantity),
                    f"{t.buy_date} @ {t.buy_price_local}",
                    f"{t.sell_date} @ {t.sell_price_local}",
                    f"{t.gross_local} {t.currency_local}",
                    f"{t.tob_buy_local + t.tob_sell_local} {t.currency_local}",
                    f"{t.net_local} {t.currency_local}",
                    str(t.hold_days),
                    f"{t.net_pct_on_cost} %",
                ]
            )
        flow.append(_make_table(trade_rows))
    else:
        flow.append(Paragraph("Geen gerealiseerde trades dit jaar.", styles["BodyText"]))
    flow.append(Spacer(1, 6 * mm))

    # Dividends section.
    flow.append(Paragraph("Ontvangen dividenden", styles["Heading2"]))
    if report.dividends:
        div_rows: list[list[str]] = [[
            "Symbool", "Land", "Datum", "Valuta", "Bruto", "BB %", "Netto",
        ]]
        for d in report.dividends:
            div_rows.append(
                [
                    str(d.get("symbol", "—")),
                    str(d.get("country_code") or "—"),
                    str(d.get("pay_date", "—")),
                    str(d.get("currency_local", "—")),
                    str(d.get("gross_local", "—")),
                    f"{d.get('withholding_pct', '—')} %",
                    str(d.get("net_local", "—")),
                ]
            )
        flow.append(_make_table(div_rows))
    else:
        flow.append(
            Paragraph(
                "Geen dividenden geregistreerd dit jaar.",
                styles["BodyText"],
            )
        )

    # Notes.
    if report.notes_nl:
        flow.append(Spacer(1, 6 * mm))
        flow.append(Paragraph("Opmerkingen", styles["Heading3"]))
        for note in report.notes_nl:
            flow.append(Paragraph(f"• {note}", styles["BodyText"]))

    doc.build(flow)
    return buffer.getvalue()


def render_monthly_report_pdf(report: Any) -> bytes:
    """Render één maandrapport naar PDF-bytes."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Maandrapport {report.year:04d}-{report.month:02d}",
    )
    styles = getSampleStyleSheet()
    flow: list[Any] = []
    flow.append(
        Paragraph(
            f"Maandrapport {report.year:04d}-{report.month:02d}",
            styles["Title"],
        )
    )
    flow.append(Spacer(1, 6 * mm))
    flow.append(
        Paragraph(report.executive_summary.headline_nl, styles["BodyText"])
    )
    if report.executive_summary.vs_baseline_eur:
        flow.append(
            Paragraph(
                report.executive_summary.vs_baseline_eur, styles["BodyText"]
            )
        )
    flow.append(Spacer(1, 4 * mm))

    # Activity counts.
    a = report.action_draft_activity
    activity_rows = [
        ["Activiteit", "Aantal"],
        ["Voorgestelde drafts", str(a.proposed)],
        ["Goedgekeurd", str(a.user_approved)],
        ["Verzonden", str(a.submitted)],
        ["Filled", str(a.filled)],
        ["Afgewezen", str(a.dismissed)],
        ["Open posities", str(report.open_positions_count)],
    ]
    flow.append(_make_table(activity_rows))
    flow.append(Spacer(1, 4 * mm))

    # Income.
    income = report.income
    income_rows = [
        ["Income", "Waarde"],
        ["Capital gains (bruto)", ", ".join(
            f"{v} {ccy}" for ccy, v in income.capital_gains_local_by_currency.items()
        ) or "—"],
        ["TOB", ", ".join(
            f"{v} {ccy}" for ccy, v in income.tob_local_by_currency.items()
        ) or "—"],
        ["Netto deze maand", ", ".join(
            f"{v} {ccy}" for ccy, v in income.net_local_by_currency.items()
        ) or "—"],
        ["YTD cumulatief", ", ".join(
            f"{v} {ccy}" for ccy, v in income.ytd_net_local_by_currency.items()
        ) or "—"],
    ]
    flow.append(_make_table(income_rows))
    flow.append(Spacer(1, 4 * mm))

    # Performance.
    perf = report.software_performance
    perf_rows = [
        ["Software-prestatie", "Waarde"],
        ["Hit-rate", f"{perf.hit_rate_pct} %"],
        ["Gem. hold (dagen)", str(perf.average_hold_days)],
        ["Voorstellen → goedgekeurd",
         f"{perf.proposals_vs_approved[0]} → {perf.proposals_vs_approved[1]}"],
    ]
    flow.append(_make_table(perf_rows))

    # Trades.
    if report.realised_trades:
        flow.append(Spacer(1, 4 * mm))
        flow.append(Paragraph("Gesloten trades deze maand", styles["Heading3"]))
        trade_rows: list[list[str]] = [
            ["Symbool", "Aantal", "Buy date", "Sell date", "Netto", "Hold"]
        ]
        for t in report.realised_trades:
            trade_rows.append(
                [
                    t.symbol,
                    str(t.quantity),
                    t.buy_date.isoformat(),
                    t.sell_date.isoformat(),
                    f"{t.net_local} {t.currency_local}",
                    str(t.hold_days),
                ]
            )
        flow.append(_make_table(trade_rows))

    # Notes.
    if report.notes_nl:
        flow.append(Spacer(1, 4 * mm))
        flow.append(Paragraph("Opmerkingen", styles["Heading3"]))
        for note in report.notes_nl:
            flow.append(Paragraph(f"• {note}", styles["BodyText"]))

    doc.build(flow)
    return buffer.getvalue()


__all__ = ["render_tax_year_report_pdf", "render_monthly_report_pdf"]
