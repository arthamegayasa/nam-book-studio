#!/usr/bin/env python3
"""Validate AskNam's install-portable resource bundle and repository mirrors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROFILE_FILES = {
    "friendly-explainer.json",
    "textbook.json",
    "exam-prep.json",
}
SCHEMA_FILES = {
    "book-architecture.schema.json",
    "book-artifact.schema.json",
    "book-profile.schema.json",
    "book-project.schema.json",
    "book-route.schema.json",
    "capability-catalog.schema.json",
    "evidence-ledger.schema.json",
}
PROJECT_SCHEMA_URI = (
    "https://raw.githubusercontent.com/arthamegayasa/nam-book-studio/"
    "main/skills/asknam/references/schemas/book-project.schema.json"
)


def load_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def validate(require_mirrors: bool = False) -> list[str]:
    asknam = Path(__file__).resolve().parents[1]
    repository = asknam.parents[1]
    references = asknam / "references"
    errors: list[str] = []

    groups = {
        "profiles": PROFILE_FILES,
        "schemas": SCHEMA_FILES,
    }
    for group, names in groups.items():
        bundled_dir = references / group
        actual = {item.name for item in bundled_dir.glob("*.json")}
        if actual != names:
            errors.append(
                f"bundled {group} differ: missing={sorted(names - actual)}, "
                f"extra={sorted(actual - names)}"
            )
        for name in sorted(names & actual):
            bundled = bundled_dir / name
            try:
                load_object(bundled)
            except ValueError as exc:
                errors.append(str(exc))

            mirror = repository / group / name
            mirror_set_exists = (repository / group).is_dir()
            if require_mirrors and not mirror.is_file():
                errors.append(f"repository mirror is missing: {mirror}")
            elif mirror_set_exists and mirror.is_file():
                try:
                    mirror_value = load_object(mirror)
                    bundled_value = load_object(bundled)
                except ValueError as exc:
                    errors.append(str(exc))
                    continue
                if bundled_value != mirror_value:
                    errors.append(f"repository mirror differs from bundle: {mirror}")

    catalog_path = references / "skill-catalog.json"
    try:
        catalog = load_object(catalog_path)
        if catalog.get("$schema") != "schemas/capability-catalog.schema.json":
            errors.append("skill catalog must resolve its schema within AskNam")
    except ValueError as exc:
        errors.append(str(exc))

    project_schema = references / "schemas" / "book-project.schema.json"
    try:
        schema = load_object(project_schema)
        if schema.get("$id") != PROJECT_SCHEMA_URI:
            errors.append("bundled project schema has the wrong public $id")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-mirrors",
        action="store_true",
        help="Require structurally identical top-level repository mirrors",
    )
    args = parser.parse_args(argv)
    errors = validate(args.require_mirrors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("AskNam bundled resources are valid and portable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
