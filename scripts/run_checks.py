#!/usr/bin/env python3
"""Run every repository gate in order with the Python standard library.

This is the single pre-finish command named in AGENTS.md and the only test step
in the Validate workflow. It stops at the first failing gate so the failure is
the first thing in the log, prints a one-line verdict per gate, and exits with a
non-zero status when any gate failed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Gate:
    """One command in the gate sequence; ``args`` are relative to the repository root."""

    name: str
    description: str
    args: tuple[str, ...]

    def command(self, python: str = sys.executable) -> list[str]:
        return [python, *self.args]


GATES: tuple[Gate, ...] = (
    Gate("validate_repository", "Structural repository checks", ("scripts/validate_repository.py",)),
    Gate("tests", "Repository test suite", ("-m", "unittest", "discover", "-s", "tests", "-v")),
    Gate("state_tools", "AskNam state and routing tests", ("skills/asknam/scripts/test_state_tools.py",)),
    Gate(
        "resources",
        "Install-portable profiles and schemas with mirrors",
        ("skills/asknam/scripts/validate_resources.py", "--require-mirrors"),
    ),
    Gate("compileall", "Byte-compile helper scripts", ("-m", "compileall", "-q", "scripts", "skills")),
)


def run_gate(gate: Gate, *, python: str = sys.executable) -> tuple[int, float]:
    started = time.monotonic()
    completed = subprocess.run(gate.command(python), cwd=ROOT, check=False)
    return completed.returncode, time.monotonic() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run every Nam Book Studio gate in order.")
    parser.add_argument("--list", action="store_true", help="Print the gate commands without running them")
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Run the remaining gates after a failure instead of stopping at the first one",
    )
    args = parser.parse_args(argv)

    if args.list:
        for gate in GATES:
            print(" ".join(["python", *gate.args]))
        return 0

    results: list[tuple[Gate, str, float]] = []
    failed = False
    for gate in GATES:
        print(f"==> {gate.name}: {gate.description}", flush=True)
        code, elapsed = run_gate(gate)
        verdict = "pass" if code == 0 else f"fail (exit {code})"
        results.append((gate, verdict, elapsed))
        if code != 0:
            failed = True
            if not args.keep_going:
                break

    print()
    print("Gate summary:")
    width = max(len(gate.name) for gate in GATES)
    for gate, verdict, elapsed in results:
        print(f"  {gate.name.ljust(width)}  {verdict}  ({elapsed:.1f}s)")
    skipped = [gate.name for gate in GATES[len(results):]]
    if skipped:
        print("  not run: " + ", ".join(skipped))
    print("RESULT: " + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
