# SPDX-License-Identifier: GPL-3.0-only

import json
from pathlib import Path

import jsonschema
import pytest

from creative_treatments import parse_shot_plan, shot_plan_instruction
from camera_state import _camera_height_band, _vertical_class
from prompt_guides import _spatial_camera_output_gaps


def _plan(shot):
    return {"schemaVersion": 2, "timingMode": "auto", "shots": [shot]}


def _shot(**values):
    return {"id": "s1", "generationId": "g1", "action": "Juan crosses toward Olivia.", **values}


def test_camera_height_fixture_keeps_python_bands_and_delta_classes_in_sync():
    fixture = json.loads((Path(__file__).parents[1] / "docs" / "fixtures" / "camera_elevation_bands.json").read_text(encoding="utf-8"))
    for row in fixture["bands"]:
        assert _camera_height_band(row["value"]) == row["band"]
    for row in fixture["segments"]:
        delta = row["to"] - row["from"]
        assert _vertical_class(delta) == row["kind"]
        assert (None if row["kind"] == "hold" else "ascend" if delta > 0 else "descend") == row["direction"]


def test_waypoint_named_targets_are_validated_and_compile_as_a_reframe():
    plan = parse_shot_plan(_plan(_shot(cameraPath={
        "motionType": "tracking", "coordinateSpace": "subject",
        "anchorTarget": {"kind": "subject", "id": "juan"},
        "waypoints": [
            {"id": "a", "at": 0, "x": -.5, "y": 0, "z": .5,
             "aimMode": "target", "aimTarget": {"kind": "subject", "id": "juan"}},
            {"id": "b", "at": 1, "x": .5, "y": .2, "z": -.5,
             "aimMode": "target", "aimTarget": {"kind": "subject", "id": "olivia"}},
        ],
    })), 4.0)
    instruction = shot_plan_instruction(plan, "t2va", {"project": {"subjects": [
        {"id": "juan", "name": "Juan"}, {"id": "olivia", "name": "Olivia"},
    ]}})
    assert "smoothly reframing from Juan to Olivia" in instruction
    assert "%" not in instruction.split("  Camera:", 1)[1]
    assert "degrees" not in instruction


def test_waypoint_height_is_explicit_and_not_confused_with_level_lens_aim():
    plan = parse_shot_plan(_plan(_shot(cameraPath={
        "motionType": "tracking", "coordinateSpace": "subject",
        "waypoints": [
            {"id": "high", "at": 0, "x": -.72, "y": 1, "z": .62,
             "aimMode": "custom", "panDegrees": 105, "tiltDegrees": 0},
            {"id": "low", "at": 1, "x": .79, "y": -.85, "z": -.45,
             "aimMode": "custom", "panDegrees": -81, "tiltDegrees": 0},
        ],
    })), 4.0)
    instruction = shot_plan_instruction(plan, "t2va")
    assert "high above the active subjects" in instruction
    assert "a very low position, well below the active subjects" in instruction
    assert "lens horizontal rather than tilted down toward the active subjects" in instruction
    assert "held level" not in instruction


def test_waypoint_height_changes_compile_as_directed_vertical_motion():
    plan = parse_shot_plan(_plan(_shot(cameraPath={
        "motionType": "tracking", "coordinateSpace": "subject",
        "waypoints": [
            {"id": "a", "at": 0, "x": -.72, "y": 1, "z": .62},
            {"id": "b", "at": .5, "x": -.2, "y": .52, "z": -.29},
            {"id": "c", "at": 1, "x": .79, "y": -.85, "z": -.45},
        ],
    })), 4.0)
    instruction = shot_plan_instruction(plan, "t2va")
    assert "only ever descends" in instruction
    assert "descends to a raised position, still above the active subjects" in instruction
    assert "plunges past the active subjects' eye line to a very low position" in instruction
    assert "rising" not in instruction


@pytest.mark.parametrize("heights,expected,forbidden", [
    ([.8, -.4, .2], ("first descends, then rises", "plunges", "rises"), ("only ever descends",)),
    ([0, .03, .04], ("level with the active subjects",), ("rises", "descends", "plunges")),
    ([-.5, -.2, .6], ("only ever ascends", "drifts a little higher", "rises"), ("descends",)),
])
def test_vertical_motion_is_resolved_per_leg(heights, expected, forbidden):
    waypoints = [
        {"id": f"p{index}", "at": index / (len(heights) - 1), "x": 0, "y": height, "z": 0}
        for index, height in enumerate(heights)
    ]
    plan = parse_shot_plan(_plan(_shot(cameraPath={
        "motionType": "tracking", "coordinateSpace": "subject", "waypoints": waypoints,
    })), 4.0)
    instruction = shot_plan_instruction(plan, "t2va")
    for phrase in expected:
        assert phrase in instruction
    for phrase in forbidden:
        assert phrase not in instruction


@pytest.mark.parametrize("waypoint", [
    {"aimMode": "target"},
    {"aimMode": "anchor", "aimTarget": {"kind": "subject", "id": "juan"}},
])
def test_waypoint_target_mode_and_target_are_atomic(waypoint):
    base = {"id": "a", "at": 0, "x": 0, "y": 0, "z": 0, **waypoint}
    with pytest.raises(ValueError, match="aimTarget"):
        parse_shot_plan(_plan(_shot(cameraPath={
            "motionType": "tracking", "waypoints": [base, {"id": "b", "at": 1, "x": 0, "y": 0, "z": 1}],
        })), 4.0)


def test_staging_positions_and_facing_compile_to_qualitative_subject_prose():
    plan = parse_shot_plan(_plan(_shot(staging=[
        {"subjectId": "juan", "start": {"x": -.7, "y": 0, "z": .7, "facing": "target", "facingTarget": {"kind": "subject", "id": "olivia"}},
         "end": {"x": .1, "y": 0, "z": 0, "facing": "travel"}, "movement": "walks"},
        {"subjectId": "olivia", "start": {"x": .7, "y": .5, "z": -.7, "facing": "camera"}},
    ])), 4.0)
    instruction = shot_plan_instruction(plan, "t2va", {"project": {"subjects": [
        {"id": "juan", "name": "Juan"}, {"id": "olivia", "name": "Olivia"},
    ]}})
    assert "Subject staging:" in instruction
    assert "Juan begins frame left, in the foreground" in instruction
    assert "facing Olivia" in instruction
    assert "then walks to near frame center" in instruction
    assert "Olivia begins frame right, in the background, on an elevated level" in instruction


def test_frame_targets_and_focus_are_not_dropped_from_the_llm_instruction():
    plan = parse_shot_plan(_plan(_shot(
        cameraStart={
            "framing": "medium_wide",
            "primaryTarget": {"kind": "subject", "id": "juan"},
            "foregroundTarget": {"kind": "subject", "id": "olivia"},
            "focus": {
                "mode": "split_focus",
                "primaryTarget": {"kind": "subject", "id": "juan"},
                "secondaryTarget": {"kind": "subject", "id": "olivia"},
                "note": "keep both faces readable",
            },
        },
    )), 4.0)
    instruction = shot_plan_instruction(plan, "t2va", {"project": {"subjects": [
        {"id": "juan", "name": "Juan"}, {"id": "olivia", "name": "Olivia"},
    ]}})
    assert "centered on Juan" in instruction
    assert "foreground occupied by Olivia" in instruction
    assert "split focus on Juan and Olivia" in instruction
    assert "keep both faces readable" in instruction


def test_spatial_output_guard_rejects_editor_notation_but_not_natural_camera_prose():
    plan = _plan(_shot(cameraPath={"motionType": "tracking", "waypoints": [
        {"id": "a", "at": 0, "x": 0, "y": 0, "z": 1},
        {"id": "b", "at": 1, "x": 0, "y": 0, "z": -1},
    ]}))
    assert not _spatial_camera_output_gaps(
        "The camera passes behind Juan and smoothly reframes toward Olivia.", plan,
    )
    gaps = _spatial_camera_output_gaps(
        "At 50% the camera uses arc_left and aims 90 degrees right.", plan,
    )
    assert len(gaps) == 3


def test_published_shot_schema_accepts_the_same_staging_and_named_aim_as_runtime():
    document = _plan(_shot(
        subjects=[{"subjectId": "juan", "presence": "present"}, {"subjectId": "olivia", "presence": "present"}],
        staging=[
            {"subjectId": "juan", "start": {"x": -.5, "y": 0, "z": 0, "facing": "target", "facingTarget": {"kind": "subject", "id": "olivia"}}},
            {"subjectId": "olivia", "start": {"x": .5, "y": 0, "z": 0, "facing": "camera"}},
        ],
        cameraPath={"motionType": "tracking", "waypoints": [
            {"id": "a", "at": 0, "x": 0, "y": 0, "z": 1, "aimMode": "target", "aimTarget": {"kind": "subject", "id": "juan"}},
            {"id": "b", "at": 1, "x": 0, "y": 0, "z": -1, "aimMode": "target", "aimTarget": {"kind": "subject", "id": "olivia"}},
        ]},
    ))
    schema = json.loads((Path(__file__).parents[1] / "docs" / "schemas" / "shot_plan_v2.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(document)
    assert parse_shot_plan(document, 4.0)["shots"][0]["staging"][0]["subjectId"] == "juan"
