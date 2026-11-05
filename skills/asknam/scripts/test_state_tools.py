from __future__ import annotations

import json
import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from state_core import (
    PROJECT_SCHEMA_URI,
    StateError,
    artifact_is_fresh,
    atomic_write_json,
    build_route,
    create_manifest,
    decide_approval,
    format_route_receipt,
    load_catalog,
    load_profile,
    mark_artifact_stale,
    migrate_illustration_setup,
    retained_nodes,
    refresh_file_staleness,
    register_artifact,
    transition_node,
    validate_state,
)
from validate_resources import validate as validate_resources


class StateToolsTests(unittest.TestCase):
    def register_fixture(self, state, state_path, kind, artifact_id, payload,
                         input_ids=None, chapter_id=None, status="review", raw_text=False,
                         blockers=None, callout_ids=None, locale=None, operation="run"):
        slot = state["artifact_registry"]["slots"][kind]
        locale = locale or state["source_locale"]
        path = slot["path"].replace("{artifact_id}", artifact_id).replace(
            "{locale}", locale
        ).replace("{chapter_id}", chapter_id or "")
        destination = state_path.parent.parent / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if kind == "illustration_calibration":
            destination.mkdir(exist_ok=True)
            # Structural fixture: gate checks the bundle fingerprint, not image aesthetics.
            (destination / "sample.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><circle cx="16" cy="16" r="8"/></svg>',
                encoding="utf-8",
            )
        elif isinstance(payload, dict) and payload.get("__bundle__"):
            # Directory bundle: every key except the marker becomes a file.
            destination.mkdir(exist_ok=True)
            for name, content in payload.items():
                if name == "__bundle__":
                    continue
                (destination / name).write_text(
                    content if isinstance(content, str) else json.dumps(content), encoding="utf-8",
                )
        else:
            destination.write_text(payload if raw_text else json.dumps(payload), encoding="utf-8")
        return register_artifact(
            state, state_path, artifact_id=artifact_id, kind=kind,
            relative_path=path, produced_by=slot["produced_by"], status=status,
            locale=locale, chapter_id=chapter_id,
            input_ids=input_ids or [], claim_ids=[], source_ids=[],
            blockers=blockers, callout_ids=callout_ids, operation=operation,
            origin="test-fixture", creator="Test author", license_name="project-owned",
            source_url="", notice_path="",
        )

    def setup_fixture(self, state, state_path, mode="custom", adopt_bible=False, adoption=None):
        transition_node(state, "nam-book-illustration-setup", "running")
        self.register_fixture(state, state_path, "illustration_calibration", "calibration-1", {})
        self.register_fixture(state, state_path, "illustration_setup", "illustration-setup", {
            "mascot_mode": mode, "hand_drawn": True,
            "adoption": adoption,
            "calibration": {"status": "passed", "sample_artifact_ids": ["calibration-1"]},
        }, ["calibration-1"])
        if not adopt_bible:
            self.register_fixture(state, state_path, "character_bible", "character-bible", {
                "mascot_mode": mode, "identity": None if mode == "none" else {"name": "River Otter"},
            }, ["calibration-1"])

    def approve_brief(self, state):
        decide_approval(state, approval_id="project-brief", decision="approved",
                        decided_by="Project owner", basis_ids=[], note="Scope accepted")

    def create(self, project_dir: Path, **overrides):
        options = {
            "title": "A Friendly Brain Book",
            "project_id": "brain-book",
            "subtitle": "",
            "audience": "Interested adult beginners",
            "reader_outcome": "Explain the core concepts accurately",
            "profile_id": "friendly-explainer",
            "source_locale": "id-ID",
            "target_locales": [],
            "risk_level": "R0",
            "medical_enabled": False,
            "jurisdiction": None,
            "evidence_cutoff": None,
            "revalidate_before_export": None,
            "assessments": "auto",
            "illustrations": "auto",
            "diagrams": "auto",
            "deliverables": ["markdown", "pdf"],
        }
        options.update(overrides)
        state = create_manifest(**options)
        state_path = project_dir / ".nam-book" / "project.json"
        atomic_write_json(state_path, state)
        return state, state_path

    def test_initial_route_is_gated_and_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            errors, warnings = validate_state(state, state_path)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            route = {item["skill"]: item for item in state["route"]["nodes"]}
            self.assertEqual(route["nam-book-research"]["status"], "blocked")
            self.assertIn("approval:project-brief", route["nam-book-research"]["blockers"])
            self.assertIn("nam-book-illustrate", route)
            setup = route["nam-book-illustration-setup"]
            self.assertEqual(setup["depends_on"], [])
            self.assertEqual(setup["required_approvals"], ["project-brief"])
            self.approve_brief(state)
            self.assertEqual(setup["status"], "ready")
            self.assertEqual(route["nam-book-research"]["status"], "ready")

    def test_setup_selection_is_early_optional_and_focused(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary), illustrations="no", diagrams="yes")
            nodes = {item["id"]: item for item in state["route"]["nodes"]}
            self.assertIn("nam-book-illustration-setup", nodes)
            self.assertIn("illustration-setup", nodes["nam-book-visuals"]["required_approvals"])
            state, state_path = self.create(Path(temporary), illustrations="no", diagrams="no")
            self.assertNotIn("nam-book-illustration-setup", {item["id"] for item in state["route"]["nodes"]})
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "setup-illustration")
            self.assertEqual([item["id"] for item in state["route"]["nodes"]], ["nam-book-illustration-setup"])
            self.assertFalse(state["features"]["illustrations"])
            self.assertFalse(state["features"]["diagrams"])
            self.assertEqual(validate_state(state, state_path)[0], [])
            cutoff = date.today()
            state, state_path = self.create(Path(temporary), medical_enabled=True, risk_level="R3",
                jurisdiction="Indonesia", evidence_cutoff=cutoff.isoformat(),
                revalidate_before_export=(cutoff + timedelta(days=30)).isoformat())
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "setup-illustration")
            self.assertEqual(len(state["route"]["nodes"]), 1)
            self.assertEqual(validate_state(state, state_path)[0], [])

    def test_setup_approval_binds_complete_pair_and_reviewed_calibration(self):
        for mode in ("custom", "supplied", "nam", "none"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                state, state_path = self.create(Path(temporary))
                self.approve_brief(state)
                self.setup_fixture(state, state_path, mode)
                options = dict(approval_id="illustration-setup", decision="approved",
                               decided_by="Project owner", note="Visual sample accepted", state_path=state_path)
                with self.assertRaisesRegex(StateError, "completed setup"):
                    decide_approval(state, basis_ids=["illustration-setup", "character-bible"], **options)
                transition_node(state, "nam-book-illustration-setup", "complete")
                with self.assertRaisesRegex(StateError, "must bind"):
                    decide_approval(state, basis_ids=["calibration-1"], **options)
                with self.assertRaisesRegex(StateError, "must bind"):
                    decide_approval(state, basis_ids=["character-bible"], **options)
                approval = decide_approval(state, basis_ids=["illustration-setup", "character-bible"], **options)
                self.assertEqual(len(approval["basis"]), 2)
                self.assertEqual(validate_state(state, state_path)[0], [])
                calibration = next(item for item in state["artifact_registry"]["entries"] if item["artifact_id"] == "calibration-1")
                self.assertEqual(calibration["hash_kind"], "sha256-tree-v1")
                (Path(temporary) / calibration["path"] / "sample.svg").write_text("changed sample", encoding="utf-8")
                refresh_file_staleness(state, state_path)
                self.assertEqual(approval["status"], "expired")
                affected = set(state["staleness"][0]["invalidates_nodes"])
                self.assertIn("nam-book-visuals", affected)
                self.assertNotIn("nam-book-research", affected)
                self.assertNotIn("nam-book-write", affected)

    def test_setup_rejects_unreviewed_calibration_and_changed_basis_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            self.approve_brief(state)
            self.setup_fixture(state, state_path)
            setup = next(item for item in state["artifact_registry"]["entries"] if item["kind"] == "illustration_setup")
            self.register_fixture(state, state_path, "illustration_setup", "illustration-setup", {
                "mascot_mode": "custom", "hand_drawn": True,
                "calibration": {"status": "pending", "sample_artifact_ids": ["calibration-1"]},
            }, ["calibration-1"])
            # Re-register the unchanged bible after a setup invalidation.
            self.register_fixture(state, state_path, "character_bible", "character-bible", {
                "mascot_mode": "custom", "identity": {"name": "River Otter"},
            }, ["calibration-1"])
            transition_node(state, "nam-book-illustration-setup", "complete")
            with self.assertRaisesRegex(StateError, "passed calibration"):
                decide_approval(state, approval_id="illustration-setup", decision="approved",
                    decided_by="Owner", basis_ids=["illustration-setup", "character-bible"],
                    note="", state_path=state_path)
            (Path(temporary) / setup["path"]).write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(StateError, "bytes differ"):
                decide_approval(state, approval_id="illustration-setup", decision="approved",
                    decided_by="Owner", basis_ids=["illustration-setup", "character-bible"],
                    note="", state_path=state_path)

    def test_setup_rejects_identity_inconsistent_with_mascot_mode(self):
        for mode, identity in (("none", {"name": "Unexpected mascot"}), ("custom", None)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                state, state_path = self.create(Path(temporary))
                self.approve_brief(state)
                self.setup_fixture(state, state_path, mode)
                self.register_fixture(state, state_path, "character_bible", "character-bible", {
                    "mascot_mode": mode, "identity": identity,
                }, ["calibration-1"])
                self.register_fixture(state, state_path, "illustration_setup", "illustration-setup", {
                    "mascot_mode": mode, "hand_drawn": True,
                    "calibration": {"status": "passed", "sample_artifact_ids": ["calibration-1"]},
                }, ["calibration-1"])
                transition_node(state, "nam-book-illustration-setup", "complete")
                with self.assertRaisesRegex(StateError, "identity"):
                    decide_approval(state, approval_id="illustration-setup", decision="approved",
                        decided_by="Owner", basis_ids=["illustration-setup", "character-bible"],
                        note="", state_path=state_path)

    def test_focused_setup_preserves_completed_text_and_parked_invalidations(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            self.approve_brief(state)
            research = next(item for item in state["route"]["nodes"] if item["id"] == "nam-book-research")
            transition_node(state, research["id"], "running")
            self.register_fixture(state, state_path, "research_brief", "research-brief", {})
            self.register_fixture(state, state_path, "evidence_ledger", "evidence-ledger", {})
            transition_node(state, research["id"], "complete")
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "setup-illustration")
            self.assertEqual(next(item for item in retained_nodes(state) if item["id"] == research["id"])["status"], "complete")
            self.setup_fixture(state, state_path)
            transition_node(state, "nam-book-illustration-setup", "complete")
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "resume")
            self.assertEqual(next(item for item in state["route"]["nodes"] if item["id"] == research["id"])["status"], "complete")
            # Repeated focused routes must not erase omitted canonical dependencies.
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "illustrate")
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "setup-illustration")
            invalidated = mark_artifact_stale(state, "research-brief", "Evidence changed while art setup is focused")
            self.assertTrue({"nam-book-visuals", "nam-book-diagram", "nam-book-illustrate", "nam-book-validate",
                             "nam-book-publish-release"}.issubset(invalidated))
            self.assertNotIn("nam-book-illustration-setup", invalidated)
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "resume")
            self.assertEqual(next(item for item in state["route"]["nodes"] if item["id"] == research["id"])["status"], "stale")

    def test_legacy_migration_preserves_bible_history_and_text_then_requires_new_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary), assessments="no", diagrams="no")
            # A v0.1 manifest remains readable with its original owner and gate.
            slots = state["artifact_registry"]["slots"]
            del slots["illustration_setup"]
            del slots["illustration_calibration"]
            slots["character_bible"]["produced_by"] = "nam-book-visuals"
            state["approvals"] = [item for item in state["approvals"] if item["approval_id"] != "illustration-setup"]
            old_gate = copy.deepcopy(state["approvals"][1])
            old_gate.update(approval_id="character-bible", kind="character-bible")
            state["approvals"].append(old_gate)
            state["route"]["nodes"] = [item for item in state["route"]["nodes"] if item["id"] != "nam-book-illustration-setup"]
            for node in state["route"]["nodes"]:
                node["depends_on"] = [item for item in node["depends_on"] if item != "nam-book-illustration-setup"]
                if node["id"] == "nam-book-visuals":
                    node["required_approvals"] = ["architecture"]
                    node["produces"] = ["visual_brief", "character_bible"]
                elif node["id"] == "nam-book-illustrate":
                    node["required_approvals"] = ["character-bible"]
            state["route"]["edges"] = [
                {"from": dep, "to": node["id"]}
                for node in state["route"]["nodes"] for dep in node["depends_on"]
            ]
            self.approve_brief(state)
            decide_approval(state, approval_id="architecture", decision="approved",
                            decided_by="Owner", basis_ids=[], note="Architecture accepted")
            for node in state["route"]["nodes"]:
                if node["id"] in {"nam-book-research", "nam-book-architect", "nam-book-voice"}:
                    node["status"] = "complete"
            transition_node(state, "nam-book-write", "running")
            draft = self.register_fixture(state, state_path, "chapter_draft", "chapter-1", {"text": "Original draft"}, chapter_id="chapter-1")
            transition_node(state, "nam-book-write", "complete")
            next(node for node in state["route"]["nodes"] if node["id"] == "nam-book-teach")["status"] = "complete"
            transition_node(state, "nam-book-visuals", "running")
            self.register_fixture(state, state_path, "visual_brief", "visual-brief", {})
            bible = self.register_fixture(state, state_path, "character_bible", "character-bible",
                "Nam character bible\nEyes: small round charcoal; no blue.\n", raw_text=True)
            transition_node(state, "nam-book-visuals", "complete")
            decide_approval(state, approval_id="character-bible", decision="approved", decided_by="Nam",
                            basis_ids=["character-bible"], note="Existing Nam accepted")
            original_bible = copy.deepcopy(bible)
            original_gate = copy.deepcopy(old_gate)
            original_draft = copy.deepcopy(draft)
            errors, warnings = validate_state(state, state_path)
            self.assertEqual(errors, [])
            self.assertTrue(any("Legacy visual ownership" in item for item in warnings))
            with self.assertRaisesRegex(StateError, "explicit migrate-illustration-setup"):
                build_route(state, load_catalog(), load_profile(state["profile"]), "resume")
            result = migrate_illustration_setup(state)
            self.assertTrue(result["migrated"])
            self.assertNotIn("nam-book-write", result["invalidated_nodes"])
            self.assertEqual(bible["produced_by"], "nam-book-illustration-setup")
            for key in ("artifact_id", "path", "sha256", "revision", "revision_history", "status", "provenance"):
                self.assertEqual(bible[key], original_bible[key])
            self.assertEqual(old_gate, original_gate)
            self.assertEqual(draft, original_draft)
            self.assertEqual(validate_state(state, state_path)[0], [])
            after_migration = copy.deepcopy(state)
            self.assertFalse(migrate_illustration_setup(state)["migrated"])
            self.assertEqual(state, after_migration)
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "setup-illustration")
            self.setup_fixture(state, state_path, "nam", adopt_bible=True, adoption={
                "character_bible_artifact_id": "character-bible", "sha256": bible["sha256"],
                "approval_ids": ["character-bible"], "reason": "Preserve existing Nam",
            })
            transition_node(state, "nam-book-illustration-setup", "complete")
            approval = decide_approval(state, approval_id="illustration-setup", decision="approved", decided_by="Nam",
                basis_ids=["illustration-setup", "character-bible"], note="Adopted art reviewed", state_path=state_path)
            self.assertEqual(approval["status"], "approved")
            self.assertEqual(bible["revision_history"], original_bible["revision_history"])
            self.assertEqual(old_gate, original_gate)
            state["route"] = build_route(state, load_catalog(), load_profile(state["profile"]), "resume")
            self.assertEqual(next(node for node in state["route"]["nodes"] if node["id"] == "nam-book-write")["status"], "complete")
            self.assertEqual(next(node for node in state["route"]["nodes"] if node["id"] == "nam-book-visuals")["status"], "stale")
            self.assertEqual(validate_state(state, state_path)[0], [])

    def test_bundled_resources_match_repository_mirrors(self):
        self.assertEqual(validate_resources(require_mirrors=True), [])

    def test_asknam_initializes_from_per_skill_install_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            isolated = Path(temporary)
            asknam_source = Path(__file__).resolve().parents[1]
            installed_asknam = isolated / "skills" / "asknam"
            shutil.copytree(asknam_source, installed_asknam)
            project = isolated / "book-project"
            init = subprocess.run(
                [
                    sys.executable,
                    str(installed_asknam / "scripts" / "init_project.py"),
                    "--project-dir",
                    str(project),
                    "--title",
                    "Portable Book",
                    "--audience",
                    "Adult beginners",
                    "--reader-outcome",
                    "Explain the topic",
                    "--profile",
                    "friendly-explainer",
                    "--source-locale",
                    "id-ID",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            state_path = project / ".nam-book" / "project.json"
            validate = subprocess.run(
                [
                    sys.executable,
                    str(installed_asknam / "scripts" / "validate_state.py"),
                    "--state",
                    str(state_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            plan = subprocess.run(
                [
                    sys.executable,
                    str(installed_asknam / "scripts" / "plan_route.py"),
                    "--state",
                    str(state_path),
                    "--intent",
                    "resume",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)

    def test_exam_profile_cannot_disable_assessment(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(StateError):
                self.create(
                    Path(temporary),
                    profile_id="exam-prep",
                    assessments="no",
                )

    def test_medical_route_requires_dates_and_signoff(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(StateError):
                self.create(Path(temporary), medical_enabled=True, risk_level="R3")
            cutoff = date.today()
            state, state_path = self.create(
                Path(temporary),
                medical_enabled=True,
                risk_level="R3",
                jurisdiction="Indonesia",
                evidence_cutoff=cutoff.isoformat(),
                revalidate_before_export=(cutoff + timedelta(days=30)).isoformat(),
            )
            publish = next(
                item
                for item in state["route"]["nodes"]
                if item["id"] == "nam-book-publish-release"
            )
            self.assertIn("medical-expert-signoff", publish["required_approvals"])
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])

    def test_r3_requires_medical_but_r2_medical_has_no_expert_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(StateError):
                self.create(Path(temporary), risk_level="R3", medical_enabled=False)

            cutoff = date.today()
            state, state_path = self.create(
                Path(temporary),
                risk_level="R2",
                medical_enabled=True,
                jurisdiction="Indonesia",
                evidence_cutoff=cutoff.isoformat(),
                revalidate_before_export=(cutoff + timedelta(days=30)).isoformat(),
            )
            approvals = {item["approval_id"] for item in state["approvals"]}
            self.assertNotIn("medical-expert-signoff", approvals)
            release = next(
                item
                for item in state["route"]["nodes"]
                if item["id"] == "nam-book-publish-release"
            )
            self.assertNotIn("medical-expert-signoff", release["required_approvals"])
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])

    def test_r3_approval_requires_named_expert_and_hash_bound_basis(self):
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary)
            cutoff = date.today()
            state, state_path = self.create(
                project_dir,
                risk_level="R3",
                medical_enabled=True,
                jurisdiction="Indonesia",
                evidence_cutoff=cutoff.isoformat(),
                revalidate_before_export=(cutoff + timedelta(days=30)).isoformat(),
            )
            decide_approval(
                state,
                approval_id="project-brief",
                decision="approved",
                decided_by="Nam",
                basis_ids=[],
                note="Scope confirmed",
            )
            transition_node(state, "nam-book-research", "running")
            research_path = (
                project_dir
                / ".nam-book"
                / "artifacts"
                / "research"
                / "research-brief.json"
            )
            research_path.parent.mkdir(parents=True)
            research_path.write_text("{}", encoding="utf-8")
            with self.assertRaises(StateError):
                register_artifact(
                    state,
                    state_path,
                    artifact_id="research-brief",
                    kind="research_brief",
                    relative_path=".nam-book/artifacts/research/research-brief.json",
                    produced_by="nam-book-research",
                    status="approved",
                    locale="id-ID",
                    chapter_id=None,
                    input_ids=[],
                    claim_ids=[],
                    source_ids=[],
                    origin="project-generated",
                    creator="Nam Book Studio",
                    license_name="project-owned",
                    source_url="",
                    notice_path="",
                )

            state["artifact_registry"]["entries"].extend(
                [
                    {
                        "artifact_id": "evidence-ledger",
                        "kind": "evidence_ledger",
                        "status": "review",
                        "operation": "run",
                        "revision": 1,
                        "sha256": "a" * 64,
                        "blockers": [],
                    },
                    {
                        "artifact_id": "validation-report",
                        "kind": "validation_report",
                        "status": "review",
                        "operation": "run",
                        "revision": 1,
                        "sha256": "b" * 64,
                        "blockers": [],
                    },
                ]
            )
            validation = next(
                item
                for item in state["route"]["nodes"]
                if item["id"] == "nam-book-validate"
            )
            validation["status"] = "complete"
            validation["blockers"] = []
            with self.assertRaises(StateError):
                decide_approval(
                    state,
                    approval_id="medical-expert-signoff",
                    decision="approved",
                    decided_by="Dr. Ayu Pradnyani",
                    basis_ids=["evidence-ledger", "validation-report"],
                    note="Reviewed",
                )
            approval = decide_approval(
                state,
                approval_id="medical-expert-signoff",
                decision="approved",
                decided_by="Dr. Ayu Pradnyani",
                reviewer_role="Consultant physician",
                reviewer_credentials="MD, Internal Medicine",
                basis_ids=["evidence-ledger", "validation-report"],
                note="Evidence and clinical meaning reviewed",
            )
            self.assertEqual(approval["reviewer_role"], "Consultant physician")
            self.assertEqual(approval["basis"][0]["revision"], 1)
            registered = register_artifact(
                state,
                state_path,
                artifact_id="research-brief",
                kind="research_brief",
                relative_path=".nam-book/artifacts/research/research-brief.json",
                produced_by="nam-book-research",
                status="approved",
                locale="id-ID",
                chapter_id=None,
                input_ids=[],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            self.assertEqual(registered["status"], "approved")

    def test_registered_hash_change_expires_approval_and_invalidates_descendants(self):
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary)
            state, state_path = self.create(project_dir)
            decide_approval(
                state,
                approval_id="project-brief",
                decision="approved",
                decided_by="Nam",
                basis_ids=[],
                note="Scope confirmed",
            )
            transition_node(state, "nam-book-research", "running")
            artifact_path = project_dir / ".nam-book" / "artifacts" / "research" / "research-brief.json"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text(json.dumps({"version": 1}), encoding="utf-8")
            register_artifact(
                state,
                state_path,
                artifact_id="research-brief",
                kind="research_brief",
                relative_path=".nam-book/artifacts/research/research-brief.json",
                produced_by="nam-book-research",
                status="approved",
                locale="id-ID",
                chapter_id=None,
                input_ids=[],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            decide_approval(
                state,
                approval_id="architecture",
                decision="approved",
                decided_by="Nam",
                basis_ids=["research-brief"],
                note="Basis accepted for test",
            )
            invalidated = mark_artifact_stale(state, "research-brief", "Source changed")
            self.assertIn("nam-book-architect", invalidated)
            architecture_approval = next(
                item for item in state["approvals"] if item["approval_id"] == "architecture"
            )
            self.assertEqual(architecture_approval["status"], "expired")

    def test_stale_node_can_enter_rerun_and_register_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary)
            state, state_path = self.create(project_dir)
            decide_approval(
                state,
                approval_id="project-brief",
                decision="approved",
                decided_by="Nam",
                basis_ids=[],
                note="Scope confirmed",
            )
            transition_node(state, "nam-book-research", "running")
            artifacts = [
                (
                    "research-brief",
                    "research_brief",
                    ".nam-book/artifacts/research/research-brief.json",
                ),
                (
                    "evidence-ledger",
                    "evidence_ledger",
                    ".nam-book/artifacts/research/evidence-ledger.json",
                ),
            ]
            for artifact_id, kind, relative in artifacts:
                path = project_dir / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{"version": 1}', encoding="utf-8")
                register_artifact(
                    state,
                    state_path,
                    artifact_id=artifact_id,
                    kind=kind,
                    relative_path=relative,
                    produced_by="nam-book-research",
                    status="review",
                    locale="id-ID",
                    chapter_id=None,
                    input_ids=[],
                    claim_ids=[],
                    source_ids=[],
                    origin="project-generated",
                    creator="Nam Book Studio",
                    license_name="project-owned",
                    source_url="",
                    notice_path="",
                )
            transition_node(state, "nam-book-research", "complete")
            brief_path = project_dir / artifacts[0][2]
            brief_path.write_text('{"version": 2}', encoding="utf-8")
            self.assertEqual(refresh_file_staleness(state, state_path), ["research-brief"])
            transition_node(state, "nam-book-research", "running")
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])
            register_artifact(
                state,
                state_path,
                artifact_id="research-brief",
                kind="research_brief",
                relative_path=artifacts[0][2],
                produced_by="nam-book-research",
                status="review",
                locale="id-ID",
                chapter_id=None,
                input_ids=[],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            register_artifact(
                state,
                state_path,
                artifact_id="evidence-ledger",
                kind="evidence_ledger",
                relative_path=artifacts[1][2],
                produced_by="nam-book-research",
                status="review",
                locale="id-ID",
                chapter_id=None,
                input_ids=[],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            transition_node(state, "nam-book-research", "complete")
            record = state["staleness"][0]
            self.assertIn("nam-book-research", record["resolved_nodes"])
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])
            state["route"] = build_route(
                state, load_catalog(), load_profile(state["profile"]), "resume"
            )
            routed = {item["id"]: item for item in state["route"]["nodes"]}
            self.assertEqual(routed["nam-book-architect"]["blockers"], [])
            self.assertIn(
                "dependency:nam-book-architect",
                routed["nam-book-voice"]["blockers"],
            )
            actionable = format_route_receipt(state["route"]).splitlines()[-1]
            self.assertIn("nam-book-architect", actionable)
            self.assertNotIn("nam-book-voice", actionable)

    def test_upstream_revision_preserves_blocked_downstream_without_unlocking_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(
                Path(temporary), risk_level="R3", medical_enabled=True,
                jurisdiction="Test jurisdiction", evidence_cutoff=date.today().isoformat(),
                revalidate_before_export=date.today().isoformat(),
            )
            self.approve_brief(state)
            transition_node(state, "nam-book-research", "running")
            self.register_fixture(state, state_path, "research_brief", "research-brief", {"version": 1})
            self.register_fixture(state, state_path, "evidence_ledger", "evidence-ledger", {"version": 1})
            transition_node(state, "nam-book-research", "complete")
            transition_node(state, "nam-book-architect", "running")
            architecture = self.register_fixture(
                state, state_path, "book_architecture", "book-architecture", {"version": 1},
                input_ids=["research-brief", "evidence-ledger"], status="blocked",
                blockers=["missing-source:mechanism"],
            )
            original_architecture = copy.deepcopy(architecture)

            mark_artifact_stale(state, "research-brief", "Additional evidence inspected")
            mark_artifact_stale(state, "evidence-ledger", "Additional evidence inspected")
            transition_node(state, "nam-book-research", "running")
            updated_brief = self.register_fixture(
                state, state_path, "research_brief", "research-brief", {"version": 2},
            )
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])
            self.register_fixture(state, state_path, "evidence_ledger", "evidence-ledger", {"version": 2})
            transition_node(state, "nam-book-research", "complete")

            artifacts = {item["artifact_id"]: item for item in state["artifact_registry"]["entries"]}
            architecture = artifacts["book-architecture"]
            self.assertEqual(architecture, original_architecture)
            self.assertNotEqual(architecture["inputs"][0]["sha256"], updated_brief["sha256"])
            self.assertFalse(artifact_is_fresh(architecture, artifacts))
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])
            with self.assertRaisesRegex(StateError, "stale or blocked"):
                decide_approval(
                    state, approval_id="architecture", decision="approved",
                    decided_by="Reviewer", basis_ids=["book-architecture"], note="Attempt blocked basis",
                )
            with self.assertRaisesRegex(StateError, "lacks registered outputs"):
                transition_node(state, "nam-book-architect", "complete")
            with self.assertRaisesRegex(StateError, "blocked by"):
                transition_node(state, "nam-book-voice", "running")

            # Retained fingerprints are permitted only while the artifact is unusable.
            incorrectly_unblocked = copy.deepcopy(state)
            candidate = next(item for item in incorrectly_unblocked["artifact_registry"]["entries"]
                             if item["artifact_id"] == "book-architecture")
            candidate.update(status="review", blockers=[])
            errors, _ = validate_state(incorrectly_unblocked, state_path)
            self.assertTrue(any("stale because input research-brief changed" in error for error in errors))

    def test_registry_preserves_ids_blockers_provenance_and_revision_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary)
            state, state_path = self.create(project_dir)
            decide_approval(
                state,
                approval_id="project-brief",
                decision="approved",
                decided_by="Nam",
                basis_ids=[],
                note="Scope confirmed",
            )
            transition_node(state, "nam-book-research", "running")
            artifact_path = (
                project_dir
                / ".nam-book"
                / "artifacts"
                / "research"
                / "research-brief.json"
            )
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text('{"version": 1}', encoding="utf-8")
            with self.assertRaises(StateError):
                register_artifact(
                    state,
                    state_path,
                    artifact_id="research-brief",
                    kind="research_brief",
                    relative_path=".nam-book/artifacts/research/research-brief.json",
                    produced_by="nam-book-research",
                    status="approved",
                    locale="id-ID",
                    chapter_id=None,
                    input_ids=[],
                    claim_ids=[],
                    source_ids=[],
                    blockers=["missing-source"],
                    origin="project-generated",
                    creator="Nam Book Studio",
                    license_name="project-owned",
                    source_url="",
                    notice_path="",
                )
            first = register_artifact(
                state,
                state_path,
                artifact_id="research-brief",
                kind="research_brief",
                relative_path=".nam-book/artifacts/research/research-brief.json",
                produced_by="nam-book-research",
                status="blocked",
                locale="id-ID",
                chapter_id=None,
                input_ids=[],
                claim_ids=["claim-001"],
                source_ids=["source-001"],
                objective_ids=["objective-001"],
                figure_ids=["figure-001"],
                item_ids=["item-001"],
                semantic_block_ids=["block-001"],
                blockers=["needs-domain-review"],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            self.assertEqual(first["objective_ids"], ["objective-001"])
            self.assertEqual(first["figure_ids"], ["figure-001"])
            self.assertEqual(first["item_ids"], ["item-001"])
            self.assertEqual(first["semantic_block_ids"], ["block-001"])
            self.assertEqual(first["blockers"], ["needs-domain-review"])
            self.assertEqual(first["provenance"]["license"], "project-owned")
            first["status"] = "approved"
            errors, _ = validate_state(state, state_path)
            self.assertTrue(
                any("open blockers but is not blocked" in error for error in errors)
            )
            first["status"] = "blocked"
            first_snapshot = project_dir / first["revision_history"][0]["snapshot_path"]
            self.assertEqual(first_snapshot.read_text(encoding="utf-8"), '{"version": 1}')

            artifact_path.write_text('{"version": 2}', encoding="utf-8")
            second = register_artifact(
                state,
                state_path,
                artifact_id="research-brief",
                kind="research_brief",
                relative_path=".nam-book/artifacts/research/research-brief.json",
                produced_by="nam-book-research",
                status="review",
                locale="id-ID",
                chapter_id=None,
                input_ids=[],
                claim_ids=["claim-001"],
                source_ids=["source-001"],
                objective_ids=["objective-001"],
                figure_ids=["figure-001"],
                item_ids=["item-001"],
                semantic_block_ids=["block-001"],
                blockers=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            self.assertEqual(second["revision"], 2)
            self.assertEqual(len(second["revision_history"]), 2)
            self.assertEqual(first_snapshot.read_text(encoding="utf-8"), '{"version": 1}')
            second_snapshot = project_dir / second["revision_history"][1]["snapshot_path"]
            self.assertEqual(second_snapshot.read_text(encoding="utf-8"), '{"version": 2}')

    def test_public_schema_uri_and_two_phase_release_route(self):
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary)
            state, state_path = self.create(project_dir, illustrations="no", diagrams="no")
            self.assertEqual(state["$schema"], PROJECT_SCHEMA_URI)
            self.approve_brief(state)
            self.design_fixture(state, state_path)
            decide_approval(state, approval_id="design", decision="approved", decided_by="Nam",
                            basis_ids=["design-spec", "design-assets"], note="Sample approved",
                            state_path=state_path)
            state["route"] = build_route(
                state, load_catalog(), load_profile(state["profile"]), "publish"
            )
            ids = [item["id"] for item in state["route"]["nodes"]]
            self.assertEqual(
                ids,
                [
                    "nam-book-publish-proof",
                    "nam-book-validate",
                    "nam-book-publish-release",
                ],
            )
            proof, validation, release = state["route"]["nodes"]
            self.assertNotIn("final-proof", proof["required_approvals"])
            self.assertIn("nam-book-publish-proof", validation["depends_on"])
            self.assertIn("nam-book-validate", release["depends_on"])
            self.assertIn("final-proof", release["required_approvals"])
            with self.assertRaises(StateError):
                transition_node(state, release["id"], "running")

            transition_node(state, proof["id"], "running")
            proof_bundle = (
                project_dir / ".nam-book" / "artifacts" / "publication" / "proof-v1"
            )
            proof_bundle.parent.mkdir(parents=True)
            proof_bundle.write_text("proof bytes", encoding="utf-8")
            register_artifact(
                state,
                state_path,
                artifact_id="proof-v1",
                kind="publication_bundle",
                relative_path=".nam-book/artifacts/publication/proof-v1",
                produced_by="nam-book-publish",
                producer_node="nam-book-publish-proof",
                operation="proof",
                status="review",
                locale="id-ID",
                chapter_id=None,
                input_ids=[],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            proof_report = (
                project_dir
                / ".nam-book"
                / "artifacts"
                / "publication"
                / "reports"
                / "proof-report-v1.json"
            )
            proof_report.parent.mkdir(parents=True)
            proof_report.write_text("{}", encoding="utf-8")
            register_artifact(
                state,
                state_path,
                artifact_id="proof-report-v1",
                kind="publish_report",
                relative_path=".nam-book/artifacts/publication/reports/proof-report-v1.json",
                produced_by="nam-book-publish",
                producer_node="nam-book-publish-proof",
                operation="proof",
                status="review",
                locale="id-ID",
                chapter_id=None,
                input_ids=["proof-v1"],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            transition_node(state, proof["id"], "complete")
            transition_node(state, validation["id"], "running")
            validation_path = (
                project_dir
                / ".nam-book"
                / "artifacts"
                / "validation"
                / "validation-report.json"
            )
            validation_path.parent.mkdir(parents=True)
            validation_path.write_text("{}", encoding="utf-8")
            register_artifact(
                state,
                state_path,
                artifact_id="validation-report",
                kind="validation_report",
                relative_path=".nam-book/artifacts/validation/validation-report.json",
                produced_by="nam-book-validate",
                status="review",
                locale="id-ID",
                chapter_id=None,
                input_ids=["proof-v1", "proof-report-v1"],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            transition_node(state, validation["id"], "complete")
            decide_approval(
                state,
                approval_id="final-proof",
                decision="approved",
                decided_by="Nam",
                basis_ids=["proof-v1"],
                note="Exact proof approved",
            )
            transition_node(state, release["id"], "running")
            release_bundle = (
                project_dir / ".nam-book" / "artifacts" / "publication" / "release-v1"
            )
            release_bundle.write_text("release bytes", encoding="utf-8")
            with self.assertRaises(StateError):
                register_artifact(
                    state,
                    state_path,
                    artifact_id="release-v1",
                    kind="publication_bundle",
                    relative_path=".nam-book/artifacts/publication/release-v1",
                    produced_by="nam-book-publish",
                    producer_node="nam-book-publish-release",
                    operation="release",
                    status="locked",
                    locale="id-ID",
                    chapter_id=None,
                    input_ids=[],
                    claim_ids=[],
                    source_ids=[],
                    origin="project-generated",
                    creator="Nam Book Studio",
                    license_name="project-owned",
                    source_url="",
                    notice_path="",
                )
            register_artifact(
                state,
                state_path,
                artifact_id="release-v1",
                kind="publication_bundle",
                relative_path=".nam-book/artifacts/publication/release-v1",
                produced_by="nam-book-publish",
                producer_node="nam-book-publish-release",
                operation="release",
                status="locked",
                locale="id-ID",
                chapter_id=None,
                input_ids=["proof-v1"],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            release_report = (
                project_dir
                / ".nam-book"
                / "artifacts"
                / "publication"
                / "reports"
                / "release-report-v1.json"
            )
            release_report.write_text("{}", encoding="utf-8")
            register_artifact(
                state,
                state_path,
                artifact_id="release-report-v1",
                kind="publish_report",
                relative_path=".nam-book/artifacts/publication/reports/release-report-v1.json",
                produced_by="nam-book-publish",
                producer_node="nam-book-publish-release",
                operation="release",
                status="locked",
                locale="id-ID",
                chapter_id=None,
                input_ids=["proof-v1", "release-v1"],
                claim_ids=[],
                source_ids=[],
                origin="project-generated",
                creator="Nam Book Studio",
                license_name="project-owned",
                source_url="",
                notice_path="",
            )
            transition_node(state, release["id"], "complete")
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])

    def test_audit_route_is_smaller_than_start_route(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, _ = self.create(Path(temporary))
            audit = build_route(
                state,
                load_catalog(),
                load_profile("friendly-explainer"),
                "audit",
            )
            self.assertEqual([item["skill"] for item in audit["nodes"]], ["nam-book-validate"])


    def advance_text_pipeline_to_localize(self, state, state_path, callout_ids):
        """Run the text-only lane up to a running localize node with a locked source."""
        self.approve_brief(state)
        transition_node(state, "nam-book-research", "running")
        self.register_fixture(state, state_path, "research_brief", "research-brief", {"version": 1})
        self.register_fixture(state, state_path, "evidence_ledger", "evidence-ledger", {"version": 1})
        transition_node(state, "nam-book-research", "complete")
        transition_node(state, "nam-book-architect", "running")
        self.register_fixture(state, state_path, "book_architecture", "book-architecture", {"version": 1},
                              input_ids=["research-brief", "evidence-ledger"])
        transition_node(state, "nam-book-architect", "complete")
        decide_approval(state, approval_id="architecture", decision="approved", decided_by="Reviewer",
                        basis_ids=["book-architecture"], note="Chapter graph accepted")
        transition_node(state, "nam-book-voice", "running")
        self.register_fixture(state, state_path, "voice_profile", "voice-profile", "voice: warm", raw_text=True)
        transition_node(state, "nam-book-voice", "complete")
        transition_node(state, "nam-book-write", "running")
        self.register_fixture(state, state_path, "chapter_draft", "chapter-ch01-draft", "# Draft",
                              chapter_id="ch-01", raw_text=True)
        transition_node(state, "nam-book-write", "complete")
        transition_node(state, "nam-book-teach", "running")
        self.register_fixture(state, state_path, "teaching_plan", "teaching-plan", "enhancements: []", raw_text=True)
        self.register_fixture(state, state_path, "enriched_draft", "chapter-ch01-enriched", "# Enriched",
                              chapter_id="ch-01", raw_text=True, input_ids=["chapter-ch01-draft"],
                              callout_ids=callout_ids)
        transition_node(state, "nam-book-teach", "complete")
        transition_node(state, "nam-book-edit", "running")
        self.register_fixture(state, state_path, "edited_manuscript", "edited-id", "# Edited", raw_text=True,
                              input_ids=["chapter-ch01-enriched"], callout_ids=callout_ids)
        self.register_fixture(state, state_path, "edit_report", "edit-report", "pass: integration", raw_text=True)
        transition_node(state, "nam-book-edit", "complete")
        decide_approval(state, approval_id="source-content-lock", decision="approved", decided_by="Reviewer",
                        basis_ids=["edited-id"], note="Source edition locked")
        transition_node(state, "nam-book-localize", "running")

    def test_registry_records_callout_ids_in_entry_history_and_cli(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            self.approve_brief(state)
            transition_node(state, "nam-book-research", "running")
            entry = self.register_fixture(
                state, state_path, "research_brief", "research-brief", {"version": 1},
                callout_ids=["callout-ch01-02", "callout-ch01-01", "callout-ch01-02"],
            )
            self.assertEqual(entry["callout_ids"], ["callout-ch01-02", "callout-ch01-01"])
            self.assertEqual(entry["revision_history"][-1]["callout_ids"], ["callout-ch01-02", "callout-ch01-01"])
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])
            atomic_write_json(state_path, state)

            ledger_path = ".nam-book/artifacts/research/evidence-ledger.json"
            (state_path.parent.parent / ledger_path).write_text("{}", encoding="utf-8")
            scripts = Path(__file__).resolve().parent
            result = subprocess.run(
                [sys.executable, str(scripts / "update_state.py"), "--state", str(state_path),
                 "register-artifact", "--id", "evidence-ledger", "--kind", "evidence_ledger",
                 "--path", ledger_path, "--produced-by", "nam-book-research", "--status", "review",
                 "--locale", "id-ID", "--callout-id", "callout-ch01-03", "--callout-id", "callout-ch01-04"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            ledger = next(item for item in saved["artifact_registry"]["entries"]
                          if item["artifact_id"] == "evidence-ledger")
            self.assertEqual(ledger["callout_ids"], ["callout-ch01-03", "callout-ch01-04"])

    def test_validate_state_rejects_malformed_callout_ids_but_tolerates_legacy_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            self.approve_brief(state)
            transition_node(state, "nam-book-research", "running")
            self.register_fixture(state, state_path, "research_brief", "research-brief", {"version": 1},
                                  callout_ids=["callout-ch01-01"])
            malformed = copy.deepcopy(state)
            target = next(item for item in malformed["artifact_registry"]["entries"]
                          if item["artifact_id"] == "research-brief")
            target["callout_ids"] = ["callout-ch01-01", "", "callout-ch01-01"]
            errors, _ = validate_state(malformed, state_path)
            self.assertTrue(any("invalid callout_ids" in error for error in errors), errors)

            legacy = copy.deepcopy(state)
            target = next(item for item in legacy["artifact_registry"]["entries"]
                          if item["artifact_id"] == "research-brief")
            del target["callout_ids"]
            errors, _ = validate_state(legacy, state_path)
            self.assertEqual(errors, [])

    def test_localized_manuscript_missing_source_callouts_is_a_parity_warning(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(
                Path(temporary), target_locales=["en-US"], assessments="no",
                illustrations="no", diagrams="no",
            )
            self.advance_text_pipeline_to_localize(
                state, state_path, ["callout-ch01-01", "callout-ch01-02"],
            )
            self.register_fixture(
                state, state_path, "localized_manuscript", "localized-en", "# Localized",
                raw_text=True, locale="en-US", input_ids=["edited-id"],
                callout_ids=["callout-ch01-01"],
            )
            errors, warnings = validate_state(state, state_path)
            self.assertEqual(errors, [])
            parity = [item for item in warnings if "callout" in item.lower()]
            self.assertEqual(len(parity), 1, warnings)
            self.assertIn("callout-ch01-02", parity[0])
            self.assertIn("localized-en", parity[0])

            self.register_fixture(
                state, state_path, "localized_manuscript", "localized-en", "# Localized v2",
                raw_text=True, locale="en-US", input_ids=["edited-id"],
                callout_ids=["callout-ch01-02", "callout-ch01-01"],
            )
            errors, warnings = validate_state(state, state_path)
            self.assertEqual(errors, [])
            self.assertEqual([item for item in warnings if "callout" in item.lower()], [])


    def design_fixture(self, state, state_path, *, spec_inputs=None, report=None, proof_id="design-proof-1"):
        """Complete the design stage and render one proof bundle for it."""
        transition_node(state, "nam-book-design", "running")
        self.register_fixture(state, state_path, "design_spec", "design-spec", {
            "profile": state["profile"], "design_version": "1.0.0",
            "render": {"pdf": {"engine": "chromium"}},
        }, input_ids=spec_inputs or [])
        self.register_fixture(state, state_path, "design_assets", "design-assets", {
            "__bundle__": True, "print.css": "aside.callout { border: 1px solid; }",
            "callouts.lua": "return {}",
        }, input_ids=["design-spec"])
        transition_node(state, "nam-book-design", "complete")
        transition_node(state, "nam-book-design-proof", "running")
        self.register_fixture(state, state_path, "design_proof", proof_id, {
            "__bundle__": True,
            "report.json": report or {"status": "pass", "formats": ["pdf"]},
            "sample-chapter.pdf": "%PDF-1.7 fixture",
        }, input_ids=["design-spec", "design-assets"], operation="proof")
        transition_node(state, "nam-book-design-proof", "complete")

    def test_two_output_node_can_reregister_both_outputs_without_explicit_mark_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            self.approve_brief(state)
            transition_node(state, "nam-book-research", "running")
            self.register_fixture(state, state_path, "research_brief", "research-brief", {"version": 1})
            self.register_fixture(state, state_path, "evidence_ledger", "evidence-ledger", {"version": 1})
            transition_node(state, "nam-book-research", "complete")
            transition_node(state, "nam-book-research", "running")
            self.register_fixture(state, state_path, "research_brief", "research-brief", {"version": 2})
            self.register_fixture(state, state_path, "evidence_ledger", "evidence-ledger", {"version": 2})
            transition_node(state, "nam-book-research", "complete")
            self.assertTrue(state["staleness"])
            self.assertTrue(all("nam-book-research" in record["resolved_nodes"] for record in state["staleness"]))
            self.assertEqual(validate_state(state, state_path)[0], [])

    def test_design_stage_is_routed_after_setup_and_gates_publish_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            nodes = {item["id"]: item for item in state["route"]["nodes"]}
            self.assertEqual(nodes["nam-book-design"]["depends_on"], ["nam-book-illustration-setup"])
            self.assertEqual(nodes["nam-book-design"]["required_approvals"], ["project-brief"])
            self.assertEqual(nodes["nam-book-design-proof"]["depends_on"], ["nam-book-design"])
            self.assertEqual(nodes["nam-book-design-proof"]["required_approvals"], [])
            self.assertEqual(nodes["nam-book-design-proof"]["operation"], "proof")
            self.assertIn("nam-book-design", nodes["nam-book-publish-proof"]["depends_on"])
            self.assertIn("design", nodes["nam-book-publish-proof"]["required_approvals"])
            self.assertIn("design", {item["approval_id"] for item in state["approvals"]})
            slots = state["artifact_registry"]["slots"]
            self.assertEqual(slots["design_spec"]["produced_by"], "nam-book-design")
            self.assertEqual(slots["design_assets"]["path"], ".nam-book/artifacts/design/assets")
            self.assertEqual(slots["design_proof"]["path"], ".nam-book/artifacts/design/proofs/{artifact_id}")
            self.assertIn("proof", slots["design_proof"]["operations"])
            self.assertEqual(validate_state(state, state_path)[0], [])

            text_only, text_path = self.create(Path(temporary) / "text", illustrations="no", diagrams="no")
            nodes = {item["id"]: item for item in text_only["route"]["nodes"]}
            self.assertEqual(nodes["nam-book-design"]["depends_on"], [])
            self.assertNotIn("nam-book-illustration-setup", nodes)

            focused = build_route(text_only, load_catalog(), load_profile(text_only["profile"]), "design")
            self.assertEqual([item["id"] for item in focused["nodes"]], ["nam-book-design", "nam-book-design-proof"])
            visual_focus = build_route(state, load_catalog(), load_profile(state["profile"]), "design")
            self.assertEqual(
                [item["id"] for item in visual_focus["nodes"]],
                ["nam-book-illustration-setup", "nam-book-design", "nam-book-design-proof"],
            )

    def test_legacy_manifest_without_design_record_publishes_ungated(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            legacy = copy.deepcopy(state)
            legacy["approvals"] = [item for item in legacy["approvals"] if item["approval_id"] != "design"]
            legacy["route"] = build_route(legacy, load_catalog(), load_profile(legacy["profile"]), "publish")
            proof = next(item for item in legacy["route"]["nodes"] if item["id"] == "nam-book-publish-proof")
            self.assertNotIn("design", proof["required_approvals"])
            self.assertNotIn("nam-book-design", proof["depends_on"])
            self.assertEqual(validate_state(legacy, state_path)[0], [])
            resumed = build_route(legacy, load_catalog(), load_profile(legacy["profile"]), "resume")
            self.assertIn("design", {item["approval_id"] for item in legacy["approvals"]})
            proof = next(item for item in resumed["nodes"] if item["id"] == "nam-book-publish-proof")
            self.assertIn("design", proof["required_approvals"])

    def test_design_approval_requires_fresh_passing_proof_of_the_bound_spec(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary), illustrations="no", diagrams="no")
            self.approve_brief(state)
            transition_node(state, "nam-book-design", "running")
            self.register_fixture(state, state_path, "design_spec", "design-spec", {
                "profile": state["profile"], "design_version": "1.0.0",
            })
            self.register_fixture(state, state_path, "design_assets", "design-assets", {
                "__bundle__": True, "print.css": "aside.callout {}",
            }, input_ids=["design-spec"])
            transition_node(state, "nam-book-design", "complete")
            with self.assertRaisesRegex(StateError, "design proof"):
                decide_approval(state, approval_id="design", decision="approved", decided_by="Author",
                                basis_ids=["design-spec", "design-assets"], note="", state_path=state_path)
            with self.assertRaisesRegex(StateError, "design_spec and design_assets"):
                decide_approval(state, approval_id="design", decision="approved", decided_by="Author",
                                basis_ids=["design-spec"], note="", state_path=state_path)

            transition_node(state, "nam-book-design-proof", "running")
            self.register_fixture(state, state_path, "design_proof", "design-proof-1", {
                "__bundle__": True, "report.json": {"status": "fail", "formats": ["pdf"]},
            }, input_ids=["design-spec", "design-assets"], operation="proof")
            transition_node(state, "nam-book-design-proof", "complete")
            with self.assertRaisesRegex(StateError, "report"):
                decide_approval(state, approval_id="design", decision="approved", decided_by="Author",
                                basis_ids=["design-spec", "design-assets"], note="", state_path=state_path)

            transition_node(state, "nam-book-design-proof", "running")
            self.register_fixture(state, state_path, "design_proof", "design-proof-2", {
                "__bundle__": True, "report.json": {"status": "pass", "formats": ["docx"]},
            }, input_ids=["design-spec", "design-assets"], operation="proof")
            transition_node(state, "nam-book-design-proof", "complete")
            with self.assertRaisesRegex(StateError, "pdf"):
                decide_approval(state, approval_id="design", decision="approved", decided_by="Author",
                                basis_ids=["design-spec", "design-assets"], note="", state_path=state_path)

            transition_node(state, "nam-book-design-proof", "running")
            self.register_fixture(state, state_path, "design_proof", "design-proof-3", {
                "__bundle__": True, "report.json": {"status": "pass", "formats": ["pdf", "docx"]},
            }, input_ids=["design-spec", "design-assets"], operation="proof")
            transition_node(state, "nam-book-design-proof", "complete")
            approval = decide_approval(state, approval_id="design", decision="approved", decided_by="Author",
                                       basis_ids=["design-spec", "design-assets"], note="Sample chapter looks right",
                                       state_path=state_path)
            self.assertEqual({item["artifact_id"] for item in approval["basis"]}, {"design-spec", "design-assets"})
            errors, _ = validate_state(state, state_path)
            self.assertEqual(errors, [])
            publish = next(item for item in state["route"]["nodes"] if item["id"] == "nam-book-publish-proof")
            self.assertNotIn("approval:design", publish["blockers"])

            # A changed spec expires the decision and stales the proof.
            transition_node(state, "nam-book-design", "running")
            self.register_fixture(state, state_path, "design_spec", "design-spec", {
                "profile": state["profile"], "design_version": "1.1.0",
            })
            approval = next(item for item in state["approvals"] if item["approval_id"] == "design")
            self.assertEqual(approval["status"], "expired")
            proof_entry = next(item for item in state["artifact_registry"]["entries"]
                               if item["artifact_id"] == "design-proof-3")
            self.assertEqual(proof_entry["status"], "stale")
            self.assertEqual(validate_state(state, state_path)[0], [])

    def test_design_spec_profile_must_match_the_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary), illustrations="no", diagrams="no")
            self.approve_brief(state)
            transition_node(state, "nam-book-design", "running")
            self.register_fixture(state, state_path, "design_spec", "design-spec", {
                "profile": "textbook", "design_version": "1.0.0",
            })
            self.register_fixture(state, state_path, "design_assets", "design-assets", {
                "__bundle__": True, "print.css": "aside.callout {}",
            }, input_ids=["design-spec"])
            transition_node(state, "nam-book-design", "complete")
            transition_node(state, "nam-book-design-proof", "running")
            self.register_fixture(state, state_path, "design_proof", "design-proof-1", {
                "__bundle__": True, "report.json": {"status": "pass", "formats": ["pdf"]},
            }, input_ids=["design-spec", "design-assets"], operation="proof")
            transition_node(state, "nam-book-design-proof", "complete")
            with self.assertRaisesRegex(StateError, "profile"):
                decide_approval(state, approval_id="design", decision="approved", decided_by="Author",
                                basis_ids=["design-spec", "design-assets"], note="", state_path=state_path)

    def test_changed_illustration_setup_expires_design_but_design_change_keeps_setup(self):
        with tempfile.TemporaryDirectory() as temporary:
            state, state_path = self.create(Path(temporary))
            self.approve_brief(state)
            self.setup_fixture(state, state_path)
            transition_node(state, "nam-book-illustration-setup", "complete")
            decide_approval(state, approval_id="illustration-setup", decision="approved", decided_by="Author",
                            basis_ids=["illustration-setup", "character-bible"], note="", state_path=state_path)
            self.design_fixture(state, state_path, spec_inputs=["illustration-setup"])
            decide_approval(state, approval_id="design", decision="approved", decided_by="Author",
                            basis_ids=["design-spec", "design-assets"], note="", state_path=state_path)
            approvals = {item["approval_id"]: item for item in state["approvals"]}
            self.assertEqual(approvals["design"]["status"], "approved")

            # Design revision: illustration approval survives.
            transition_node(state, "nam-book-design", "running")
            self.register_fixture(state, state_path, "design_spec", "design-spec", {
                "profile": state["profile"], "design_version": "1.1.0", "render": {"pdf": {"engine": "chromium"}},
            }, input_ids=["illustration-setup"])
            approvals = {item["approval_id"]: item for item in state["approvals"]}
            self.assertEqual(approvals["design"]["status"], "expired")
            self.assertEqual(approvals["illustration-setup"]["status"], "approved")
            self.assertEqual(validate_state(state, state_path)[0], [])

            # Setup revision: design approval and proof become stale too.
            self.register_fixture(state, state_path, "design_assets", "design-assets", {
                "__bundle__": True, "print.css": "aside.callout { color: teal; }",
            }, input_ids=["design-spec"])
            transition_node(state, "nam-book-design", "complete")
            transition_node(state, "nam-book-design-proof", "running")
            self.register_fixture(state, state_path, "design_proof", "design-proof-1", {
                "__bundle__": True, "report.json": {"status": "pass", "formats": ["pdf"], "revision": 2},
            }, input_ids=["design-spec", "design-assets"], operation="proof")
            transition_node(state, "nam-book-design-proof", "complete")
            decide_approval(state, approval_id="design", decision="approved", decided_by="Author",
                            basis_ids=["design-spec", "design-assets"], note="", state_path=state_path)
            transition_node(state, "nam-book-illustration-setup", "running")
            self.register_fixture(state, state_path, "illustration_setup", "illustration-setup", {
                "mascot_mode": "custom", "hand_drawn": True, "adoption": None, "palette": ["teal"],
                "calibration": {"status": "passed", "sample_artifact_ids": ["calibration-1"]},
            }, ["calibration-1"])
            approvals = {item["approval_id"]: item for item in state["approvals"]}
            self.assertEqual(approvals["design"]["status"], "expired")
            nodes = {item["id"]: item for item in state["route"]["nodes"]}
            self.assertEqual(nodes["nam-book-design"]["status"], "stale")
            self.assertEqual(nodes["nam-book-publish-proof"]["status"], "stale")
            self.assertEqual(validate_state(state, state_path)[0], [])


if __name__ == "__main__":
    unittest.main()
