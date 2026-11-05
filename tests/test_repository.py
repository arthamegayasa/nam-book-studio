from __future__ import annotations

import contextlib
import importlib.util
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_repository.py"
SPEC = importlib.util.spec_from_file_location("validate_repository", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

CHECKS_SPEC = importlib.util.spec_from_file_location("run_checks", ROOT / "scripts" / "run_checks.py")
assert CHECKS_SPEC and CHECKS_SPEC.loader
RUN_CHECKS = importlib.util.module_from_spec(CHECKS_SPEC)
sys.modules[CHECKS_SPEC.name] = RUN_CHECKS
CHECKS_SPEC.loader.exec_module(RUN_CHECKS)


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

    def test_markdown_scan_skips_ignored_and_scratch_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                "tmp/x.md",
                ".scratch/y.md",
                "docs/z.md",
                "skills/a/SKILL.md",
                "output/o.md",
                "build/b.md",
                "dist/d.md",
                ".git/g.md",
                "skills/__pycache__/p.md",
                "skills/a/tmp/nested.md",
                ".claude/worktrees/w/README.md",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# x\n", encoding="utf-8")
            found = sorted(path.relative_to(root).as_posix() for path in VALIDATOR.markdown_files(root))
        self.assertEqual(["docs/z.md", "skills/a/SKILL.md"], found)
        self.assertIn(".claude", VALIDATOR.SKIPPED_DIRECTORIES)

    ASKNAM_SKILL = (
        "---\nname: asknam\n"
        "description: Route and run a Nam Book Studio project through the smallest sufficient workflow.\n"
        "disable-model-invocation: true\n---\n\n# AskNam\n"
    )
    ASKNAM_YAML = (
        'interface:\n  default_prompt: "Use $asknam to route my book."\n'
        "policy:\n  allow_implicit_invocation: false\n"
    )
    SPECIALIST_SKILL = (
        "---\nname: nam-book-write\n"
        "description: Draft or revise book chapters from an approved chapter specification.\n---\n\n# Nam Book Write\n"
    )
    SPECIALIST_YAML = (
        'interface:\n  default_prompt: "Use $nam-book-write to draft this chapter."\n'
        "policy:\n  allow_implicit_invocation: true\n"
    )

    def test_skill_metadata_requires_explicit_only_asknam_in_both_hosts(self) -> None:
        check = VALIDATOR.check_skill_metadata
        self.assertEqual([], check("asknam", self.ASKNAM_SKILL, self.ASKNAM_YAML))
        errors = check("asknam", self.ASKNAM_SKILL.replace("disable-model-invocation: true\n", ""), self.ASKNAM_YAML)
        self.assertTrue(any("disable-model-invocation" in error for error in errors), errors)
        errors = check("asknam", self.ASKNAM_SKILL, self.ASKNAM_YAML.replace("false", "true"))
        self.assertTrue(any("explicit-only" in error for error in errors), errors)

    def test_skill_metadata_keeps_specialists_model_invoked_in_both_hosts(self) -> None:
        check = VALIDATOR.check_skill_metadata
        self.assertEqual([], check("nam-book-write", self.SPECIALIST_SKILL, self.SPECIALIST_YAML))
        flagged = self.SPECIALIST_SKILL.replace("---\n\n# Nam", "disable-model-invocation: true\n---\n\n# Nam")
        errors = check("nam-book-write", flagged, self.SPECIALIST_YAML)
        self.assertTrue(any("disable-model-invocation" in error for error in errors), errors)
        undeclared = self.SPECIALIST_YAML.split("policy:")[0]
        errors = check("nam-book-write", self.SPECIALIST_SKILL, undeclared)
        self.assertTrue(any("allow_implicit_invocation: true" in error for error in errors), errors)
        errors = check("nam-book-write", self.SPECIALIST_SKILL, self.SPECIALIST_YAML.replace("true", "false"))
        self.assertTrue(any("model-invoked" in error for error in errors), errors)
        errors = check("nam-book-write", self.SPECIALIST_SKILL, self.SPECIALIST_YAML.replace("$nam-book-write", "the skill"))
        self.assertTrue(any("default_prompt" in error for error in errors), errors)
        errors = check("nam-book-write", self.SPECIALIST_SKILL, None)
        self.assertTrue(any("openai.yaml is missing" in error for error in errors), errors)

    @staticmethod
    def write_json(root: Path, relative: str, payload: dict) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_claude_manifests_match_codex_version_and_list_the_plugin(self) -> None:
        codex = {
            "name": "nam-book-studio", "version": "0.2.0", "skills": "./skills/",
            "author": {"name": "A"}, "interface": {"defaultPrompt": ["Use $asknam to go."]},
        }
        plugin = {"name": "nam-book-studio", "version": "0.2.0", "description": "d"}
        marketplace = {
            "name": "nam-book-studio", "owner": {"name": "A"},
            "plugins": [{"name": "nam-book-studio", "source": "./", "version": "0.2.0"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_json(root, ".codex-plugin/plugin.json", codex)
            errors = VALIDATOR.check_claude_manifests(root)
            self.assertTrue(any(".claude-plugin/plugin.json" in error for error in errors), errors)
            self.assertTrue(any("marketplace.json" in error for error in errors), errors)
            self.write_json(root, ".claude-plugin/plugin.json", plugin)
            self.write_json(root, ".claude-plugin/marketplace.json", marketplace)
            self.assertEqual([], VALIDATOR.check_claude_manifests(root))
            self.write_json(root, ".claude-plugin/plugin.json", {**plugin, "version": "0.3.0"})
            self.assertTrue(any("version" in error for error in VALIDATOR.check_claude_manifests(root)))
            self.write_json(root, ".claude-plugin/plugin.json", {**plugin, "name": "other"})
            self.assertTrue(any("name" in error for error in VALIDATOR.check_claude_manifests(root)))
            self.write_json(root, ".claude-plugin/plugin.json", plugin)
            self.write_json(
                root, ".claude-plugin/marketplace.json",
                {**marketplace, "plugins": [{"name": "nam-book-studio", "source": "./plugins/nam", "version": "0.2.0"}]},
            )
            self.assertTrue(any("source" in error for error in VALIDATOR.check_claude_manifests(root)))
            self.write_json(root, ".claude-plugin/marketplace.json", {**marketplace, "plugins": []})
            self.assertTrue(any("marketplace" in error for error in VALIDATOR.check_claude_manifests(root)))

    def test_host_specific_references_are_allowed_only_in_codex_files(self) -> None:
        files = {
            "skills/x/SKILL.md": "Route evidence to `$nam-book-research`.\n",
            "skills/x/references/r.md": "Scored banks belong to $nam-book-assess.\n",
            "skills/x/scripts/s.py": "PROMPT = 'Use $asknam to continue'\n",
            "skills/x/agents/openai.yaml": 'default_prompt: "Use $nam-book-x to do it."\n',
            "docs/a.md": "Use $asknam to set up.\n",
            "docs/b.json": '{"prompt": "Use $asknam"}\n',
            "README.md": "Use $asknam to create a book.\n",
            "CONTEXT.md": "A dollar sign alone, as in `$price`, is not a skill reference.\n",
            ".codex-plugin/plugin.json": '{"defaultPrompt": ["Use $asknam to go."]}\n',
            "scripts/validate_repository.py": "pattern = '$asknam'\n",
            "tests/test_x.py": "x = '$nam-book-write'\n",
            ".claude/worktrees/w/skills/x/SKILL.md": "`$nam-book-research`\n",
            "tmp/t.md": "$asknam\n",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            found = VALIDATOR.host_specific_references(root)
            self.assertEqual(
                ["docs/a.md", "docs/b.json", "skills/x/SKILL.md", "skills/x/references/r.md", "skills/x/scripts/s.py"],
                sorted({path.relative_to(root).as_posix() for path, _, _ in found}),
            )
            hit = next(item for item in found if item[0].name == "SKILL.md")
            self.assertEqual(1, hit[1])
            self.assertIn("$nam-book-research", hit[2])

    def test_real_tree_is_host_neutral_outside_codex_files(self) -> None:
        self.assertEqual(
            [],
            [f"{path.relative_to(ROOT).as_posix()}:{number}: {text}" for path, number, text in VALIDATOR.host_specific_references(ROOT)],
        )

    def test_claude_plugin_packaging_matches_codex(self) -> None:
        codex = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual("nam-book-studio", plugin["name"])
        self.assertEqual(codex["version"], plugin["version"])
        self.assertEqual(["nam-book-studio"], [item["name"] for item in marketplace["plugins"]])
        self.assertEqual("./", marketplace["plugins"][0]["source"])
        self.assertEqual(codex["version"], marketplace["plugins"][0]["version"])
        self.assertEqual([], VALIDATOR.check_claude_manifests(ROOT))
        asknam = VALIDATOR.frontmatter((ROOT / "skills" / "asknam" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual("true", asknam.get("disable-model-invocation"))
        for name in sorted(VALIDATOR.EXPECTED_SKILLS - {"asknam"}):
            with self.subTest(skill=name):
                meta = VALIDATOR.frontmatter((ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8"))
                self.assertNotIn("disable-model-invocation", meta)
                policy = (ROOT / "skills" / name / "agents" / "openai.yaml").read_text(encoding="utf-8")
                self.assertIn("allow_implicit_invocation: true", policy)
        claude_md = [line for line in (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual("@AGENTS.md", claude_md[-1])

    def test_run_checks_lists_five_existing_gates(self) -> None:
        self.assertEqual(5, len(RUN_CHECKS.GATES))
        for gate in RUN_CHECKS.GATES:
            with self.subTest(gate=gate.name):
                self.assertTrue(gate.name)
                script = next((arg for arg in gate.args if arg.endswith(".py")), None)
                if script is not None:
                    self.assertTrue((ROOT / script).is_file(), script)
                else:
                    self.assertIn("-m", gate.args)
        self.assertEqual(
            ["validate_repository", "tests", "state_tools", "resources", "compileall"],
            [gate.name for gate in RUN_CHECKS.GATES],
        )

    def test_run_checks_list_mode_prints_commands_without_running(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = RUN_CHECKS.main(["--list"])
        self.assertEqual(0, code)
        output = buffer.getvalue()
        self.assertIn("scripts/validate_repository.py", output)
        self.assertIn("compileall", output)
        self.assertEqual(5, len([line for line in output.splitlines() if line.strip()]))

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

    def test_design_stage_owns_page_design_and_gates_publish_proof(self) -> None:
        catalog = json.loads(
            (ROOT / "skills" / "asknam" / "references" / "skill-catalog.json").read_text(encoding="utf-8")
        )
        capabilities = {item["skill"]: item for item in catalog["capabilities"]}
        design = capabilities["nam-book-design"]
        nodes = {item["id"]: item for item in design["route_nodes"]}
        self.assertEqual(["nam-book-illustration-setup"], nodes["nam-book-design"]["depends_on"])
        self.assertEqual(["project-brief"], nodes["nam-book-design"]["approval_gates"])
        self.assertEqual({"design_spec", "design_assets"}, set(nodes["nam-book-design"]["produces"]))
        self.assertEqual("proof", nodes["nam-book-design-proof"]["operation"])
        self.assertEqual(["nam-book-design"], nodes["nam-book-design-proof"]["depends_on"])
        self.assertEqual(["design_proof"], nodes["nam-book-design-proof"]["produces"])
        publish = capabilities["nam-book-publish"]
        proof = next(item for item in publish["route_nodes"] if item["id"] == "nam-book-publish-proof")
        self.assertIn("nam-book-design", proof["depends_on"])
        self.assertIn("design", proof["approval_gates"])
        owners = [
            item["skill"] for item in capabilities.values()
            if any(output["kind"] in {"design_spec", "design_assets", "design_proof"} for output in item["produces"])
        ]
        self.assertEqual(["nam-book-design"], owners)
        schema = json.loads(
            (ROOT / "skills" / "asknam" / "references" / "schemas" / "book-project.schema.json").read_text(encoding="utf-8")
        )
        kinds = schema["properties"]["approvals"]["items"]["properties"]["kind"]["enum"]
        self.assertIn("design", kinds)

    def test_design_presets_match_the_template_and_cover_every_mode(self) -> None:
        assets = ROOT / "skills" / "nam-book-design" / "assets"
        template = json.loads((assets / "design-spec.template.json").read_text(encoding="utf-8"))
        self.assertEqual("", template["project_id"])
        self.assertTrue(template["open_questions"])
        presets = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in (assets / "presets").glob("*.json")}
        self.assertEqual({"friendly-explainer", "textbook", "exam-prep"}, set(presets))
        for mode, preset in presets.items():
            with self.subTest(mode=mode):
                self.assertEqual(mode, preset["profile"])
                self.assertEqual(mode, preset["preset"])
                self.assertEqual(set(template), set(preset))
                self.assertEqual({"inline", "side-column", "band", "full-page", "opener"}, set(preset["callouts"]))
                self.assertIn(preset["render"]["pdf"]["engine"], {"chromium", "libreoffice"})
        catalog = json.loads(
            (ROOT / "skills" / "asknam" / "references" / "callout-catalog.json").read_text(encoding="utf-8")
        )
        icons = {path.stem for path in (assets / "icons").glob("*.svg")}
        self.assertEqual({item["type_id"] for item in catalog["types"]}, icons)
        for locale in ("en-US", "id-ID"):
            sample = (assets / "sample-chapter" / f"{locale}.md").read_text(encoding="utf-8")
            for entry in catalog["types"]:
                self.assertIn(f"type={entry['type_id']}", sample, f"{locale} sample lacks {entry['type_id']}")

    def test_all_profiles_include_early_art_setup(self) -> None:
        for profile_path in (ROOT / "skills" / "asknam" / "references" / "profiles").glob("*.json"):
            with self.subTest(profile=profile_path.stem):
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
                self.assertIn("nam-book-illustration-setup", profile["start_skills"])
                self.assertIn("nam-book-design", profile["start_skills"])
                self.assertLess(
                    profile["start_skills"].index("nam-book-illustration-setup"),
                    profile["start_skills"].index("nam-book-design"),
                )

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
