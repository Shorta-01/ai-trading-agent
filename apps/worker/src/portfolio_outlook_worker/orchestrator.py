"""Task 127: scheduled-run orchestrator.

The orchestrator is the single function APScheduler invokes for every
fire. It performs the locked cold-start detection algorithm,
writes one append-only audit row, and returns. **No other work** —
no advice generation, no market data fetch, no discovery. Those are
explicitly out of scope for Task 127.

Algorithm:

1. Acquire single-flight lock via the injected
   :class:`SingleFlightLockProtocol`. Failure → audit row with
   ``mode_detected="skipped_locked"`` and exit.
2. Check IBKR gateway connection. Disconnected → audit row with
   ``mode_detected="disconnected"`` and exit.
3. Read latest persisted position-snapshot count + watchlist count
   for the configured ``ibkr_account_id``. Both zero →
   ``cold_start``; otherwise ``normal``.
4. Compute the next scheduled fire time from the injected scheduler.
5. Write the audit row with the computed outcome + duration_ms.
6. Release the lock and return.

Errors anywhere in the pipeline → ``outcome="error"`` audit row with
``error_details_json`` carrying a Dutch reason string. The
orchestrator never raises — it always returns cleanly so APScheduler
doesn't kill the job.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    ScheduledRunAuditEntry,
    SqlAlchemyScheduledRunAuditRepository,
)

from portfolio_outlook_worker.single_flight_lock import (
    SingleFlightLockProtocol,
)

logger = logging.getLogger(__name__)

RunType = Literal["pre_briefing", "morning_briefing", "hourly_delta"]
ModeDetected = Literal[
    "cold_start",
    "normal",
    "disconnected",
    "skipped_locked",
    "skipped_disabled",
    # Task 128: between the cold-start seed and the user's BEVESTIG.
    "awaiting_watchlist_confirmation",
]
Outcome = Literal["completed", "error"]


class _ConfirmationStateProtocol(Protocol):
    """Task 128 adapter exposing the watchlist confirmation state.

    Returns ``None`` when no row exists for the account yet (i.e.
    the cold-start seed hasn't run).
    """

    def get_state(self, ibkr_account_id: str) -> str | None: ...


class _SeedRunnerProtocol(Protocol):
    """Task 128 adapter that triggers the cold-start seed.

    Idempotent — the implementation is responsible for the
    one-time-per-account guarantee (the storage layer enforces it
    via ``UNIQUE`` on ``ibkr_account_id``).
    """

    def seed(self, ibkr_account_id: str) -> bool: ...


class _MarketDataRunnerProtocol(Protocol):
    """Task 129 adapter that runs the EOD market-data fetch.

    Called only on ``normal`` fires that are also ``pre_briefing``
    or ``morning_briefing``. Returns a dict folded into the
    audit row's ``details_json``. Never raises.
    """

    def run(
        self, *, ibkr_account_id: str, run_type: str
    ) -> dict[str, object]: ...


class _GatewayProtocol(Protocol):
    def is_connected(self) -> bool: ...


class _SnapshotCountsProtocol(Protocol):
    """Storage adapter exposing the two counts the orchestrator needs.

    Pulled out as a Protocol so production wires it to a SQLAlchemy
    repository while unit tests inject a hand-built fake.
    """

    def position_snapshot_count_for_account(
        self, ibkr_account_id: str
    ) -> int: ...

    def watchlist_item_count_for_account(
        self, ibkr_account_id: str
    ) -> int: ...


@dataclass(frozen=True)
class OrchestratorResult:
    """What the orchestrator returns after one fire."""

    run_id: str
    run_type: RunType
    mode_detected: ModeDetected
    outcome: Outcome
    duration_ms: int


def _relabel_morning_briefing(
    run_type: RunType, brussels_now_hour: int
) -> RunType:
    """The 07:00 hourly fire gets relabelled in the audit row.

    Task 127 product lock §2: the cron job is one ``hourly`` trigger;
    the 07:00 instance is the morning briefing. Encoding this in the
    orchestrator (not in two separate cron jobs) keeps the trigger
    surface narrow.
    """

    if run_type == "hourly_delta" and brussels_now_hour == 7:
        return "morning_briefing"
    return run_type


def run_orchestrator(
    *,
    run_type: RunType,
    ibkr_account_id: str | None,
    gateway: _GatewayProtocol,
    snapshot_counts: _SnapshotCountsProtocol,
    audit_repo: SqlAlchemyScheduledRunAuditRepository,
    lock: SingleFlightLockProtocol,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
    brussels_hour_provider: Callable[[], int] | None = None,
    next_scheduled_at: datetime | None = None,
    confirmation_state: _ConfirmationStateProtocol | None = None,
    seed_runner: _SeedRunnerProtocol | None = None,
    market_data_runner: _MarketDataRunnerProtocol | None = None,
) -> OrchestratorResult:
    """One scheduled-run cycle.

    Never raises — every failure path lands in a ``mode_detected``
    or ``outcome="error"`` audit row. The return value is informative
    for tests and the worker logs; APScheduler itself ignores it.
    """

    started = now_provider()
    run_id = f"srun_{uuid4().hex}"

    # 1. Single-flight lock acquisition.
    if not lock.try_acquire():
        _safe_append(
            audit_repo,
            ScheduledRunAuditEntry(
                run_id=run_id,
                run_at=started,
                run_type=run_type,
                ibkr_account_id=ibkr_account_id,
                mode_detected="skipped_locked",
                duration_ms=_duration_ms(started, now_provider()),
                outcome="completed",
                error_details_json=None,
                next_scheduled_at=next_scheduled_at,
            ),
        )
        return OrchestratorResult(
            run_id=run_id,
            run_type=run_type,
            mode_detected="skipped_locked",
            outcome="completed",
            duration_ms=_duration_ms(started, now_provider()),
        )

    try:
        # 2. Optional run-type relabel for the 07:00 morning briefing.
        if brussels_hour_provider is not None:
            run_type = _relabel_morning_briefing(
                run_type, brussels_hour_provider()
            )

        # 3. Gateway connectivity check. Disconnected → exit clean.
        if not gateway.is_connected():
            mode_detected: ModeDetected = "disconnected"
            duration = _duration_ms(started, now_provider())
            _safe_append(
                audit_repo,
                ScheduledRunAuditEntry(
                    run_id=run_id,
                    run_at=started,
                    run_type=run_type,
                    ibkr_account_id=ibkr_account_id,
                    mode_detected=mode_detected,
                    duration_ms=duration,
                    outcome="completed",
                    error_details_json=None,
                    next_scheduled_at=next_scheduled_at,
                ),
            )
            return OrchestratorResult(
                run_id=run_id,
                run_type=run_type,
                mode_detected=mode_detected,
                outcome="completed",
                duration_ms=duration,
            )

        # 4. Cold-start detection (Tasks 127 + 128).
        if ibkr_account_id is None:
            mode_detected = "cold_start"
        else:
            position_count = snapshot_counts.position_snapshot_count_for_account(
                ibkr_account_id
            )
            watchlist_count = snapshot_counts.watchlist_item_count_for_account(
                ibkr_account_id
            )
            if position_count == 0 and watchlist_count == 0:
                mode_detected = "cold_start"
            else:
                mode_detected = "normal"

        # 5. Task 128 onboarding gate.
        # First fire that detects cold_start: trigger the starter
        # seed (idempotent via storage-side UNIQUE constraint).
        if mode_detected == "cold_start" and ibkr_account_id is not None:
            if seed_runner is not None:
                try:
                    seed_runner.seed(ibkr_account_id)
                except Exception:  # noqa: BLE001 — boundary
                    logger.exception(
                        "starter watchlist seed failed for %s",
                        ibkr_account_id,
                    )

        # After the seed (or when state already exists), check
        # confirmation state. If unconfirmed, override the audit
        # row to ``awaiting_watchlist_confirmation`` per Task 128
        # product lock §3. On the very first fire that just
        # triggered the seed, the original ``cold_start`` label
        # stays — that's the documented sequence:
        # ``cold_start → awaiting_watchlist_confirmation → normal``.
        if (
            confirmation_state is not None
            and ibkr_account_id is not None
            and mode_detected != "cold_start"
        ):
            state = confirmation_state.get_state(ibkr_account_id)
            if state == "unconfirmed":
                mode_detected = "awaiting_watchlist_confirmation"

        # 6. Task 129 market-data fetch.
        # Only on normal fires that are also pre_briefing or
        # morning_briefing. Hourly delta fires never re-fetch — EOD
        # prices don't change intraday. The runner returns a small
        # dict folded into the audit row.
        market_data_details: dict[str, object] | None = None
        if (
            market_data_runner is not None
            and mode_detected == "normal"
            and run_type in ("pre_briefing", "morning_briefing")
            and ibkr_account_id is not None
        ):
            try:
                market_data_details = market_data_runner.run(
                    ibkr_account_id=ibkr_account_id, run_type=run_type
                )
            except Exception:  # noqa: BLE001 — boundary
                logger.exception("market_data_runner failed")
                market_data_details = {"error": "market_data_runner_exception"}

        duration = _duration_ms(started, now_provider())
        error_details_json: str | None = None
        if market_data_details is not None:
            import json as _json

            error_details_json = _json.dumps(
                {"market_data": market_data_details}
            )
        _safe_append(
            audit_repo,
            ScheduledRunAuditEntry(
                run_id=run_id,
                run_at=started,
                run_type=run_type,
                ibkr_account_id=ibkr_account_id,
                mode_detected=mode_detected,
                duration_ms=duration,
                outcome="completed",
                error_details_json=error_details_json,
                next_scheduled_at=next_scheduled_at,
            ),
        )
        return OrchestratorResult(
            run_id=run_id,
            run_type=run_type,
            mode_detected=mode_detected,
            outcome="completed",
            duration_ms=duration,
        )
    except Exception as exc:  # noqa: BLE001 — boundary
        logger.exception("orchestrator run failed")
        duration = _duration_ms(started, now_provider())
        _safe_append(
            audit_repo,
            ScheduledRunAuditEntry(
                run_id=run_id,
                run_at=started,
                run_type=run_type,
                ibkr_account_id=ibkr_account_id,
                mode_detected="disconnected",
                duration_ms=duration,
                outcome="error",
                error_details_json=json.dumps(
                    {"reason": "orchestrator_exception", "message": str(exc)}
                ),
                next_scheduled_at=next_scheduled_at,
            ),
        )
        return OrchestratorResult(
            run_id=run_id,
            run_type=run_type,
            mode_detected="disconnected",
            outcome="error",
            duration_ms=duration,
        )
    finally:
        lock.release()


def _duration_ms(start: datetime, now: datetime) -> int:
    return max(0, int((now - start).total_seconds() * 1000))


def _safe_append(
    audit_repo: SqlAlchemyScheduledRunAuditRepository,
    entry: ScheduledRunAuditEntry,
) -> None:
    """Persist the audit row; log + swallow on storage failure.

    The orchestrator can't usefully recover if storage is down — the
    only honest move is to log the failure and move on. APScheduler's
    next fire will try again.
    """

    try:
        audit_repo.append(entry)
    except Exception:  # noqa: BLE001 — boundary
        logger.exception("failed to persist scheduled-run audit row")
