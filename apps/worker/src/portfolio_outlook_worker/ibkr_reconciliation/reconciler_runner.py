"""V1.2 §BM / GAPS.md P0-3 — runner that wires :class:`IbkrReconciler`
into the worker scheduler.

The reconciler orchestrator was always built but never invoked: the
scheduler had no factory that opens a storage connection, constructs
the seven repositories + two read-side fetchers, and feeds them into
``IbkrReconciler.tick()``. Without this runner the three audit queues
the ``/admin/reconciliation`` dashboard reads (``reconciliation_run_audit``,
``unmatched_execution_audit``, ``manual_review_queue``) never advanced
automatically — which is exactly the doctrine gap CLAUDE.md §2 calls
out.

The runner mirrors the existing order-sweep wiring in
``scheduler._run_order_sweep``: per tick it opens a fresh writable
storage connection (so each tick is a self-contained transaction),
builds the lock + fetchers + repos against that connection, then
delegates the actual reconciliation logic to ``IbkrReconciler``.

Doctrine-locks preserved:
* ``IbkrReconciler`` itself enforces single-flight via the lock, so a
  slow tick won't queue behind itself.
* When the gateway is disconnected or storage is paused, ``tick()``
  records the audit row with ``mode_detected="skipped_*"`` — no
  silent skip.
* No ``safe_for_*`` flag is flipped; the runner only updates the
  audit-trail rows.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyManualReviewQueueRepository,
    SqlAlchemyReconciliationAuditRepository,
    SqlAlchemyReconciliationRunAuditRepository,
    SqlAlchemyUnmatchedExecutionAuditRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_worker.ibkr_reconciliation.ibkr_reconciliation_adapter import (
    IbkrExecutionFetcher,
    IbkrOrderStatusFetcher,
    ReadCapableIbClientProtocol,
)
from portfolio_outlook_worker.ibkr_reconciliation.reconciler import (
    IbkrReconciler,
    IbkrReconcilerGatewayProtocol,
    IbkrReconcilerResult,
)
from portfolio_outlook_worker.single_flight_lock import SingleFlightLockProtocol

logger = logging.getLogger(__name__)


# Re-export the protocol types so the scheduler can spell out the
# imports in one place.
LockFactory = Any  # Callable[[connection], SingleFlightLockProtocol]
NowProvider = Any  # Callable[[], datetime]


class _GatewayBridge:
    """Adapt the worker's ``IbkrGateway`` to ``IbkrReconcilerGatewayProtocol``.

    The reconciler only needs ``is_connected()``; the bridge keeps the
    explicit method signature so a future reconciler-protocol expansion
    doesn't break the worker by accident.
    """

    def __init__(self, gateway: IbkrReconcilerGatewayProtocol) -> None:
        self._gateway = gateway

    def is_connected(self) -> bool:
        return self._gateway.is_connected()


def run_reconciler_tick(
    *,
    storage_provider: StorageConnectionProvider,
    ib_client: ReadCapableIbClientProtocol,
    gateway: IbkrReconcilerGatewayProtocol,
    lock_factory: LockFactory,
    ibkr_account_id: str,
    pass_c_timeout_cutoff: timedelta,
    now_provider: NowProvider = lambda: datetime.now(UTC),
) -> IbkrReconcilerResult | None:
    """Open one writable storage connection and run ``IbkrReconciler.tick()``.

    Returns the result so the scheduler can track per-mode outcomes
    (e.g. surface ``mode_detected="error"`` to ``/systeemmeldingen``).
    ``None`` means we never even opened storage — the operator's DB
    is unreachable, which is logged but doesn't raise (scheduled jobs
    must never crash the scheduler loop).
    """

    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            lock = lock_factory(checked.connection)
            action_draft_repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            executions_repo = SqlAlchemyIbkrExecutionsRepository(
                checked.connection, checked.readiness
            )
            submission_audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(
                checked.connection, checked.readiness
            )
            unmatched_repo = SqlAlchemyUnmatchedExecutionAuditRepository(
                checked.connection, checked.readiness
            )
            manual_review_repo = SqlAlchemyManualReviewQueueRepository(
                checked.connection, checked.readiness
            )
            reconciliation_audit_repo = SqlAlchemyReconciliationAuditRepository(
                checked.connection, checked.readiness
            )
            run_audit_repo = SqlAlchemyReconciliationRunAuditRepository(
                checked.connection, checked.readiness
            )

            execution_fetcher = IbkrExecutionFetcher(ib_client=ib_client)
            order_status_fetcher = IbkrOrderStatusFetcher(ib_client=ib_client)

            reconciler = IbkrReconciler(
                ibkr_account_id=ibkr_account_id,
                lock=lock,
                gateway=_GatewayBridge(gateway),
                execution_fetcher=execution_fetcher,
                order_status_fetcher=order_status_fetcher,
                action_draft_repo=action_draft_repo,
                executions_repo=executions_repo,
                submission_audit_repo=submission_audit_repo,
                unmatched_repo=unmatched_repo,
                manual_review_repo=manual_review_repo,
                reconciliation_audit_repo=reconciliation_audit_repo,
                run_audit_repo=run_audit_repo,
                now_provider=now_provider,
                pass_c_timeout_cutoff=pass_c_timeout_cutoff,
            )
            result = reconciler.tick()
            # ``checked_connection`` doesn't auto-commit; persistence
            # would otherwise be rolled back when the context manager
            # closes.
            checked.connection.commit()
            return result
    except StorageConnectionError as exc:
        logger.warning(
            "reconciler tick could not open storage: %s", exc
        )
        return None


def build_storage_provider(database_url: str) -> StorageConnectionProvider:
    """Thin factory so the scheduler can construct providers without
    importing ``ai_trading_agent_storage`` directly. Mirrors the
    pattern used by the order-sweep wiring."""

    return StorageConnectionProvider(
        build_database_connection_settings(database_url)
    )


__all__ = [
    "LockFactory",
    "NowProvider",
    "SingleFlightLockProtocol",
    "build_storage_provider",
    "run_reconciler_tick",
]
