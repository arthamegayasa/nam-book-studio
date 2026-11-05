#!/usr/bin/env python3
"""Inspect the callouts in a Nam Book manuscript against the callout catalog.

A callout is a Pandoc fenced div carrying the ``.callout`` class::

    ::: {#callout-ch03-02 .callout type=warning placement=band objective=obj-ch03-01}
    Body in the manuscript locale.
    :::

The inspector checks structure only: catalog membership, IDs, placements,
objective links, reveal rules, item links, answer-key targets and entries,
nesting, and density. It never judges whether a callout teaches well. Errors
make the manuscript unfit for registration; warnings need editorial judgment.

Quick checks join the assessment item bank through ``item=``. Pass the bank
with ``--items items.<locale>.yaml`` (repeatable; YAML or JSON) and every
``item=`` must name an ``item_id`` found there. The bank is scanned line by
line for ``item_id: <id>`` or ``"item_id": "<id>"``; no YAML parser is needed.

An ``answer-key`` body is a list whose entries start with the ID they answer::

    - item-ch01-001: B. One-line rationale.
    - callout-ch01-04: The discussion a chapter-end reflection points to.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

MODES = ("friendly-explainer", "textbook", "exam-prep")
LOCALES = ("en-US", "id-ID")
DENSITIES = ("high", "medium", "low")
KNOWN_ATTRIBUTES = {"type", "placement", "objective", "item", "reveal", "for", "title"}

OPEN_RE = re.compile(r"^(:{3,})\s*\{(.*)\}\s*$")
CLOSE_RE = re.compile(r"^(:{3,})\s*$")
ATTRIBUTE_RE = re.compile(
    r"""(?P<id>#[\w.:-]+)|(?P<class>\.[\w-]+)|(?P<key>[\w-]+)=(?:"(?P<dq>[^"]*)"|'(?P<sq>[^']*)'|(?P<bare>\S+))"""
)
WORD_RE = re.compile(r"\w+", re.UNICODE)
FOR_RE = re.compile(r"^(?:ch-[0-9]{2,}|book)$")
ITEM_RE = re.compile(r"^item-[a-z0-9][a-z0-9-]*$")
# One answer-key entry: a list marker, the item or callout ID (optionally bold), a colon, the key text.
ANSWER_KEY_ENTRY_RE = re.compile(
    r"^\s*(?:[-*+]|\d+[.)])\s+(?:\*\*)?(?P<id>(?:item|callout)-[A-Za-z0-9][\w-]*)(?:\*\*)?\s*:\s*(?P<text>.*)$"
)
# ``item_id: item-ch01-001`` in YAML or ``"item_id": "item-ch01-001"`` in JSON, anywhere on a line.
ITEM_ID_LINE_RE = re.compile(r"""(?:^|[\s{,\[-])["']?item_id["']?\s*:\s*["']?(?P<id>[A-Za-z0-9][\w.-]*)""")


def default_catalog_path() -> Path:
    """Resolve the shared catalog from a sibling AskNam installation."""
    return Path(__file__).resolve().parents[2] / "asknam" / "references" / "callout-catalog.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def parse_attributes(raw: str) -> dict[str, Any]:
    attributes: dict[str, Any] = {"id": None, "classes": [], "attrs": {}}
    for match in ATTRIBUTE_RE.finditer(raw):
        if match.group("id"):
            attributes["id"] = match.group("id")[1:]
        elif match.group("class"):
            attributes["classes"].append(match.group("class")[1:])
        else:
            value = match.group("dq")
            if value is None:
                value = match.group("sq")
            if value is None:
                value = match.group("bare")
            attributes["attrs"][match.group("key")] = value
    return attributes


def split_front_matter(text: str) -> tuple[dict[str, str], list[str], int]:
    """Return simple front-matter scalars, the body lines, and the body's first line number."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, lines, 1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            scalars: dict[str, str] = {}
            for line in lines[1:index]:
                match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*$", line)
                if match:
                    scalars[match.group(1)] = match.group(2)
            return scalars, lines[index + 1:], index + 2
    return {}, lines, 1


def parse_blocks(lines: list[str], first_line: int, errors: list[str]) -> list[dict[str, Any]]:
    """Split a manuscript into ordered prose and callout blocks."""
    blocks: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    prose_lines: list[str] = []

    def flush_prose() -> None:
        if any(line.strip() for line in prose_lines):
            blocks.append({"kind": "prose", "words": sum(len(WORD_RE.findall(line)) for line in prose_lines)})
        prose_lines.clear()

    for offset, line in enumerate(lines):
        line_number = first_line + offset
        opener = OPEN_RE.match(line)
        closer = CLOSE_RE.match(line)
        current = stack[-1] if stack else None
        if opener:
            attributes = parse_attributes(opener.group(2))
            is_callout = "callout" in attributes["classes"]
            if current and current["kind"] == "callout":
                errors.append(
                    f"Callout {current['id'] or '<no id>'} at line {current['line']} contains a nested fenced div "
                    f"at line {line_number}; callouts cannot be nested"
                )
                stack.append({"kind": "div", "line": line_number})
            elif is_callout:
                flush_prose()
                stack.append({
                    "kind": "callout", "id": attributes["id"], "classes": attributes["classes"],
                    "attrs": attributes["attrs"], "line": line_number, "body": [],
                })
            else:
                stack.append({"kind": "div", "line": line_number})
            continue
        if closer and stack:
            frame = stack.pop()
            if frame["kind"] == "callout":
                blocks.append(frame)
            continue
        if current and current["kind"] == "callout":
            current["body"].append(line)
        elif current and current["kind"] == "div" and any(
            frame["kind"] == "callout" for frame in stack
        ):
            callout_frame = next(frame for frame in reversed(stack) if frame["kind"] == "callout")
            callout_frame["body"].append(line)
        else:
            prose_lines.append(line)
    flush_prose()
    for frame in stack:
        if frame["kind"] == "callout":
            errors.append(f"Callout {frame['id'] or '<no id>'} opened at line {frame['line']} is not closed")
            blocks.append(frame)
    return blocks


def architecture_objectives(architecture: dict[str, Any] | None) -> set[str] | None:
    if architecture is None:
        return None
    objectives: set[str] = set()
    for chapter in architecture.get("chapters", []):
        for objective in chapter.get("objectives", []):
            if isinstance(objective, dict) and objective.get("objective_id"):
                objectives.add(str(objective["objective_id"]))
            elif isinstance(objective, str):
                objectives.add(objective)
        for objective_id in chapter.get("objective_ids", []):
            objectives.add(str(objective_id))
    return objectives


def chapter_from_callout_id(callout_id: str | None) -> str | None:
    if not callout_id:
        return None
    parts = callout_id.split("-")
    if len(parts) < 3 or not parts[1].startswith("ch"):
        return None
    return "ch-" + parts[1][2:]


def load_item_ids(paths: Iterable[Path]) -> set[str]:
    """Collect every ``item_id`` declared in the given item-bank files (YAML or JSON).

    The scan is line-based and needs no YAML parser: any ``item_id: <id>`` or
    ``"item_id": "<id>"`` occurrence counts. Unreadable files raise ``OSError``.
    """
    item_ids: set[str] = set()
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        for line in text.splitlines():
            for match in ITEM_ID_LINE_RE.finditer(line):
                item_ids.add(match.group("id"))
    return item_ids


def parse_answer_key(body: Iterable[str] | str) -> tuple[dict[str, str], list[str]]:
    """Return the keyed entries of an answer-key body and the non-empty lines that are not entries.

    An entry starts with a list marker and the ID it answers (``- item-ch01-001: ...`` or
    ``- callout-ch01-04: ...``); indented lines continue the previous entry.
    """
    lines = body.splitlines() if isinstance(body, str) else list(body)
    entries: dict[str, str] = {}
    unkeyed: list[str] = []
    current: str | None = None
    for line in lines:
        if not line.strip():
            current = None
            continue
        match = ANSWER_KEY_ENTRY_RE.match(line)
        if match:
            current = match.group("id")
            entries[current] = match.group("text").strip()
        elif current is not None and line[:1].isspace():
            entries[current] = (entries[current] + " " + line.strip()).strip()
        else:
            current = None
            unkeyed.append(line.strip())
    return entries, unkeyed


def answer_key_entries(body: Iterable[str] | str) -> dict[str, str]:
    """Map each ID an answer-key body answers to its key or discussion text."""
    return parse_answer_key(body)[0]


def inspect_manuscript(
    text: str,
    *,
    mode: str,
    locale: str,
    catalog: dict[str, Any],
    chapter_id: str | None = None,
    density: str | None = None,
    architecture: dict[str, Any] | None = None,
    item_ids: set[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if mode not in MODES:
        errors.append(f"Unsupported mode {mode}")
    if locale not in LOCALES:
        errors.append(f"Unsupported locale {locale}")
    if density is not None and density not in DENSITIES:
        errors.append(f"Unsupported density {density}")

    front_matter, lines, first_line = split_front_matter(text)
    chapter_id = chapter_id or front_matter.get("chapter_id") or None
    id_pattern = re.compile(catalog.get("id_pattern", r"^callout-ch[0-9]{2,}-[0-9]{2,}$"))
    types = {item["type_id"]: item for item in catalog.get("types", [])}
    known_objectives = architecture_objectives(architecture)

    blocks = parse_blocks(lines, first_line, errors)
    callouts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    prose_words = 0
    previous_block: dict[str, Any] | None = None
    opener_counts: dict[str, int] = {}
    chapter_end_chapters: set[str] = set()
    book_end_needed = False
    answer_keys: dict[str, dict[str, str]] = {}
    quick_checks: list[dict[str, str]] = []
    chapter_end_reflections: list[tuple[str, str]] = []

    for block in blocks:
        if block["kind"] == "prose":
            prose_words += block["words"]
            previous_block = block
            continue
        attrs: dict[str, str] = block["attrs"]
        callout_id: str | None = block["id"]
        label_id = callout_id or f"<line {block['line']}>"
        record: dict[str, Any] = {
            "callout_id": callout_id, "line": block["line"], "type": attrs.get("type"),
            "label": None, "placement": attrs.get("placement"), "objective": attrs.get("objective"),
            "reveal": attrs.get("reveal"), "item": attrs.get("item"), "for": attrs.get("for"),
            "title": attrs.get("title"),
        }

        if not callout_id:
            errors.append(f"Callout at line {block['line']} has no #id")
        else:
            if not id_pattern.match(callout_id):
                errors.append(f"Callout ID {callout_id} does not match the catalog pattern {id_pattern.pattern}")
            if callout_id in seen_ids:
                errors.append(f"duplicate callout id {callout_id}")
            seen_ids.add(callout_id)
            own_chapter = chapter_from_callout_id(callout_id)
            if chapter_id and own_chapter and own_chapter.replace("-", "") != chapter_id.replace("-", ""):
                errors.append(f"Callout {callout_id} belongs to chapter {own_chapter} but the manuscript is {chapter_id}")

        for extra_class in block["classes"]:
            if extra_class != "callout":
                warnings.append(f"Callout {label_id} carries an unexpected class .{extra_class}")
        for key in attrs:
            if key not in KNOWN_ATTRIBUTES:
                warnings.append(f"Callout {label_id} has unknown attribute {key}")

        type_id = attrs.get("type")
        spec = types.get(type_id or "")
        if not type_id:
            errors.append(f"Callout {label_id} has no type")
        elif spec is None:
            errors.append(f"Callout {label_id} uses unknown type {type_id}")
        else:
            record["label"] = spec["labels"].get(locale)
            if mode in MODES and mode not in spec["modes"]:
                errors.append(f"Callout {label_id} type {type_id} is not allowed in mode {mode}")
            if spec.get("deprecated"):
                warnings.append(f"Callout {label_id} uses deprecated type {type_id}")
            placement = attrs.get("placement") or spec["default_placement"]
            if placement not in spec["allowed_placements"]:
                errors.append(
                    f"Callout {label_id} placement {placement} is not allowed for type {type_id}; "
                    f"use one of {spec['allowed_placements']}"
                )
            record["placement"] = placement

            requires_for = bool(spec.get("requires_for"))
            objective = attrs.get("objective")
            if not requires_for:
                if not objective or re.search(r"[\s,]", objective):
                    errors.append(f"Callout {label_id} must link exactly one objective (objective=obj-...)")
                elif known_objectives is not None and objective not in known_objectives:
                    errors.append(f"Callout {label_id} objective {objective} is not in the architecture")
            elif objective:
                warnings.append(f"Callout {label_id} type {type_id} ignores objective")

            item = attrs.get("item")
            if spec.get("requires_item"):
                if not item:
                    errors.append(f"Callout {label_id} type {type_id} requires item=item-... from the assessment bank")
                elif not ITEM_RE.match(item):
                    errors.append(f"Callout {label_id} item {item} is not a valid item id")
            elif item:
                errors.append(f"Callout {label_id} type {type_id} must not reference an item")

            reveal_rules = spec.get("reveal", [])
            reveal = attrs.get("reveal")
            if reveal_rules:
                effective = reveal or spec.get("default_reveal", {}).get(mode)
                if effective is None:
                    errors.append(f"Callout {label_id} type {type_id} requires reveal= from {reveal_rules}")
                elif effective not in reveal_rules:
                    errors.append(f"Callout {label_id} reveal {effective} is not allowed for type {type_id}; use {reveal_rules}")
                record["reveal"] = effective
                own_chapter = chapter_from_callout_id(callout_id) or chapter_id or "<unknown>"
                if type_id == "quick-check" and effective == "chapter-end":
                    chapter_end_chapters.add(own_chapter)
                if type_id == "quick-check" and effective == "book-end":
                    book_end_needed = True
                if type_id == "quick-check" and item and ITEM_RE.match(item):
                    quick_checks.append(
                        {"callout_id": label_id, "item": item, "reveal": str(effective), "chapter": own_chapter}
                    )
                if type_id == "reflect" and effective == "chapter-end":
                    chapter_end_chapters.add(own_chapter)
                    chapter_end_reflections.append((label_id, own_chapter))
            elif reveal:
                errors.append(f"Callout {label_id} type {type_id} does not take reveal")

            target = attrs.get("for")
            if requires_for:
                if not target or not FOR_RE.match(target):
                    errors.append(f"Callout {label_id} type {type_id} requires for=ch-NN or for=book")
                else:
                    entries, unkeyed = parse_answer_key(block["body"])
                    answer_keys.setdefault(target, {}).update(entries)
                    record["entries"] = sorted(entries)
                    if unkeyed:
                        warnings.append(
                            f"Answer-key {label_id} has {len(unkeyed)} line(s) that are not keyed entries; "
                            "write each key as '- item-chNN-NNN: ...' or '- callout-chNN-NN: ...'"
                        )
            elif target:
                errors.append(f"Callout {label_id} type {type_id} does not take for=")

            if not any(line.strip() for line in block["body"]) and not requires_for:
                errors.append(f"Callout {label_id} has an empty body")

            if placement == "opener":
                key = chapter_from_callout_id(callout_id) or chapter_id or "<unknown>"
                opener_counts[key] = opener_counts.get(key, 0) + 1

        if (
            previous_block is not None
            and previous_block["kind"] == "callout"
            and not requires_for_type(types, previous_block)
            and not requires_for_type(types, block)
        ):
            warnings.append(
                f"Callouts {previous_block['id'] or '<no id>'} and {label_id} are adjacent without prose between them"
            )
        previous_block = block
        callouts.append(record)

    for chapter in sorted(chapter_end_chapters):
        if chapter not in answer_keys:
            errors.append(
                f"Quick checks or reflections in {chapter} reveal at chapter-end "
                f"but no answer-key with for={chapter} exists"
            )
    if book_end_needed and chapter_id is None and "book" not in answer_keys:
        errors.append("Quick checks reveal at book-end but no answer-key with for=book exists in the book manuscript")

    referenced: dict[str, set[str]] = {}
    placements_by_item: dict[str, list[str]] = {}
    for check in quick_checks:
        check_id, item = check["callout_id"], check["item"]
        placements_by_item.setdefault(item, []).append(check_id)
        if item_ids is not None and item not in item_ids:
            errors.append(f"Quick check {check_id} item {item} is not in the assessment bank")
        if check["reveal"] == "chapter-end":
            target = check["chapter"]
            referenced.setdefault(target, set()).add(item)
            if target in answer_keys and item not in answer_keys[target]:
                errors.append(
                    f"Quick check {check_id} reveals at chapter-end but answer-key for={target} has no entry for {item}"
                )
        elif check["reveal"] == "book-end":
            if chapter_id is None:
                referenced.setdefault("book", set()).add(item)
                if "book" in answer_keys and item not in answer_keys["book"]:
                    errors.append(
                        f"Quick check {check_id} reveals at book-end but answer-key for=book has no entry for {item}"
                    )
            else:
                warnings.append(
                    f"Quick check {check_id} reveals at book-end; its key belongs to the for=book answer-key "
                    "outside this chapter manuscript"
                )
    for reflection_id, chapter in chapter_end_reflections:
        referenced.setdefault(chapter, set()).add(reflection_id)
        if chapter in answer_keys and reflection_id not in answer_keys[chapter]:
            errors.append(
                f"Reflection {reflection_id} reveals at chapter-end but answer-key for={chapter} "
                f"has no discussion entry for {reflection_id}"
            )
    for item, placed_by in sorted(placements_by_item.items()):
        if len(placed_by) > 1:
            warnings.append(f"Item {item} is placed by quick checks {', '.join(placed_by)}; place each item once")
    for target, entries in sorted(answer_keys.items()):
        if target == "book" and chapter_id is not None:
            continue
        for entry_id in sorted(entries):
            if entry_id not in referenced.get(target, set()):
                warnings.append(
                    f"Answer-key for={target} entry {entry_id} has no quick check or reflection pointing to it"
                )
    for chapter, count in sorted(opener_counts.items()):
        if count > 1:
            warnings.append(f"Chapter {chapter} has {count} opener callouts; at most one is expected")

    counted = [item for item in callouts if item["type"] != "answer-key"]
    if density in DENSITIES and counted:
        threshold = int(catalog.get("density_minimum_words_per_callout", {}).get(density, 0))
        ratio = prose_words / len(counted)
        if threshold and ratio < threshold:
            warnings.append(
                f"Callout density: {prose_words} prose words for {len(counted)} callouts is below the "
                f"{density} ceiling of {threshold} words per callout"
            )

    by_type: dict[str, int] = {}
    for item in callouts:
        if item["type"]:
            by_type[item["type"]] = by_type.get(item["type"], 0) + 1
    return {
        "status": "fail" if errors else "pass",
        "mode": mode,
        "locale": locale,
        "chapter_id": chapter_id,
        "catalog_version": catalog.get("catalog_version"),
        "errors": errors,
        "warnings": warnings,
        "callout_ids": [item["callout_id"] for item in callouts if item["callout_id"]],
        "callouts": callouts,
        "counts": {"callouts": len(callouts), "prose_words": prose_words, "by_type": by_type},
        "item_bank": None if item_ids is None else {"paths": [], "item_count": len(item_ids)},
    }


def requires_for_type(types: dict[str, dict[str, Any]], block: dict[str, Any]) -> bool:
    spec = types.get(block.get("attrs", {}).get("type", ""))
    return bool(spec and spec.get("requires_for"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manuscript", type=Path, required=True, help="Markdown manuscript to inspect")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--locale", choices=LOCALES, required=True)
    parser.add_argument("--chapter-id", help="Chapter scope; omit for a whole-book manuscript")
    parser.add_argument("--density", choices=DENSITIES, help="Project visual_density used as the callout ceiling")
    parser.add_argument("--architecture", type=Path, help="book-architecture.json for objective cross-checks")
    parser.add_argument(
        "--items", type=Path, action="append", default=None, metavar="PATH",
        help="Assessment item bank (items.<locale>.yaml or JSON); repeatable. Every quick-check item= must exist in it.",
    )
    parser.add_argument("--catalog", type=Path, default=default_catalog_path())
    parser.add_argument("--print-ids", action="store_true", help="Print callout IDs one per line instead of JSON")
    args = parser.parse_args(argv)

    try:
        catalog = load_json(args.catalog)
        architecture = load_json(args.architecture) if args.architecture else None
        item_ids = load_item_ids(args.items) if args.items else None
        text = args.manuscript.read_text(encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "errors": [str(exc)], "warnings": []}, indent=2))
        return 1
    report = inspect_manuscript(
        text, mode=args.mode, locale=args.locale, catalog=catalog, chapter_id=args.chapter_id,
        density=args.density, architecture=architecture, item_ids=item_ids,
    )
    if report["item_bank"] is not None:
        report["item_bank"]["paths"] = [str(path) for path in args.items]
    if args.print_ids:
        for callout_id in report["callout_ids"]:
            print(callout_id)
        for error in report["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
