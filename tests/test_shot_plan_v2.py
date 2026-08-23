# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pytest

from camera_state import resolve_camera_end
from creative_treatments import build_shots_package, parse_shot_plan, shot_plan_instruction
from prompt_guides import build_user_request


def _plan(*shots, timing="auto"):
    return {"schemaVersion": 2, "timingMode": timing, "shots": list(shots)}


def _shot(**overrides):
    value = {"id": "s1", "generationId": "g1", "action": "Ana crosses the bridge."}
    value.update(overrides)
    return value


def test_v2_normalizes_camera_end_as_delta_and_renders_temporal_phases():
    plan = parse_shot_plan(_plan(_shot(
        openingState="Ana stands at the near end.",
        cameraStart={"framing": "wide", "viewpoint": "rear_three_quarter"},
        cameraEnd={"framing": "medium", "viewpoint": "rear_three_quarter"},
        cameraPath={
            "motionType": "push_in", "amplitude": "small", "speed": "slow",
            "easing": "ease_out", "timing": "during_action",
        },
    )), 8.0)

    assert plan["schemaVersion"] == 2
    assert plan["shots"][0]["cameraEnd"] == {"framing": "medium"}
    assert resolve_camera_end(plan["shots"][0]["cameraStart"], plan["shots"][0]["cameraEnd"]) == {
        "framing": "medium", "viewpoint": "rear_three_quarter",
    }
    instruction = shot_plan_instruction(plan, "t2va")
    assert "different temporal phases, not conflicting instructions" in instruction
    assert "Camera: Start wide, rear three quarter" in instruction
    assert "End medium, rear three quarter" in instruction
    assert "cinematic" not in instruction.casefold()
    assert "realistic" not in instruction.casefold()


def test_v2_accepts_full_structured_allocation_and_transitions():
    plan = parse_shot_plan(_plan(_shot(
        subjectPresenceComplete=True,
        subjects=[{"subjectId": "ana", "presence": "present", "blocking": "At the railing."}],
        environment={"environmentId": "bridge", "viewIds": ["railing"]},
        referenceUses=[{
            "assetId": "camera.reference", "role": "camera_transfer",
            "cameraAspects": ["motion", "framing"],
        }],
        appearanceTransitions=[{
            "subjectId": "ana", "fromStateId": "base", "toStateId": "wounded",
            "timing": "during_shot", "trigger": "She wraps her arm.",
        }],
        environmentTransitions=[{
            "environmentId": "bridge", "fromStateId": "day", "toStateId": "rain",
            "timing": "during_shot", "trigger": "Rain begins.",
        }],
    )), 8.0)

    shot = plan["shots"][0]
    assert shot["subjects"][0]["subjectId"] == "ana"
    assert shot["environment"]["viewIds"] == ["railing"]
    assert shot["appearanceTransitions"][0]["toStateId"] == "wounded"


def test_v2_exact_timing_is_validated_per_generation():
    plan = parse_shot_plan(_plan(
        _shot(id="s1", generationId="g1", durationSeconds=3),
        _shot(id="s2", generationId="g1", durationSeconds=5, transitionIn="match_cut"),
        _shot(id="s3", generationId="g2", durationSeconds=8),
        timing="exact",
    ), 8.0, mode="chained_multishot")

    assert plan["expectedCutTimesByGeneration"] == {"g1": [3.0], "g2": []}
    assert plan["totalDurationSeconds"] == 16.0


def test_v2_rejects_non_g1_generation_in_ordinary_mode():
    with pytest.raises(ValueError, match="must be 'g1'"):
        parse_shot_plan(_plan(_shot(generationId="g2")), 8.0, mode="t2va")


def test_v2_rejects_non_camera_role_aspects_and_static_qualifiers():
    with pytest.raises(ValueError, match="only valid for role 'camera_transfer'"):
        parse_shot_plan(_plan(_shot(referenceUses=[{
            "assetId": "a1", "role": "appearance", "cameraAspects": ["framing"],
        }])), 8.0)
    with pytest.raises(ValueError, match="motionType is 'static'"):
        parse_shot_plan(_plan(_shot(cameraPath={"motionType": "static", "speed": "slow"})), 8.0)


def test_spatial_camera_waypoints_are_canonical_and_reach_prompt_instruction():
    path = {
        "motionType": "tracking", "coordinateSpace": "subject", "pathShape": "arc_left",
        "anchorTarget": {"kind": "subject", "id": "marta"},
        "easing": "ease_in_out",
        "waypoints": [
            {"id": "cam1", "at": 0, "x": -0.8, "y": 0.1, "z": 0.7, "framing": "wide", "aimMode": "anchor"},
            {"id": "cam2", "at": 0.45, "x": -0.1, "y": 0.25, "z": 0.1, "hold": True, "aimMode": "travel"},
            {"id": "cam3", "at": 1, "x": 0.65, "y": -0.1, "z": -0.4, "framing": "close_up", "aimMode": "custom", "panDegrees": 135, "tiltDegrees": -15},
        ],
    }
    plan = parse_shot_plan(_plan(_shot(cameraPath=path)), 8.0)
    assert plan["shots"][0]["cameraPath"] == path
    instruction = shot_plan_instruction(plan, "t2va")
    assert "along a left-curving path around Marta" in instruction
    assert "around Marta" in instruction
    assert "aimed at Marta" in instruction
    assert "aiming along the direction of travel" in instruction
    assert "turned toward frame right" in instruction
    assert "around the midpoint" in instruction
    assert "behind it" in instruction
    assert "in front of it" in instruction
    assert "degrees" not in instruction
    assert "45%" not in instruction
    assert "x=" not in instruction
    assert "y=" not in instruction
    assert "z=" not in instruction
    assert "holding momentarily" in instruction


def test_numbered_subject_anchor_uses_the_h3_reference_label():
    path = {
        "motionType": "arc", "coordinateSpace": "subject",
        "anchorTarget": {"kind": "subject", "id": "subject.2"},
        "waypoints": [
            {"id": "a", "at": 0, "x": 0, "y": 0, "z": 0.8, "aimMode": "anchor"},
            {"id": "b", "at": 1, "x": 0, "y": 0, "z": -0.8, "aimMode": "anchor"},
        ],
    }
    instruction = shot_plan_instruction(parse_shot_plan(_plan(_shot(cameraPath=path)), 8.0), "ref2va")
    assert "around <Subject 2>" in instruction
    assert "in front of it" in instruction
    assert "behind it" in instruction
    assert "aimed at <Subject 2>" in instruction


@pytest.mark.parametrize("waypoints", [
    [{"id": "a", "at": 0, "x": 0, "y": 0, "z": 0}],
    [
        {"id": "a", "at": 0.2, "x": 0, "y": 0, "z": 0},
        {"id": "b", "at": 1, "x": 0, "y": 0, "z": 0},
    ],
    [
        {"id": "a", "at": 0, "x": 0, "y": 0, "z": 0},
        {"id": "b", "at": 0, "x": 0, "y": 0, "z": 0},
    ],
])
def test_spatial_camera_waypoints_reject_invalid_timeline(waypoints):
    with pytest.raises(ValueError):
        parse_shot_plan(_plan(_shot(cameraPath={"motionType": "tracking", "waypoints": waypoints})), 8.0)


def test_custom_camera_aim_requires_custom_mode_and_bounded_angles():
    base = [
        {"id": "a", "at": 0, "x": 0, "y": 0, "z": 1},
        {"id": "b", "at": 1, "x": 0, "y": 0, "z": -1},
    ]
    with pytest.raises(ValueError, match="require aimMode 'custom'"):
        parse_shot_plan(_plan(_shot(cameraPath={"motionType": "tracking", "waypoints": [
            {**base[0], "panDegrees": 45}, base[1],
        ]})), 8.0)
    with pytest.raises(ValueError, match="between -180 and 180"):
        parse_shot_plan(_plan(_shot(cameraPath={"motionType": "tracking", "waypoints": [
            {**base[0], "aimMode": "custom", "panDegrees": 200}, base[1],
        ]})), 8.0)


def test_action_beats_link_visible_action_and_dialogue_without_leaking_control_labels():
    plan = parse_shot_plan(_plan(_shot(actionBeats=[
        {"id": "b1", "at": .2, "action": "Ana notices the open door."},
        {"id": "b2", "at": .65, "action": "She stops.", "dialogue": {
            "speakerId": "ana", "text": "Who is there?", "delivery": "whispers", "mood": "wary",
        }},
    ])), 8.0)
    assert plan["shots"][0]["actionBeats"][1]["dialogue"]["speakerId"] == "ana"
    instruction = shot_plan_instruction(plan, "t2va")
    assert "At 65%" in instruction
    assert 'ana whispers with wary mood: "Who is there?"' in instruction
    assert "never expose JSON, percentages" in instruction


def test_action_beat_spans_calls_out_and_dialogue_camera_timing_reach_instruction():
    plan = parse_shot_plan(_plan(
        _shot(id="s1", action="Ana enters."),
        _shot(id="s2",
              actionBeats=[{"id": "b1", "at": .2, "endAt": .55, "dialogue": {
                  "speakerId": "ana", "text": "Wait for me!", "delivery": "calls_out",
              }}],
              cameraPath={"motionType": "push_in", "timing": "during_dialogue"},
              transitionIn="cross_dissolve"),
    ), 8.0)
    instruction = shot_plan_instruction(plan, "t2va")
    assert "From 20% to 55%" in instruction
    assert 'ana calls out: "Wait for me!"' in instruction
    assert "during the dialogue" in instruction
    assert "brief cross-dissolve" in instruction


def test_scale_relationships_are_explicit_non_metric_prompt_constraints():
    plan = parse_shot_plan(_plan(_shot(scaleRelationships=[
        {"subjectId": "giant", "relativeToId": "ana", "relation": "twice_height"},
        {"subjectId": "ana", "relativeToId": "child", "relation": "custom", "note": "Ana reaches the child's shoulder."},
    ])), 8.0)
    instruction = shot_plan_instruction(plan, "t2va")
    assert "giant is about twice the visible height of ana" in instruction
    assert "preserve without inventing physical units" in instruction
    with pytest.raises(ValueError, match="two different subjects"):
        parse_shot_plan(_plan(_shot(scaleRelationships=[
            {"subjectId": "ana", "relativeToId": "ana", "relation": "same_height"},
        ])), 8.0)
    with pytest.raises(ValueError, match="note is required"):
        parse_shot_plan(_plan(_shot(scaleRelationships=[
            {"subjectId": "ana", "relativeToId": "child", "relation": "custom"},
        ])), 8.0)


def test_action_beats_require_content_and_strictly_increasing_progress():
    with pytest.raises(ValueError, match="requires action or dialogue"):
        parse_shot_plan(_plan(_shot(actionBeats=[{"id": "b1", "at": .5}])), 8.0)
    with pytest.raises(ValueError, match="strictly increasing"):
        parse_shot_plan(_plan(_shot(actionBeats=[
            {"id": "b1", "at": .6, "action": "First"},
            {"id": "b2", "at": .4, "action": "Second"},
        ])), 8.0)


def test_v2_rejects_empty_end_after_delta_normalization_without_serializing_it():
    plan = parse_shot_plan(_plan(_shot(
        cameraStart={"framing": "wide"}, cameraEnd={"framing": "wide"},
    )), 8.0)
    assert "cameraEnd" not in plan["shots"][0]
    assert '"cameraEnd"' not in plan["canonicalJson"]


def test_future_version_still_rejected_without_affecting_v1_contract():
    with pytest.raises(ValueError, match="must be one of: 1, 2"):
        parse_shot_plan({"schemaVersion": 3, "timingMode": "auto", "shots": []}, 8.0)
    legacy = parse_shot_plan({
        "schemaVersion": 1, "timingMode": "auto",
        "shots": [{"id": "s1", "description": "Ana waits."}],
    }, 8.0)
    assert legacy["schemaVersion"] == 1
    assert legacy["shots"] == [{"id": "s1", "description": "Ana waits."}]


def test_v2_chained_package_maps_prompts_by_generation_not_by_shot():
    plan = parse_shot_plan(_plan(
        _shot(id="s1", generationId="g1", action="Ana enters."),
        _shot(id="s2", generationId="g1", action="Ana stops."),
        _shot(id="s3", generationId="g2", action="Rain begins.", referenceUses=[{
            "assetId": "rain.reference", "role": "environment_view",
        }]),
    ), 8.0, mode="chained_multishot")
    package = build_shots_package(
        '{"prompts":["generation one prompt","generation two prompt"]}',
        "chained_multishot", plan,
    )

    assert package["schemaVersion"] == 2
    assert package["complete"] is True
    assert package["shots"][0]["enhancedPrompt"] == "generation one prompt"
    assert package["shots"][1]["enhancedPrompt"] == "generation one prompt"
    assert package["shots"][2]["enhancedPrompt"] == "generation two prompt"
    assert package["generations"]["g2"]["activeAssetIds"] == ["rain.reference"]


def test_v2_chained_output_count_is_generation_count_while_shot_count_is_preserved():
    raw = _plan(
        _shot(id="s1", generationId="g1", action="Ana enters."),
        _shot(id="s2", generationId="g1", action="Ana stops."),
        _shot(id="s3", generationId="g2", action="Rain begins."),
    )
    parsed = parse_shot_plan(raw, 8.0, mode="chained_multishot")
    assert parsed["shotCount"] == 3
    assert parsed["generationCount"] == 2
    request = build_user_request(
        "Ana crosses the bridge, then rain begins.", "chained_multishot", 8.0,
        shot_plan_json=raw,
    )
    assert "OUTPUT EXACTLY 2 PROMPT ITEMS" in request
    assert "Use exactly 3 shots" in request
