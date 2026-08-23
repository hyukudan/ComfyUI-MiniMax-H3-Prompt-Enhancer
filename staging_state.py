# SPDX-License-Identifier: GPL-3.0-only
"""Qualitative subject staging primitives for Shot Plan v2."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
POINT_KEYS = {"x", "y", "z", "facing", "facingTarget"}
FACING = {"camera", "travel", "frame_left", "frame_right", "away_from_camera", "target"}
MOVEMENTS = {"holds", "walks", "runs", "crosses", "approaches", "withdraws", "circles"}


def _identifier(value: Any, path: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(ID_PATTERN, value.strip()):
        raise ValueError(f"{path} must be a valid 1-64 character id")
    return value.strip()


def _coordinate(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not -1 <= result <= 1:
        raise ValueError(f"{path} must be finite and between -1 and 1")
    return result


def _target(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    raw = dict(value)
    if set(raw) != {"kind", "id"} or raw.get("kind") != "subject":
        raise ValueError(f"{path} must reference one subject id")
    return {"kind": "subject", "id": _identifier(raw["id"], f"{path}.id")}


def _point(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    raw = dict(value)
    unknown = sorted(set(raw) - POINT_KEYS)
    if unknown:
        raise ValueError(f"{path} contains unsupported keys: {unknown}")
    result = {key: _coordinate(raw.get(key), f"{path}.{key}") for key in ("x", "y", "z")}
    facing = raw.get("facing", "camera")
    if facing not in FACING:
        raise ValueError(f"{path}.facing is unsupported")
    result["facing"] = facing
    if "facingTarget" in raw:
        result["facingTarget"] = _target(raw["facingTarget"], f"{path}.facingTarget")
    if ("facingTarget" in result) != (facing == "target"):
        raise ValueError(f"{path}.facingTarget requires facing 'target', and target facing requires facingTarget")
    return result


def normalize_staging(value: Any, path: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 16:
        raise ValueError(f"{path} must be an array containing at most 16 subject placements")
    result = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, Mapping):
            raise ValueError(f"{item_path} must be an object")
        raw = dict(item)
        unknown = sorted(set(raw) - {"subjectId", "start", "end", "movement"})
        if unknown:
            raise ValueError(f"{item_path} contains unsupported keys: {unknown}")
        subject_id = _identifier(raw.get("subjectId"), f"{item_path}.subjectId")
        if subject_id in seen:
            raise ValueError(f"{path} contains duplicate subjectId {subject_id!r}")
        seen.add(subject_id)
        placement: dict[str, Any] = {"subjectId": subject_id, "start": _point(raw.get("start"), f"{item_path}.start")}
        if "end" in raw:
            placement["end"] = _point(raw["end"], f"{item_path}.end")
        movement = raw.get("movement", "holds")
        if movement not in MOVEMENTS:
            raise ValueError(f"{item_path}.movement is unsupported")
        if movement != "holds" and "end" not in placement:
            raise ValueError(f"{item_path}.movement {movement!r} requires an end placement")
        if movement != "holds":
            placement["movement"] = movement
        result.append(placement)
    return result


def _name(subject_id: str, labels: Mapping[str, str] | None) -> str:
    if labels and subject_id in labels:
        return str(labels[subject_id])
    match = re.fullmatch(r"subject\.(\d+)", subject_id)
    if match:
        return f"<Subject {match.group(1)}>"
    value = re.sub(r"[._-]+", " ", subject_id).strip()
    return value[:1].upper() + value[1:]


def _position(point: Mapping[str, Any]) -> str:
    x, y, z = (float(point[key]) for key in ("x", "y", "z"))
    horizontal = "frame left" if x <= -.2 else "frame right" if x >= .2 else "near frame center"
    depth = "in the background" if z <= -.35 else "in the foreground" if z >= .35 else "in the midground"
    height = "at ground level" if y <= -.35 else "on an elevated level" if y >= .35 else "at normal standing level"
    return f"{horizontal}, {depth}, {height}"


def _facing(point: Mapping[str, Any], labels: Mapping[str, str] | None) -> str:
    mode = point.get("facing", "camera")
    if mode == "camera":
        return "facing the camera"
    if mode == "away_from_camera":
        return "facing away from the camera"
    if mode == "travel":
        return "facing the direction of movement"
    if mode in {"frame_left", "frame_right"}:
        return f"facing {mode.replace('_', ' ')}"
    target = point.get("facingTarget", {})
    return f"facing {_name(str(target.get('id', '')), labels)}"


def staging_sentence(staging: list[Mapping[str, Any]],
                     subject_labels: Mapping[str, str] | None = None) -> str:
    if not staging:
        return ""
    lines = []
    for placement in staging:
        name = _name(str(placement["subjectId"]), subject_labels)
        start = placement["start"]
        text = f"{name} begins {_position(start)}, {_facing(start, subject_labels)}"
        if placement.get("end"):
            movement = str(placement.get("movement", "moves"))
            end = placement["end"]
            text += f", then {movement} to {_position(end)}, {_facing(end, subject_labels)}"
        else:
            text += " and holds that placement"
        lines.append(text + ".")
    return "Subject staging: " + " ".join(lines)
