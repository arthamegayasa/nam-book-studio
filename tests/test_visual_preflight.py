from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "visual_preflight", ROOT / "skills/nam-book-validate/scripts/preflight_project.py"
)
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)
SETUP_NODE = "nam-book-illustration-setup"


class VisualPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.entries: dict[str, dict] = {}
        self.paths: dict[str, Path] = {}
        self.manifest = {
            "schema_version": "1.0.0",
            "project_id": "visual-preflight",
            "profile": "friendly-explainer",
            "source_locale": "en-US",
            "target_locales": [],
            "risk_level": "R1",
            "medical": {"enabled": False},
            "features": {"illustrations": True, "diagrams": False},
            "deliverables": ["pdf"],
            "artifact_registry": {"root": ".nam-book/artifacts", "slots": [], "entries": []},
            "route": {"route_version": "1.0.0", "nodes": [], "edges": [], "parked_nodes": []},
            "approvals": [],
            "staleness": [],
        }
        self.manifest["route"]["nodes"] = [
            self.node(SETUP_NODE), self.node("nam-book-publish-proof", "nam-book-publish", "proof")
        ]
        # These fixtures exercise structural checks, not art quality or rendering.
        self.add_artifact("sample", "illustration_calibration", "<svg xmlns='http://www.w3.org/2000/svg'/>")
        self.payload = {
            "mascot_mode": "custom",
            "hand_drawn": True,
            "calibration": {"status": "passed", "sample_artifact_ids": ["sample"]},
        }
        self.add_artifact("setup", "illustration_setup", json.dumps(self.payload), ["sample"])
        self.add_artifact("bible", "character_bible", json.dumps({"mascot_mode": "custom", "identity": {"name": "Tara", "fixed_anchors": ["rounded shell"]}}), ["sample"])
        self.add_artifact("proof", "publication_bundle", "proof fixture", producer="nam-book-publish-proof")
        self.manifest["approvals"] = [
            self.approval("illustration-setup", ["setup", "bible"]),
            self.approval("final-proof", ["proof"]),
        ]

    @staticmethod
    def node(node_id: str, skill: str | None = None, operation: str = "default") -> dict:
        return {"id": node_id, "skill": skill or node_id, "operation": operation, "depends_on": [], "status": "complete", "blockers": []}

    def basis(self, artifact_id: str) -> dict:
        entry = self.entries[artifact_id]
        return {key: entry[key] for key in ("artifact_id", "revision", "sha256")}

    def approval(self, kind: str, ids: list[str]) -> dict:
        return {
            "approval_id": f"approve-{kind}", "kind": kind, "status": "approved",
            "requested_at": "2026-09-04T00:00:00Z", "decided_at": "2026-09-04T00:01:00Z",
            "decided_by": "Project owner", "basis": [self.basis(item) for item in ids],
        }

    def add_artifact(self, artifact_id: str, kind: str, content: str, inputs: list[str] | None = None, producer: str = SETUP_NODE) -> None:
        is_bundle = kind == "illustration_calibration"
        path = self.root / ".nam-book/artifacts" / (f"visuals/calibration/{artifact_id}" if is_bundle else f"{artifact_id}.json")
        if is_bundle:
            path.mkdir(parents=True, exist_ok=True)
            (path / "sample.svg").write_text(content, encoding="utf-8")
            (path / "sample-metadata.json").write_text(json.dumps({"purpose": "Structural test only"}), encoding="utf-8")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        digest, hash_kind = PREFLIGHT.sha256_path(path)
        snapshot = self.root / ".nam-book/history" / artifact_id / ("r0001" if is_bundle else "r0001.json")
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if is_bundle:
            shutil.copytree(path, snapshot)
        else:
            snapshot.write_bytes(path.read_bytes())
        entry = {
            "schema_version": "1.0.0", "artifact_id": artifact_id, "kind": kind,
            "path": path.relative_to(self.root).as_posix(), "project_id": "visual-preflight", "locale": "en-US",
            "produced_by": "nam-book-publish" if producer == "nam-book-publish-proof" else producer,
            "producer_node": producer, "operation": "proof" if producer == "nam-book-publish-proof" else "default",
            "status": "review", "revision": 1, "sha256": digest, "hash_kind": hash_kind,
            "inputs": [self.basis(item) for item in (inputs or [])], "blockers": [], "provenance": {},
            "revision_history": [{"revision": 1, "sha256": digest, "hash_kind": hash_kind, "snapshot_path": snapshot.relative_to(self.root).as_posix()}],
        }
        self.entries[artifact_id] = entry
        self.paths[artifact_id] = path
        self.manifest["artifact_registry"]["entries"] = list(self.entries.values())

    def audit(self, *, full: bool = False, phase: str = "release"):
        audit = PREFLIGHT.Audit()
        if full:
            self.assertTrue(PREFLIGHT.check_manifest_shape(self.manifest, audit))
            entries, paths, _ = PREFLIGHT.check_registry(self.manifest, self.root, phase, audit)
            PREFLIGHT.check_staleness(self.manifest, entries, phase, audit)
            PREFLIGHT.check_route(self.manifest, audit)
        else:
            entries, paths = self.entries, self.paths
        PREFLIGHT.check_approvals(self.manifest, entries, phase, audit, paths)
        return audit

    def codes(self, **kwargs) -> set[str]:
        return {item["code"] for item in self.audit(**kwargs).errors}

    def set_payload(self, **updates) -> None:
        self.payload.update(updates)
        self.add_artifact("setup", "illustration_setup", json.dumps(self.payload), ["sample"])
        self.manifest["approvals"][0] = self.approval("illustration-setup", ["setup", "bible"])

    def test_complete_setup_supports_each_project_mascot_mode(self) -> None:
        for mode in ("custom", "supplied", "nam", "none"):
            with self.subTest(mode=mode):
                self.add_artifact("bible", "character_bible", json.dumps({"mascot_mode": mode, "identity": None if mode == "none" else {"name": "Test identity"}}), ["sample"])
                self.set_payload(mascot_mode=mode)
                self.assertEqual(set(), self.codes(full=True))

    def test_mascot_mode_mismatch_or_identity_in_none_mode_fails(self) -> None:
        self.set_payload(mascot_mode="none")
        self.assertIn("illustration_setup_mascot_mismatch", self.codes())
        self.add_artifact("bible", "character_bible", json.dumps({"mascot_mode": "none", "identity": {"name": "Unexpected mascot"}}), ["sample"])
        self.set_payload(mascot_mode="none")
        self.assertIn("illustration_setup_none_identity", self.codes())
        self.add_artifact("bible", "character_bible", json.dumps({"mascot_mode": "custom", "identity": None}), ["sample"])
        self.set_payload(mascot_mode="custom")
        self.assertIn("illustration_setup_identity_missing", self.codes())

    def test_legacy_bible_bytes_need_explicit_hash_bound_adoption(self) -> None:
        self.add_artifact("bible", "character_bible", "# Approved Nam legacy bible\n", ["sample"])
        self.set_payload(mascot_mode="nam")
        self.assertIn("illustration_setup_legacy_adoption_missing", self.codes())
        self.set_payload(adoption={"character_bible_artifact_id": "bible", "sha256": self.entries["bible"]["sha256"], "approval_ids": ["old-character-bible"], "reason": "Preserve approved Nam identity."})
        self.assertIn("illustration_setup_legacy_adoption_missing", self.codes())
        self.manifest["provenance"] = [{
            "item_id": "illustration-setup-adoption-bible",
            "notes": json.dumps({**self.basis("bible"), "new_owner": SETUP_NODE}),
        }]
        self.assertEqual(set(), self.codes(full=True))

    def test_legacy_identity_cannot_be_adopted_as_a_mascot_free_bible(self) -> None:
        self.add_artifact("bible", "character_bible", "# Approved Nam legacy bible\n", ["sample"])
        self.set_payload(mascot_mode="none", adoption={
            "character_bible_artifact_id": "bible", "sha256": self.entries["bible"]["sha256"],
            "approval_ids": ["old-character-bible"], "reason": "Attempted mascot-free reuse.",
        })
        self.manifest["provenance"] = [{
            "item_id": "illustration-setup-adoption-bible",
            "notes": json.dumps({**self.basis("bible"), "new_owner": SETUP_NODE}),
        }]
        self.assertIn("illustration_setup_none_legacy_bible", self.codes())
        self.assertIn("illustration_setup_approval_missing", self.codes())

    def test_missing_setup_and_legacy_bible_approval_do_not_unlock_release(self) -> None:
        self.manifest["approvals"][0] = self.approval("character-bible", ["bible"])
        self.assertIn("illustration_setup_approval_missing", self.codes())

    def test_basis_requires_both_setup_and_bible_not_an_unrelated_artifact(self) -> None:
        for ids in (["setup"], ["bible"], ["proof"]):
            with self.subTest(ids=ids):
                self.manifest["approvals"][0] = self.approval("illustration-setup", ids)
                codes = self.codes()
                self.assertIn("illustration_setup_basis_incomplete", codes)
                self.assertIn("illustration_setup_approval_missing", codes)

    def test_stale_hash_or_revision_invalidates_setup_approval(self) -> None:
        for field, value, expected in (("sha256", "0" * 64, "approval_hash_stale"), ("revision", 99, "approval_revision_stale")):
            with self.subTest(field=field):
                approval = self.approval("illustration-setup", ["setup", "bible"])
                approval["basis"][0][field] = value
                self.manifest["approvals"][0] = approval
                self.assertIn(expected, self.codes())
                self.assertIn("illustration_setup_approval_missing", self.codes())

    def test_stale_or_blocked_input_closure_invalidates_setup(self) -> None:
        for status in ("stale", "blocked"):
            with self.subTest(status=status):
                self.entries["sample"]["status"] = status
                self.assertIn("illustration_setup_input_not_fresh", self.codes())
        self.entries["sample"]["status"] = "review"
        self.entries["setup"]["inputs"][0]["sha256"] = "0" * 64
        self.assertIn("illustration_setup_input_stale", self.codes())

    def test_resolved_setup_source_is_fresh_while_downstream_work_remains(self) -> None:
        self.manifest["staleness"] = [{
            "stale_id": "stale-sample", "artifact_id": "sample",
            "reason": "Calibration sample changed", "detected_at": "2026-09-04T00:00:00Z",
            "invalidates_nodes": [SETUP_NODE, "nam-book-diagram", "nam-book-edit"],
            "resolved_nodes": [], "resolved_at": None,
        }]
        self.assertIn("illustration_setup_input_not_fresh", self.codes())
        self.manifest["staleness"][0]["resolved_nodes"] = [SETUP_NODE]
        self.assertEqual(set(), self.codes())
        # A stale current entry cannot be rescued by the resolution record alone.
        self.entries["sample"]["status"] = "stale"
        self.assertIn("illustration_setup_input_not_fresh", self.codes())

    def test_changed_sample_bytes_fail_complete_preflight(self) -> None:
        (self.paths["sample"] / "sample.svg").write_text("changed sample", encoding="utf-8")
        self.assertIn("artifact_hash_mismatch", self.codes(full=True))

    def test_incomplete_stage_and_unmigrated_legacy_producer_fail(self) -> None:
        self.manifest["route"]["nodes"][0]["status"] = "review"
        self.assertIn("illustration_setup_stage_incomplete", self.codes())
        self.manifest["route"]["nodes"][0]["status"] = "complete"
        self.entries["bible"]["producer_node"] = "nam-book-visuals"
        self.assertIn("illustration_setup_producer_mismatch", self.codes())

    def test_completed_parked_setup_is_valid_for_focused_routes(self) -> None:
        setup = self.manifest["route"]["nodes"].pop(0)
        self.manifest["route"]["parked_nodes"].append(setup)
        self.assertEqual(set(), self.codes(full=True))

    def test_calibration_must_be_passed_registered_and_hash_bound(self) -> None:
        for calibration, expected in (
            ({"status": "provisional", "sample_artifact_ids": ["sample"]}, "illustration_setup_calibration_incomplete"),
            ({"status": "passed", "sample_artifact_ids": []}, "illustration_setup_calibration_incomplete"),
            ({"status": "passed", "sample_artifact_ids": ["missing"]}, "illustration_setup_calibration_basis"),
            ({"status": "passed", "sample_artifact_ids": ["proof"]}, "illustration_setup_calibration_basis"),
        ):
            with self.subTest(calibration=calibration):
                self.set_payload(calibration=calibration)
                self.assertIn(expected, self.codes())
        self.set_payload(calibration={"status": "passed", "sample_artifact_ids": ["sample"]})
        self.entries["setup"]["inputs"] = []
        self.assertIn("illustration_setup_calibration_basis", self.codes())

    def test_expired_historical_basis_does_not_block_current_approval(self) -> None:
        old = copy.deepcopy(self.manifest["approvals"][0])
        old.update(approval_id="old-setup", status="expired")
        old["basis"][0]["sha256"] = "0" * 64
        self.manifest["approvals"].append(old)
        audit = self.audit(full=True)
        self.assertEqual([], audit.errors)
        self.assertIn("approval_hash_stale", {item["code"] for item in audit.notes})

    def test_diagram_only_still_requires_setup_but_no_visual_book_does_not(self) -> None:
        self.manifest["features"] = {"illustrations": False, "diagrams": True}
        self.assertEqual(set(), self.codes(full=True))
        self.manifest["approvals"].pop(0)
        self.assertIn("illustration_setup_approval_missing", self.codes())
        self.manifest["features"]["diagrams"] = False
        self.assertEqual(set(), self.codes())
        self.manifest["approvals"] = []
        self.assertIn("final_proof_missing", self.codes())

    def test_nonvisual_r3_still_requires_expert_signoff(self) -> None:
        self.manifest["features"] = {"illustrations": False, "diagrams": False}
        self.manifest["approvals"] = [self.approval("final-proof", ["proof"])]
        self.manifest["risk_level"] = "R3"
        self.assertIn("expert_signoff_missing", self.codes())


if __name__ == "__main__":
    unittest.main()
