#!/usr/bin/env python3
"""Build DOCX, EPUB, HTML, and PDF deliverables from one Markdown manuscript and a design assets bundle.

The same path renders the design sample chapter and the full book: Pandoc converts the
semantic source with the generated ``callouts.lua`` filter, ``reference.docx``, and CSS;
PDF comes from the standalone HTML through a Chromium-family browser, or from the DOCX
through LibreOffice when the design spec asks for it. Every tool, version, command, and
output hash lands in ``build-manifest.json``. A missing tool is an error, never a placeholder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

FORMATS = ("docx", "epub", "html", "pdf")
NONDETERMINISTIC_FIELDS = [
    "docx: docProps/core.xml dcterms:created and dcterms:modified",
    "epub: OPF dcterms:modified and the generated identifier when none is supplied",
    "pdf: CreationDate, ModDate, and document ID",
]
BROWSER_NAMES = ("chrome", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge")
BROWSER_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)
SOFFICE_NAMES = ("soffice", "libreoffice")
SOFFICE_PATHS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(path: Path) -> str:
    """Order-independent fingerprint of a directory: relative path and content per file."""
    digest = hashlib.sha256()
    for file in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(file.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(file).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def find_tools(env_var: str, names: tuple[str, ...], paths: tuple[str, ...]) -> list[str]:
    """Every usable candidate in preference order; an environment override is the only candidate."""
    override = os.environ.get(env_var)
    if override:
        return [override] if Path(override).exists() or shutil.which(override) else []
    found: list[str] = []
    for name in names:
        located = shutil.which(name)
        if located and located not in found:
            found.append(located)
    for candidate in paths:
        if Path(candidate).is_file() and candidate not in found:
            found.append(candidate)
    return found


def find_tool(env_var: str, names: tuple[str, ...], paths: tuple[str, ...]) -> str | None:
    candidates = find_tools(env_var, names, paths)
    return candidates[0] if candidates else None


def tool_version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or result.stderr or "").strip().splitlines()
    return text[0].strip() if text else None


def pandoc_version(executable: str) -> str | None:
    line = tool_version([executable, "--version"])
    return line.split()[-1] if line else None


def pandoc_major(version: str | None) -> int:
    match = re.match(r"(\d+)", version or "")
    return int(match.group(1)) if match else 0


def discover_tools(pdf_engine: str | None) -> dict[str, Any]:
    pandoc = find_tool("NAM_BOOK_PANDOC", ("pandoc",), ())
    tools: dict[str, Any] = {
        "pandoc": {"path": pandoc, "version": pandoc_version(pandoc) if pandoc else None},
        "platform": platform.platform(),
    }
    if pdf_engine == "libreoffice":
        soffice = find_tool("NAM_BOOK_SOFFICE", SOFFICE_NAMES, SOFFICE_PATHS)
        tools["libreoffice"] = {"path": soffice, "version": tool_version([soffice, "--version"]) if soffice else None}
    elif pdf_engine == "chromium":
        candidates = find_tools("NAM_BOOK_BROWSER", BROWSER_NAMES, BROWSER_PATHS)
        browser = candidates[0] if candidates else None
        version = None
        if browser and platform.system() != "Windows":
            version = tool_version([browser, "--version"])
        tools["chromium"] = {"path": browser, "version": version, "candidates": candidates}
    return tools


def run(command: list[str], manifest: dict[str, Any], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    manifest["commands"].append(command)
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)


def pandoc_common(
    pandoc: str, manuscript: Path, assets: Path, *, lang: str, title: str | None, resource_paths: list[Path],
) -> list[str]:
    paths = [assets, manuscript.parent, *resource_paths]
    command = [pandoc, str(manuscript), "--from", "markdown", "--metadata", f"lang={lang}",
               "--resource-path", os.pathsep.join(str(item) for item in paths)]
    lua = assets / "callouts.lua"
    if lua.is_file():
        command.extend(["--lua-filter", str(lua)])
    if title:
        command.extend(["--metadata", f"title={title}"])
    return command


def build(
    manuscript: Path,
    assets: Path,
    out: Path,
    formats: list[str],
    *,
    lang: str,
    title: str | None = None,
    pdf_engine: str | None = "chromium",
    resource_paths: list[Path] | None = None,
    toc: bool = True,
    stem: str = "book",
) -> dict[str, Any]:
    requested = [item for item in formats if item in FORMATS]
    unknown = [item for item in formats if item not in FORMATS]
    needs_html = "html" in requested or ("pdf" in requested and pdf_engine == "chromium")
    needs_docx = "docx" in requested or ("pdf" in requested and pdf_engine == "libreoffice")
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "generator": "build_deliverables.py",
        "inputs": {
            "manuscript": {"path": str(manuscript), "sha256": sha256_file(manuscript)},
            "assets": {"path": str(assets), "sha256_tree": sha256_tree(assets) if assets.is_dir() else None},
        },
        "lang": lang,
        "formats_requested": list(formats),
        "pdf_engine": pdf_engine if "pdf" in requested else None,
        "tools": discover_tools(pdf_engine if "pdf" in requested else None),
        "commands": [],
        "outputs": {},
        "errors": [f"unsupported format {item}" for item in unknown],
        "limitations": [],
        "nondeterministic_fields": NONDETERMINISTIC_FIELDS,
    }
    pandoc = manifest["tools"]["pandoc"]["path"]
    if not pandoc:
        manifest["errors"].append("pandoc is not installed; install Pandoc 3.x and retry")
        write_manifest(out, manifest)
        return manifest
    major = pandoc_major(manifest["tools"]["pandoc"]["version"])
    common = pandoc_common(pandoc, manuscript, assets, lang=lang, title=title, resource_paths=resource_paths or [])

    def record_output(fmt: str, path: Path) -> None:
        if path.is_file() and path.stat().st_size > 0:
            manifest["outputs"][fmt] = {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
        else:
            manifest["errors"].append(f"{fmt}: no output file was produced")

    if needs_docx:
        docx_path = out / f"{stem}.docx"
        command = [*common, "--to", "docx", "-o", str(docx_path)]
        reference = assets / "reference.docx"
        if reference.is_file():
            command.extend(["--reference-doc", str(reference)])
        else:
            manifest["limitations"].append("docx: no reference.docx in the assets bundle; Pandoc defaults were used")
        if toc:
            command.append("--toc")
        result = run(command, manifest)
        if result.returncode != 0:
            manifest["errors"].append(f"docx: pandoc failed: {result.stderr.strip()[:500]}")
        elif "docx" in requested:
            record_output("docx", docx_path)
        manifest["limitations"].append("docx: side-column callouts render as band paragraphs; update TOC fields after opening")

    if "epub" in requested:
        epub_path = out / f"{stem}.epub"
        command = [*common, "--to", "epub3", "-o", str(epub_path)]
        css = assets / "epub.css"
        if css.is_file():
            command.extend(["--css", str(css)])
        command.append("--split-level=1" if major >= 3 else "--epub-chapter-level=1")
        if toc:
            command.append("--toc")
        result = run(command, manifest)
        if result.returncode != 0:
            manifest["errors"].append(f"epub: pandoc failed: {result.stderr.strip()[:500]}")
        else:
            record_output("epub", epub_path)
        manifest["limitations"].append("epub: reflowable; side-column and band callouts flow inline; run EPUBCheck separately")

    html_path = out / f"{stem}.html"
    if needs_html:
        command = [*common, "--to", "html5", "--standalone", "-o", str(html_path)]
        css = assets / "print.css"
        if css.is_file():
            command.extend(["--css", str(css)])
        command.append("--embed-resources" if major >= 3 else "--self-contained")
        result = run(command, manifest)
        if result.returncode != 0:
            manifest["errors"].append(f"html: pandoc failed: {result.stderr.strip()[:500]}")
        elif "html" in requested:
            record_output("html", html_path)

    if "pdf" in requested:
        pdf_path = out / f"{stem}.pdf"
        if pdf_engine == "chromium":
            candidates = manifest["tools"].get("chromium", {}).get("candidates", [])
            if not candidates:
                manifest["errors"].append(
                    "pdf: no Chromium-family browser found (Google Chrome, Chromium, Microsoft Edge); "
                    "set NAM_BOOK_BROWSER or choose render.pdf.engine libreoffice"
                )
            elif not html_path.is_file():
                manifest["errors"].append("pdf: the HTML intermediate was not produced")
            else:
                attempts: list[str] = []
                for browser in candidates:
                    pdf_path.unlink(missing_ok=True)
                    profile = Path(tempfile.mkdtemp(prefix="nam-book-chromium-"))
                    command = [
                        browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                        f"--user-data-dir={profile}", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri(),
                    ]
                    result = run(command, manifest, timeout=900)
                    shutil.rmtree(profile, ignore_errors=True)
                    if pdf_path.is_file() and pdf_path.stat().st_size > 0:
                        manifest["tools"]["chromium"]["path"] = browser
                        break
                    attempts.append(
                        f"{browser}: exit {result.returncode}, no PDF written"
                        + (f" ({(result.stderr or result.stdout).strip()[:200]})" if (result.stderr or result.stdout).strip() else "")
                    )
                if attempts:
                    manifest["limitations"].append("pdf (chromium): skipped browsers that wrote no PDF: " + "; ".join(attempts))
                if pdf_path.is_file() and pdf_path.stat().st_size > 0:
                    record_output("pdf", pdf_path)
                else:
                    manifest["errors"].append("pdf: every Chromium-family browser exited without writing a PDF; see limitations")
                manifest["limitations"].append("pdf (chromium): @page size and margins apply; running heads and page numbers are not rendered")
        elif pdf_engine == "libreoffice":
            soffice = manifest["tools"].get("libreoffice", {}).get("path")
            docx_path = out / f"{stem}.docx"
            if not soffice:
                manifest["errors"].append("pdf: LibreOffice (soffice) not found; set NAM_BOOK_SOFFICE or choose render.pdf.engine chromium")
            elif not docx_path.is_file():
                manifest["errors"].append("pdf: the DOCX intermediate was not produced")
            else:
                profile = Path(tempfile.mkdtemp(prefix="nam-book-soffice-"))
                command = [
                    soffice, "--headless", "--norestore", f"-env:UserInstallation={profile.resolve().as_uri()}",
                    "--convert-to", "pdf", "--outdir", str(out), str(docx_path),
                ]
                result = run(command, manifest, timeout=900)
                shutil.rmtree(profile, ignore_errors=True)
                if not pdf_path.is_file():
                    manifest["errors"].append(f"pdf: LibreOffice produced no file: {(result.stderr or result.stdout).strip()[:500]}")
                else:
                    record_output("pdf", pdf_path)
                manifest["limitations"].append("pdf (libreoffice): rendered from the DOCX; side-column callouts render as band paragraphs")
        else:
            manifest["errors"].append(f"pdf: unknown engine {pdf_engine}")

    missing = [item for item in requested if item not in manifest["outputs"]]
    for item in missing:
        if not any(error.startswith(f"{item}:") for error in manifest["errors"]):
            manifest["errors"].append(f"{item}: not produced")
    manifest["status"] = "fail" if manifest["errors"] else "pass"
    write_manifest(out, manifest)
    return manifest


def write_manifest(out: Path, manifest: dict[str, Any]) -> None:
    (out / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manuscript", type=Path, required=True, help="Markdown manuscript (one file)")
    parser.add_argument("--assets", type=Path, required=True, help="approved design assets bundle")
    parser.add_argument("--out", type=Path, required=True, help="staging directory for the build")
    parser.add_argument("--formats", nargs="+", choices=FORMATS, required=True)
    parser.add_argument("--lang", required=True, help="edition locale, for example id-ID")
    parser.add_argument("--title", default=None)
    parser.add_argument("--pdf-engine", choices=("chromium", "libreoffice"), default="chromium")
    parser.add_argument("--resource-path", type=Path, action="append", default=[], help="extra directories for images")
    parser.add_argument("--no-toc", action="store_true")
    parser.add_argument("--stem", default="book", help="output file stem")
    args = parser.parse_args(argv)
    manifest = build(
        args.manuscript, args.assets, args.out, args.formats, lang=args.lang, title=args.title,
        pdf_engine=args.pdf_engine, resource_paths=args.resource_path, toc=not args.no_toc, stem=args.stem,
    )
    print(json.dumps({key: manifest[key] for key in ("status", "outputs", "errors", "limitations")}, indent=2, ensure_ascii=False))
    return 0 if manifest["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
