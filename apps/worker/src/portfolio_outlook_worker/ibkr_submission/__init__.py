"""Task 134: IBKR submission lifecycle (Stage 3 of the action flow).

This package owns the worker-side machinery that takes a
``user_approved`` Action Draft, re-runs the safety + behavioural gates,
builds an IB Insync ``Contract`` + ``Order``, calls ``placeOrder()``,
and tracks the reply-handshake state machine through to a terminal
status. Stages:

* 3a (Task 134a) — ``safety_recheck`` + ``order_builder`` pure
  functions; storage + dataclasses + repos.
* 3b (Task 134b) — ``submitter`` + ``lifecycle_handler`` +
  ``submission_sweep``. The submitter calls ``placeOrder()`` through
  an injected adapter; the lifecycle_handler maps IBKR callbacks to
  draft status transitions; the sweep is the once-per-minute job.
* 3c (Task 134c) — API routes + frontend tabs.
"""

from portfolio_outlook_worker.ibkr_submission.lifecycle_handler import (
    CancellationEvent,
    CommissionReportEvent,
    FillEvent,
    LifecycleEvent,
    LifecycleHandler,
    LifecycleHandlerResult,
    OrderStatusEvent,
    RejectionEvent,
    map_raw_status_to_lifecycle_status,
)
from portfolio_outlook_worker.ibkr_submission.order_builder import (
    LimitPriceNotOnTickSizeError,
    TickSize,
    build_ib_order,
    round_to_tick_size,
)
from portfolio_outlook_worker.ibkr_submission.safety_recheck import (
    RecentSubmissionRecord,
    SubmissionBlockReason,
    SubmissionGateResult,
    evaluate_submission_gates,
)
from portfolio_outlook_worker.ibkr_submission.submission_sweep import (
    BlockedDraftRecord,
    BrusselsBusinessHoursMarket,
    SubmissionSweep,
    SubmissionSweepResult,
    SubmittedDraftRecord,
    SweepMode,
)
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrConnectionLostError,
    IbkrSubmitProtocol,
    IbkrSubmitter,
    IbkrTickSizeFetchError,
    SubmissionResult,
    SubmittedTrade,
)

__all__ = [
    "BlockedDraftRecord",
    "BrusselsBusinessHoursMarket",
    "CancellationEvent",
    "CommissionReportEvent",
    "FillEvent",
    "IbkrConnectionLostError",
    "IbkrSubmitProtocol",
    "IbkrSubmitter",
    "IbkrTickSizeFetchError",
    "LifecycleEvent",
    "LifecycleHandler",
    "LifecycleHandlerResult",
    "LimitPriceNotOnTickSizeError",
    "OrderStatusEvent",
    "RecentSubmissionRecord",
    "RejectionEvent",
    "SubmissionBlockReason",
    "SubmissionGateResult",
    "SubmissionResult",
    "SubmissionSweep",
    "SubmissionSweepResult",
    "SubmittedDraftRecord",
    "SubmittedTrade",
    "SweepMode",
    "TickSize",
    "build_ib_order",
    "evaluate_submission_gates",
    "map_raw_status_to_lifecycle_status",
    "round_to_tick_size",
]
