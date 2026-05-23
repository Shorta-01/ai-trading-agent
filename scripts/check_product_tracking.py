from __future__ import annotations

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


def check_file_exists(relative_path: str) -> tuple[bool, str]:
    target = REPO_ROOT / relative_path
    if not target.exists():
        return False, f"MISSING: {relative_path}"
    return True, f"OK: {relative_path}"


def check_next_task_has_title() -> tuple[bool, str]:
    text = (REPO_ROOT / "docs/product/next-task.md").read_text(encoding="utf-8")
    has_title = re.search(r"^#\s+Task\s+\d+", text, flags=re.MULTILINE)
    if has_title:
        return True, "OK: next-task has task title"
    return False, "MISSING: next-task task title line starting with '# Task <number>'"


def check_current_state_marker() -> tuple[bool, str]:
    text = (REPO_ROOT / "docs/product/current-state.md").read_text(encoding="utf-8")
    marker = "Huidige toestand:"
    if marker in text:
        return True, "OK: current-state contains 'Huidige toestand:'"
    return False, "MISSING: current-state marker 'Huidige toestand:'"


def main() -> int:
    results: list[tuple[bool, str]] = []

    for file_path in REQUIRED_FILES:
        results.append(check_file_exists(file_path))

    if all(ok for ok, _ in results):
        results.append(check_next_task_has_title())
        results.append(check_current_state_marker())

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
