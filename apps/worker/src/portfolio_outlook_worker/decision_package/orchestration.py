"""Task 132: Decision Package composition orchestration.

The bridge between the persisted forecasts of a scheduled run and the
``compose_decision_package`` pure function. Iterates non-``Geblokkeerd``
forecasts, composes a Decision Package per asset, persists each.

Failures in single-asset composition are logged but do **not** crash
the run — the forecast row is already durable, so a failed package
composition is a soft degradation, not data loss. The summary dict
folded into the scheduled_run_audit makes the failure visible.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from ai_trading_agent_storage import (
    AssetListingRecord,
    ForecastEntry,
    FxRateRecord,
    IbkrPositionSnapshotRecord,
    MarketDataEodSnapshotEntry,
    SqlAlchemyDecisionPackageRepository,
)

from portfolio_outlook_worker.decision_package.composer import (
    GeblokkeerdForecastError,
    compose_decision_package,
)

logger = logging.getLogger(__name__)


class _ForecastSourceProtocol(Protocol):
    """Returns the forecasts written under a given scheduled_run_id."""

    def list_forecasts_for_scheduled_run(
        self, *, ibkr_account_id: str, scheduled_run_id: str
    ) -> tuple[ForecastEntry, ...]: ...


class _ContextProviderProtocol(Protocol):
    """Returns the per-asset context the composer needs."""

    def market_snapshot_for_conid(
        self, *, conid: str
    ) -> MarketDataEodSnapshotEntry | None: ...

    def fx_rate_for_currency(
        self, *, currency_local: str
    ) -> FxRateRecord | None: ...

    def asset_listing_for_conid(
        self, *, conid: str
    ) -> AssetListingRecord | None: ...

    def position_for_account_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> IbkrPositionSnapshotRecord | None: ...


@dataclass(frozen=True)
class DecisionPackageCompositionResult:
    """Audit-row summary the orchestrator folds into scheduled_run_audit.

    The invariant for the audit is:

        forecasts_seen ==
            composed + skipped_geblokkeerd + missing_context + composition_errors
    """

    forecasts_seen: int
    composed: int
    skipped_geblokkeerd: int
    missing_context: int = 0
    composition_errors: int = 0
    persisted_ids: tuple[str, ...] = field(default_factory=tuple)

    def as_audit_dict(self) -> dict[str, object]:
        return {
            "forecasts_seen": self.forecasts_seen,
            "composed": self.composed,
            "skipped_geblokkeerd": self.skipped_geblokkeerd,
            "missing_context": self.missing_context,
            "composition_errors": self.composition_errors,
        }


def compose_and_persist_for_run(
    *,
    ibkr_account_id: str,
    scheduled_run_id: str,
    forecast_source: _ForecastSourceProtocol,
    context_provider: _ContextProviderProtocol,
    decision_package_repo: SqlAlchemyDecisionPackageRepository,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> DecisionPackageCompositionResult:
    """Compose + persist one Decision Package per non-Geblokkeerd forecast.

    Never raises. Per-asset failures are caught and counted in the
    returned ``DecisionPackageCompositionResult``.
    """

    forecasts = forecast_source.list_forecasts_for_scheduled_run(
        ibkr_account_id=ibkr_account_id,
        scheduled_run_id=scheduled_run_id,
    )

    composed = 0
    skipped_geblokkeerd = 0
    missing_context = 0
    composition_errors = 0
    persisted_ids: list[str] = []

    for forecast in forecasts:
        if forecast.label == "Geblokkeerd":
            skipped_geblokkeerd += 1
            continue

        snapshot = context_provider.market_snapshot_for_conid(
            conid=forecast.conid
        )
        if snapshot is None:
            # No snapshot → composer can't compute current_price_eur or
            # the freshness gate. Skip cleanly + count the gap.
            logger.warning(
                "Skipping Decision Package for %s: no market snapshot",
                forecast.conid,
            )
            missing_context += 1
            continue

        fx_rate = (
            None
            if forecast.currency_local == "EUR"
            else context_provider.fx_rate_for_currency(
                currency_local=forecast.currency_local
            )
        )
        asset_listing = context_provider.asset_listing_for_conid(
            conid=forecast.conid
        )
        position = context_provider.position_for_account_conid(
            ibkr_account_id=ibkr_account_id, conid=forecast.conid
        )
        previous_package = (
            decision_package_repo.get_latest_for_account_conid(
                ibkr_account_id=ibkr_account_id, conid=forecast.conid
            )
        )

        try:
            package = compose_decision_package(
                forecast=forecast,
                ibkr_account_id=ibkr_account_id,
                market_snapshot=snapshot,
                fx_rate=fx_rate,
                asset_listing=asset_listing,
                position_snapshot=position,
                previous_package=previous_package,
                composed_at=now_provider(),
            )
        except GeblokkeerdForecastError:
            # Defensive — already filtered above.
            skipped_geblokkeerd += 1
            continue
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "Decision Package composition failed for %s",
                forecast.conid,
            )
            composition_errors += 1
            continue

        try:
            decision_package_repo.append(package)
            composed += 1
            persisted_ids.append(package.decision_package_id)
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "Decision Package persistence failed for %s",
                forecast.conid,
            )
            composition_errors += 1

    return DecisionPackageCompositionResult(
        forecasts_seen=len(forecasts),
        composed=composed,
        skipped_geblokkeerd=skipped_geblokkeerd,
        missing_context=missing_context,
        composition_errors=composition_errors,
        persisted_ids=tuple(persisted_ids),
    )


__all__ = [
    "DecisionPackageCompositionResult",
    "compose_and_persist_for_run",
]
