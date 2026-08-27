# SPDX-License-Identifier: GPL-3.0-only
"""Structured reference-media context for MiniMax H3 prompt construction."""

from __future__ import annotations

import json
import hashlib
import math
import re
from typing import Any

try:
    from .continuity_state import compile_generation_states, resolve_state, validate_state_graph
    from .reference_resolution import resolve_generation_references
except ImportError:
    from continuity_state import compile_generation_states, resolve_state, validate_state_graph
    from reference_resolution import resolve_generation_references


ASPECT_RATIOS = ("auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
MEDIA_TYPES = {"picture", "image", "video", "audio"}
MEDIA_MANIFEST_SCHEMA_VERSION = 2


def parse_media_manifest(value: str | dict | list | None) -> dict[str, Any]:
    """Parse the optional JSON manifest without guessing facts from prose."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return {"items": [], "mode": "", "warnings": [], "errors": []}
    if isinstance(value, str):
        # Builds before the structured manifest existed can deserialize the adjacent aspect-ratio
        # widget into this slot. Those enum values can never be manifest JSON, so repair only this
        # unambiguous migration case while continuing to reject every other malformed string.
        if value.strip().lower() in ASPECT_RATIOS:
            return {
                "items": [], "mode": "", "errors": [],
                "warnings": [f"Ignored migrated aspect-ratio value {value.strip()!r} in media_manifest"],
            }
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            return {"items": [], "mode": "", "warnings": [], "errors": [f"media_manifest is invalid JSON: {exc.msg}"]}
    else:
        data = value
    if isinstance(data, list):
        data = {"items": data}
    if not isinstance(data, dict):
        return {"items": [], "mode": "", "warnings": [], "errors": ["media_manifest must be a JSON object or array"]}
    if data.get("schemaVersion") == MEDIA_MANIFEST_SCHEMA_VERSION:
        return _legacy_projection_v2(parse_media_project(data))
    raw_items = data.get("items", data.get("assets", data.get("media", [])))
    if not isinstance(raw_items, list):
        return {"items": [], "mode": "", "warnings": [], "errors": ["media_manifest.items must be an array"]}

    items: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    counters = {"picture": 0, "video": 0, "audio": 0}
    total_files = 0
    video_seconds = 0.0
    audio_seconds = 0.0
    for position, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            errors.append(f"media item {position} must be an object")
            continue
        if raw.get("enabled", True) is False:
            continue
        kind = str(raw.get("type", raw.get("kind", ""))).strip().lower()
        kind = "picture" if kind == "image" else kind
        if kind not in {"picture", "video", "audio"}:
            errors.append(f"media item {position} has unsupported type {kind!r}")
            continue
        total_files += 1
        raw_duration = raw.get("duration_seconds", raw.get("duration", 0))
        try:
            duration = float(raw_duration or 0)
        except (TypeError, ValueError):
            duration = 0.0
            errors.append(f"media item {position} duration must be numeric")
        if kind in {"video", "audio"} and duration:
            if not 2.0 <= duration <= 15.0:
                errors.append(f"media item {position} duration {duration:g}s is outside the documented 2-15s range")
            if kind == "video":
                video_seconds += duration
            else:
                audio_seconds += duration

        audio_mode = str(raw.get("audio_mode", "off")).strip().lower()
        soundtrack_label = ""
        if kind == "video" and audio_mode in {"paired", "alone"}:
            counters["audio"] += 1
            soundtrack_label = f"<Audio {counters['audio']}>"
            audio_seconds += duration
        counters[kind] += 1
        label = f"<{kind.title()} {counters[kind]}>"
        item = dict(raw)
        item.update({"type": kind, "label": label, "position": position, "duration_seconds": duration})
        if soundtrack_label:
            item["soundtrack_label"] = soundtrack_label
        items.append(item)

    if counters["picture"] > 9:
        errors.append("Ref2VA accepts at most 9 pictures")
    if counters["video"] > 3:
        errors.append("Ref2VA accepts at most 3 videos")
    if counters["audio"] > 3:
        errors.append("Ref2VA accepts at most 3 audio references, including enabled video soundtracks")
    if total_files > 12:
        errors.append("Ref2VA accepts at most 12 media files")
    if video_seconds > 15.0:
        errors.append(f"reference video duration totals {video_seconds:g}s; the documented maximum is 15s")
    if audio_seconds > 15.0:
        errors.append(f"reference audio duration totals {audio_seconds:g}s; the documented maximum is 15s")
    if counters["audio"] and not (counters["picture"] or counters["video"]):
        errors.append("Ref2VA audio cannot be the only reference modality")
    subjects: list[dict[str, Any]] = []
    raw_subjects = data.get("subjects", [])
    if not isinstance(raw_subjects, list):
        errors.append("media_manifest.subjects must be an array")
    else:
        available_labels = {
            label for item in items for label in (item.get("label"), item.get("soundtrack_label")) if label
        }
        for position, raw_subject in enumerate(raw_subjects, start=1):
            if not isinstance(raw_subject, dict):
                errors.append(f"manifest subject {position} must be an object")
                continue
            raw_id = raw_subject.get("id", raw_subject.get("subject_id", position))
            match = re.search(r"\d+", str(raw_id))
            if not match:
                errors.append(f"manifest subject {position} requires a numeric id")
                continue
            label = f"<Subject {int(match.group())}>"
            description = str(raw_subject.get("description", raw_subject.get("analysis", ""))).strip()
            sources = raw_subject.get("sources", raw_subject.get("source", []))
            sources = [sources] if isinstance(sources, str) else list(sources or [])
            sources = [str(source).strip() for source in sources if str(source).strip()]
            unknown = [source for source in sources if source not in available_labels]
            if not description:
                errors.append(f"{label} requires a concrete description")
            if not sources:
                errors.append(f"{label} requires at least one media source label")
            if unknown:
                errors.append(f"{label} has unknown source labels: {unknown}")
            subjects.append({"label": label, "description": description, "sources": sources})
    return {
        "items": items,
        "subjects": subjects,
        "mode": str(data.get("mode", "")).strip().lower(),
        "warnings": warnings,
        "errors": errors,
        "counts": counters,
        "totalFiles": total_files,
        "videoSeconds": video_seconds,
        "audioSeconds": audio_seconds,
    }


class _DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _project_issue(code: str, message: str, field: str = "media_manifest", **data: Any) -> dict[str, Any]:
    return {"code": code, "message": message, "field": field, "data": data}


def _canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _unknown_keys(value: Any, allowed: set[str], field: str, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        return
    for key in value.keys() - allowed:
        issues.append(_project_issue("schema.media_manifest.unknown_field", f"Unknown field {key!r} at {field}", f"{field}.{key}"))


def _require_object(value: Any, field: str, issues: list[dict[str, Any]]) -> bool:
    if isinstance(value, dict):
        return True
    issues.append(_project_issue("schema.media_manifest.invalid_type", f"{field} must be an object", field))
    return False


def _require_array(value: Any, field: str, issues: list[dict[str, Any]], maximum: int | None = None) -> bool:
    if not isinstance(value, list):
        issues.append(_project_issue("schema.media_manifest.invalid_type", f"{field} must be an array", field))
        return False
    if maximum is not None and len(value) > maximum:
        issues.append(_project_issue("schema.media_manifest.limit", f"{field} accepts at most {maximum} items", field))
    return True


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value) is not None


def _all_unique(values: list[Any]) -> bool:
    keys = [_canonical_json(value) for value in values]
    return len(keys) == len(set(keys))


def _required_fields(value: dict[str, Any], required: set[str], field: str, issues: list[dict[str, Any]]) -> None:
    for key in required - value.keys():
        issues.append(_project_issue("schema.media_manifest.missing_field", f"Missing required field {key!r} at {field}", f"{field}.{key}"))


def _text_field(value: Any, field: str, issues: list[dict[str, Any]], maximum: int, *,
                required: bool = False, allow_empty: bool = False) -> None:
    if value is None and not required:
        return
    if not isinstance(value, str) or (not value and not allow_empty) or len(value) > maximum:
        issues.append(_project_issue("schema.media_manifest.invalid_text", f"{field} must be a non-empty string of at most {maximum} characters", field))


def _check_text_values(value: Any, field: str, issues: list[dict[str, Any]]) -> None:
    if isinstance(value, str) and "\x00" in value:
        issues.append(_project_issue("schema.media_manifest.invalid_text", f"{field} contains a NUL character", field))
    elif isinstance(value, dict):
        for key, child in value.items():
            _check_text_values(child, f"{field}.{key}", issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_text_values(child, f"{field}.{index}", issues)


def _validate_v2_shape(project: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    root_fields = {"schemaVersion", "mode", "assets", "subjects", "props", "environments", "generations"}
    _unknown_keys(project, root_fields, "media_manifest", issues)
    _required_fields(project, {"schemaVersion", "assets", "subjects", "environments", "generations"}, "media_manifest", issues)
    _check_text_values(project, "media_manifest", issues)
    mode = project.get("mode", "auto")
    if mode not in {"auto", "t2va", "i2va", "fl2va", "l2va", "ref2va", "chained_multishot"}:
        issues.append(_project_issue("schema.media_manifest.invalid_value", f"Unsupported mode {mode!r}", "media_manifest.mode"))
    arrays = (("assets", 128), ("subjects", 64), ("environments", 64), ("generations", 64))
    if not all(_require_array(project.get(name), f"media_manifest.{name}", issues, maximum) for name, maximum in arrays):
        return issues
    if "props" in project and not _require_array(project.get("props"), "media_manifest.props", issues, 64):
        return issues
    if not project["generations"]:
        issues.append(_project_issue("schema.media_manifest.limit", "media_manifest.generations requires at least one item", "media_manifest.generations"))

    asset_fields = {"id", "type", "name", "available", "durationSeconds", "audioMode", "description", "analysis", "transcript", "cameraTransfer", "audioClip"}
    for index, asset in enumerate(project["assets"]):
        field = f"media_manifest.assets.{index}"
        if not _require_object(asset, field, issues):
            continue
        _unknown_keys(asset, asset_fields, field, issues)
        _required_fields(asset, {"id", "type", "name"}, field, issues)
        _text_field(asset.get("name"), f"{field}.name", issues, 500, required=True)
        _text_field(asset.get("description"), f"{field}.description", issues, 8000)
        if asset.get("type") not in {"picture", "video", "audio"}:
            issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid asset type {asset.get('type')!r}", f"{field}.type"))
        if "available" in asset and not isinstance(asset["available"], bool):
            issues.append(_project_issue("schema.media_manifest.invalid_type", f"{field}.available must be boolean", f"{field}.available"))
        duration = asset.get("durationSeconds")
        if duration is not None and (not isinstance(duration, (int, float)) or isinstance(duration, bool) or not 0 <= duration <= 15):
            issues.append(_project_issue("schema.media_manifest.invalid_value", f"{field}.durationSeconds must be between 0 and 15", f"{field}.durationSeconds"))
        if asset.get("type") != "video" and ("audioMode" in asset or "cameraTransfer" in asset):
            issues.append(_project_issue("schema.media_manifest.invalid_value", "Only video assets may declare audioMode or cameraTransfer", field))
        clip = asset.get("audioClip")
        if clip is not None:
            if asset.get("type") != "audio":
                issues.append(_project_issue("schema.media_manifest.invalid_value", "Only audio assets may declare audioClip", f"{field}.audioClip"))
            elif _require_object(clip, f"{field}.audioClip", issues):
                _unknown_keys(clip, {"startSeconds", "endSeconds"}, f"{field}.audioClip", issues)
                _required_fields(clip, {"startSeconds", "endSeconds"}, f"{field}.audioClip", issues)
                start, end = clip.get("startSeconds"), clip.get("endSeconds")
                valid_numbers = all(
                    isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                    for value in (start, end)
                )
                if not valid_numbers or start < 0 or end <= start or end - start > 15:
                    issues.append(_project_issue("schema.media_manifest.invalid_value", f"{field}.audioClip requires finite 0 <= startSeconds < endSeconds and at most 15 seconds", f"{field}.audioClip"))
        if asset.get("type") == "video" and asset.get("audioMode", "off") not in {"off", "paired", "alone"}:
            issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid audioMode for {asset.get('id')!r}", f"{field}.audioMode"))
        transfer = asset.get("cameraTransfer")
        if transfer is not None:
            if _require_object(transfer, f"{field}.cameraTransfer", issues):
                _unknown_keys(transfer, {"enabled", "role", "aspects"}, f"{field}.cameraTransfer", issues)
                _required_fields(transfer, {"enabled", "role", "aspects"}, f"{field}.cameraTransfer", issues)
                if transfer.get("enabled") is not True or transfer.get("role") != "camera_reference":
                    issues.append(_project_issue("schema.media_manifest.invalid_value", "cameraTransfer requires enabled=true and role='camera_reference'", f"{field}.cameraTransfer"))
                aspects = transfer.get("aspects")
                allowed = {"motion", "framing", "angle", "viewpoint", "composition", "focus", "distance", "stability", "lens", "parallax"}
                if not isinstance(aspects, list) or not aspects or not _all_unique(aspects) or any(item not in allowed for item in aspects):
                    issues.append(_project_issue("schema.media_manifest.invalid_value", "cameraTransfer.aspects must be a non-empty unique list of camera aspects", f"{field}.cameraTransfer.aspects"))
        if "transcript" in asset:
            if _require_array(asset["transcript"], f"{field}.transcript", issues, 256):
                for transcript_index, entry in enumerate(asset["transcript"]):
                    entry_field = f"{field}.transcript.{transcript_index}"
                    if isinstance(entry, str):
                        _text_field(entry, entry_field, issues, 8000, required=True)
                    elif _require_object(entry, entry_field, issues):
                        _unknown_keys(entry, {"text", "language", "unclear"}, entry_field, issues)
                        _required_fields(entry, {"text"}, entry_field, issues)
                        _text_field(entry.get("text"), f"{entry_field}.text", issues, 8000, required=True)

    state_fields = {"id", "name", "extends", "controls", "description", "attributes", "source"}
    subject_fields = {"id", "h3Index", "name", "description", "identityAssetIds", "defaultVoiceAssetId", "baseAppearanceStateId", "appearanceStates"}
    required_subject_fields = subject_fields - {"defaultVoiceAssetId"}
    for index, subject in enumerate(project["subjects"]):
        field = f"media_manifest.subjects.{index}"
        if not _require_object(subject, field, issues):
            continue
        _unknown_keys(subject, subject_fields, field, issues)
        _required_fields(subject, required_subject_fields, field, issues)
        _text_field(subject.get("name"), f"{field}.name", issues, 500, required=True)
        _text_field(subject.get("description"), f"{field}.description", issues, 8000, required=True, allow_empty=True)
        if subject.get("description") == "Describe the stable identity.":
            issues.append(_project_issue(
                "schema.media_manifest.invalid_value",
                f"{field}.description is unfinished instructional text",
                f"{field}.description",
            ))
        if not isinstance(subject.get("h3Index"), int) or isinstance(subject.get("h3Index"), bool) or not 1 <= subject.get("h3Index", 0) <= 64:
            issues.append(_project_issue("schema.media_manifest.invalid_value", f"{field}.h3Index must be 1..64", f"{field}.h3Index"))
        if _require_array(subject.get("identityAssetIds"), f"{field}.identityAssetIds", issues):
            if not str(subject.get("description") or "").strip() and not subject["identityAssetIds"]:
                issues.append(_project_issue(
                    "schema.media_manifest.missing_field",
                    f"{field} requires either a stable description or at least one identity Picture",
                    f"{field}.description",
                ))
            if not _all_unique(subject["identityAssetIds"]):
                issues.append(_project_issue("schema.media_manifest.duplicate", f"{field}.identityAssetIds must be unique", f"{field}.identityAssetIds"))
            if any(not _valid_id(asset_id) for asset_id in subject["identityAssetIds"]):
                issues.append(_project_issue("schema.media_manifest.invalid_id", f"{field}.identityAssetIds contains an invalid ID", f"{field}.identityAssetIds"))
        if _require_array(subject.get("appearanceStates"), f"{field}.appearanceStates", issues, 64):
            if not subject["appearanceStates"]:
                issues.append(_project_issue("schema.media_manifest.limit", f"{field}.appearanceStates requires at least one state", f"{field}.appearanceStates"))
            for state_index, state in enumerate(subject["appearanceStates"]):
                state_field = f"{field}.appearanceStates.{state_index}"
                if not _require_object(state, state_field, issues):
                    continue
                _unknown_keys(state, state_fields, state_field, issues)
                _required_fields(state, {"id", "name", "controls"}, state_field, issues)
                _text_field(state.get("name"), f"{state_field}.name", issues, 500, required=True)
                _text_field(state.get("description"), f"{state_field}.description", issues, 8000)
                controls = state.get("controls")
                allowed_controls = {"wardrobe", "hair", "makeup", "accessories", "carried_items", "damage", "wetness", "body_condition", "transformation", "other"}
                if not isinstance(controls, list) or not _all_unique(controls) or any(item not in allowed_controls for item in controls):
                    issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid controls in {state_field}", f"{state_field}.controls"))
                if "extends" in state and not _valid_id(state["extends"]):
                    issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid extends ID in {state_field}", f"{state_field}.extends"))
                if "attributes" in state and _require_object(state["attributes"], f"{state_field}.attributes", issues):
                    _unknown_keys(state["attributes"], {"wardrobe", "hair", "makeup", "accessories", "carriedItems", "damage", "wetness", "bodyCondition", "transformation", "other"}, f"{state_field}.attributes", issues)
                source = state.get("source")
                if source is not None:
                    if _require_object(source, f"{state_field}.source", issues):
                        _unknown_keys(source, {"mode", "assetId", "region"}, f"{state_field}.source", issues)
                        if source.get("mode") not in {"description", "asset"} or (source.get("mode") == "asset" and "assetId" not in source):
                            issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid appearance source in {state_field}", f"{state_field}.source"))
                        if source.get("mode") == "asset" and not _valid_id(source.get("assetId")):
                            issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid appearance source asset ID in {state_field}", f"{state_field}.source.assetId"))

    prop_fields = {"id", "h3Index", "name", "category", "description", "designAssetIds"}
    for index, prop in enumerate(project.get("props", [])):
        field = f"media_manifest.props.{index}"
        if not _require_object(prop, field, issues):
            continue
        _unknown_keys(prop, prop_fields, field, issues)
        _required_fields(prop, {"id", "h3Index", "name", "designAssetIds"}, field, issues)
        _text_field(prop.get("name"), f"{field}.name", issues, 500, required=True)
        _text_field(prop.get("category"), f"{field}.category", issues, 500)
        _text_field(prop.get("description"), f"{field}.description", issues, 8000)
        if not isinstance(prop.get("h3Index"), int) or isinstance(prop.get("h3Index"), bool) or not 1 <= prop.get("h3Index", 0) <= 64:
            issues.append(_project_issue("schema.media_manifest.invalid_value", f"{field}.h3Index must be 1..64", f"{field}.h3Index"))
        if _require_array(prop.get("designAssetIds"), f"{field}.designAssetIds", issues):
            if not _all_unique(prop["designAssetIds"]):
                issues.append(_project_issue("schema.media_manifest.duplicate", f"{field}.designAssetIds must be unique", f"{field}.designAssetIds"))
            if any(not _valid_id(asset_id) for asset_id in prop["designAssetIds"]):
                issues.append(_project_issue("schema.media_manifest.invalid_id", f"{field}.designAssetIds contains an invalid ID", f"{field}.designAssetIds"))

    environment_fields = {"id", "name", "permanent", "views", "defaultStateId", "states"}
    for index, environment in enumerate(project["environments"]):
        field = f"media_manifest.environments.{index}"
        if not _require_object(environment, field, issues):
            continue
        _unknown_keys(environment, environment_fields, field, issues)
        _required_fields(environment, environment_fields, field, issues)
        _text_field(environment.get("name"), f"{field}.name", issues, 500, required=True)
        if _require_object(environment.get("permanent"), f"{field}.permanent", issues):
            _unknown_keys(environment["permanent"], {"geography", "architecture", "fixedElements", "scale", "other"}, f"{field}.permanent", issues)
        if _require_array(environment.get("views"), f"{field}.views", issues, 24):
            for view_index, view in enumerate(environment["views"]):
                view_field = f"{field}.views.{view_index}"
                if not _require_object(view, view_field, issues):
                    continue
                _unknown_keys(view, {"id", "name", "role", "assetId", "description"}, view_field, issues)
                _required_fields(view, {"id", "name", "role", "assetId"}, view_field, issues)
                _text_field(view.get("name"), f"{view_field}.name", issues, 500, required=True)
                _text_field(view.get("description"), f"{view_field}.description", issues, 8000)
                if not _valid_id(view.get("assetId")):
                    issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid view asset ID in {view_field}", f"{view_field}.assetId"))
                if view.get("role") not in {"overview", "alternate", "detail", "lighting", "custom"}:
                    issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid view role {view.get('role')!r}", f"{view_field}.role"))
        if _require_array(environment.get("states"), f"{field}.states", issues, 64):
            if not environment["states"]:
                issues.append(_project_issue("schema.media_manifest.limit", f"{field}.states requires at least one state", f"{field}.states"))
            for state_index, state in enumerate(environment["states"]):
                state_field = f"{field}.states.{state_index}"
                if not _require_object(state, state_field, issues):
                    continue
                _unknown_keys(state, {"id", "name", "extends", "temporary"}, state_field, issues)
                _required_fields(state, {"id", "name"}, state_field, issues)
                _text_field(state.get("name"), f"{state_field}.name", issues, 500, required=True)
                if "extends" in state and not _valid_id(state["extends"]):
                    issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid extends ID in {state_field}", f"{state_field}.extends"))
                if "temporary" in state and _require_object(state["temporary"], f"{state_field}.temporary", issues):
                    _unknown_keys(state["temporary"], {"lighting", "weather", "atmosphere", "condition", "timeOfDay", "temporaryElements", "other"}, f"{state_field}.temporary", issues)

    generation_fields = {"id", "order", "activation", "bindings", "subjectStates", "environmentStates"}
    for index, generation in enumerate(project["generations"]):
        field = f"media_manifest.generations.{index}"
        if not _require_object(generation, field, issues):
            continue
        _unknown_keys(generation, generation_fields, field, issues)
        _required_fields(generation, generation_fields, field, issues)
        if not isinstance(generation.get("order"), int) or isinstance(generation.get("order"), bool) or not 1 <= generation.get("order", 0) <= 64:
            issues.append(_project_issue("schema.media_manifest.invalid_value", f"{field}.order must be 1..64", f"{field}.order"))
        activation = generation.get("activation")
        if _require_object(activation, f"{field}.activation", issues):
            _unknown_keys(activation, {"mode", "roots", "exclude"}, f"{field}.activation", issues)
            if activation.get("mode") not in {"auto", "explicit"}:
                issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid activation mode {activation.get('mode')!r}", f"{field}.activation.mode"))
            if activation.get("mode") == "explicit" and ("roots" not in activation or not isinstance(activation.get("roots"), list) or not activation["roots"]):
                issues.append(_project_issue("schema.media_manifest.invalid_value", "Explicit activation requires at least one root", f"{field}.activation.roots"))
            for list_name in ("roots", "exclude"):
                if list_name in activation and _require_array(activation[list_name], f"{field}.activation.{list_name}", issues):
                    for ref_index, resource in enumerate(activation[list_name]):
                        ref_field = f"{field}.activation.{list_name}.{ref_index}"
                        if _require_object(resource, ref_field, issues):
                            _unknown_keys(resource, {"kind", "id"}, ref_field, issues)
                            _required_fields(resource, {"kind", "id"}, ref_field, issues)
                            if not _valid_id(resource.get("id")):
                                issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid resource ID at {ref_field}", f"{ref_field}.id"))
                            if resource.get("kind") not in {"asset", "subject", "prop", "environment"}:
                                issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid resource kind {resource.get('kind')!r}", f"{ref_field}.kind"))
        for list_name in ("bindings", "subjectStates", "environmentStates"):
            _require_array(generation.get(list_name), f"{field}.{list_name}", issues, 15 if list_name == "bindings" else None)
        for binding_index, binding in enumerate(generation.get("bindings", ()) if isinstance(generation.get("bindings"), list) else ()):
            binding_field = f"{field}.bindings.{binding_index}"
            if _require_object(binding, binding_field, issues):
                _unknown_keys(binding, {"assetId", "slotIndex", "soundtrackSlotIndex", "role"}, binding_field, issues)
                _required_fields(binding, {"assetId", "slotIndex"}, binding_field, issues)
                if not _valid_id(binding.get("assetId")):
                    issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid asset ID at {binding_field}", f"{binding_field}.assetId"))
                for slot_field in ("slotIndex", "soundtrackSlotIndex"):
                    if slot_field in binding and (not isinstance(binding[slot_field], int) or isinstance(binding[slot_field], bool) or not 1 <= binding[slot_field] <= (3 if slot_field == "soundtrackSlotIndex" else 9)):
                        issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid {slot_field}", f"{binding_field}.{slot_field}"))
                if binding.get("role", "reference") not in {"reference", "first_frame", "last_frame"}:
                    issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid binding role {binding.get('role')!r}", f"{binding_field}.role"))
                asset = next((item for item in project["assets"] if item.get("id") == binding.get("assetId")), None)
                if binding.get("role") in {"first_frame", "last_frame"} and asset and asset.get("type") != "picture":
                    issues.append(_project_issue("schema.media_manifest.invalid_value", "Only picture bindings may be first-frame or last-frame anchors", f"{binding_field}.role"))
        for selection_index, selection in enumerate(generation.get("subjectStates", ()) if isinstance(generation.get("subjectStates"), list) else ()):
            selection_field = f"{field}.subjectStates.{selection_index}"
            if _require_object(selection, selection_field, issues):
                _unknown_keys(selection, {"subjectId", "policy", "stateId", "reason"}, selection_field, issues)
                required = {"subjectId", "policy"} | ({"stateId"} if selection.get("policy") != "carry" else set()) | ({"reason"} if selection.get("policy") == "reset" else set())
                _required_fields(selection, required, selection_field, issues)
                if not _valid_id(selection.get("subjectId")) or ("stateId" in selection and not _valid_id(selection.get("stateId"))):
                    issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid subject/state ID at {selection_field}", selection_field))
                if selection.get("policy") not in {"carry", "explicit", "reset"}:
                    issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid subject-state policy {selection.get('policy')!r}", f"{selection_field}.policy"))
        for selection_index, selection in enumerate(generation.get("environmentStates", ()) if isinstance(generation.get("environmentStates"), list) else ()):
            selection_field = f"{field}.environmentStates.{selection_index}"
            if _require_object(selection, selection_field, issues):
                _unknown_keys(selection, {"environmentId", "policy", "stateId", "viewIds", "reason"}, selection_field, issues)
                required = {"environmentId", "policy", "viewIds"} | ({"stateId"} if selection.get("policy") != "carry" else set()) | ({"reason"} if selection.get("policy") == "reset" else set())
                _required_fields(selection, required, selection_field, issues)
                if not _valid_id(selection.get("environmentId")) or ("stateId" in selection and not _valid_id(selection.get("stateId"))):
                    issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid environment/state ID at {selection_field}", selection_field))
                if selection.get("policy") not in {"carry", "explicit", "reset"}:
                    issues.append(_project_issue("schema.media_manifest.invalid_value", f"Invalid environment-state policy {selection.get('policy')!r}", f"{selection_field}.policy"))
                _require_array(selection.get("viewIds"), f"{selection_field}.viewIds", issues)
                if isinstance(selection.get("viewIds"), list) and (not _all_unique(selection["viewIds"]) or any(not _valid_id(view_id) for view_id in selection["viewIds"])):
                    issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid or duplicate view ID at {selection_field}", f"{selection_field}.viewIds"))
    return issues


def _duplicate_id_issues(items: list[dict[str, Any]], namespace: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        item_id = item.get("id")
        field = f"media_manifest.{namespace}.{index}.id"
        if not _valid_id(item_id):
            issues.append(_project_issue("schema.media_manifest.invalid_id", f"Invalid ID {item_id!r} in {namespace}", field))
        elif item_id in seen:
            issues.append(_project_issue("schema.media_manifest.duplicate_id", f"Duplicate {namespace} ID {item_id!r}", field))
        if _valid_id(item_id):
            seen.add(item_id)
    return issues


def _validate_v2_semantics(project: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for namespace in ("assets", "subjects", "props", "environments", "generations"):
        issues.extend(_duplicate_id_issues(project.get(namespace, []), namespace))
    assets = {asset["id"]: asset for asset in project["assets"] if _valid_id(asset.get("id"))}
    h3_indices: set[int] = set()
    for subject in project["subjects"]:
        if subject["h3Index"] in h3_indices:
            issues.append(_project_issue("schema.media_manifest.duplicate_h3_index", f"Duplicate h3Index {subject['h3Index']}", f"subjects.{subject['id']}.h3Index"))
        h3_indices.add(subject["h3Index"])
        issues.extend(_duplicate_id_issues(subject["appearanceStates"], f"subjects.{subject['id']}.appearanceStates"))
        state_ids = {state["id"] for state in subject["appearanceStates"] if _valid_id(state.get("id"))}
        if not _valid_id(subject.get("baseAppearanceStateId")) or subject["baseAppearanceStateId"] not in state_ids:
            issues.append(_project_issue("appearance.state.unknown", f"Subject {subject['id']!r} has unknown base appearance state", f"subjects.{subject['id']}.baseAppearanceStateId"))
        if all(_valid_id(state.get("id")) and ("extends" not in state or _valid_id(state.get("extends"))) for state in subject["appearanceStates"]):
            issues.extend(validate_state_graph(subject["appearanceStates"], entity_kind="appearance", entity_id=subject["id"]))
        for asset_id in subject["identityAssetIds"]:
            if not _valid_id(asset_id) or asset_id not in assets or assets[asset_id]["type"] != "picture":
                issues.append(_project_issue("reference.binding.type_mismatch", f"Identity asset {asset_id!r} for subject {subject['id']!r} must be a picture", f"subjects.{subject['id']}.identityAssetIds"))
        voice_asset_id = subject.get("defaultVoiceAssetId")
        if voice_asset_id is not None:
            if not _valid_id(voice_asset_id) or voice_asset_id not in assets or assets[voice_asset_id]["type"] != "audio":
                issues.append(_project_issue("reference.binding.type_mismatch", f"Default voice asset {voice_asset_id!r} for subject {subject['id']!r} must be audio", f"subjects.{subject['id']}.defaultVoiceAssetId"))
        for state in subject["appearanceStates"]:
            source = state.get("source", {})
            if source.get("mode") == "asset":
                asset = assets.get(source.get("assetId"))
                if asset is None or asset["type"] not in {"picture", "video"}:
                    issues.append(_project_issue("reference.binding.type_mismatch", f"Appearance source {source.get('assetId')!r} must be a picture or video", f"subjects.{subject['id']}.appearanceStates.{state['id']}.source"))
    for prop in project.get("props", []):
        if prop["h3Index"] in h3_indices:
            issues.append(_project_issue("schema.media_manifest.duplicate_h3_index", f"Duplicate h3Index {prop['h3Index']}", f"props.{prop['id']}.h3Index"))
        h3_indices.add(prop["h3Index"])
        for asset_id in prop["designAssetIds"]:
            if not _valid_id(asset_id) or asset_id not in assets or assets[asset_id]["type"] != "picture":
                issues.append(_project_issue("reference.binding.type_mismatch", f"Design asset {asset_id!r} for prop {prop['id']!r} must be a picture", f"props.{prop['id']}.designAssetIds"))
    for environment in project["environments"]:
        issues.extend(_duplicate_id_issues(environment["views"], f"environments.{environment['id']}.views"))
        issues.extend(_duplicate_id_issues(environment["states"], f"environments.{environment['id']}.states"))
        state_ids = {state["id"] for state in environment["states"] if _valid_id(state.get("id"))}
        if not _valid_id(environment.get("defaultStateId")) or environment["defaultStateId"] not in state_ids:
            issues.append(_project_issue("environment.state.unknown", f"Environment {environment['id']!r} has unknown default state", f"environments.{environment['id']}.defaultStateId"))
        if all(_valid_id(state.get("id")) and ("extends" not in state or _valid_id(state.get("extends"))) for state in environment["states"]):
            issues.extend(validate_state_graph(environment["states"], entity_kind="environment", entity_id=environment["id"]))
        for view in environment["views"]:
            asset = assets.get(view["assetId"]) if _valid_id(view.get("assetId")) else None
            if asset is None or asset["type"] != "picture":
                issues.append(_project_issue("reference.binding.type_mismatch", f"Environment view asset {view['assetId']!r} must be a picture", f"environments.{environment['id']}.views.{view['id']}"))
    orders = sorted(generation["order"] for generation in project["generations"] if isinstance(generation.get("order"), int))
    if orders != list(range(1, len(project["generations"]) + 1)):
        issues.append(_project_issue("schema.media_manifest.generation_order", "Generation orders must be contiguous from 1", "media_manifest.generations"))
    mode = project.get("mode", "auto")
    if mode != "chained_multishot" and (len(project["generations"]) != 1 or project["generations"][0].get("id") != "g1"):
        issues.append(_project_issue("schema.media_manifest.generation_mode", "Ordinary modes require exactly generation g1", "media_manifest.generations"))
    if mode in {"i2va", "fl2va", "l2va"} and len(project["generations"]) == 1:
        bindings = project["generations"][0]["bindings"]
        pictures = sorted(binding["slotIndex"] for binding in bindings if assets.get(binding["assetId"], {}).get("type") == "picture")
        expected = [1, 2] if mode == "fl2va" else [1]
        if pictures[:len(expected)] != expected:
            issues.append(_project_issue("reference.binding.fixed_mode", f"Mode {mode} requires picture slots {expected}", "generations.g1.bindings"))
    return issues


def _legacy_project(value: str | dict | list | None) -> dict[str, Any]:
    parsed = parse_media_manifest(value)
    if isinstance(value, str):
        canonical = value.strip() if value.strip() else ""
    else:
        canonical = _canonical_json(value) if value is not None else ""
    return {
        "schemaVersion": 1,
        "valid": not parsed["errors"],
        "errors": list(parsed["errors"]),
        "warnings": list(parsed["warnings"]),
        "diagnostics": [
            _project_issue("schema.media_manifest.legacy_error", message) for message in parsed["errors"]
        ],
        "canonicalJson": canonical,
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "legacy": parsed,
        "legacyValue": value,
        "generations": {},
    }


def parse_media_project(value: str | dict | list | None) -> dict[str, Any]:
    """Parse a legacy manifest or compile a canonical logical media project v2."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return _legacy_project(value)
    if isinstance(value, str):
        if value.strip().lower() in ASPECT_RATIOS:
            return _legacy_project(value)
        try:
            data = json.loads(value, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, _DuplicateKeyError) as exc:
            message = exc.msg if isinstance(exc, json.JSONDecodeError) else str(exc)
            diagnostic = _project_issue("schema.media_manifest.invalid_json", f"media_manifest is invalid JSON: {message}")
            return {
                "schemaVersion": None, "valid": False, "errors": [diagnostic["message"]], "warnings": [],
                "diagnostics": [diagnostic], "canonicalJson": "", "digest": "", "generations": {},
            }
    else:
        data = value
    if not isinstance(data, dict) or "schemaVersion" not in data:
        return _legacy_project(value)
    if data.get("schemaVersion") != MEDIA_MANIFEST_SCHEMA_VERSION:
        diagnostic = _project_issue(
            "schema.media_manifest.unsupported_version",
            f"Unsupported media_manifest schemaVersion {data.get('schemaVersion')!r}; expected 2",
            "media_manifest.schemaVersion",
        )
        raw = _canonical_json(data)
        return {
            "schemaVersion": data.get("schemaVersion"), "valid": False, "errors": [diagnostic["message"]],
            "warnings": [], "diagnostics": [diagnostic], "canonicalJson": raw,
            "digest": hashlib.sha256(raw.encode("utf-8")).hexdigest(), "generations": {},
        }
    shape_issues = _validate_v2_shape(data)
    canonical = _canonical_json(data)
    if shape_issues:
        return {
            "schemaVersion": 2, "valid": False, "errors": [issue["message"] for issue in shape_issues],
            "warnings": [], "diagnostics": shape_issues, "canonicalJson": canonical,
            "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(), "project": data, "generations": {},
        }
    semantic_issues = _validate_v2_semantics(data)
    if semantic_issues:
        return {
            "schemaVersion": 2, "valid": False, "errors": [issue["message"] for issue in semantic_issues],
            "warnings": [], "diagnostics": semantic_issues, "canonicalJson": canonical,
            "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(), "project": data, "generations": {},
        }
    generation_states, continuity_issues = compile_generation_states(data)
    semantic_issues.extend(continuity_issues)
    generation_results: dict[str, dict[str, Any]] = {}
    assets_by_id = {asset["id"]: asset for asset in data["assets"]}
    for generation in sorted(data["generations"], key=lambda item: item["order"]):
        generation_for_resolution = dict(generation)
        generation_for_resolution["subjectStates"] = [dict(item) for item in generation["subjectStates"]]
        generation_for_resolution["environmentStates"] = [dict(item) for item in generation["environmentStates"]]
        state = generation_states.get(generation["id"], {})
        for selection in generation_for_resolution["subjectStates"]:
            selection["resolvedStateId"] = state.get("subjects", {}).get(selection["subjectId"], selection.get("stateId"))
        for selection in generation_for_resolution["environmentStates"]:
            selection["resolvedStateId"] = state.get("environments", {}).get(selection["environmentId"], selection.get("stateId"))
        resolution = resolve_generation_references(data, generation_for_resolution)
        counts = resolution["counts"]
        total_files = resolution["totalFiles"]
        mode = data.get("mode", "auto")
        mode_invalid = (
            (mode == "t2va" and total_files != 0)
            or (mode in {"i2va", "l2va"} and (counts["picture"] != 1 or total_files != 1))
            or (mode == "fl2va" and (counts["picture"] != 2 or total_files != 2))
            or (mode == "ref2va" and (total_files == 0 or not (counts["picture"] or counts["video"])))
        )
        if mode_invalid:
            resolution["issues"].append(_project_issue(
                "reference.binding.mode_mismatch",
                f"Generation {generation['id']} bindings do not match mode {mode}",
                f"generations.{generation['id']}.bindings",
            ))
        for asset_id in resolution["activeAssetIds"]:
            if assets_by_id[asset_id].get("available", True) is False:
                resolution["issues"].append(_project_issue("reference.activation.unavailable", f"Unavailable asset {asset_id!r} is active", f"generations.{generation['id']}.activation"))
        resolution["initialState"] = state
        resolution["stateDigest"] = state.get("initialDigest", "")
        generation_results[generation["id"]] = resolution
        semantic_issues.extend(resolution["issues"])
    return {
        "schemaVersion": 2,
        "valid": not semantic_issues,
        "errors": [issue["message"] for issue in semantic_issues],
        "warnings": [],
        "diagnostics": semantic_issues,
        "canonicalJson": canonical,
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "project": data,
        "generations": generation_results,
    }


def _legacy_projection_v2(compiled: dict[str, Any]) -> dict[str, Any]:
    if not compiled.get("valid") or not compiled.get("project"):
        return {"items": [], "subjects": [], "mode": "", "warnings": [], "errors": list(compiled.get("errors", ())) }
    project = compiled["project"]
    first_generation = next(iter(compiled.get("generations", {}).values()), {"inputMap": {}})
    input_map = first_generation.get("inputMap", {})
    first_generation_id = next(iter(compiled.get("generations", {})), None)
    generation_contract = next((item for item in project.get("generations", ()) if item.get("id") == first_generation_id), {})
    binding_by_asset = {item.get("assetId"): item for item in generation_contract.get("bindings", ())}
    items: list[dict[str, Any]] = []
    for position, asset in enumerate(project["assets"], start=1):
        label = input_map.get(asset["id"])
        if not label:
            continue
        item = dict(asset)
        item.update({"label": label, "position": position, "duration_seconds": float(asset.get("durationSeconds", 0))})
        role = binding_by_asset.get(asset["id"], {}).get("role")
        if not role and project.get("mode") in {"i2va", "l2va", "fl2va"} and asset.get("type") == "picture":
            if project["mode"] == "i2va":
                role = "first_frame"
            elif project["mode"] == "l2va":
                role = "last_frame"
            else:
                picture_bindings = sorted(
                    (binding for binding in generation_contract.get("bindings", ())
                     if next((candidate for candidate in project["assets"] if candidate.get("id") == binding.get("assetId") and candidate.get("type") == "picture"), None)),
                    key=lambda binding: binding.get("slotIndex", 0),
                )
                position_in_pictures = next((index for index, binding in enumerate(picture_bindings) if binding.get("assetId") == asset["id"]), -1)
                if position_in_pictures == 0:
                    role = "first_frame"
                elif position_in_pictures == len(picture_bindings) - 1:
                    role = "last_frame"
        if role and role != "reference":
            item["role"] = role
        soundtrack = input_map.get(f"{asset['id']}:soundtrack")
        if soundtrack:
            item["soundtrack_label"] = soundtrack
            item["audio_mode"] = asset.get("audioMode")
        items.append(item)
    subjects = [
        {
            "label": f"<Subject {subject['h3Index']}>",
            "description": subject["description"],
            "sources": [input_map[asset_id] for asset_id in subject["identityAssetIds"] if asset_id in input_map],
            "family": "character",
            **({"voice_source": input_map[subject["defaultVoiceAssetId"]]}
               if subject.get("defaultVoiceAssetId") in input_map else {}),
        }
        for subject in project["subjects"]
    ]
    subjects.extend({
        "label": f"<Subject {prop['h3Index']}>",
        "description": prop.get("description") or prop["name"],
        "sources": [input_map[asset_id] for asset_id in prop["designAssetIds"] if asset_id in input_map],
        "family": "design",
        "name": prop["name"],
    } for prop in project.get("props", []))
    counts = {kind: sum(item["type"] == kind for item in items) for kind in ("picture", "video", "audio")}
    counts["audio"] += sum(bool(item.get("soundtrack_label")) for item in items)
    return {
        "items": items, "subjects": subjects, "mode": project.get("mode", ""),
        "warnings": list(compiled.get("warnings", ())), "errors": list(compiled.get("errors", ())),
        "counts": counts, "totalFiles": len(items),
        "videoSeconds": sum(item["duration_seconds"] for item in items if item["type"] == "video"),
        "audioSeconds": sum(item["duration_seconds"] for item in items if item["type"] == "audio") + sum(item["duration_seconds"] for item in items if item.get("soundtrack_label")),
    }


def manifest_context_for_generation(compiled: dict[str, Any], generation_id: str) -> str:
    """Render only the logical resources active and bound in one generation."""
    if compiled.get("schemaVersion") != 2:
        return manifest_context(compiled.get("legacyValue"))
    project = compiled.get("project", {})
    resolved = compiled.get("generations", {}).get(generation_id)
    if not resolved:
        return ""
    active_resources = {(item["kind"], item["id"]) for item in resolved["activeResources"]}
    active_assets = set(resolved["activeAssetIds"])
    input_map = resolved["inputMap"]
    state = resolved.get("initialState", {})
    lines = [f"CONNECTED MEDIA PROJECT — GENERATION {generation_id} (only active resources are authoritative):"]
    if input_map:
        lines.append("PHYSICAL INPUT MAP:")
        for asset in project["assets"]:
            if asset["id"] not in active_assets or asset["id"] not in input_map:
                continue
            detail = asset.get("analysis", asset.get("description", ""))
            if isinstance(detail, dict):
                detail = "; ".join(f"{key}={value}" for key, value in detail.items() if value not in (None, "", [], {}))
            suffix = f"; {detail}" if detail else ""
            lines.append(f"- {input_map[asset['id']]} = asset {asset['id']} ({asset['name']}){suffix}")
            soundtrack = input_map.get(f"{asset['id']}:soundtrack")
            if soundtrack:
                lines.append(f"- {soundtrack} = {asset.get('audioMode')} soundtrack from {input_map[asset['id']]}")
    for subject in project["subjects"]:
        if ("subject", subject["id"]) not in active_resources:
            continue
        lines.append(f"<Subject {subject['h3Index']}> ({subject['name']}): {subject['description']}")
        state_id = state.get("subjects", {}).get(subject["id"], subject["baseAppearanceStateId"])
        appearance = resolve_state(subject["appearanceStates"], state_id, "attributes")
        details = "; ".join(f"{key}: {value}" for key, value in appearance["attributes"].items() if value not in (None, "", [], {}))
        if details or appearance["description"]:
            lines.append(f"- Initial appearance {state_id}: {details or appearance['description']}")
        voice_asset_id = subject.get("defaultVoiceAssetId")
        if voice_asset_id in input_map:
            lines.append(
                f"- {input_map[voice_asset_id]} supplies the default voice timbre and delivery for "
                f"<Subject {subject['h3Index']}>; it supplies no dialogue words."
            )
    for prop in project.get("props", []):
        if ("prop", prop["id"]) not in active_resources:
            continue
        description = prop.get("description") or "No additional design description."
        category = f"; category: {prop['category']}" if prop.get("category") else ""
        lines.append(
            f"<Subject {prop['h3Index']}> ({prop['name']}), family design{category}: {description}"
        )
        sources = [input_map[asset_id] for asset_id in prop["designAssetIds"] if asset_id in input_map]
        if sources:
            lines.append(
                f"- {', '.join(sources)} supplies only the reusable physical design of "
                f"<Subject {prop['h3Index']}>; do not copy source people, background, camera, lighting, or text."
            )
    for environment in project["environments"]:
        if ("environment", environment["id"]) not in active_resources:
            continue
        permanent = "; ".join(f"{key}: {value}" for key, value in environment["permanent"].items() if value not in (None, "", [], {}))
        lines.append(f"Environment {environment['id']} ({environment['name']}), permanent facts: {permanent or 'no additional permanent facts'}")
        state_id = state.get("environments", {}).get(environment["id"], environment["defaultStateId"])
        temporary = resolve_state(environment["states"], state_id, "temporary")
        details = "; ".join(f"{key}: {value}" for key, value in temporary["temporary"].items() if value not in (None, "", [], {}))
        if details:
            lines.append(f"- Initial environment state {state_id}: {details}")
        view_ids = set(state.get("views", {}).get(environment["id"], ()))
        for view in environment["views"]:
            if view["id"] in view_ids and view["assetId"] in input_map:
                suffix = f"; {view['description']}" if view.get("description") else ""
                lines.append(f"- View {view['id']} ({view['role']}) uses {input_map[view['assetId']]}{suffix}")
    return "\n".join(lines)


def manifest_context(value: str | dict | list | None) -> str:
    parsed = parse_media_manifest(value)
    if not parsed["items"]:
        return ""
    lines = ["CONNECTED MEDIA MANIFEST (labels below are authoritative and follow effective input order):"]
    for item in parsed["items"]:
        raw_role = item.get("role", item.get("roles", item.get("purpose", "unspecified role")))
        role = ", ".join(map(str, raw_role)) if isinstance(raw_role, list) else str(raw_role).strip()
        role = role.replace("_", " ")
        raw_analysis = item.get("analysis", item.get("description", ""))
        if isinstance(raw_analysis, dict):
            analysis = "; ".join(
                f"{key}={value}" for key, value in raw_analysis.items()
                if key != "transcript" and value not in (None, "", (), [])
            )
        else:
            analysis = str(raw_analysis).strip()
        extra = f"; analysis: {analysis}" if analysis else ""
        if item.get("reuse_mode"):
            extra += f"; reuse mode: {str(item['reuse_mode']).replace('_', ' ')}"
        lines.append(f"- Connected asset {item['label']} has role: {role}{extra}")
        if item.get("soundtrack_label"):
            lines.append(
                f"- Connected asset {item['soundtrack_label']} is the {item.get('audio_mode')} soundtrack from "
                f"{item['label']}"
            )
    if parsed.get("subjects"):
        lines.append("AUTHORITATIVE SUBJECT DEFINITIONS (supports multiple subjects per asset and multiple assets per subject):")
        for subject in parsed["subjects"]:
            sources = ", ".join(subject["sources"])
            family = f" (family {subject['family']})" if subject.get("family") else ""
            lines.append(f"{subject['label']}{family} is {subject['description']} from {sources}.")
            if subject.get("voice_source"):
                lines.append(f"- {subject['voice_source']} supplies the default voice timbre and delivery for {subject['label']}; it supplies no dialogue words.")
    return "\n".join(lines)


def _detect_lang_fallback(text: str) -> str:
    try:
        from .prompt_guides import _detect_language
        return _detect_language(text, default="English")
    except Exception:
        try:
            from prompt_guides import _detect_language
            return _detect_language(text, default="English")
        except Exception:
            return "English"


def manifest_dialogue(value: str | dict | list | None) -> list[tuple[str, str, str]]:
    """Return authoritative transcribed reference-audio dialogue."""
    found: list[tuple[str, str, str]] = []
    for item in parse_media_manifest(value)["items"]:
        if item["type"] == "video" and not item.get("soundtrack_label"):
            continue
        if str(item.get("reuse_mode", "")).strip().lower() == "reference_only":
            continue
        analysis = item.get("analysis", {})
        transcript = item.get("transcript", analysis.get("transcript") if isinstance(analysis, dict) else None)
        if not transcript:
            continue
        entries = transcript if isinstance(transcript, list) else [transcript]
        for entry in entries:
            if isinstance(entry, str):
                cleaned = _normalize_transcript_text(entry)
                lang = _detect_lang_fallback(cleaned)
                found.append((
                    item.get("soundtrack_label", item["label"]),
                    lang,
                    cleaned,
                ))
            elif isinstance(entry, dict) and (entry.get("text") or entry.get("unclear")):
                if str(entry.get("reuse_mode", item.get("reuse_mode", ""))).strip().lower() == "reference_only":
                    continue
                transcript_text = "[unclear]" if entry.get("unclear") else _normalize_transcript_text(entry.get("text", ""))
                if not transcript_text:
                    transcript_text = "[unclear]"
                lang = str(entry.get("language") or _detect_lang_fallback(transcript_text))
                found.append((
                    str(entry.get("source", item.get("soundtrack_label", item["label"]))),
                    lang,
                    transcript_text,
                ))
    return found


def _normalize_transcript_text(value: Any) -> str:
    """Apply the official conservative transcript punctuation cleanup."""
    text = re.sub(r"[~～]{2,}", "", str(value or "")).strip()
    text = re.sub(r"^[\s•●▪◦*-]+", "", text).strip()
    text = re.sub(r"([!?.,])\1+", r"\1", text)
    if text and text != "[unclear]" and text[-1] not in ".?!":
        text += "."
    return text


MIN_GENERATION_SECONDS = 4.0
TRAINED_GENERATION_SECONDS = 15.0
MAX_GENERATION_SECONDS = 150.0


def generation_profile(duration_seconds: float, aspect_ratio: str = "auto", frame_count: int = 0) -> dict[str, Any]:
    """Validate H3 generation geometry and return the effective duration."""
    errors: list[str] = []
    warnings: list[str] = []
    frames = int(frame_count or 0)
    effective = float(duration_seconds)
    if frames:
        if frames < 5 or (frames - 5) % 17:
            errors.append("frame_count must lie on H3's 17k+5 frame grid")
        effective = frames / 24.0
        if abs(float(duration_seconds) - effective) > 0.5:
            warnings.append("frame_count overrides duration_seconds by more than 0.5s; effective duration follows frames/24")
    if not MIN_GENERATION_SECONDS <= effective <= MAX_GENERATION_SECONDS:
        errors.append(
            "MiniMax H3 single-generation duration must be within 4-150 seconds "
            "(the native ComfyUI node accepts up to 3600 frames)"
        )
    elif effective > TRAINED_GENERATION_SECONDS:
        warnings.append(
            "duration exceeds MiniMax H3's approximately 5-15 second trained range; "
            "longer single generations are supported by the native node but are untested and use substantially more memory"
        )
    if aspect_ratio not in ASPECT_RATIOS:
        errors.append(f"Unsupported aspect ratio {aspect_ratio!r}")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "durationSeconds": float(duration_seconds),
        "effectiveDurationSeconds": effective,
        "frameCount": frames,
        "aspectRatio": aspect_ratio,
    }
