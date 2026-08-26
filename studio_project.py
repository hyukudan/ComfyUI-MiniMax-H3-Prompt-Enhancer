# SPDX-License-Identifier: GPL-3.0-only
"""Prompt Studio v3 aggregate and authoritative reference compilation."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping

try:
    from .reference_director import build_reference_project, reference_context_for_project
except ImportError:  # Direct module imports in tests and standalone tooling.
    from reference_director import build_reference_project, reference_context_for_project


STUDIO_PROJECT_SCHEMA_VERSION = 3
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MEDIA_LIMITS = {"picture": 9, "video": 3, "audio": 3}
MEDIA_TYPES = tuple(MEDIA_LIMITS)
SHOT_REFERENCE_ROLES = {
    "identity_reinforcement", "appearance", "environment_view", "scale", "placement",
    "continuity", "lighting", "composition", "performance", "voice", "exact_dialogue",
    "soundtrack", "camera_transfer",
}


def empty_studio_project() -> dict[str, Any]:
    """Return a useful, neutral v3 project without invented creative content."""
    return {
        "schemaVersion": STUDIO_PROJECT_SCHEMA_VERSION,
        "project": {
            "name": "Untitled project",
            "mode": "auto",
            "timingMode": "auto",
            "look": {
                "creativeTreatment": {"schemaVersion": 2},
                "cinematography": {"schemaVersion": 2},
            },
        },
        "files": [],
        "subjects": [],
        "environments": [],
        "generations": [{"id": "g1", "order": 1}],
        "shots": [],
        "links": [],
    }


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_object(value: str | Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return empty_studio_project()
    try:
        parsed = json.loads(value) if isinstance(value, str) else deepcopy(dict(value))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError(f"Studio Project JSON is invalid: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Studio Project must be a JSON object.")
    return parsed


def _id(value: Any, field: str, issues: list[str]) -> str:
    result = str(value or "")
    if not ID_PATTERN.fullmatch(result):
        issues.append(f"{field} must be a stable ID using letters, numbers, dot, underscore or hyphen.")
    return result


def _unique_ids(items: Any, field: str, issues: list[str]) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        issues.append(f"{field} must be an array.")
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"{field}[{index}] must be an object.")
            continue
        item_id = _id(item.get("id"), f"{field}[{index}].id", issues)
        if item_id in seen:
            issues.append(f"{field} contains duplicate ID {item_id!r}.")
        seen.add(item_id)
        result.append(deepcopy(item))
    return result


def parse_studio_project(value: str | Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate the v3 aggregate without compiling runtime slot assignments."""
    project = _json_object(value)
    issues: list[str] = []
    if project.get("schemaVersion") != STUDIO_PROJECT_SCHEMA_VERSION:
        issues.append(f"Studio Project schemaVersion must be {STUDIO_PROJECT_SCHEMA_VERSION}.")
    settings = project.get("project")
    if not isinstance(settings, dict):
        issues.append("project must be an object.")
        settings = {}
    mode = settings.get("mode", "auto")
    if mode not in {"auto", "t2va", "i2va", "fl2va", "l2va", "ref2va", "chained_multishot"}:
        issues.append(f"project.mode {mode!r} is unsupported.")
    timing = settings.get("timingMode", "auto")
    if timing not in {"auto", "exact"}:
        issues.append("project.timingMode must be auto or exact.")

    files = _unique_ids(project.get("files"), "files", issues)
    subjects = _unique_ids(project.get("subjects"), "subjects", issues)
    environments = _unique_ids(project.get("environments"), "environments", issues)
    generations = _unique_ids(project.get("generations"), "generations", issues)
    shots = _unique_ids(project.get("shots"), "shots", issues)
    links = _unique_ids(project.get("links"), "links", issues)
    if not generations:
        issues.append("generations must contain at least one Generation.")
    if len(shots) > 64:
        issues.append("shots may not contain more than 64 Shots.")

    file_ids = {item.get("id") for item in files}
    subject_ids = {item.get("id") for item in subjects}
    environment_ids = {item.get("id") for item in environments}
    generation_ids = {item.get("id") for item in generations}
    shot_ids = {item.get("id") for item in shots}
    for index, file in enumerate(files):
        if file.get("type") not in MEDIA_TYPES:
            issues.append(f"files[{index}].type must be picture, video or audio.")
        if not str(file.get("name", "")).strip():
            issues.append(f"files[{index}].name is required.")
        source = file.get("source")
        if source is not None and not isinstance(source, dict):
            issues.append(f"files[{index}].source must be an object.")
    for index, subject in enumerate(subjects):
        if not str(subject.get("name", "")).strip():
            issues.append(f"subjects[{index}].name is required.")
        for file_id in subject.get("identityFileIds", []):
            if file_id not in file_ids:
                issues.append(f"Subject {subject.get('id')!r} references missing identity file {file_id!r}.")
        voice_id = subject.get("defaultVoiceFileId")
        if voice_id and voice_id not in file_ids:
            issues.append(f"Subject {subject.get('id')!r} references missing voice file {voice_id!r}.")
    for environment in environments:
        for view in environment.get("views", []):
            if view.get("fileId") not in file_ids:
                issues.append(f"Environment {environment.get('id')!r} view references missing file {view.get('fileId')!r}.")
    for shot in shots:
        if shot.get("generationId", generations[0].get("id") if generations else "") not in generation_ids:
            issues.append(f"Shot {shot.get('id')!r} references an unknown Generation.")
        for cast in shot.get("cast", []):
            if cast.get("subjectId") not in subject_ids:
                issues.append(f"Shot {shot.get('id')!r} references missing Subject {cast.get('subjectId')!r}.")
        environment = shot.get("environment") or {}
        if environment.get("environmentId") and environment.get("environmentId") not in environment_ids:
            issues.append(f"Shot {shot.get('id')!r} references a missing Environment.")
    for generation in generations:
        for root in (generation.get("activation") or {}).get("roots", []):
            kind, root_id = root.get("kind"), root.get("id")
            valid = (
                kind == "subject" and root_id in subject_ids
                or kind == "environment" and root_id in environment_ids
                or kind in {"asset", "file"} and root_id in file_ids
            )
            if not valid:
                issues.append(f"Generation {generation.get('id')!r} has an invalid activation root {kind}:{root_id}.")
    for link in links:
        if link.get("fileId") not in file_ids:
            issues.append(f"Link {link.get('id')!r} references missing file {link.get('fileId')!r}.")
        owner = link.get("owner") or {}
        valid_owner = (
            owner.get("kind") == "subject" and owner.get("id") in subject_ids
            or owner.get("kind") == "environment" and owner.get("id") in environment_ids
            or owner.get("kind") == "shot" and owner.get("id") in shot_ids
            or owner.get("kind") == "project" and owner.get("id") in {None, "", "project"}
        )
        if not valid_owner:
            issues.append(f"Link {link.get('id')!r} has an invalid owner.")

    canonical = _canonical(project)
    return {
        "valid": not issues,
        "issues": issues,
        "value": project,
        "canonicalJson": canonical,
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def _legacy_file(file: Mapping[str, Any]) -> dict[str, Any]:
    result = {"id": file["id"], "type": file["type"], "name": str(file.get("name") or file["id"])}
    for source, target in (
        ("available", "available"), ("durationSeconds", "durationSeconds"),
        ("audioMode", "audioMode"), ("description", "description"),
        ("analysis", "analysis"), ("transcript", "transcript"),
        ("cameraTransfer", "cameraTransfer"),
    ):
        if file.get(source) not in (None, "", [], {}):
            result[target] = deepcopy(file[source])
    return result


def _legacy_subject(subject: Mapping[str, Any], index: int) -> dict[str, Any]:
    states = deepcopy(subject.get("appearanceStates") or [{"id": "base", "name": "Base", "controls": []}])
    base_id = str(subject.get("baseAppearanceStateId") or states[0]["id"])
    return {
        "id": subject["id"],
        "h3Index": int(subject.get("h3Index") or index + 1),
        "name": str(subject.get("name") or subject["id"]),
        "description": str(subject.get("description") or "Unspecified stable identity."),
        "identityAssetIds": list(subject.get("identityFileIds") or []),
        **({"defaultVoiceAssetId": subject["defaultVoiceFileId"]} if subject.get("defaultVoiceFileId") else {}),
        "baseAppearanceStateId": base_id,
        "appearanceStates": states,
    }


def _legacy_environment(environment: Mapping[str, Any]) -> dict[str, Any]:
    states = deepcopy(environment.get("states") or [{"id": "base", "name": "Base"}])
    views = []
    for index, view in enumerate(environment.get("views") or []):
        views.append({
            "id": str(view.get("id") or f"view{index + 1}"),
            "name": str(view.get("name") or f"View {index + 1}"),
            "role": view.get("role") if view.get("role") in {"overview", "alternate", "detail", "lighting", "custom"} else "overview",
            "assetId": view.get("fileId"),
            **({"description": view["description"]} if view.get("description") else {}),
        })
    return {
        "id": environment["id"],
        "name": str(environment.get("name") or environment["id"]),
        "permanent": deepcopy(environment.get("permanent") or {}),
        "views": views,
        "defaultStateId": str(environment.get("defaultStateId") or states[0]["id"]),
        "states": states,
    }


def _shot_uses(shot: Mapping[str, Any], links: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    uses: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    raw = [*shot.get("referenceBindings", []), *(
        link for link in links if (link.get("owner") or {}).get("kind") == "shot"
        and (link.get("owner") or {}).get("id") == shot.get("id")
    )]
    for item in raw:
        file_id = item.get("fileId") or item.get("assetId")
        role = item.get("role", "continuity")
        if role not in SHOT_REFERENCE_ROLES:
            continue
        targets = list(item.get("targetIds") or [])
        target = item.get("target") or {}
        if target.get("id") and target.get("id") not in targets:
            targets.append(target["id"])
        signature = (file_id, role, tuple(targets), tuple(item.get("cameraAspects") or []))
        if not file_id or signature in seen:
            continue
        seen.add(signature)
        use = {"assetId": file_id, "role": role}
        if targets:
            use["targetIds"] = targets
        if role == "camera_transfer":
            use["cameraAspects"] = list(item.get("cameraAspects") or ["motion"])
        if item.get("note"):
            use["note"] = str(item["note"])
        uses.append(use)
    return uses


def _legacy_shot(shot: Mapping[str, Any], timing_mode: str, links: list[Mapping[str, Any]]) -> dict[str, Any]:
    result = {
        "id": shot["id"],
        "generationId": str(shot.get("generationId") or "g1"),
        "action": str(shot.get("action") or ""),
    }
    if timing_mode == "exact":
        result["durationSeconds"] = float(shot.get("durationSeconds") or 1.0)
    cast = shot.get("cast", shot.get("subjects", []))
    if cast:
        result["subjects"] = [{
            "subjectId": item.get("subjectId"),
            "presence": item.get("presence") if item.get("presence") in {"present", "enters", "exits", "absent"} else "present",
            **({"blocking": item["blocking"]} if item.get("blocking") else {}),
        } for item in cast]
        result["subjectPresenceComplete"] = bool(shot.get("subjectPresenceComplete", True))
    environment = shot.get("environment")
    if isinstance(environment, dict) and environment.get("environmentId"):
        result["environment"] = {"environmentId": environment["environmentId"]}
        view_ids = list(environment.get("viewIds") or ([] if not environment.get("viewId") else [environment["viewId"]]))
        if view_ids:
            result["environment"]["viewIds"] = view_ids
    uses = _shot_uses(shot, links)
    if uses:
        result["referenceUses"] = uses
    for key in (
        "openingState", "transitionIn", "cutContext", "actionBeats", "scaleRelationships",
        "staging", "cameraStart", "cameraEnd", "cameraPath", "appearanceTransitions",
        "environmentTransitions",
    ):
        if shot.get(key) not in (None, "", [], {}):
            result[key] = deepcopy(shot[key])
    return result


def _active_file_ids(
    generation: Mapping[str, Any],
    shots: list[Mapping[str, Any]],
    subjects: list[Mapping[str, Any]],
    environments: list[Mapping[str, Any]],
    links: list[Mapping[str, Any]],
) -> list[str]:
    generation_id = str(generation.get("id") or "g1")
    present_subjects: set[str] = set()
    used_environments: set[str] = set()
    explicit_files: list[str] = []
    ordered: list[str] = []
    seen: set[str] = set()

    def add(file_id: Any) -> None:
        if file_id and file_id not in seen:
            seen.add(str(file_id)); ordered.append(str(file_id))

    selected = [shot for shot in shots if shot.get("generationId", "g1") == generation_id]
    for root in (generation.get("activation") or {}).get("roots", []):
        if root.get("kind") == "subject":
            present_subjects.add(root.get("id"))
        elif root.get("kind") == "environment":
            used_environments.add(root.get("id"))
        elif root.get("kind") in {"asset", "file"} and root.get("id"):
            explicit_files.append(str(root["id"]))
    shot_use_ids: list[str] = []
    for shot in selected:
        for cast in shot.get("cast", shot.get("subjects", [])):
            if cast.get("presence", "present") != "absent":
                present_subjects.add(cast.get("subjectId"))
        environment = shot.get("environment") or {}
        if environment.get("environmentId"):
            used_environments.add(environment["environmentId"])
        for use in _shot_uses(shot, links):
            if use.get("assetId"):
                shot_use_ids.append(use["assetId"])
    for subject in subjects:
        if subject.get("id") not in present_subjects:
            continue
        for file_id in subject.get("identityFileIds", []):
            add(file_id)
        add(subject.get("defaultVoiceFileId"))
    for environment in environments:
        if environment.get("id") not in used_environments:
            continue
        chosen = {
            view_id for shot in selected
            for view_id in ((shot.get("environment") or {}).get("viewIds") or ([] if not (shot.get("environment") or {}).get("viewId") else [(shot.get("environment") or {}).get("viewId")]))
            if (shot.get("environment") or {}).get("environmentId") == environment.get("id")
        }
        for view in environment.get("views", []):
            if not chosen or view.get("id") in chosen:
                add(view.get("fileId"))
    for link in links:
        owner = link.get("owner") or {}
        scope = link.get("scope") or {}
        if scope.get("generationIds") and generation_id not in scope["generationIds"]:
            continue
        if owner.get("kind") == "subject" and owner.get("id") in present_subjects:
            add(link.get("fileId"))
        elif owner.get("kind") == "environment" and owner.get("id") in used_environments:
            add(link.get("fileId"))
        elif owner.get("kind") == "project":
            add(link.get("fileId"))
    for file_id in explicit_files:
        add(file_id)
    for file_id in shot_use_ids:
        add(file_id)
    return ordered


def compile_studio_project(value: str | Mapping[str, Any] | None, generation_id: str = "") -> dict[str, Any]:
    """Compile v3 authoring state to legacy runtime contracts and one physical input map."""
    parsed = parse_studio_project(value)
    if not parsed["valid"]:
        raise ValueError("Studio Project is invalid: " + " ".join(parsed["issues"]))
    value = parsed["value"]
    settings = value["project"]
    files = value["files"]
    subjects = value["subjects"]
    environments = value["environments"]
    generations = sorted(value["generations"], key=lambda item: int(item.get("order", 0)))
    shots = value["shots"]
    links = value["links"]
    files_by_id = {item["id"]: item for item in files}
    legacy_subjects = [_legacy_subject(item, index) for index, item in enumerate(subjects)]
    legacy_environments = [_legacy_environment(item) for item in environments]
    compiled_generations = []
    quotas: dict[str, dict[str, int]] = {}
    issues: list[str] = []
    for shot in shots:
        if not str(shot.get("action") or "").strip():
            issues.append(f"Shot {shot['id']} needs a visible action before generation.")
    for generation in generations:
        active_ids = _active_file_ids(generation, shots, subjects, environments, links)
        counters = {kind: 0 for kind in MEDIA_TYPES}
        bindings = []
        for file_id in active_ids:
            file = files_by_id[file_id]
            kind = file["type"]
            counters[kind] += 1
            binding = {"assetId": file_id, "slotIndex": counters[kind]}
            if kind == "video" and file.get("audioMode") in {"paired", "alone"}:
                counters["audio"] += 1
                binding["soundtrackSlotIndex"] = counters["audio"]
            bindings.append(binding)
        for kind, maximum in MEDIA_LIMITS.items():
            if counters[kind] > maximum:
                issues.append(f"Generation {generation['id']} uses {counters[kind]} {kind} files; H3 allows {maximum}.")
        quotas[generation["id"]] = {**counters, "files": len(active_ids)}
        compiled_generations.append({
            "id": generation["id"], "order": int(generation.get("order", len(compiled_generations) + 1)),
            "activation": {"mode": "auto"}, "bindings": bindings,
            "subjectStates": deepcopy(generation.get("subjectStates") or []),
            "environmentStates": deepcopy(generation.get("environmentStates") or []),
        })
    if issues:
        raise ValueError(" ".join(issues))
    media_project = {
        "schemaVersion": 2,
        "mode": settings.get("mode", "auto"),
        "assets": [_legacy_file(item) for item in files],
        "subjects": legacy_subjects,
        "environments": legacy_environments,
        "generations": compiled_generations,
    }
    timing_mode = settings.get("timingMode", "auto")
    shot_plan = {
        "schemaVersion": 2,
        "timingMode": timing_mode,
        "shots": [_legacy_shot(item, timing_mode, links) for item in shots],
    }
    look = settings.get("look") or {}
    creative = deepcopy(look.get("creativeTreatment") or {"schemaVersion": 2})
    cinematography = deepcopy(look.get("cinematography") or {"schemaVersion": 2})
    creative["schemaVersion"] = 2
    cinematography["schemaVersion"] = 2
    sources = {
        file["id"]: deepcopy(file["source"])
        for file in files if isinstance(file.get("source"), dict)
    }
    director = {"format": "minimax-h3-reference-director", "formatVersion": 1, "sources": sources}
    reference_project = build_reference_project(director, media_project, shot_plan)
    if reference_project.get("issues"):
        raise ValueError("Studio Project references are not ready: " + " ".join(reference_project["issues"]))
    selected = generation_id if generation_id else generations[0]["id"]
    if selected not in reference_project["inputsByGeneration"]:
        raise ValueError(f"Unknown Studio Project generation {selected!r}.")
    context = reference_context_for_project(reference_project, selected)
    input_map = {
        item["assetId"] + (":soundtrack" if item.get("role") == "video_soundtrack" else ""): item["label"]
        for item in reference_project["inputsByGeneration"][selected]
    }
    payload = {
        "schemaVersion": STUDIO_PROJECT_SCHEMA_VERSION,
        "projectDigest": parsed["digest"],
        "generationId": selected,
        "mediaProject": media_project,
        "shotPlan": shot_plan,
        "creativeTreatment": creative,
        "cinematography": cinematography,
        "referenceDirector": director,
        "referenceProject": reference_project,
        "referenceContext": context,
        "inputMap": input_map,
        "quotas": quotas,
        "issues": [],
    }
    payload["digest"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return payload
