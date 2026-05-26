"""Task 133: action_draft package.

The Action Draft is the User To-Do tier of the three-stage flow
(System Advice → User To-Do → IBKR Submission). It's a prefilled
IBKR-format order proposal derived from a non-Geblokkeerd Decision
Package + IBKR cash/position context. Editable until the user
approves; after that it's immutable.

This package owns:

* ``composer`` — pure functions that mint ``ActionDraftEntry`` rows
  from either a Decision Package (cash-aware sizing) or user-supplied
  fields (no sizing logic).
* ``supersede_check`` — given a fresh Decision Package, flag any
  pending Action Draft for the same (account, conid) as superseded
  (flag-never-modify per Task 133 product lock §6).
"""

from portfolio_outlook_worker.action_draft.composer import (
    InsufficientCashError,
    NoPositionToSellError,
    UnsupportedDecisionPackageLabelError,
    compose_action_draft_from_decision_package,
    compose_action_draft_user_supplied,
)
from portfolio_outlook_worker.action_draft.supersede_check import (
    SupersedeCheckResult,
    mark_superseded_drafts,
)

__all__ = [
    "InsufficientCashError",
    "NoPositionToSellError",
    "UnsupportedDecisionPackageLabelError",
    "compose_action_draft_from_decision_package",
    "compose_action_draft_user_supplied",
    "mark_superseded_drafts",
    "SupersedeCheckResult",
]
