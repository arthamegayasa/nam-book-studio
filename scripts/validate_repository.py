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
PLUGIN_NAME = "nam-book-studio"
SEMVER = re.compile(r"\d+\.\d+\.\d+")
EXPECTED_SKILLS = {
    "asknam",
    "nam-book-architect",
    "nam-book-assess",
    "nam-book-design",
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

# Codex-style `$skill` references are host-specific. They are allowed only in the
# files that Codex itself reads, in the README's Codex examples, and in this
# validator; every other file names a skill by its bare backticked name.
HOST_REFERENCE = re.compile(r"\$(?:asknam|nam-book-[a-z-]+)")
HOST_SPECIFIC_ALLOWED = {"README.md", ".codex-plugin/plugin.json", "scripts/validate_repository.py"}
SCANNED_CODE_SUFFIXES = {".json", ".yaml", ".yml", ".py"}
SCANNED_CODE_FOLDERS = ("skills", "docs")


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


SKIPPED_DIRECTORIES = {"tmp", "output", "build", "dist", ".scratch", ".git", ".claude", "__pycache__"}


def _skipped(root: Path, path: Path) -> bool:
    return any(part in SKIPPED_DIRECTORIES for part in path.relative_to(root).parts[:-1])


def markdown_files(root: Path) -> list[Path]:
    """Return the Markdown files under *root* that belong to the package.

    Directories that Git ignores or that hold scratch notes (``tmp/``, ``output/``,
    ``build/``, ``dist/``, ``.scratch/``, ``.git/``, ``.claude/``, ``__pycache__/``)
    are skipped at any depth so local experiments and harness worktrees cannot
    fail the repository checks.
    """

    return [path for path in sorted(root.rglob("*.md")) if not _skipped(root, path)]


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


def host_specific_references(root: Path) -> list[tuple[Path, int, str]]:
    """Return ``(path, line_number, line)`` for every Codex-style ``$skill`` reference
    outside the files allowed to carry one.

    Every Markdown file is scanned (except the root README, whose Codex examples
    are the documented exception), plus JSON, YAML, and Python files under
    ``skills/`` and ``docs/``. ``agents/openai.yaml`` files are Codex metadata and
    stay allowed.
    """

    candidates = list(markdown_files(root))
    for folder in SCANNED_CODE_FOLDERS:
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in SCANNED_CODE_SUFFIXES and not _skipped(root, path):
                candidates.append(path)

    hits: list[tuple[Path, int, str]] = []
    seen: set[str] = set()
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        if relative in seen:
            continue
        seen.add(relative)
        if relative in HOST_SPECIFIC_ALLOWED:
            continue
        if path.name == "openai.yaml" and path.parent.name == "agents":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if HOST_REFERENCE.search(line):
                hits.append((path, number, line.strip()))
    return hits


def check_skill_metadata(name: str, skill_text: str, openai_text: str | None) -> list[str]:
    """Check one skill's SKILL.md frontmatter and Codex metadata for both hosts.

    AskNam must be explicit-only everywhere: ``disable-model-invocation: true`` for
    Claude Code and ``allow_implicit_invocation: false`` for Codex. Specialists
    must stay model-invoked in both hosts and say so explicitly in Codex metadata.
    """

    errors: list[str] = []
    meta = frontmatter(skill_text)
    if meta.get("name") != name:
        errors.append(f"{name}: frontmatter name does not match directory")
    if len(meta.get("description", "").strip()) < 20:
        errors.append(f"{name}: description is missing or too short")
    if "TODO" in skill_text or "[TODO:" in skill_text:
        errors.append(f"{name}: unfinished TODO remains in SKILL.md")

    claude_explicit_only = meta.get("disable-model-invocation", "").strip().lower() == "true"
    if name == "asknam" and not claude_explicit_only:
        errors.append("asknam: SKILL.md frontmatter must declare disable-model-invocation: true (explicit-only in Claude Code)")
    if name != "asknam" and "disable-model-invocation" in meta:
        errors.append(f"{name}: specialists must not declare disable-model-invocation; they stay model-invoked in Claude Code")

    if openai_text is None:
        errors.append(f"{name}: agents/openai.yaml is missing")
        return errors
    if f"${name}" not in openai_text:
        errors.append(f"{name}: default_prompt must explicitly mention ${name}")
    implicit_false = bool(re.search(r"allow_implicit_invocation:\s*false", openai_text, re.IGNORECASE))
    implicit_true = bool(re.search(r"allow_implicit_invocation:\s*true", openai_text, re.IGNORECASE))
    if name == "asknam" and not implicit_false:
        errors.append("asknam must be explicit-only (allow_implicit_invocation: false in agents/openai.yaml)")
    if name != "asknam":
        if implicit_false:
            errors.append(f"{name}: specialists must remain model-invoked")
        elif not implicit_true:
            errors.append(f"{name}: agents/openai.yaml must declare allow_implicit_invocation: true")
    return errors


def _load_json(path: Path, label: str, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"{label} is missing")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report every structural failure
        errors.append(f"{label} is unreadable: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    return payload


def check_codex_manifest(root: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    manifest = _load_json(root / ".codex-plugin" / "plugin.json", ".codex-plugin/plugin.json", errors) or {}
    if manifest.get("name") != PLUGIN_NAME:
        errors.append(f"plugin name must be {PLUGIN_NAME}")
    if not SEMVER.fullmatch(str(manifest.get("version", ""))):
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
    return manifest, errors


def check_claude_manifests(root: Path) -> list[str]:
    """Check the Claude Code plugin and marketplace manifests against the Codex one.

    Both hosts package the same ``skills/`` directory, so the Claude manifest must
    carry the Codex manifest's name and version, and the marketplace must list
    exactly that plugin with this repository root as its source.
    """

    errors: list[str] = []
    codex_version: str | None = None
    codex_path = root / ".codex-plugin" / "plugin.json"
    if codex_path.is_file():
        try:
            codex_version = str(json.loads(codex_path.read_text(encoding="utf-8")).get("version", ""))
        except Exception:  # noqa: BLE001 - the Codex manifest check reports this
            codex_version = None

    plugin = _load_json(root / ".claude-plugin" / "plugin.json", ".claude-plugin/plugin.json", errors)
    if plugin is not None:
        if plugin.get("name") != PLUGIN_NAME:
            errors.append(f".claude-plugin/plugin.json name must be {PLUGIN_NAME}")
        version = str(plugin.get("version", ""))
        if not SEMVER.fullmatch(version):
            errors.append(".claude-plugin/plugin.json version must be strict semver")
        elif codex_version is not None and version != codex_version:
            errors.append(
                f".claude-plugin/plugin.json version {version} must equal the Codex manifest version {codex_version}"
            )
        skills = plugin.get("skills")
        if skills is not None and skills not in ("./skills/", "./skills", ["./skills/"], ["./skills"]):
            errors.append(".claude-plugin/plugin.json skills must point at ./skills/ when declared")

    marketplace = _load_json(root / ".claude-plugin" / "marketplace.json", ".claude-plugin/marketplace.json", errors)
    if marketplace is not None:
        if marketplace.get("name") != PLUGIN_NAME:
            errors.append(f".claude-plugin/marketplace.json name must be {PLUGIN_NAME}")
        if not isinstance(marketplace.get("owner"), dict) or not marketplace["owner"].get("name"):
            errors.append(".claude-plugin/marketplace.json owner.name is required")
        plugins = marketplace.get("plugins")
        entries = (
            [item for item in plugins if isinstance(item, dict) and item.get("name") == PLUGIN_NAME]
            if isinstance(plugins, list)
            else []
        )
        if len(entries) != 1:
            errors.append(f".claude-plugin/marketplace.json must list exactly one plugin named {PLUGIN_NAME}")
        else:
            entry = entries[0]
            if entry.get("source") != "./":
                errors.append(".claude-plugin/marketplace.json plugin source must be ./ (this repository root)")
            entry_version = entry.get("version")
            if codex_version is not None and entry_version not in (None, codex_version):
                errors.append(
                    f".claude-plugin/marketplace.json plugin version {entry_version} must equal the Codex manifest version {codex_version}"
                )
    return errors


def validate() -> list[str]:
    errors: list[str] = []

    _, manifest_errors = check_codex_manifest(ROOT)
    errors.extend(manifest_errors)
    errors.extend(check_claude_manifests(ROOT))

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
        metadata = metadata_path.read_text(encoding="utf-8") if metadata_path.is_file() else None
        errors.extend(check_skill_metadata(name, skill_path.read_text(encoding="utf-8"), metadata))

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

    for markdown_path in markdown_files(ROOT):
        for target in local_markdown_targets(markdown_path):
            if not target.exists():
                errors.append(
                    f"{markdown_path.relative_to(ROOT)} links to missing local target: "
                    f"{target}"
                )

    for path, number, line in host_specific_references(ROOT):
        errors.append(
            f"{path.relative_to(ROOT).as_posix()}:{number}: host-specific skill reference in prose ({line}); "
            "use the bare skill name"
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
