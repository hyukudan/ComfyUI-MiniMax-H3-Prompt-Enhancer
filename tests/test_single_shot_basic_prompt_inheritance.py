# SPDX-License-Identifier: GPL-3.0-only

from prompt_enhancer import _inherit_basic_prompt_for_single_blank_shot
from prompt_guides import _build_user_request_compiled


def test_single_blank_shot_inherits_basic_prompt_without_mutating_source():
    source = {
        "schemaVersion": 2,
        "timingMode": "auto",
        "shots": [{
            "id": "s1",
            "generationId": "g1",
            "action": "",
            "subjects": [{"subjectId": "juan", "presence": "present"}],
        }],
    }

    effective, inherited = _inherit_basic_prompt_for_single_blank_shot(
        source, "Juan dances in the rain.",
    )

    assert inherited is True
    assert source["shots"][0]["action"] == ""
    assert effective["shots"][0]["action"] == "Juan dances in the rain."
    assert effective["shots"][0]["subjects"] == source["shots"][0]["subjects"]


def test_multiple_blank_shots_remain_strictly_ambiguous():
    source = {
        "schemaVersion": 2,
        "timingMode": "auto",
        "shots": [
            {"id": "s1", "generationId": "g1", "action": ""},
            {"id": "s2", "generationId": "g1", "action": ""},
        ],
    }
    effective, inherited = _inherit_basic_prompt_for_single_blank_shot(source, "They dance.")
    assert inherited is False
    assert effective is source


def test_existing_action_is_never_replaced():
    raw = '{"schemaVersion":2,"timingMode":"auto","shots":[{"id":"s1","generationId":"g1","action":"Juan waves."}]}'
    effective, inherited = _inherit_basic_prompt_for_single_blank_shot(raw, "Juan dances.")
    assert inherited is False
    assert effective == raw


def test_effective_single_shot_document_survives_final_request_compilation():
    raw = '{"schemaVersion":2,"timingMode":"auto","shots":[{"id":"s1","generationId":"g1","action":"","subjects":[{"subjectId":"juan","presence":"present"}]}]}'
    effective, inherited = _inherit_basic_prompt_for_single_blank_shot(
        raw, "Juan dances in the rain.",
    )
    assert inherited is True
    request = _build_user_request_compiled(
        "Juan dances in the rain.", "t2va", 4.0, "", True,
        "auto", "follow_prompt", "audible", "", "16:9", "", 0, 0,
        "", "", "", (), "", effective, "", "none", "none", "off",
    )
    assert 'action="Juan dances in the rain."' in request
    assert '"subjectId":"juan"' in request
