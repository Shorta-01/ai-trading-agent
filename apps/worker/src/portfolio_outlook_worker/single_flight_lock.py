"""Task 127: single-flight lock abstraction.

Task 127 product lock §3 — only one orchestrator run may execute at a
time. Production uses Postgres ``pg_advisory_lock``; tests use a
process-local mutex so the locking semantic can be exercised without
a live Postgres instance.

Both implementations satisfy :class:`SingleFlightLockProtocol`:

* ``try_acquire()`` returns ``True`` when the lock was claimed,
  ``False`` when another runner is already holding it. Never blocks.
* ``release()`` is idempotent — calling it when not held is a no-op.

The locked key is a fixed bigint hash so two worker processes on the
same Postgres database serialise their fires.
"""

from __future__ import annotations

import logging
import threading
from typing import Protocol

logger = logging.getLogger(__name__)


# Stable lock key for the orchestrator's advisory lock. Two-byte hash
# of the locked string "portfolio_outlook_orchestrator" — fits inside
# Postgres bigint range.
ORCHESTRATOR_LOCK_KEY = 0x504F5F4F5243484F  # "PO_ORCHO" packed as bigint


class SingleFlightLockProtocol(Protocol):
    """Locked surface shared by production + test implementations."""

    def try_acquire(self) -> bool: ...

    def release(self) -> None: ...


class InMemoryLock:
    """Process-local mutex used by the worker test suite.

    Hands the lock out to the first caller that asks; subsequent
    callers get ``False`` until the holder releases.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        return self._lock.acquire(blocking=False)

    def release(self) -> None:
        if self._lock.locked():
            self._lock.release()


class PostgresAdvisoryLock:
    """Production lock backed by ``pg_advisory_lock``.

    Wraps a SQLAlchemy ``Connection`` (provided by the caller). The
    lock is session-scoped — it lives for the duration of the
    underlying Postgres connection, so the orchestrator must keep
    the same connection open between ``try_acquire`` and
    ``release``.
    """

    def __init__(self, connection: object) -> None:
        self._connection = connection
        self._held = False

    def try_acquire(self) -> bool:
        from sqlalchemy import text

        try:
            result = self._connection.execute(  # type: ignore[attr-defined]
                text("SELECT pg_try_advisory_lock(:k)"),
                {"k": ORCHESTRATOR_LOCK_KEY},
            ).scalar()
        except Exception:  # noqa: BLE001 — boundary
            logger.exception("pg_try_advisory_lock failed")
            return False
        acquired = bool(result)
        self._held = acquired
        return acquired

    def release(self) -> None:
        if not self._held:
            return
        from sqlalchemy import text

        try:
            self._connection.execute(  # type: ignore[attr-defined]
                text("SELECT pg_advisory_unlock(:k)"),
                {"k": ORCHESTRATOR_LOCK_KEY},
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception("pg_advisory_unlock failed")
        finally:
            self._held = False
