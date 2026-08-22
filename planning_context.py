# SPDX-License-Identifier: GPL-3.0-only
"""Compile media-project and shot-plan v2 into one deterministic planning context."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

try:
    from .camera_authority import (
        claims_from_shot_plan,
        claims_from_video_references,
        resolve_camera_authority,
    )
    from .creative_treatments import parse_shot_plan
    from .continuity_state import resolve_state
    from .diagnostics import (
        DiagnosticCode,
        DiagnosticCollector,
        DiagnosticLocation,
        DiagnosticResource,
        LocationScope,
        ResourceKind,
    )
    from .media_manifest import manifest_context_for_generation, parse_media_project
    from .reference_resolution import resolve_generation_references
except ImportError:
    from camera_authority import (
        claims_from_shot_plan,
        claims_from_video_references,
        resolve_camera_authority,
    )
    from creative_treatments import parse_shot_plan
    from continuity_state import resolve_state
    from diagnostics import (
        DiagnosticCode,
        DiagnosticCollector,
        DiagnosticLocation,
        DiagnosticResource,
        LocationScope,
        ResourceKind,
    )
    from media_manifest import manifest_context_for_generation, parse_media_project
    from reference_resolution import resolve_generation_references


PLANNING_CONTEXT_SCHEMA_VERSION = 1


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _resource(kind: ResourceKind, resource_id: str) -> tuple[DiagnosticResource, ...]:
    return (DiagnosticResource(kind, resource_id),)


def _location(generation_id: str, shot: Mapping[str, Any], shot_index: int, field: str) -> DiagnosticLocation:
    return DiagnosticLocation(
        LocationScope.CONFIGURATION,
        f"shot_plan_json.shots.{shot_index}.{field}",
        generation_id=generation_id,
        shot_id=str(shot["id"]),
        shot_index=shot_index,
    )


def _emit_unknown(
    collector: DiagnosticCollector,
    generation_id: str,
    shot: Mapping[str, Any],
    shot_index: int,
    field: str,
    kind: ResourceKind,
    resource_id: str,
    message: str,
) -> None:
    collector.emit(
        DiagnosticCode.ACTIVATION_UNKNOWN_RESOURCE,
        message,
        _location(generation_id, shot, shot_index, field),
        related=_resource(kind, resource_id),
        data={"resourceKind": kind.value, "resourceId": resource_id},
    )


def _target_refs(frame: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for field in ("primaryTarget", "secondaryTarget", "foregroundTarget"):
        target = frame.get(field)
        if isinstance(target, Mapping) and target.get("kind") != "text":
            found.append((str(target.get("kind", "")), str(target.get("id", "")), field))
    focus = frame.get("focus")
    if isinstance(focus, Mapping):
        for field in ("primaryTarget", "secondaryTarget"):
            target = focus.get(field)
            if isinstance(target, Mapping) and target.get("kind") != "text":
                found.append((str(target.get("kind", "")), str(target.get("id", "")), f"focus.{field}"))
    return found


def _path_target_refs(path: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    target = path.get("anchorTarget")
    if isinstance(target, Mapping) and target.get("kind") != "text":
        return [(str(target.get("kind", "")), str(target.get("id", "")), "anchorTarget")]
    return []


def _appearance_source_roots(subject: Mapping[str, Any], state_id: str) -> list[dict[str, str]]:
    states = {state["id"]: state for state in subject["appearanceStates"]}
    roots: list[dict[str, str]] = []
    seen: set[str] = set()
    current = state_id
    while current and current in states and current not in seen:
        seen.add(current)
        state = states[current]
        source = state.get("source", {})
        if source.get("mode") == "asset":
            roots.append({"kind": "asset", "id": source["assetId"]})
        current = str(state.get("extends", ""))
    return roots


def _generation_initial_state(
    project: Mapping[str, Any],
    generation: Mapping[str, Any],
    previous_final: Mapping[str, Any] | None,
) -> dict[str, Any]:
    subjects = {subject["id"]: subject for subject in project["subjects"]}
    environments = {environment["id"]: environment for environment in project["environments"]}
    if previous_final is None:
        subject_states = {subject_id: item["baseAppearanceStateId"] for subject_id, item in subjects.items()}
        environment_states = {environment_id: item["defaultStateId"] for environment_id, item in environments.items()}
        views: dict[str, list[str]] = {}
    else:
        subject_states = dict(previous_final["subjects"])
        environment_states = dict(previous_final["environments"])
        views = {key: list(value) for key, value in previous_final["views"].items()}
    for selection in generation["subjectStates"]:
        subject_id = selection["subjectId"]
        if selection["policy"] != "carry":
            subject_states[subject_id] = selection["stateId"]
    for selection in generation["environmentStates"]:
        environment_id = selection["environmentId"]
        if selection["policy"] != "carry":
            environment_states[environment_id] = selection["stateId"]
        views[environment_id] = list(selection["viewIds"])
    payload = {"subjects": subject_states, "environments": environment_states, "views": views}
    payload["digest"] = _digest(payload)
    return payload


def _generation_entities(
    generation: Mapping[str, Any],
    shots: list[tuple[int, Mapping[str, Any]]],
    subjects: Mapping[str, Any],
    environments: Mapping[str, Any],
    assets: Mapping[str, Any],
) -> tuple[set[str], set[str], set[str], dict[str, set[str]]]:
    subject_ids = {
        item["id"] for item in generation["activation"].get("roots", ())
        if item["kind"] == "subject" and item["id"] in subjects
    }
    environment_ids = {
        item["id"] for item in generation["activation"].get("roots", ())
        if item["kind"] == "environment" and item["id"] in environments
    }
    asset_ids = {
        item["id"] for item in generation["activation"].get("roots", ())
        if item["kind"] == "asset" and item["id"] in assets
    }
    view_ids: dict[str, set[str]] = {}
    for _shot_index, shot in shots:
        for presence in shot.get("subjects", ()):
            if presence["presence"] != "absent":
                subject_ids.add(presence["subjectId"])
        for transition in shot.get("appearanceTransitions", ()):
            subject_ids.add(transition["subjectId"])
        environment = shot.get("environment")
        if environment:
            environment_id = environment["environmentId"]
            environment_ids.add(environment_id)
            view_ids.setdefault(environment_id, set()).update(environment.get("viewIds", ()))
        for transition in shot.get("environmentTransitions", ()):
            environment_ids.add(transition["environmentId"])
        for reference_use in shot.get("referenceUses", ()):
            asset_ids.add(reference_use["assetId"])
            for target_id in reference_use.get("targetIds", ()):
                if target_id in subjects:
                    subject_ids.add(target_id)
                elif target_id in environments:
                    environment_ids.add(target_id)
                elif target_id in assets:
                    asset_ids.add(target_id)
        for frame_name in ("cameraStart", "cameraEnd"):
            for kind, resource_id, _field in _target_refs(shot.get(frame_name, {})):
                if kind == "subject":
                    subject_ids.add(resource_id)
                elif kind == "environment":
                    environment_ids.add(resource_id)
                elif kind == "asset":
                    asset_ids.add(resource_id)
        for kind, resource_id, _field in _path_target_refs(shot.get("cameraPath", {})):
            if kind == "subject":
                subject_ids.add(resource_id)
            elif kind == "environment":
                environment_ids.add(resource_id)
            elif kind == "asset":
                asset_ids.add(resource_id)
    return subject_ids, environment_ids, asset_ids, view_ids


def _filtered_generation(
    generation: Mapping[str, Any],
    initial_state: Mapping[str, Any],
    subject_ids: set[str],
    environment_ids: set[str],
    view_ids: Mapping[str, set[str]],
) -> dict[str, Any]:
    filtered = dict(generation)
    filtered["subjectStates"] = []
    selections = {item["subjectId"]: item for item in generation["subjectStates"]}
    for subject_id in sorted(subject_ids):
        selection = dict(selections.get(subject_id, {"subjectId": subject_id, "policy": "carry"}))
        selection["resolvedStateId"] = initial_state["subjects"].get(subject_id)
        filtered["subjectStates"].append(selection)
    filtered["environmentStates"] = []
    selections = {item["environmentId"]: item for item in generation["environmentStates"]}
    for environment_id in sorted(environment_ids):
        selection = dict(selections.get(environment_id, {
            "environmentId": environment_id, "policy": "carry", "viewIds": [],
        }))
        selected_views = set(selection.get("viewIds", ())) | set(view_ids.get(environment_id, ()))
        selection["viewIds"] = sorted(selected_views)
        selection["resolvedStateId"] = initial_state["environments"].get(environment_id)
        filtered["environmentStates"].append(selection)
    return filtered


def _mode_anchor_roots(
    mode: str,
    generation: Mapping[str, Any],
    assets: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, str]]:
    required_slots = {"i2va": {1}, "l2va": {1}, "fl2va": {1, 2}}.get(mode, set())
    return [
        {"kind": "asset", "id": binding["assetId"]}
        for binding in generation["bindings"]
        if binding["slotIndex"] in required_slots
        and assets.get(binding["assetId"], {}).get("type") == "picture"
    ]


_RESOLUTION_CODES = {
    "reference.activation.unknown_resource": DiagnosticCode.ACTIVATION_UNKNOWN_RESOURCE,
    "reference.activation.required_excluded": DiagnosticCode.ACTIVATION_REQUIRED_EXCLUDED,
    "reference.binding.missing": DiagnosticCode.BINDING_MISSING,
    "reference.binding.duplicate_slot": DiagnosticCode.BINDING_DUPLICATE_SLOT,
    "reference.capacity.exceeded": DiagnosticCode.REFERENCE_CAPACITY_EXCEEDED,
}


def _collect_resolution_issues(
    collector: DiagnosticCollector,
    generation_id: str,
    issues: list[Mapping[str, Any]],
) -> None:
    for issue in issues:
        code = _RESOLUTION_CODES.get(str(issue.get("code")), DiagnosticCode.BINDING_TYPE_MISMATCH)
        data = dict(issue.get("data", {}))
        related: tuple[DiagnosticResource, ...] = ()
        if data.get("assetId"):
            related = _resource(ResourceKind.ASSET, str(data["assetId"]))
        elif data.get("kind") in {"asset", "subject", "environment"} and data.get("id"):
            related = _resource(ResourceKind(str(data["kind"])), str(data["id"]))
        collector.emit(
            code,
            str(issue.get("message", "Invalid generation reference configuration"))[:500],
            DiagnosticLocation(
                LocationScope.CONFIGURATION,
                str(issue.get("field", f"media_manifest.generations.{generation_id}")),
                generation_id=generation_id,
            ),
            related=related,
            data={"sourceCode": str(issue.get("code", "")), **data},
        )


def _validate_target(
    collector: DiagnosticCollector,
    target_kind: str,
    target_id: str,
    field: str,
    generation_id: str,
    shot: Mapping[str, Any],
    shot_index: int,
    subjects: Mapping[str, Any],
    environments: Mapping[str, Any],
    assets: Mapping[str, Any],
    presence: Mapping[str, str],
    active_environment_id: str | None,
    active_asset_ids: set[str],
) -> None:
    tables = {"subject": subjects, "environment": environments, "asset": assets}
    kinds = {"subject": ResourceKind.SUBJECT, "environment": ResourceKind.ENVIRONMENT, "asset": ResourceKind.ASSET}
    table = tables.get(target_kind, {})
    if target_id not in table:
        _emit_unknown(
            collector, generation_id, shot, shot_index, field,
            kinds.get(target_kind, ResourceKind.ASSET), target_id,
            f"Shot {shot['id']!r} targets unknown {target_kind or 'resource'} {target_id!r}.",
        )
        return
    active = (
        (target_kind == "subject" and presence.get(target_id) in {"present", "enters", "exits"})
        or (target_kind == "environment" and target_id == active_environment_id)
        or (target_kind == "asset" and target_id in active_asset_ids)
    )
    if not active:
        _emit_unknown(
            collector, generation_id, shot, shot_index, field,
            kinds[target_kind], target_id,
            f"Shot {shot['id']!r} targets {target_kind} {target_id!r}, but it is not active in that shot.",
        )


def _validate_shots_and_resolve_state(
    collector: DiagnosticCollector,
    generation_id: str,
    shots: list[tuple[int, Mapping[str, Any]]],
    generation_subject_ids: set[str],
    initial_state: Mapping[str, Any],
    subjects: Mapping[str, Mapping[str, Any]],
    environments: Mapping[str, Mapping[str, Any]],
    assets: Mapping[str, Mapping[str, Any]],
    active_asset_ids: set[str],
    input_map: Mapping[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    subject_states = dict(initial_state["subjects"])
    environment_states = dict(initial_state["environments"])
    views = {key: list(value) for key, value in initial_state["views"].items()}
    resolved_shots: list[dict[str, Any]] = []
    for shot_index, shot in shots:
        presence = {item["subjectId"]: item["presence"] for item in shot.get("subjects", ())}
        if shot.get("subjectPresenceComplete"):
            missing = sorted(generation_subject_ids - presence.keys())
            for subject_id in missing:
                _emit_unknown(
                    collector, generation_id, shot, shot_index, "subjects",
                    ResourceKind.SUBJECT, subject_id,
                    f"Shot {shot['id']!r} declares complete subject presence but omits active subject {subject_id!r}.",
                )
        for subject_id in presence:
            if subject_id not in subjects:
                _emit_unknown(
                    collector, generation_id, shot, shot_index, "subjects",
                    ResourceKind.SUBJECT, subject_id,
                    f"Shot {shot['id']!r} references unknown subject {subject_id!r}.",
                )
        environment = shot.get("environment") or {}
        active_environment_id = environment.get("environmentId")
        if active_environment_id and active_environment_id not in environments:
            _emit_unknown(
                collector, generation_id, shot, shot_index, "environment.environmentId",
                ResourceKind.ENVIRONMENT, active_environment_id,
                f"Shot {shot['id']!r} references unknown environment {active_environment_id!r}.",
            )
        elif active_environment_id:
            known_views = {view["id"] for view in environments[active_environment_id]["views"]}
            for view_id in environment.get("viewIds", ()):
                if view_id not in known_views:
                    _emit_unknown(
                        collector, generation_id, shot, shot_index, "environment.viewIds",
                        ResourceKind.ENVIRONMENT, active_environment_id,
                        f"Shot {shot['id']!r} selects unknown view {view_id!r} of environment {active_environment_id!r}.",
                    )
            if "viewIds" in environment:
                views[active_environment_id] = list(environment["viewIds"])

        before = {
            "subjects": dict(subject_states), "environments": dict(environment_states),
            "views": {key: list(value) for key, value in views.items()},
        }
        for transition_index, transition in enumerate(shot.get("appearanceTransitions", ())):
            subject_id = transition["subjectId"]
            field = f"appearanceTransitions.{transition_index}"
            subject = subjects.get(subject_id)
            if subject is None:
                _emit_unknown(
                    collector, generation_id, shot, shot_index, field,
                    ResourceKind.SUBJECT, subject_id,
                    f"Shot {shot['id']!r} transitions unknown subject {subject_id!r}.",
                )
                continue
            known_states = {state["id"] for state in subject["appearanceStates"]}
            if transition["fromStateId"] not in known_states or transition["toStateId"] not in known_states:
                collector.emit(
                    DiagnosticCode.APPEARANCE_TRANSITION_FROM_MISMATCH,
                    f"Shot {shot['id']!r} uses an unknown appearance state for subject {subject_id!r}.",
                    _location(generation_id, shot, shot_index, field),
                    related=_resource(ResourceKind.SUBJECT, subject_id),
                )
                continue
            current = subject_states.get(subject_id, subject["baseAppearanceStateId"])
            if transition["fromStateId"] != current:
                collector.emit(
                    DiagnosticCode.APPEARANCE_TRANSITION_FROM_MISMATCH,
                    f"Shot {shot['id']!r} expects subject {subject_id!r} in {transition['fromStateId']!r}, but resolved state is {current!r}.",
                    _location(generation_id, shot, shot_index, field + ".fromStateId"),
                    related=_resource(ResourceKind.SUBJECT, subject_id),
                    data={"expectedStateId": current, "authoredStateId": transition["fromStateId"]},
                )
            if presence.get(subject_id) == "absent":
                collector.emit(
                    DiagnosticCode.APPEARANCE_TRANSITION_SUBJECT_ABSENT,
                    f"Shot {shot['id']!r} transitions subject {subject_id!r} while that subject is absent.",
                    _location(generation_id, shot, shot_index, field),
                    related=_resource(ResourceKind.SUBJECT, subject_id),
                )
            subject_states[subject_id] = transition["toStateId"]

        for transition_index, transition in enumerate(shot.get("environmentTransitions", ())):
            environment_id = transition["environmentId"]
            field = f"environmentTransitions.{transition_index}"
            environment_item = environments.get(environment_id)
            if environment_item is None:
                _emit_unknown(
                    collector, generation_id, shot, shot_index, field,
                    ResourceKind.ENVIRONMENT, environment_id,
                    f"Shot {shot['id']!r} transitions unknown environment {environment_id!r}.",
                )
                continue
            current = environment_states.get(environment_id, environment_item["defaultStateId"])
            known_states = {state["id"] for state in environment_item["states"]}
            invalid = transition["fromStateId"] not in known_states or transition["toStateId"] not in known_states
            inactive = environment_id != active_environment_id
            if invalid or inactive or transition["fromStateId"] != current:
                collector.emit(
                    DiagnosticCode.ENVIRONMENT_TRANSITION_FROM_MISMATCH,
                    (
                        f"Shot {shot['id']!r} cannot transition environment {environment_id!r}: "
                        + ("it is not the active shot environment." if inactive else f"resolved state is {current!r}.")
                    ),
                    _location(generation_id, shot, shot_index, field),
                    related=_resource(ResourceKind.ENVIRONMENT, environment_id),
                    data={"expectedStateId": current, "authoredStateId": transition["fromStateId"]},
                )
            if not invalid and not inactive:
                environment_states[environment_id] = transition["toStateId"]

        for use_index, reference_use in enumerate(shot.get("referenceUses", ())):
            asset_id = reference_use["assetId"]
            field = f"referenceUses.{use_index}"
            asset = assets.get(asset_id)
            if asset is None:
                _emit_unknown(
                    collector, generation_id, shot, shot_index, field,
                    ResourceKind.ASSET, asset_id,
                    f"Shot {shot['id']!r} uses unknown asset {asset_id!r}.",
                )
                continue
            if asset_id not in active_asset_ids or asset_id not in input_map:
                collector.emit(
                    DiagnosticCode.BINDING_MISSING,
                    f"Shot {shot['id']!r} uses asset {asset_id!r}, but it is not active and bound in generation {generation_id!r}.",
                    _location(generation_id, shot, shot_index, field),
                    related=_resource(ResourceKind.ASSET, asset_id),
                )
            if reference_use["role"] == "camera_transfer":
                transfer = asset.get("cameraTransfer", {})
                requested = set(reference_use.get("cameraAspects", ()))
                allowed = set(transfer.get("aspects", ())) if isinstance(transfer, Mapping) else set()
                valid_transfer = (
                    asset.get("type") == "video"
                    and transfer.get("enabled") is True
                    and transfer.get("role") == "camera_reference"
                    and requested <= allowed
                )
                if not valid_transfer:
                    collector.emit(
                        DiagnosticCode.BINDING_TYPE_MISMATCH,
                        f"Shot {shot['id']!r} requests camera transfer {sorted(requested)} from asset {asset_id!r}, which does not declare that capability.",
                        _location(generation_id, shot, shot_index, field + ".cameraAspects"),
                        related=_resource(ResourceKind.ASSET, asset_id),
                        data={"requestedAspects": sorted(requested), "allowedAspects": sorted(allowed)},
                    )
            for target_id in reference_use.get("targetIds", ()):
                if target_id in subjects:
                    kind = "subject"
                elif target_id in environments:
                    kind = "environment"
                else:
                    kind = "asset"
                _validate_target(
                    collector, kind, target_id, field + ".targetIds", generation_id,
                    shot, shot_index, subjects, environments, assets, presence,
                    active_environment_id, active_asset_ids,
                )
        for frame_name in ("cameraStart", "cameraEnd"):
            for kind, target_id, target_field in _target_refs(shot.get(frame_name, {})):
                _validate_target(
                    collector, kind, target_id, f"{frame_name}.{target_field}", generation_id,
                    shot, shot_index, subjects, environments, assets, presence,
                    active_environment_id, active_asset_ids,
                )
        for kind, target_id, target_field in _path_target_refs(shot.get("cameraPath", {})):
            _validate_target(
                collector, kind, target_id, f"cameraPath.{target_field}", generation_id,
                shot, shot_index, subjects, environments, assets, presence,
                active_environment_id, active_asset_ids,
            )

        after = {
            "subjects": dict(subject_states), "environments": dict(environment_states),
            "views": {key: list(value) for key, value in views.items()},
        }
        before["digest"] = _digest(before)
        after["digest"] = _digest(after)
        resolved_shots.append({
            "id": shot["id"], "generationId": generation_id,
            "stateBefore": before, "stateAfter": after,
        })
    final_state = {
        "subjects": subject_states, "environments": environment_states, "views": views,
    }
    final_state["digest"] = _digest(final_state)
    return resolved_shots, final_state


def _structured_generation_context(
    media_context: str,
    shots: list[tuple[int, Mapping[str, Any]]],
    input_map: Mapping[str, str],
    subjects: Mapping[str, Mapping[str, Any]],
    environments: Mapping[str, Mapping[str, Any]],
) -> str:
    lines = [media_context] if media_context else []
    appearance_destinations = {
        (transition["subjectId"], transition["toStateId"])
        for _index, shot in shots for transition in shot.get("appearanceTransitions", ())
        if transition["subjectId"] in subjects
    }
    environment_destinations = {
        (transition["environmentId"], transition["toStateId"])
        for _index, shot in shots for transition in shot.get("environmentTransitions", ())
        if transition["environmentId"] in environments
    }
    if appearance_destinations or environment_destinations:
        lines.append("STATE DEFINITIONS USED BY EXPLICIT TRANSITIONS:")
    for subject_id, state_id in sorted(appearance_destinations):
        subject = subjects[subject_id]
        state = resolve_state(subject["appearanceStates"], state_id, "attributes")
        details = "; ".join(
            f"{key}: {value}" for key, value in state["attributes"].items()
            if value not in (None, "", [], {})
        )
        source_labels = [
            input_map[source["assetId"]] for source in state["sources"]
            if source.get("mode") == "asset" and source.get("assetId") in input_map
        ]
        source = f"; source: {', '.join(source_labels)}" if source_labels else ""
        lines.append(f"- Appearance {subject_id}.{state_id}: {details or state['description']}{source}")
    for environment_id, state_id in sorted(environment_destinations):
        environment = environments[environment_id]
        state = resolve_state(environment["states"], state_id, "temporary")
        details = "; ".join(
            f"{key}: {value}" for key, value in state["temporary"].items()
            if value not in (None, "", [], {})
        )
        lines.append(f"- Environment state {environment_id}.{state_id}: {details}")
    return "\n".join(lines)


def compile_planning_context(
    media_manifest: str | Mapping[str, Any] | list[Any] | None,
    shot_plan: str | Mapping[str, Any] | None,
    duration_seconds: float,
    *,
    frame_count: int = 0,
    mode: str = "auto",
    collector: DiagnosticCollector | None = None,
) -> dict[str, Any]:
    """Compile media and shots once; all downstream consumers reuse this result."""
    diagnostic_collector = collector if collector is not None else DiagnosticCollector()
    media = (
        dict(media_manifest)
        if isinstance(media_manifest, Mapping) and "canonicalJson" in media_manifest and "generations" in media_manifest
        else parse_media_project(media_manifest)
    )
    project = media.get("project", {})
    resolved_mode = str(mode or "auto").strip().lower()
    if resolved_mode == "auto" and isinstance(project, Mapping):
        resolved_mode = str(project.get("mode", "auto"))
    try:
        shots = (
            dict(shot_plan)
            if isinstance(shot_plan, Mapping) and "canonicalJson" in shot_plan and "shots" in shot_plan
            else parse_shot_plan(shot_plan, duration_seconds, frame_count, resolved_mode)
        )
    except ValueError as exc:
        code = (
            DiagnosticCode.SHOT_PLAN_UNSUPPORTED_VERSION
            if "schemaVersion" in str(exc) and "one of" in str(exc)
            else DiagnosticCode.SHOT_PLAN_INVALID_JSON
        )
        diagnostic_collector.emit(
            code, str(exc)[:500],
            DiagnosticLocation(LocationScope.CONFIGURATION, "shot_plan_json"),
        )
        shots = {"schemaVersion": None, "shots": [], "digest": ""}
    if not media.get("valid"):
        for issue in media.get("diagnostics", ()):
            try:
                code = DiagnosticCode(str(issue.get("code", "")))
            except ValueError:
                code = DiagnosticCode.MEDIA_MANIFEST_INVALID_JSON
            diagnostic_collector.emit(
                code,
                str(issue.get("message", "Invalid media manifest"))[:500],
                DiagnosticLocation(
                    LocationScope.CONFIGURATION,
                    str(issue.get("field", "media_manifest")),
                ),
                data={"sourceCode": str(issue.get("code", "")), **dict(issue.get("data", {}))},
            )
    if media.get("schemaVersion") != 2 or shots.get("schemaVersion") != 2 or not media.get("valid"):
        report = diagnostic_collector.to_report()
        payload = {
            "schemaVersion": PLANNING_CONTEXT_SCHEMA_VERSION,
            "applied": False,
            "valid": bool(media.get("valid")) and not report["summary"]["errors"],
            "mediaManifestSchemaVersion": media.get("schemaVersion"),
            "shotPlanSchemaVersion": shots.get("schemaVersion"),
            "mediaDigest": media.get("digest", ""),
            "shotPlanDigest": shots.get("digest", ""),
            "generations": {}, "shots": [], "diagnosticReport": report,
        }
        payload["digest"] = _digest({key: value for key, value in payload.items() if key != "diagnosticReport"})
        return payload

    assets = {item["id"]: item for item in project["assets"]}
    subjects = {item["id"]: item for item in project["subjects"]}
    environments = {item["id"]: item for item in project["environments"]}
    generations = {item["id"]: item for item in project["generations"]}
    shots_by_generation: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    for shot_index, shot in enumerate(shots["shots"]):
        generation_id = shot["generationId"]
        if generation_id not in generations:
            _emit_unknown(
                diagnostic_collector, generation_id, shot, shot_index, "generationId",
                ResourceKind.GENERATION, generation_id,
                f"Shot {shot['id']!r} references unknown generation {generation_id!r}.",
            )
            continue
        shots_by_generation.setdefault(generation_id, []).append((shot_index, shot))

    compiled_generations: dict[str, dict[str, Any]] = {}
    resolved_shots: list[dict[str, Any]] = []
    previous_final: dict[str, Any] | None = None
    for generation in sorted(project["generations"], key=lambda item: item["order"]):
        generation_id = generation["id"]
        generation_shots = shots_by_generation.get(generation_id, [])
        initial_state = _generation_initial_state(project, generation, previous_final)
        subject_ids, environment_ids, asset_ids, view_ids = _generation_entities(
            generation, generation_shots, subjects, environments, assets,
        )
        filtered_generation = _filtered_generation(
            generation, initial_state, subject_ids, environment_ids, view_ids,
        )
        roots = [
            *({"kind": "subject", "id": item} for item in sorted(subject_ids)),
            *({"kind": "environment", "id": item} for item in sorted(environment_ids)),
            *({"kind": "asset", "id": item} for item in sorted(asset_ids)),
            *_mode_anchor_roots(resolved_mode, generation, assets),
        ]
        for _shot_index, shot in generation_shots:
            for transition in shot.get("appearanceTransitions", ()):
                subject = subjects.get(transition["subjectId"])
                if subject:
                    roots.extend(_appearance_source_roots(subject, transition["toStateId"]))
        resolution = resolve_generation_references(
            project, filtered_generation, roots, binding_assets_are_roots=False,
        )
        _collect_resolution_issues(diagnostic_collector, generation_id, resolution["issues"])
        generation_resolved_shots, final_state = _validate_shots_and_resolve_state(
            diagnostic_collector, generation_id, generation_shots, subject_ids,
            initial_state, subjects, environments, assets,
            set(resolution["activeAssetIds"]), resolution["inputMap"],
        )
        resolved_shots.extend(generation_resolved_shots)
        previous_final = final_state
        generation_resolution = {
            **resolution,
            "initialState": initial_state,
            "finalState": final_state,
            "stateDigest": final_state["digest"],
            "shotIds": [shot["id"] for _index, shot in generation_shots],
        }
        compiled_generations[generation_id] = generation_resolution

    recomposed_media = {**media, "generations": compiled_generations}
    for generation_id, generation_result in compiled_generations.items():
        generation_shots = shots_by_generation.get(generation_id, [])
        generation_result["mediaContext"] = manifest_context_for_generation(recomposed_media, generation_id)
        generation_result["context"] = _structured_generation_context(
            generation_result["mediaContext"], generation_shots,
            generation_result["inputMap"], subjects, environments,
        )
        generation_result["contextDigest"] = hashlib.sha256(generation_result["context"].encode("utf-8")).hexdigest()

    claims = (*claims_from_shot_plan(shots), *claims_from_video_references(recomposed_media, shots))
    camera_authority = resolve_camera_authority(claims, diagnostic_collector)
    camera_payload = camera_authority.to_dict()
    authority_digest = _digest(camera_payload)
    shot_generation = {shot["id"]: shot["generationId"] for shot in shots["shots"]}
    for generation_id, generation in compiled_generations.items():
        generation_camera = {
            "owners": [item for item in camera_payload["owners"] if shot_generation.get(item["shotId"]) == generation_id],
            "shadowed": [item for item in camera_payload["shadowed"] if shot_generation.get(item["winner"]["shotId"]) == generation_id],
            "conflicts": [item for item in camera_payload["conflicts"] if shot_generation.get(item["shotId"]) == generation_id],
        }
        generation_camera["valid"] = not generation_camera["conflicts"]
        generation["authorityDigest"] = _digest(generation_camera)

    report = diagnostic_collector.to_report()
    summary = {
        "generationCount": len(compiled_generations),
        "shotCount": len(shots["shots"]),
        "activeAssetCount": sum(len(item["activeAssetIds"]) for item in compiled_generations.values()),
        "subjectCount": len(subjects),
        "environmentCount": len(environments),
        "diagnosticCount": len(report["diagnostics"]),
    }
    digest_payload = {
        "mediaDigest": media["digest"], "shotPlanDigest": shots["digest"],
        "generations": {
            generation_id: {
                "activeAssetIds": item["activeAssetIds"], "inputMap": item["inputMap"],
                "stateDigest": item["stateDigest"], "contextDigest": item["contextDigest"],
            }
            for generation_id, item in compiled_generations.items()
        },
        "shots": resolved_shots, "authorityDigest": authority_digest,
    }
    return {
        "schemaVersion": PLANNING_CONTEXT_SCHEMA_VERSION,
        "applied": True,
        "valid": bool(media["valid"] and report["summary"]["valid"]),
        "mediaManifestSchemaVersion": 2,
        "shotPlanSchemaVersion": 2,
        "mediaDigest": media["digest"],
        "shotPlanDigest": shots["digest"],
        "digest": _digest(digest_payload),
        "diagnosticsDigest": diagnostic_collector.digest(),
        "diagnosticReport": report,
        "planningSummary": summary,
        "mediaProject": recomposed_media,
        "shotPlan": shots,
        "generations": compiled_generations,
        "shots": resolved_shots,
        "cameraAuthority": camera_payload,
        "authorityDigest": authority_digest,
    }


def planning_context_for_generation(compiled: Mapping[str, Any], generation_id: str) -> str:
    generation = compiled.get("generations", {}).get(generation_id, {})
    return str(generation.get("context", ""))
