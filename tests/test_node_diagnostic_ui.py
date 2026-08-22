# SPDX-License-Identifier: GPL-3.0-only

import json

from prompt_enhancer_node import (
    MiniMaxH3GGUFPromptEnhancer,
    MiniMaxH3PromptEnhancer,
    _diagnostic_ui_payload,
)


def test_enhancers_use_ui_wrapper_without_changing_direct_enhance_contract():
    validation = {
        "valid": True,
        "qualityValid": True,
        "diagnosticReport": {
            "schemaVersion": 1,
            "summary": {"valid": True, "qualityValid": True, "advice": 1},
            "diagnostics": [{"code": "coach.action.opening_duplicate"}],
        },
    }
    direct = ("prompt", json.dumps(validation), "{}", 8.0, "16:9", "", 1280, 720)
    enhancer = MiniMaxH3PromptEnhancer()
    enhancer.enhance = lambda *args, **kwargs: direct

    wrapped = enhancer.enhance_with_ui()
    assert wrapped["result"] is direct
    payload = json.loads(wrapped["ui"]["minimax_h3_diagnostics"][0])
    assert payload["diagnostics"][0]["code"] == "coach.action.opening_duplicate"
    assert MiniMaxH3PromptEnhancer.FUNCTION == "enhance_with_ui"
    assert MiniMaxH3GGUFPromptEnhancer.FUNCTION == "enhance_with_ui"


def test_diagnostic_ui_payload_is_compact_and_tolerates_invalid_text():
    payload = _diagnostic_ui_payload("not json")
    assert len(payload) == 1
    decoded = json.loads(payload[0])
    assert decoded["diagnostics"] == []
    assert "\n" not in payload[0]
