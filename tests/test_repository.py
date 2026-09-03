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


if __name__ == "__main__":
    unittest.main()
