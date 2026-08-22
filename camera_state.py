# SPDX-License-Identifier: GPL-3.0-only
"""Strict camera-state primitives used by shot-plan v2.

The module deliberately has no knowledge of media manifests or prompt text.
It validates the user-authored camera grammar and keeps ``cameraEnd`` as a
delta from ``cameraStart`` so a change between both phases is not mistaken for
a conflict.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"

FRAME_ENUMS = {
    "framing": {
        "extreme_close_up", "close_up", "medium_close_up", "medium",
        "medium_wide", "wide", "extreme_wide",
    },
    "angle": {
        "eye_level", "low_angle", "high_angle", "overhead",
        "dutch_static", "worms_eye",
    },
    "viewpoint": {
        "pov", "over_the_shoulder", "mirror_or_reflection", "front",
        "three_quarter", "profile", "rear_three_quarter", "rear",
    },
    "composition": {
        "centered", "rule_of_thirds", "symmetrical", "layered_depth",
        "frame_within_frame", "negative_space", "two_shot", "custom",
    },
    "distance": {"intimate", "near", "medium", "far", "very_far", "custom"},
}

TARGET_KEYS = {"primaryTarget", "secondaryTarget", "foregroundTarget"}
FRAME_KEYS = set(FRAME_ENUMS) | TARGET_KEYS | {
    "compositionNote", "focus", "distanceNote",
}
TARGET_KINDS = {"subject", "environment", "asset"}
FOCUS_MODES = {"single_target", "split_focus", "deep_focus", "custom"}
MOTION_TYPES = {
    "static", "zoom_in", "zoom_out", "push_in", "pull_out", "pan_left",
    "pan_right", "truck_left", "truck_right", "tilt_up", "tilt_down",
    "pedestal_up", "pedestal_down", "arc", "tracking", "shake",
    "roll_clockwise", "roll_counterclockwise",
}
PATH_KEYS = {"motionType", "amplitude", "speed", "easing", "timing"}


def _short_text(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{path} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{path} must not be blank")
    if len(text) > 500:
        raise ValueError(f"{path} exceeds 500 characters")
    if "\x00" in text:
        raise ValueError(f"{path} contains a NUL character")
    return text


def _identifier(value: Any, path: str) -> str:
    import re

    if not isinstance(value, str) or not re.fullmatch(ID_PATTERN, value.strip()):
        raise ValueError(
            f"{path} must be 1-64 ASCII letters, digits, dot, underscore, or hyphen"
        )
    return value.strip()


def normalize_target(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    raw = dict(value)
    kind = raw.get("kind")
    if kind == "text":
        allowed = {"kind", "text"}
        unknown = sorted(set(raw) - allowed)
        if unknown:
            raise ValueError(f"{path} contains unsupported keys: {unknown}")
        if set(raw) != allowed:
            raise ValueError(f"{path} with kind 'text' requires text")
        return {"kind": "text", "text": _short_text(raw["text"], f"{path}.text")}
    allowed = {"kind", "id"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"{path} contains unsupported keys: {unknown}")
    if kind not in TARGET_KINDS:
        raise ValueError(f"{path}.kind must be one of: asset, environment, subject, text")
    if set(raw) != allowed:
        raise ValueError(f"{path} with kind {kind!r} requires id")
    return {"kind": kind, "id": _identifier(raw["id"], f"{path}.id")}


def normalize_focus(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    raw = dict(value)
    allowed = {"mode", "primaryTarget", "secondaryTarget", "note"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"{path} contains unsupported keys: {unknown}")
    mode = raw.get("mode")
    if mode not in FOCUS_MODES:
        raise ValueError(f"{path}.mode must be one of: {', '.join(sorted(FOCUS_MODES))}")
    result: dict[str, Any] = {"mode": mode}
    for key in ("primaryTarget", "secondaryTarget"):
        if key in raw:
            result[key] = normalize_target(raw[key], f"{path}.{key}")
    if "note" in raw:
        result["note"] = _short_text(raw["note"], f"{path}.note")
    return result


def normalize_camera_frame(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    raw = dict(value)
    if not raw:
        raise ValueError(f"{path} must contain at least one camera property")
    unknown = sorted(set(raw) - FRAME_KEYS)
    if unknown:
        raise ValueError(f"{path} contains unsupported keys: {unknown}")
    result: dict[str, Any] = {}
    for key, choices in FRAME_ENUMS.items():
        if key in raw:
            value = raw[key]
            if value not in choices:
                raise ValueError(f"{path}.{key} must be one of: {', '.join(sorted(choices))}")
            result[key] = value
    for key in TARGET_KEYS:
        if key in raw:
            result[key] = normalize_target(raw[key], f"{path}.{key}")
    for key in ("compositionNote", "distanceNote"):
        if key in raw:
            result[key] = _short_text(raw[key], f"{path}.{key}")
    if "focus" in raw:
        result["focus"] = normalize_focus(raw["focus"], f"{path}.focus")
    return result


def normalize_camera_end_delta(value: Any, start: Mapping[str, Any], path: str) -> dict[str, Any]:
    """Validate an end frame and retain only fields differing from the start."""
    end = normalize_camera_frame(value, path)
    return {key: item for key, item in end.items() if start.get(key) != item}


def resolve_camera_end(start: Mapping[str, Any] | None,
                       end_delta: Mapping[str, Any] | None) -> dict[str, Any]:
    resolved = dict(start or {})
    resolved.update(dict(end_delta or {}))
    return resolved


def normalize_camera_path(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    raw = dict(value)
    unknown = sorted(set(raw) - PATH_KEYS)
    if unknown:
        raise ValueError(f"{path} contains unsupported keys: {unknown}")
    motion = raw.get("motionType")
    if motion not in MOTION_TYPES:
        raise ValueError(f"{path}.motionType must be one of: {', '.join(sorted(MOTION_TYPES))}")
    result = {"motionType": motion}
    choices = {
        "amplitude": {"small", "medium", "large"},
        "speed": {"slow", "normal", "fast"},
        "easing": {"linear", "ease_in", "ease_out", "ease_in_out"},
        "timing": {"throughout", "during_opening", "after_opening", "during_action", "before_cut"},
    }
    for key, allowed in choices.items():
        if key in raw:
            if raw[key] not in allowed:
                raise ValueError(f"{path}.{key} must be one of: {', '.join(sorted(allowed))}")
            result[key] = raw[key]
    if motion == "static" and any(key in result for key in ("amplitude", "speed", "easing")):
        raise ValueError(f"{path} cannot set amplitude, speed, or easing when motionType is 'static'")
    return result


def camera_frame_sentence(frame: Mapping[str, Any], phase: str = "start") -> str:
    """Render only explicit structured values; never infer an aesthetic."""
    if not frame:
        return ""
    labels = {
        "framing": "framing", "angle": "angle", "viewpoint": "viewpoint",
        "composition": "composition", "distance": "distance",
    }
    parts = [f"{labels[key]} {str(frame[key]).replace('_', ' ')}" for key in labels if key in frame]
    for key, label in (("compositionNote", "composition detail"), ("distanceNote", "distance detail")):
        if key in frame:
            parts.append(f"{label} {frame[key]}")
    prefix = "Camera starts with" if phase == "start" else "Camera ends with"
    return prefix + " " + ", ".join(parts) + "." if parts else ""


def camera_path_sentence(path: Mapping[str, Any]) -> str:
    if not path:
        return ""
    motion = str(path["motionType"]).replace("_", " ")
    if motion == "static":
        return "The camera remains static throughout the shot."
    qualifiers = [str(path[key]).replace("_", " ") for key in ("amplitude", "speed") if key in path]
    text = f"The camera performs a {motion}"
    if qualifiers:
        text += " with " + " and ".join(qualifiers)
    if "easing" in path:
        text += f", using {str(path['easing']).replace('_', ' ')} easing"
    if "timing" in path:
        text += f", {str(path['timing']).replace('_', ' ')}"
    return text + "."
