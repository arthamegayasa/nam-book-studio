from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "inspect_deliverable", ROOT / "skills/nam-book-publish/scripts/inspect_deliverable.py"
)
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


def xhtml(doctype: bytes) -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8"?>\n' + doctype + b"\n"
        b'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>t</title></head>'
        b'<body><nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc"><ol><li><a href="text/ch001.xhtml">One</a></li></ol></nav>'
        b'<p>Hello</p><img src="../icons/tip.svg" alt=""/></body></html>'
    )


def write_epub(path: Path, doctype: bytes) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", CONTAINER, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/content.opf", PACKAGE, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/nav.xhtml", xhtml(doctype), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/text/ch001.xhtml", xhtml(doctype), compress_type=zipfile.ZIP_DEFLATED)


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


if __name__ == "__main__":
    unittest.main()
