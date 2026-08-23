# SPDX-License-Identifier: GPL-3.0-only
"""Strict camera-state primitives used by shot-plan v2.

The module deliberately has no knowledge of media manifests or prompt text.
It validates the user-authored camera grammar and keeps ``cameraEnd`` as a
delta from ``cameraStart`` so a change between both phases is not mistaken for
a conflict.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
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
    "coordinateSpace", "pathShape", "anchorTarget", "waypoints",
}
WAYPOINT_KEYS = {
    "id", "at", "x", "y", "z", "framing", "angle", "hold",
    "aimMode", "aimTarget", "panDegrees", "tiltDegrees",
}


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
        if "aimMode" in raw:
            if raw["aimMode"] not in {"anchor", "travel", "custom", "target"}:
                raise ValueError(f"{item_path}.aimMode must be anchor, travel, custom, or target")
            normalized["aimMode"] = raw["aimMode"]
        if "aimTarget" in raw:
            normalized["aimTarget"] = normalize_target(raw["aimTarget"], f"{item_path}.aimTarget")
        for key, minimum, maximum in (
            ("panDegrees", -180.0, 180.0), ("tiltDegrees", -90.0, 90.0),
        ):
            if key in raw:
                normalized[key] = _finite_number(raw[key], f"{item_path}.{key}", minimum, maximum)
        if any(key in normalized for key in ("panDegrees", "tiltDegrees")) and normalized.get("aimMode") != "custom":
            raise ValueError(f"{item_path} panDegrees/tiltDegrees require aimMode 'custom'")
        if ("aimTarget" in normalized) != (normalized.get("aimMode") == "target"):
            raise ValueError(f"{item_path} aimTarget requires aimMode 'target', and target mode requires aimTarget")
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
    if "anchorTarget" in raw:
        result["anchorTarget"] = normalize_target(raw["anchorTarget"], f"{path}.anchorTarget")
    if "waypoints" in raw:
        result["waypoints"] = normalize_camera_waypoints(raw["waypoints"], f"{path}.waypoints")
    if motion == "static" and any(
        key in result for key in ("amplitude", "speed", "easing", "coordinateSpace", "pathShape", "anchorTarget", "waypoints")
    ):
        raise ValueError(f"{path} cannot set movement properties when motionType is 'static'")
    if "waypoints" in result and "coordinateSpace" not in result:
        result["coordinateSpace"] = "subject"
    if "waypoints" in result and "pathShape" not in result:
        result["pathShape"] = "smooth"
    return result


def _target_label(target: Mapping[str, Any] | None,
                  target_labels: Mapping[tuple[str, str], str] | None = None) -> str:
    if not isinstance(target, Mapping):
        return "the declared target"
    if target.get("kind") == "text":
        return str(target.get("text", "the declared target"))
    kind = str(target.get("kind", "target"))
    target_id = str(target.get("id", ""))
    if target_labels and (kind, target_id) in target_labels:
        return str(target_labels[(kind, target_id)])
    subject_number = re.fullmatch(r"subject\.(\d+)", target_id)
    if kind == "subject" and subject_number:
        return f"<Subject {subject_number.group(1)}>"
    readable = re.sub(r"[._-]+", " ", target_id).strip()
    return readable[:1].upper() + readable[1:] if readable else f"the {kind}"


def camera_frame_sentence(frame: Mapping[str, Any], phase: str = "start",
                          target_labels: Mapping[tuple[str, str], str] | None = None) -> str:
    """Render every explicit frame fact in natural camera prose."""
    if not frame:
        return ""
    parts = [
        str(frame[key]).replace("_", " ")
        for key in ("framing", "angle", "viewpoint", "composition", "distance")
        if key in frame
    ]
    for key, label in (
        ("primaryTarget", "centered on"), ("secondaryTarget", "also including"),
        ("foregroundTarget", "with the foreground occupied by"),
    ):
        if key in frame:
            parts.append(f"{label} {_target_label(frame[key], target_labels)}")
    focus = frame.get("focus")
    if isinstance(focus, Mapping):
        focus_text = {
            "single_target": "single-target focus",
            "split_focus": "split focus",
            "deep_focus": "deep focus",
            "custom": "custom focus",
        }.get(str(focus.get("mode", "")), "authored focus")
        targets = [
            _target_label(focus[key], target_labels)
            for key in ("primaryTarget", "secondaryTarget") if key in focus
        ]
        if targets:
            focus_text += " on " + " and ".join(targets)
        if focus.get("note"):
            focus_text += f" ({focus['note']})"
        parts.append(focus_text)
    for key, label in (("compositionNote", "composition detail"), ("distanceNote", "distance detail")):
        if key in frame:
            parts.append(f"{label} {frame[key]}")
    return ("Start " if phase == "start" else "End ") + ", ".join(parts) + "."


_MOTION_PHRASES = {
    "zoom_in": "zooms in", "zoom_out": "zooms out", "push_in": "pushes in",
    "pull_out": "pulls back", "pan_left": "pans left", "pan_right": "pans right",
    "truck_left": "trucks left", "truck_right": "trucks right", "tilt_up": "tilts up",
    "tilt_down": "tilts down", "pedestal_up": "rises", "pedestal_down": "descends",
    "arc": "arcs around the action", "tracking": "tracks the action",
    "shake": "moves with camera shake", "roll_clockwise": "rolls clockwise",
    "roll_counterclockwise": "rolls counterclockwise",
}


def _progress_words(value: float) -> str:
    if value <= 0.02:
        return "at the start"
    if value < 0.38:
        return "early in the shot"
    if value <= 0.62:
        return "around the midpoint"
    if value < 0.98:
        return "near the end"
    return "at the end"


def _camera_height_band(value: float) -> int:
    if value <= -0.60:
        return 1
    if value <= -0.15:
        return 2
    if value < 0.15:
        return 3
    if value < 0.60:
        return 4
    return 5


def _height_state(value: float, reference: str, *, scene_space: bool = False) -> str:
    band = _camera_height_band(value)
    if scene_space:
        return {
            1: "very low in the framed scene", 2: "low in the framed scene",
            3: "at the scene's eye line", 4: "raised in the framed scene",
            5: "high in the framed scene",
        }[band]
    return {
        1: f"very low, well below {reference}", 2: f"low, below {reference}",
        3: f"level with {reference}", 4: f"raised above {reference}",
        5: f"high above {reference}",
    }[band]


def _height_destination(value: float, reference: str, *, scene_space: bool = False) -> str:
    band = _camera_height_band(value)
    if scene_space:
        return {
            1: "a very low position in the framed scene", 2: "a low position in the framed scene",
            3: "the scene's eye line", 4: "a raised position in the framed scene",
            5: "a high position in the framed scene",
        }[band]
    return {
        1: f"a very low position, well below {reference}", 2: f"a low position, below {reference}",
        3: _eye_line(reference), 4: f"a raised position, still above {reference}",
        5: f"a very elevated position, high above {reference}",
    }[band]


def _eye_line(reference: str, *, scene_space: bool = False) -> str:
    if scene_space:
        return "the scene's eye line"
    if reference.startswith("the ") and reference.endswith("s"):
        return f"{reference}' eye line"
    return f"{reference}'s eye level"


def _qualitative_custom_aim(point: Mapping[str, Any], reference: str, *, scene_space: bool = False) -> str:
    pan = float(point.get("panDegrees", 0.0))
    tilt = float(point.get("tiltDegrees", 0.0))
    if abs(pan) < 20:
        horizontal = "straight ahead"
    elif abs(pan) > 155:
        horizontal = "back toward the space behind the camera"
    else:
        horizontal = f"toward frame {'right' if pan > 0 else 'left'}"
    if tilt >= 20:
        return horizontal + ", angled upward"
    if tilt <= -20:
        return horizontal + ", angled downward"
    band = _camera_height_band(float(point.get("y", 0.0)))
    if band >= 4:
        return horizontal + f", with the lens horizontal rather than tilted down toward {reference}"
    if band <= 2:
        return horizontal + f", with the lens horizontal rather than tilted up toward {reference}"
    return horizontal + ", without tilting the lens up or down"


def _vertical_class(delta: float) -> str:
    magnitude = abs(delta)
    if magnitude < 0.10:
        return "hold"
    if magnitude < 0.35:
        return "drift"
    if magnitude < 0.90:
        return "move"
    return "sweep"


def _vertical_events(waypoints: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    """Resolve authored y deltas once, including cumulative sub-noise."""
    events: dict[int, dict[str, Any]] = {}
    origin_index = 0
    for index in range(1, len(waypoints)):
        previous_y = float(waypoints[index - 1]["y"])
        current_y = float(waypoints[index]["y"])
        raw_delta = current_y - previous_y
        cumulative_delta = current_y - float(waypoints[origin_index]["y"])
        if abs(raw_delta) < 0.10 and abs(cumulative_delta) < 0.15:
            continue
        event_class = _vertical_class(cumulative_delta)
        if event_class == "hold":
            continue
        origin_y = float(waypoints[origin_index]["y"])
        direction = "ascend" if cumulative_delta > 0 else "descend"
        crossed = (origin_y < -0.15 and current_y >= 0.15) or (origin_y >= 0.15 and current_y < -0.15)
        events[index] = {
            "class": event_class, "direction": direction, "delta": cumulative_delta,
            "originY": origin_y, "destinationY": current_y, "crossedEyeLine": crossed,
        }
        origin_index = index
    return events


def _vertical_event_phrase(event: Mapping[str, Any], reference: str, *, scene_space: bool = False) -> str:
    direction = str(event["direction"])
    event_class = str(event["class"])
    destination_y = float(event["destinationY"])
    origin_y = float(event["originY"])
    destination = _height_destination(destination_y, reference, scene_space=scene_space)
    if event_class == "drift" and _camera_height_band(origin_y) == _camera_height_band(destination_y):
        return f"drifts a little {'higher' if direction == 'ascend' else 'lower'} while staying {destination}"
    verbs = {
        ("ascend", "drift"): "drifts a little higher",
        ("ascend", "move"): "rises",
        ("ascend", "sweep"): "climbs steeply",
        ("descend", "drift"): "drifts a little lower",
        ("descend", "move"): "descends",
        ("descend", "sweep"): "plunges",
    }
    verb = verbs[(direction, event_class)]
    crossing = f" past {_eye_line(reference, scene_space=scene_space)}" if event.get("crossedEyeLine") else ""
    return f"{verb}{crossing} to {destination}"


def _vertical_envelope(waypoints: Sequence[Mapping[str, Any]], events: Mapping[int, Mapping[str, Any]],
                       reference: str, *, scene_space: bool = False) -> str:
    start = _height_state(float(waypoints[0]["y"]), reference, scene_space=scene_space)
    end = _height_state(float(waypoints[-1]["y"]), reference, scene_space=scene_space)
    if not events:
        if _camera_height_band(float(waypoints[0]["y"])) in {1, 5}:
            return f"Across this move the camera stays {start}."
        return ""
    directions = [str(event["direction"]) for event in events.values()]
    if len(set(directions)) == 1:
        verb = "ascends" if directions[0] == "ascend" else "descends"
        return f"Across this move the camera only ever {verb}: it starts {start} and ends {end}; keep this height change visible."
    runs = [directions[0]]
    for direction in directions[1:]:
        if direction != runs[-1]:
            runs.append(direction)
    if len(runs) == 2:
        first = "rises" if runs[0] == "ascend" else "descends"
        second = "rises" if runs[1] == "ascend" else "descends"
        return f"Across this move the camera first {first}, then {second}, ending {end}; keep both height changes visible."
    return f"Across this move the camera changes height several times, ending {end}; keep each change visible."


def _waypoint_place(point: Mapping[str, Any], reference: str, *, scene_space: bool = False,
                    include_height: bool = True) -> str:
    x, y, z = (float(point[key]) for key in ("x", "y", "z"))
    spatial = []
    if x <= -0.2:
        spatial.append(f"to the left of {reference}")
    elif x >= 0.2:
        spatial.append(f"to the right of {reference}")
    if z <= -0.2:
        spatial.append(f"behind {reference}")
    elif z >= 0.2:
        spatial.append(f"in front of {reference}")
    parts = spatial
    if include_height:
        height = _height_state(y, reference, scene_space=scene_space)
        parts = [height, *spatial] if _camera_height_band(y) in {1, 5} else [*spatial, height]
    radius = (x * x + z * z) ** 0.5
    if radius <= 0.30:
        parts.append("at close distance")
    elif radius <= 0.70:
        parts.append("at medium distance")
    elif radius <= 1.05:
        parts.append("at far distance")
    else:
        parts.append("at a very far distance")
    return ", ".join(parts)


def _resolved_waypoint_aims(path: Mapping[str, Any]) -> list[tuple[str | None, Mapping[str, Any] | None]]:
    result: list[tuple[str | None, Mapping[str, Any] | None]] = []
    previous_mode: str | None = None
    previous_target: Mapping[str, Any] | None = None
    for index, point in enumerate(path.get("waypoints", ())):
        mode = point.get("aimMode")
        target = point.get("aimTarget") if mode == "target" else None
        if not mode:
            if index == 0 and (path.get("anchorTarget") or path.get("coordinateSpace", "subject") == "subject"):
                mode = "anchor"
            else:
                mode, target = previous_mode, previous_target
        resolved = (str(mode) if mode else None, target if isinstance(target, Mapping) else None)
        result.append(resolved)
        previous_mode, previous_target = resolved
    return result


def camera_path_sentence(path: Mapping[str, Any],
                         target_labels: Mapping[tuple[str, str], str] | None = None) -> str:
    if not path:
        return ""
    motion = str(path["motionType"])
    if motion == "static":
        return "The camera remains static throughout the shot."
    text = "The camera " + _MOTION_PHRASES.get(motion, motion.replace("_", " "))
    if "amplitude" in path:
        text += {"small": " with a restrained range", "medium": " with a moderate range", "large": " with a broad range"}[path["amplitude"]]
    if "speed" in path:
        text += f" at {path['speed']} speed"
    if "easing" in path:
        text += {"linear": ", at constant pace", "ease_in": ", accelerating smoothly", "ease_out": ", decelerating smoothly", "ease_in_out": ", easing smoothly in and out"}[path["easing"]]
    if "timing" in path:
        text += ", " + {
            "throughout": "throughout the shot", "during_opening": "during the opening",
            "after_opening": "after the opening", "during_action": "during the action",
            "during_dialogue": "during the dialogue", "after_dialogue": "after the dialogue",
            "before_cut": "before the cut",
        }[path["timing"]]
    waypoints = path.get("waypoints")
    if not waypoints:
        return text + "."
    shape = {"smooth": "smooth", "straight": "straight", "arc_left": "left-curving", "arc_right": "right-curving"}.get(str(path.get("pathShape", "smooth")), "smooth")
    anchor = path.get("anchorTarget")
    anchor_text = _target_label(anchor, target_labels) if isinstance(anchor, Mapping) else (
        "the active subjects" if path.get("coordinateSpace", "subject") == "subject" else "the framed scene"
    )
    scene_space = path.get("coordinateSpace", "subject") == "scene"
    events = _vertical_events(waypoints)
    positions = []
    aims = _resolved_waypoint_aims(path)
    previous_aim_label = None
    for index, point in enumerate(waypoints):
        pieces = [_progress_words(float(point["at"]))]
        if index in events:
            pieces.append(_vertical_event_phrase(events[index], anchor_text, scene_space=scene_space))
        place = _waypoint_place(
            point, anchor_text, scene_space=scene_space,
            include_height=index == 0,
        )
        if place:
            pieces.append(place)
        details = [str(point[key]).replace("_", " ") for key in ("framing", "angle") if key in point]
        if details:
            pieces.append("framed as " + " with ".join(details))
        if point.get("hold"):
            pieces.append("holding momentarily")
        aim_mode, aim_target = aims[index]
        aim_label = previous_aim_label
        if aim_mode == "anchor":
            aim_label = anchor_text
            pieces.append(f"aimed at {aim_label}" if aim_label != previous_aim_label else "maintaining that aim")
        elif aim_mode == "travel":
            aim_label = "the direction of travel"
            event = events.get(index)
            if event:
                travel = "downward" if event["direction"] == "descend" else "climbing"
                pieces.append(f"aiming along its {travel} path")
            else:
                pieces.append("aiming along the direction of travel")
        elif aim_mode == "target" and aim_target:
            aim_label = _target_label(aim_target, target_labels)
            if previous_aim_label and previous_aim_label != aim_label:
                pieces.append(f"smoothly reframing from {previous_aim_label} to {aim_label}")
            elif aim_label == anchor_text:
                pieces.append("keeping the anchor in frame")
            else:
                pieces.append(f"aimed at {aim_label}")
        elif aim_mode == "custom":
            aim_label = "a custom direction"
            pieces.append("turned " + _qualitative_custom_aim(point, anchor_text, scene_space=scene_space))
        previous_aim_label = aim_label
        positions.append(", ".join(pieces))
    relation = "around" if path.get("coordinateSpace", "subject") == "subject" else "through"
    text += f" along a {shape} path {relation} {anchor_text}."
    envelope = _vertical_envelope(waypoints, events, anchor_text, scene_space=scene_space)
    if envelope:
        text += " " + envelope
    text += " " + positions[0][:1].upper() + positions[0][1:]
    if len(positions) > 1:
        text += "; then " + "; then ".join(positions[1:])
    return text + ". Keep this as one continuous camera move without adding a cut."
