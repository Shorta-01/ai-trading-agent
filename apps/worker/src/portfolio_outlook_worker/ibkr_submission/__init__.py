"""Task 134: IBKR submission lifecycle (Stage 3 of the action flow).

This package owns the worker-side machinery that takes a
``user_approved`` Action Draft, re-runs the safety + behavioural gates,
builds an IB Insync ``Contract`` + ``Order``, calls ``placeOrder()``,
and tracks the reply-handshake state machine through to a terminal
status. Stage 3a (this PR) ships:

* ``safety_recheck`` — pure-function gate evaluator. Returns Ok or
  Blocked(reason) and never mutates a draft directly.
* ``order_builder`` — pure function that converts a draft + tick size
  to an ``ib_insync.Contract`` + ``ib_insync.Order``. The only place
  in the codebase that crosses the Decimal → float boundary.

Stage 3b adds the submitter + lifecycle handler + APScheduler sweep
job. Stage 3c adds the API + frontend surfaces.
"""

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

__all__ = [
    "LimitPriceNotOnTickSizeError",
    "RecentSubmissionRecord",
    "SubmissionBlockReason",
    "SubmissionGateResult",
    "TickSize",
    "build_ib_order",
    "evaluate_submission_gates",
    "round_to_tick_size",
]
