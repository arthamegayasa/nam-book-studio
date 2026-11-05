from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ASSETS = load_module("build_design_assets", "skills/nam-book-design/scripts/build_design_assets.py")
RENDER = load_module("render_sample", "skills/nam-book-design/scripts/render_sample.py")
BUILDER = load_module("build_deliverables", "skills/nam-book-publish/scripts/build_deliverables.py")
PRESETS = ROOT / "skills/nam-book-design/assets/presets"
PANDOC = shutil.which("pandoc")
BROWSER = BUILDER.find_tool("NAM_BOOK_BROWSER", BUILDER.BROWSER_NAMES, BUILDER.BROWSER_PATHS)


def write_spec(directory: Path, preset: str = "friendly-explainer", **overrides) -> Path:
    spec = json.loads((PRESETS / f"{preset}.json").read_text(encoding="utf-8"))
    spec["project_id"] = "design-render-test"
    spec.update(overrides)
    path = directory / "design-spec.json"
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path


class BuildDesignAssetsTests(unittest.TestCase):
    def test_assets_are_generated_from_the_spec_and_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_path = write_spec(root)
            manifest = ASSETS.build_assets(spec_path, root / "assets")
            print_css = (root / "assets" / "print.css").read_text(encoding="utf-8")
            epub_css = (root / "assets" / "epub.css").read_text(encoding="utf-8")
            lua = (root / "assets" / "callouts.lua").read_text(encoding="utf-8")
            self.assertIn("@page { size: 148mm 210mm; margin: 16mm 14mm 18mm 16mm; }", print_css)
            self.assertIn("--side-column: 34mm;", print_css)
            self.assertIn('font-family: "Source Serif 4", "Georgia", serif;', print_css)
            self.assertIn(".placement-side-column { font-size: 0.86em;", print_css)
            self.assertIn("float: right;", print_css)
            self.assertIn("--callout-accent-warning: #b42318;", print_css)
            self.assertNotIn("@page", epub_css)
            self.assertNotIn("float: right", epub_css)
            self.assertIn('["tip"] = {\n    ["en-US"] = "Tip",\n    ["id-ID"] = "Kiat",', lua)
            self.assertIn('["epub"] = {', lua)
            self.assertIn('["side-column"] = "inline"', lua)
            self.assertIn("custom-style", lua)
            icons = sorted(path.name for path in (root / "assets" / "icons").glob("*.svg"))
            self.assertEqual(len(icons), 22)
            self.assertIn("quick-check.svg", icons)
            self.assertEqual(manifest["profile"], "friendly-explainer")
            self.assertEqual(manifest["catalog_version"], "1.0.0")
            self.assertIn("print.css", manifest["generated"])
            self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", manifest["spec_sha256"]))
            saved = json.loads((root / "assets" / "assets-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["generated"], manifest["generated"])

    def test_invalid_spec_is_rejected_with_named_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_path = write_spec(root)
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            del spec["color"]
            spec["callouts"].pop("band")
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lacks color"):
                ASSETS.build_assets(spec_path, root / "assets")
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["color"] = {"ink": "black", "paper": "#ffffff", "accent": "#c97832", "muted": "#6b7280", "rule": "#d0d7de"}
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "color.ink") as caught:
                ASSETS.build_assets(spec_path, root / "assets")
            self.assertIn("callouts lacks a style for band", str(caught.exception))

    def test_side_column_disabled_degrades_to_band_in_html(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_path = write_spec(root)
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["page"]["side_column_mm"] = 0
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            ASSETS.build_assets(spec_path, root / "assets")
            lua = (root / "assets" / "callouts.lua").read_text(encoding="utf-8")
            self.assertRegex(lua, r'\["html"\] = \{\s*\["side-column"\] = "band"')
            print_css = (root / "assets" / "print.css").read_text(encoding="utf-8")
            self.assertNotIn("float: right", print_css)

    @unittest.skipUnless(PANDOC, "pandoc is required to derive reference.docx")
    def test_reference_docx_carries_fonts_and_callout_styles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_path = write_spec(root, preset="textbook")
            manifest = ASSETS.build_assets(spec_path, root / "assets")
            self.assertIn("reference.docx", manifest["generated"])
            with zipfile.ZipFile(root / "assets" / "reference.docx") as archive:
                styles = archive.read("word/styles.xml").decode("utf-8")
            self.assertIn('w:ascii="Source Serif 4"', styles)
            self.assertIn('<w:name w:val="Callout Band"/>', styles)
            self.assertIn('<w:name w:val="Callout Side"/>', styles)
            self.assertIn('<w:name w:val="Callout Label"/>', styles)
            self.assertIn('w:fill="F1F5F9"', styles)


class RenderSampleTests(unittest.TestCase):
    def render(self, root: Path, formats: list[str], *, preset: str = "friendly-explainer", locale: str = "id-ID", **overrides):
        spec_path = write_spec(root, preset=preset, **overrides)
        ASSETS.build_assets(spec_path, root / "assets")
        return RENDER.render(spec_path, root / "assets", root / "proof", locale=locale, formats=formats)

    def test_mode_filter_keeps_only_allowed_types_and_passes_the_contract(self) -> None:
        inspector = RENDER.load_sibling("nam-book-teach", "inspect_callouts.py")
        catalog = json.loads((ROOT / "skills/asknam/references/callout-catalog.json").read_text(encoding="utf-8"))
        text = (RENDER.SAMPLE_DIR / "en-US.md").read_text(encoding="utf-8")
        for mode in ("friendly-explainer", "textbook", "exam-prep"):
            with self.subTest(mode=mode):
                filtered, dropped = RENDER.filter_callouts_for_mode(text, mode, catalog, inspector)
                report = inspector.inspect_manuscript(filtered, mode=mode, locale="en-US", catalog=catalog, chapter_id="ch-01")
                self.assertEqual(report["errors"], [], report["errors"])
                self.assertTrue(dropped)
                self.assertNotIn("type=exam-trap" if mode != "exam-prep" else "type=big-idea", filtered)

    @unittest.skipUnless(PANDOC, "pandoc is required to render the sample chapter")
    def test_sample_renders_docx_and_epub_with_catalog_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = self.render(root, ["docx", "epub"])
            self.assertEqual(report["errors"], [], report["errors"])
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["formats"], ["docx", "epub"])
            self.assertIn("callout-ch01-02", report["sample"]["dropped_callouts"])
            self.assertTrue((root / "proof" / "report.json").is_file())
            self.assertTrue((root / "proof" / "build-manifest.json").is_file())
            with zipfile.ZipFile(root / "proof" / "sample-chapter.epub") as archive:
                content = "\n".join(
                    archive.read(name).decode("utf-8") for name in archive.namelist() if name.endswith(".xhtml")
                )
                # Pandoc 3.1 names SVG media .svgz, Pandoc 3.9 names it .svg; the media type is what readers use.
                media = [name for name in archive.namelist() if name.startswith("EPUB/media/") and name.endswith((".svg", ".svgz"))]
                self.assertGreaterEqual(len(media), 10, archive.namelist())
            self.assertIn("Kiat", content)
            self.assertIn("Peringatan", content)
            self.assertIn('class="callout callout-tip placement-inline"', content)
            self.assertIn('class="callout callout-warning placement-inline"', content)
            self.assertIn('class="callout-icon"', content)
            self.assertNotIn("Clinical Pearl", content)
            with zipfile.ZipFile(root / "proof" / "sample-chapter.docx") as archive:
                document = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("Kiat", document)
            self.assertIn('w:val="CalloutBand"', document)
            self.assertIn('w:val="CalloutLabel"', document)
            checks = {item["format"]: item for item in report["checks"]}
            self.assertEqual(checks["epub"]["inspector"], "pass", checks["epub"])
            self.assertEqual(checks["docx"]["inspector"], "pass", checks["docx"])

    @unittest.skipUnless(PANDOC and BROWSER, "pandoc and a Chromium-family browser are required for the PDF path")
    def test_sample_renders_pdf_through_chromium(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = self.render(root, ["pdf"], locale="en-US")
            self.assertEqual(report["errors"], [], report["errors"])
            self.assertEqual(report["formats"], ["pdf"])
            pdf = root / "proof" / "sample-chapter.pdf"
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))
            self.assertGreater(pdf.stat().st_size, 10_000)
            self.assertTrue(any("running heads" in item for item in report["limitations"]), report["limitations"])
            self.assertIn(report["tools"]["chromium"]["path"], BUILDER.find_tools("NAM_BOOK_BROWSER", BUILDER.BROWSER_NAMES, BUILDER.BROWSER_PATHS))

    @unittest.skipUnless(PANDOC, "pandoc is required to reach the browser lookup")
    def test_missing_browser_is_an_error_not_a_placeholder(self) -> None:
        original = BUILDER.find_tools

        def no_browser(env_var, names, paths):
            if env_var == "NAM_BOOK_BROWSER":
                return []
            return original(env_var, names, paths)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_path = write_spec(root)
            ASSETS.build_assets(spec_path, root / "assets")
            builder = RENDER.load_sibling("nam-book-publish", "build_deliverables.py")
            builder.find_tools = no_browser
            try:
                report = RENDER.render(spec_path, root / "assets", root / "proof", locale="en-US", formats=["pdf"])
            finally:
                builder.find_tools = original
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["missing_formats"], ["pdf"])
            self.assertTrue(any("Chromium-family browser" in item for item in report["errors"]), report["errors"])
            self.assertFalse((root / "proof" / "sample-chapter.pdf").exists())


if __name__ == "__main__":
    unittest.main()
