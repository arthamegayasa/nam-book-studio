#!/usr/bin/env python3
"""Validate a Nam Book manifest, dependency graph, approvals, and hashes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from state_core import StateError, load_json, validate_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args(argv)
    try:
        state = load_json(args.state)
        errors, warnings = validate_state(state, args.state)
    except StateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors or (args.strict and warnings):
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
