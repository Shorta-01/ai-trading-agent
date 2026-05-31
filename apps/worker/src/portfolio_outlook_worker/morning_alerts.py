"""Compute morning-chain alerts from today's persisted suggestions.

Sister module to :mod:`daily_digest`: same alert dict shape, different
trigger conditions. Fires at 07:00 (worker ``morning_briefing`` event)
after the API morning chain has persisted today's suggestions —
:class:`MorningAlertsRunner` then emails the operator if anything
urgent landed before they wake up.

Trigger conditions (V1):

* ``high_confidence_sell_morning`` — a held position has a fresh
  Verkopen or Verminderen suggestion at high confidence. This is the
  one the user explicitly asked for ("ping me when a held position
  flips to sell"). Most urgent.

* ``new_high_confidence_buy`` — a non-held asset has a fresh Kopen
  suggestion at high confidence. Optional and less urgent; useful for
  operators on the Groei profile who want a heads-up before EU open.

* ``morning_chain_failure`` — the chain itself raised, so today's
  forecasts may be stale or missing. Surfaces the failure so the
  operator notices before relying on yesterday's data.

The compute function is pure: same shape as ``compute_daily_digest_payload``'s
internal ``_alerts`` helper. Persistence + email delivery live in
:class:`MorningAlertsRunner`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

_VERKOOP_LABELS_NL = frozenset({"Verkopen", "Verminderen"})
_KOOP_LABEL_NL = "Kopen"


def _is_high_confidence(suggestion: Any) -> bool:
    label = str(getattr(suggestion, "confidence_label", "")).lower()
    return label in {"high", "hoog"}


def _is_ready(suggestion: Any) -> bool:
    return str(getattr(suggestion, "status", "")).lower() == "ready"


def compute_morning_alerts(
    *,
    suggestions: Sequence[Any],
    held_conids: Iterable[str],
    chain_failed: bool = False,
    failure_reason_nl: str | None = None,
) -> list[dict[str, object]]:
    """Return the operator-facing alert list for one morning chain.

    ``suggestions`` is the freshly persisted set for the operator's
    universe. ``held_conids`` decides which suggestions count as a
    held-position sell vs a cold-start buy. ``chain_failed`` surfaces
    a deterministic failure-mode alert independently of the
    suggestion-driven ones — useful when the morning chain partially
    or wholly errored out.
    """

    alerts: list[dict[str, object]] = []
    held = {str(c) for c in held_conids if c}

    if chain_failed:
        alerts.append(
            {
                "kind": "morning_chain_failure",
                "severity_nl": "Belangrijk",
                "title_nl": (
                    "Morgen-chain heeft vandaag een fout — voorspellingen "
                    "kunnen ontbreken of stale zijn"
                ),
                "body_nl": (
                    failure_reason_nl
                    or "Controleer de scheduler-audit en het system-events log."
                ),
                "reference_kind": "scheduler_run",
                "reference_id": None,
            }
        )

    high_conf_sells: list[Any] = []
    high_conf_buys: list[Any] = []

    for suggestion in suggestions:
        if not _is_ready(suggestion):
            continue
        if not _is_high_confidence(suggestion):
            continue
        label = str(getattr(suggestion, "action_label_nl", ""))
        conid = str(getattr(suggestion, "ibkr_conid", "") or "")
        in_held = conid in held
        if in_held and label in _VERKOOP_LABELS_NL:
            high_conf_sells.append(suggestion)
        elif not in_held and label == _KOOP_LABEL_NL:
            high_conf_buys.append(suggestion)

    if high_conf_sells:
        symbols = ", ".join(
            sorted(
                {
                    str(getattr(s, "symbol", "?") or "?")
                    for s in high_conf_sells
                }
            )
        )
        alerts.append(
            {
                "kind": "high_confidence_sell_morning",
                "severity_nl": "Belangrijk",
                "title_nl": (
                    f"{len(high_conf_sells)} verkoop-suggestie(s) met hoge "
                    "zekerheid op posities die je bezit"
                ),
                "body_nl": (
                    f"Symbolen: {symbols}. Open /suggesties en bekijk de "
                    "Decision Packages voor markt-open."
                ),
                "reference_kind": "suggestions",
                "reference_id": None,
            }
        )

    if high_conf_buys:
        symbols = ", ".join(
            sorted(
                {
                    str(getattr(s, "symbol", "?") or "?")
                    for s in high_conf_buys
                }
            )
        )
        alerts.append(
            {
                "kind": "new_high_confidence_buy",
                "severity_nl": "Aanbeveling",
                "title_nl": (
                    f"{len(high_conf_buys)} nieuwe Kopen-suggestie(s) met "
                    "hoge zekerheid"
                ),
                "body_nl": (
                    f"Symbolen: {symbols}. Niet automatisch — review de "
                    "Decision Package voordat je BEVESTIG-t."
                ),
                "reference_kind": "suggestions",
                "reference_id": None,
            }
        )

    return alerts


__all__ = ["compute_morning_alerts"]
