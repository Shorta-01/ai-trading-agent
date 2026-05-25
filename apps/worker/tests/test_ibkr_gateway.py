"""Task 126 worker IBKR gateway tests.

Covers the two-tier mode detection (prefix + behavioural) and the
audit-row writes that prove every connection-lifecycle event lands
in durable storage. Real ``ib_insync`` is never imported — every
test injects a fake client via ``ib_client_factory``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ai_trading_agent_storage import IbkrConnectionAuditRecord

from portfolio_outlook_worker.ibkr_gateway import (
    IbkrConnectionResult,
    IbkrGateway,
    _mode_from_prefix,
)


class _FakeContractDetails:
    """Marker object returned by the live-only behavioural probe."""


class _FakeIB:
    """Minimal stand-in for ``ib_insync.IB`` for tests."""

    def __init__(
        self,
        *,
        managed_accounts: list[str] | None = None,
        behavioural_returns_details: bool = False,
        connect_raises: BaseException | None = None,
        managed_accounts_raises: BaseException | None = None,
    ) -> None:
        self._managed = managed_accounts or []
        self._behavioural_details = behavioural_returns_details
        self._connect_raises = connect_raises
        self._managed_raises = managed_accounts_raises
        self.connected = False
        self.connect_calls: list[dict[str, Any]] = []
        self.req_contract_details_calls = 0
        self.disconnect_calls = 0

    def connect(
        self,
        host: str,
        port: int,
        clientId: int,
        readonly: bool = False,
        timeout: int = 4,
    ) -> object:
        if self._connect_raises is not None:
            raise self._connect_raises
        self.connect_calls.append(
            {"host": host, "port": port, "clientId": clientId, "readonly": readonly}
        )
        self.connected = True
        return self

    def disconnect(self) -> object:
        self.connected = False
        self.disconnect_calls += 1
        return self

    def isConnected(self) -> bool:
        return self.connected

    def managedAccounts(self) -> list[str]:
        if self._managed_raises is not None:
            raise self._managed_raises
        return list(self._managed)

    def reqContractDetails(self, contract: object) -> list[object]:
        self.req_contract_details_calls += 1
        return [_FakeContractDetails()] if self._behavioural_details else []

    def accountSummary(self, account: str = "") -> list[object]:
        return []

    def positions(self, account: str = "") -> list[object]:
        return []


class _FakeAuditRepo:
    def __init__(self) -> None:
        self.records: list[IbkrConnectionAuditRecord] = []

    def append(self, record: IbkrConnectionAuditRecord) -> object:
        self.records.append(record)
        return record


_FIXED_NOW = datetime(2026, 5, 25, 7, 0, 0, tzinfo=UTC)


def _build_gateway(
    *,
    ib: _FakeIB,
    audit: _FakeAuditRepo | None = None,
) -> IbkrGateway:
    return IbkrGateway(
        ib_client_factory=lambda: ib,
        audit_repo=audit,
        clock=lambda: _FIXED_NOW,
    )


# ---- mode-from-prefix unit ---------------------------------------


def test_mode_from_prefix_paper_for_DU_account() -> None:
    assert _mode_from_prefix("DU1234567") == "paper"


def test_mode_from_prefix_paper_for_DF_account() -> None:
    assert _mode_from_prefix("DF999") == "paper"


def test_mode_from_prefix_live_for_U_account() -> None:
    assert _mode_from_prefix("U7654321") == "live"


def test_mode_from_prefix_unknown_for_empty() -> None:
    assert _mode_from_prefix("") == "unknown"


def test_mode_from_prefix_is_case_insensitive() -> None:
    assert _mode_from_prefix("du1234567") == "paper"
    assert _mode_from_prefix("u7654321") == "live"


# ---- happy-path connect ------------------------------------------


def test_connect_paper_success_writes_full_audit_chain() -> None:
    ib = _FakeIB(
        managed_accounts=["DU1234567"],
        behavioural_returns_details=False,  # paper account → no live-only details
    )
    audit = _FakeAuditRepo()
    gateway = _build_gateway(ib=ib, audit=audit)

    result = gateway.connect(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        account_id="DU1234567",
    )

    assert isinstance(result, IbkrConnectionResult)
    assert result.connected is True
    assert result.account_id == "DU1234567"
    assert result.account_mode == "paper"
    assert result.connection_id is not None
    assert result.verified_at == _FIXED_NOW
    assert result.error_nl is None

    event_types = [r.event_type for r in audit.records]
    assert event_types == [
        "connect_attempt",
        "mode_check_prefix",
        "mode_check_behavioural",
        "connect_success",
    ]

    prefix_row = audit.records[1]
    assert prefix_row.account_mode_detected == "paper"
    assert prefix_row.ibkr_account_id == "DU1234567"

    behavioural_row = audit.records[2]
    assert behavioural_row.account_mode_detected == "paper"

    success_row = audit.records[3]
    assert success_row.account_mode_detected == "paper"
    assert success_row.connection_id == result.connection_id

    assert ib.req_contract_details_calls == 1
    assert ib.connect_calls[0]["readonly"] is True
    assert gateway.is_connected() is True
    assert gateway.get_account_mode() == "paper"


def test_connect_live_success_writes_full_audit_chain() -> None:
    ib = _FakeIB(
        managed_accounts=["U7654321"],
        behavioural_returns_details=True,  # live → live-only contract resolves
    )
    audit = _FakeAuditRepo()
    gateway = _build_gateway(ib=ib, audit=audit)

    result = gateway.connect(
        host="127.0.0.1",
        port=7496,
        client_id=1,
        account_id="U7654321",
    )

    assert result.connected is True
    assert result.account_mode == "live"
    assert audit.records[1].account_mode_detected == "live"
    assert audit.records[2].account_mode_detected == "live"


# ---- failure paths -----------------------------------------------


def test_connect_refuses_when_prefix_and_behavioural_disagree() -> None:
    """Behavioural says live but prefix says paper → refuse."""

    ib = _FakeIB(
        managed_accounts=["DU1234567"],
        behavioural_returns_details=True,  # → behavioural mode = live
    )
    audit = _FakeAuditRepo()
    gateway = _build_gateway(ib=ib, audit=audit)

    result = gateway.connect(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        account_id="DU1234567",  # prefix-paper
    )

    assert result.connected is False
    assert result.error_nl is not None
    assert "mislukt" in result.error_nl
    event_types = [r.event_type for r in audit.records]
    assert event_types == [
        "connect_attempt",
        "mode_check_prefix",
        "mode_check_behavioural",
        "connect_refused",
    ]
    assert ib.disconnect_calls == 1
    refused = audit.records[3]
    assert refused.event_type == "connect_refused"
    assert refused.details_json is not None
    details = json.loads(refused.details_json)
    assert details["reason"] == "mode_check_disagreement"
    assert details["prefix_mode"] == "paper"
    assert details["behavioural_mode"] == "live"


def test_connect_refuses_when_account_id_missing() -> None:
    ib = _FakeIB(managed_accounts=["DU1234567"])
    audit = _FakeAuditRepo()
    gateway = _build_gateway(ib=ib, audit=audit)

    result = gateway.connect(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        account_id="",
    )
    assert result.connected is False
    assert "IBKR_ACCOUNT_ID" in (result.error_nl or "")
    # No audit rows because we never even reached the connect_attempt
    # branch (the gateway requires a non-empty account_id to write
    # any row, since the audit table requires it as NOT NULL).
    assert audit.records == []


def test_connect_refuses_when_account_not_managed() -> None:
    ib = _FakeIB(managed_accounts=["DU9999999"])
    audit = _FakeAuditRepo()
    gateway = _build_gateway(ib=ib, audit=audit)

    result = gateway.connect(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        account_id="DU1234567",
    )
    assert result.connected is False
    assert "niet bereikbaar" in (result.error_nl or "")
    event_types = [r.event_type for r in audit.records]
    assert event_types == ["connect_attempt", "connect_refused"]
    refused = audit.records[1]
    details = json.loads(refused.details_json or "{}")
    assert details["reason"] == "account_not_managed"


def test_connect_refuses_when_tws_connect_raises() -> None:
    ib = _FakeIB(connect_raises=ConnectionRefusedError("nope"))
    audit = _FakeAuditRepo()
    gateway = _build_gateway(ib=ib, audit=audit)

    result = gateway.connect(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        account_id="DU1234567",
    )
    assert result.connected is False
    assert "TWS" in (result.error_nl or "")
    event_types = [r.event_type for r in audit.records]
    assert event_types == ["connect_attempt", "connect_refused"]
    refused = audit.records[1]
    details = json.loads(refused.details_json or "{}")
    assert details["reason"] == "tws_connect_failed"


# ---- disconnect / is_connected -----------------------------------


def test_disconnect_writes_audit_row_and_clears_state() -> None:
    ib = _FakeIB(managed_accounts=["DU1234567"])
    audit = _FakeAuditRepo()
    gateway = _build_gateway(ib=ib, audit=audit)
    gateway.connect(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        account_id="DU1234567",
    )
    audit.records.clear()

    gateway.disconnect()

    assert gateway.is_connected() is False
    assert gateway.get_account_mode() == "unknown"
    assert [r.event_type for r in audit.records] == ["disconnect"]


def test_get_account_mode_returns_unknown_when_not_connected() -> None:
    ib = _FakeIB()
    gateway = _build_gateway(ib=ib)
    assert gateway.get_account_mode() == "unknown"
