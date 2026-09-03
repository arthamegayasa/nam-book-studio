#!/usr/bin/env python3
"""Apply guarded AskNam state transitions and artifact registrations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from state_core import (
    StateError,
    decide_approval,
    load_json,
    mark_artifact_stale,
    refresh_file_staleness,
    register_artifact,
    save_state,
    transition_node,
    unique,
    validate_state,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--state", type=Path, required=True)
    commands = root.add_subparsers(dest="command", required=True)

    approval = commands.add_parser("approval", help="Approve or reject a human gate")
    approval.add_argument("--id", required=True)
    approval.add_argument("--decision", choices=["approved", "rejected"], required=True)
    approval.add_argument("--by", required=True)
    approval.add_argument("--basis", action="append", default=[])
    approval.add_argument("--note", default="")
    approval.add_argument("--role", default="", help="Reviewer's professional role")
    approval.add_argument("--credentials", default="", help="Reviewer's credentials")

    artifact = commands.add_parser("register-artifact", help="Register a produced file and its provenance")
    artifact.add_argument("--id", required=True)
    artifact.add_argument("--kind", required=True)
    artifact.add_argument("--path", required=True)
    artifact.add_argument("--produced-by", required=True)
    artifact.add_argument("--producer-node")
    artifact.add_argument("--operation", default="run")
    artifact.add_argument("--status", choices=["draft", "review", "approved", "locked", "blocked"], default="draft")
    artifact.add_argument("--locale", choices=["en-US", "id-ID"], required=True)
    artifact.add_argument("--chapter-id")
    artifact.add_argument("--input", action="append", default=[])
    artifact.add_argument("--claim-id", action="append", default=[])
    artifact.add_argument("--source-id", action="append", default=[])
    artifact.add_argument("--objective-id", action="append", default=[])
    artifact.add_argument("--figure-id", action="append", default=[])
    artifact.add_argument("--item-id", action="append", default=[])
    artifact.add_argument("--semantic-block-id", action="append", default=[])
    artifact.add_argument("--blocker", action="append", default=[])
    artifact.add_argument("--origin", default="project-generated")
    artifact.add_argument("--creator", default="Nam Book Studio")
    artifact.add_argument("--license", default="project-owned")
    artifact.add_argument("--source-url", default="")
    artifact.add_argument("--notice-path", default="")

    transition = commands.add_parser("transition", help="Change a route node status")
    transition_target = transition.add_mutually_exclusive_group(required=True)
    transition_target.add_argument("--node", help="Exact route node id")
    transition_target.add_argument(
        "--skill", help="Skill id when it maps to exactly one route node"
    )
    transition.add_argument(
        "--status",
        choices=["ready", "running", "complete", "failed", "blocked", "stale"],
        required=True,
    )

    stale = commands.add_parser("mark-stale", help="Invalidate an artifact and downstream work")
    stale.add_argument("--artifact", required=True)
    stale.add_argument("--reason", required=True)
    stale.add_argument("--high-risk-change", action="store_true")

    commands.add_parser("refresh-staleness", help="Compare registered hashes with files on disk")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        state = load_json(args.state)
        if args.command == "approval":
            result = decide_approval(
                state,
                approval_id=args.id,
                decision=args.decision,
                decided_by=args.by,
                basis_ids=unique(args.basis),
                note=args.note,
                reviewer_role=args.role,
                reviewer_credentials=args.credentials,
            )
        elif args.command == "register-artifact":
            result = register_artifact(
                state,
                args.state,
                artifact_id=args.id,
                kind=args.kind,
                relative_path=args.path,
                produced_by=args.produced_by,
                status=args.status,
                locale=args.locale,
                chapter_id=args.chapter_id,
                input_ids=unique(args.input),
                claim_ids=unique(args.claim_id),
                source_ids=unique(args.source_id),
                origin=args.origin,
                creator=args.creator,
                license_name=args.license,
                source_url=args.source_url,
                notice_path=args.notice_path,
                producer_node=args.producer_node,
                operation=args.operation,
                objective_ids=unique(args.objective_id),
                figure_ids=unique(args.figure_id),
                item_ids=unique(args.item_id),
                semantic_block_ids=unique(args.semantic_block_id),
                blockers=unique(args.blocker),
            )
        elif args.command == "transition":
            result = transition_node(state, args.node or args.skill, args.status)
        elif args.command == "mark-stale":
            result = {
                "invalidated_nodes": sorted(
                    mark_artifact_stale(
                        state,
                        args.artifact,
                        args.reason,
                        high_risk_change=args.high_risk_change,
                    )
                )
            }
        else:
            result = {"changed_artifacts": refresh_file_staleness(state, args.state)}

        errors, warnings = validate_state(state, args.state)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 2
        save_state(state, args.state)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except StateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
