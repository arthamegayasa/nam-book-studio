#!/usr/bin/env python3
"""Rebuild the smallest sufficient AskNam route for a project intent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from state_core import (
    StateError,
    build_route,
    format_route_receipt,
    load_catalog,
    load_json,
    load_profile,
    save_state,
    validate_state,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument(
        "--intent",
        choices=["start", "resume", "revise", "audit", "illustrate", "localize", "publish"],
        default="resume",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        state = load_json(args.state)
        state["route"] = build_route(
            state,
            load_catalog(),
            load_profile(state["profile"]),
            args.intent,
        )
        errors, warnings = validate_state(state, args.state)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 2
        if not args.dry_run:
            save_state(state, args.state)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print(
            json.dumps(state["route"], ensure_ascii=False, indent=2)
            if args.as_json
            else format_route_receipt(state["route"])
        )
        return 0
    except StateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
