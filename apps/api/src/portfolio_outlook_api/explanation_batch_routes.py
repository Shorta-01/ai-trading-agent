"""Pre-compute morning Claude explanations for held-position Decision Packages.

Fired by the worker after the daily morning chain. Reads today's
persisted Decision Packages for the operator's held positions and
calls :func:`generate_explanations_for_morning_batch` to populate
Claude's Dutch paraphrase for each one. By the time the operator
opens the dashboard at 07:00 coffee, every suggestion already has its
explanation ready instead of generating lazily on first click.

Budget enforcement still applies: the underlying provider factory
short-circuits to ``stubbed`` when the monthly cap is hit, so the
batch can never run away. The endpoint reports the exact counts in
its response so the worker scheduler-runs audit shows what landed.
"""

from __future__ import annotations

import logging
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyAssetDecisionPackageRepository,
    SqlAlchemyDecisionPackageExplanationRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyResearchSourceArchiveRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.ai_explanation_provider import (
    build_explanation_provider,
)
from portfolio_outlook_api.ai_explanation_sync import (
    generate_explanations_for_morning_batch,
)
from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class MorningExplanationBatchResponse(BaseModel):
    status: str
    status_nl: str
    help_nl: str
    package_count: int
    generated_count: int
    blocked_count: int
    skipped_count: int
    blocking_reasons: list[str]
    safe_for_orders: bool


_HELP_NL = (
    "Voorspelt 's ochtends elke Decision Package alvast door Claude "
    "zodat de operator om 07:00 al de Nederlandse paraphrase ziet "
    "in plaats van bij elke klik te wachten. Respecteert het maand-"
    "budget — bij overschrijding valt elke uitleg terug op de stub."
)


def _empty(status: str, status_nl: str) -> MorningExplanationBatchResponse:
    return MorningExplanationBatchResponse(
        status=status,
        status_nl=status_nl,
        help_nl=_HELP_NL,
        package_count=0,
        generated_count=0,
        blocked_count=0,
        skipped_count=0,
        blocking_reasons=[],
        safe_for_orders=False,
    )


@router.post(
    "/explanations/morning-batch",
    response_model=MorningExplanationBatchResponse,
)
def trigger_morning_explanation_batch() -> MorningExplanationBatchResponse:
    if not settings.ai_explanation_morning_batch_enabled:
        return _empty(
            "disabled",
            "Morning explanation batch is uitgeschakeld (env-var opt-in).",
        )

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty(
            "not_configured", "Opslag niet geconfigureerd"
        )

    try:
        storage_provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        # Phase 1: read-only fetch of today's DPs for held conids.
        with storage_provider.checked_connection(require_writable=False) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return _empty(
                    "no_ibkr_sync_run", "Geen IBKR-sync gevonden"
                )
            positions = list(
                ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
            )
            held_conids = tuple({p.conid for p in positions if p.conid})
            if not held_conids:
                return _empty(
                    "no_held_positions",
                    "Geen posities — geen Decision Packages om uit te leggen.",
                )
            dp_repo = SqlAlchemyAssetDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            dp_result = dp_repo.list_latest_asset_decision_packages_by_conids(
                held_conids
            )
            decision_packages = list(dp_result.records)

        if not decision_packages:
            return _empty(
                "no_decision_packages",
                "Nog geen Decision Packages voor vandaag.",
            )

        # Phase 2: open a writable connection per batch so the
        # explanation upserts + budget rows commit cleanly. The
        # provider's budget check happens inside generate_explanation,
        # so a burnt cap mid-batch still fails gracefully.
        with storage_provider.checked_connection(require_writable=True) as checked:
            explanation_repo = SqlAlchemyDecisionPackageExplanationRepository(
                checked.connection, checked.readiness
            )
            research_repo = SqlAlchemyResearchSourceArchiveRepository(
                checked.connection, checked.readiness
            )

            def _sources_for(symbol: str) -> tuple[Any, ...]:
                # The research-source archive is symbol-scoped, not
                # conid-scoped, because research is researched once per
                # ticker regardless of how many IBKR conids share it.
                return tuple(
                    research_repo.list_research_sources_for_asset(symbol)
                )

            provider = build_explanation_provider(settings)
            report = generate_explanations_for_morning_batch(
                decision_packages=decision_packages,
                research_sources_for_symbol=_sources_for,
                provider=provider,
                repo=explanation_repo,
                max_output_chars=settings.ai_explanation_max_output_chars,
            )
            checked.connection.commit()
    except StorageConnectionError as exc:
        logger.warning("morning-explanation-batch storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    status = "ok" if report.generated_count > 0 else "no_explanations_generated"
    if report.skipped_count > 0 and report.generated_count == 0:
        status = "provider_unavailable"

    return MorningExplanationBatchResponse(
        status=status,
        status_nl=(
            f"{report.generated_count} uitleg(en) gegenereerd, "
            f"{report.blocked_count} geblokkeerd, "
            f"{report.skipped_count} overgeslagen "
            f"(totaal {report.package_count} pakketten)."
        ),
        help_nl=_HELP_NL,
        package_count=report.package_count,
        generated_count=report.generated_count,
        blocked_count=report.blocked_count,
        skipped_count=report.skipped_count,
        blocking_reasons=list(report.blocking_reasons),
        safe_for_orders=False,
    )


__all__ = ["MorningExplanationBatchResponse", "router"]
