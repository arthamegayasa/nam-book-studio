#!/usr/bin/env python3
"""Write a project's design tokens into a diagram's first ``<style>`` block.

The design spec supplies the label typography (``typography.labels``) and the
color roles (``color``); the illustration setup may override roles through
``visual_tokens.palette``. Only the known role selectors of the first style
block change. Geometry, IDs, text, and every other declaration stay untouched.
The script never certifies rendering, contrast, or factual accuracy.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


STYLE_RE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.S)
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
TOKEN_RE = re.compile(
    r"/\*.*?\*/|(?P<lead>\s*)(?P<selector>[^\s{}/][^{}/]*?)\s*\{(?P<body>[^{}]*)\}",
    re.S,
)
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
FONT_SIZE_RE = re.compile(r"\b(\d+(?:\.\d+)?(?:px|pt|em|rem|%))\b")

# Bare palette values in the setup are read in this order.
PALETTE_ORDER = ["ink", "paper", "accent", "muted", "neutral", "process", "outcome"]
GENERIC_FAMILIES = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "math", "emoji",
}
# selector -> {property: role}
ROLE_TARGETS: dict[str, dict[str, str]] = {
    ".canvas": {"fill": "paper"},
    ".node": {"stroke": "ink"},
    ".input": {"fill": "neutral"},
    ".process": {"fill": "process"},
    ".outcome": {"fill": "outcome"},
    ".edge": {"stroke": "muted"},
    ".arrowhead": {"fill": "muted"},
    ".label": {"fill": "ink"},
}


def is_hex(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_RE.match(value.strip()))


def parse_hex(value: str) -> tuple[int, int, int]:
    digits = value.strip().lstrip("#")
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def mix(color: str, base: str, weight: float) -> str:
    """Return ``weight`` of ``color`` blended over ``base`` as lowercase hex."""

    top = parse_hex(color)
    bottom = parse_hex(base)
    blended = tuple(round(t * weight + b * (1 - weight)) for t, b in zip(top, bottom))
    return "#" + "".join(f"{max(0, min(255, channel)):02x}" for channel in blended)


def palette_overrides(setup: dict[str, Any] | None) -> tuple[dict[str, str], list[str]]:
    """Read role overrides from ``visual_tokens.palette``.

    Objects name their role (``{"role": "ink", "value": "#222222"}``); bare values
    are mapped by position in ``PALETTE_ORDER``. Unusable entries are reported.
    """

    tokens = (setup or {}).get("visual_tokens") or {}
    palette = tokens.get("palette") or []
    overrides: dict[str, str] = {}
    ignored: list[str] = []
    if not isinstance(palette, list):
        return overrides, [f"palette is not a list: {palette!r}"]
    position = 0
    for entry in palette:
        if isinstance(entry, dict):
            role = str(entry.get("role", "")).strip().lower()
            value = entry.get("value") or entry.get("hex") or entry.get("color")
            if role in PALETTE_ORDER and is_hex(value):
                overrides[role] = str(value).strip().lower()
            else:
                ignored.append(json.dumps(entry, sort_keys=True))
        else:
            if is_hex(entry) and position < len(PALETTE_ORDER):
                overrides[PALETTE_ORDER[position]] = str(entry).strip().lower()
            else:
                ignored.append(repr(entry))
            position += 1
    return overrides, ignored


def resolve_roles(design_spec: dict[str, Any], setup: dict[str, Any] | None = None) -> tuple[dict[str, str], list[str]]:
    color = design_spec.get("color") or {}
    roles: dict[str, str] = {}
    for role in ("paper", "ink", "accent", "muted"):
        if is_hex(color.get(role)):
            roles[role] = color[role].strip().lower()
    if is_hex(color.get("tint")):
        roles["neutral"] = color["tint"].strip().lower()
    overrides, ignored = palette_overrides(setup)
    roles.update(overrides)
    ink = roles.setdefault("ink", "#000000")
    paper = roles.setdefault("paper", "#ffffff")
    accent = roles.setdefault("accent", ink)
    roles.setdefault("muted", mix(ink, paper, 0.6))
    roles.setdefault("neutral", mix(ink, paper, 0.08))
    roles.setdefault("process", mix(accent, paper, 0.25))
    roles.setdefault("outcome", mix(accent, paper, 0.5))
    return roles, ignored


def quote_family(name: str) -> str:
    if name in GENERIC_FAMILIES or re.fullmatch(r"[A-Za-z-]+", name):
        return name
    return '"' + name.replace('"', "") + '"'


def label_font(design_spec: dict[str, Any]) -> tuple[str | None, str | None]:
    labels = (design_spec.get("typography") or {}).get("labels") or {}
    names: list[str] = []
    for candidate in [labels.get("family"), *(labels.get("fallbacks") or [])]:
        text = str(candidate or "").strip()
        if text and text not in names:
            names.append(text)
    family = None
    if names:
        if names[-1] not in GENERIC_FAMILIES:
            names.append("sans-serif")
        family = ", ".join(quote_family(name) for name in names)
    weight = labels.get("weight")
    return family, (str(weight) if weight not in (None, "") else None)


def parse_declarations(body: str) -> list[tuple[str, str]]:
    declarations: list[tuple[str, str]] = []
    for part in body.split(";"):
        if ":" in part:
            prop, value = part.split(":", 1)
            if prop.strip():
                declarations.append((prop.strip(), value.strip()))
    return declarations


def set_declaration(declarations: list[tuple[str, str]], prop: str, value: str) -> None:
    for index, (existing, _) in enumerate(declarations):
        if existing == prop:
            declarations[index] = (prop, value)
            return
    declarations.append((prop, value))


def expand_font_shorthand(declarations: list[tuple[str, str]]) -> None:
    """Replace a ``font`` shorthand with longhands so family and weight can change."""

    for index, (prop, value) in enumerate(declarations):
        if prop != "font":
            continue
        size = FONT_SIZE_RE.search(value)
        weight = re.search(r"\b(\d{3}|bold|normal)\b", value.split(size.group(0), 1)[0] if size else value)
        del declarations[index]
        if weight:
            set_declaration(declarations, "font-weight", weight.group(1))
        if size:
            set_declaration(declarations, "font-size", size.group(1))
        return


def parse_style(svg_text: str) -> dict[str, dict[str, str]]:
    """Return ``{selector: {property: value}}`` for the first style block."""

    match = STYLE_RE.search(svg_text)
    if not match:
        return {}
    rules: dict[str, dict[str, str]] = {}
    for token in TOKEN_RE.finditer(COMMENT_RE.sub("", match.group(2))):
        if token.group("selector") is None:
            continue
        selector = " ".join(token.group("selector").split())
        rules[selector] = dict(parse_declarations(token.group("body")))
    return rules


def apply_tokens(svg_text: str, design_spec: dict[str, Any], setup: dict[str, Any] | None = None) -> str:
    roles, _ = resolve_roles(design_spec, setup)
    family, weight = label_font(design_spec)

    def rewrite_rule(token: re.Match[str]) -> str:
        if token.group("selector") is None:
            return token.group(0)
        selector = " ".join(token.group("selector").split())
        targets = ROLE_TARGETS.get(selector)
        if targets is None:
            return token.group(0)
        declarations = parse_declarations(token.group("body"))
        if selector == ".label":
            expand_font_shorthand(declarations)
            if family:
                set_declaration(declarations, "font-family", family)
            if weight:
                set_declaration(declarations, "font-weight", weight)
        for prop, role in targets.items():
            set_declaration(declarations, prop, roles[role])
        body = " ".join(f"{prop}: {value};" for prop, value in declarations)
        return f"{token.group('lead')}{selector} {{ {body} }}"

    def rewrite_block(match: re.Match[str]) -> str:
        return match.group(1) + TOKEN_RE.sub(rewrite_rule, match.group(2)) + match.group(3)

    return STYLE_RE.sub(rewrite_block, svg_text, count=1)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write design-spec and setup tokens into an SVG diagram's style block.")
    parser.add_argument("--svg", type=Path, required=True, help="SVG master to tokenize")
    parser.add_argument("--design-spec", type=Path, required=True, help="design_spec JSON")
    parser.add_argument("--setup", type=Path, help="illustration_setup JSON with visual_tokens.palette")
    parser.add_argument("--out", type=Path, required=True, help="output path (may equal --svg)")
    args = parser.parse_args(argv)

    svg_text = args.svg.read_text(encoding="utf-8")
    if not STYLE_RE.search(svg_text):
        print(json.dumps({"error": "the SVG has no <style> block to tokenize", "svg": str(args.svg)}), file=sys.stderr)
        return 1
    design_spec = load_json(args.design_spec)
    setup = load_json(args.setup) if args.setup else None
    roles, ignored = resolve_roles(design_spec, setup)
    family, weight = label_font(design_spec)
    result = apply_tokens(svg_text, design_spec, setup)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(result, encoding="utf-8", newline="\n")
    report = {
        "svg": str(args.svg),
        "out": str(args.out),
        "font_family": family,
        "font_weight": weight,
        "roles": roles,
        "ignored_palette_entries": ignored,
        "scope": "first <style> block only; rendering, contrast, and content remain to be reviewed",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
