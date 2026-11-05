#!/usr/bin/env python3
"""Render the design sample chapter through the real publish build path.

The bundled sample chapter uses every callout type in the catalog; this script keeps
only the types the active book mode allows, renders the requested formats with the
publish skill's ``build_deliverables.py`` and the design assets, runs the publish
skill's structural inspector on every output, and writes ``report.json`` beside the
rendered files. ``status`` is ``pass`` only when every requested format rendered and
passed inspection; a missing tool is reported, never papered over with a placeholder.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

SKILLS_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = Path(__file__).resolve().parents[1] / "assets" / "sample-chapter"
LOCALES = ("en-US", "id-ID")


def load_sibling(skill: str, script: str) -> ModuleType:
    """Load a sibling skill's script once; later calls return the same module object."""
    path = SKILLS_ROOT / skill / "scripts" / script
    cached = sys.modules.get(path.stem)
    if cached is not None and Path(getattr(cached, "__file__", "") or "").resolve() == path.resolve():
        return cached
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def filter_callouts_for_mode(text: str, mode: str, catalog: dict[str, Any], inspector: ModuleType) -> tuple[str, list[str]]:
    """Drop callouts whose type the mode does not allow; return the text and dropped IDs."""
    allowed = {item["type_id"] for item in catalog["types"] if mode in item["modes"]}
    kept: list[str] = []
    dropped: list[str] = []
    skipping_depth = 0
    for line in text.splitlines():
        opener = inspector.OPEN_RE.match(line)
        closer = inspector.CLOSE_RE.match(line)
        if skipping_depth:
            if opener:
                skipping_depth += 1
            elif closer:
                skipping_depth -= 1
            continue
        if opener:
            attributes = inspector.parse_attributes(opener.group(2))
            type_id = attributes["attrs"].get("type")
            if "callout" in attributes["classes"] and type_id and type_id not in allowed:
                dropped.append(attributes["id"] or f"<{type_id}>")
                skipping_depth = 1
                continue
        kept.append(line)
    # Collapse the blank-line runs left behind by removed callouts.
    joined = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)) + "\n"
    return joined, dropped


def front_matter_value(text: str, key: str) -> str | None:
    inspector_split = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not inspector_split:
        return None
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", inspector_split.group(1), re.M)
    return match.group(1) if match else None


def render(
    spec_path: Path,
    assets: Path,
    out: Path,
    *,
    locale: str,
    formats: list[str],
    manuscript: Path | None = None,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    inspector = load_sibling("nam-book-teach", "inspect_callouts.py")
    builder = load_sibling("nam-book-publish", "build_deliverables.py")
    deliverable_inspector = load_sibling("nam-book-publish", "inspect_deliverable.py")

    spec = load_json(spec_path)
    catalog = load_json(catalog_path or inspector.default_catalog_path())
    mode = spec["profile"]
    pdf_engine = spec.get("render", {}).get("pdf", {}).get("engine", "chromium")
    out.mkdir(parents=True, exist_ok=True)
    source_dir = out / "source"
    source_dir.mkdir(exist_ok=True)

    if manuscript is None:
        bundled = SAMPLE_DIR / f"{locale}.md"
        text = bundled.read_text(encoding="utf-8")
        shutil.copyfile(SAMPLE_DIR / "figure-placeholder.svg", source_dir / "figure-placeholder.svg")
        sample = {"source": "bundled", "path": str(bundled)}
    else:
        text = manuscript.read_text(encoding="utf-8")
        for asset in manuscript.parent.glob("*.svg"):
            shutil.copyfile(asset, source_dir / asset.name)
        sample = {"source": "chapter", "path": str(manuscript)}
    filtered, dropped = filter_callouts_for_mode(text, mode, catalog, inspector)
    staged = source_dir / "sample.md"
    staged.write_text(filtered, encoding="utf-8", newline="\n")
    sample.update({"mode": mode, "locale": locale, "sha256": sha256_text(filtered), "dropped_callouts": dropped})

    chapter_id = front_matter_value(filtered, "chapter_id")
    callout_report = inspector.inspect_manuscript(
        filtered, mode=mode, locale=locale, catalog=catalog, chapter_id=chapter_id, density=None,
    )
    errors: list[str] = [f"callouts: {item}" for item in callout_report["errors"]]
    limitations: list[str] = []
    checks: list[dict[str, Any]] = []

    proof_title = {"id-ID": "Contoh bab untuk persetujuan desain", "en-US": "Sample chapter for design approval"}[locale]
    manifest = builder.build(
        staged, assets, out, formats, lang=locale, title=proof_title,
        pdf_engine=pdf_engine, resource_paths=[source_dir], toc=False, stem="sample-chapter",
    )
    errors.extend(manifest["errors"])
    limitations.extend(manifest["limitations"])
    if pdf_engine == "chromium" and "pdf" in formats:
        limitations.extend(spec.get("render", {}).get("pdf", {}).get("page_media_limitations", []))

    for fmt, output in manifest["outputs"].items():
        if fmt == "html":
            checks.append({"format": fmt, "inspector": "not-applicable", "warnings": [], "errors": []})
            continue
        file_errors: list[str] = []
        file_warnings: list[str] = []
        path = Path(output["path"])
        if fmt == "docx":
            details = deliverable_inspector.inspect_docx(path, file_errors, file_warnings)
        elif fmt == "epub":
            details = deliverable_inspector.inspect_epub(path, file_errors, file_warnings)
        else:
            details = deliverable_inspector.inspect_pdf(path, file_errors, file_warnings)
        checks.append({
            "format": fmt, "inspector": "fail" if file_errors else "pass",
            "errors": file_errors, "warnings": file_warnings, "details": details,
        })
        errors.extend(f"{fmt}: {item}" for item in file_errors)

    rendered = sorted(fmt for fmt in manifest["outputs"] if fmt in formats)
    missing = sorted(set(formats) - set(rendered))
    status = "pass" if not errors and not missing else "fail"
    report = {
        "status": status,
        "formats": rendered,
        "formats_requested": list(formats),
        "missing_formats": missing,
        "checks": checks,
        "errors": errors,
        "limitations": sorted(set(limitations)),
        "tools": manifest["tools"],
        "sample": sample,
        "callout_inspection": {
            "status": callout_report["status"], "callout_ids": callout_report["callout_ids"],
            "warnings": callout_report["warnings"],
        },
        "spec": {"path": str(spec_path), "sha256": builder.sha256_file(spec_path), "design_version": spec.get("design_version")},
        "assets": {"path": str(assets), "sha256_tree": manifest["inputs"]["assets"]["sha256_tree"]},
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", type=Path, required=True, help="design-spec.json")
    parser.add_argument("--assets", type=Path, required=True, help="generated design assets bundle")
    parser.add_argument("--out", type=Path, required=True, help="proof bundle directory (design/proofs/<artifact_id>)")
    parser.add_argument("--locale", choices=LOCALES, required=True)
    parser.add_argument("--formats", nargs="+", choices=("docx", "epub", "pdf"), required=True)
    parser.add_argument("--manuscript", type=Path, default=None, help="render a registered chapter instead of the bundled sample")
    parser.add_argument("--catalog", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        report = render(
            args.spec, args.assets, args.out, locale=args.locale, formats=args.formats,
            manuscript=args.manuscript, catalog_path=args.catalog,
        )
    except (OSError, ValueError, ImportError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2))
        return 1
    print(json.dumps({key: report[key] for key in ("status", "formats", "errors", "limitations")}, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
