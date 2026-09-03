"""Deterministic state and routing primitives for AskNam.

The module intentionally uses only the Python standard library.  AskNam is the
sole writer of the global project manifest; specialist skills return artifacts
for AskNam to register through these functions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0.0"
ROUTE_VERSION = "1.0.0"
PROJECT_SCHEMA_URI = (
    "https://raw.githubusercontent.com/arthamegayasa/nam-book-studio/"
    "main/skills/asknam/references/schemas/book-project.schema.json"
)
LEGACY_PROJECT_SCHEMA_URIS = {
    "../schemas/book-project.schema.json",
    "https://raw.githubusercontent.com/arthamegayasa/nam-book-studio/"
    "main/schemas/book-project.schema.json",
}
SUPPORTED_LOCALES = {"en-US", "id-ID"}
SUPPORTED_PROFILES = {"friendly-explainer", "textbook", "exam-prep"}
SUPPORTED_RISKS = {"R0", "R1", "R2", "R3"}
SUPPORTED_INTENTS = {
    "start",
    "resume",
    "revise",
    "audit",
    "illustrate",
    "localize",
    "publish",
}
SUPPORTED_DELIVERABLES = {"markdown", "docx", "pdf", "epub"}
NODE_STATUSES = {
    "pending",
    "ready",
    "running",
    "blocked",
    "complete",
    "skipped",
    "failed",
    "stale",
}
ARTIFACT_STATUSES = {"draft", "review", "approved", "locked", "stale", "blocked"}
APPROVAL_STATUSES = {"pending", "approved", "rejected", "expired"}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ARTIFACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")


class StateError(ValueError):
    """Raised when a requested state transition would break an invariant."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def asknam_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resource_candidates(base: Path | None, relative: Path) -> list[Path]:
    """Return repo and installed-skill resource locations in canonical order."""
    if base is None:
        return [
            asknam_root() / "references" / relative,
            repository_root() / relative,
        ]
    return [
        base / "skills" / "asknam" / "references" / relative,
        base / "references" / relative,
        base / relative,
    ]


def resolve_resource(base: Path | None, relative: Path) -> Path:
    candidates = _resource_candidates(base, relative)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    rendered = ", ".join(str(item) for item in candidates)
    raise StateError(f"Bundled AskNam resource not found; checked: {rendered}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise StateError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StateError(f"Expected a JSON object in {path}")
    return value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or "book-project"


def load_profile(profile_id: str, root: Path | None = None) -> dict[str, Any]:
    if profile_id not in SUPPORTED_PROFILES:
        raise StateError(f"Unsupported profile: {profile_id}")
    profile = load_json(
        resolve_resource(root, Path("profiles") / f"{profile_id}.json")
    )
    if profile.get("profile_id") != profile_id:
        raise StateError(f"Profile id mismatch in {profile_id}.json")
    return profile


def load_catalog(root: Path | None = None) -> dict[str, Any]:
    catalog = load_json(resolve_resource(root, Path("skill-catalog.json")))
    capabilities = catalog.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise StateError("The capability catalog is empty or malformed")
    names = [item.get("skill") for item in capabilities if isinstance(item, dict)]
    if len(names) != len(set(names)):
        raise StateError("The capability catalog contains duplicate skill ids")
    return catalog


def catalog_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["skill"]: item for item in catalog["capabilities"]}


def _resolve_feature(
    profile: dict[str, Any], feature: str, requested: str
) -> bool:
    default = bool(profile["defaults"][feature])
    locked = bool(profile["locked_features"][feature])
    if requested == "auto":
        return default
    value = requested == "yes"
    if locked and not value:
        raise StateError(
            f"Profile {profile['profile_id']} requires feature '{feature}'"
        )
    return value


def _approval_record(kind: str, now: str) -> dict[str, Any]:
    return {
        "approval_id": kind,
        "kind": kind,
        "status": "pending",
        "requested_at": now,
        "decided_at": None,
        "decided_by": None,
        "reviewer_role": None,
        "reviewer_credentials": None,
        "note": "",
        "basis": [],
    }


def _artifact_slots(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    slots: dict[str, dict[str, Any]] = {}
    for capability in catalog["capabilities"]:
        operations = ["run"]
        if capability.get("route_nodes"):
            operations = [item["operation"] for item in capability["route_nodes"]]
        for output in capability["produces"]:
            kind = output["kind"]
            if kind in slots:
                raise StateError(f"Duplicate artifact kind in catalog: {kind}")
            slots[kind] = {
                "path": f".nam-book/artifacts/{output['path']}",
                "cardinality": output["cardinality"],
                "produced_by": capability["skill"],
                "operations": operations,
                "required": output.get("required", True),
            }
    return slots


def create_manifest(
    *,
    title: str,
    project_id: str | None,
    subtitle: str,
    audience: str,
    reader_outcome: str,
    profile_id: str,
    source_locale: str,
    target_locales: list[str],
    risk_level: str,
    medical_enabled: bool,
    jurisdiction: str | None,
    evidence_cutoff: str | None,
    revalidate_before_export: str | None,
    assessments: str,
    illustrations: str,
    diagrams: str,
    deliverables: list[str],
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or repository_root()
    profile = load_profile(profile_id, base)
    catalog = load_catalog(base)
    now = utc_now()
    resolved_project_id = project_id or slugify(title)

    if not title.strip():
        raise StateError("Title must not be empty")
    if not ID_RE.fullmatch(resolved_project_id):
        raise StateError("Project id must be lowercase kebab-case")
    if source_locale not in SUPPORTED_LOCALES:
        raise StateError(f"Unsupported source locale: {source_locale}")
    if any(locale not in SUPPORTED_LOCALES for locale in target_locales):
        raise StateError("Target locales must be en-US or id-ID")
    if source_locale in target_locales:
        raise StateError("The source locale cannot also be a target locale")
    if len(target_locales) != len(set(target_locales)):
        raise StateError("Target locales must be unique")
    if risk_level not in SUPPORTED_RISKS:
        raise StateError(f"Unsupported risk level: {risk_level}")
    if not deliverables or any(item not in SUPPORTED_DELIVERABLES for item in deliverables):
        raise StateError("Choose at least one supported deliverable")
    if risk_level == "R3" and not medical_enabled:
        raise StateError("R3 projects must enable the medical safety workflow")
    if medical_enabled:
        if not jurisdiction:
            raise StateError("Medical projects require a jurisdiction")
        if not evidence_cutoff:
            raise StateError("Medical projects require an evidence cutoff date")
        if not revalidate_before_export:
            raise StateError("Medical projects require a revalidation-before-export date")

    features = {
        "assessments": _resolve_feature(profile, "assessments", assessments),
        "illustrations": _resolve_feature(profile, "illustrations", illustrations),
        "diagrams": _resolve_feature(profile, "diagrams", diagrams),
        "visual_density": profile["defaults"]["visual_density"],
    }
    approvals = [
        _approval_record("project-brief", now),
        _approval_record("architecture", now),
    ]
    if features["illustrations"]:
        approvals.append(_approval_record("character-bible", now))
    if target_locales:
        approvals.append(_approval_record("source-content-lock", now))
    if risk_level == "R3":
        approvals.append(_approval_record("medical-expert-signoff", now))
    approvals.append(_approval_record("final-proof", now))

    state: dict[str, Any] = {
        "$schema": PROJECT_SCHEMA_URI,
        "schema_version": SCHEMA_VERSION,
        "project_id": resolved_project_id,
        "title": title.strip(),
        "subtitle": subtitle.strip(),
        "audience": audience.strip(),
        "reader_outcome": reader_outcome.strip(),
        "profile": profile_id,
        "source_locale": source_locale,
        "target_locales": target_locales,
        "risk_level": risk_level,
        "medical": {
            "enabled": medical_enabled,
            "jurisdiction": jurisdiction,
            "evidence_cutoff": evidence_cutoff,
            "revalidate_before_export": revalidate_before_export,
        },
        "features": features,
        "deliverables": list(dict.fromkeys(deliverables)),
        "artifact_registry": {
            "root": ".nam-book/artifacts",
            "slots": _artifact_slots(catalog),
            "entries": [],
        },
        "route": {},
        "approvals": approvals,
        "staleness": [],
        "provenance": [],
        "created_at": now,
        "updated_at": now,
    }
    state["route"] = build_route(state, catalog, profile, "start")
    return state


def approval_index(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["approval_id"]: item for item in state.get("approvals", [])}


def artifact_index(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["artifact_id"]: item
        for item in state.get("artifact_registry", {}).get("entries", [])
    }


def approval_is_current(
    state: dict[str, Any], approval: dict[str, Any] | None
) -> bool:
    if not approval or approval.get("status") != "approved":
        return False
    artifacts = artifact_index(state)
    for basis in approval.get("basis", []):
        source = artifacts.get(basis.get("artifact_id"))
        if source is None:
            return False
        if source.get("sha256") != basis.get("sha256"):
            return False
    return True


def _select_skills(
    state: dict[str, Any], profile: dict[str, Any], intent: str
) -> set[str]:
    if intent not in SUPPORTED_INTENTS:
        raise StateError(f"Unsupported intent: {intent}")
    if intent in {"start", "resume"}:
        selected = set(profile["start_skills"])
    elif intent == "revise":
        selected = {"nam-book-edit", "nam-book-validate", "nam-book-publish"}
    elif intent == "audit":
        selected = {"nam-book-validate"}
    elif intent == "illustrate":
        selected = {"nam-book-visuals", "nam-book-validate"}
    elif intent == "localize":
        selected = {"nam-book-localize", "nam-book-validate", "nam-book-publish"}
    else:
        selected = {"nam-book-validate", "nam-book-publish"}

    features = state["features"]
    if not features["assessments"]:
        selected.discard("nam-book-assess")
    if not features["illustrations"]:
        selected.discard("nam-book-illustrate")
    elif intent == "illustrate":
        selected.add("nam-book-illustrate")
    if not features["diagrams"]:
        selected.discard("nam-book-diagram")
    elif intent == "illustrate":
        selected.add("nam-book-diagram")
    if not features["illustrations"] and not features["diagrams"]:
        selected.discard("nam-book-visuals")
    if state["target_locales"] and intent in {"start", "resume", "localize"}:
        selected.add("nam-book-localize")
    if state["medical"]["enabled"] or state["risk_level"] in {"R2", "R3"}:
        selected.add("nam-book-research")
        selected.add("nam-book-validate")

    for record in state.get("staleness", []):
        if record.get("resolved_at") is None:
            selected.update(
                set(record.get("invalidates_nodes", []))
                - set(record.get("resolved_nodes", []))
            )
    return selected


def _descendants(node_id: str, route: dict[str, Any]) -> set[str]:
    children: dict[str, set[str]] = {}
    for edge in route.get("edges", []):
        children.setdefault(edge["from"], set()).add(edge["to"])
    seen: set[str] = set()
    frontier = list(children.get(node_id, set()))
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        frontier.extend(children.get(current, set()))
    return seen


def build_route(
    state: dict[str, Any],
    catalog: dict[str, Any],
    profile: dict[str, Any],
    intent: str,
) -> dict[str, Any]:
    selected = _select_skills(state, profile, intent)
    index = catalog_index(catalog)
    specialized_nodes = {
        node["id"]
        for capability in catalog["capabilities"]
        for node in capability.get("route_nodes", [])
    }
    unknown = selected - set(index) - specialized_nodes
    if unknown:
        raise StateError(f"Route references unknown skills: {sorted(unknown)}")

    previous = {
        item.get("id"): item
        for item in state.get("route", {}).get("nodes", [])
        if isinstance(item, dict)
    }
    open_stale = {
        node
        for record in state.get("staleness", [])
        if record.get("resolved_at") is None
        for node in record.get("invalidates_nodes", [])
        if node not in set(record.get("resolved_nodes", []))
    }
    approvals = approval_index(state)
    planned: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for capability in catalog["capabilities"]:
        skill = capability["skill"]
        route_nodes = capability.get("route_nodes") or [
            {
                "id": skill,
                "operation": "run",
                "purpose": capability["purpose"],
                "depends_on": capability["depends_on"],
                "approval_gates": capability["approval_gates"],
                "produces": [
                    item["kind"]
                    for item in capability["produces"]
                    if item.get("required", True)
                ],
            }
        ]
        if skill in selected:
            included = route_nodes
        else:
            included = [item for item in route_nodes if item["id"] in selected]
        planned.extend((capability, item) for item in included)

    included_ids = {spec["id"] for _, spec in planned}
    nodes: list[dict[str, Any]] = []
    for capability, spec in planned:
        skill = capability["skill"]
        node_id = spec["id"]
        dependencies = [item for item in spec["depends_on"] if item in included_ids]
        if node_id == "nam-book-validate" and "nam-book-research" in included_ids:
            dependencies.append("nam-book-research")
        if node_id == "nam-book-validate" and "nam-book-publish-proof" in included_ids:
            dependencies.append("nam-book-publish-proof")
        gates = list(spec["approval_gates"])
        if node_id == "nam-book-publish-release" and state["risk_level"] == "R3":
            gates.append("medical-expert-signoff")
        prior_status = previous.get(node_id, {}).get("status", "pending")
        if node_id in open_stale or skill in open_stale:
            status = "stale"
        elif prior_status == "complete":
            status = "complete"
        elif prior_status in {"running", "failed"}:
            status = prior_status
        else:
            status = "pending"
        nodes.append(
            {
                "id": node_id,
                "skill": skill,
                "operation": spec["operation"],
                "purpose": spec["purpose"],
                "depends_on": list(dict.fromkeys(dependencies)),
                "required_approvals": list(dict.fromkeys(gates)),
                "produces": list(spec["produces"]),
                "status": status,
                "blockers": [],
            }
        )

    ordered_nodes: list[dict[str, Any]] = []
    remaining = list(nodes)
    emitted: set[str] = set()
    while remaining:
        ready = [
            node for node in remaining if set(node["depends_on"]).issubset(emitted)
        ]
        if not ready:
            raise StateError("Selected route contains a dependency cycle")
        for node in ready:
            ordered_nodes.append(node)
            emitted.add(node["id"])
            remaining.remove(node)
    nodes = ordered_nodes

    route = {
        "route_version": ROUTE_VERSION,
        "generated_at": utc_now(),
        "intent": intent,
        "nodes": nodes,
        "edges": [
            {"from": dependency, "to": node["id"]}
            for node in nodes
            for dependency in node["depends_on"]
        ],
    }
    refresh_route_statuses(state, route, approvals)
    return route


def refresh_route_statuses(
    state: dict[str, Any],
    route: dict[str, Any] | None = None,
    approvals: dict[str, dict[str, Any]] | None = None,
) -> None:
    target = route or state["route"]
    approval_map = approvals or approval_index(state)
    nodes = {item["id"]: item for item in target.get("nodes", [])}
    changed = True
    while changed:
        changed = False
        for node in nodes.values():
            if node["status"] in {"complete", "running", "failed", "skipped"}:
                continue
            blockers: list[str] = []
            for dependency in node["depends_on"]:
                if nodes.get(dependency, {}).get("status") != "complete":
                    blockers.append(f"dependency:{dependency}")
            for approval_id in node["required_approvals"]:
                if not approval_is_current(state, approval_map.get(approval_id)):
                    blockers.append(f"approval:{approval_id}")
            next_status = (
                "stale"
                if node["status"] == "stale"
                else ("blocked" if blockers else "ready")
            )
            if node["status"] != next_status or node["blockers"] != blockers:
                node["status"] = next_status
                node["blockers"] = blockers
                changed = True


def ensure_relative_path(value: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise StateError(f"Artifact path must stay inside the project: {value}")


def project_root_from_state_path(state_path: Path) -> Path:
    resolved = state_path.resolve()
    if resolved.parent.name == ".nam-book":
        return resolved.parent.parent
    return resolved.parent


def resolve_artifact_path(state_path: Path, relative_path: str) -> Path:
    ensure_relative_path(relative_path)
    project_root = project_root_from_state_path(state_path).resolve()
    candidate = (project_root / relative_path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise StateError(f"Artifact path escapes the project: {relative_path}") from exc
    return candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError as exc:
        raise StateError(f"Artifact file not found: {path}") from exc
    return digest.hexdigest()


def sha256_path(path: Path) -> tuple[str, str]:
    """Hash a file or a directory tree without depending on archive metadata."""
    if path.is_symlink():
        raise StateError(f"Artifact paths may not be symbolic links: {path}")
    if path.is_file():
        return sha256_file(path), "sha256-file"
    if not path.exists():
        raise StateError(f"Artifact path not found: {path}")
    if not path.is_dir():
        raise StateError(f"Artifact path is neither a file nor directory: {path}")

    digest = hashlib.sha256()
    for item in sorted(path.rglob("*"), key=lambda value: value.relative_to(path).as_posix()):
        if item.is_symlink():
            raise StateError(f"Artifact trees may not contain symbolic links: {item}")
        relative = item.relative_to(path).as_posix().encode("utf-8")
        if item.is_dir():
            digest.update(b"D\0" + relative + b"\0")
            continue
        digest.update(b"F\0" + relative + b"\0")
        digest.update(str(item.stat().st_size).encode("ascii") + b"\0")
        with item.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest(), "sha256-tree-v1"


def snapshot_artifact_revision(
    state_path: Path,
    artifact_id: str,
    revision: int,
    source: Path,
    expected_hash: str,
) -> str:
    """Copy registered bytes to a new immutable history path."""
    project_root = project_root_from_state_path(state_path).resolve()
    suffix = source.suffix if source.is_file() else ""
    relative = Path(".nam-book") / "history" / artifact_id / f"r{revision:04d}{suffix}"
    target = resolve_artifact_path(state_path, relative.as_posix())
    if target.exists():
        raise StateError(f"Revision snapshot already exists; refusing overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    if source.is_file():
        descriptor, temporary_name = tempfile.mkstemp(
            dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
        )
        os.close(descriptor)
        try:
            shutil.copy2(source, temporary_name)
            os.replace(temporary_name, target)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
    else:
        staging_root = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}."))
        staging = staging_root / "snapshot"
        try:
            shutil.copytree(source, staging)
            os.replace(staging, target)
        finally:
            if staging_root.exists():
                shutil.rmtree(staging_root)

    snapshot_hash, _ = sha256_path(target)
    if snapshot_hash != expected_hash:
        raise StateError("Revision snapshot hash differs from the registered artifact")
    return target.relative_to(project_root).as_posix()


def _next_stale_id(state: dict[str, Any]) -> str:
    numbers = []
    for record in state.get("staleness", []):
        match = re.fullmatch(r"stale-(\d+)", str(record.get("stale_id", "")))
        if match:
            numbers.append(int(match.group(1)))
    return f"stale-{max(numbers, default=0) + 1:04d}"


def mark_artifact_stale(
    state: dict[str, Any], artifact_id: str, reason: str, *, high_risk_change: bool = False
) -> set[str]:
    artifacts = artifact_index(state)
    if artifact_id not in artifacts:
        raise StateError(f"Unknown artifact id: {artifact_id}")
    existing = next(
        (
            item
            for item in state.get("staleness", [])
            if item.get("artifact_id") == artifact_id and item.get("resolved_at") is None
        ),
        None,
    )
    producer = artifacts[artifact_id].get(
        "producer_node", artifacts[artifact_id]["produced_by"]
    )
    invalidated = {producer}
    invalidated.update(_descendants(producer, state["route"]))
    for candidate in artifacts.values():
        if any(item["artifact_id"] == artifact_id for item in candidate.get("inputs", [])):
            invalidated.add(candidate.get("producer_node", candidate["produced_by"]))
    if high_risk_change or (
        state["risk_level"] in {"R2", "R3"}
        and artifacts[artifact_id]["produced_by"]
        in {"nam-book-edit", "nam-book-localize"}
    ):
        invalidated.update({"nam-book-research", "nam-book-validate"})
    invalidated &= {item["id"] for item in state["route"]["nodes"]}

    artifacts[artifact_id]["status"] = "stale"
    for node in state["route"]["nodes"]:
        if node["id"] in invalidated and node["status"] != "skipped":
            node["status"] = "stale"
            node["blockers"] = [f"stale-artifact:{artifact_id}"]
    for approval in state.get("approvals", []):
        if approval["status"] == "approved" and any(
            item["artifact_id"] == artifact_id for item in approval.get("basis", [])
        ):
            approval["status"] = "expired"
            approval["note"] = f"Expired because {artifact_id} changed."
    if existing:
        existing["reason"] = reason
        existing["detected_at"] = utc_now()
        existing["invalidates_nodes"] = sorted(invalidated)
        existing["resolved_nodes"] = []
    else:
        state["staleness"].append(
            {
                "stale_id": _next_stale_id(state),
                "artifact_id": artifact_id,
                "reason": reason,
                "detected_at": utc_now(),
                "invalidates_nodes": sorted(invalidated),
                "resolved_nodes": [],
                "resolved_at": None,
            }
        )
    return invalidated


def refresh_file_staleness(state: dict[str, Any], state_path: Path) -> list[str]:
    changed: list[str] = []
    for artifact in list(artifact_index(state).values()):
        path = resolve_artifact_path(state_path, artifact["path"])
        if not path.exists():
            mark_artifact_stale(state, artifact["artifact_id"], "Artifact file is missing")
            changed.append(artifact["artifact_id"])
            continue
        current_hash, current_kind = sha256_path(path)
        if current_kind != artifact.get("hash_kind", "sha256-file"):
            mark_artifact_stale(
                state,
                artifact["artifact_id"],
                "Artifact changed between a file and a directory tree",
            )
            changed.append(artifact["artifact_id"])
            continue
        if current_hash != artifact["sha256"]:
            mark_artifact_stale(
                state,
                artifact["artifact_id"],
                "Artifact bytes differ from the registered SHA-256",
            )
            changed.append(artifact["artifact_id"])
    return changed


def register_artifact(
    state: dict[str, Any],
    state_path: Path,
    *,
    artifact_id: str,
    kind: str,
    relative_path: str,
    produced_by: str,
    status: str,
    locale: str,
    chapter_id: str | None,
    input_ids: list[str],
    claim_ids: list[str],
    source_ids: list[str],
    origin: str,
    creator: str,
    license_name: str,
    source_url: str,
    notice_path: str,
    producer_node: str | None = None,
    operation: str = "run",
    objective_ids: list[str] | None = None,
    figure_ids: list[str] | None = None,
    item_ids: list[str] | None = None,
    semantic_block_ids: list[str] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    if not ARTIFACT_ID_RE.fullmatch(artifact_id):
        raise StateError("Artifact id must use lowercase letters, digits, dots, underscores, or hyphens")
    if status not in ARTIFACT_STATUSES - {"stale"}:
        raise StateError(f"Unsupported artifact status: {status}")
    if locale not in SUPPORTED_LOCALES:
        raise StateError(f"Unsupported artifact locale: {locale}")
    if not ID_RE.fullmatch(operation):
        raise StateError("Artifact operation must be lowercase kebab-case")
    ensure_relative_path(relative_path)
    slots = state["artifact_registry"]["slots"]
    if kind not in slots:
        raise StateError(f"Unknown artifact kind: {kind}")
    if slots[kind]["produced_by"] != produced_by:
        raise StateError(
            f"Artifact kind {kind} must be produced by {slots[kind]['produced_by']}"
        )
    if operation not in slots[kind].get("operations", ["run"]):
        raise StateError(
            f"Artifact kind {kind} does not support operation {operation}"
        )
    candidate_nodes = [
        item
        for item in state["route"]["nodes"]
        if item["skill"] == produced_by
        and item.get("operation", "run") == operation
    ]
    resolved_producer_node = producer_node or (
        candidate_nodes[0]["id"] if len(candidate_nodes) == 1 else produced_by
    )
    matching_nodes = [
        item for item in candidate_nodes if item["id"] == resolved_producer_node
    ]
    if not matching_nodes:
        raise StateError(
            f"Producer node {resolved_producer_node} ({operation}) is not in the current route"
        )
    expected_path = slots[kind]["path"]
    replacements = {
        "{artifact_id}": artifact_id,
        "{locale}": locale,
        "{chapter_id}": chapter_id or "",
    }
    for marker, value in replacements.items():
        expected_path = expected_path.replace(marker, value)
    if not chapter_id and "{chapter_id}" in slots[kind]["path"]:
        raise StateError(f"Artifact kind {kind} requires --chapter-id")
    if relative_path != expected_path:
        raise StateError(f"Artifact kind {kind} must use registry path {expected_path}")

    path = resolve_artifact_path(state_path, relative_path)
    digest, hash_kind = sha256_path(path)
    artifacts = artifact_index(state)
    duplicate_paths = [
        item["artifact_id"]
        for item in artifacts.values()
        if item["artifact_id"] != artifact_id and item.get("path") == relative_path
    ]
    if duplicate_paths:
        raise StateError(
            f"Registry path is already owned by artifact {duplicate_paths[0]}"
        )
    missing_inputs = [item for item in input_ids if item not in artifacts]
    if missing_inputs:
        raise StateError(f"Unknown input artifact ids: {missing_inputs}")
    normalized_blockers = list(dict.fromkeys(blockers or []))
    if status == "blocked" and not normalized_blockers:
        raise StateError("A blocked artifact must record at least one blocker")
    if normalized_blockers and status != "blocked":
        raise StateError("An artifact with open blockers must use blocked status")
    if not origin.strip() or not creator.strip() or not license_name.strip():
        raise StateError("Artifact provenance requires origin, creator, and license")
    inputs = [
        {
            "artifact_id": item,
            "revision": artifacts[item]["revision"],
            "sha256": artifacts[item]["sha256"],
        }
        for item in input_ids
    ]
    now = utc_now()
    previous = artifacts.get(artifact_id)
    if previous:
        identity = {
            "kind": kind,
            "path": relative_path,
            "project_id": state["project_id"],
            "chapter_id": chapter_id,
            "locale": locale,
            "produced_by": produced_by,
            "producer_node": resolved_producer_node,
            "operation": operation,
        }
        changed_identity = [
            field for field, value in identity.items() if previous.get(field) != value
        ]
        if changed_identity:
            raise StateError(
                "An artifact id has immutable identity fields; use a new id to change "
                + ", ".join(changed_identity)
            )

    producer = matching_nodes[0]
    if producer.get("status") != "running":
        raise StateError(
            f"Producer node {resolved_producer_node} must be running before registration"
        )
    for dependency in producer.get("depends_on", []):
        dependency_node = next(
            (item for item in state["route"]["nodes"] if item["id"] == dependency),
            None,
        )
        if dependency_node and dependency_node.get("status") != "complete":
            raise StateError(
                f"Producer node {resolved_producer_node} has incomplete dependency {dependency}"
            )
    approvals = approval_index(state)
    for gate in producer.get("required_approvals", []):
        if not approval_is_current(state, approvals.get(gate)):
            raise StateError(
                f"Producer node {resolved_producer_node} lacks approval {gate}"
            )

    if (
        state["risk_level"] == "R3"
        and status in {"approved", "locked"}
        and not approval_is_current(state, approvals.get("medical-expert-signoff"))
    ):
        raise StateError(
            "R3 artifacts cannot be approved or locked before medical expert signoff"
        )

    if operation == "proof" and status != "review":
        raise StateError("Publication proofs must be registered with review status")
    if operation == "release":
        if status not in {"approved", "locked"}:
            raise StateError("Publication releases must be approved or locked")
        proof_approval = approvals.get("final-proof", {})
        proof_basis = {
            item["artifact_id"]
            for item in proof_approval.get("basis", [])
            if artifacts.get(item["artifact_id"], {}).get("operation") == "proof"
        }
        if not proof_basis or not proof_basis.issubset(set(input_ids)):
            raise StateError(
                "A release must cite every proof artifact in the final-proof approval basis"
            )

    if previous and previous["sha256"] != digest:
        already_open = any(
            item.get("artifact_id") == artifact_id
            and item.get("resolved_at") is None
            for item in state.get("staleness", [])
        )
        if not already_open:
            mark_artifact_stale(
                state,
                artifact_id,
                "A new artifact revision replaced the registered bytes",
                high_risk_change=(
                    state["risk_level"] in {"R2", "R3"}
                    and produced_by in {"nam-book-edit", "nam-book-localize"}
                ),
            )
            producer["status"] = "running"
            producer["blockers"] = []
        now = utc_now()

    next_revision = (previous["revision"] + 1) if previous else 1
    snapshot_path = snapshot_artifact_revision(
        state_path, artifact_id, next_revision, path, digest
    )
    normalized_claim_ids = list(dict.fromkeys(claim_ids))
    normalized_source_ids = list(dict.fromkeys(source_ids))
    normalized_objective_ids = list(dict.fromkeys(objective_ids or []))
    normalized_figure_ids = list(dict.fromkeys(figure_ids or []))
    normalized_item_ids = list(dict.fromkeys(item_ids or []))
    normalized_semantic_block_ids = list(dict.fromkeys(semantic_block_ids or []))
    provenance = {
        "origin": origin,
        "creator": creator,
        "license": license_name,
        "source_url": source_url,
        "notice_path": notice_path,
    }
    revision_record = {
        "revision": next_revision,
        "sha256": digest,
        "hash_kind": hash_kind,
        "snapshot_path": snapshot_path,
        "status": status,
        "inputs": inputs,
        "claim_ids": normalized_claim_ids,
        "source_ids": normalized_source_ids,
        "objective_ids": normalized_objective_ids,
        "figure_ids": normalized_figure_ids,
        "item_ids": normalized_item_ids,
        "semantic_block_ids": normalized_semantic_block_ids,
        "blockers": normalized_blockers,
        "provenance": provenance,
        "registered_at": now,
    }
    revision_history = list(previous.get("revision_history", [])) if previous else []
    revision_history.append(revision_record)
    entry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "kind": kind,
        "path": relative_path,
        "project_id": state["project_id"],
        "chapter_id": chapter_id,
        "locale": locale,
        "produced_by": produced_by,
        "producer_node": resolved_producer_node,
        "operation": operation,
        "status": status,
        "revision": next_revision,
        "sha256": digest,
        "hash_kind": hash_kind,
        "inputs": inputs,
        "claim_ids": normalized_claim_ids,
        "source_ids": normalized_source_ids,
        "objective_ids": normalized_objective_ids,
        "figure_ids": normalized_figure_ids,
        "item_ids": normalized_item_ids,
        "semantic_block_ids": normalized_semantic_block_ids,
        "blockers": normalized_blockers,
        "provenance": provenance,
        "revision_history": revision_history,
        "created_at": previous["created_at"] if previous else now,
        "updated_at": now,
    }
    entries = state["artifact_registry"]["entries"]
    if previous:
        entries[entries.index(previous)] = entry
    else:
        entries.append(entry)
    state["updated_at"] = now
    return entry


def decide_approval(
    state: dict[str, Any],
    *,
    approval_id: str,
    decision: str,
    decided_by: str,
    basis_ids: list[str],
    note: str,
    reviewer_role: str = "",
    reviewer_credentials: str = "",
) -> dict[str, Any]:
    approvals = approval_index(state)
    if approval_id not in approvals:
        raise StateError(f"Unknown approval id: {approval_id}")
    if decision not in {"approved", "rejected"}:
        raise StateError("Approval decision must be approved or rejected")
    if not decided_by.strip():
        raise StateError("The decision maker must be recorded")
    artifacts = artifact_index(state)
    missing = [item for item in basis_ids if item not in artifacts]
    if missing:
        raise StateError(f"Unknown approval basis artifacts: {missing}")
    unusable = [
        item
        for item in basis_ids
        if artifacts[item].get("status") in {"stale", "blocked"}
        or artifacts[item].get("blockers")
    ]
    if decision == "approved" and unusable:
        raise StateError(f"Approval basis contains stale or blocked artifacts: {unusable}")

    if decision == "approved" and approval_id in {
        "medical-expert-signoff",
        "final-proof",
    }:
        validation = next(
            (
                item
                for item in state["route"]["nodes"]
                if item["id"] == "nam-book-validate"
            ),
            None,
        )
        if validation is None or validation.get("status") != "complete":
            raise StateError(f"{approval_id} requires completed final validation")

    if decision == "approved" and approval_id == "medical-expert-signoff":
        if state["risk_level"] != "R3" or not state["medical"].get("enabled"):
            raise StateError("Medical expert signoff is reserved for R3 medical projects")
        if not reviewer_role.strip() or not reviewer_credentials.strip():
            raise StateError(
                "Medical expert signoff requires the reviewer's role and credentials"
            )
        basis_kinds = {artifacts[item]["kind"] for item in basis_ids}
        required_kinds = {"evidence_ledger", "validation_report"}
        if not required_kinds.issubset(basis_kinds):
            raise StateError(
                "Medical expert signoff must bind the evidence ledger and validation report"
            )

    if decision == "approved" and approval_id == "final-proof":
        proof_ids = [
            item for item in basis_ids if artifacts[item].get("operation") == "proof"
        ]
        if not proof_ids:
            raise StateError("Final-proof approval must bind a registered proof artifact")
        if state["risk_level"] == "R3":
            expert = approvals.get("medical-expert-signoff", {})
            if not approval_is_current(state, expert):
                raise StateError("R3 final-proof approval requires medical expert signoff")

    approval = approvals[approval_id]
    approval.update(
        {
            "status": decision,
            "decided_at": utc_now(),
            "decided_by": decided_by.strip(),
            "reviewer_role": reviewer_role.strip() or None,
            "reviewer_credentials": reviewer_credentials.strip() or None,
            "note": note,
            "basis": [
                {
                    "artifact_id": item,
                    "revision": artifacts[item]["revision"],
                    "sha256": artifacts[item]["sha256"],
                }
                for item in basis_ids
            ],
        }
    )
    state["updated_at"] = utc_now()
    refresh_route_statuses(state)
    return approval


def transition_node(state: dict[str, Any], target: str, status: str) -> dict[str, Any]:
    if status not in {"ready", "running", "complete", "failed", "blocked", "stale"}:
        raise StateError(f"Unsupported node transition target: {status}")
    refresh_route_statuses(state)
    node = next(
        (item for item in state["route"]["nodes"] if item["id"] == target), None
    )
    if node is None:
        candidates = [
            item for item in state["route"]["nodes"] if item["skill"] == target
        ]
        if len(candidates) > 1:
            raise StateError(
                f"Skill {target} has multiple route nodes; use the exact node id"
            )
        node = candidates[0] if candidates else None
    if node is None:
        raise StateError(f"Node is not in the current route: {target}")
    node_id = node["id"]
    if status in {"running", "complete"}:
        live_blockers: list[str] = []
        for dependency in node["depends_on"]:
            dependency_node = next(
                (
                    item
                    for item in state["route"]["nodes"]
                    if item["id"] == dependency
                ),
                None,
            )
            if dependency_node and dependency_node["status"] != "complete":
                live_blockers.append(f"dependency:{dependency}")
        for gate in node["required_approvals"]:
            if not approval_is_current(state, approval_index(state).get(gate)):
                live_blockers.append(f"approval:{gate}")
        if live_blockers:
            raise StateError(f"Node {node_id} is blocked by {live_blockers}")
    if status == "complete":
        outputs = [
            item
            for item in state["artifact_registry"]["entries"]
            if item.get("producer_node", item["produced_by"]) == node_id
            and item.get("operation", "run") == node.get("operation", "run")
            and item["status"] not in {"stale", "blocked"}
        ]
        output_kinds = {item["kind"] for item in outputs}
        missing_kinds = set(node["produces"]) - output_kinds
        if missing_kinds:
            raise StateError(
                f"Node {node_id} lacks registered outputs {sorted(missing_kinds)}"
            )
        stale_outputs = [
            item
            for item in state["artifact_registry"]["entries"]
            if item.get("producer_node", item["produced_by"]) == node_id
            and item.get("status") == "stale"
        ]
        if stale_outputs:
            raise StateError(
                f"Node {node_id} still has stale artifacts: "
                f"{[item['artifact_id'] for item in stale_outputs]}"
            )
        for record in state.get("staleness", []):
            if (
                record.get("resolved_at") is not None
                or node_id not in record.get("invalidates_nodes", [])
                or node_id in record.get("resolved_nodes", [])
            ):
                continue
            fresh_kinds = {
                item["kind"]
                for item in outputs
                if item.get("updated_at", "") >= record.get("detected_at", "")
            }
            missing_refresh = set(node["produces"]) - fresh_kinds
            if missing_refresh:
                raise StateError(
                    f"Node {node_id} has not regenerated outputs after staleness: "
                    f"{sorted(missing_refresh)}"
                )
    node["status"] = status
    node["blockers"] = [] if status in {"ready", "running", "complete"} else node["blockers"]
    state["updated_at"] = utc_now()
    if status == "complete":
        for record in state.get("staleness", []):
            if (
                record.get("resolved_at") is None
                and node_id in record.get("invalidates_nodes", [])
            ):
                resolved = set(record.get("resolved_nodes", []))
                resolved.add(node_id)
                record["resolved_nodes"] = sorted(resolved)
                if resolved.issuperset(set(record.get("invalidates_nodes", []))):
                    record["resolved_at"] = utc_now()
    refresh_route_statuses(state)
    return node


def _parse_date(value: Any, field: str, errors: list[str]) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        errors.append(f"{field} must be an ISO date (YYYY-MM-DD)")
        return None


def _topological_errors(route: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = route.get("nodes", [])
    ids = [item.get("id") for item in nodes if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        errors.append("Route node ids must be unique")
    known = set(ids)
    indegree = {item: 0 for item in known}
    children = {item: [] for item in known}
    for node in nodes:
        for dependency in node.get("depends_on", []):
            if dependency not in known:
                errors.append(f"Route node {node.get('id')} has unknown dependency {dependency}")
                continue
            indegree[node["id"]] += 1
            children[dependency].append(node["id"])
    frontier = [item for item, degree in indegree.items() if degree == 0]
    visited = 0
    while frontier:
        current = frontier.pop()
        visited += 1
        for child in children[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                frontier.append(child)
    if visited != len(known):
        errors.append("Route dependencies contain a cycle")
    return errors


def validate_state(
    state: dict[str, Any], state_path: Path, *, root: Path | None = None
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    base = root or repository_root()

    required = {
        "$schema",
        "schema_version",
        "project_id",
        "title",
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
        "provenance",
        "created_at",
        "updated_at",
    }
    missing = sorted(required - set(state))
    if missing:
        errors.append(f"Missing top-level fields: {missing}")
        return errors, warnings
    if state["schema_version"] != SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {state['schema_version']}")
    if state["$schema"] != PROJECT_SCHEMA_URI:
        if state["$schema"] in LEGACY_PROJECT_SCHEMA_URIS:
            warnings.append("Legacy $schema URI will upgrade on the next state write")
        else:
            errors.append("$schema must use the public raw repository URL")
    if not ID_RE.fullmatch(str(state["project_id"])):
        errors.append("project_id must be lowercase kebab-case")
    if state["profile"] not in SUPPORTED_PROFILES:
        errors.append(f"Unsupported profile: {state['profile']}")
    else:
        try:
            load_profile(state["profile"], base)
        except StateError as exc:
            errors.append(str(exc))
    if state["source_locale"] not in SUPPORTED_LOCALES:
        errors.append(f"Unsupported source_locale: {state['source_locale']}")
    targets = state["target_locales"]
    if not isinstance(targets, list) or any(item not in SUPPORTED_LOCALES for item in targets):
        errors.append("target_locales must contain only en-US or id-ID")
    elif state["source_locale"] in targets or len(targets) != len(set(targets)):
        errors.append("target_locales must be unique and exclude source_locale")
    if state["risk_level"] not in SUPPORTED_RISKS:
        errors.append(f"Unsupported risk_level: {state['risk_level']}")
    if state["risk_level"] == "R3" and not state.get("medical", {}).get("enabled"):
        errors.append("R3 projects must enable the medical safety workflow")
    if not isinstance(state["deliverables"], list) or not state["deliverables"]:
        errors.append("deliverables must be a non-empty list")
    elif any(item not in SUPPORTED_DELIVERABLES for item in state["deliverables"]):
        errors.append("deliverables contains an unsupported format")

    medical = state["medical"]
    cutoff = _parse_date(medical.get("evidence_cutoff"), "medical.evidence_cutoff", errors)
    revalidate = _parse_date(
        medical.get("revalidate_before_export"),
        "medical.revalidate_before_export",
        errors,
    )
    if medical.get("enabled"):
        if not medical.get("jurisdiction"):
            errors.append("Medical projects require medical.jurisdiction")
        if cutoff is None:
            errors.append("Medical projects require medical.evidence_cutoff")
        if revalidate is None:
            errors.append("Medical projects require medical.revalidate_before_export")
        if cutoff and revalidate and revalidate < cutoff:
            errors.append("Medical revalidation date cannot precede the evidence cutoff")
        if revalidate and date.today() > revalidate:
            warnings.append("Medical evidence is past its revalidation-before-export date")

    registry = state["artifact_registry"]
    try:
        ensure_relative_path(registry["root"])
    except (KeyError, StateError) as exc:
        errors.append(str(exc))
    slots = registry.get("slots", {})
    if not isinstance(slots, dict):
        errors.append("artifact_registry.slots must be an object")
        slots = {}
    for kind, slot in slots.items():
        try:
            ensure_relative_path(slot["path"])
        except (KeyError, StateError) as exc:
            errors.append(f"Invalid slot {kind}: {exc}")
        operations = slot.get("operations")
        if not isinstance(operations, list) or not operations:
            errors.append(f"Invalid slot {kind}: operations must be a non-empty list")

    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        errors.append("artifact_registry.entries must be a list")
        entries = []
    ids = [item.get("artifact_id") for item in entries if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        errors.append("Artifact ids must be unique")
    artifacts = artifact_index(state)
    for artifact in entries:
        artifact_id = artifact.get("artifact_id", "<unknown>")
        if not ARTIFACT_ID_RE.fullmatch(str(artifact_id)):
            errors.append(f"Invalid artifact id: {artifact_id}")
        if artifact.get("kind") not in slots:
            errors.append(f"Artifact {artifact_id} has unknown kind {artifact.get('kind')}")
        if artifact.get("status") not in ARTIFACT_STATUSES:
            errors.append(f"Artifact {artifact_id} has invalid status")
        if artifact.get("locale") not in SUPPORTED_LOCALES:
            errors.append(f"Artifact {artifact_id} has invalid locale")
        if not ID_RE.fullmatch(str(artifact.get("producer_node", ""))):
            errors.append(f"Artifact {artifact_id} has invalid producer_node")
        if not ID_RE.fullmatch(str(artifact.get("operation", ""))):
            errors.append(f"Artifact {artifact_id} has invalid operation")
        slot = slots.get(artifact.get("kind"), {})
        if artifact.get("operation") not in slot.get("operations", []):
            errors.append(f"Artifact {artifact_id} operation is not allowed by its slot")
        if not HASH_RE.fullmatch(str(artifact.get("sha256", ""))):
            errors.append(f"Artifact {artifact_id} has invalid SHA-256")
        if artifact.get("hash_kind") not in {"sha256-file", "sha256-tree-v1"}:
            errors.append(f"Artifact {artifact_id} has invalid hash_kind")
        if artifact.get("status") == "blocked" and not artifact.get("blockers"):
            errors.append(f"Blocked artifact {artifact_id} has no recorded blocker")
        if artifact.get("blockers") and artifact.get("status") != "blocked":
            errors.append(
                f"Artifact {artifact_id} has open blockers but is not blocked"
            )
        for field in (
            "claim_ids",
            "source_ids",
            "objective_ids",
            "figure_ids",
            "item_ids",
            "semantic_block_ids",
        ):
            values = artifact.get(field)
            if (
                not isinstance(values, list)
                or any(not isinstance(value, str) or not value for value in values)
                or len(values) != len(set(values))
            ):
                errors.append(f"Artifact {artifact_id} has invalid {field}")
        provenance = artifact.get("provenance")
        if not isinstance(provenance, dict) or any(
            not str(provenance.get(field, "")).strip()
            for field in ("origin", "creator", "license")
        ):
            errors.append(f"Artifact {artifact_id} has incomplete provenance")
        try:
            resolve_artifact_path(state_path, artifact["path"])
        except (KeyError, StateError) as exc:
            errors.append(f"Artifact {artifact_id}: {exc}")
        for item in artifact.get("inputs", []):
            source = artifacts.get(item.get("artifact_id"))
            if source is None:
                errors.append(f"Artifact {artifact_id} has unknown input {item.get('artifact_id')}")
            elif source["sha256"] != item.get("sha256") and artifact.get(
                "status"
            ) != "stale":
                errors.append(
                    f"Artifact {artifact_id} is stale because input {source['artifact_id']} changed"
                )
        history = artifact.get("revision_history")
        if not isinstance(history, list) or not history:
            errors.append(f"Artifact {artifact_id} has no revision history")
        else:
            revisions = [item.get("revision") for item in history]
            if revisions != list(range(1, len(history) + 1)):
                errors.append(f"Artifact {artifact_id} revision history is not contiguous")
            if artifact.get("revision") != len(history):
                errors.append(f"Artifact {artifact_id} current revision does not match history")
            latest = history[-1]
            if (
                latest.get("sha256") != artifact.get("sha256")
                or latest.get("hash_kind") != artifact.get("hash_kind")
            ):
                errors.append(f"Artifact {artifact_id} current hash differs from history")
            for revision in history:
                try:
                    snapshot = resolve_artifact_path(
                        state_path, revision["snapshot_path"]
                    )
                    snapshot_hash, snapshot_kind = sha256_path(snapshot)
                    if (
                        snapshot_hash != revision.get("sha256")
                        or snapshot_kind != revision.get("hash_kind")
                    ):
                        errors.append(
                            f"Artifact {artifact_id} revision {revision.get('revision')} snapshot hash differs"
                        )
                except (KeyError, StateError) as exc:
                    errors.append(
                        f"Artifact {artifact_id} revision {revision.get('revision')}: {exc}"
                    )

    approvals = state.get("approvals", [])
    approval_ids = [item.get("approval_id") for item in approvals]
    if len(approval_ids) != len(set(approval_ids)):
        errors.append("Approval ids must be unique")
    for approval in approvals:
        if approval.get("status") not in APPROVAL_STATUSES:
            errors.append(f"Approval {approval.get('approval_id')} has invalid status")
        if approval.get("status") == "approved" and not approval.get("decided_by"):
            errors.append(f"Approval {approval.get('approval_id')} has no decision maker")
        for basis in approval.get("basis", []):
            source = artifacts.get(basis.get("artifact_id"))
            if source is None:
                errors.append(
                    f"Approval {approval.get('approval_id')} has unknown basis artifact"
                )
            elif source["sha256"] != basis.get("sha256") and approval.get(
                "status"
            ) == "approved":
                errors.append(
                    f"Approval {approval.get('approval_id')} must expire because its basis changed"
                )
        if (
            approval.get("approval_id") == "medical-expert-signoff"
            and approval.get("status") == "approved"
        ):
            if not approval.get("reviewer_role") or not approval.get(
                "reviewer_credentials"
            ):
                errors.append("Medical expert signoff lacks role or credentials")
            basis_kinds = {
                artifacts[item["artifact_id"]]["kind"]
                for item in approval.get("basis", [])
                if item.get("artifact_id") in artifacts
            }
            if not {"evidence_ledger", "validation_report"}.issubset(basis_kinds):
                errors.append(
                    "Medical expert signoff must bind evidence and validation artifacts"
                )
        if (
            approval.get("approval_id") == "final-proof"
            and approval.get("status") == "approved"
        ):
            proof_basis = [
                item
                for item in approval.get("basis", [])
                if artifacts.get(item.get("artifact_id"), {}).get("operation")
                == "proof"
            ]
            if not proof_basis:
                errors.append("Final-proof approval must bind a proof artifact")

    if state["risk_level"] == "R3" and not approval_is_current(
        state, approval_index(state).get("medical-expert-signoff")
    ):
        prematurely_approved = [
            item["artifact_id"]
            for item in entries
            if item.get("status") in {"approved", "locked"}
        ]
        if prematurely_approved:
            errors.append(
                "R3 artifacts were approved before medical expert signoff: "
                f"{prematurely_approved}"
            )

    route = state["route"]
    if route.get("intent") not in SUPPORTED_INTENTS:
        errors.append(f"Unsupported route intent: {route.get('intent')}")
    errors.extend(_topological_errors(route))
    known_approvals = set(approval_ids)
    catalog = load_catalog(base)
    known_skills = set(catalog_index(catalog))
    for node in route.get("nodes", []):
        if node.get("skill") not in known_skills:
            errors.append(f"Route contains unknown skill {node.get('skill')}")
        if node.get("status") not in NODE_STATUSES:
            errors.append(f"Route node {node.get('id')} has invalid status")
        if not ID_RE.fullmatch(str(node.get("operation", ""))):
            errors.append(f"Route node {node.get('id')} has invalid operation")
        missing_gates = set(node.get("required_approvals", [])) - known_approvals
        if missing_gates:
            errors.append(f"Route node {node.get('id')} has unknown approvals {sorted(missing_gates)}")
        if node.get("status") in {"ready", "running", "complete"}:
            for dependency in node.get("depends_on", []):
                dependency_node = next(
                    (item for item in route["nodes"] if item["id"] == dependency), None
                )
                if dependency_node and dependency_node["status"] != "complete":
                    errors.append(
                        f"Route node {node.get('id')} advanced before dependency {dependency}"
                    )
            for gate in node.get("required_approvals", []):
                if not approval_is_current(state, approval_index(state).get(gate)):
                    errors.append(f"Route node {node.get('id')} advanced before approval {gate}")

    proof_node = next(
        (item for item in route.get("nodes", []) if item.get("id") == "nam-book-publish-proof"),
        None,
    )
    release_node = next(
        (item for item in route.get("nodes", []) if item.get("id") == "nam-book-publish-release"),
        None,
    )
    validation_node = next(
        (item for item in route.get("nodes", []) if item.get("id") == "nam-book-validate"),
        None,
    )
    final_proof_approval = approval_index(state).get("final-proof", {})
    if approval_is_current(state, final_proof_approval):
        if validation_node is None or validation_node.get("status") != "complete":
            errors.append("Final-proof approval predates completed final validation")
        if state["risk_level"] == "R3" and not approval_is_current(
            state, approval_index(state).get("medical-expert-signoff")
        ):
            errors.append("R3 final-proof approval predates medical expert signoff")
    if proof_node and "final-proof" in proof_node.get("required_approvals", []):
        errors.append("Proof builds must not require final-proof approval")
    if release_node:
        if "nam-book-validate" not in release_node.get("depends_on", []):
            errors.append("Publication release must depend on final validation")
        if "final-proof" not in release_node.get("required_approvals", []):
            errors.append("Publication release must require final-proof approval")
        if not proof_node:
            errors.append("Publication release route must include a proof build")
        if validation_node and "nam-book-publish-proof" not in validation_node.get(
            "depends_on", []
        ):
            errors.append("Release validation must inspect the generated proof")

    if state["risk_level"] == "R3":
        required_gates = {"medical-expert-signoff", "final-proof"}
        if not required_gates.issubset(set(approval_ids)):
            errors.append("R3 projects require expert-signoff and final-proof approvals")
        if release_node and "medical-expert-signoff" not in release_node.get(
            "required_approvals", []
        ):
            errors.append("R3 publication release must require medical-expert-signoff")
    if state["risk_level"] in {"R2", "R3"}:
        route_skills = {item.get("skill") for item in route.get("nodes", [])}
        if "nam-book-research" not in route_skills or "nam-book-validate" not in route_skills:
            errors.append("R2/R3 routes require research and validation")

    open_stale = [item for item in state.get("staleness", []) if item.get("resolved_at") is None]
    for record in open_stale:
        if record.get("artifact_id") not in artifacts:
            errors.append(f"Staleness record {record.get('stale_id')} has an unknown artifact")
        resolved_nodes = set(record.get("resolved_nodes", []))
        unknown_resolved = resolved_nodes - set(record.get("invalidates_nodes", []))
        if unknown_resolved:
            errors.append(
                f"Staleness record {record.get('stale_id')} resolves unknown nodes "
                f"{sorted(unknown_resolved)}"
            )
        for node_id in record.get("invalidates_nodes", []):
            node = next((item for item in route.get("nodes", []) if item.get("id") == node_id), None)
            if node_id in resolved_nodes:
                if node and node.get("status") != "complete":
                    errors.append(f"Resolved stale node {node_id} is not complete")
            elif node and node.get("status") not in {
                "stale",
                "blocked",
                "failed",
                "running",
            }:
                errors.append(f"Stale dependency did not invalidate route node {node_id}")

    if not state.get("audience"):
        warnings.append("Audience is empty; architecture should not start until it is resolved")
    if not state.get("reader_outcome"):
        warnings.append("Reader outcome is empty; architecture should not start until it is resolved")
    return errors, warnings


def save_state(state: dict[str, Any], state_path: Path) -> None:
    state["$schema"] = PROJECT_SCHEMA_URI
    state["updated_at"] = utc_now()
    atomic_write_json(state_path, state)


def format_route_receipt(route: dict[str, Any]) -> str:
    lines = [f"Intent: {route['intent']}", "Route:"]
    for node in route["nodes"]:
        dependencies = ", ".join(node["depends_on"]) or "none"
        blockers = ", ".join(node["blockers"]) or "none"
        lines.append(
            f"- {node['id']} ({node['operation']}): {node['status']} | "
            f"depends on: {dependencies} | blockers: {blockers}"
        )
    ready = [
        item["id"]
        for item in route["nodes"]
        if item["status"] in {"ready", "stale"} and not item["blockers"]
    ]
    lines.append(f"Actionable now: {', '.join(ready) if ready else 'none'}")
    return "\n".join(lines)


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))
