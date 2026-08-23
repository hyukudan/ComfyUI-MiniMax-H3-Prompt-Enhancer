# SPDX-License-Identifier: GPL-3.0-only

import json
from pathlib import Path

import jsonschema
import pytest

from creative_treatments import parse_shot_plan, shot_plan_instruction
from prompt_guides import _spatial_camera_output_gaps


def _plan(shot):
    return {"schemaVersion": 2, "timingMode": "auto", "shots": [shot]}


def _shot(**values):
    return {"id": "s1", "generationId": "g1", "action": "Juan crosses toward Olivia.", **values}


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
