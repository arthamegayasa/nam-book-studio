#!/usr/bin/env python3
"""Validate the Nam Book Studio package using the Python standard library."""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EXPECTED_SKILLS = {
    "asknam",
    "nam-book-architect",
    "nam-book-assess",
    "nam-book-diagram",
    "nam-book-edit",
    "nam-book-illustrate",
    "nam-book-illustration-setup",
    "nam-book-localize",
    "nam-book-publish",
    "nam-book-research",
    "nam-book-teach",
    "nam-book-validate",
    "nam-book-visuals",
    "nam-book-voice",
    "nam-book-write",
}


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
    if len(parts) < 3:
        return {}
    result: dict[str, str] = {}
    for line in parts[1].splitlines():
        match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*?)\s*$", line)
        if match:
            result[match.group(1)] = match.group(2).strip('"\'')
    return result


def png_color_type(path: Path) -> int:
    with path.open("rb") as handle:
        header = handle.read(26)
    if len(header) < 26 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    if header[12:16] != b"IHDR":
        raise ValueError("missing IHDR")
    struct.unpack(">II", header[16:24])
    return header[25]


def load_catalog(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("skills", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError("catalog must contain a skills array")
    names: set[str] = set()
    for entry in entries:
        if isinstance(entry, str):
            name = entry
        elif isinstance(entry, dict):
            name = entry.get("id") or entry.get("name") or entry.get("skill")
        else:
            raise ValueError("catalog entries must be strings or objects")
        if not isinstance(name, str) or not name:
            raise ValueError("catalog entry lacks id/name")
        names.add(name)
    return names


def local_markdown_targets(path: Path) -> list[Path]:
    """Return repository-local Markdown link targets declared by *path*."""

    text = path.read_text(encoding="utf-8")
    targets: list[Path] = []
    for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        raw = match.group(1).strip().strip("<>")
        # Drop optional Markdown titles while preserving ordinary relative paths.
        raw = re.split(r'\s+["\']', raw, maxsplit=1)[0]
        parsed = urlparse(raw)
        if parsed.scheme or raw.startswith(("#", "//")):
            continue
        relative = unquote(raw.split("#", 1)[0])
        if relative:
            targets.append((path.parent / relative).resolve())
    return targets


def validate() -> list[str]:
    errors: list[str] = []

    manifest_path = ROOT / ".codex-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report every structural failure
        errors.append(f"plugin manifest is unreadable: {exc}")
        manifest = {}

    if manifest.get("name") != "nam-book-studio":
        errors.append("plugin name must be nam-book-studio")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", ""))):
        errors.append("plugin version must be strict semver")
    if manifest.get("skills") != "./skills/":
        errors.append("plugin skills path must be ./skills/")
    if not manifest.get("author", {}).get("name"):
        errors.append("plugin author.name is required")
    default_prompts = manifest.get("interface", {}).get("defaultPrompt", [])
    if isinstance(default_prompts, str):
        default_prompts = [default_prompts]
    if not isinstance(default_prompts, list) or not any(
        isinstance(prompt, str) and "$asknam" in prompt for prompt in default_prompts
    ):
        errors.append("plugin defaultPrompt must explicitly invoke $asknam")

    actual = {path.name for path in SKILLS.iterdir() if path.is_dir()}
    if actual != EXPECTED_SKILLS:
        errors.append(
            "skill directories differ from expected set: "
            f"missing={sorted(EXPECTED_SKILLS - actual)}, extra={sorted(actual - EXPECTED_SKILLS)}"
        )

    for name in sorted(actual):
        skill_dir = SKILLS / name
        skill_path = skill_dir / "SKILL.md"
        metadata_path = skill_dir / "agents" / "openai.yaml"
        if not skill_path.is_file():
            errors.append(f"{name}: SKILL.md is missing")
            continue
        text = skill_path.read_text(encoding="utf-8")
        meta = frontmatter(text)
        if meta.get("name") != name:
            errors.append(f"{name}: frontmatter name does not match directory")
        if len(meta.get("description", "").strip()) < 20:
            errors.append(f"{name}: description is missing or too short")
        if "TODO" in text or "[TODO:" in text:
            errors.append(f"{name}: unfinished TODO remains in SKILL.md")
        if not metadata_path.is_file():
            errors.append(f"{name}: agents/openai.yaml is missing")
        else:
            metadata = metadata_path.read_text(encoding="utf-8")
            if f"${name}" not in metadata:
                errors.append(f"{name}: default_prompt must explicitly mention ${name}")
            implicit_false = bool(
                re.search(r"allow_implicit_invocation:\s*false", metadata, re.IGNORECASE)
            )
            if name == "asknam" and not implicit_false:
                errors.append("asknam must be explicit-only")
            if name != "asknam" and implicit_false:
                errors.append(f"{name}: specialists must remain model-invoked")

        for path in skill_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py"}:
                content = path.read_text(encoding="utf-8")
                if "[TODO:" in content:
                    errors.append(f"{path.relative_to(ROOT)}: scaffold placeholder remains")

    catalog_path = SKILLS / "asknam" / "references" / "skill-catalog.json"
    try:
        catalog_names = load_catalog(catalog_path)
        if catalog_names != EXPECTED_SKILLS:
            errors.append(
                "skill catalog differs from directories: "
                f"missing={sorted(EXPECTED_SKILLS - catalog_names)}, "
                f"extra={sorted(catalog_names - EXPECTED_SKILLS)}"
            )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"skill catalog is unreadable: {exc}")

    for schema_path in sorted((ROOT / "schemas").glob("*.json")):
        try:
            json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{schema_path.relative_to(ROOT)} is invalid JSON: {exc}")

    for markdown_path in sorted(ROOT.rglob("*.md")):
        for target in local_markdown_targets(markdown_path):
            if not target.exists():
                errors.append(
                    f"{markdown_path.relative_to(ROOT)} links to missing local target: "
                    f"{target}"
                )

    icon_path = ROOT / "assets" / "nam-icon.png"
    try:
        if png_color_type(icon_path) not in {4, 6}:
            errors.append("assets/nam-icon.png must contain an alpha channel")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"plugin icon is invalid: {exc}")

    sheet = (
        ROOT
        / "skills"
        / "nam-book-illustrate"
        / "assets"
        / "nam-v1"
        / "nam-character-sheet.png"
    )
    if not sheet.is_file():
        errors.append("canonical Nam character sheet is missing")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"Nam Book Studio validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Nam Book Studio validation passed: {len(EXPECTED_SKILLS)} skills checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
