from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


INSPECTOR = load_module("inspect_callouts", "skills/nam-book-teach/scripts/inspect_callouts.py")
RESOURCES = load_module("validate_resources", "skills/asknam/scripts/validate_resources.py")
CATALOG_PATH = ROOT / "skills/asknam/references/callout-catalog.json"
CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
MODES = ("friendly-explainer", "textbook", "exam-prep")


def prose(words: int, seed: str = "kata") -> str:
    return " ".join(f"{seed}{index % 7}" for index in range(words)) + "."


def callout(callout_id: str, type_id: str, body: str = "Isi callout.", **attrs: str) -> str:
    rendered = " ".join(f"{key}={value}" for key, value in attrs.items())
    header = f"::: {{#{callout_id} .callout type={type_id} {rendered}}}".replace("  ", " ")
    return f"{header}\n{body}\n:::"


FRONT_MATTER = "---\nchapter_id: ch-01\nobjective_ids: [obj-ch01-01, obj-ch01-02]\n---\n"


def friendly_chapter() -> str:
    return "\n\n".join(
        [
            FRONT_MATTER + "# Mengapa roti mengembang",
            prose(300),
            callout("callout-ch01-01", "big-idea", "Ragi mengubah gula menjadi gas.", objective="obj-ch01-01"),
            prose(300),
            callout("callout-ch01-02", "tip", "Gunakan air hangat.", placement="side-column", objective="obj-ch01-01"),
            prose(300),
            callout("callout-ch01-03", "warning", "Oven panas dapat membakar.", objective="obj-ch01-02"),
            prose(300),
            callout("callout-ch01-04", "reflect", "Menurut Anda, mana yang paling berpengaruh?", objective="obj-ch01-02"),
            prose(300),
            callout("callout-ch01-05", "quick-check", "Apa fungsi gula bagi ragi?",
                    item="item-ch01-001", reveal="chapter-end", objective="obj-ch01-01"),
            prose(50),
            "::: {#callout-ch01-06 .callout type=answer-key for=ch-01}\n:::",
        ]
    )


class CalloutCatalogTests(unittest.TestCase):
    def test_catalog_lists_the_agreed_types_with_both_locales(self) -> None:
        expected = {
            "big-idea", "why-it-matters", "tip", "remember", "warning", "myth-fact", "try-it",
            "technical-corner", "definition", "key-principle", "evidence-note", "worked-example",
            "case", "limits", "must-know", "high-yield", "pearl", "exam-trap", "memory-aid",
            "reflect", "quick-check", "answer-key",
        }
        types = {item["type_id"]: item for item in CATALOG["types"]}
        self.assertEqual(set(types), expected)
        for entry in types.values():
            self.assertTrue(entry["labels"]["en-US"].strip())
            self.assertTrue(entry["labels"]["id-ID"].strip())
            self.assertIn(entry["default_placement"], entry["allowed_placements"])
        self.assertEqual(CATALOG["placements"], ["inline", "side-column", "band", "full-page", "opener"])
        self.assertEqual(types["reflect"]["reveal"], ["none", "chapter-end"])
        self.assertEqual(types["quick-check"]["reveal"], ["inline", "chapter-end", "book-end"])
        self.assertTrue(types["quick-check"]["requires_item"])
        self.assertTrue(types["answer-key"]["requires_for"])
        self.assertEqual(types["warning"]["modes"], list(MODES))

    def test_resource_validator_rejects_a_broken_catalog(self) -> None:
        broken = copy.deepcopy(CATALOG)
        broken["types"][0]["labels"]["id-ID"] = ""
        broken["types"][1]["default_placement"] = "spread"
        broken["types"].append(copy.deepcopy(broken["types"][2]))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "callout-catalog.json"
            path.write_text(json.dumps(broken), encoding="utf-8")
            errors = RESOURCES.validate_callout_catalog(path)
        joined = "\n".join(errors)
        self.assertIn("big-idea needs non-empty labels", joined)
        self.assertIn("why-it-matters default_placement", joined)
        self.assertIn("duplicate type_id tip", joined)


class InspectCalloutsTests(unittest.TestCase):
    def inspect(self, text: str, **overrides):
        options = {"mode": "friendly-explainer", "locale": "id-ID", "catalog": CATALOG,
                   "chapter_id": "ch-01", "density": "high"}
        options.update(overrides)
        return INSPECTOR.inspect_manuscript(text, **options)

    def test_valid_chapter_passes_and_lists_callouts_in_document_order(self) -> None:
        report = self.inspect(friendly_chapter())
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            report["callout_ids"],
            [f"callout-ch01-0{index}" for index in range(1, 7)],
        )
        by_id = {item["callout_id"]: item for item in report["callouts"]}
        self.assertEqual(by_id["callout-ch01-01"]["placement"], "opener")
        self.assertEqual(by_id["callout-ch01-02"]["placement"], "side-column")
        self.assertEqual(by_id["callout-ch01-04"]["reveal"], "none")
        self.assertEqual(by_id["callout-ch01-05"]["reveal"], "chapter-end")
        self.assertEqual(by_id["callout-ch01-05"]["item"], "item-ch01-001")
        self.assertEqual(by_id["callout-ch01-06"]["for"], "ch-01")
        self.assertEqual(by_id["callout-ch01-02"]["label"], "Kiat")
        self.assertEqual(report["counts"]["callouts"], 6)

    def test_structural_errors_are_reported_per_callout(self) -> None:
        cases = {
            "unknown type": callout("callout-ch01-01", "sidebar", objective="obj-ch01-01"),
            "not allowed in mode": callout("callout-ch01-01", "exam-trap", objective="obj-ch01-01"),
            "duplicate callout id": callout("callout-ch01-01", "tip", objective="obj-ch01-01") + "\n\n"
            + prose(5) + "\n\n" + callout("callout-ch01-01", "tip", objective="obj-ch01-01"),
            "does not match": callout("callout-ch1-1", "tip", objective="obj-ch01-01"),
            "belongs to chapter": callout("callout-ch02-01", "tip", objective="obj-ch01-01"),
            "placement": callout("callout-ch01-01", "tip", placement="full-page", objective="obj-ch01-01"),
            "exactly one objective": callout("callout-ch01-01", "tip"),
            "exactly one objective ": callout("callout-ch01-01", "tip", objective='"obj-ch01-01 obj-ch01-02"'),
            "requires item": callout("callout-ch01-01", "quick-check", objective="obj-ch01-01", reveal="inline"),
            "must not reference an item": callout("callout-ch01-01", "reflect", objective="obj-ch01-01", item="item-ch01-001"),
            "reveal": callout("callout-ch01-01", "reflect", objective="obj-ch01-01", reveal="inline"),
            "requires for": callout("callout-ch01-01", "answer-key"),
            "no answer-key": callout("callout-ch01-01", "quick-check", objective="obj-ch01-01",
                                     item="item-ch01-001", reveal="chapter-end"),
            "empty body": "::: {#callout-ch01-01 .callout type=tip objective=obj-ch01-01}\n:::",
        }
        for expected, snippet in cases.items():
            with self.subTest(expected=expected):
                report = self.inspect(FRONT_MATTER + prose(400) + "\n\n" + snippet + "\n\n" + prose(400),
                                      density=None)
                self.assertEqual(report["status"], "fail")
                self.assertTrue(
                    any(expected.strip() in error for error in report["errors"]),
                    f"{expected!r} not in {report['errors']}",
                )

    def test_nesting_and_unclosed_callouts_are_errors(self) -> None:
        nested = (
            FRONT_MATTER
            + "::: {#callout-ch01-01 .callout type=tip objective=obj-ch01-01}\n"
            + "::: {#callout-ch01-02 .callout type=remember objective=obj-ch01-01}\nInner\n:::\n:::\n"
        )
        report = self.inspect(nested, density=None)
        self.assertTrue(any("nested" in error for error in report["errors"]), report["errors"])
        unclosed = FRONT_MATTER + "::: {#callout-ch01-01 .callout type=tip objective=obj-ch01-01}\nBody\n"
        report = self.inspect(unclosed, density=None)
        self.assertTrue(any("not closed" in error for error in report["errors"]), report["errors"])

    def test_density_adjacency_and_opener_rules_are_warnings(self) -> None:
        crowded = "\n\n".join(
            [
                FRONT_MATTER + prose(40),
                callout("callout-ch01-01", "big-idea", objective="obj-ch01-01"),
                callout("callout-ch01-02", "big-idea", objective="obj-ch01-01"),
                prose(40),
                callout("callout-ch01-03", "tip", objective="obj-ch01-01"),
            ]
        )
        report = self.inspect(crowded)
        self.assertEqual(report["errors"], [])
        joined = "\n".join(report["warnings"])
        self.assertIn("density", joined)
        self.assertIn("adjacent", joined)
        self.assertIn("opener", joined)
        self.assertEqual(report["status"], "pass")

    def test_deprecated_type_warns_but_still_passes(self) -> None:
        catalog = copy.deepcopy(CATALOG)
        next(item for item in catalog["types"] if item["type_id"] == "try-it")["deprecated"] = True
        text = FRONT_MATTER + prose(400) + "\n\n" + callout("callout-ch01-01", "try-it", objective="obj-ch01-01")
        report = self.inspect(text, catalog=catalog)
        self.assertEqual(report["errors"], [])
        self.assertTrue(any("deprecated" in item for item in report["warnings"]), report["warnings"])

    def test_architecture_cross_check_rejects_unknown_objectives(self) -> None:
        architecture = {
            "chapters": [
                {"chapter_id": "ch-01", "objectives": [{"objective_id": "obj-ch01-01", "text": "Explain yeast"}]}
            ]
        }
        text = FRONT_MATTER + prose(400) + "\n\n" + callout("callout-ch01-01", "tip", objective="obj-ch01-02")
        report = self.inspect(text, architecture=architecture)
        self.assertTrue(any("obj-ch01-02" in error and "architecture" in error for error in report["errors"]))
        text = FRONT_MATTER + prose(400) + "\n\n" + callout("callout-ch01-01", "tip", objective="obj-ch01-01")
        self.assertEqual(self.inspect(text, architecture=architecture)["errors"], [])

    def test_book_end_target_is_checked_only_at_book_scope(self) -> None:
        chapter = FRONT_MATTER + prose(400) + "\n\n" + callout(
            "callout-ch01-01", "quick-check", item="item-ch01-001", reveal="book-end", objective="obj-ch01-01"
        )
        self.assertEqual(self.inspect(chapter)["errors"], [])
        book = chapter.replace(FRONT_MATTER, "")
        report = self.inspect(book, chapter_id=None)
        self.assertTrue(any("for=book" in error for error in report["errors"]), report["errors"])
        book_with_key = book + "\n\n::: {#callout-ch01-02 .callout type=answer-key for=book}\n:::"
        self.assertEqual(self.inspect(book_with_key, chapter_id=None)["errors"], [])

    def test_cli_prints_ids_and_uses_exit_codes(self) -> None:
        script = ROOT / "skills/nam-book-teach/scripts/inspect_callouts.py"
        with tempfile.TemporaryDirectory() as temporary:
            manuscript = Path(temporary) / "enriched.id-ID.md"
            manuscript.write_text(friendly_chapter(), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), "--manuscript", str(manuscript), "--mode", "friendly-explainer",
                 "--locale", "id-ID", "--chapter-id", "ch-01", "--density", "high", "--print-ids"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.split(), [f"callout-ch01-0{index}" for index in range(1, 7)])
            manuscript.write_text(friendly_chapter().replace("type=tip", "type=exam-trap"), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), "--manuscript", str(manuscript), "--mode", "friendly-explainer",
                 "--locale", "id-ID", "--chapter-id", "ch-01"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "fail")
            self.assertTrue(any("exam-trap" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
