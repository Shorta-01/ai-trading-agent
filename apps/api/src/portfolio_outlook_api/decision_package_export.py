"""Render the latest Decision Packages as a downloadable Markdown document.

The export bundles every current buy/sell suggestion together with the full
"why" (rationale + AI explanation), the supporting forecast numbers, and the
content hash / audit links that make each suggestion traceable. Pure
functions only — no I/O — so the format is deterministic and unit-testable.
The records passed in are the same dicts returned by
``serialize_decision_package_for_response`` (the ``/decision-packages/latest``
JSON shape).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime


def export_filename(generated_at: datetime) -> str:
    """Attachment filename for a download generated at ``generated_at``."""

    return f"suggesties-export-{generated_at:%Y%m%d-%H%M%S}.md"


def _txt(value: object) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text else "—"


def _yes_no(value: object) -> str:
    return "Ja" if value else "Nee"


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _bullets(value: object) -> str:
    items = _as_str_list(value)
    if not items:
        return "_Geen._"
    return "\n".join(f"- {item}" for item in items)


def _block(value: object) -> str:
    """A free-text block — preserved verbatim, or an em dash when empty."""

    if value is None:
        return "—"
    text = str(value).strip()
    return text if text else "—"


def render_decision_packages_markdown(
    packages: Sequence[dict[str, object]],
    *,
    generated_at: datetime,
    risk_profile: str | None,
    status_nl: str | None = None,
) -> str:
    """Render the latest Decision Packages as a single Markdown document.

    ``status_nl`` carries a terminal-state label (e.g. "Geen posities") so an
    empty export is still a valid, self-explanatory ``.md`` file rather than
    an error page.
    """

    lines: list[str] = []
    lines.append("# Portfolio Outlook — Suggesties")
    lines.append("")
    lines.append(f"- **Gegenereerd op:** {generated_at.isoformat()}")
    lines.append(f"- **Risicoprofiel:** {_txt(risk_profile)}")
    lines.append(f"- **Aantal suggesties:** {len(packages)}")
    lines.append("")
    lines.append(
        "> Informatief overzicht van de actuele systeemsuggesties. "
        "Geen beleggingsadvies. Er worden geen orders verzonden op basis "
        "van dit document."
    )
    lines.append("")

    if not packages:
        lines.append("---")
        lines.append("")
        lines.append("## Geen suggesties beschikbaar")
        lines.append("")
        lines.append(_txt(status_nl) if status_nl else "Er zijn momenteel geen Decision Packages.")
        lines.append("")
        return "\n".join(lines)

    for index, pkg in enumerate(packages, start=1):
        symbol = _txt(pkg.get("symbol"))
        action_nl = _txt(pkg.get("suggestion_action_label_nl"))
        action_code = _txt(pkg.get("suggestion_action_label"))
        confidence_nl = _txt(pkg.get("suggestion_confidence_label_nl"))

        lines.append("---")
        lines.append("")
        lines.append(f"## {index}. {symbol} — {action_nl}")
        lines.append("")
        lines.append(f"- **Actie:** {action_nl} (`{action_code}`)")
        lines.append(f"- **Vertrouwen:** {confidence_nl}")
        lines.append(f"- **Munt:** {_txt(pkg.get('currency'))}")
        lines.append(f"- **Heeft positie:** {_yes_no(pkg.get('has_position'))}")
        lines.append(f"- **Gegenereerd op:** {_txt(pkg.get('generated_at'))}")
        lines.append(f"- **Geldig tot:** {_txt(pkg.get('valid_until'))}")
        lines.append("")

        lines.append("### Forecast")
        lines.append("")
        lines.append("| Metriek | Waarde |")
        lines.append("| --- | --- |")
        lines.append(f"| Horizon (dagen) | {_txt(pkg.get('forecast_horizon_days'))} |")
        lines.append(
            "| Prijs P10 / P50 / P90 | "
            f"{_txt(pkg.get('forecast_p10_price'))} / "
            f"{_txt(pkg.get('forecast_p50_price'))} / "
            f"{_txt(pkg.get('forecast_p90_price'))} |"
        )
        lines.append(f"| Kans op winst | {_txt(pkg.get('forecast_prob_gain'))} |")
        lines.append(f"| Kans op verlies | {_txt(pkg.get('forecast_prob_loss'))} |")
        lines.append(
            f"| Verwacht rendement | {_txt(pkg.get('forecast_expected_return_pct'))} |"
        )
        lines.append(
            "| Verwachte volatiliteit (jaar) | "
            f"{_txt(pkg.get('forecast_expected_volatility_annual'))} |"
        )
        lines.append(
            f"| Neerwaarts risico | {_txt(pkg.get('forecast_downside_risk_score'))} |"
        )
        lines.append(
            f"| Vertrouwensscore | {_txt(pkg.get('forecast_confidence_score'))} |"
        )
        lines.append(f"| Laatste marktprijs | {_txt(pkg.get('market_last_price'))} |")
        lines.append("")

        lines.append("### Waarom deze suggestie?")
        lines.append("")
        lines.append(_block(pkg.get("rationale_nl")))
        lines.append("")

        lines.append("### Volledige uitleg")
        lines.append("")
        lines.append(_block(pkg.get("explanation_nl")))
        lines.append("")

        lines.append("### Onderzoek")
        lines.append("")
        lines.append(
            f"- **Aantal bronnen:** {_txt(pkg.get('research_evidence_count'))}"
        )
        lines.append(
            f"- **Geloofwaardigheid:** {_txt(pkg.get('research_credibility_summary'))}"
        )
        lines.append(f"- **Versheid:** {_txt(pkg.get('research_freshness_status'))}")
        snippet = pkg.get("research_snippet_nl")
        if snippet is not None and str(snippet).strip():
            lines.append("")
            lines.append(f"> {str(snippet).strip()}")
        lines.append("")

        lines.append("### Gate-uitkomsten")
        lines.append("")
        lines.append(_bullets(pkg.get("gate_outcomes")))
        lines.append("")

        lines.append("### Herkomst & traceerbaarheid")
        lines.append("")
        lines.append(
            f"- **Decision Package ID:** `{_txt(pkg.get('decision_package_id'))}`"
        )
        lines.append(f"- **Content hash:** `{_txt(pkg.get('content_hash'))}`")
        lines.append(f"- **Suggestion ID:** `{_txt(pkg.get('suggestion_id'))}`")
        lines.append(
            "- **Forecast-model:** "
            f"{_txt(pkg.get('forecast_model_code'))} "
            f"{_txt(pkg.get('forecast_model_version'))}"
        )
        lines.append("- **Audit links:**")
        audit_items = _as_str_list(pkg.get("audit_links"))
        if audit_items:
            for item in audit_items:
                lines.append(f"  - {item}")
        else:
            lines.append("  - _Geen._")
        lines.append("")

    return "\n".join(lines)
