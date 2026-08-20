# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import hashlib
import json

import pytest

from creative_treatments import build_shots_package, parse_shot_plan
from prompt_enhancer import enhance_prompt_with_completion
from prompt_enhancer_node import MiniMaxH3PromptGuideBuilder, MiniMaxH3ShotSelector
from prompt_guides import build_user_request, treatment_warning_report, validate_prompt


TWO_SHOT_PROMPT = """integrated_multimodal_description:
[Shot 1] Live-action, cinematic, a woman approaches the driver's door of a parked car.
[Shot 2] At 00:04.000, she opens that door, sits behind the wheel, and closes it.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""


CREATIVE_JSON = json.dumps({
    "schemaVersion": 1,
    "genre": "action",
    "visualLanguage": "anime_shonen",
    "worldAesthetic": "cyberpunk",
    "tone": "epic",
})


AUTO_SHOTS_JSON = json.dumps({
    "schemaVersion": 1,
    "timingMode": "auto",
    "shots": [
        {"id": "approach", "description": "She approaches the driver's door."},
        {"id": "entry", "description": "She opens that door and sits behind the wheel."},
    ],
})


CINEMATOGRAPHY_JSON = json.dumps({
    "schemaVersion": 1,
    "colorPalette": "restrained",
    "exposureContrast": "low_key",
    "cameraMotion": "tracking",
    "cameraAmplitude": "medium",
    "cameraSpeed": "slow",
    "optics": "compressed_telephoto",
    "depthOfField": "shallow",
    "imageTexture": "film_35mm",
    "lensEffects": "restrained_halation",
    "motionRendering": "natural_blur",
})


def test_neutral_controls_preserve_the_current_user_request_byte_for_byte():
    legacy_call = build_user_request("A woman crosses a quiet station.", "t2va", 5.0, "")
    explicit_neutral = build_user_request(
        "A woman crosses a quiet station.", "t2va", 5.0, "",
        creative_treatment_json=json.dumps({
            "schemaVersion": 1,
            "genre": "none",
            "visualLanguage": "none",
            "worldAesthetic": "none",
            "tone": "none",
        }),
        shot_plan_json=json.dumps({"schemaVersion": 1, "timingMode": "auto", "shots": []}),
    )
    assert legacy_call == explicit_neutral
    # The hash guards that neutral controls change nothing, not that the request is frozen for
    # ever. Updated 2026-08-20 for deliberate edits: the emotional-performance contract lost a
    # sentence that banned stacked instructions while stacking six of its own, and a seven-link
    # precedence chain; and the voice-policy branches are now keyed on the requested performance
    # mode rather than on whether the source happened to contain quotation marks.
    assert hashlib.sha256(legacy_call.encode("utf-8")).hexdigest() == (
        "75298fc6eec289ef14c90f9ad60e4c90ae489d1d5c5ab1e2ce9b8ad2d8285d5e"
    )


def test_neutral_controls_preserve_pipeline_request_and_enhanced_result():
    captured = []

    def complete(messages):
        captured.append(messages[-1]["content"])
        return """integrated_multimodal_description: [Shot 1] Live-action, cinematic, a woman crosses a quiet station.

overall_soundscape: Quiet station room tone.

non_diegetic_music: N/A"""

    legacy = enhance_prompt_with_completion(
        "A woman crosses a quiet station. No music.", "t2va", 5.0, "", complete, 0, {"provider": "test"},
    )
    explicit = enhance_prompt_with_completion(
        "A woman crosses a quiet station. No music.", "t2va", 5.0, "", complete, 0, {"provider": "test"},
        creative_treatment_json="", shot_plan_json="",
    )
    assert captured[0] == captured[1]
    assert legacy[0] == explicit[0]
    assert legacy[1] == explicit[1]
    manifest = explicit[2]
    assert manifest["creativeTreatmentSchemaVersion"] == 1
    assert manifest["creativeProfileCatalogVersion"] == 22
    assert manifest["cinematographySchemaVersion"] == 1
    assert manifest["cinematographyCatalogVersion"] == 6
    assert manifest["shotPlanSchemaVersion"] == 1
    assert manifest["shotsPackageSchemaVersion"] == 1
    assert manifest["creativeTreatment"]["applied"] is False
    assert manifest["creativeTreatment"]["profileIds"] == []
    assert manifest["cinematography"]["applied"] is False
    assert len(manifest["creativeTreatment"]["digest"]) == 64
    assert manifest["shotPlan"]["applied"] is False
    assert manifest["shotsPackage"] == {}


def test_treatment_and_shot_plan_are_injected_without_overriding_audio_or_cuts():
    request = build_user_request(
        "A woman approaches a car and enters through the driver's door. No music.",
        "t2va", 8.0, "", True, "off", "off", "audible", "",
        creative_treatment_json=CREATIVE_JSON,
        shot_plan_json=AUTO_SHOTS_JSON,
    )
    assert "SECONDARY CREATIVE TREATMENT" in request
    assert "anticipation, action, impact, and recovery" in request
    assert "non-photorealistic hand-authored 2D action-anime" in request
    assert "dynamic pose strength, perspective emphasis, and kinetic timing" in request
    assert "high-tech/low-life material contrast" in request
    assert "clear escalation" in request
    for private_id in (
        "genre:action", "visual_language:anime_shonen", "world_aesthetic:cyberpunk", "tone:epic",
    ):
        assert private_id not in request
    assert "AUTHORITATIVE EXPLICIT SHOT PLAN" in request
    assert "Use exactly 2 shots" in request
    assert "Do not merge, split, reorder, omit, duplicate, or add" in request
    assert "AMBIENCE AND FOLEY POLICY — OFF" in request
    assert "NON-DIEGETIC MUSIC POLICY — OFF" in request
    assert "A profile never creates a cut" in request
    assert "music remains entirely governed" in request.lower()


def test_cinematography_is_injected_as_bounded_h3_direction_and_recorded():
    captured = []

    def complete(messages):
        captured.append(messages[-1]["content"])
        return TWO_SHOT_PROMPT

    _prompt, report, manifest = enhance_prompt_with_completion(
        "A woman approaches a car and enters through the driver's door. No music.",
        "t2va", 8.0, "", complete, 0, {"provider": "test"},
        ambience_foley_policy="off", background_score_policy="off",
        shot_plan_json=AUTO_SHOTS_JSON,
        cinematography_json=CINEMATOGRAPHY_JSON,
    )
    request = captured[0]
    assert "EXPLICIT CINEMATOGRAPHY — AUTHORITATIVE PRESENTATION CONTROL" in request
    assert "motion type + amplitude + speed" in request
    assert (
        "The camera tracks with medium amplitude at slow speed alongside the principal subject already present "
        "in the shot"
    ) in request
    assert "Use medium camera-motion amplitude." not in request
    assert "Use slow camera-motion speed." not in request
    assert "may not create a cut" in request
    assert "light source" in request
    assert report["valid"], report

    cinematography = manifest["cinematography"]
    assert cinematography["applied"] is True
    assert cinematography["cameraMotion"] == "tracking"
    assert cinematography["cameraAmplitude"] == "medium"
    assert cinematography["cameraSpeed"] == "slow"
    assert len(cinematography["digest"]) == 64


def test_disabled_description_enhancement_ignores_treatment_but_not_explicit_shot_plan():
    request = build_user_request(
        "A woman approaches a car and enters.", "t2va", 8.0, "", False,
        creative_treatment_json=CREATIVE_JSON, shot_plan_json=AUTO_SHOTS_JSON,
    )
    assert "SECONDARY CREATIVE TREATMENT" not in request
    assert "AUTHORITATIVE EXPLICIT SHOT PLAN" in request


@pytest.mark.parametrize(
    "kwargs",
    (
        {"creative_treatment_json": "{"},
        {"creative_treatment_json": '{"schemaVersion":1,"genre":"invalid"}'},
        {"shot_plan_json": "{"},
        {"shot_plan_json": '{"schemaVersion":1,"timingMode":"exact","shots":[],'},
    ),
)
def test_invalid_configuration_stops_before_any_llm_completion(kwargs):
    called = False

    def complete(_messages):
        nonlocal called
        called = True
        return TWO_SHOT_PROMPT

    with pytest.raises(ValueError):
        enhance_prompt_with_completion(
            "A woman approaches a car.", "t2va", 8.0, "", complete, 0, {"provider": "test"}, **kwargs,
        )
    assert called is False


def test_pipeline_records_canonical_treatment_plan_digests_and_shots_package():
    prompt, report, manifest = enhance_prompt_with_completion(
        "A woman approaches a car and enters through the driver's door. No music.",
        "t2va", 8.0, "", lambda _messages: TWO_SHOT_PROMPT, 0, {"provider": "test"},
        ambience_foley_policy="off", background_score_policy="off",
        creative_treatment_json=CREATIVE_JSON, shot_plan_json=AUTO_SHOTS_JSON,
    )
    assert report["valid"], report
    assert prompt.count("[Shot ") == 2

    treatment = manifest["creativeTreatment"]
    assert treatment["schemaVersion"] == 1
    assert treatment["genre"] == "action"
    assert treatment["visualLanguage"] == "anime_shonen"
    assert treatment["worldAesthetic"] == "cyberpunk"
    assert treatment["tone"] == "epic"
    assert treatment["applied"] is True
    assert len(treatment["digest"]) == 64

    shot_plan = manifest["shotPlan"]
    assert shot_plan["schemaVersion"] == 1
    assert shot_plan["shotCount"] == 2
    assert shot_plan["applied"] is True
    assert len(shot_plan["digest"]) == 64

    package = manifest["shotsPackage"]
    assert package["schemaVersion"] == 1
    assert package["shotPlanDigest"] == shot_plan["digest"]
    assert package["shotCount"] == 2
    assert [shot["id"] for shot in package["shots"]] == ["approach", "entry"]
    assert package["complete"] is True
    assert len(package["digest"]) == 64


def test_exact_plan_normalization_and_validation_follow_frame_count_duration():
    shot_plan = json.dumps({
        "schemaVersion": 1,
        "timingMode": "exact",
        "shots": [
            {"id": "s1", "description": "First beat.", "durationSeconds": 2.125},
            {"id": "s2", "description": "Second beat.", "durationSeconds": 8.0},
        ],
    })
    generated = TWO_SHOT_PROMPT.replace("00:04.000", "00:09.000")
    prompt, report, _manifest = enhance_prompt_with_completion(
        "A woman approaches a car, then enters. No music.",
        "t2va", 5.0, "", lambda _messages: generated, 0, {"provider": "test"},
        ambience_foley_policy="off", background_score_policy="off", frame_count=243,
        shot_plan_json=shot_plan,
    )
    assert "[Shot 2] At 00:02.125," in prompt
    assert report["valid"], report
    assert report["generationProfile"]["effectiveDurationSeconds"] == 243 / 24

    wrong = prompt.replace("00:02.125", "00:02.400")
    invalid = validate_prompt(
        wrong, "t2va", 5.0, "A woman approaches a car, then enters. No music.",
        ambience_foley_policy="off", background_score_policy="off", frame_count=243,
        shot_plan_json=shot_plan,
    )
    assert any("exact requested boundaries" in error for error in invalid["errors"])


def test_chained_plan_produces_exact_autonomous_items_with_locks_and_dialogue():
    plan = json.dumps({
        "schemaVersion": 1,
        "timingMode": "auto",
        "shots": [
            {"id": "greeting", "description": 'The woman says exactly "Hola." in Spanish.'},
            {"id": "departure", "description": "The same woman walks away silently."},
        ],
    })
    generated = json.dumps({"prompts": [
        "The woman (S1) says clearly: <d>[Spanish] Hola.</d>.",
        "The same woman walks away silently.",
    ]})
    prompt, report, manifest = enhance_prompt_with_completion(
        'A woman says in Spanish "Hola." Then she walks away silently.',
        "chained_multishot", 8.0, "", lambda _messages: generated, 0, {"provider": "test"},
        multishot_identity_lock="The woman keeps the same red coat.",
        multishot_voice_lock="Her Spanish voice remains identical.",
        shot_plan_json=plan,
    )
    assert report["valid"], report
    prompts = json.loads(prompt)["prompts"]
    assert len(prompts) == 2
    assert prompts[0].count("<d>[Spanish] Hola.</d>") == 1
    assert "<d>" not in prompts[1]
    assert all("The woman keeps the same red coat." in item for item in prompts)
    assert all("Her Spanish voice remains identical." in item for item in prompts)
    assert [shot["id"] for shot in manifest["shotsPackage"]["shots"]] == ["greeting", "departure"]


def test_standalone_t2va_shots_are_complete_and_never_leak_other_shot_dialogue_or_audio():
    source = """integrated_multimodal_description:
[Shot 1] A woman (S1) says clearly: <d>[Spanish] Secreto.</d>. She stays beside the car.
[Shot 2] At 00:04.000, the same woman enters the car and closes the door without speaking.

overall_soundscape:
Her spoken line is clear in the first shot; the car door slams in the second shot.

non_diegetic_music:
A continuous low string pulse."""
    plan = parse_shot_plan(AUTO_SHOTS_JSON, 8.0, mode="t2va")
    package = build_shots_package(source, "t2va", plan)
    assert package["complete"] is True
    assert package["allAutonomous"] is True
    assert len(package["shots"]) == 2

    first, second = package["shots"]
    assert first["timelineBody"].count("<d>[Spanish] Secreto.</d>") == 1
    assert "<d>[Spanish] Secreto.</d>" not in second["timelineBody"]
    assert "<d>[Spanish] Secreto.</d>" not in second["autonomousPrompt"]
    assert "car door slams" not in first["autonomousPrompt"]
    assert "car door slams" not in second["autonomousPrompt"]
    for shot in (first, second):
        prompt = shot["autonomousPrompt"]
        assert shot["autonomous"] is True
        assert shot["sharedAudioOmitted"] is True
        assert shot["audioFidelity"] == "omitted_to_prevent_cross_shot_leakage"
        assert prompt.startswith("integrated_multimodal_description:")
        assert prompt.count("[Shot 1]") == 1
        assert "[Shot 2]" not in prompt
        assert "overall_soundscape:\nN/A" in prompt
        assert "non_diegetic_music:\nN/A" in prompt

    selected = MiniMaxH3ShotSelector().select(json.dumps({"shotsPackage": package}), 2)["result"]
    assert selected[0] == second["autonomousPrompt"].strip()
    assert selected[1] == second["timelineBody"].strip()
    assert selected[2] == "She opens that door and sits behind the wheel."
    assert selected[3:] == ("entry", 2, True)


@pytest.mark.parametrize("value", ("", "{", "[]", '{"schemaVersion":1,"shots":[]}'))
def test_shot_selector_rejects_invalid_or_empty_packages(value):
    with pytest.raises(ValueError):
        MiniMaxH3ShotSelector().select(value, 1)


def test_shot_selector_never_emits_a_non_autonomous_prompt():
    package = {
        "schemaVersion": 1,
        "shots": [{
            "id": "s1",
            "description": "A keyframe-dependent fragment.",
            "timelineBody": "Fragment for inspection.",
            "enhancedPrompt": "This must not be emitted.",
            "autonomousPrompt": "",
            "autonomous": False,
            "autonomyReason": "Missing keyframe anchor.",
        }],
    }
    result = MiniMaxH3ShotSelector().select(json.dumps(package), 1)["result"]
    assert result == (
        "", "Fragment for inspection.", "A keyframe-dependent fragment.", "s1", 1, False,
    )


def test_multishot_ref2va_retention_is_never_exposed_as_an_autonomous_prompt():
    source = """subject_definitions:
<Subject 1> is the woman from <Picture 1>.
<Subject 2> is the car from <Picture 2>.
summary:
[reference generation] The woman approaches and enters the car.
retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - identity remains stable.
<Subject 2> (appears in [Shot 2]): fully_preserved - the car remains stable.
detailed_description:
[Shot 1] <Subject 1> from <Picture 1> approaches the parked car.
[Shot 2] At 00:04.000, <Subject 1> enters <Subject 2> from <Picture 2>.
overall_soundscape:
N/A
non_diegetic_music:
N/A"""
    plan = parse_shot_plan(AUTO_SHOTS_JSON, 8.0, mode="ref2va")
    package = build_shots_package(source, "ref2va", plan)
    assert package["complete"] is True
    assert package["allAutonomous"] is False
    for shot in package["shots"]:
        assert shot["autonomous"] is False
        assert shot["autonomousPrompt"] == ""
        assert "retention analysis" in shot["autonomyReason"].lower()
    result = MiniMaxH3ShotSelector().select(json.dumps(package), 2)["result"]
    assert result[0] == ""
    assert result[-1] is False


def test_single_shot_ref2va_can_preserve_its_complete_reference_contract():
    source = """subject_definitions:
<Subject 1> is the woman from <Picture 1>.
summary:
[reference generation] The woman turns toward camera.
retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - identity remains stable.
detailed_description:
[Shot 1] <Subject 1> from <Picture 1> turns toward camera.
overall_soundscape:
N/A
non_diegetic_music:
N/A"""
    one = json.dumps({
        "schemaVersion": 1,
        "timingMode": "auto",
        "shots": [{"id": "turn", "description": "The woman turns toward camera."}],
    })
    package = build_shots_package(source, "ref2va", parse_shot_plan(one, 5.0, mode="ref2va"))
    shot = package["shots"][0]
    assert shot["autonomous"] is True
    assert shot["autonomousPrompt"].startswith("subject_definitions:")
    assert "summary:\n[reference generation] Autonomous execution" in shot["autonomousPrompt"]
    assert "retention_analysis:" in shot["autonomousPrompt"]
    assert "detailed_description:\n[Shot 1]" in shot["autonomousPrompt"]


def test_invalid_complete_prompt_disables_every_autonomous_package_item():
    plan = parse_shot_plan(AUTO_SHOTS_JSON, 8.0, mode="t2va")
    package = build_shots_package(TWO_SHOT_PROMPT, "t2va", plan, source_valid=False)
    assert package["sourcePromptValid"] is False
    assert package["allAutonomous"] is False
    assert all(not shot["autonomous"] and not shot["autonomousPrompt"] for shot in package["shots"])
    assert all("failed validation" in shot["autonomyReason"] for shot in package["shots"])


def test_new_camera_axes_and_merged_motion_reach_the_assembled_request():
    request = build_user_request(
        "A woman studies a map.", "t2va", 5.0, "",
        cinematography_json=json.dumps({
            "schemaVersion": 1,
            "shotScale": "medium_close_up",
            "cameraAngle": "low_angle",
            "cameraViewpoint": "over_the_shoulder",
            "cameraMotion": "truck_right",
            "cameraAmplitude": "medium",
            "cameraSpeed": "normal",
            "optics": "lens_50mm",
        }),
    )
    assert "Frame the principal subject in a medium close-up, from mid-chest up" in request
    assert "below the subject's eye line, tilted slightly up" in request
    assert "just behind one character's shoulder" in request
    assert "The camera trucks right with medium amplitude at normal speed" in request
    assert "photographed on a 50mm lens" in request
    assert "override any conflicting camera, optical, exposure, or color advice" in request


def test_acoustic_space_lands_in_the_audio_controls_and_stays_subordinate():
    request = build_user_request(
        "A woman reads aloud in a chapel.", "t2va", 5.0, "",
        acoustic_space="large_reverberant_interior",
    )
    assert "DIEGETIC ACOUSTIC SPACE — AUTHORITATIVE OVER EVERY TREATMENT SOUND SUGGESTION" in request
    assert "Selected acoustic space: large_reverberant_interior." in request
    assert "a long decaying reverb tail" in request
    assert "it never re-enables a disabled audio layer" in request
    assert request.index("AMBIENCE AND FOLEY POLICY") < request.index("DIEGETIC ACOUSTIC SPACE")
    assert "DIEGETIC ACOUSTIC SPACE" not in build_user_request("A woman reads aloud.", "t2va", 5.0, "")


def test_dialogue_coverage_is_injected_only_when_a_voice_can_be_seen():
    active = build_user_request(
        'A woman says "Hola."', "t2va", 5.0, "", dialogue_coverage="on",
    )
    assert "DIALOGUE COVERAGE — REQUIRED" in active
    assert (
        "Keep each speaking character's mouth and eyes unobstructed and in focus for the full duration of "
        "their line, at medium close-up or tighter, with a stable eyeline."
    ) in active
    assert "do not add a cut, character, line, or camera control" in active
    assert "DIALOGUE COVERAGE" not in build_user_request('A woman says "Hola."', "t2va", 5.0, "")
    assert "DIALOGUE COVERAGE" not in build_user_request(
        'A woman says "Hola."', "t2va", 5.0, "", voice_performance="none", dialogue_coverage="on",
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"acoustic_space": "cathedral"}, "Unsupported acoustic space"),
        ({"dialogue_coverage": "maybe"}, "Unsupported dialogue coverage"),
    ),
)
def test_invalid_sound_and_coverage_controls_fail_before_assembly(kwargs, message):
    with pytest.raises(ValueError, match=message):
        build_user_request("A woman speaks.", "t2va", 5.0, "", **kwargs)


def test_conflicting_treatment_lines_are_dropped_from_the_assembled_request():
    quartet = json.dumps({
        "schemaVersion": 1,
        "genre": "action",
        "visualLanguage": "documentary_observational",
        "worldAesthetic": "film_noir",
        "tone": "serene",
    })
    request = build_user_request(
        "A woman runs across a station.", "t2va", 8.0, "", creative_treatment_json=quartet,
    )
    assert "the camera observes rather than choreographs attention theatrically" in request
    assert "wide tracking or lateral staging" not in request
    warnings = treatment_warning_report(quartet, "", "", 8.0)
    assert len(warnings.splitlines()) == 2
    assert all("camera_energy conflict" in line for line in warnings.splitlines())
    assert all(
        "visual_language 'documentary_observational' (observational) overrides genre 'action'" in line
        for line in warnings.splitlines()
    )


def test_pipeline_surfaces_treatment_warnings_through_the_manifest_and_node_output():
    prompt, _report, manifest = enhance_prompt_with_completion(
        "A woman approaches a car and enters through the driver's door. No music.",
        "t2va", 8.0, "", lambda _messages: TWO_SHOT_PROMPT, 0, {"provider": "test"},
        ambience_foley_policy="off", background_score_policy="off",
        creative_treatment_json=json.dumps({"schemaVersion": 1, "genre": "action"}),
        cinematography_json=json.dumps({"schemaVersion": 1, "cameraMotion": "shake_slightly"}),
    )
    assert prompt
    assert manifest["cinematography"]["warnings"]
    assert [item["dimension"] for item in manifest["treatmentConflicts"]] == ["camera_energy"] * 2
    assert manifest["treatmentWarnings"][0].startswith("cameraMotion 'shake_slightly' is a legacy value")
    assert any("camera_energy conflict" in warning for warning in manifest["treatmentWarnings"])
    recorded = manifest["creativeTreatment"]
    assert recorded["droppedLines"] == [item["droppedText"] for item in manifest["treatmentConflicts"]]
    assert not any(
        line in recorded["dimensions"]["camera_and_framing"] for line in recorded["droppedLines"]
    )

    _system, _request, _mode, warnings, _width, _height = MiniMaxH3PromptGuideBuilder().build(
        "A woman approaches a car.", "t2va", 8.0, "",
        creative_treatment_json=json.dumps({"schemaVersion": 1, "genre": "action"}),
        cinematography_json=json.dumps({"schemaVersion": 1, "cameraMotion": "shake_slightly"}),
    )
    assert warnings.splitlines() == manifest["treatmentWarnings"]


def test_shot_rows_carry_their_own_camera_and_transition_into_the_request():
    plan = json.dumps({
        "schemaVersion": 1,
        "timingMode": "auto",
        "shots": [
            {"id": "approach", "description": "She approaches the door.", "cameraMotion": "push_in"},
            {"id": "entry", "description": "She sits behind the wheel.", "transitionIn": "whip_pan"},
        ],
    })
    request = build_user_request(
        "A woman approaches a car and enters.", "t2va", 8.0, "", shot_plan_json=plan,
    )
    assert 'camera="The camera pushes in toward the principal subject' in request
    assert 'transition="Enter this shot through a fast whip-pan blur' in request
    assert treatment_warning_report("", "", plan, 8.0) == ""

    legacy_row = json.dumps({
        "schemaVersion": 1,
        "timingMode": "auto",
        "shots": [{"id": "approach", "description": "She approaches the door.", "cameraMotion": "pov"}],
    })
    assert "legacy value" in treatment_warning_report("", "", legacy_row, 8.0)
