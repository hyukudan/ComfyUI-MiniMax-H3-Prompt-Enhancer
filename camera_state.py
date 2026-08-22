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
PATH_KEYS = {
    "motionType", "amplitude", "speed", "easing", "timing",
    "coordinateSpace", "pathShape", "waypoints",
}
WAYPOINT_KEYS = {"id", "at", "x", "y", "z", "framing", "angle", "hold"}


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


def _finite_number(value: Any, path: str, minimum: float, maximum: float) -> float:
    import math

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < minimum or result > maximum:
        raise ValueError(f"{path} must be finite and between {minimum:g} and {maximum:g}")
    return result


def normalize_camera_waypoints(value: Any, path: str) -> list[dict[str, Any]]:
    """Validate 2–6 normalized, duration-independent spatial camera keyframes."""
    if not isinstance(value, list) or not 2 <= len(value) <= 6:
        raise ValueError(f"{path} must be an array containing 2-6 waypoints")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    previous_at = -1.0
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, Mapping):
            raise ValueError(f"{item_path} must be an object")
        raw = dict(item)
        unknown = sorted(set(raw) - WAYPOINT_KEYS)
        if unknown:
            raise ValueError(f"{item_path} contains unsupported keys: {unknown}")
        waypoint_id = _identifier(raw.get("id"), f"{item_path}.id")
        if waypoint_id in seen:
            raise ValueError(f"{path} contains duplicate id {waypoint_id!r}")
        seen.add(waypoint_id)
        at = _finite_number(raw.get("at"), f"{item_path}.at", 0.0, 1.0)
        if at <= previous_at:
            raise ValueError(f"{path} at values must be strictly increasing")
        previous_at = at
        normalized: dict[str, Any] = {
            "id": waypoint_id,
            "at": at,
            "x": _finite_number(raw.get("x"), f"{item_path}.x", -1.0, 1.0),
            "y": _finite_number(raw.get("y"), f"{item_path}.y", -1.0, 1.0),
            "z": _finite_number(raw.get("z"), f"{item_path}.z", -1.0, 1.0),
        }
        for key in ("framing", "angle"):
            if key in raw:
                if raw[key] not in FRAME_ENUMS[key]:
                    raise ValueError(
                        f"{item_path}.{key} must be one of: {', '.join(sorted(FRAME_ENUMS[key]))}"
                    )
                normalized[key] = raw[key]
        if "hold" in raw:
            if not isinstance(raw["hold"], bool):
                raise ValueError(f"{item_path}.hold must be boolean")
            if raw["hold"]:
                normalized["hold"] = True
        result.append(normalized)
    if result[0]["at"] != 0.0 or result[-1]["at"] != 1.0:
        raise ValueError(f"{path} must start at 0 and end at 1")
    return result


def normalize_camera_path(value: Any, path: str) -> dict[str, Any]:
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
        "timing": {"throughout", "during_opening", "after_opening", "during_action", "during_dialogue", "after_dialogue", "before_cut"},
    }
    for key, allowed in choices.items():
        if key in raw:
            if raw[key] not in allowed:
                raise ValueError(f"{path}.{key} must be one of: {', '.join(sorted(allowed))}")
            result[key] = raw[key]
    if "coordinateSpace" in raw:
        if raw["coordinateSpace"] not in {"subject", "scene"}:
            raise ValueError(f"{path}.coordinateSpace must be subject or scene")
        result["coordinateSpace"] = raw["coordinateSpace"]
    if "pathShape" in raw:
        if raw["pathShape"] not in {"straight", "smooth", "arc_left", "arc_right"}:
            raise ValueError(f"{path}.pathShape must be straight, smooth, arc_left, or arc_right")
        result["pathShape"] = raw["pathShape"]
    if "waypoints" in raw:
        result["waypoints"] = normalize_camera_waypoints(raw["waypoints"], f"{path}.waypoints")
    if motion == "static" and any(
        key in result for key in ("amplitude", "speed", "easing", "coordinateSpace", "pathShape", "waypoints")
    ):
        raise ValueError(f"{path} cannot set movement properties when motionType is 'static'")
    if "waypoints" in result and "coordinateSpace" not in result:
        result["coordinateSpace"] = "subject"
    if "waypoints" in result and "pathShape" not in result:
        result["pathShape"] = "smooth"
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
    waypoints = path.get("waypoints")
    if waypoints:
        space = str(path.get("coordinateSpace", "subject")).replace("_", " ")
        shape = str(path.get("pathShape", "smooth")).replace("_", " ")
        positions = []
        for index, point in enumerate(waypoints):
            progress = round(float(point["at"]) * 100)
            position = (
                f"{progress}% at relative position "
                f"x={float(point['x']):.2f}, y={float(point['y']):.2f}, z={float(point['z']):.2f}"
            )
            details = [str(point[key]).replace("_", " ") for key in ("framing", "angle") if key in point]
            if details:
                position += " (" + ", ".join(details) + ")"
            if point.get("hold"):
                position += " with a brief hold"
            positions.append(position)
        text += (
            f" along a {shape} path in {space}-relative space, passing "
            + "; then ".join(positions)
        )
    return text + "."
