#!/usr/bin/env python3
"""Perform dependency-free structural and safety checks on an SVG.

The result does not certify factual accuracy, accessibility, rendering fidelity,
color contrast, font embedding, or publication conformance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


FORBIDDEN_ELEMENTS = {"script", "foreignObject", "iframe", "object", "embed"}
HREF_NAMES = {"href", "{http://www.w3.org/1999/xlink}href"}
VIEWBOX_RE = re.compile(
    r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
    r"[ ,]+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
    r"[ ,]+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
    r"[ ,]+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*$"
)
URL_REF_RE = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", re.IGNORECASE)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def inspect_svg(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    report: dict[str, object] = {
        "file": str(path),
        "scope": "XML structure, self-containment, active-content checks, IDs, and basic accessibility metadata",
        "errors": errors,
        "warnings": warnings,
    }

    try:
        raw = path.read_bytes()
    except OSError as exc:
        errors.append(f"cannot read file: {exc}")
        report["status"] = "fail"
        return report

    report["bytes"] = len(raw)
    report["sha256"] = hashlib.sha256(raw).hexdigest()
    upper = raw.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        errors.append("DOCTYPE and ENTITY declarations are not allowed")

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        errors.append(f"XML parse error: {exc}")
        report["status"] = "fail"
        return report

    if local_name(root.tag) != "svg":
        errors.append("root element is not svg")
    if not root.tag.startswith("{http://www.w3.org/2000/svg}"):
        errors.append("root SVG namespace is missing or incorrect")

    view_box = root.get("viewBox")
    match = VIEWBOX_RE.match(view_box or "")
    if not match:
        errors.append("root must have a numeric four-value viewBox")
    else:
        values = [float(value) for value in match.groups()]
        if values[2] <= 0 or values[3] <= 0:
            errors.append("viewBox width and height must be positive")
        report["viewBox"] = values

    ids: dict[str, str] = {}
    references: list[tuple[str, str]] = []
    counts: dict[str, int] = {}
    text_values: list[str] = []
    title_ids: list[str] = []
    desc_ids: list[str] = []

    for element in root.iter():
        name = local_name(element.tag)
        counts[name] = counts.get(name, 0) + 1
        if name in FORBIDDEN_ELEMENTS:
            errors.append(f"forbidden active or nonportable element: {name}")
        element_id = element.get("id")
        if element_id:
            if element_id in ids:
                errors.append(f"duplicate id: {element_id}")
            ids[element_id] = name
        if name == "title" and (element.text or "").strip():
            if element_id:
                title_ids.append(element_id)
        if name == "desc" and (element.text or "").strip():
            if element_id:
                desc_ids.append(element_id)
        if name == "text":
            value = "".join(element.itertext()).strip()
            text_values.append(value)
            if not value:
                warnings.append("empty text element found")

        for attr_name, attr_value in element.attrib.items():
            attr_local = local_name(attr_name).lower()
            if attr_local.startswith("on"):
                errors.append(f"event-handler attribute is not allowed: {attr_local}")
            if attr_name in HREF_NAMES or attr_local == "href":
                if not attr_value.startswith("#"):
                    errors.append(f"external or embedded href is not allowed: {attr_value}")
                else:
                    references.append((f"{name}@href", attr_value[1:]))
            for _, target in URL_REF_RE.findall(attr_value):
                if target.startswith("#"):
                    references.append((f"{name}@{attr_local}", target[1:]))
                else:
                    errors.append(f"external URL reference is not allowed: {target}")
            lowered = attr_value.strip().lower()
            if "javascript:" in lowered or "@import" in lowered:
                errors.append(f"active or external content found in {name}@{attr_local}")

        if name == "style":
            style_text = "".join(element.itertext())
            for _, target in URL_REF_RE.findall(style_text):
                if target.startswith("#"):
                    references.append(("style", target[1:]))
                else:
                    errors.append(f"external URL reference is not allowed in style: {target}")
            lowered_style = style_text.lower()
            if "@import" in lowered_style or "javascript:" in lowered_style:
                errors.append("style contains an import or active URL")

    if not title_ids:
        errors.append("a nonempty title element with an id is required")
    if not desc_ids:
        errors.append("a nonempty desc element with an id is required")
    if root.get("role") != "img":
        errors.append('root role must be "img"')

    labelled = (root.get("aria-labelledby") or "").split()
    if not labelled:
        errors.append("root aria-labelledby is required")
    else:
        for target in labelled:
            if target not in ids:
                errors.append(f"aria-labelledby references missing id: {target}")
        if title_ids and not any(target in title_ids for target in labelled):
            errors.append("aria-labelledby must reference the title id")
        if desc_ids and not any(target in desc_ids for target in labelled):
            errors.append("aria-labelledby must reference the desc id")

    for context, target in references:
        if target not in ids:
            errors.append(f"{context} references missing id: {target}")

    if counts.get("image", 0):
        warnings.append("embedded image elements require separate rights and resolution review")
    if not any(text_values):
        warnings.append("no visible text labels were found; confirm this is intentional")

    report["element_counts"] = counts
    report["id_count"] = len(ids)
    report["status"] = "fail" if errors else "pass"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a publication-oriented SVG subset.")
    parser.add_argument("svg", type=Path)
    args = parser.parse_args()
    report = inspect_svg(args.svg)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
