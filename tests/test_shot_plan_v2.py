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
    assert "Camera starts with framing wide" in instruction
    assert "Camera ends with framing medium" in instruction
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
