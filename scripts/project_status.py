from __future__ import annotations

from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKING_FILES = [
    "docs/product/current-state.md",
    "docs/product/next-task.md",
    "docs/product/task-history.md",
    "docs/product/version-1-backlog.md",
    "docs/product/version-1-scope-register.md",
]


def read_next_task_title() -> str:
    next_task = REPO_ROOT / "docs/product/next-task.md"
    if not next_task.exists():
        return "WARNING: docs/product/next-task.md ontbreekt"
    for line in next_task.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "WARNING: geen titelregel gevonden in next-task.md"


def git_info() -> str:
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
        return f"{branch} @ {commit}"
    except (OSError, subprocess.SubprocessError):
        return "WARNING: git info niet beschikbaar in deze omgeving"


def product_tracking_check_status() -> str:
    script_path = REPO_ROOT / "scripts/check_product_tracking.py"
    if not script_path.exists():
        return "WARNING: checker ontbreekt"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "WARNING: checker kon niet worden gestart"

    return "PASS" if result.returncode == 0 else "FAIL"


def main() -> None:
    print("Local project workflow status")
    print("=" * 30)
    print(f"Current next task: {read_next_task_title()}")
    print(f"Product tracking checker: {product_tracking_check_status()}")
    print("\nProduct tracking files:")
    for relative_path in TRACKING_FILES:
        exists = (REPO_ROOT / relative_path).exists()
        flag = "OK" if exists else "MISSING"
        print(f"- {flag}: {relative_path}")

    print(f"\nGit: {git_info()}")
    print(
        "\nReminder: GitHub CI status moet extern in GitHub worden geverifieerd; "
        "dit script kan CI niet valideren."
    )


if __name__ == "__main__":
    main()
