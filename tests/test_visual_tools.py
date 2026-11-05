from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SVG_SCRIPT = ROOT / "skills/nam-book-diagram/scripts/validate_svg.py"
PNG_SCRIPT = ROOT / "skills/nam-book-illustrate/scripts/inspect_png.py"
TEMPLATE = ROOT / "skills/nam-book-diagram/assets/diagram-template.svg"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SVG = load_module("validate_svg", SVG_SCRIPT)

ENTITY_SVG = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<!DOCTYPE svg [<!ENTITY e "expanded">]>\n'
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" role="img" aria-labelledby="t d">'
    b'<title id="t">&e;</title><desc id="d">&e;</desc></svg>'
)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def tiny_png(width: int = 4, height: int = 4) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    scanlines = b"".join(b"\x00" + b"\x00\x00\x00\xff" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(scanlines))
        + png_chunk(b"IEND", b"")
    )


class SvgValidatorTests(unittest.TestCase):
    def test_doctype_and_entity_fail_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "entity.svg"
            path.write_bytes(ENTITY_SVG)
            report = SVG.inspect_svg(path)
        self.assertEqual(report["status"], "fail")
        self.assertIn("DOCTYPE and ENTITY declarations are not allowed", report["errors"])
        self.assertFalse(any("parse error" in error for error in report["errors"]), report["errors"])
        self.assertNotIn("element_counts", report)

    def test_bundled_template_passes(self) -> None:
        report = SVG.inspect_svg(TEMPLATE)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["status"], "pass")


class PngInspectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "tiny.png"
        self.path.write_bytes(tiny_png())

    def run_cli(self, *flags: str) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, str(PNG_SCRIPT), str(self.path), *flags], capture_output=True, text=True, check=False
        )
        return completed.returncode, json.loads(completed.stdout)

    def test_missing_placed_size_is_reported_as_not_checked(self) -> None:
        code, report = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["ppi_check"], "not-checked")
        self.assertIsNone(report["effective_ppi"])
        self.assertIsNone(report["minimum_ppi_target"])
        self.assertTrue(any("placed size" in warning for warning in report["warnings"]), report["warnings"])

    def test_require_placed_size_turns_a_missing_size_into_an_error(self) -> None:
        code, report = self.run_cli("--require-placed-size")
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["ppi_check"], "not-checked")
        self.assertTrue(any("placed size" in error for error in report["errors"]), report["errors"])

    def test_placed_size_below_target_fails(self) -> None:
        code, report = self.run_cli("--placed-width-in", "1")
        self.assertEqual(code, 1)
        self.assertEqual(report["ppi_check"], "checked")
        self.assertEqual(report["minimum_ppi_target"], 300.0)
        self.assertEqual(report["effective_ppi"], {"x": 4.0})
        self.assertTrue(any("below target" in error for error in report["errors"]), report["errors"])

    def test_explicit_min_ppi_applies_when_checked(self) -> None:
        code, report = self.run_cli("--placed-width-in", "1", "--min-ppi", "2")
        self.assertEqual(code, 0)
        self.assertEqual(report["ppi_check"], "checked")
        self.assertEqual(report["minimum_ppi_target"], 2.0)


if __name__ == "__main__":
    unittest.main()
