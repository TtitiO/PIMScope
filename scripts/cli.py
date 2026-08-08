"""Compatibility entry point for the simulator-owned PIMScope CLI.

The reusable command implementation lives in :mod:`ramulator.pimscope.cli`.
This parent alias remains so existing ``pimscope`` commands keep working while
paper-artifact tooling stays in the PIMScope repository.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ramulator.pimscope.cli import main as _simulator_main

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _git_revision(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    return _simulator_main(
        prog="pimscope",
        output_base=PROJECT_ROOT,
        provenance={"pimscope_commit": _git_revision(PROJECT_ROOT)},
    )


if __name__ == "__main__":
    raise SystemExit(main())
