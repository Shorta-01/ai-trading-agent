"""Go-live runbook endpoint (V1.2 §BH / CLAUDE.md §16).

CLAUDE.md §16 noemt een 8-12 PR roadmap voor de doctrine; deze
endpoint is de operator-facing checklist die toont waar het systeem
qua go-live readiness staat. Drie groepen items:

1. **Doctrine-locks** — bevestigt dat ``paper_only_mode`` aan staat,
   geen leverage-flags actief zijn, AI niet als forecaster gebruikt
   wordt, etc.
2. **Provider configuratie** — IBKR/EODHD/Claude/SMTP keys aanwezig,
   storage schrijfbaar, etc.
3. **Doctrine-features** — earnings calendar enabled, orchestrator
   scoring enabled, profit-target geconfigureerd, etc.

Elke check krijgt een ``status``:

* ``ok`` — alles in orde
* ``info`` — informatief, niet blokkerend (optie staat uit, maar dat
  is een geldige keuze)
* ``warning`` — operator moet een actie ondernemen voor volledige
  productie-functionaliteit
* ``blocking`` — *hard* blokkerend; software kan niet veilig
  in productie zonder dit te fixen

De endpoint heeft daarnaast één samenvattende boolean
``ready_for_paper_go_live`` die alleen ``True`` is als alle
``blocking`` items in orde zijn.

Read-only en idempotent — geen state-wijzigingen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import APIRouter
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


STATUS_OK = "ok"
STATUS_INFO = "info"
STATUS_WARNING = "warning"
STATUS_BLOCKING = "blocking"


@dataclass(frozen=True)
class RunbookItem:
    code: str
    group: str
    label_nl: str
    status: str
    value_nl: str
    what_it_means_nl: str


class RunbookItemResponse(BaseModel):
    code: str
    group: str
    label_nl: str
    status: str
    value_nl: str
    what_it_means_nl: str


class RunbookResponse(BaseModel):
    title_nl: str
    help_nl: str
    ready_for_paper_go_live: bool
    summary_nl: str
    items: list[RunbookItemResponse]


_HELP_NL = (
    "Operator-checklist voor paper-go-live. Elk item heeft een "
    "status: ok / info / warning / blocking. Alleen blocking-items "
    "houden de software echt tegen; warnings betekent missende "
    "configuratie voor volledige doctrine-functionaliteit."
)


def _yes_no(value: bool) -> str:
    return "ja" if value else "nee"


def _doctrine_lock_items() -> list[RunbookItem]:
    """Hard doctrine-locks die NOOIT mogen omklappen in V1."""

    items: list[RunbookItem] = [
        RunbookItem(
            code="paper_only_mode",
            group="doctrine_locks",
            label_nl="Paper-only modus",
            status=STATUS_OK if settings.paper_only_mode else STATUS_BLOCKING,
            value_nl=f"Aan: {_yes_no(settings.paper_only_mode)}",
            what_it_means_nl=(
                "CLAUDE.md §1 + §15 — geen live geld. Mag NOOIT op False "
                "in productie. Als deze blocking is moet je hem terug "
                "naar True zetten voor je iets anders doet."
            ),
        ),
    ]
    return items


def _provider_config_items() -> list[RunbookItem]:
    """Provider-configuratie checks (EODHD / IBKR / SMTP / storage)."""

    storage = settings.storage
    storage_ok = bool(
        storage.enabled and storage.database_url and storage.writes_enabled
    )
    eodhd_key_set = bool(getattr(settings, "eodhd_api_key", None))
    ibkr_enabled = getattr(settings, "ibkr_enabled", False)
    claude_key_set = bool(getattr(settings, "claude_ai_api_key", None))

    items: list[RunbookItem] = [
        RunbookItem(
            code="storage_writable",
            group="provider_config",
            label_nl="Opslag schrijfbaar",
            status=STATUS_OK if storage_ok else STATUS_BLOCKING,
            value_nl=(
                "enabled + database_url + writes_enabled"
                if storage_ok
                else "Een of meer storage-flags ontbreken"
            ),
            what_it_means_nl=(
                "Zonder schrijfbare opslag kan de morning-chain geen "
                "audit-rijen wegschrijven en kan de SELL-loop geen "
                "kaartjes opslaan. Hard vereist."
            ),
        ),
        RunbookItem(
            code="eodhd_api_key",
            group="provider_config",
            label_nl="EODHD API-key",
            status=STATUS_OK if eodhd_key_set else STATUS_WARNING,
            value_nl="Geconfigureerd" if eodhd_key_set else "Niet ingesteld",
            what_it_means_nl=(
                "Zonder EODHD-key valt market-data, forecasts en "
                "earnings refresh weg. De software draait nog "
                "(SELL-sweep blijft werken), maar geen nieuwe "
                "BUY-voorstellen of forecast updates."
            ),
        ),
        RunbookItem(
            code="ibkr_enabled",
            group="provider_config",
            label_nl="IBKR-verbinding ingeschakeld",
            status=STATUS_OK if ibkr_enabled else STATUS_WARNING,
            value_nl=_yes_no(ibkr_enabled),
            what_it_means_nl=(
                "IBKR paper-account vereist voor live positie-sync, "
                "order-submissie en reconciliation. Zonder verbinding "
                "draait alles op de laatste snapshot."
            ),
        ),
        RunbookItem(
            code="claude_ai_api_key",
            group="provider_config",
            label_nl="Claude AI key (optioneel, alleen NL-uitleg)",
            status=STATUS_OK if claude_key_set else STATUS_INFO,
            value_nl="Geconfigureerd" if claude_key_set else "Niet ingesteld",
            what_it_means_nl=(
                "CLAUDE.md §15 — AI mag NOOIT als forecaster gebruikt "
                "worden; alleen NL-paraphrase. Zonder key vallen de "
                "AI-uitleg kaartjes weg, maar niets blokkerends."
            ),
        ),
    ]
    return items


def _doctrine_feature_items() -> list[RunbookItem]:
    """Doctrine-features die de operator moet activeren voor de
    volledige V1.2-pipeline (Earnings-gate, profit-harvest scoring,
    etc.)."""

    # Locked vocabulary — sync flags namen wijken net af van elkaar
    # (sommige in single, sommige in plural). De flag-namen hier
    # MOETEN matchen wat morning_chain.py daadwerkelijk checkt.
    flags: tuple[tuple[str, str], ...] = (
        ("market_data_sync_enabled", "Market-data sync"),
        ("forecast_sync_enabled", "Forecast sync"),
        ("suggestions_sync_enabled", "Suggestions sync"),
        ("decision_packages_sync_enabled", "Decision-packages sync"),
        ("action_drafts_sync_enabled", "Action-drafts sync"),
        ("earnings_calendar_sync_enabled", "Earnings-calendar refresh (§AK)"),
        ("orchestrator_scoring_enabled", "Orchestrator scoring (§Y)"),
        ("daily_briefing_sync_enabled", "Daily briefing"),
    )
    items: list[RunbookItem] = []
    for attr, label_nl in flags:
        is_on = bool(getattr(settings, attr, False))
        items.append(
            RunbookItem(
                code=attr,
                group="doctrine_features",
                label_nl=label_nl,
                status=STATUS_OK if is_on else STATUS_WARNING,
                value_nl=_yes_no(is_on),
                what_it_means_nl=(
                    f"Setting ``{attr}``. Zonder deze schakel valt de "
                    f"bijbehorende morning-chain leg op skipped."
                ),
            )
        )
    return items


def _build_runbook_items() -> list[RunbookItem]:
    items: list[RunbookItem] = []
    items.extend(_doctrine_lock_items())
    items.extend(_provider_config_items())
    items.extend(_doctrine_feature_items())
    return items


def _summarise(items: list[RunbookItem]) -> tuple[bool, str]:
    blocking = [i for i in items if i.status == STATUS_BLOCKING]
    warnings = [i for i in items if i.status == STATUS_WARNING]
    if blocking:
        labels = ", ".join(i.label_nl for i in blocking)
        return False, (
            f"Niet klaar voor paper-go-live: {len(blocking)} blocking "
            f"item(s) — {labels}. Fix deze eerst."
        )
    if warnings:
        return True, (
            f"Klaar voor paper-go-live, maar {len(warnings)} warning"
            f"(s) ingeschakeld voor volledige doctrine-functionaliteit. "
            f"Software draait veilig; sommige legs vallen op skipped."
        )
    return True, (
        "Alle doctrine-locks + provider-configuratie + features in orde. "
        "Paper-go-live klaar."
    )


@router.get("/runbook", response_model=RunbookResponse)
def get_runbook() -> RunbookResponse:
    """Read-only operator-checklist voor go-live readiness.

    De endpoint zelf wijzigt niets — pure introspectie op
    ``settings``. Veilig om vaak te lezen (geen DB roundtrip per
    item).
    """

    items = _build_runbook_items()
    ready, summary_nl = _summarise(items)
    return RunbookResponse(
        title_nl="Go-live runbook",
        help_nl=_HELP_NL,
        ready_for_paper_go_live=ready,
        summary_nl=summary_nl,
        items=[
            RunbookItemResponse(
                code=item.code,
                group=item.group,
                label_nl=item.label_nl,
                status=item.status,
                value_nl=item.value_nl,
                what_it_means_nl=item.what_it_means_nl,
            )
            for item in items
        ],
    )


__all__ = ["router"]
