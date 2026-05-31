"""Compute one end-of-day digest from the existing persisted state.

The worker's ``market_close`` fire calls :func:`compute_daily_digest`
after the market-data runner has refreshed prices. The compute
function is a pure transform over what storage already has — no new
fetches, no IBKR calls — so it can run inside the same DB transaction
the orchestrator uses.

The returned :class:`DailyDigestRecord` is upserted by the orchestrator
via :class:`SqlAlchemyDailyDigestRepository`. The API surfaces it
through ``GET /digests/today`` for the dashboard.

Doctrine: this module never writes; the orchestrator owns persistence.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

# A small data-shape protocol surface to keep the compute function
# testable without dragging the full ``ai_trading_agent_storage``
# imports into the worker domain layer. The orchestrator passes typed
# records in; this module only reads the documented attributes below.


def _safe_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001 — boundary
        return None


def _percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return (numerator / denominator) * Decimal("100")


def _topn_by_pnl_pct(
    positions: Sequence[Any], *, n: int = 5, reverse: bool
) -> list[dict[str, object]]:
    """Sort positions by ``pnl_pct`` ascending (losers) or descending
    (winners). Positions with no PnL are dropped silently."""

    scored: list[tuple[Decimal, Any]] = []
    for position in positions:
        pnl_pct = _safe_decimal(getattr(position, "pnl_pct", None))
        if pnl_pct is None:
            continue
        scored.append((pnl_pct, position))
    scored.sort(key=lambda pair: pair[0], reverse=reverse)
    out: list[dict[str, object]] = []
    for pnl_pct, position in scored[:n]:
        out.append(
            {
                "symbol": str(getattr(position, "symbol", "?")),
                "pnl_pct": str(pnl_pct.quantize(Decimal("0.01"))),
                "pnl_abs": (
                    str(_safe_decimal(getattr(position, "pnl_abs", None)) or Decimal("0"))
                ),
                "currency": str(getattr(position, "currency", "USD")),
            }
        )
    return out


def _nav_summary(
    *, today_nav: Decimal | None, prev_nav: Decimal | None, currency: str
) -> dict[str, object]:
    if today_nav is None or prev_nav is None:
        return {
            "total_nav": str(today_nav) if today_nav is not None else None,
            "prev_nav": str(prev_nav) if prev_nav is not None else None,
            "delta_abs": None,
            "delta_pct": None,
            "currency": currency,
            "computed_from": "missing_snapshot",
        }
    delta_abs = today_nav - prev_nav
    delta_pct = _percent(delta_abs, prev_nav)
    return {
        "total_nav": str(today_nav),
        "prev_nav": str(prev_nav),
        "delta_abs": str(delta_abs.quantize(Decimal("0.01"))),
        "delta_pct": str(delta_pct.quantize(Decimal("0.01"))),
        "currency": currency,
        "computed_from": "nav_snapshots",
    }


def _positions_summary(positions: Sequence[Any]) -> dict[str, object]:
    by_currency: Counter[str] = Counter()
    for position in positions:
        by_currency[str(getattr(position, "currency", "USD"))] += 1
    return {
        "position_count": len(positions),
        "by_currency": dict(by_currency),
        "top_winners": _topn_by_pnl_pct(positions, reverse=True),
        "top_losers": _topn_by_pnl_pct(positions, reverse=False),
    }


def _suggestions_summary(
    suggestions: Sequence[Any],
) -> dict[str, object]:
    if not suggestions:
        return {
            "total": 0,
            "by_action_label": {},
            "new_today": 0,
            "high_confidence_count": 0,
        }
    by_label: Counter[str] = Counter()
    high_conf = 0
    for suggestion in suggestions:
        by_label[str(getattr(suggestion, "action_label_nl", "Onbekend"))] += 1
        if str(getattr(suggestion, "confidence_label", "")).lower() in {
            "high",
            "hoog",
        }:
            high_conf += 1
    return {
        "total": len(suggestions),
        "by_action_label": dict(by_label),
        "new_today": len(suggestions),
        "high_confidence_count": high_conf,
    }


def _action_drafts_summary(
    drafts: Sequence[Any],
) -> dict[str, object]:
    by_state: Counter[str] = Counter()
    created_today = 0
    approved_today = 0
    submitted_today = 0
    cancelled_today = 0
    for draft in drafts:
        state = str(getattr(draft, "state", "unknown")).lower()
        by_state[state] += 1
        if state == "draft":
            created_today += 1
        elif state == "approved":
            approved_today += 1
        elif state in {"submitted_to_broker", "live_at_broker", "filled"}:
            submitted_today += 1
        elif state in {"cancelled", "rejected"}:
            cancelled_today += 1
    return {
        "created_today": created_today,
        "approved_today": approved_today,
        "submitted_today": submitted_today,
        "cancelled_today": cancelled_today,
        "by_state": dict(by_state),
    }


def _alerts(
    *,
    nav_summary: dict[str, object],
    positions_summary: dict[str, object],
    suggestions_summary: dict[str, object],
) -> list[dict[str, object]]:
    """Build the operator-facing alert list from the digest aggregates.

    Three deterministic triggers for v1; more can be added later
    without changing the schema. Each alert is a Dutch one-liner the
    UI can render as a callout.
    """

    alerts: list[dict[str, object]] = []

    delta_pct_raw = nav_summary.get("delta_pct")
    if delta_pct_raw is not None:
        delta_pct = _safe_decimal(delta_pct_raw)
        if delta_pct is not None and delta_pct <= Decimal("-2.0"):
            alerts.append(
                {
                    "kind": "nav_drop",
                    "severity_nl": "Waarschuwing",
                    "title_nl": (
                        f"Portfolio-NAV is vandaag {delta_pct:.2f}% gedaald"
                    ),
                    "body_nl": (
                        "Bekijk de top-losers in deze digest om te zien "
                        "welke posities het meest bijdroegen."
                    ),
                    "reference_kind": "nav",
                    "reference_id": None,
                }
            )

    raw_high_conf = suggestions_summary.get("high_confidence_count", 0) or 0
    high_conf = int(raw_high_conf) if isinstance(raw_high_conf, (int, str)) else 0
    if high_conf > 0:
        raw_by_label = suggestions_summary.get("by_action_label", {}) or {}
        by_label_counts: dict[str, int] = (
            raw_by_label if isinstance(raw_by_label, dict) else {}
        )
        sell_count = int(by_label_counts.get("Verkopen", 0) or 0) + int(
            by_label_counts.get("Verminderen", 0) or 0
        )
        if sell_count > 0:
            alerts.append(
                {
                    "kind": "high_confidence_sell",
                    "severity_nl": "Belangrijk",
                    "title_nl": (
                        f"{sell_count} hoge-zekerheid verkoop-suggestie(s) "
                        "vandaag"
                    ),
                    "body_nl": (
                        "Open /suggesties om de Decision Packages te "
                        "reviewen voordat de markt morgen opent."
                    ),
                    "reference_kind": "suggestion",
                    "reference_id": None,
                }
            )

    top_losers = positions_summary.get("top_losers", []) or []
    if isinstance(top_losers, list) and top_losers:
        first_loser = top_losers[0]
        if isinstance(first_loser, dict):
            pnl_pct = _safe_decimal(first_loser.get("pnl_pct"))
            if pnl_pct is not None and pnl_pct <= Decimal("-5.0"):
                alerts.append(
                    {
                        "kind": "position_drop",
                        "severity_nl": "Waarschuwing",
                        "title_nl": (
                            f"{first_loser.get('symbol', '?')} viel "
                            f"vandaag {pnl_pct:.2f}%"
                        ),
                        "body_nl": (
                            "Controleer of de positie nog binnen je "
                            "risico-profiel valt."
                        ),
                        "reference_kind": "position",
                        "reference_id": str(first_loser.get("symbol", "?")),
                    }
                )

    return alerts


def compute_daily_digest_payload(
    *,
    ibkr_account_ref: str,
    market_code: str,
    briefing_date: date,
    generated_at: datetime,
    today_nav: Decimal | None,
    prev_nav: Decimal | None,
    base_currency: str,
    positions: Iterable[Any],
    suggestions: Iterable[Any],
    action_drafts: Iterable[Any],
) -> dict[str, Any]:
    """Pure compute: take the day's persisted state in, return a fully
    populated dict ready for ``DailyDigestRecord(**payload)``.

    Keeping persistence out of this function makes it easy to test
    (no DB) and easy to call from a hypothetical "preview the digest
    before saving" endpoint later.
    """

    positions_list = list(positions)
    suggestions_list = list(suggestions)
    drafts_list = list(action_drafts)

    nav_summary = _nav_summary(
        today_nav=today_nav, prev_nav=prev_nav, currency=base_currency
    )
    positions_summary = _positions_summary(positions_list)
    suggestions_summary = _suggestions_summary(suggestions_list)
    drafts_summary = _action_drafts_summary(drafts_list)
    alerts = _alerts(
        nav_summary=nav_summary,
        positions_summary=positions_summary,
        suggestions_summary=suggestions_summary,
    )

    status = "ready"
    blocking_reason: str | None = None
    if today_nav is None or prev_nav is None:
        status = "partial"
        blocking_reason = "missing_nav_snapshot"

    return {
        "digest_id": f"digest_{uuid4().hex}",
        "ibkr_account_ref": ibkr_account_ref,
        "market_code": market_code,
        "briefing_date": briefing_date,
        "generated_at": generated_at,
        "nav_summary_json": nav_summary,
        "positions_summary_json": positions_summary,
        "suggestions_summary_json": suggestions_summary,
        "action_drafts_summary_json": drafts_summary,
        "alerts_json": alerts,
        "status": status,
        "blocking_reason": blocking_reason,
    }


__all__ = [
    "compute_daily_digest_payload",
]
