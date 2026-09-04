#!/usr/bin/env python3
"""Run conservative structural preflight checks for a Nam Book project.

This standard-library tool checks paths, files, hashes, dependency records,
approval bases, route references, and ledger state transitions. It does not
implement full JSON Schema validation, fetch sources, judge whether prose is
true, render deliverables, assess accessibility, or grant human approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


HASH_RE = re.compile(r"^[a-f0-9]{64}$")
PROJECT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ARTIFACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SKILL_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LOCALES = {"en-US", "id-ID"}
RISK_LEVELS = {"R0", "R1", "R2", "R3"}
ARTIFACT_STATUSES = {"draft", "review", "approved", "locked", "stale", "blocked"}
APPROVAL_STATUSES = {"pending", "approved", "rejected", "expired"}


class Audit:
    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []
        self.notes: list[dict[str, str]] = []

    def add(self, level: str, code: str, message: str, location: str = "") -> None:
        item = {"code": code, "message": message}
        if location:
            item["location"] = location
        getattr(self, f"{level}s").append(item)

    def error(self, code: str, message: str, location: str = "") -> None:
        self.add("error", code, message, location)

    def warning(self, code: str, message: str, location: str = "") -> None:
        self.add("warning", code, message, location)

    def note(self, code: str, message: str, location: str = "") -> None:
        self.add("note", code, message, location)


def load_json(path: Path, audit: Audit, label: str) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        audit.error("file_missing", f"{label} does not exist: {path}", label)
    except PermissionError:
        audit.error("file_unreadable", f"{label} is not readable: {path}", label)
    except UnicodeDecodeError as exc:
        audit.error("utf8_invalid", f"{label} is not valid UTF-8: {exc}", label)
    except json.JSONDecodeError as exc:
        audit.error(
            "json_invalid",
            f"{label} is not valid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            label,
        )
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_path(path: Path) -> tuple[str, str]:
    """Match the project's versioned file-or-tree hashing contract."""
    if path.is_symlink():
        raise ValueError(f"Artifact paths may not be symbolic links: {path}")
    if path.is_file():
        return sha256_file(path), "sha256-file"
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Artifact path is neither a file nor directory: {path}")
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*"), key=lambda value: value.relative_to(path).as_posix()):
        if item.is_symlink():
            raise ValueError(f"Artifact trees may not contain symbolic links: {item}")
        relative = item.relative_to(path).as_posix().encode("utf-8")
        if item.is_dir():
            digest.update(b"D\0" + relative + b"\0")
            continue
        digest.update(b"F\0" + relative + b"\0")
        digest.update(str(item.stat().st_size).encode("ascii") + b"\0")
        with item.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest(), "sha256-tree-v1"


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_safe_relative(value: Any) -> bool:
    if not nonempty_string(value):
        return False
    path = Path(value)
    return not path.is_absolute() and not path.drive and ".." not in path.parts


def under_root(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_registered_path(
    project_root: Path,
    registry_root: Path,
    value: Any,
    audit: Audit,
    location: str,
) -> Path | None:
    if not is_safe_relative(value):
        audit.error("unsafe_path", "Path must be a non-empty relative path without '..'.", location)
        return None
    candidate = (project_root / value).resolve()
    if not under_root(project_root, candidate):
        audit.error("path_escape", f"Resolved path leaves project root: {value}", location)
        return None
    if not under_root(registry_root, candidate):
        audit.error("path_outside_registry", f"Resolved path is outside artifact_registry.root: {value}", location)
        return None
    return candidate


def require_fields(value: Any, fields: tuple[str, ...], audit: Audit, location: str) -> bool:
    if not isinstance(value, dict):
        audit.error("object_required", "Expected an object.", location)
        return False
    missing = [field for field in fields if field not in value]
    if missing:
        audit.error("required_fields_missing", f"Missing fields: {', '.join(missing)}", location)
        return False
    return True


def parse_date(value: Any, audit: Audit, location: str) -> date | None:
    if not nonempty_string(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        audit.error("date_invalid", f"Expected an ISO 8601 calendar date, got {value!r}.", location)
        return None


def check_manifest_shape(manifest: Any, audit: Audit) -> bool:
    required = (
        "schema_version",
        "project_id",
        "profile",
        "source_locale",
        "target_locales",
        "risk_level",
        "medical",
        "features",
        "deliverables",
        "artifact_registry",
        "route",
        "approvals",
        "staleness",
    )
    if not require_fields(manifest, required, audit, "project"):
        return False
    if manifest.get("schema_version") != "1.0.0":
        audit.error("schema_version", "Project schema_version must be '1.0.0'.", "project.schema_version")
    if not nonempty_string(manifest.get("project_id")) or not PROJECT_ID_RE.fullmatch(manifest["project_id"]):
        audit.error("project_id", "project_id must be a lowercase kebab-case identifier.", "project.project_id")
    if manifest.get("source_locale") not in LOCALES:
        audit.error("source_locale", "source_locale must be en-US or id-ID.", "project.source_locale")
    targets = manifest.get("target_locales")
    if not isinstance(targets, list) or any(not isinstance(item, str) or item not in LOCALES for item in targets):
        audit.error("target_locales", "target_locales must contain only en-US or id-ID.", "project.target_locales")
    elif len(targets) != len(set(targets)):
        audit.error("target_locales_duplicate", "target_locales contains duplicates.", "project.target_locales")
    if manifest.get("risk_level") not in RISK_LEVELS:
        audit.error("risk_level", "risk_level must be R0, R1, R2, or R3.", "project.risk_level")
    return True


def check_registry(
    manifest: dict[str, Any], project_root: Path, phase: str, audit: Audit
) -> tuple[dict[str, dict[str, Any]], dict[str, Path], Path | None]:
    registry = manifest.get("artifact_registry")
    if not require_fields(registry, ("root", "slots", "entries"), audit, "project.artifact_registry"):
        return {}, {}, None
    root_value = registry.get("root")
    if not is_safe_relative(root_value):
        audit.error(
            "artifact_root_unsafe",
            "artifact_registry.root must be a non-empty relative path without '..'.",
            "project.artifact_registry.root",
        )
        return {}, {}, None
    registry_root = (project_root / root_value).resolve()
    if not under_root(project_root, registry_root):
        audit.error("artifact_root_escape", "Artifact root resolves outside the project root.", "project.artifact_registry.root")
        return {}, {}, None

    entries = registry.get("entries")
    if not isinstance(entries, list):
        audit.error("entries_type", "artifact_registry.entries must be an array.", "project.artifact_registry.entries")
        return {}, {}, registry_root

    by_id: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    seen_paths: dict[str, str] = {}
    required = (
        "schema_version",
        "artifact_id",
        "kind",
        "path",
        "project_id",
        "locale",
        "produced_by",
        "producer_node",
        "operation",
        "status",
        "revision",
        "sha256",
        "hash_kind",
        "inputs",
        "blockers",
        "provenance",
        "revision_history",
    )

    for index, entry in enumerate(entries):
        location = f"project.artifact_registry.entries[{index}]"
        if not require_fields(entry, required, audit, location):
            continue
        artifact_id = entry.get("artifact_id")
        if not nonempty_string(artifact_id) or not ARTIFACT_ID_RE.fullmatch(artifact_id):
            audit.error("artifact_id", "Invalid artifact_id.", f"{location}.artifact_id")
            continue
        if artifact_id in by_id:
            audit.error("artifact_id_duplicate", f"Duplicate artifact_id: {artifact_id}", f"{location}.artifact_id")
            continue
        by_id[artifact_id] = entry

        if entry.get("schema_version") != "1.0.0":
            audit.error("artifact_schema_version", "Artifact schema_version must be '1.0.0'.", location)
        if entry.get("project_id") != manifest.get("project_id"):
            audit.error("artifact_project_mismatch", "Artifact project_id does not match the manifest.", location)
        if entry.get("locale") not in LOCALES:
            audit.error("artifact_locale", "Artifact locale must be en-US or id-ID.", location)
        producer = entry.get("produced_by")
        if not nonempty_string(producer) or not SKILL_RE.fullmatch(producer):
            audit.error("artifact_producer", "produced_by must be lowercase kebab-case.", location)
        producer_node = entry.get("producer_node")
        operation = entry.get("operation")
        if not nonempty_string(producer_node) or not SKILL_RE.fullmatch(producer_node):
            audit.error("artifact_producer_node", "producer_node must be lowercase kebab-case.", location)
        if not nonempty_string(operation) or not SKILL_RE.fullmatch(operation):
            audit.error("artifact_operation", "operation must be lowercase kebab-case.", location)
        route_value = manifest.get("route")
        route_items = (
            route_value.get("nodes", []) + route_value.get("parked_nodes", [])
            if isinstance(route_value, dict)
            and isinstance(route_value.get("nodes", []), list)
            and isinstance(route_value.get("parked_nodes", []), list)
            else []
        )
        route_nodes = {
            item.get("id"): item
            for item in route_items
            if isinstance(item, dict) and nonempty_string(item.get("id"))
        }
        route_node = route_nodes.get(producer_node)
        if route_node is None:
            audit.error("producer_node_missing", f"Route does not contain producer node {producer_node!r}.", location)
        else:
            if route_node.get("skill") != producer:
                audit.error("producer_skill_mismatch", "Artifact producer does not match its route node skill.", location)
            if route_node.get("operation") != operation:
                audit.error("producer_operation_mismatch", "Artifact operation does not match its route node operation.", location)
        status = entry.get("status")
        if status not in ARTIFACT_STATUSES:
            audit.error("artifact_status", f"Unknown artifact status: {status!r}", location)
        blockers = entry.get("blockers")
        if not isinstance(blockers, list) or any(not nonempty_string(item) for item in blockers):
            audit.error("artifact_blockers", "blockers must be an array of non-empty strings.", location)
        elif blockers and status in {"approved", "locked"}:
            audit.error("approved_with_blockers", "Approved or locked artifact has open blockers.", location)
        if status in {"stale", "blocked"} and phase in {"proof", "release"}:
            audit.error("artifact_not_ready", f"Artifact {artifact_id} is {status} during {phase} preflight.", location)

        expected_hash = entry.get("sha256")
        if not nonempty_string(expected_hash) or not HASH_RE.fullmatch(expected_hash):
            audit.error("artifact_hash_format", "sha256 must be 64 lowercase hexadecimal characters.", location)
        hash_kind = entry.get("hash_kind")
        if hash_kind not in {"sha256-file", "sha256-tree-v1"}:
            audit.error("artifact_hash_kind", f"Unknown hash_kind: {hash_kind!r}", location)

        path = resolve_registered_path(
            project_root,
            registry_root,
            entry.get("path"),
            audit,
            f"{location}.path",
        )
        if path is None:
            continue
        normalized = str(path).casefold()
        if normalized in seen_paths:
            audit.error(
                "artifact_path_duplicate",
                f"Artifact path is shared by {seen_paths[normalized]} and {artifact_id}.",
                f"{location}.path",
            )
        else:
            seen_paths[normalized] = artifact_id
        paths[artifact_id] = path
        if not path.exists():
            audit.error("artifact_file_missing", f"Registered file does not exist: {path}", location)
        elif HASH_RE.fullmatch(str(expected_hash or "")):
            try:
                actual_hash, actual_kind = sha256_path(path)
                if actual_kind != hash_kind:
                    audit.error(
                        "artifact_hash_kind_mismatch",
                        f"Stored {hash_kind}; path requires {actual_kind}.",
                        location,
                    )
                if actual_hash != expected_hash:
                    audit.error(
                        "artifact_hash_mismatch",
                        f"Stored {expected_hash}; actual {actual_hash}.",
                        location,
                    )
            except (OSError, ValueError) as exc:
                audit.error("artifact_hash_failed", str(exc), location)

        history = entry.get("revision_history")
        if not isinstance(history, list) or not history:
            audit.error("revision_history_missing", "revision_history must contain at least one snapshot record.", location)
        else:
            latest = history[-1]
            if not isinstance(latest, dict):
                audit.error("revision_history_record", "Latest revision history item must be an object.", location)
            else:
                for field in ("revision", "sha256", "hash_kind"):
                    if latest.get(field) != entry.get(field):
                        audit.error(
                            "revision_history_mismatch",
                            f"Latest revision history {field} does not match the current entry.",
                            location,
                        )
            revisions = [item.get("revision") for item in history if isinstance(item, dict)]
            if len(revisions) != len(history) or any(not isinstance(value, int) for value in revisions):
                audit.error("revision_history_revision", "Each revision history item needs an integer revision.", location)
            elif revisions != sorted(revisions) or len(revisions) != len(set(revisions)):
                audit.error("revision_history_order", "Revision history must be unique and ascending.", location)
            snapshot_value = latest.get("snapshot_path") if isinstance(latest, dict) else None
            if not is_safe_relative(snapshot_value):
                audit.error("snapshot_path_unsafe", "Latest snapshot path must remain relative to the project.", location)
            else:
                snapshot = (project_root / snapshot_value).resolve()
                if not under_root(project_root, snapshot):
                    audit.error("snapshot_path_escape", "Latest snapshot path leaves the project root.", location)
                elif not snapshot.exists():
                    audit.error("snapshot_missing", f"Latest immutable snapshot is missing: {snapshot}", location)
                elif HASH_RE.fullmatch(str(entry.get("sha256") or "")):
                    try:
                        snapshot_hash, snapshot_kind = sha256_path(snapshot)
                        if snapshot_hash != entry.get("sha256") or snapshot_kind != entry.get("hash_kind"):
                            audit.error("snapshot_mismatch", "Latest immutable snapshot does not match the registry hash and kind.", location)
                    except (OSError, ValueError) as exc:
                        audit.error("snapshot_hash_failed", str(exc), location)

    for artifact_id, entry in by_id.items():
        location = f"artifact:{artifact_id}"
        inputs = entry.get("inputs")
        if not isinstance(inputs, list):
            audit.error("artifact_inputs", "inputs must be an array.", location)
            continue
        seen_inputs: set[str] = set()
        for index, item in enumerate(inputs):
            item_location = f"{location}.inputs[{index}]"
            if not require_fields(item, ("artifact_id", "revision", "sha256"), audit, item_location):
                continue
            source_id = item.get("artifact_id")
            if not nonempty_string(source_id):
                audit.error("input_id", "Input artifact_id must be non-empty.", item_location)
                continue
            if source_id in seen_inputs:
                audit.warning("input_duplicate", f"Repeated input dependency: {source_id}", item_location)
            seen_inputs.add(source_id)
            source = by_id.get(source_id)
            if source is None:
                audit.error("input_missing", f"Input artifact is not registered: {source_id}", item_location)
            elif item.get("sha256") != source.get("sha256"):
                audit.error(
                    "input_hash_stale",
                    f"Recorded input hash does not match current registry hash for {source_id}.",
                    item_location,
                )
            elif item.get("revision") != source.get("revision"):
                audit.error(
                    "input_revision_stale",
                    f"Recorded input revision does not match current registry revision for {source_id}.",
                    item_location,
                )
    return by_id, paths, registry_root


def check_staleness(manifest: dict[str, Any], entries: dict[str, Any], phase: str, audit: Audit) -> None:
    records = manifest.get("staleness")
    if not isinstance(records, list):
        audit.error("staleness_type", "staleness must be an array.", "project.staleness")
        return
    seen: set[str] = set()
    for index, record in enumerate(records):
        location = f"project.staleness[{index}]"
        if not require_fields(record, ("stale_id", "artifact_id", "reason", "detected_at", "invalidates_nodes"), audit, location):
            continue
        stale_id = record.get("stale_id")
        if not nonempty_string(stale_id):
            audit.error("stale_id", "stale_id must be non-empty.", location)
            continue
        if stale_id in seen:
            audit.error("stale_id_duplicate", f"Duplicate stale_id: {stale_id}", location)
        seen.add(stale_id)
        record_artifact_id = record.get("artifact_id")
        if not nonempty_string(record_artifact_id) or record_artifact_id not in entries:
            audit.error("stale_artifact_missing", "Staleness record names an unregistered artifact.", location)
        unresolved = not record.get("resolved_at")
        if unresolved:
            message = f"Unresolved staleness record {stale_id} affects {record.get('artifact_id')}."
            if phase in {"proof", "release"}:
                audit.error("staleness_unresolved", message, location)
            else:
                audit.warning("staleness_unresolved", message, location)


def check_route(manifest: dict[str, Any], audit: Audit) -> None:
    route = manifest.get("route")
    if not require_fields(route, ("route_version", "nodes", "edges"), audit, "project.route"):
        return
    if route.get("route_version") != "1.0.0":
        audit.error("route_version", "route_version must be '1.0.0'.", "project.route.route_version")
    nodes = route.get("nodes")
    edges = route.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        audit.error("route_arrays", "route.nodes and route.edges must be arrays.", "project.route")
        return
    node_ids: set[str] = set()
    node_map: dict[str, dict[str, Any]] = {}
    adjacency: dict[str, set[str]] = {}
    for index, node in enumerate(nodes):
        location = f"project.route.nodes[{index}]"
        if not require_fields(node, ("id", "skill", "operation", "depends_on", "status", "blockers"), audit, location):
            continue
        node_id = node.get("id")
        if not nonempty_string(node_id):
            audit.error("route_node_id", "Route node id must be non-empty.", location)
            continue
        if node_id in node_ids:
            audit.error("route_node_duplicate", f"Duplicate route node id: {node_id}", location)
        node_ids.add(node_id)
        node_map[node_id] = node
        adjacency.setdefault(node_id, set())
        blockers = node.get("blockers")
        if node.get("status") == "complete" and isinstance(blockers, list) and blockers:
            audit.error("complete_node_blocked", "Complete route node still has blockers.", location)

    for node_id, node in node_map.items():
        dependencies = node.get("depends_on")
        if not isinstance(dependencies, list):
            audit.error("route_dependencies", "depends_on must be an array.", f"route.node:{node_id}")
            continue
        for dependency in dependencies:
            if not nonempty_string(dependency) or dependency not in node_ids:
                audit.error("route_dependency_missing", f"Unknown dependency {dependency!r}.", f"route.node:{node_id}")
            else:
                adjacency.setdefault(dependency, set()).add(node_id)
    for index, edge in enumerate(edges):
        location = f"project.route.edges[{index}]"
        if not require_fields(edge, ("from", "to"), audit, location):
            continue
        start, end = edge.get("from"), edge.get("to")
        if not nonempty_string(start) or not nonempty_string(end) or start not in node_ids or end not in node_ids:
            audit.error("route_edge_missing_node", f"Edge references unknown node: {start!r} -> {end!r}.", location)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        if any(visit(child) for child in adjacency.get(node_id, ())):
            return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    if any(visit(node_id) for node_id in tuple(node_ids) if node_id not in visited):
        audit.error("route_cycle", "Route dependencies contain a cycle.", "project.route")


def check_illustration_setup_basis(
    manifest: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    basis: list[Any],
    paths: dict[str, Path],
    audit: Audit,
    location: str,
) -> None:
    """Check setup-specific readiness; art judgment remains a human review."""
    basis_entries = [
        entries[item["artifact_id"]]
        for item in basis
        if isinstance(item, dict) and nonempty_string(item.get("artifact_id")) and item["artifact_id"] in entries
    ]
    required_kinds = {"illustration_setup", "character_bible"}
    present = {entry.get("kind") for entry in basis_entries}
    if not required_kinds <= present:
        audit.error(
            "illustration_setup_basis_incomplete",
            "Illustration setup approval must name both illustration_setup and character_bible artifacts.",
            location,
        )

    route = manifest.get("route")
    route_items: list[Any] = []
    if isinstance(route, dict):
        for key in ("nodes", "parked_nodes"):
            if isinstance(route.get(key), list):
                route_items.extend(route[key])
    setup_nodes = [
        node for node in route_items
        if isinstance(node, dict) and node.get("id") == "nam-book-illustration-setup"
    ]
    if (
        len(setup_nodes) != 1
        or setup_nodes[0].get("skill") != "nam-book-illustration-setup"
        or setup_nodes[0].get("status") != "complete"
        or setup_nodes[0].get("blockers")
    ):
        audit.error(
            "illustration_setup_stage_incomplete",
            "Illustration setup approval requires one completed, unblocked setup stage (active or parked).",
            location,
        )

    stale_records = manifest.get("staleness", [])
    stale_ids = {
        record.get("artifact_id")
        for record in (stale_records if isinstance(stale_records, list) else [])
        if isinstance(record, dict)
        and not record.get("resolved_at")
        and nonempty_string(record.get("artifact_id"))
        and entries.get(record["artifact_id"], {}).get("producer_node")
        not in (record.get("resolved_nodes") or [])
    }
    visited: set[str] = set()
    visiting: set[str] = set()
    setup_payloads: list[dict[str, Any]] = []

    def check_fresh(artifact_id: str) -> None:
        if artifact_id in visiting:
            audit.error("illustration_setup_input_cycle", "Setup input dependencies contain a cycle.", location)
            return
        if artifact_id in visited:
            return
        artifact = entries.get(artifact_id)
        if artifact is None:
            audit.error("illustration_setup_input_missing", f"Setup input {artifact_id!r} is not registered.", location)
            return
        visiting.add(artifact_id)
        if artifact.get("status") not in {"draft", "review", "approved", "locked"} or artifact.get("blockers") or artifact_id in stale_ids:
            audit.error("illustration_setup_input_not_fresh", f"Setup basis or input {artifact_id!r} is stale or blocked.", location)
        inputs = artifact.get("inputs")
        if not isinstance(inputs, list):
            audit.error("illustration_setup_inputs_invalid", f"Setup basis or input {artifact_id!r} needs an inputs array.", location)
        else:
            for item in inputs:
                if not isinstance(item, dict) or not nonempty_string(item.get("artifact_id")):
                    audit.error("illustration_setup_input_invalid", "Setup input reference is malformed.", location)
                    continue
                source = entries.get(item["artifact_id"])
                if source is not None and (item.get("revision") != source.get("revision") or item.get("sha256") != source.get("sha256")):
                    audit.error("illustration_setup_input_stale", f"Setup input reference to {item['artifact_id']!r} is out of date.", location)
                check_fresh(item["artifact_id"])
        visiting.remove(artifact_id)
        visited.add(artifact_id)

    for entry in basis_entries:
        check_fresh(entry["artifact_id"])
        if entry.get("kind") not in required_kinds:
            continue
        if entry.get("producer_node") != "nam-book-illustration-setup" or entry.get("produced_by") != "nam-book-illustration-setup":
            audit.error(
                "illustration_setup_producer_mismatch",
                "Setup and bible basis artifacts must belong to the setup stage; migrate a legacy bible explicitly.",
                location,
            )
        if entry.get("kind") != "illustration_setup":
            continue
        setup_path = paths.get(entry["artifact_id"])
        if setup_path is None:
            audit.error("illustration_setup_payload_missing", "Cannot inspect the registered setup payload.", location)
            continue
        payload = load_json(setup_path, audit, f"setup:{entry['artifact_id']}")
        if not isinstance(payload, dict):
            audit.error("illustration_setup_payload_invalid", "Setup payload must be a JSON object.", location)
            continue
        setup_payloads.append(payload)
        if payload.get("mascot_mode") not in ("custom", "supplied", "nam", "none"):
            audit.error("illustration_setup_mascot_mode", "Setup must choose custom, supplied, nam, or none mascot mode.", location)
        if payload.get("hand_drawn") is not True:
            audit.error("illustration_setup_hand_drawn", "Setup must retain the hand-drawn foundation.", location)
        calibration = payload.get("calibration")
        samples = calibration.get("sample_artifact_ids") if isinstance(calibration, dict) else None
        if not isinstance(calibration, dict) or calibration.get("status") != "passed" or not isinstance(samples, list) or not samples:
            audit.error("illustration_setup_calibration_incomplete", "Setup needs passed calibration with registered sample artifact IDs.", location)
            continue
        entry_inputs = entry.get("inputs")
        setup_inputs = {
            item.get("artifact_id") for item in (entry_inputs if isinstance(entry_inputs, list) else [])
            if isinstance(item, dict) and nonempty_string(item.get("artifact_id"))
        }
        for sample_id in samples:
            sample = entries.get(sample_id) if isinstance(sample_id, str) else None
            if sample is None or sample.get("kind") != "illustration_calibration" or sample_id not in setup_inputs:
                audit.error("illustration_setup_calibration_basis", "Every calibration sample must be a registered illustration_calibration artifact in setup inputs.", location)

    for bible in (entry for entry in basis_entries if entry.get("kind") == "character_bible"):
        bible_path = paths.get(bible["artifact_id"])
        if bible_path is None:
            audit.error("illustration_setup_bible_missing", "Cannot inspect the registered character bible.", location)
            continue
        try:
            bible_text = bible_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            audit.error("illustration_setup_bible_unreadable", f"Cannot read character bible: {exc}", location)
            continue
        try:
            bible_payload = json.loads(bible_text)
        except json.JSONDecodeError:
            bible_payload = None  # A migrated legacy bible may be Markdown.
        for setup in setup_payloads:
            if isinstance(bible_payload, dict) and "mascot_mode" in bible_payload:
                if bible_payload["mascot_mode"] != setup.get("mascot_mode"):
                    audit.error("illustration_setup_mascot_mismatch", "Setup and character bible must select the same mascot mode.", location)
                if bible_payload["mascot_mode"] == "none" and ("identity" not in bible_payload or bible_payload["identity"] is not None):
                    audit.error("illustration_setup_none_identity", "A mascot-free character bible must explicitly set identity to null.", location)
                elif bible_payload["mascot_mode"] != "none" and not isinstance(bible_payload.get("identity"), dict):
                    audit.error("illustration_setup_identity_missing", "A character bible with a mascot must define an identity object.", location)
                continue
            if setup.get("mascot_mode") == "none":
                audit.error("illustration_setup_none_legacy_bible", "Mascot-free setup requires a new explicit mascot_mode:none, identity:null bible; a legacy identity cannot substitute.", location)
                continue
            adoption = setup.get("adoption")
            provenance = manifest.get("provenance", [])
            migration_matches = False
            for event in (provenance if isinstance(provenance, list) else []):
                if not isinstance(event, dict) or event.get("item_id") != f"illustration-setup-adoption-{bible['artifact_id']}":
                    continue
                try:
                    notes = json.loads(event.get("notes", ""))
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(notes, dict) and all(notes.get(key) == bible.get(key) for key in ("artifact_id", "revision", "sha256")) and notes.get("new_owner") == "nam-book-illustration-setup":
                    migration_matches = True
            if (
                not isinstance(adoption, dict)
                or adoption.get("character_bible_artifact_id") != bible["artifact_id"]
                or adoption.get("sha256") != bible["sha256"]
                or not migration_matches
            ):
                audit.error("illustration_setup_legacy_adoption_missing", "A legacy bible without mascot_mode needs setup adoption ID/hash and the matching explicit migration provenance event.", location)


def check_approvals(
    manifest: dict[str, Any], entries: dict[str, dict[str, Any]], phase: str, audit: Audit,
    paths: dict[str, Path] | None = None,
) -> None:
    approvals = manifest.get("approvals")
    if not isinstance(approvals, list):
        audit.error("approvals_type", "approvals must be an array.", "project.approvals")
        return
    seen_ids: set[str] = set()
    approved_kinds: set[str] = set()
    for index, approval in enumerate(approvals):
        errors_before = len(audit.errors)
        location = f"project.approvals[{index}]"
        if not require_fields(approval, ("approval_id", "kind", "status", "requested_at", "basis"), audit, location):
            continue
        approval_id = approval.get("approval_id")
        if not nonempty_string(approval_id):
            audit.error("approval_id", "approval_id must be non-empty.", location)
            continue
        if approval_id in seen_ids:
            audit.error("approval_id_duplicate", f"Duplicate approval_id: {approval_id}", location)
        seen_ids.add(approval_id)
        status = approval.get("status")
        if status not in APPROVAL_STATUSES:
            audit.error("approval_status", f"Unknown approval status: {status!r}", location)
        if status == "approved":
            if not nonempty_string(approval.get("decided_at")) or not nonempty_string(approval.get("decided_by")):
                audit.error("approval_decision_missing", "Approved record needs decided_at and decided_by.", location)
        basis = approval.get("basis")
        if not isinstance(basis, list):
            audit.error("approval_basis", "Approval basis must be an array.", location)
            continue
        if status == "approved" and not basis:
            if approval.get("kind") == "project-brief":
                audit.note(
                    "project_brief_manifest_bound",
                    "Bootstrap exception: project-brief may be approved before artifacts exist; the manifest carries the decision record without an artifact hash basis.",
                    location,
                )
            else:
                audit.error("approval_basis_empty", "Approved record must have a hash-bound artifact basis.", location)
        for item_index, item in enumerate(basis):
            item_location = f"{location}.basis[{item_index}]"
            if not require_fields(item, ("artifact_id", "revision", "sha256"), audit, item_location):
                continue
            basis_artifact_id = item.get("artifact_id")
            if not nonempty_string(basis_artifact_id):
                audit.error("approval_artifact_id", "Approval basis artifact_id must be non-empty.", item_location)
                continue
            artifact = entries.get(basis_artifact_id)
            report_basis = audit.error if status == "approved" else audit.note
            if artifact is None:
                report_basis("approval_artifact_missing", "Approval basis names an unregistered artifact.", item_location)
            elif item.get("sha256") != artifact.get("sha256"):
                report_basis("approval_hash_stale", "Approval basis hash no longer matches the registry.", item_location)
            elif item.get("revision") != artifact.get("revision"):
                report_basis("approval_revision_stale", "Approval basis revision no longer matches the registry.", item_location)
            elif status == "approved" and (artifact.get("status") in {"stale", "blocked"} or artifact.get("blockers")):
                audit.error("approval_basis_not_fresh", "Approved basis artifact is stale or blocked.", item_location)

        if status == "approved" and approval.get("kind") == "illustration-setup":
            check_illustration_setup_basis(manifest, entries, basis, paths or {}, audit, location)

        if status == "approved" and approval.get("kind") == "medical-expert-signoff":
            if not nonempty_string(approval.get("reviewer_role")) or not nonempty_string(approval.get("reviewer_credentials")):
                audit.error(
                    "expert_identity_incomplete",
                    "Approved medical-expert-signoff needs reviewer_role and reviewer_credentials.",
                    location,
                )

        if status == "approved" and len(audit.errors) == errors_before:
            approved_kinds.add(str(approval.get("kind")))

    features = manifest.get("features") if isinstance(manifest.get("features"), dict) else {}
    if phase == "release":
        if "final-proof" not in approved_kinds:
            audit.error("final_proof_missing", "Release requires an approved hash-bound final-proof record.", "project.approvals")
        if manifest.get("risk_level") == "R3" and "medical-expert-signoff" not in approved_kinds:
            audit.error("expert_signoff_missing", "R3 release requires approved medical-expert-signoff.", "project.approvals")
        if (features.get("illustrations") or features.get("diagrams")) and "illustration-setup" not in approved_kinds:
            audit.error("illustration_setup_approval_missing", "Release with illustrations or diagrams requires current illustration-setup approval bound to setup and bible artifacts; legacy character-bible approval alone is insufficient.", "project.approvals")


def find_evidence_path(
    explicit: Path | None,
    entries: dict[str, dict[str, Any]],
    paths: dict[str, Path],
) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    for artifact_id, entry in entries.items():
        kind = str(entry.get("kind", "")).replace("-", "_").casefold()
        if kind == "evidence_ledger":
            return paths.get(artifact_id)
    return None


def check_medical_context(manifest: dict[str, Any], phase: str, audit: Audit) -> None:
    medical = manifest.get("medical")
    if not isinstance(medical, dict) or "enabled" not in medical:
        audit.error("medical_shape", "medical must be an object with enabled and context fields.", "project.medical")
        return
    if not medical.get("enabled"):
        return
    for field in ("jurisdiction", "evidence_cutoff", "revalidate_before_export"):
        if not nonempty_string(medical.get(field)):
            audit.error("medical_context_missing", f"Medical project requires {field}.", f"project.medical.{field}")
    cutoff = parse_date(medical.get("evidence_cutoff"), audit, "project.medical.evidence_cutoff")
    deadline = parse_date(medical.get("revalidate_before_export"), audit, "project.medical.revalidate_before_export")
    if cutoff and deadline and deadline < cutoff:
        audit.error("medical_dates_order", "revalidate_before_export precedes evidence_cutoff.", "project.medical")
    if deadline and deadline < date.today():
        message = f"Medical evidence revalidation deadline passed on {deadline.isoformat()}."
        if phase in {"proof", "release"}:
            audit.error("medical_revalidation_due", message, "project.medical.revalidate_before_export")
        else:
            audit.warning("medical_revalidation_due", message, "project.medical.revalidate_before_export")


def check_evidence(
    ledger: Any, manifest: dict[str, Any], phase: str, audit: Audit, label: str
) -> dict[str, int]:
    counts = {"sources": 0, "claims": 0, "high_stakes_claims": 0, "verified_claims": 0}
    if not require_fields(
        ledger,
        ("schema_version", "project_id", "locale", "research_cutoff", "sources", "claims", "limitations", "unresolved_gaps"),
        audit,
        label,
    ):
        return counts
    if ledger.get("schema_version") != "1.0.0":
        audit.error("evidence_schema_version", "Evidence schema_version must be '1.0.0'.", label)
    if ledger.get("project_id") != manifest.get("project_id"):
        audit.error("evidence_project_mismatch", "Evidence ledger project_id does not match the manifest.", label)
    sources = ledger.get("sources")
    claims = ledger.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        audit.error("evidence_arrays", "Evidence sources and claims must be arrays.", label)
        return counts
    counts["sources"] = len(sources)
    counts["claims"] = len(claims)
    source_map: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        location = f"{label}.sources[{index}]"
        if not require_fields(
            source,
            ("source_id", "retrieval_status", "metadata_status", "correction_status"),
            audit,
            location,
        ):
            continue
        source_id = source.get("source_id")
        if not nonempty_string(source_id):
            audit.error("source_id", "source_id must be non-empty.", location)
            continue
        if source_id in source_map:
            audit.error("source_id_duplicate", f"Duplicate source_id: {source_id}", location)
        source_map[source_id] = source

    claim_ids: set[str] = set()
    used_sources: set[str] = set()
    for index, claim in enumerate(claims):
        location = f"{label}.claims[{index}]"
        if not require_fields(
            claim,
            ("claim_id", "claim_text", "risk_level", "evidence_status", "evidence"),
            audit,
            location,
        ):
            continue
        claim_id = claim.get("claim_id")
        if not nonempty_string(claim_id):
            audit.error("claim_id", "claim_id must be non-empty.", location)
            continue
        if claim_id in claim_ids:
            audit.error("claim_id_duplicate", f"Duplicate claim_id: {claim_id}", location)
        claim_ids.add(claim_id)
        risk = claim.get("risk_level")
        high_stakes = risk in {"R2", "R3"}
        if risk not in RISK_LEVELS:
            audit.error("claim_risk", f"Unknown claim risk: {risk!r}", location)
        if high_stakes:
            counts["high_stakes_claims"] += 1
        evidence = claim.get("evidence")
        if not isinstance(evidence, list):
            audit.error("claim_evidence", "Claim evidence must be an array.", location)
            continue
        supporting_entries: list[tuple[dict[str, Any], dict[str, Any]]] = []
        contradiction = False
        for item_index, item in enumerate(evidence):
            item_location = f"{location}.evidence[{item_index}]"
            if not require_fields(item, ("source_id", "passage_status", "claim_support"), audit, item_location):
                continue
            source_id = item.get("source_id")
            source = source_map.get(source_id)
            if source is None:
                audit.error("claim_source_missing", f"Evidence references unknown source {source_id!r}.", item_location)
                continue
            used_sources.add(source_id)
            if item.get("claim_support") == "contradicts":
                contradiction = True
            if item.get("passage_status") == "found" and item.get("claim_support") == "supports":
                supporting_entries.append((item, source))

        status = claim.get("evidence_status")
        if status == "verified":
            counts["verified_claims"] += 1
            if not nonempty_string(claim.get("verified_by")):
                audit.error("verified_by_missing", "Verified claim needs verified_by.", location)
            if contradiction:
                audit.error("verified_claim_conflict", "Verified claim retains contradicting evidence without a resolution field.", location)
            valid_support = []
            for item, source in supporting_entries:
                if (
                    source.get("retrieval_status") == "success"
                    and source.get("metadata_status") == "verified"
                    and source.get("correction_status") not in {"retracted", "expression-of-concern"}
                    and nonempty_string(item.get("supporting_passage"))
                    and nonempty_string(item.get("location"))
                ):
                    valid_support.append(item)
            if not valid_support:
                audit.error(
                    "verified_claim_unsupported",
                    "Verified claim lacks a found supporting passage with location from a retrieved, metadata-verified, non-retracted source.",
                    location,
                )
        elif high_stakes and status in {"candidate", "conflicting", "missing"}:
            message = f"High-stakes claim {claim_id} is {status}, not verified."
            if phase in {"proof", "release"}:
                audit.error("high_stakes_unverified", message, location)
            else:
                audit.warning("high_stakes_unverified", message, location)

    for source_id in sorted(used_sources):
        source = source_map[source_id]
        correction = source.get("correction_status")
        if correction in {"retracted", "expression-of-concern"}:
            audit.error("source_correction_alert", f"Used source {source_id} is {correction}.", f"source:{source_id}")
        elif correction in {"not-checked", "unknown"}:
            message = f"Used source {source_id} has correction status {correction}."
            if phase == "release" and counts["high_stakes_claims"]:
                audit.error("source_correction_unchecked", message, f"source:{source_id}")
            else:
                audit.warning("source_correction_unchecked", message, f"source:{source_id}")
        elif correction == "corrected":
            audit.warning("source_corrected", f"Confirm claim passages incorporate corrections for {source_id}.", f"source:{source_id}")

    medical = manifest.get("medical") if isinstance(manifest.get("medical"), dict) else {}
    if medical.get("enabled"):
        if ledger.get("jurisdiction") != medical.get("jurisdiction"):
            audit.error("evidence_jurisdiction_mismatch", "Ledger jurisdiction does not match the medical project context.", label)
        if ledger.get("research_cutoff") != medical.get("evidence_cutoff"):
            audit.error("evidence_cutoff_mismatch", "Ledger research_cutoff does not match the medical evidence cutoff.", label)
        if not nonempty_string(ledger.get("retraction_check_date")):
            message = "Medical evidence ledger has no retraction_check_date."
            if phase == "release":
                audit.error("retraction_check_missing", message, label)
            else:
                audit.warning("retraction_check_missing", message, label)
    gaps = ledger.get("unresolved_gaps")
    if isinstance(gaps, list) and gaps:
        message = f"Evidence ledger records {len(gaps)} unresolved gap(s)."
        if phase == "release" and counts["high_stakes_claims"]:
            audit.error("high_stakes_gaps", message, label)
        else:
            audit.warning("evidence_gaps", message, label)
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Path to the Nam Book project manifest JSON.")
    parser.add_argument(
        "--root",
        type=Path,
        help="Project root used to resolve registry paths (default: parent of .nam-book, otherwise manifest directory).",
    )
    parser.add_argument("--evidence", type=Path, help="Explicit evidence ledger JSON path.")
    parser.add_argument(
        "--phase",
        choices=("draft", "proof", "release"),
        default="proof",
        help="Gate strictness. Release also requires current final-proof approval.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = Audit()
    project_path = args.project.resolve()
    if args.root:
        project_root = args.root.resolve()
    elif project_path.parent.name == ".nam-book":
        project_root = project_path.parent.parent.resolve()
    else:
        project_root = project_path.parent.resolve()
    manifest = load_json(project_path, audit, "project")
    counts: dict[str, int] = {"artifacts": 0, "approvals": 0, "staleness_records": 0}
    evidence_counts: dict[str, int] | None = None

    if isinstance(manifest, dict) and check_manifest_shape(manifest, audit):
        entries, paths, registry_root = check_registry(manifest, project_root, args.phase, audit)
        counts["artifacts"] = len(entries)
        counts["approvals"] = len(manifest.get("approvals", [])) if isinstance(manifest.get("approvals"), list) else 0
        counts["staleness_records"] = len(manifest.get("staleness", [])) if isinstance(manifest.get("staleness"), list) else 0
        check_staleness(manifest, entries, args.phase, audit)
        check_route(manifest, audit)
        check_approvals(manifest, entries, args.phase, audit, paths)
        check_medical_context(manifest, args.phase, audit)

        evidence_path = find_evidence_path(args.evidence, entries, paths)
        needs_evidence = manifest.get("risk_level") in {"R2", "R3"} or bool(
            isinstance(manifest.get("medical"), dict) and manifest["medical"].get("enabled")
        )
        if evidence_path is None:
            message = "No evidence ledger was supplied or found in the artifact registry."
            if needs_evidence and args.phase in {"proof", "release"}:
                audit.error("evidence_missing", message, "evidence")
            else:
                audit.warning("evidence_missing", message, "evidence")
        else:
            ledger = load_json(evidence_path, audit, "evidence")
            if isinstance(ledger, dict):
                evidence_counts = check_evidence(ledger, manifest, args.phase, audit, "evidence")
        if registry_root is not None:
            audit.note("artifact_root", str(registry_root), "project.artifact_registry.root")

    result = "fail" if audit.errors else ("pass-with-warnings" if audit.warnings else "pass")
    report = {
        "tool": "preflight_project.py",
        "scope": "structural preflight only; overall release readiness is not assessed",
        "phase": args.phase,
        "project": str(project_path),
        "structural_result": result,
        "counts": {**counts, **(evidence_counts or {})},
        "errors": audit.errors,
        "warnings": audit.warnings,
        "notes": audit.notes,
        "limitations": [
            "Does not perform complete JSON Schema validation.",
            "Does not fetch sources or establish factual, medical, legal, or cultural correctness.",
            "Does not render or visually inspect DOCX, EPUB, PDF, SVG, or PNG files.",
            "Does not establish accessibility, format conformance, rights clearance, or human approval.",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if audit.errors else 0


if __name__ == "__main__":
    sys.exit(main())
