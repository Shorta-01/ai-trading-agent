from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "docs/product/next-task.md",
    "docs/product/current-state.md",
    "docs/product/task-history.md",
    "docs/product/version-1-backlog.md",
    "docs/product/version-1-scope-register.md",
]
CURRENT_STATE_PATH = REPO_ROOT / "docs/product/current-state.md"
MARKER_RE = re.compile(
    r"Huidige toestand:\s*\*\*na\s+Task\s+(\d+)([A-Z]?)(?:-(R))?\*\*"
)
COMPLETED_TASK_RE = re.compile(
    r"Task\s+(\d+)([A-Z]?)(?:-(R))?\s*:\s*\*\*completed\*\*"
)


@dataclass(frozen=True, order=True)
class TaskId:
    number: int
    suffix_rank: int
    suffix_letter: str
    repair_rank: int


def parse_task_id(number: str, suffix: str, repair: str) -> TaskId:
    suffix_clean = suffix or ""
    repair_clean = repair or ""
    return TaskId(
        number=int(number),
        suffix_rank=0 if not suffix_clean else 1,
        suffix_letter=suffix_clean,
        repair_rank=1 if repair_clean == "R" else 0,
    )


def format_task(task_id: TaskId) -> str:
    suffix = task_id.suffix_letter
    repair = "-R" if task_id.repair_rank else ""
    return f"{task_id.number}{suffix}{repair}"


def check_file_exists(relative_path: str) -> tuple[bool, str]:
    target = REPO_ROOT / relative_path
    if not target.exists():
        return False, f"MISSING: {relative_path}"
    return True, f"OK: {relative_path}"


def check_next_task_has_title() -> tuple[bool, str]:
    text = (REPO_ROOT / "docs/product/next-task.md").read_text(encoding="utf-8")
    has_title = re.search(r"^#\s+Task\s+\d+[A-Z]?(?:-R)?", text, flags=re.MULTILINE)
    if has_title:
        return True, "OK: next-task has task title"
    return (
        False,
        "MISSING: next-task task title line starting with '# Task <number|suffix>'",
    )


def check_current_state_marker_exists() -> tuple[bool, str]:
    text = CURRENT_STATE_PATH.read_text(encoding="utf-8")
    marker = "Huidige toestand:"
    if marker in text:
        return True, "OK: current-state contains 'Huidige toestand:'"
    return False, "MISSING: current-state marker 'Huidige toestand:'"


def check_current_state_marker_not_stale() -> tuple[bool, str]:
    text = CURRENT_STATE_PATH.read_text(encoding="utf-8")
    marker_match = MARKER_RE.search(text)
    if not marker_match:
        return (
            False,
            "MISSING: current-state marker format "
            "'Huidige toestand: **na Task <number><suffix>[-R]**'",
        )

    first_task_match = COMPLETED_TASK_RE.search(text)
    if not first_task_match:
        return False, "MISSING: first completed task entry in current-state"

    marker_task = parse_task_id(*marker_match.groups())
    first_task = parse_task_id(*first_task_match.groups())

    if marker_task < first_task:
        return (
            False,
            "STALE: current-state marker Task "
            f"{format_task(marker_task)} is older than first completed "
            f"Task {format_task(first_task)}",
        )

    return (
        True,
        "OK: current-state marker Task "
        f"{format_task(marker_task)} is not older than "
        f"Task {format_task(first_task)}",
    )


def main() -> int:
    results: list[tuple[bool, str]] = []

    for file_path in REQUIRED_FILES:
        results.append(check_file_exists(file_path))

    if all(ok for ok, _ in results):
        results.append(check_next_task_has_title())
        results.append(check_current_state_marker_exists())
        results.append(check_current_state_marker_not_stale())

    failed = [message for ok, message in results if not ok]
    passed = [message for ok, message in results if ok]

    print("Product tracking check summary")
    print("=" * 30)
    for message in passed:
        print(f"PASS: {message}")
    for message in failed:
        print(f"FAIL: {message}")

    if failed:
        print(f"\nResult: FAIL ({len(failed)} issue(s))")
        return 1

    print("\nResult: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
