# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic activation and physical-slot resolution for media projects."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


RESOURCE_KINDS = {"asset", "subject", "environment"}
ASSET_LIMITS = {"picture": 9, "video": 3, "audio": 3}


def _issue(code: str, message: str, field: str, **data: Any) -> dict[str, Any]:
    return {"code": code, "message": message, "field": field, "data": data}


def _resource_key(resource: dict[str, Any]) -> tuple[str, str]:
    return str(resource.get("kind", "")), str(resource.get("id", ""))


def _state_chain(states: dict[str, dict[str, Any]], state_id: str) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = state_id
    while current:
        if current in seen or current not in states:
            break
        seen.add(current)
        state = states[current]
        chain.append(state)
        current = str(state.get("extends", ""))
    chain.reverse()
    return chain


def dependency_closure(
    project: dict[str, Any],
    generation: dict[str, Any],
    roots: Iterable[dict[str, Any]],
) -> tuple[set[tuple[str, str]], list[dict[str, Any]]]:
    """Expand logical resources into their required assets in stable project order."""
    assets = {item["id"]: item for item in project.get("assets", [])}
    subjects = {item["id"]: item for item in project.get("subjects", [])}
    environments = {item["id"]: item for item in project.get("environments", [])}
    subject_selections = {item["subjectId"]: item for item in generation.get("subjectStates", [])}
    environment_selections = {item["environmentId"]: item for item in generation.get("environmentStates", [])}
    active: set[tuple[str, str]] = set()
    issues: list[dict[str, Any]] = []
    queue = list(roots)
    cursor = 0
    while cursor < len(queue):
        resource = queue[cursor]
        cursor += 1
        key = _resource_key(resource)
        if key in active:
            continue
        kind, resource_id = key
        table = {"asset": assets, "subject": subjects, "environment": environments}.get(kind)
        if table is None or resource_id not in table:
            issues.append(_issue(
                "reference.activation.unknown_resource",
                f"Generation {generation['id']} activates unknown {kind or 'resource'} {resource_id!r}",
                f"generations.{generation['id']}.activation",
                kind=kind,
                id=resource_id,
            ))
            continue
        active.add(key)
        if kind == "subject":
            subject = subjects[resource_id]
            queue.extend({"kind": "asset", "id": asset_id} for asset_id in subject["identityAssetIds"])
            selection = subject_selections.get(resource_id, {})
            state_id = selection.get("resolvedStateId", selection.get("stateId", subject["baseAppearanceStateId"]))
            states = {state["id"]: state for state in subject["appearanceStates"]}
            for state in _state_chain(states, str(state_id)):
                source = state.get("source", {})
                if source.get("mode") == "asset":
                    queue.append({"kind": "asset", "id": source.get("assetId", "")})
        elif kind == "environment":
            environment = environments[resource_id]
            selection = environment_selections.get(resource_id, {})
            selected_views = set(selection.get("viewIds", ()))
            queue.extend(
                {"kind": "asset", "id": view["assetId"]}
                for view in environment["views"] if view["id"] in selected_views
            )
    return active, issues


def resolve_generation_references(
    project: dict[str, Any],
    generation: dict[str, Any],
    additional_roots: Iterable[dict[str, Any]] = (),
    *,
    binding_assets_are_roots: bool = True,
) -> dict[str, Any]:
    """Resolve one generation without deriving identity from physical slot labels."""
    activation = generation["activation"]
    roots: list[dict[str, Any]] = []
    if activation["mode"] == "explicit":
        roots.extend(activation.get("roots", ()))
    roots.extend({"kind": "subject", "id": item["subjectId"]} for item in generation.get("subjectStates", ()))
    roots.extend({"kind": "environment", "id": item["environmentId"]} for item in generation.get("environmentStates", ()))
    roots.extend(additional_roots)
    # Before a shot plan is compiled, bindings are the only declaration that an
    # otherwise standalone asset is intended for this generation.
    if binding_assets_are_roots:
        roots.extend({"kind": "asset", "id": item["assetId"]} for item in generation.get("bindings", ()))
    active, issues = dependency_closure(project, generation, roots)
    mandatory = set(active)
    assets = {item["id"]: item for item in project.get("assets", [])}
    subjects = {item["id"]: item for item in project.get("subjects", [])}
    environments = {item["id"]: item for item in project.get("environments", [])}

    excluded = {_resource_key(item) for item in activation.get("exclude", ())}
    for key in sorted(excluded):
        table = {"asset": assets, "subject": subjects, "environment": environments}.get(key[0], {})
        if key[1] not in table:
            issues.append(_issue(
                "reference.activation.unknown_resource",
                f"Generation {generation['id']} excludes unknown {key[0] or 'resource'} {key[1]!r}",
                f"generations.{generation['id']}.activation.exclude",
                kind=key[0], id=key[1],
            ))
            continue
        if key in mandatory:
            issues.append(_issue(
                "reference.activation.required_excluded",
                f"Generation {generation['id']} excludes required {key[0]} {key[1]!r}",
                f"generations.{generation['id']}.activation.exclude",
                kind=key[0], id=key[1],
            ))
        else:
            active.discard(key)

    active_asset_ids = {resource_id for kind, resource_id in active if kind == "asset"}
    bindings = generation.get("bindings", [])
    bound_ids: set[str] = set()
    input_map: dict[str, str] = {}
    occupied: dict[tuple[str, int], str] = {}
    for index, binding in enumerate(bindings):
        asset_id = binding["assetId"]
        asset = assets.get(asset_id)
        field = f"generations.{generation['id']}.bindings.{index}"
        if asset is None:
            issues.append(_issue("reference.binding.type_mismatch", f"Binding references unknown asset {asset_id!r}", field))
            continue
        if asset_id in bound_ids:
            issues.append(_issue("reference.binding.duplicate_asset", f"Asset {asset_id!r} is bound more than once", field, assetId=asset_id))
        bound_ids.add(asset_id)
        kind = asset["type"]
        slot = binding["slotIndex"]
        if slot > ASSET_LIMITS[kind]:
            issues.append(_issue(
                "reference.binding.type_mismatch",
                f"{kind.title()} asset {asset_id!r} cannot use slot {slot}", field,
                assetId=asset_id, slotIndex=slot,
            ))
        slot_key = (kind, slot)
        if slot_key in occupied:
            issues.append(_issue(
                "reference.binding.duplicate_slot",
                f"{kind.title()} slot {slot} is shared by {occupied[slot_key]!r} and {asset_id!r}", field,
                assetId=asset_id, slotIndex=slot,
            ))
        occupied[slot_key] = asset_id
        label = f"<{kind.title()} {slot}>"
        input_map[asset_id] = label
        soundtrack_slot = binding.get("soundtrackSlotIndex")
        audio_mode = asset.get("audioMode", "off")
        if kind == "video" and audio_mode in {"paired", "alone"}:
            if soundtrack_slot is None:
                issues.append(_issue("reference.binding.missing_soundtrack", f"Video {asset_id!r} requires a soundtrack slot", field))
            else:
                audio_key = ("audio", soundtrack_slot)
                if audio_key in occupied:
                    issues.append(_issue(
                        "reference.binding.duplicate_slot",
                        f"Audio slot {soundtrack_slot} is already occupied by {occupied[audio_key]!r}", field,
                        assetId=asset_id, slotIndex=soundtrack_slot,
                    ))
                occupied[audio_key] = f"{asset_id}:soundtrack"
                input_map[f"{asset_id}:soundtrack"] = f"<Audio {soundtrack_slot}>"
        elif soundtrack_slot is not None:
            issues.append(_issue("reference.binding.type_mismatch", f"Asset {asset_id!r} cannot declare a soundtrack slot", field))

    for asset_id in sorted(active_asset_ids - bound_ids):
        issues.append(_issue(
            "reference.binding.missing", f"Active asset {asset_id!r} has no binding in generation {generation['id']}",
            f"generations.{generation['id']}.bindings", assetId=asset_id,
        ))
    for asset_id in sorted(bound_ids - active_asset_ids):
        issues.append(_issue(
            "reference.binding.inactive", f"Binding for inactive asset {asset_id!r} is not allowed in generation {generation['id']}",
            f"generations.{generation['id']}.bindings", assetId=asset_id,
        ))

    active_assets = [asset for asset in project.get("assets", []) if asset["id"] in active_asset_ids]
    counts = {kind: sum(asset["type"] == kind for asset in active_assets) for kind in ASSET_LIMITS}
    soundtrack_count = sum(asset.get("audioMode") in {"paired", "alone"} for asset in active_assets if asset["type"] == "video")
    counts["audio"] += soundtrack_count
    total_files = len(active_assets)
    video_seconds = sum(float(asset.get("durationSeconds", 0)) for asset in active_assets if asset["type"] == "video")
    audio_seconds = sum(float(asset.get("durationSeconds", 0)) for asset in active_assets if asset["type"] == "audio")
    audio_seconds += sum(
        float(asset.get("durationSeconds", 0)) for asset in active_assets
        if asset["type"] == "video" and asset.get("audioMode") in {"paired", "alone"}
    )
    violations = [
        (counts["picture"] > 9, "more than 9 pictures"),
        (counts["video"] > 3, "more than 3 videos"),
        (counts["audio"] > 3, "more than 3 audio references including soundtracks"),
        (total_files > 12, "more than 12 media files"),
        (video_seconds > 15, "more than 15 seconds of video"),
        (audio_seconds > 15, "more than 15 seconds of audio"),
        (counts["audio"] > 0 and not (counts["picture"] or counts["video"]), "audio as the only reference modality"),
    ]
    for violated, detail in violations:
        if violated:
            issues.append(_issue(
                "reference.capacity.exceeded", f"Generation {generation['id']} has {detail}",
                f"generations.{generation['id']}.bindings",
            ))
    return {
        "generationId": generation["id"],
        "activeResources": [
            {"kind": kind, "id": resource_id} for kind, resource_id in sorted(active)
        ],
        "activeAssetIds": [asset["id"] for asset in active_assets],
        "inputMap": input_map,
        "counts": counts,
        "totalFiles": total_files,
        "videoSeconds": video_seconds,
        "audioSeconds": audio_seconds,
        "issues": issues,
    }
