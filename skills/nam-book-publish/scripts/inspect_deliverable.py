#!/usr/bin/env python3
"""Inspect DOCX, EPUB, or PDF package structure with the Python standard library.

This tool never claims visual, accessibility, semantic, PDF-profile, or medical
conformance. It does not extract archive members to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath


ACTIVE_XML = (b"<!DOCTYPE", b"<!ENTITY")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_xml(payload: bytes, label: str, errors: list[str]) -> ET.Element | None:
    upper = payload.upper()
    if any(marker in upper for marker in ACTIVE_XML):
        errors.append(f"{label} contains a forbidden DOCTYPE or ENTITY declaration")
        return None
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:
        errors.append(f"{label} XML parse error: {exc}")
        return None


def unsafe_member(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return path.is_absolute() or ".." in path.parts or bool(re.match(r"^[A-Za-z]:", name))


def inspect_zip_common(archive: zipfile.ZipFile, errors: list[str], warnings: list[str]) -> dict[str, object]:
    infos = archive.infolist()
    names = [item.filename for item in infos]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    for name in names:
        if unsafe_member(name):
            errors.append(f"unsafe archive member path: {name}")
    if duplicates:
        errors.append("duplicate archive members: " + ", ".join(duplicates))
    encrypted = [item.filename for item in infos if item.flag_bits & 0x1]
    if encrypted:
        errors.append("encrypted archive members are not supported: " + ", ".join(encrypted))
    extreme = [
        item.filename
        for item in infos
        if item.compress_size and item.file_size > 100_000_000 and item.file_size / item.compress_size > 1000
    ]
    if extreme:
        warnings.append("extreme compression ratio detected: " + ", ".join(extreme))
    return {
        "member_count": len(infos),
        "uncompressed_bytes": sum(item.file_size for item in infos),
        "compressed_bytes": sum(item.compress_size for item in infos),
    }


def inspect_docx(path: Path, errors: list[str], warnings: list[str]) -> dict[str, object]:
    required = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
    optional_expected = {"word/styles.xml", "word/_rels/document.xml.rels", "docProps/core.xml"}
    try:
        with zipfile.ZipFile(path) as archive:
            summary = inspect_zip_common(archive, errors, warnings)
            names = set(archive.namelist())
            missing = sorted(required - names)
            if missing:
                errors.append("missing DOCX members: " + ", ".join(missing))
            for name in sorted(optional_expected - names):
                warnings.append(f"expected editorial DOCX member is absent: {name}")

            roots: dict[str, ET.Element] = {}
            for name in sorted(required & names):
                root = parse_xml(archive.read(name), name, errors)
                if root is not None:
                    roots[name] = root

            document = roots.get("word/document.xml")
            paragraphs = 0
            tables = 0
            drawings = 0
            missing_alt = 0
            toc_field_found = False
            if document is not None:
                for element in document.iter():
                    name = local_name(element.tag)
                    if name == "p":
                        paragraphs += 1
                    elif name == "tbl":
                        tables += 1
                    elif name == "drawing":
                        drawings += 1
                    elif name == "docPr" and not (element.get("descr") or element.get("title")):
                        missing_alt += 1
                    elif name in {"instrText", "fldSimple"}:
                        value = "".join(element.itertext()) + " " + " ".join(element.attrib.values())
                        if re.search(r"\bTOC\b", value):
                            toc_field_found = True
            if drawings and missing_alt:
                warnings.append(f"{missing_alt} drawing metadata elements have no title or description")
            if not toc_field_found:
                warnings.append("no TOC field instruction was detected")

            media = sorted(name for name in names if name.startswith("word/media/") and not name.endswith("/"))
            summary.update(
                {
                    "paragraph_count": paragraphs,
                    "table_count": tables,
                    "drawing_count": drawings,
                    "media_count": len(media),
                    "toc_field_detected": toc_field_found,
                }
            )
            return summary
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"invalid DOCX ZIP package: {exc}")
        return {}


def resolved_member(base_file: str, href: str) -> str:
    base = posixpath.dirname(base_file)
    return posixpath.normpath(posixpath.join(base, href.split("#", 1)[0]))


def inspect_epub(path: Path, errors: list[str], warnings: list[str]) -> dict[str, object]:
    try:
        with zipfile.ZipFile(path) as archive:
            summary = inspect_zip_common(archive, errors, warnings)
            infos = archive.infolist()
            names = set(archive.namelist())
            if not infos or infos[0].filename != "mimetype":
                errors.append("EPUB mimetype must be the first archive member")
            elif infos[0].compress_type != zipfile.ZIP_STORED:
                errors.append("EPUB mimetype must be stored without compression")
            if "mimetype" not in names:
                errors.append("EPUB mimetype member is missing")
            elif archive.read("mimetype") != b"application/epub+zip":
                errors.append("EPUB mimetype content is not exactly application/epub+zip")
            if "META-INF/container.xml" not in names:
                errors.append("META-INF/container.xml is missing")
                return summary

            container = parse_xml(archive.read("META-INF/container.xml"), "container.xml", errors)
            rootfiles = [] if container is None else [
                node.get("full-path")
                for node in container.iter()
                if local_name(node.tag) == "rootfile" and node.get("full-path")
            ]
            if len(rootfiles) != 1:
                errors.append(f"expected exactly one package rootfile, found {len(rootfiles)}")
                return summary
            opf_path = rootfiles[0]
            if unsafe_member(opf_path) or opf_path not in names:
                errors.append(f"package document is missing or unsafe: {opf_path}")
                return summary

            package = parse_xml(archive.read(opf_path), opf_path, errors)
            if package is None:
                return summary

            metadata_values: dict[str, list[str]] = {"title": [], "language": [], "identifier": []}
            manifest: dict[str, dict[str, str]] = {}
            spine_ids: list[str] = []
            for element in package.iter():
                name = local_name(element.tag)
                if name in metadata_values and (element.text or "").strip():
                    metadata_values[name].append((element.text or "").strip())
                elif name == "item" and element.get("id"):
                    manifest[element.get("id", "")] = {
                        "href": element.get("href", ""),
                        "media_type": element.get("media-type", ""),
                        "properties": element.get("properties", ""),
                    }
                elif name == "itemref" and element.get("idref"):
                    spine_ids.append(element.get("idref", ""))

            for key, values in metadata_values.items():
                if not values:
                    errors.append(f"EPUB package metadata has no {key}")
            if not manifest:
                errors.append("EPUB manifest is empty")
            if not spine_ids:
                errors.append("EPUB spine is empty")
            for item_id in spine_ids:
                if item_id not in manifest:
                    errors.append(f"spine references missing manifest id: {item_id}")

            missing_resources = []
            nav_ids = []
            content_docs = []
            for item_id, item in manifest.items():
                href = item["href"]
                if not href:
                    errors.append(f"manifest item {item_id} has no href")
                    continue
                member = resolved_member(opf_path, href)
                if unsafe_member(member) or member not in names:
                    missing_resources.append(member)
                if "nav" in item["properties"].split():
                    nav_ids.append(item_id)
                if item["media_type"] in {"application/xhtml+xml", "image/svg+xml"} and member in names:
                    content_docs.append(member)
            if missing_resources:
                errors.append("manifest resources are missing or unsafe: " + ", ".join(sorted(missing_resources)))
            if len(nav_ids) != 1:
                errors.append(f"expected exactly one manifest navigation item, found {len(nav_ids)}")

            images = 0
            missing_alt = 0
            scripted_docs = 0
            for member in content_docs:
                root = parse_xml(archive.read(member), member, errors)
                if root is None:
                    continue
                has_script = False
                for element in root.iter():
                    name = local_name(element.tag)
                    if name == "img":
                        images += 1
                        if element.get("alt") is None:
                            missing_alt += 1
                    elif name == "script":
                        has_script = True
                if has_script:
                    scripted_docs += 1
            if missing_alt:
                warnings.append(f"{missing_alt} EPUB img elements have no alt attribute")
            if scripted_docs:
                warnings.append(f"{scripted_docs} content documents contain scripts and need security and fallback review")

            summary.update(
                {
                    "package_document": opf_path,
                    "metadata": metadata_values,
                    "manifest_items": len(manifest),
                    "spine_items": len(spine_ids),
                    "navigation_item_ids": nav_ids,
                    "image_elements": images,
                    "scripted_content_documents": scripted_docs,
                }
            )
            return summary
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"invalid EPUB ZIP package: {exc}")
        return {}


def inspect_pdf(path: Path, errors: list[str], warnings: list[str]) -> dict[str, object]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        errors.append(f"cannot read PDF: {exc}")
        return {}
    if not payload.startswith(b"%PDF-"):
        errors.append("PDF header is missing")
    if b"%%EOF" not in payload[-2048:]:
        errors.append("PDF EOF marker was not found near the end of the file")
    if b"/Encrypt" in payload:
        warnings.append("PDF appears encrypted; verify accessibility, permissions, and intended distribution")
    if b"/StructTreeRoot" not in payload:
        warnings.append("tagged-PDF structure marker was not detected")
    if b"/Lang" not in payload:
        warnings.append("document language marker was not detected")
    if b"/Outlines" not in payload:
        warnings.append("bookmark outline marker was not detected")
    if b"/Metadata" not in payload:
        warnings.append("metadata stream marker was not detected")
    page_count_hint = len(re.findall(rb"/Type\s*/Page\b", payload))
    return {
        "pdf_header": payload[:8].decode("latin-1", errors="replace"),
        "page_object_count_hint": page_count_hint,
        "tag_structure_marker": b"/StructTreeRoot" in payload,
        "language_marker": b"/Lang" in payload,
        "outline_marker": b"/Outlines" in payload,
        "output_intent_marker": b"/OutputIntent" in payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Structurally inspect a DOCX, EPUB, or PDF.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--format", choices=("docx", "epub", "pdf"))
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    path = args.file
    detected = args.format or path.suffix.lower().lstrip(".")
    report: dict[str, object] = {
        "file": str(path),
        "format": detected,
        "scope": "package and marker inspection only; render, accessibility, semantic, and conformance validation remain required",
        "errors": errors,
        "warnings": warnings,
    }

    if not path.is_file():
        errors.append("file does not exist or is not a regular file")
    else:
        payload = path.read_bytes()
        report["bytes"] = len(payload)
        report["sha256"] = hashlib.sha256(payload).hexdigest()
        if detected == "docx":
            report["details"] = inspect_docx(path, errors, warnings)
        elif detected == "epub":
            report["details"] = inspect_epub(path, errors, warnings)
        elif detected == "pdf":
            report["details"] = inspect_pdf(path, errors, warnings)
        else:
            errors.append("format is unknown; pass --format docx, epub, or pdf")

    report["status"] = "fail" if errors else "pass"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
