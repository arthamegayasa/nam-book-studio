from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/nam-book-publish/scripts/inspect_deliverable.py"
SPEC = importlib.util.spec_from_file_location("inspect_deliverable", SCRIPT)
assert SPEC and SPEC.loader
INSPECTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = INSPECTOR
SPEC.loader.exec_module(INSPECTOR)

CONTAINER = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
    b'<rootfiles><rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/></rootfiles>'
    b"</container>"
)
PACKAGE = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
    b'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
    b"<dc:title>Sample</dc:title><dc:language>en-US</dc:language><dc:identifier id=\"id\">urn:uuid:1</dc:identifier>"
    b"</metadata>"
    b'<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    b'<item id="ch1" href="text/ch001.xhtml" media-type="application/xhtml+xml"/></manifest>'
    b'<spine><itemref idref="nav"/><itemref idref="ch1"/></spine></package>'
)
NAV = (
    b'<nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc">'
    b'<ol><li><a href="text/ch001.xhtml">One</a></li></ol></nav>'
)
DEFAULT_BODY = NAV + b'<p>Hello</p><img src="../icons/tip.svg" alt=""/>'

HOLLOW_PDF = b"%PDF-1.7\n%%EOF\n"
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 420 595] >>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n178\n%%EOF\n"
)
OBJECT_STREAM_PDF = (
    b"%PDF-1.5\n"
    b"1 0 obj\n<< /Type /ObjStm /N 2 /First 8 /Length 44 >>\nstream\n"
    b"2 0 3 22 << /Type /Catalog >> << /Type /Pages >>\n"
    b"endstream\nendobj\n"
    b"startxref\n0\n%%EOF\n"
)

CONTENT_TYPES_NS = b"http://schemas.openxmlformats.org/package/2006/content-types"
WORD_NS = b"http://schemas.openxmlformats.org/wordprocessingml/2006/main"
HOLLOW_TYPES = b'<Types xmlns="' + CONTENT_TYPES_NS + b'"/>'
VALID_TYPES = (
    b'<Types xmlns="' + CONTENT_TYPES_NS + b'">'
    b'<Default Extension="xml" ContentType="application/xml"/>'
    b'<Override PartName="/word/document.xml" '
    b'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    b"</Types>"
)
RELATIONSHIPS = b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
HOLLOW_DOCUMENT = b'<w:document xmlns:w="' + WORD_NS + b'"/>'
VALID_DOCUMENT = (
    b'<w:document xmlns:w="' + WORD_NS + b'"><w:body>'
    b"<w:p><w:r><w:t>Hello world</w:t></w:r></w:p>"
    b"</w:body></w:document>"
)


def xhtml(doctype: bytes, body: bytes = DEFAULT_BODY) -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8"?>\n' + doctype + b"\n"
        b'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>t</title></head>'
        b"<body>" + body + b"</body></html>"
    )


def write_epub(path: Path, doctype: bytes = b"<!DOCTYPE html>", chapter_body: bytes = DEFAULT_BODY) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", CONTAINER, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/content.opf", PACKAGE, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/nav.xhtml", xhtml(doctype), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/text/ch001.xhtml", xhtml(doctype, chapter_body), compress_type=zipfile.ZIP_DEFLATED)


def write_docx(path: Path, types: bytes, document: bytes) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", types)
        archive.writestr("_rels/.rels", RELATIONSHIPS)
        archive.writestr("word/document.xml", document)


class DoctypeHandlingTests(unittest.TestCase):
    def inspect(self, doctype: bytes) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.epub"
            write_epub(path, doctype)
            INSPECTOR.inspect_epub(path, errors, warnings)
        return errors, warnings

    def test_bare_html5_doctype_passes(self) -> None:
        errors, _ = self.inspect(b"<!DOCTYPE html>")
        self.assertEqual(errors, [])
        errors, _ = self.inspect(b"<!DOCTYPE html >")
        self.assertEqual(errors, [])

    def test_internal_subset_external_identifier_and_entities_fail(self) -> None:
        for doctype in (
            b'<!DOCTYPE html [<!ENTITY x "y">]>',
            b'<!DOCTYPE html SYSTEM "evil.dtd">',
            b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">',
            b"<!DOCTYPE html>\n<!DOCTYPE html>",
        ):
            with self.subTest(doctype=doctype):
                errors, _ = self.inspect(doctype)
                self.assertTrue(any("forbidden" in error for error in errors), errors)

    def test_forbidden_declaration_reasons(self) -> None:
        self.assertIsNone(INSPECTOR.forbidden_declaration(b"<?xml version='1.0'?><a/>"))
        self.assertIsNone(INSPECTOR.forbidden_declaration(b"<!DOCTYPE html><html/>"))
        self.assertEqual(INSPECTOR.forbidden_declaration(b"<!DOCTYPE a [ <!ENTITY e 'x'> ]><a/>"), "ENTITY declaration")
        self.assertIn("internal subset", INSPECTOR.forbidden_declaration(b"<!DOCTYPE a [ ]><a/>") or "")


class EpubBodyTextTests(unittest.TestCase):
    def inspect(self, chapter_body: bytes) -> tuple[list[str], list[str], dict]:
        errors: list[str] = []
        warnings: list[str] = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.epub"
            write_epub(path, chapter_body=chapter_body)
            details = INSPECTOR.inspect_epub(path, errors, warnings)
        return errors, warnings, details

    def test_epub_whose_chapters_have_no_text_fails(self) -> None:
        errors, _, details = self.inspect(b'<img src="../icons/tip.svg" alt="icon"/>')
        self.assertTrue(any("body text" in error for error in errors), errors)
        self.assertEqual(details["text_characters"], 0)

    def test_epub_with_chapter_text_reports_characters(self) -> None:
        errors, _, details = self.inspect(b"<p>Hello</p>")
        self.assertEqual(errors, [])
        self.assertEqual(details["text_characters"], 5)


class PdfTests(unittest.TestCase):
    def inspect(self, payload: bytes) -> tuple[list[str], list[str], dict]:
        errors: list[str] = []
        warnings: list[str] = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.pdf"
            path.write_bytes(payload)
            details = INSPECTOR.inspect_pdf(path, errors, warnings)
        return errors, warnings, details

    def test_hollow_pdf_fails(self) -> None:
        errors, _, _ = self.inspect(HOLLOW_PDF)
        self.assertTrue(any("startxref" in error for error in errors), errors)
        self.assertTrue(any("page object" in error for error in errors), errors)

    def test_minimal_pdf_has_no_structural_errors(self) -> None:
        errors, warnings, details = self.inspect(MINIMAL_PDF)
        self.assertEqual(errors, [])
        self.assertEqual(details["page_object_count_hint"], 1)
        self.assertTrue(any("tagged-PDF" in warning for warning in warnings), warnings)

    def test_object_streams_downgrade_missing_page_objects_to_a_warning(self) -> None:
        errors, warnings, details = self.inspect(OBJECT_STREAM_PDF)
        self.assertEqual(errors, [])
        self.assertTrue(any("object streams" in warning for warning in warnings), warnings)
        self.assertEqual(details["page_object_count_hint"], 0)
        self.assertTrue(details["object_streams"])


class DocxTests(unittest.TestCase):
    def inspect(self, types: bytes, document: bytes) -> tuple[list[str], list[str], dict]:
        errors: list[str] = []
        warnings: list[str] = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.docx"
            write_docx(path, types, document)
            details = INSPECTOR.inspect_docx(path, errors, warnings)
        return errors, warnings, details

    def test_hollow_docx_fails_with_named_reasons(self) -> None:
        errors, _, _ = self.inspect(HOLLOW_TYPES, HOLLOW_DOCUMENT)
        joined = "\n".join(errors)
        for fragment in ("no body element", "no paragraphs", "no text runs", "main document part"):
            self.assertIn(fragment, joined)

    def test_minimal_docx_has_warnings_only(self) -> None:
        errors, warnings, details = self.inspect(VALID_TYPES, VALID_DOCUMENT)
        self.assertEqual(errors, [])
        self.assertEqual(details["paragraph_count"], 1)
        self.assertEqual(details["text_characters"], 11)
        self.assertTrue(any("TOC" in warning for warning in warnings), warnings)


class StrictModeTests(unittest.TestCase):
    def test_apply_strict_promotes_only_accessibility_and_navigation_warnings(self) -> None:
        kept = "expected editorial DOCX member is absent: word/styles.xml"
        promotable = [
            "2 drawing metadata elements have no title or description",
            "no TOC field instruction was detected",
            "3 EPUB img elements have no alt attribute",
            "tagged-PDF structure marker was not detected",
            "document language marker was not detected",
            "bookmark outline marker was not detected",
            "metadata stream marker was not detected",
        ]
        warnings = [kept, *promotable]
        errors: list[str] = []
        promoted = INSPECTOR.apply_strict(errors, warnings)
        self.assertEqual(promoted, promotable)
        self.assertEqual(warnings, [kept])
        self.assertEqual(errors, [f"strict: {item}" for item in promotable])

    def run_cli(self, path: Path, *flags: str) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), str(path), *flags], capture_output=True, text=True, check=False
        )
        return completed.returncode, json.loads(completed.stdout)

    def test_cli_strict_flag_changes_exit_code_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.pdf"
            path.write_bytes(MINIMAL_PDF)
            code, report = self.run_cli(path)
            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "pass")
            self.assertFalse(report["strict"])
            self.assertEqual(report["promoted_warnings"], [])
            code, report = self.run_cli(path, "--strict")
            self.assertEqual(code, 1)
            self.assertEqual(report["status"], "fail")
            self.assertTrue(report["strict"])
            self.assertEqual(len(report["promoted_warnings"]), 4)
            self.assertTrue(all(error.startswith("strict: ") for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
