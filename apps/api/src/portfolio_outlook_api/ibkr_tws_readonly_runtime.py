from __future__ import annotations

from dataclasses import dataclass

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_tws_readonly_adapter import (
    IbkrTwsReadonlyAdapterError,
    IbkrTwsReadonlyClient,
)


@dataclass(frozen=True)
class IbkrTwsReadonlyRuntimeGateResult:
    status: str
    status_nl: str
    allowed: bool
    allowed_nl: str
    blocked: bool
    blocked_reasons: tuple[str, ...]
    help_nl: str
    next_step_nl: str
    runtime_connection_allowed: bool
    runtime_connection_blocked_reason: str | None
    manual_status_check_allowed: bool
    manual_status_check_allowed_nl: str


@dataclass(frozen=True)
class IbkrTwsReadonlyRuntimeCheckResult:
    status: str
    status_nl: str
    allowed: bool
    allowed_nl: str
    blocked: bool
    blocked_reasons: tuple[str, ...]
    help_nl: str
    next_step_nl: str
    connection_status: str
    account_mode_status: str
    account_mode: str | None
    session_status_reason: str
    session_check_source: str
    runtime_connection_allowed: bool
    runtime_connection_blocked_reason: str | None
    manual_status_check_allowed: bool
    manual_status_check_allowed_nl: str
    connect_attempted: bool
    disconnect_attempted: bool
    disconnect_error_ignored: bool
    actions_allowed: bool = False
    suggestions_allowed: bool = False
    action_drafts_allowed: bool = False
    orders_allowed: bool = False
    order_submission_allowed: bool = False
    order_modification_allowed: bool = False
    order_cancellation_allowed: bool = False
    can_submit_orders: bool = False
    safe_for_orders: bool = False
    blocks_orders: bool = True


@dataclass(frozen=True)
class IbkrTwsReadonlyStatusCheckReadinessResult:
    status: str
    status_nl: str
    ready: bool
    ready_nl: str
    blocked: bool
    blocked_reasons: tuple[str, ...]
    blocking_summary_nl: str
    help_nl: str
    next_step_nl: str
    endpoint: str
    method: str
    runtime_enabled: bool
    adapter_enabled: bool
    real_client_enabled: bool
    host_configured: bool
    port_configured: bool
    client_id_configured: bool
    paper_only_mode: bool
    expected_account_mode: str | None
    runtime_client_available: bool
    runtime_connection_allowed: bool
    runtime_connection_blocked_reason: str | None
    manual_status_check_allowed: bool
    manual_status_check_allowed_nl: str
    connect_attempted: bool
    disconnect_attempted: bool
    actions_allowed: bool = False
    suggestions_allowed: bool = False
    action_drafts_allowed: bool = False
    orders_allowed: bool = False
    order_submission_allowed: bool = False
    order_modification_allowed: bool = False
    order_cancellation_allowed: bool = False
    can_submit_orders: bool = False
    safe_for_orders: bool = False
    blocks_orders: bool = True


def check_tws_readonly_runtime_preflight(
    settings: Settings,
    runtime_client: IbkrTwsReadonlyClient | None,
) -> IbkrTwsReadonlyRuntimeGateResult:
    blocked_reasons: list[str] = []

    if not settings.ibkr_tws_readonly_runtime_enabled:
        blocked_reasons.append("runtime_disabled")
    if not settings.ibkr_status_check_enabled:
        blocked_reasons.append("status_check_disabled")
    if not settings.ibkr_enabled:
        blocked_reasons.append("ibkr_disabled")
    if not settings.ibkr_tws_readonly_adapter_enabled:
        blocked_reasons.append("adapter_disabled")
    if not settings.ibkr_tws_readonly_real_client_enabled:
        blocked_reasons.append("real_client_disabled")
    if not settings.paper_only_mode:
        blocked_reasons.append("paper_only_required")

    expected_mode = _normalize_mode(settings.ibkr_expected_environment)
    if expected_mode != "paper":
        blocked_reasons.append("expected_account_mode_not_paper")

    if settings.ibkr_sync_host is None:
        blocked_reasons.append("missing_host")
    if settings.ibkr_sync_port is None:
        blocked_reasons.append("missing_port")
    if settings.ibkr_sync_client_id is None:
        blocked_reasons.append("missing_client_id")
    if runtime_client is None:
        blocked_reasons.append("missing_runtime_client")

    if blocked_reasons:
        first = blocked_reasons[0]
        return IbkrTwsReadonlyRuntimeGateResult(
            status=first,
            status_nl=_reason_nl(first),
            allowed=False,
            allowed_nl="Handmatige read-only statuscontrole geblokkeerd",
            blocked=True,
            blocked_reasons=tuple(blocked_reasons),
            help_nl="Runtime blijft veilig uitgeschakeld zonder expliciete preflight-groen.",
            next_step_nl="Los alle blockers op en blijf in paper-only handmatige modus.",
            runtime_connection_allowed=False,
            runtime_connection_blocked_reason=first,
            manual_status_check_allowed=False,
            manual_status_check_allowed_nl="Geblokkeerd",
        )

    return IbkrTwsReadonlyRuntimeGateResult(
        status="manual_status_check_ready",
        status_nl="Handmatige read-only statuscontrole klaar",
        allowed=True,
        allowed_nl="Handmatige read-only statuscontrole toegestaan",
        blocked=False,
        blocked_reasons=(),
        help_nl="Alleen één handmatige statuscontrole met injected testclient.",
        next_step_nl="Voer éénmalig connect/check/disconnect uit.",
        runtime_connection_allowed=True,
        runtime_connection_blocked_reason=None,
        manual_status_check_allowed=True,
        manual_status_check_allowed_nl="Toegestaan",
    )


def run_manual_tws_readonly_status_check(
    settings: Settings,
    runtime_client: IbkrTwsReadonlyClient | None,
) -> IbkrTwsReadonlyRuntimeCheckResult:
    gate = check_tws_readonly_runtime_preflight(settings, runtime_client)
    if runtime_client is None or not gate.allowed:
        return _blocked_result(gate)

    connect_attempted = False
    disconnect_attempted = False
    disconnect_error_ignored = False

    def _disconnect() -> tuple[bool, bool]:
        try:
            runtime_client.disconnect()
            return True, False
        except Exception:
            return True, True

    try:
        connect_attempted = True
        runtime_client.connect_readonly(settings.ibkr_connection_timeout_seconds)

        account_mode = _normalize_mode(runtime_client.get_account_mode())
        expected_mode = _normalize_mode(settings.ibkr_expected_environment)

        if account_mode is None:
            result = _result_from_gate(
                gate,
                status="unknown_account_mode",
                status_nl="Onbekende accountmodus",
                connection_status="connected_readonly",
                account_mode_status="unknown",
                account_mode=None,
                session_status_reason="unknown_account_mode",
                connect_attempted=connect_attempted,
                disconnect_attempted=False,
                disconnect_error_ignored=False,
            )
            disconnect_attempted, disconnect_error_ignored = _disconnect()
            return _result_from_gate(
                gate,
                status=result.status,
                status_nl=result.status_nl,
                connection_status=result.connection_status,
                account_mode_status=result.account_mode_status,
                account_mode=result.account_mode,
                session_status_reason=result.session_status_reason,
                connect_attempted=connect_attempted,
                disconnect_attempted=disconnect_attempted,
                disconnect_error_ignored=disconnect_error_ignored,
            )

        if account_mode != expected_mode:
            result = _result_from_gate(
                gate,
                status="wrong_account_mode",
                status_nl="Verkeerde accountmodus",
                connection_status="connected_wrong_account_mode",
                account_mode_status="mismatch",
                account_mode=account_mode,
                session_status_reason="wrong_account_mode",
                connect_attempted=connect_attempted,
                disconnect_attempted=False,
                disconnect_error_ignored=False,
            )
            disconnect_attempted, disconnect_error_ignored = _disconnect()
            return _result_from_gate(
                gate,
                status=result.status,
                status_nl=result.status_nl,
                connection_status=result.connection_status,
                account_mode_status=result.account_mode_status,
                account_mode=result.account_mode,
                session_status_reason=result.session_status_reason,
                connect_attempted=connect_attempted,
                disconnect_attempted=disconnect_attempted,
                disconnect_error_ignored=disconnect_error_ignored,
            )

        result = _result_from_gate(
            gate,
            status="manual_status_check_completed",
            status_nl="Handmatige read-only statuscontrole uitgevoerd",
            connection_status="connected_readonly",
            account_mode_status="match",
            account_mode=account_mode,
            session_status_reason="manual_status_check_completed",
            connect_attempted=connect_attempted,
            disconnect_attempted=False,
            disconnect_error_ignored=False,
        )
        disconnect_attempted, disconnect_error_ignored = _disconnect()
        return _result_from_gate(
            gate,
            status=result.status,
            status_nl=result.status_nl,
            connection_status=result.connection_status,
            account_mode_status=result.account_mode_status,
            account_mode=result.account_mode,
            session_status_reason=result.session_status_reason,
            connect_attempted=connect_attempted,
            disconnect_attempted=disconnect_attempted,
            disconnect_error_ignored=disconnect_error_ignored,
        )
    except TimeoutError:
        result = _result_from_gate(
            gate,
            status="timeout",
            status_nl="Verbindingstime-out",
            connection_status="connection_failed",
            account_mode_status="unknown",
            account_mode=None,
            session_status_reason="timeout",
            connect_attempted=connect_attempted,
            disconnect_attempted=False,
            disconnect_error_ignored=False,
        )
        disconnect_attempted, disconnect_error_ignored = _disconnect()
        return _result_from_gate(
            gate,
            status=result.status,
            status_nl=result.status_nl,
            connection_status=result.connection_status,
            account_mode_status=result.account_mode_status,
            account_mode=result.account_mode,
            session_status_reason=result.session_status_reason,
            connect_attempted=connect_attempted,
            disconnect_attempted=disconnect_attempted,
            disconnect_error_ignored=disconnect_error_ignored,
        )
    except IbkrTwsReadonlyAdapterError as error:
        reason = _map_adapter_error_code(error.code)
        result = _result_from_gate(
            gate,
            status=reason,
            status_nl=_reason_nl(reason),
            connection_status=(
                reason
                if reason
                in {"authentication_required", "pacing_limited", "connection_failed"}
                else "unknown"
            ),
            account_mode_status="unknown",
            account_mode=None,
            session_status_reason=reason,
            connect_attempted=connect_attempted,
            disconnect_attempted=False,
            disconnect_error_ignored=False,
        )
        disconnect_attempted, disconnect_error_ignored = _disconnect()
        return _result_from_gate(
            gate,
            status=result.status,
            status_nl=result.status_nl,
            connection_status=result.connection_status,
            account_mode_status=result.account_mode_status,
            account_mode=result.account_mode,
            session_status_reason=result.session_status_reason,
            connect_attempted=connect_attempted,
            disconnect_attempted=disconnect_attempted,
            disconnect_error_ignored=disconnect_error_ignored,
        )
    except Exception:
        result = _result_from_gate(
            gate,
            status="unexpected_client_error",
            status_nl="Onverwachte clientfout",
            connection_status="unknown",
            account_mode_status="unknown",
            account_mode=None,
            session_status_reason="unexpected_client_error",
            connect_attempted=connect_attempted,
            disconnect_attempted=False,
            disconnect_error_ignored=False,
        )
        disconnect_attempted, disconnect_error_ignored = _disconnect()
        return _result_from_gate(
            gate,
            status=result.status,
            status_nl=result.status_nl,
            connection_status=result.connection_status,
            account_mode_status=result.account_mode_status,
            account_mode=result.account_mode,
            session_status_reason=result.session_status_reason,
            connect_attempted=connect_attempted,
            disconnect_attempted=disconnect_attempted,
            disconnect_error_ignored=disconnect_error_ignored,
        )


def _blocked_result(gate: IbkrTwsReadonlyRuntimeGateResult) -> IbkrTwsReadonlyRuntimeCheckResult:
    return IbkrTwsReadonlyRuntimeCheckResult(
        status=gate.status,
        status_nl=gate.status_nl,
        allowed=gate.allowed,
        allowed_nl=gate.allowed_nl,
        blocked=gate.blocked,
        blocked_reasons=gate.blocked_reasons,
        help_nl=gate.help_nl,
        next_step_nl=gate.next_step_nl,
        connection_status="configured_not_connected",
        account_mode_status="unknown",
        account_mode=None,
        session_status_reason=gate.status,
        session_check_source="manual_tws_readonly_runtime_gate",
        runtime_connection_allowed=gate.runtime_connection_allowed,
        runtime_connection_blocked_reason=gate.runtime_connection_blocked_reason,
        manual_status_check_allowed=gate.manual_status_check_allowed,
        manual_status_check_allowed_nl=gate.manual_status_check_allowed_nl,
        connect_attempted=False,
        disconnect_attempted=False,
        disconnect_error_ignored=False,
    )


def build_manual_tws_readonly_status_check_readiness(
    settings: Settings,
    runtime_client: IbkrTwsReadonlyClient | None,
) -> IbkrTwsReadonlyStatusCheckReadinessResult:
    gate = check_tws_readonly_runtime_preflight(settings, runtime_client)
    expected_mode = _normalize_mode(settings.ibkr_expected_environment)
    status = (
        "manual_status_check_ready_for_test_client"
        if gate.allowed
        else "manual_status_check_blocked"
    )
    status_nl = (
        "Handmatige read-only statuscontrole klaar voor testclient"
        if gate.allowed
        else "Handmatige read-only statuscontrole geblokkeerd"
    )
    summary = (
        "Geen blokkades; alleen handmatige testclient-controle toegestaan"
        if gate.allowed
        else ", ".join(_reason_nl(reason) for reason in gate.blocked_reasons)
    )
    return IbkrTwsReadonlyStatusCheckReadinessResult(
        status=status,
        status_nl=status_nl,
        ready=gate.allowed,
        ready_nl="Klaar" if gate.allowed else "Niet klaar",
        blocked=gate.blocked,
        blocked_reasons=gate.blocked_reasons,
        blocking_summary_nl=summary,
        help_nl="Alleen diagnostiek; geen verbinding geprobeerd",
        next_step_nl="Gebruik alleen veilige testinjectie; brokeracties blijven geblokkeerd",
        endpoint="/ibkr/session/manual-readonly-status-check",
        method="POST",
        runtime_enabled=settings.ibkr_tws_readonly_runtime_enabled,
        adapter_enabled=settings.ibkr_tws_readonly_adapter_enabled,
        real_client_enabled=settings.ibkr_tws_readonly_real_client_enabled,
        host_configured=settings.ibkr_sync_host is not None,
        port_configured=settings.ibkr_sync_port is not None,
        client_id_configured=settings.ibkr_sync_client_id is not None,
        paper_only_mode=settings.paper_only_mode,
        expected_account_mode=expected_mode,
        runtime_client_available=runtime_client is not None,
        runtime_connection_allowed=gate.runtime_connection_allowed,
        runtime_connection_blocked_reason=gate.runtime_connection_blocked_reason,
        manual_status_check_allowed=gate.manual_status_check_allowed,
        manual_status_check_allowed_nl=gate.manual_status_check_allowed_nl,
        connect_attempted=False,
        disconnect_attempted=False,
    )


def _result_from_gate(
    gate: IbkrTwsReadonlyRuntimeGateResult,
    *,
    status: str,
    status_nl: str,
    connection_status: str,
    account_mode_status: str,
    account_mode: str | None,
    session_status_reason: str,
    connect_attempted: bool,
    disconnect_attempted: bool,
    disconnect_error_ignored: bool,
) -> IbkrTwsReadonlyRuntimeCheckResult:
    return IbkrTwsReadonlyRuntimeCheckResult(
        status=status,
        status_nl=status_nl,
        allowed=gate.allowed,
        allowed_nl=gate.allowed_nl,
        blocked=status != "manual_status_check_completed",
        blocked_reasons=() if status == "manual_status_check_completed" else (status,),
        help_nl="Orders blijven geblokkeerd",
        next_step_nl="Suggesties zijn nog niet actief",
        connection_status=connection_status,
        account_mode_status=account_mode_status,
        account_mode=account_mode,
        session_status_reason=session_status_reason,
        session_check_source="manual_tws_readonly_runtime",
        runtime_connection_allowed=gate.runtime_connection_allowed,
        runtime_connection_blocked_reason=gate.runtime_connection_blocked_reason,
        manual_status_check_allowed=gate.manual_status_check_allowed,
        manual_status_check_allowed_nl=gate.manual_status_check_allowed_nl,
        connect_attempted=connect_attempted,
        disconnect_attempted=disconnect_attempted,
        disconnect_error_ignored=disconnect_error_ignored,
    )


def _normalize_mode(mode: str | None) -> str | None:
    if mode is None:
        return None
    normalized = mode.strip().lower()
    if normalized in {"paper", "live"}:
        return normalized
    return None


def _map_adapter_error_code(code: str) -> str:
    normalized = code.strip().lower()
    if normalized in {"authentication_required", "pacing_limited", "connection_failed"}:
        return normalized
    return "unexpected_client_error"


def _reason_nl(reason: str) -> str:
    mappings = {
        "runtime_disabled": "Runtime staat uit",
        "adapter_disabled": "TWS/Gateway adapter staat uit",
        "real_client_disabled": "Echte IBKR statuscontrole staat uit",
        "ibkr_disabled": "IBKR staat uit",
        "status_check_disabled": "Statuscontrole staat uit",
        "missing_host": "TWS/Gateway host ontbreekt",
        "missing_port": "TWS/Gateway poort ontbreekt",
        "missing_client_id": "Client-ID ontbreekt",
        "missing_runtime_client": "Runtime-client ontbreekt",
        "paper_only_required": "Paper-only is verplicht",
        "expected_account_mode_not_paper": "Verwachte accountmodus moet paper zijn",
        "authentication_required": "Authenticatie vereist",
        "pacing_limited": "Pacing-limiet bereikt",
        "connection_failed": "Verbinding mislukt",
        "timeout": "Verbindingstime-out",
        "unexpected_client_error": "Onverwachte clientfout",
    }
    return mappings.get(reason, reason)
