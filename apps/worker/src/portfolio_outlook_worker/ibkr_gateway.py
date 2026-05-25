"""Task 126: worker-owned IBKR TWS session + two-tier mode detection.

The worker is the only component that opens a long-lived TWS API
session; the API reads worker-persisted state via the storage layer.
The gateway:

1. Connects via ``ib_insync.IB().connect(host, port, clientId=...)``.
2. Reads the managed account ID via ``managedAccounts()``.
3. Derives the prefix-based mode (``DU*`` / ``DF*`` → paper, anything
   else → live) and writes a ``mode_check_prefix`` audit row.
4. Runs a behavioural cross-check: requesting contract details for a
   contract type that only exists on live accounts. If the prefix and
   behavioural mode disagree the connection refuses with a Dutch
   error and the ``connect_refused`` audit row carries the reason.
5. On success writes ``connect_success`` and exposes
   ``fetch_account_summary()`` + ``fetch_positions()`` for the
   higher-level sync orchestrators (wired by Task 126b).

Every monetary value crosses the gateway boundary as ``Decimal``;
the gateway never returns ``float``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, Protocol, cast
from uuid import uuid4

from ai_trading_agent_storage import IbkrConnectionAuditRecord

logger = logging.getLogger(__name__)


AccountMode = Literal["paper", "live", "unknown"]

# Task 126 product lock §2 — prefix-derived mode is the primary
# detection mechanism; ``DU*`` / ``DF*`` are paper-account markers
# documented in the TWS API integration guide. Anything else → live.
_PAPER_PREFIXES = ("DU", "DF")


class _AuditRepoProtocol(Protocol):
    def append(
        self, record: IbkrConnectionAuditRecord
    ) -> object: ...


class IbClientProtocol(Protocol):
    """Structural subset of ``ib_insync.IB`` we depend on.

    Method signatures are intentionally permissive (``*args`` /
    ``**kwargs``, ``Any`` returns) so this Protocol accepts both the
    real ``ib_insync.IB`` (which uses ``float`` timeouts + extra
    kwargs + typed return collections) and the lightweight test
    fakes that don't depend on the SDK at import time.
    """

    def connect(self, *args: Any, **kwargs: Any) -> Any: ...

    def disconnect(self) -> Any: ...

    def isConnected(self) -> bool: ...

    def managedAccounts(self) -> list[str]: ...

    def reqContractDetails(self, contract: Any) -> list[Any]: ...

    def accountSummary(self, account: str = "") -> list[Any]: ...

    def positions(self, account: str = "") -> list[Any]: ...


@dataclass(frozen=True)
class CashSummaryRow:
    """One row of the IBKR account-summary table, Decimal-only."""

    tag: str  # e.g. "AvailableFunds", "NetLiquidationValue"
    currency: str
    value: Decimal


@dataclass(frozen=True)
class AccountSummary:
    """Aggregated cash-side snapshot returned by ``fetch_account_summary``."""

    rows: tuple[CashSummaryRow, ...]
    as_of: datetime


@dataclass(frozen=True)
class Position:
    """One position row returned by ``fetch_positions`` — Decimal-only."""

    conid: int | None
    symbol: str
    exchange: str | None
    currency: str
    quantity: Decimal
    avg_cost: Decimal
    as_of: datetime


@dataclass(frozen=True)
class IbkrConnectionResult:
    """Outcome of ``IbkrGateway.connect(...)``."""

    connected: bool
    account_id: str | None
    account_mode: AccountMode
    connection_id: str | None
    verified_at: datetime | None
    error_nl: str | None = None
    audit_ids: tuple[str, ...] = field(default_factory=tuple)


def _mode_from_prefix(account_id: str) -> AccountMode:
    """Task 126 §2 primary detection — prefix-derived mode."""

    normalised = (account_id or "").strip().upper()
    if not normalised:
        return "unknown"
    if normalised.startswith(_PAPER_PREFIXES):
        return "paper"
    return "live"


def _decimal_or_zero(value: object) -> Decimal:
    """Best-effort Decimal coercion that never falls back to ``float``.

    ``ib_insync`` returns numeric account-summary values as plain
    strings, so converting via the string form preserves precision.
    """

    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        try:
            return Decimal(value.strip() or "0")
        except (ArithmeticError, ValueError):
            return Decimal("0")
    return Decimal(str(value))


class IbkrGateway:
    """Worker-owned IBKR TWS session.

    Instantiate with ``ib_client_factory`` returning an object that
    satisfies :class:`IbClientProtocol` (in production, a freshly
    constructed ``ib_insync.IB``). The ``audit_repo`` is the
    durable storage repository; the gateway always writes audit rows
    when it has one, even on the failure paths.

    Example test wiring::

        gateway = IbkrGateway(
            ib_client_factory=lambda: FakeIB(),
            audit_repo=FakeAuditRepo(),
            clock=fixed_clock,
        )
    """

    def __init__(
        self,
        *,
        ib_client_factory: Callable[[], IbClientProtocol] | None = None,
        audit_repo: _AuditRepoProtocol | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._ib_client_factory = ib_client_factory or _default_ib_factory
        self._audit_repo = audit_repo
        self._clock = clock or (lambda: datetime.now(UTC))
        self._ib: IbClientProtocol | None = None
        self._account_id: str | None = None
        self._account_mode: AccountMode = "unknown"
        self._connection_id: str | None = None
        self._verified_at: datetime | None = None

    # ---- public surface ------------------------------------------

    def connect(
        self,
        *,
        host: str,
        port: int,
        client_id: int,
        account_id: str,
    ) -> IbkrConnectionResult:
        """Open the TWS session + run two-tier mode detection."""

        account_id = (account_id or "").strip()
        if not account_id:
            return self._refuse(
                account_id="",
                reason_nl=(
                    "IBKR_ACCOUNT_ID ontbreekt. Stel het account-ID in via "
                    "Instellingen of de WORKER_IBKR__ACCOUNT_ID env-variabele."
                ),
                audit_ids=(),
            )

        audit_ids: list[str] = []
        attempt_id = self._append_audit(
            ibkr_account_id=account_id,
            event_type="connect_attempt",
            account_mode_detected=None,
            connection_id=None,
            details={"host": host, "port": port, "client_id": client_id},
        )
        if attempt_id is not None:
            audit_ids.append(attempt_id)

        try:
            client = self._ib_client_factory()
            client.connect(host, port, clientId=client_id, readonly=True)
        except Exception as exc:  # noqa: BLE001 — boundary
            error_msg = str(exc)
            refused_id = self._append_audit(
                ibkr_account_id=account_id,
                event_type="connect_refused",
                account_mode_detected=None,
                connection_id=None,
                details={"reason": "tws_connect_failed", "message": error_msg},
            )
            if refused_id is not None:
                audit_ids.append(refused_id)
            logger.warning("IBKR connect failed: %s", error_msg)
            return IbkrConnectionResult(
                connected=False,
                account_id=account_id,
                account_mode="unknown",
                connection_id=None,
                verified_at=None,
                error_nl=(
                    "Kan geen verbinding maken met IBKR TWS. Controleer "
                    "host/port/client-id en of TWS draait."
                ),
                audit_ids=tuple(audit_ids),
            )

        managed = self._safe_managed_accounts(client)
        if account_id not in managed:
            client.disconnect()
            refused_id = self._append_audit(
                ibkr_account_id=account_id,
                event_type="connect_refused",
                account_mode_detected=None,
                connection_id=None,
                details={
                    "reason": "account_not_managed",
                    "managed_accounts": managed,
                },
            )
            if refused_id is not None:
                audit_ids.append(refused_id)
            return IbkrConnectionResult(
                connected=False,
                account_id=account_id,
                account_mode="unknown",
                connection_id=None,
                verified_at=None,
                error_nl=(
                    f"Account {account_id} is niet bereikbaar via de TWS "
                    "sessie. Controleer welk account in TWS is ingelogd."
                ),
                audit_ids=tuple(audit_ids),
            )

        prefix_mode = _mode_from_prefix(account_id)
        prefix_audit_id = self._append_audit(
            ibkr_account_id=account_id,
            event_type="mode_check_prefix",
            account_mode_detected=prefix_mode,
            connection_id=None,
            details={"account_id": account_id, "derived_from": "prefix"},
        )
        if prefix_audit_id is not None:
            audit_ids.append(prefix_audit_id)

        behavioural_mode = self._behavioural_mode_check(client)
        behavioural_audit_id = self._append_audit(
            ibkr_account_id=account_id,
            event_type="mode_check_behavioural",
            account_mode_detected=behavioural_mode,
            connection_id=None,
            details={"probe": "live_only_contract_details"},
        )
        if behavioural_audit_id is not None:
            audit_ids.append(behavioural_audit_id)

        if prefix_mode != behavioural_mode:
            client.disconnect()
            refused_id = self._append_audit(
                ibkr_account_id=account_id,
                event_type="connect_refused",
                account_mode_detected=prefix_mode,
                connection_id=None,
                details={
                    "reason": "mode_check_disagreement",
                    "prefix_mode": prefix_mode,
                    "behavioural_mode": behavioural_mode,
                },
            )
            if refused_id is not None:
                audit_ids.append(refused_id)
            return IbkrConnectionResult(
                connected=False,
                account_id=account_id,
                account_mode="unknown",
                connection_id=None,
                verified_at=None,
                error_nl=(
                    "IBKR account-modus check mislukt: prefix-detectie "
                    f"zegt {prefix_mode}, gedragsdetectie zegt "
                    f"{behavioural_mode}. Verbinding geweigerd."
                ),
                audit_ids=tuple(audit_ids),
            )

        connection_id = f"ibkr_{uuid4().hex[:12]}"
        verified_at = self._clock()
        success_id = self._append_audit(
            ibkr_account_id=account_id,
            event_type="connect_success",
            account_mode_detected=prefix_mode,
            connection_id=connection_id,
            details={"verified_at": verified_at.isoformat()},
        )
        if success_id is not None:
            audit_ids.append(success_id)

        self._ib = client
        self._account_id = account_id
        self._account_mode = prefix_mode
        self._connection_id = connection_id
        self._verified_at = verified_at

        return IbkrConnectionResult(
            connected=True,
            account_id=account_id,
            account_mode=prefix_mode,
            connection_id=connection_id,
            verified_at=verified_at,
            error_nl=None,
            audit_ids=tuple(audit_ids),
        )

    def disconnect(self) -> None:
        if self._ib is None:
            return
        try:
            self._ib.disconnect()
        finally:
            account_id = self._account_id or ""
            if account_id:
                self._append_audit(
                    ibkr_account_id=account_id,
                    event_type="disconnect",
                    account_mode_detected=self._account_mode,
                    connection_id=self._connection_id,
                    details=None,
                )
            self._ib = None
            self._account_id = None
            self._account_mode = "unknown"
            self._connection_id = None
            self._verified_at = None

    def is_connected(self) -> bool:
        if self._ib is None:
            return False
        try:
            return bool(self._ib.isConnected())
        except Exception:  # noqa: BLE001 — boundary
            return False

    def get_account_mode(self) -> AccountMode:
        """Live read of the connected mode (no caching of stale state).

        Task 126 product lock §2 mandates re-reading per call so a
        stale session never reports a confident mode after the
        underlying connection has dropped.
        """

        if not self.is_connected():
            return "unknown"
        return self._account_mode

    def fetch_account_summary(self) -> AccountSummary:
        """Pull the locked cash-summary rows as Decimals.

        Wired in 126b by the API ``/ibkr/sync/run`` handler via the
        worker-persistence indirection (the API never calls the
        gateway directly).
        """

        if self._ib is None:
            raise RuntimeError("IbkrGateway: not connected")
        rows: list[CashSummaryRow] = []
        account = self._account_id or ""
        for entry in self._ib.accountSummary(account):
            tag = str(getattr(entry, "tag", ""))
            currency = str(getattr(entry, "currency", "") or "")
            raw_value = getattr(entry, "value", None)
            rows.append(
                CashSummaryRow(
                    tag=tag,
                    currency=currency,
                    value=_decimal_or_zero(raw_value),
                )
            )
        return AccountSummary(rows=tuple(rows), as_of=self._clock())

    def fetch_positions(self) -> tuple[Position, ...]:
        """Pull every position row as Decimal-only."""

        if self._ib is None:
            raise RuntimeError("IbkrGateway: not connected")
        positions: list[Position] = []
        account = self._account_id or ""
        for raw in self._ib.positions(account):
            contract = getattr(raw, "contract", None)
            positions.append(
                Position(
                    conid=_int_or_none(getattr(contract, "conId", None)),
                    symbol=str(getattr(contract, "symbol", "") or ""),
                    exchange=_str_or_none(getattr(contract, "exchange", None)),
                    currency=str(getattr(contract, "currency", "") or ""),
                    quantity=_decimal_or_zero(getattr(raw, "position", None)),
                    avg_cost=_decimal_or_zero(getattr(raw, "avgCost", None)),
                    as_of=self._clock(),
                )
            )
        return tuple(positions)

    # ---- helpers --------------------------------------------------

    def _refuse(
        self,
        *,
        account_id: str,
        reason_nl: str,
        audit_ids: tuple[str, ...],
    ) -> IbkrConnectionResult:
        return IbkrConnectionResult(
            connected=False,
            account_id=account_id or None,
            account_mode="unknown",
            connection_id=None,
            verified_at=None,
            error_nl=reason_nl,
            audit_ids=audit_ids,
        )

    def _safe_managed_accounts(self, client: IbClientProtocol) -> list[str]:
        try:
            managed = client.managedAccounts()
        except Exception:  # noqa: BLE001 — boundary
            return []
        return [str(a).strip() for a in managed if str(a).strip()]

    def _behavioural_mode_check(
        self, client: IbClientProtocol
    ) -> AccountMode:
        """Probe a contract that only resolves on live accounts.

        ``reqContractDetails`` returns an empty list (or raises) on
        paper accounts for futures contracts on certain exchanges
        unavailable in paper. The exact contract is intentionally a
        seam — ``ib_insync.Future(symbol="MES", exchange="CME",
        lastTradeDateOrContractMonth="20990101")`` is a placeholder
        live-only probe that returns no details on paper. Tests
        inject a fake that returns either ``[]`` (paper) or a
        non-empty list (live) without hitting the network.
        """

        probe: object
        try:
            from ib_insync import Future

            probe = Future(
                symbol="MES",
                lastTradeDateOrContractMonth="20990101",
                exchange="CME",
            )
        except Exception:  # noqa: BLE001 — boundary
            probe = object()
        try:
            details = client.reqContractDetails(probe)
        except Exception:  # noqa: BLE001 — boundary
            return "paper"
        if details:
            return "live"
        return "paper"

    def _append_audit(
        self,
        *,
        ibkr_account_id: str,
        event_type: str,
        account_mode_detected: AccountMode | None,
        connection_id: str | None,
        details: dict[str, object] | None,
    ) -> str | None:
        if self._audit_repo is None:
            return None
        audit_id = f"icaudit_{uuid4().hex}"
        record = IbkrConnectionAuditRecord(
            audit_id=audit_id,
            event_at=self._clock(),
            ibkr_account_id=ibkr_account_id,
            event_type=event_type,
            account_mode_detected=account_mode_detected,
            connection_id=connection_id,
            details_json=None if details is None else json.dumps(details),
        )
        try:
            self._audit_repo.append(record)
        except Exception:  # noqa: BLE001 — boundary
            logger.exception("Failed to persist IBKR connection-audit row")
            return None
        return audit_id


def _default_ib_factory() -> IbClientProtocol:
    """Production factory: lazily import ``ib_insync`` to keep the
    module loadable in environments where the SDK isn't installed.

    The real ``IB`` class is cast to the structural Protocol — its
    concrete signatures (``float`` timeouts, named extras) are wider
    than what the gateway uses, so the cast is sound.
    """

    from ib_insync import IB

    return cast(IbClientProtocol, IB())  # type: ignore[no-untyped-call]


def _int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
