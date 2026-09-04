from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_repository.py"
SPEC = importlib.util.spec_from_file_location("validate_repository", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class RepositoryTests(unittest.TestCase):
    def test_repository_validator(self) -> None:
        self.assertEqual([], VALIDATOR.validate())

    def test_plugin_references_every_skill_directory(self) -> None:
        manifest = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual("./skills/", manifest["skills"])
        self.assertEqual(
            VALIDATOR.EXPECTED_SKILLS,
            {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()},
        )

    def test_final_nam_icon_has_alpha(self) -> None:
        self.assertIn(VALIDATOR.png_color_type(ROOT / "assets" / "nam-icon.png"), {4, 6})

    def test_canonical_nam_assets_are_consistent(self) -> None:
        expected_icon_hash = (
            "16b1c40578cb79f77bc87b8d4dbe09fc76bfbc6e59e91d2acaca4cd28dece8b9"
        )
        icon_paths = [
            ROOT / "assets" / "nam-icon.png",
            ROOT / "skills" / "asknam" / "assets" / "nam-icon.png",
            ROOT
            / "skills"
            / "nam-book-illustrate"
            / "assets"
            / "nam-v1"
            / "nam-icon.png",
        ]
        for path in icon_paths:
            self.assertEqual(expected_icon_hash, hashlib.sha256(path.read_bytes()).hexdigest())

        sheet_path = ROOT / "skills" / "nam-book-illustrate" / "assets" / "nam-v1" / "nam-character-sheet.png"
        self.assertEqual(
            "0b84633e4bbbb0ec88dfcac197f0cfc59ec9976c4496c459b8dbdc3f5be5944c",
            hashlib.sha256(sheet_path.read_bytes()).hexdigest(),
        )

        character_bible = (
            ROOT
            / "skills"
            / "nam-book-visuals"
            / "references"
            / "nam-character-bible.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Small round charcoal eyes", character_bible)
        self.assertIn("No blue eye patches", character_bible)

    def test_publication_route_has_separate_proof_and_release_nodes(self) -> None:
        catalog = json.loads(
            (
                ROOT
                / "skills"
                / "asknam"
                / "references"
                / "skill-catalog.json"
            ).read_text(encoding="utf-8")
        )
        publication = next(
            item for item in catalog["capabilities"] if item["skill"] == "nam-book-publish"
        )
        nodes = {item["id"]: item for item in publication["route_nodes"]}
        self.assertEqual("proof", nodes["nam-book-publish-proof"]["operation"])
        self.assertEqual("release", nodes["nam-book-publish-release"]["operation"])
        self.assertIn(
            "nam-book-validate",
            nodes["nam-book-publish-release"]["depends_on"],
        )

    def test_art_setup_owns_identity_and_precedes_visual_planning(self) -> None:
        catalog = json.loads(
            (ROOT / "skills" / "asknam" / "references" / "skill-catalog.json")
            .read_text(encoding="utf-8")
        )
        capabilities = {item["skill"]: item for item in catalog["capabilities"]}
        setup = capabilities["nam-book-illustration-setup"]
        visuals = capabilities["nam-book-visuals"]
        self.assertEqual([], setup["depends_on"])
        self.assertEqual(["project-brief"], setup["approval_gates"])
        self.assertEqual(
            {"illustration_setup", "character_bible"},
            {output["kind"] for output in setup["produces"] if output.get("required", True)},
        )
        self.assertIn("nam-book-illustration-setup", visuals["depends_on"])
        self.assertIn("illustration-setup", visuals["approval_gates"])
        self.assertEqual({"visual_brief"}, {item["kind"] for item in visuals["produces"]})
        for producer in ("nam-book-illustrate", "nam-book-diagram"):
            self.assertIn("illustration-setup", capabilities[producer]["approval_gates"])
        owners = [
            item["skill"] for item in capabilities.values()
            if any(output["kind"] == "character_bible" for output in item["produces"])
        ]
        self.assertEqual(["nam-book-illustration-setup"], owners)

    def test_all_profiles_include_early_art_setup(self) -> None:
        for profile_path in (ROOT / "skills" / "asknam" / "references" / "profiles").glob("*.json"):
            with self.subTest(profile=profile_path.stem):
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
                self.assertIn("nam-book-illustration-setup", profile["start_skills"])

    def test_skill_reference_links_stay_inside_sibling_installation(self) -> None:
        skills_root = (ROOT / "skills").resolve()
        for markdown_path in skills_root.rglob("*.md"):
            for target in VALIDATOR.local_markdown_targets(markdown_path):
                with self.subTest(source=str(markdown_path), target=str(target)):
                    self.assertTrue(target.is_relative_to(skills_root))
                    self.assertTrue(target.exists())

    def test_setup_templates_start_unapproved_and_share_project_fields(self) -> None:
        assets = ROOT / "skills" / "nam-book-illustration-setup" / "assets"
        setup = json.loads((assets / "illustration-setup.template.json").read_text(encoding="utf-8"))
        bible = json.loads((assets / "character-bible.template.json").read_text(encoding="utf-8"))
        self.assertIs(setup["hand_drawn"], True)
        self.assertEqual("pending", setup["calibration"]["status"])
        self.assertEqual([], setup["calibration"]["sample_artifact_ids"])
        for field in ("project_id", "locale", "mascot_mode"):
            self.assertEqual(setup[field], bible[field])
        self.assertTrue(setup["open_questions"])


if __name__ == "__main__":
    unittest.main()
