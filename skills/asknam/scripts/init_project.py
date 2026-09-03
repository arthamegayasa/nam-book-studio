#!/usr/bin/env python3
"""Initialize a Nam Book project manifest without overwriting existing state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from state_core import StateError, atomic_write_json, create_manifest, validate_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--project-id")
    parser.add_argument("--title", required=True)
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--audience", default="")
    parser.add_argument("--reader-outcome", default="")
    parser.add_argument(
        "--profile",
        choices=["friendly-explainer", "textbook", "exam-prep"],
        required=True,
    )
    parser.add_argument("--source-locale", choices=["en-US", "id-ID"], required=True)
    parser.add_argument(
        "--target-locale", choices=["en-US", "id-ID"], action="append", default=[]
    )
    parser.add_argument("--risk-level", choices=["R0", "R1", "R2", "R3"], default="R0")
    parser.add_argument("--medical", action="store_true")
    parser.add_argument("--jurisdiction")
    parser.add_argument("--evidence-cutoff")
    parser.add_argument("--revalidate-before-export")
    parser.add_argument("--assessments", choices=["auto", "yes", "no"], default="auto")
    parser.add_argument("--illustrations", choices=["auto", "yes", "no"], default="auto")
    parser.add_argument("--diagrams", choices=["auto", "yes", "no"], default="auto")
    parser.add_argument(
        "--deliverable",
        choices=["markdown", "docx", "pdf", "epub"],
        action="append",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state_path = args.project_dir.resolve() / ".nam-book" / "project.json"
    if state_path.exists():
        print(f"Refusing to overwrite existing state: {state_path}", file=sys.stderr)
        return 2
    try:
        state = create_manifest(
            title=args.title,
            project_id=args.project_id,
            subtitle=args.subtitle,
            audience=args.audience,
            reader_outcome=args.reader_outcome,
            profile_id=args.profile,
            source_locale=args.source_locale,
            target_locales=args.target_locale,
            risk_level=args.risk_level,
            medical_enabled=args.medical,
            jurisdiction=args.jurisdiction,
            evidence_cutoff=args.evidence_cutoff,
            revalidate_before_export=args.revalidate_before_export,
            assessments=args.assessments,
            illustrations=args.illustrations,
            diagrams=args.diagrams,
            deliverables=args.deliverable or ["markdown"],
        )
        errors, warnings = validate_state(state, state_path)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 2
        atomic_write_json(state_path, state)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print(state_path)
        return 0
    except StateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
