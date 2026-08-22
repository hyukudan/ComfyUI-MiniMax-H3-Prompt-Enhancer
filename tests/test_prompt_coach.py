# SPDX-License-Identifier: GPL-3.0-only

from diagnostics import DiagnosticCode
from prompt_coach import run_prompt_coach


def _plan(*shots):
    return {"schemaVersion": 2, "provided": True, "shots": list(shots)}


def _shot(shot_id="s1", action="Ana waits.", **values):
    shot = {"id": shot_id, "generationId": "g1", "action": action}
    shot.update(values)
    return shot


def _codes(collector):
    return [item.code for item in collector.diagnostics]


def test_coach_detects_structured_opening_duplicate_only_with_enough_overlap():
    result = run_prompt_coach(_plan(_shot(
        openingState="Ana stands beside the old bridge railing facing north.",
        action="Ana stands beside the old bridge railing facing north.",
    )), language="en")
    assert DiagnosticCode.COACH_OPENING_DUPLICATE in _codes(result)

    short = run_prompt_coach(_plan(_shot(openingState="Ana waits.", action="Ana waits.")), language="en")
    assert DiagnosticCode.COACH_OPENING_DUPLICATE not in _codes(short)


def test_coach_locomotion_requires_both_path_and_visible_final_state_to_be_missing():
    vague = run_prompt_coach(_plan(_shot(action="Ana walks.")), language="en")
    assert DiagnosticCode.COACH_LOCOMOTION_UNDER_SPECIFIED in _codes(vague)

    specified = run_prompt_coach(_plan(_shot(action="Ana walks across the bridge and stops at the railing.")), language="en")
    assert DiagnosticCode.COACH_LOCOMOTION_UNDER_SPECIFIED not in _codes(specified)


def test_coach_ambiguous_pronoun_requires_complete_multi_subject_presence():
    complete = run_prompt_coach(_plan(_shot(
        action="She looks toward the door.", subjectPresenceComplete=True,
        subjects=[
            {"subjectId": "ana", "presence": "present"},
            {"subjectId": "bea", "presence": "present"},
        ],
    )), language="en")
    assert DiagnosticCode.COACH_AMBIGUOUS_PRONOUN in _codes(complete)

    incomplete = run_prompt_coach(_plan(_shot(
        action="She looks toward the door.",
        subjects=[
            {"subjectId": "ana", "presence": "present"},
            {"subjectId": "bea", "presence": "present"},
        ],
    )), language="en")
    assert DiagnosticCode.COACH_AMBIGUOUS_PRONOUN not in _codes(incomplete)


def test_coach_aesthetic_noise_is_advice_and_does_not_rewrite_action():
    action = "Ana waits, cinematic realistic photorealistic ultra detailed dramatic masterpiece."
    plan = _plan(_shot(action=action))
    result = run_prompt_coach(plan, language="en")
    assert DiagnosticCode.COACH_AESTHETIC_NOISE in _codes(result)
    assert plan["shots"][0]["action"] == action
    diagnostic = next(item for item in result.diagnostics if item.code is DiagnosticCode.COACH_AESTHETIC_NOISE)
    assert diagnostic.repair.eligible is False


def test_coach_is_v2_only_and_caps_two_items_per_shot():
    legacy = run_prompt_coach({"schemaVersion": 1, "provided": True, "shots": []}, language="en")
    assert legacy.diagnostics == ()

    noisy = run_prompt_coach(_plan(_shot(
        openingState="She walks and looks and grabs the cinematic object beside Bea.",
        action="She walks and looks and grabs the cinematic object beside Bea, realistic photorealistic ultra detailed.",
        subjectPresenceComplete=True,
        subjects=[
            {"subjectId": "ana", "presence": "present"},
            {"subjectId": "bea", "presence": "present"},
        ],
    )), language="en")
    assert len(noisy.diagnostics) <= 2
    assert noisy.suppressed_coach >= 1


def test_weak_cut_requires_every_structured_precondition():
    target = {"kind": "subject", "id": "ana"}
    common = {
        "subjectPresenceComplete": True,
        "subjects": [{"subjectId": "ana", "presence": "present"}],
        "environment": {"environmentId": "bridge"},
        "cameraStart": {"viewpoint": "profile", "primaryTarget": target},
    }
    first = _shot("s1", "Ana stands beside the railing facing the river.", **common)
    second = _shot(
        "s2", "Ana remains beside the railing facing the river.",
        openingState="Ana stands beside the railing facing the river.",
        cutContext={"timeRelation": "continuous", "purpose": "unspecified"},
        **common,
    )
    result = run_prompt_coach(
        _plan(first, second), language="en", no_dialogue_between={("s1", "s2")},
    )
    assert DiagnosticCode.COACH_WEAK_CUT in _codes(result)

    no_proof = run_prompt_coach(_plan(first, second), language="en")
    assert DiagnosticCode.COACH_WEAK_CUT not in _codes(no_proof)


def test_dialogue_timing_is_advice_using_approximate_2_5_words_per_second():
    pressured = run_prompt_coach(_plan(_shot(
        action='Ana says: <d>[English] This line contains far too many spoken words for one brief second.</d>',
        durationSeconds=1,
    )), language="en")
    assert DiagnosticCode.COACH_DIALOGUE_TIMING_PRESSURE in _codes(pressured)
    diagnostic = next(
        item for item in pressured.diagnostics
        if item.code is DiagnosticCode.COACH_DIALOGUE_TIMING_PRESSURE
    )
    assert diagnostic.repair.eligible is False

    comfortable = run_prompt_coach(_plan(_shot(
        action='Ana says: <d>[English] We made it.</d>', durationSeconds=3,
    )), language="en")
    assert DiagnosticCode.COACH_DIALOGUE_TIMING_PRESSURE not in _codes(comfortable)
