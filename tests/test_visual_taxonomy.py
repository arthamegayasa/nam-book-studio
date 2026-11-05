from __future__ import annotations

import importlib.util
import json
import re
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


APPLY_TOKENS = load_module("apply_tokens", "skills/nam-book-diagram/scripts/apply_tokens.py")
VALIDATE_SVG = load_module("validate_svg", "skills/nam-book-diagram/scripts/validate_svg.py")

ARCHITECTURE_SCHEMA_PATH = ROOT / "skills/asknam/references/schemas/book-architecture.schema.json"
MIRROR_PATH = ROOT / "schemas/book-architecture.schema.json"
DESIGN_SCHEMA_PATH = ROOT / "skills/asknam/references/schemas/design-spec.schema.json"
CATALOG_PATH = ROOT / "skills/asknam/references/callout-catalog.json"
DIAGRAM_SPEC_DOC = ROOT / "skills/nam-book-diagram/references/diagram-specification.md"
TEMPLATE_PATH = ROOT / "skills/nam-book-diagram/assets/diagram-template.svg"
PRESET_PATH = ROOT / "skills/nam-book-design/assets/presets/friendly-explainer.json"

PLACEMENTS = ["inline", "side-column", "band", "full-page", "opener", "spread"]
KINDS = ["illustration", "diagram", "table", "data-graphic", "photograph", "hybrid", "other"]
STRUCTURES = ["process", "hierarchy", "comparison", "timeline", "cycle", "spatial", "mechanism", "decision-path", "scene"]


def planned_visual_schema() -> dict:
    schema = json.loads(ARCHITECTURE_SCHEMA_PATH.read_text(encoding="utf-8"))
    return schema["properties"]["chapters"]["items"]["properties"]["planned_visuals"]["items"]


def condition_holds(condition: dict, value: dict) -> bool:
    """Evaluate an `if` schema made of `required` and `properties` enums."""

    for key in condition.get("required", []):
        if key not in value:
            return False
    for key, sub in condition.get("properties", {}).items():
        if key in value and "enum" in sub and value[key] not in sub["enum"]:
            return False
    return True


def check_object(schema: dict, value: dict) -> list[str]:
    """Evaluate only the keywords these tests rely on.

    Covered: `type: object`, `required`, `additionalProperties: false`, per-property
    `enum` and `type: string`, and `if`/`then`. Anything else in the schema is not
    checked here; the schema's full meaning is still owned by JSON Schema 2020-12.
    """

    errors: list[str] = []
    if schema.get("type") == "object" and not isinstance(value, dict):
        return ["value is not an object"]
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in value:
            errors.append(f"missing {key}")
    if schema.get("additionalProperties") is False:
        errors.extend(f"unexpected {key}" for key in value if key not in properties)
    for key, sub in properties.items():
        if key not in value:
            continue
        if "enum" in sub and value[key] not in sub["enum"]:
            errors.append(f"{key} not in enum")
        if sub.get("type") == "string" and not isinstance(value[key], str):
            errors.append(f"{key} is not a string")
    if "if" in schema and condition_holds(schema["if"], value):
        errors.extend(check_object(schema.get("then", {}), value))
    return errors


class VocabularyTests(unittest.TestCase):
    def test_placement_enum_is_the_shared_vocabulary(self) -> None:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        expected = list(catalog["placements"]) + ["spread"]
        self.assertEqual(PLACEMENTS, expected)
        self.assertEqual(planned_visual_schema()["properties"]["placement"]["enum"], expected)
        design = json.loads(DESIGN_SCHEMA_PATH.read_text(encoding="utf-8"))
        figures = design["properties"]["figures"]["properties"]["default_placement"]
        self.assertEqual(figures["enum"], expected)

    def test_structure_enum_matches_the_diagram_reference(self) -> None:
        text = DIAGRAM_SPEC_DOC.read_text(encoding="utf-8")
        section = text.split("## Structure selection", 1)[1].split("\n## ", 1)[0]
        tokens = re.findall(r"^- \*\*[^*]+\*\* \(`([a-z-]+)`\):", section, re.MULTILINE)
        self.assertEqual(8, len(tokens), tokens)
        self.assertEqual(STRUCTURES, tokens + ["scene"])
        self.assertEqual(planned_visual_schema()["properties"]["structure"]["enum"], STRUCTURES)

    def test_kind_enum_matches_the_visual_brief_routing(self) -> None:
        self.assertEqual(planned_visual_schema()["properties"]["kind"]["enum"], KINDS)

    def test_bundled_schema_and_mirror_are_byte_identical(self) -> None:
        self.assertEqual(ARCHITECTURE_SCHEMA_PATH.read_bytes(), MIRROR_PATH.read_bytes())

    def test_contracts_name_the_same_tokens(self) -> None:
        documents = [
            ROOT / "skills/nam-book-architect/references/architecture-contract.md",
            ROOT / "skills/nam-book-visuals/references/visual-brief-contract.md",
            ROOT / "skills/nam-book-illustration-setup/references/setup-contract.md",
            ROOT / "CONTEXT.md",
        ]
        for path in documents:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                for token in PLACEMENTS:
                    self.assertIn(f"`{token}`", text)
        for path in documents[:2] + [ROOT / "CONTEXT.md"]:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name, vocabulary="structure"):
                for token in STRUCTURES:
                    self.assertIn(f"`{token}`", text)


class PlannedVisualRulesTests(unittest.TestCase):
    def check(self, **visual: str) -> list[str]:
        return check_object(planned_visual_schema(), visual)

    def test_legacy_visual_without_new_fields_still_validates(self) -> None:
        self.assertEqual([], self.check(figure_id="fig-ch01-01", kind="illustration", learning_job="orient"))
        self.assertEqual([], self.check(figure_id="fig-ch01-02", kind="table", learning_job="compare"))

    def test_diagram_and_hybrid_require_structure(self) -> None:
        for kind in ("diagram", "hybrid"):
            with self.subTest(kind=kind):
                errors = self.check(figure_id="fig-ch01-03", kind=kind, learning_job="explain")
                self.assertIn("missing structure", errors)

    def test_mechanism_diagram_with_full_page_placement_validates(self) -> None:
        errors = self.check(
            figure_id="fig-ch03-04", kind="diagram", structure="mechanism",
            placement="full-page", learning_job="make the causal chain inspectable",
        )
        self.assertEqual([], errors)

    def test_unknown_tokens_are_rejected(self) -> None:
        self.assertIn("placement not in enum", self.check(figure_id="f", kind="illustration", learning_job="x", placement="margin"))
        self.assertIn("structure not in enum", self.check(figure_id="f", kind="diagram", learning_job="x", structure="flowchart"))
        self.assertIn("kind not in enum", self.check(figure_id="f", kind="chart", learning_job="x"))
        self.assertIn("unexpected layout", self.check(figure_id="f", kind="table", learning_job="x", layout="band"))


def style_rules(svg_text: str) -> dict[str, dict[str, str]]:
    return APPLY_TOKENS.parse_style(svg_text)


class ApplyTokensTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.spec = json.loads(PRESET_PATH.read_text(encoding="utf-8"))

    def test_template_declares_token_sources_and_neutral_fallbacks(self) -> None:
        style = re.search(r"<style>(.*?)</style>", self.template, re.S).group(1)
        self.assertIn("design_spec.typography.labels", style)
        self.assertIn("illustration_setup.visual_tokens.palette", style)
        self.assertNotIn("Arial", style)
        rules = style_rules(self.template)
        self.assertIn(".arrowhead", rules)
        self.assertEqual("sans-serif", rules[".label"]["font-family"])

    def test_design_spec_fonts_and_palette_replace_template_values(self) -> None:
        result = APPLY_TOKENS.apply_tokens(self.template, self.spec)
        rules = style_rules(result)
        labels = self.spec["typography"]["labels"]
        color = self.spec["color"]
        self.assertTrue(rules[".label"]["font-family"].startswith('"Source Sans 3"'), rules[".label"])
        self.assertNotEqual("Arial", rules[".label"]["font-family"].split(",")[0].strip().strip('"'))
        self.assertEqual(str(labels["weight"]), rules[".label"]["font-weight"])
        self.assertEqual(color["ink"], rules[".label"]["fill"])
        self.assertEqual(color["paper"], rules[".canvas"]["fill"])
        self.assertEqual(color["ink"], rules[".node"]["stroke"])
        self.assertEqual(color["muted"], rules[".edge"]["stroke"])
        self.assertEqual(color["muted"], rules[".arrowhead"]["fill"])
        self.assertEqual(color["tint"], rules[".input"]["fill"])
        fills = {rules[selector]["fill"] for selector in (".input", ".process", ".outcome")}
        self.assertEqual(3, len(fills), "node fills must stay distinguishable")
        self.assertEqual("3", rules[".node"]["stroke-width"], "unrelated declarations are preserved")
        self.assertEqual(self.template.split("</style>", 1)[1], result.split("</style>", 1)[1])

    def test_result_passes_svg_validation(self) -> None:
        result = APPLY_TOKENS.apply_tokens(self.template, self.spec)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "diagram.svg"
            path.write_text(result, encoding="utf-8")
            report = VALIDATE_SVG.inspect_svg(path)
        self.assertEqual([], report["errors"], report)

    def test_setup_palette_roles_override_the_design_spec(self) -> None:
        setup = {"visual_tokens": {"palette": [
            {"role": "ink", "value": "#222222"},
            {"role": "process", "value": "#ffe0b2"},
            {"role": "sash", "value": "#0f766e"},
        ]}}
        rules = style_rules(APPLY_TOKENS.apply_tokens(self.template, self.spec, setup))
        self.assertEqual("#222222", rules[".node"]["stroke"])
        self.assertEqual("#222222", rules[".label"]["fill"])
        self.assertEqual("#ffe0b2", rules[".process"]["fill"])
        self.assertEqual(self.spec["color"]["paper"], rules[".canvas"]["fill"])

    def test_bare_palette_values_map_by_the_documented_order(self) -> None:
        self.assertEqual(["ink", "paper", "accent", "muted", "neutral", "process", "outcome"], APPLY_TOKENS.PALETTE_ORDER)
        setup = {"visual_tokens": {"palette": ["#101010", "#fafafa"]}}
        rules = style_rules(APPLY_TOKENS.apply_tokens(self.template, self.spec, setup))
        self.assertEqual("#101010", rules[".node"]["stroke"])
        self.assertEqual("#fafafa", rules[".canvas"]["fill"])
        named_only = {"visual_tokens": {"palette": ["teal"]}}
        rules = style_rules(APPLY_TOKENS.apply_tokens(self.template, self.spec, named_only))
        self.assertEqual(self.spec["color"]["ink"], rules[".node"]["stroke"])

    def test_cli_writes_the_tokenized_svg(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "out.svg"
            completed = subprocess.run(
                [sys.executable, str(ROOT / "skills/nam-book-diagram/scripts/apply_tokens.py"),
                 "--svg", str(TEMPLATE_PATH), "--design-spec", str(PRESET_PATH), "--out", str(out)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(str(out), report["out"])
            self.assertIn("Source Sans 3", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
