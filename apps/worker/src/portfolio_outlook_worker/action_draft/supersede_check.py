"""Task 133: supersede-check for Action Drafts.

Implements the "flag, never modify" rule (Task 133 product lock §6):
when a later scheduled run produces a new Decision Package for an
asset that already has a pending Action Draft (``proposed`` or
``edited``), the draft is **not** mutated. Instead, its
``superseded_by_decision_package_id`` flag is set so the UI can render
the *"Advies gewijzigd"* badge. The user keeps full ownership of the
draft — they can still approve it, dismiss it, or edit it on the new
basis.

Pure function — no I/O beyond the injected repositories. Per-asset
failures are isolated; the function records and returns counts but
never raises through to the orchestrator (per Task 132 "per-asset
failures never crash the run" doctrine).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from ai_trading_agent_storage import (
    ActionDraftEntry,
    ActionDraftStateTransitionError,
    DecisionPackageEntry,
)

logger = logging.getLogger(__name__)


class _ActionDraftRepoProtocol(Protocol):
    def list_pending_for_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> tuple[ActionDraftEntry, ...]: ...

    def mark_superseded(
        self,
        *,
        action_draft_id: str,
        by_decision_package_id: str,
        marked_at: datetime,
    ) -> ActionDraftEntry: ...


@dataclass(frozen=True)
class SupersedeCheckResult:
    """Outcome of one supersede-check pass.

    ``marked_count`` is the number of drafts flagged. ``skipped_count``
    is drafts that were pending but where the new package's audit hash
    matched an existing flag (idempotent re-runs). ``error_count``
    counts per-draft failures — each is logged but the loop continues.
    """

    marked_count: int
    skipped_count: int
    error_count: int
    marked_draft_ids: tuple[str, ...] = field(default_factory=tuple)


def mark_superseded_drafts(
    *,
    decision_packages: Iterable[DecisionPackageEntry],
    action_draft_repo: _ActionDraftRepoProtocol,
    now: datetime | None = None,
) -> SupersedeCheckResult:
    """Flag pending drafts that are superseded by newer Decision Packages.

    For each newly-composed package, look up pending drafts on the same
    (account, conid). For each such draft:

    * If its ``decision_package_id`` is already the new package's id,
      skip (idempotent — same package processed twice).
    * If its ``superseded_by_decision_package_id`` is already the new
      package's id, skip (we already marked it).
    * Otherwise, call ``mark_superseded`` to write the flag + one
      audit row.

    Per-draft failures are caught and logged. The function never raises
    through to the orchestrator.
    """

    marked = 0
    skipped = 0
    errored = 0
    marked_ids: list[str] = []
    when = now or datetime.now(UTC)

    for package in decision_packages:
        try:
            pending = action_draft_repo.list_pending_for_conid(
                ibkr_account_id=package.ibkr_account_id,
                conid=package.conid,
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "supersede_check: list_pending_for_conid failed for %s/%s",
                package.ibkr_account_id,
                package.conid,
            )
            errored += 1
            continue

        for draft in pending:
            if draft.decision_package_id == package.decision_package_id:
                # The draft already references this exact package — it
                # IS this package, not superseded by it.
                skipped += 1
                continue
            if (
                draft.superseded_by_decision_package_id
                == package.decision_package_id
            ):
                skipped += 1
                continue
            try:
                action_draft_repo.mark_superseded(
                    action_draft_id=draft.action_draft_id,
                    by_decision_package_id=package.decision_package_id,
                    marked_at=when,
                )
                marked += 1
                marked_ids.append(draft.action_draft_id)
            except ActionDraftStateTransitionError:
                # Race: draft was dismissed/deleted/approved between
                # the list and the mark — that's exactly the safety
                # rail. Count as skipped.
                skipped += 1
            except Exception:  # noqa: BLE001 — boundary
                logger.exception(
                    "supersede_check: mark_superseded failed for %s",
                    draft.action_draft_id,
                )
                errored += 1

    return SupersedeCheckResult(
        marked_count=marked,
        skipped_count=skipped,
        error_count=errored,
        marked_draft_ids=tuple(marked_ids),
    )
