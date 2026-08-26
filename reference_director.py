# SPDX-License-Identifier: GPL-3.0-only
"""Physical source contract for the visual H3 Reference Director."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


REFERENCE_DIRECTOR_FORMAT = "minimax-h3-reference-director"
REFERENCE_DIRECTOR_FORMAT_VERSION = 1
REFERENCE_PROJECT_TYPE = "H3_REFERENCE_PROJECT"
SOURCE_STORAGE = "comfy_input"
SOURCE_SUBFOLDER = "minimax_h3_reference_director"

MEDIA_EXTENSIONS = {
    "picture": {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"},
    "video": {".avi", ".mkv", ".mov", ".mp4", ".webm"},
    "audio": {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"},
}
MAX_SOURCE_BYTES = {
    "picture": 64 * 1024 * 1024,
    "audio": 256 * 1024 * 1024,
    "video": 1024 * 1024 * 1024,
}


def media_type_for_filename(filename: str) -> str:
    extension = Path(str(filename)).suffix.lower()
    for media_type, extensions in MEDIA_EXTENSIONS.items():
        if extension in extensions:
            return media_type
    raise ValueError(f"Unsupported reference file extension {extension or '(none)'!r}")


def safe_source_filename(filename: str) -> str:
    """Return a portable basename; never preserve a caller-supplied path."""
    source = Path(str(filename).replace("\\", "/")).name.strip()
    extension = Path(source).suffix.lower()
    media_type_for_filename(source)
    stem = source[: -len(extension)] if extension else source
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-_")[:80] or "reference"
    return f"{stem}{extension}"


def empty_reference_director() -> dict[str, Any]:
    return {"format": REFERENCE_DIRECTOR_FORMAT, "formatVersion": REFERENCE_DIRECTOR_FORMAT_VERSION, "sources": {}}


def parse_reference_director(value: str | dict | None) -> dict[str, Any]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return {"valid": True, "value": empty_reference_director(), "issues": []}
    try:
        data = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError as exc:
        return {"valid": False, "value": None, "issues": [f"Reference Director JSON is invalid: {exc.msg}"]}
    issues: list[str] = []
    if not isinstance(data, dict):
        issues.append("Reference Director must be a JSON object.")
        return {"valid": False, "value": None, "issues": issues}
    if data.get("format") != REFERENCE_DIRECTOR_FORMAT or data.get("formatVersion") != REFERENCE_DIRECTOR_FORMAT_VERSION:
        issues.append("Unsupported Reference Director format or version.")
    if set(data) - {"format", "formatVersion", "sources"}:
        issues.append("Reference Director contains unknown root fields.")
    sources = data.get("sources")
    if not isinstance(sources, dict):
        issues.append("Reference Director sources must be an object keyed by asset ID.")
        sources = {}
    normalized: dict[str, dict[str, Any]] = {}
    allowed = {"storage", "file", "sha256", "mediaType", "originalName", "sizeBytes", "mimeType"}
    for asset_id, source in sources.items():
        field = f"sources.{asset_id}"
        if not isinstance(asset_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", asset_id):
            issues.append(f"{field} has an invalid asset ID.")
            continue
        if not isinstance(source, dict):
            issues.append(f"{field} must be an object.")
            continue
        if set(source) - allowed:
            issues.append(f"{field} contains unknown fields.")
        media_type = source.get("mediaType")
        annotated = source.get("file")
        digest = source.get("sha256")
        if source.get("storage") != SOURCE_STORAGE:
            issues.append(f"{field}.storage must be {SOURCE_STORAGE!r}.")
        if media_type not in MEDIA_EXTENSIONS:
            issues.append(f"{field}.mediaType must be picture, video or audio.")
        if not isinstance(annotated, str) or not annotated.endswith(" [input]"):
            issues.append(f"{field}.file must be an annotated ComfyUI input filename.")
        elif not annotated.startswith(f"{SOURCE_SUBFOLDER}/"):
            issues.append(f"{field}.file must stay inside {SOURCE_SUBFOLDER}/.")
        else:
            relative_name = annotated[len(SOURCE_SUBFOLDER) + 1:-8]
            if Path(relative_name).name != relative_name or ".." in Path(relative_name).parts:
                issues.append(f"{field}.file must not contain directories or traversal segments.")
            try:
                if media_type_for_filename(annotated[:-8]) != media_type:
                    issues.append(f"{field}.mediaType does not match its file extension.")
            except ValueError as exc:
                issues.append(f"{field}.file: {exc}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            issues.append(f"{field}.sha256 must be a lowercase SHA-256 digest.")
        size = source.get("sizeBytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            issues.append(f"{field}.sizeBytes must be a non-negative integer.")
        normalized[asset_id] = {key: source[key] for key in sorted(source) if key in allowed}
    canonical = {"format": REFERENCE_DIRECTOR_FORMAT, "formatVersion": REFERENCE_DIRECTOR_FORMAT_VERSION, "sources": normalized}
    return {"valid": not issues, "value": canonical if not issues else None, "issues": issues}


def canonical_reference_director(value: str | dict | None) -> str:
    parsed = parse_reference_director(value)
    if not parsed["valid"]:
        raise ValueError(" ".join(parsed["issues"]))
    return json.dumps(parsed["value"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_reference_project(reference_director: str | dict | None, media_project: str | dict | None = None,
                            shot_plan: str | dict | None = None) -> dict[str, Any]:
    parsed = parse_reference_director(reference_director)
    if not parsed["valid"]:
        raise ValueError(" ".join(parsed["issues"]))
    def json_value(value, label):
        if value is None or value == "":
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{label} JSON is invalid: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be a JSON object.")
        if value.get("schemaVersion") != 2:
            raise ValueError(f"{label} must use schemaVersion 2.")
        return value
    director = parsed["value"]
    media_value = json_value(media_project, "Media Project")
    shot_value = json_value(shot_plan, "Shot Plan")
    assets = {item.get("id"): item for item in (media_value or {}).get("assets", []) if isinstance(item, dict)}
    sources = director["sources"]
    inputs_by_generation: dict[str, list[dict[str, Any]]] = {}
    issues: list[str] = []
    for asset_id, source in sources.items():
        asset = assets.get(asset_id)
        if not asset:
            issues.append(f"Physical source {asset_id!r} has no logical media asset.")
        elif asset.get("type") != source.get("mediaType"):
            issues.append(f"Physical source {asset_id!r} type does not match its logical media asset.")
    for generation in (media_value or {}).get("generations", []):
        generation_id = str(generation.get("id", ""))
        resolved = []
        bindings = generation.get("bindings", [])
        picture_bindings = sorted(
            (binding for binding in bindings if assets.get(binding.get("assetId"), {}).get("type") == "picture"),
            key=lambda binding: binding.get("slotIndex") if isinstance(binding.get("slotIndex"), int) else 10_000,
        )
        inferred_picture_roles: dict[int, str] = {}
        mode = (media_value or {}).get("mode")
        for index, binding in enumerate(picture_bindings):
            if binding.get("role") in {"first_frame", "last_frame"}:
                inferred_picture_roles[id(binding)] = binding["role"]
            elif mode == "i2va":
                inferred_picture_roles[id(binding)] = "first_frame"
            elif mode == "l2va":
                inferred_picture_roles[id(binding)] = "last_frame"
            elif mode == "fl2va":
                inferred_picture_roles[id(binding)] = "first_frame" if index == 0 else "last_frame" if index == len(picture_bindings) - 1 else "reference"
        for binding in bindings:
            asset_id = binding.get("assetId")
            asset = assets.get(asset_id, {})
            media_type = asset.get("type")
            slot = binding.get("slotIndex")
            label = f"<{str(media_type).title()} {slot}>" if media_type in MEDIA_EXTENSIONS and isinstance(slot, int) else ""
            source = sources.get(asset_id)
            if not source:
                issues.append(f"{generation_id or 'Generation'} binding for {asset_id!r} has no physical file.")
            resolved.append({
                "label": label,
                "assetId": asset_id,
                "mediaType": media_type,
                "slotIndex": slot,
                "role": inferred_picture_roles.get(id(binding), binding.get("role", "reference")),
                "source": source,
            })
            soundtrack_slot = binding.get("soundtrackSlotIndex")
            if media_type == "video" and isinstance(soundtrack_slot, int):
                resolved.append({
                    "label": f"<Audio {soundtrack_slot}>",
                    "assetId": asset_id,
                    "mediaType": "audio",
                    "slotIndex": soundtrack_slot,
                    "role": "video_soundtrack",
                    "source": source,
                })
        media_order = {"picture": 0, "video": 1, "audio": 2}
        resolved.sort(key=lambda item: (
            media_order.get(item.get("mediaType"), 99),
            item.get("slotIndex") if isinstance(item.get("slotIndex"), int) else 10_000,
            str(item.get("assetId", "")),
        ))
        for media_type in ("picture", "video", "audio"):
            slots = [item.get("slotIndex") for item in resolved if item.get("mediaType") == media_type]
            if any(not isinstance(slot, int) or isinstance(slot, bool) or slot < 1 for slot in slots):
                issues.append(f"{generation_id or 'Generation'} {media_type} slots must be positive integers.")
                continue
            if len(slots) != len(set(slots)):
                issues.append(f"{generation_id or 'Generation'} has duplicate {media_type} slot numbers.")
            if set(slots) != set(range(1, len(slots) + 1)):
                issues.append(f"{generation_id or 'Generation'} {media_type} slots must be contiguous from 1.")
        inputs_by_generation[generation_id] = resolved
    payload = {
        "format": "minimax-h3-reference-project",
        "formatVersion": 1,
        "director": director,
        "mediaProject": media_value,
        "shotPlan": shot_value,
        "inputsByGeneration": inputs_by_generation,
        "issues": issues,
    }
    payload["digest"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def reference_context_for_project(reference_project: dict[str, Any], generation_id: str = "") -> str:
    """Compile unambiguous prose for the prompt LLM from the same bindings sent to H3."""
    media = reference_project.get("mediaProject") or {}
    shots = (reference_project.get("shotPlan") or {}).get("shots", [])
    generations = reference_project.get("inputsByGeneration", {})
    if generation_id and generation_id not in generations:
        raise ValueError(f"Unknown reference generation {generation_id!r}.")
    selected = generation_id if generation_id in generations else next(iter(generations), "")
    subjects = {item.get("id"): item for item in media.get("subjects", [])}
    environments = {item.get("id"): item for item in media.get("environments", [])}
    uses: dict[str, list[dict[str, Any]]] = {}
    for shot in shots:
        for use in shot.get("referenceUses", []):
            uses.setdefault(use.get("assetId"), []).append({**use, "shot": shot})
    lines = [
        "AUTHORITATIVE REFERENCE RELATIONSHIPS:",
        "Explicit prompt instructions override reference assignments; references override creative invention.",
    ]
    for item in generations.get(selected, []):
        label = item.get("label") or "<Reference>"
        asset_id = item.get("assetId")
        role = item.get("role", "reference")
        related = uses.get(asset_id, [])
        target_ids = [target for use in related for target in use.get("targetIds", [])]
        subject = next((subjects[target] for target in target_ids if target in subjects), None)
        environment = next((environments[target] for target in target_ids if target in environments), None)
        if not subject:
            subject = next((value for value in subjects.values() if asset_id in value.get("identityAssetIds", [])), None)
        if not environment:
            environment = next((value for value in environments.values() if any(view.get("assetId") == asset_id for view in value.get("views", []))), None)
        if role in {"first_frame", "last_frame"}:
            boundary = "opening" if role == "first_frame" else "closing"
            lines.append(f"- {label} fixes the exact {boundary} frame: preserve its visible composition, subject appearance and pose, environment, lighting and camera at that boundary. Apply only explicitly authored changes away from the fixed frame.")
        elif role in {"identity_reinforcement", "subject_identity"} or subject and item.get("mediaType") == "picture":
            name = subject.get("name", subject.get("id")) if subject else "the assigned subject"
            lines.append(f"- {label} supplies only the stable visual identity of {name}. Preserve identity; do not copy its background, pose, lighting, camera or incidental text.")
        elif role in {"voice", "subject_voice"}:
            name = subject.get("name", subject.get("id")) if subject else "the assigned subject"
            lines.append(f"- {label} supplies voice timbre and delivery only for {name}. It supplies no dialogue words; authored dialogue remains exact.")
        elif role in {"environment_view", "background"} or environment:
            name = environment.get("name", environment.get("id")) if environment else "the assigned environment"
            lines.append(f"- {label} supplies the background/set for {name}. People and movable objects visible in it are not target subjects unless assigned separately.")
        elif role in {"performance", "performance_transfer"}:
            name = subject.get("name", subject.get("id")) if subject else "the assigned subject"
            lines.append(f"- {label} supplies performance timing and body motion for {name}. It does not transfer camera motion unless camera transfer is separately assigned.")
        elif role in {"camera", "camera_transfer"}:
            lines.append(f"- {label} supplies camera motion/composition only for its assigned shot. It does not replace subject identity or environment content.")
        elif role in {"soundtrack", "video_soundtrack"}:
            lines.append(f"- {label} supplies the assigned music or soundtrack. It does not supply dialogue words or visual content.")
        else:
            lines.append(f"- {label} is a {str(role).replace('_', ' ')} reference. Use it only for that explicit role and assigned scope.")
    if len(lines) == 2:
        lines.append("- No physical reference is active for this generation.")
    return "\n".join(lines)
