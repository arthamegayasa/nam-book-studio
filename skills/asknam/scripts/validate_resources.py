#!/usr/bin/env python3
"""Validate AskNam's install-portable resource bundle and repository mirrors."""

from __future__ import annotations

import argparse
import json
import re
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
    "callout-catalog.schema.json",
    "capability-catalog.schema.json",
    "design-spec.schema.json",
    "evidence-ledger.schema.json",
}
CALLOUT_PLACEMENTS = {"inline", "side-column", "band", "full-page", "opener"}
CALLOUT_REVEAL_RULES = {"none", "inline", "chapter-end", "book-end"}
BOOK_MODES = {"friendly-explainer", "textbook", "exam-prep"}
LOCALES = {"en-US", "id-ID"}
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


def validate_callout_catalog(path: Path) -> list[str]:
    """Structural checks for the callout catalog without a JSON Schema library."""
    errors: list[str] = []
    try:
        catalog = load_object(path)
    except ValueError as exc:
        return [str(exc)]
    label = path.name
    if catalog.get("schema_version") != "1.0.0":
        errors.append(f"{label}: schema_version must be 1.0.0")
    try:
        re.compile(str(catalog.get("id_pattern", "")))
    except re.error as exc:
        errors.append(f"{label}: id_pattern is not a valid regular expression: {exc}")
    placements = catalog.get("placements")
    if not isinstance(placements, list) or set(placements) - CALLOUT_PLACEMENTS or not placements:
        errors.append(f"{label}: placements must be a non-empty subset of {sorted(CALLOUT_PLACEMENTS)}")
        placements = []
    reveal_rules = catalog.get("reveal_rules")
    if not isinstance(reveal_rules, list) or set(reveal_rules) - CALLOUT_REVEAL_RULES or not reveal_rules:
        errors.append(f"{label}: reveal_rules must be a non-empty subset of {sorted(CALLOUT_REVEAL_RULES)}")
        reveal_rules = []
    density = catalog.get("density_minimum_words_per_callout")
    if not isinstance(density, dict) or set(density) != {"high", "medium", "low"} or any(
        not isinstance(value, int) or value < 1 for value in density.values()
    ):
        errors.append(f"{label}: density_minimum_words_per_callout needs positive integers for high, medium, low")
    types = catalog.get("types")
    if not isinstance(types, list) or not types:
        return errors + [f"{label}: types must be a non-empty list"]
    seen: set[str] = set()
    for entry in types:
        if not isinstance(entry, dict):
            errors.append(f"{label}: every type must be an object")
            continue
        type_id = str(entry.get("type_id", ""))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", type_id):
            errors.append(f"{label}: type_id must be kebab-case: {type_id!r}")
        if type_id in seen:
            errors.append(f"{label}: duplicate type_id {type_id}")
        seen.add(type_id)
        labels = entry.get("labels")
        if not isinstance(labels, dict) or set(labels) != LOCALES or any(
            not str(labels.get(locale, "")).strip() for locale in LOCALES
        ):
            errors.append(f"{label}: {type_id} needs non-empty labels for en-US and id-ID")
        modes = entry.get("modes")
        if not isinstance(modes, list) or not modes or set(modes) - BOOK_MODES:
            errors.append(f"{label}: {type_id} modes must be a non-empty subset of {sorted(BOOK_MODES)}")
        allowed = entry.get("allowed_placements")
        if not isinstance(allowed, list) or not allowed or set(allowed) - set(placements):
            errors.append(f"{label}: {type_id} allowed_placements must be a non-empty subset of the catalog placements")
            allowed = []
        if entry.get("default_placement") not in allowed:
            errors.append(f"{label}: {type_id} default_placement must be one of its allowed_placements")
        reveal = entry.get("reveal", [])
        if not isinstance(reveal, list) or set(reveal) - set(reveal_rules):
            errors.append(f"{label}: {type_id} reveal must be a subset of the catalog reveal_rules")
        default_reveal = entry.get("default_reveal", {})
        if not isinstance(default_reveal, dict) or set(default_reveal) - BOOK_MODES or any(
            value not in reveal for value in default_reveal.values()
        ):
            errors.append(f"{label}: {type_id} default_reveal must map modes to one of its reveal values")
        if not str(entry.get("purpose", "")).strip():
            errors.append(f"{label}: {type_id} needs a purpose")
    return errors


def validate(require_mirrors: bool = False) -> list[str]:
    asknam = Path(__file__).resolve().parents[1]
    repository = asknam.parents[1]
    references = asknam / "references"
    errors: list[str] = []
    errors.extend(validate_callout_catalog(references / "callout-catalog.json"))

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
