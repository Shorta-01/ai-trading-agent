"""Cold-start smoke test for the AI Trading Agent.

Drives the live API across the same status endpoints the dashboard
reads, with one combined verdict line per concern. Runs against a
running API instance — start the stack first (worker + API + web),
then invoke this script to verify everything came up cleanly.

Exit codes:

* ``0`` — all checks green; the install is ready to use.
* ``1`` — warnings only (e.g. IBKR not configured, no events yet).
  The install is structurally fine but some optional surface is
  missing.
* ``2`` — at least one critical failure (DB not connected, migrations
  behind, blocking system event). Operators should NOT rely on the
  install until they're fixed.

Output is dual-language: each line carries a Dutch summary alongside
the English status indicator so the operator can copy-paste it into
an issue without losing context.

Usage:

    python scripts/smoke_test.py --api-url http://127.0.0.1:8000

Add ``--skip-ibkr`` if you're verifying a non-IBKR install (e.g. CI
smoke).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover — caught at runtime
    sys.stderr.write(
        "ERROR: httpx is not installed. Run `pip install httpx` first.\n"
    )
    sys.exit(2)


# Status levels, in increasing severity. The overall exit code is the
# highest level seen across all checks.
STATUS_OK = "OK"
STATUS_WARN = "WARN"
STATUS_FAIL = "FAIL"

_LEVEL_RANK = {STATUS_OK: 0, STATUS_WARN: 1, STATUS_FAIL: 2}
_LEVEL_EXIT = {STATUS_OK: 0, STATUS_WARN: 1, STATUS_FAIL: 2}

# ANSI colour codes. Disabled when stdout is not a TTY.
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_RESET = "\033[0m"


@dataclass(frozen=True)
class CheckResult:
    """One check's verdict."""

    name: str
    status: str  # OK | WARN | FAIL
    summary_nl: str
    detail: str | None = None


def _colour(text: str, code: str, *, use_colour: bool) -> str:
    if not use_colour:
        return text
    return f"{code}{text}{_RESET}"


def _level_colour(level: str) -> str:
    return {STATUS_OK: _GREEN, STATUS_WARN: _YELLOW, STATUS_FAIL: _RED}[level]


def _get_json(client: httpx.Client, path: str) -> tuple[int, Any]:
    """GET ``path`` and return ``(status_code, json_or_text)``.

    Returns ``(0, error_string)`` on transport failure so the caller can
    surface it as a CheckResult instead of crashing.
    """

    try:
        response = client.get(path)
    except Exception as exc:  # noqa: BLE001 — boundary catch
        return 0, f"transport_error: {exc}"
    if response.status_code >= 400:
        return response.status_code, response.text
    try:
        return response.status_code, response.json()
    except Exception as exc:  # noqa: BLE001
        return response.status_code, f"non_json_body: {exc}"


def check_api_health(client: httpx.Client) -> CheckResult:
    code, body = _get_json(client, "/health")
    if code == 0:
        return CheckResult(
            name="API health",
            status=STATUS_FAIL,
            summary_nl="API niet bereikbaar.",
            detail=str(body),
        )
    if code != 200 or not isinstance(body, dict) or body.get("status") != "ok":
        return CheckResult(
            name="API health",
            status=STATUS_FAIL,
            summary_nl=f"API antwoordt met HTTP {code}.",
            detail=str(body),
        )
    return CheckResult(
        name="API health",
        status=STATUS_OK,
        summary_nl=f"API bereikbaar ({body.get('service', '?')}).",
    )


def check_storage(client: httpx.Client) -> CheckResult:
    code, body = _get_json(client, "/storage/status/online")
    if code == 0:
        return CheckResult(
            name="Storage",
            status=STATUS_FAIL,
            summary_nl="Storage-status endpoint niet bereikbaar.",
            detail=str(body),
        )
    if code != 200 or not isinstance(body, dict):
        return CheckResult(
            name="Storage",
            status=STATUS_FAIL,
            summary_nl=f"Storage-status HTTP {code}.",
            detail=str(body),
        )
    configured = bool(body.get("configured"))
    connected = bool(body.get("connected"))
    safe_to_write = bool(body.get("safe_to_write"))
    if not configured:
        return CheckResult(
            name="Storage",
            status=STATUS_WARN,
            summary_nl="Opslag niet geconfigureerd (database_url ontbreekt).",
        )
    if not connected:
        return CheckResult(
            name="Storage",
            status=STATUS_FAIL,
            summary_nl="Opslag geconfigureerd maar geen verbinding met de DB.",
            detail=str(body.get("writes_status_nl")),
        )
    if not safe_to_write:
        return CheckResult(
            name="Storage",
            status=STATUS_FAIL,
            summary_nl="Opslag verbonden maar schrijven geblokkeerd "
            "(migraties achter?).",
            detail=str(body.get("writes_status_nl")),
        )
    return CheckResult(
        name="Storage",
        status=STATUS_OK,
        summary_nl="Opslag verbonden + migraties actueel + schrijfbaar.",
    )


def check_scheduler(client: httpx.Client) -> CheckResult:
    code, body = _get_json(client, "/scheduler/v127/status")
    if code == 0:
        return CheckResult(
            name="Scheduler",
            status=STATUS_FAIL,
            summary_nl="Scheduler-status endpoint niet bereikbaar.",
            detail=str(body),
        )
    if code != 200 or not isinstance(body, dict):
        return CheckResult(
            name="Scheduler",
            status=STATUS_FAIL,
            summary_nl=f"Scheduler-status HTTP {code}.",
            detail=str(body),
        )
    if not body.get("enabled"):
        return CheckResult(
            name="Scheduler",
            status=STATUS_WARN,
            summary_nl="Worker-scheduler heeft nog geen heartbeat "
            "geschreven (start de worker?).",
        )
    last_outcome = body.get("last_outcome")
    if last_outcome == "error":
        return CheckResult(
            name="Scheduler",
            status=STATUS_FAIL,
            summary_nl="Laatste scheduler-fire eindigde met error.",
            detail=str(body.get("last_run_type")),
        )
    return CheckResult(
        name="Scheduler",
        status=STATUS_OK,
        summary_nl=(
            f"Scheduler actief; volgende fires: "
            f"{', '.join(body.get('next_runs') or []) or '—'}."
        ),
    )


def check_ibkr_sync(client: httpx.Client) -> CheckResult:
    code, body = _get_json(client, "/ibkr/sync/status")
    if code == 0:
        return CheckResult(
            name="IBKR sync",
            status=STATUS_WARN,
            summary_nl="IBKR-status endpoint niet bereikbaar.",
            detail=str(body),
        )
    if code != 200 or not isinstance(body, dict):
        return CheckResult(
            name="IBKR sync",
            status=STATUS_WARN,
            summary_nl=f"IBKR-status HTTP {code}.",
            detail=str(body),
        )
    if not body.get("configured"):
        return CheckResult(
            name="IBKR sync",
            status=STATUS_WARN,
            summary_nl="IBKR niet geconfigureerd (account-id ontbreekt). "
            "Optioneel; oké voor een doorlopende test.",
        )
    status_text = body.get("status") or "—"
    if body.get("status") in {"completed", "ok"}:
        return CheckResult(
            name="IBKR sync",
            status=STATUS_OK,
            summary_nl=(
                f"IBKR sync OK ({body.get('positions_count', 0)} posities, "
                f"mode={body.get('account_mode', '?')})."
            ),
        )
    return CheckResult(
        name="IBKR sync",
        status=STATUS_WARN,
        summary_nl=f"IBKR sync status: {status_text}.",
        detail=str(body.get("help_nl")),
    )


def check_system_events(client: httpx.Client) -> CheckResult:
    code, body = _get_json(client, "/system/events/active")
    if code == 0:
        return CheckResult(
            name="System events",
            status=STATUS_WARN,
            summary_nl="System-events endpoint niet bereikbaar.",
            detail=str(body),
        )
    if code != 200 or not isinstance(body, dict):
        return CheckResult(
            name="System events",
            status=STATUS_WARN,
            summary_nl=f"System-events HTTP {code}.",
            detail=str(body),
        )
    active = int(body.get("active_count") or 0)
    if active == 0:
        return CheckResult(
            name="System events",
            status=STATUS_OK,
            summary_nl="Geen actieve systeemmeldingen.",
        )
    # When events exist, escalate based on whether any block writes /
    # suggestions. A blocking event is FAIL; non-blocking is WARN.
    events = body.get("events") or []
    blocking = [
        e
        for e in events
        if isinstance(e, dict)
        and (
            e.get("blocks_suggestions")
            or e.get("blocks_writes")
            or e.get("blocks_ai_explanation")
        )
    ]
    if blocking:
        return CheckResult(
            name="System events",
            status=STATUS_FAIL,
            summary_nl=(
                f"{active} actieve systeemmelding(en) waarvan "
                f"{len(blocking)} blokkerend."
            ),
            detail=(
                blocking[0].get("title_nl") if isinstance(blocking[0], dict) else None
            ),
        )
    return CheckResult(
        name="System events",
        status=STATUS_WARN,
        summary_nl=f"{active} niet-blokkerende systeemmelding(en) actief.",
    )


def _print_check(result: CheckResult, *, use_colour: bool) -> None:
    indicator = _colour(
        f"[{result.status}]", _level_colour(result.status), use_colour=use_colour
    )
    print(f"  {indicator} {result.name}: {result.summary_nl}")
    if result.detail and result.status != STATUS_OK:
        # Truncate so a giant traceback doesn't bury the summary.
        detail = result.detail.strip().splitlines()[0][:160]
        print(f"        ↳ {detail}")


def run_smoke_test(
    *,
    api_url: str,
    skip_ibkr: bool,
    skip_events: bool,
    timeout_seconds: float,
    use_colour: bool,
) -> int:
    """Run all checks, print the report, return the exit code."""

    print(f"Cold-start smoke test — API: {api_url}")
    print(
        "-------------------------------------------------------------"
    )
    with httpx.Client(base_url=api_url, timeout=timeout_seconds) as client:
        results: list[CheckResult] = [
            check_api_health(client),
            check_storage(client),
            check_scheduler(client),
        ]
        if not skip_ibkr:
            results.append(check_ibkr_sync(client))
        if not skip_events:
            results.append(check_system_events(client))

    for result in results:
        _print_check(result, use_colour=use_colour)

    worst = max((r.status for r in results), key=lambda s: _LEVEL_RANK[s])
    exit_code = _LEVEL_EXIT[worst]
    print(
        "-------------------------------------------------------------"
    )
    if exit_code == 0:
        print(
            _colour(
                "OK — install gezond, klaar voor paper-testing.",
                _GREEN,
                use_colour=use_colour,
            )
        )
    elif exit_code == 1:
        print(
            _colour(
                "WARN — install grotendeels OK, enkele optionele "
                "onderdelen ontbreken.",
                _YELLOW,
                use_colour=use_colour,
            )
        )
    else:
        print(
            _colour(
                "FAIL — kritieke check faalde; los op vóór gebruik.",
                _RED,
                use_colour=use_colour,
            )
        )
    return exit_code


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Cold-start smoke test for the AI Trading Agent stack. "
            "Run after starting the API + worker to verify the install."
        )
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the API to test (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--skip-ibkr",
        action="store_true",
        help="Skip the IBKR sync check (e.g. when IBKR isn't configured yet).",
    )
    parser.add_argument(
        "--skip-events",
        action="store_true",
        help="Skip the system-events check.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="Per-request timeout (default: 10s).",
    )
    parser.add_argument(
        "--no-colour",
        action="store_true",
        help="Disable ANSI colour output (forced off on non-TTY by default).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    use_colour = (not args.no_colour) and sys.stdout.isatty()
    return run_smoke_test(
        api_url=args.api_url,
        skip_ibkr=args.skip_ibkr,
        skip_events=args.skip_events,
        timeout_seconds=args.timeout_seconds,
        use_colour=use_colour,
    )


if __name__ == "__main__":  # pragma: no cover — CLI entrypoint
    sys.exit(main())
