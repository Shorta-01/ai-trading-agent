"""Morning-chain leg wiring helper (V1.2 §BG).

Brengt de "real" leg-implementaties — :func:`build_real_earnings_
calendar_leg` en :func:`build_real_orchestrator_scoring_leg` — naar
*beide* code-paden die de morning chain kunnen starten:

1. **Worker-trigger pad** (`POST /scheduler/runs/morning-chain` in
   :mod:`status_routes`) — wat het worker-proces aanroept in de
   nieuwe ``scheduler_api_legacy_cron=False`` default.
2. **Legacy in-process scheduler pad** (in :mod:`scheduler.py`) —
   wat blijft draaien wanneer de operator expliciet de oude API-cron
   gebruikt.

Tot V1.2 §BG injecteerde alleen het legacy-pad de echte
EODHD-earnings leg; de HTTP-trigger viel terug op de no-op stub
in :func:`morning_chain.build_default_morning_chain_legs`. Resultaat:
een operator die ``earnings_calendar_sync_enabled=True`` zette
zag de earnings-refresh nooit lopen in productie omdat de worker
de HTTP-route gebruikt.

Deze helper consolideert de wiring zodat beide paden identiek
gedragen. De flags zelf (en bijbehorende preconditie-checks zoals
EODHD-key aanwezig) worden door de leg-builders gedaan; deze
helper schakelt enkel "real" leg ↔ "stub leg" op basis van of de
config het toelaat.

CLAUDE.md §2 + §15 — geen verandering aan safety flags. Deze
helper is een pure wiring-laag.
"""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.morning_chain import (
    LegCallable,
    build_default_morning_chain_legs,
)


def build_morning_chain_legs_with_real_overrides(
    runtime_settings: Settings,
) -> Sequence[LegCallable]:
    """Bouw de morning-chain legs met de echte EODHD + orchestrator
    leg-implementaties wanneer de bijbehorende flags ingeschakeld
    zijn.

    * ``earnings_calendar_sync_enabled=True`` → real EODHD-backed
      earnings-calendar leg.
    * ``orchestrator_scoring_enabled=True`` → real orchestrator
      scoring leg (V1.2 §Y profit-harvest).

    Wanneer een flag uit staat blijft de bestaande no-op stub uit
    :func:`build_default_morning_chain_legs` actief — net zoals
    voor V1.2 §BG. Geen ander gedragsverschil.

    Imports zijn lazy zodat het helper-module ook in een minimale
    test-context geladen kan worden zonder dat de real-leg
    afhankelijkheden (EODHD client, storage providers) hoeven te
    resolven.
    """

    earnings_override: LegCallable | None = None
    if getattr(runtime_settings, "earnings_calendar_sync_enabled", False):
        from portfolio_outlook_api.earnings_calendar_leg import (
            build_real_earnings_calendar_leg,
        )

        earnings_override = build_real_earnings_calendar_leg(runtime_settings)

    orchestrator_override: LegCallable | None = None
    if getattr(runtime_settings, "orchestrator_scoring_enabled", False):
        from portfolio_outlook_api.orchestrator_scoring_leg import (
            build_real_orchestrator_scoring_leg,
        )

        orchestrator_override = build_real_orchestrator_scoring_leg(
            runtime_settings
        )

    return build_default_morning_chain_legs(
        runtime_settings,
        earnings_calendar_leg_override=earnings_override,
        orchestrator_scoring_leg_override=orchestrator_override,
    )


__all__ = ["build_morning_chain_legs_with_real_overrides"]
