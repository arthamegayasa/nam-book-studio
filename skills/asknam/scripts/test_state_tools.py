from __future__ import annotations

import json
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
    atomic_write_json,
    build_route,
    create_manifest,
    decide_approval,
    format_route_receipt,
    load_catalog,
    load_profile,
    mark_artifact_stale,
    refresh_file_staleness,
    register_artifact,
    transition_node,
    validate_state,
)
from validate_resources import validate as validate_resources


class StateToolsTests(unittest.TestCase):
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
            state, state_path = self.create(project_dir)
            self.assertEqual(state["$schema"], PROJECT_SCHEMA_URI)
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


if __name__ == "__main__":
    unittest.main()
