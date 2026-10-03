"""Quality gate: black, flake8, mypy, bandit, pytest.

Prints one PASS/FAIL line per tool and exits non-zero if any fails.
Usage: python scripts/check.py [-v]   (-v shows each tool's output)
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TOOLS = [
    ("black", ["black", "--check", "--quiet", "."]),
    ("flake8", ["flake8"]),
    ("mypy", ["mypy", "aarogya", "app.py", "scripts"]),
    ("bandit", ["bandit", "-r", "aarogya", "-q"]),
    ("pytest", ["pytest", "-q"]),
]


def run_tool(args):
    """Runs one tool as a module of this interpreter."""
    # Use sys.executable for Windows and Linux
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    verbose = "-v" in argv
    failed = []
    for name, args in TOOLS:
        result = run_tool(args)
        ok = result.returncode == 0
        print(f"{name:<8} {'PASS' if ok else 'FAIL'}", flush=True)
        if not ok:
            failed.append(name)
        if verbose and (result.stdout or result.stderr):
            print(result.stdout + result.stderr)
    if failed:
        print(f"check: FAIL ({', '.join(failed)})")
        return 1
    print("check: all PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
