# SPDX-License-Identifier: GPL-3.0-only

import json
from pathlib import Path

import pytest

from creative_treatments import (
    ANIMATION_CADENCE_CHOICES,
    ANIMATION_CADENCE_COMPATIBLE_VISUAL_LANGUAGES,
    parse_creative_treatment,
    treatment_warnings,
)


@pytest.mark.parametrize("cadence", ("ones", "twos", "threes"))
def test_animation_cadence_is_explicit_bounded_prose_for_compatible_styles(cadence):
    treatment = parse_creative_treatment({
        "schemaVersion": 2,
        "visualLanguage": "anime_1990s_broadcast_cel",
        "animationCadence": cadence,
    })

    assert treatment["animationCadence"] == cadence
    assert treatment["animationCadenceApplied"] is True
    assert ANIMATION_CADENCE_CHOICES[cadence] in treatment["dimensions"]["editing_and_pacing"]
    guardrails = " ".join(treatment["dimensions"]["must_not_invent"]).casefold()
    for protected in ("fps", "duration", "frame count", "motion blur", "camera speed"):
        assert protected in guardrails
    assert treatment_warnings(treatment) == []


def test_adaptive_is_neutral_and_round_trips_in_canonical_v2():
    treatment = parse_creative_treatment({"schemaVersion": 2, "animationCadence": "adaptive"})
    assert treatment["requested"] is False
    assert treatment["animationCadenceApplied"] is False
    assert json.loads(treatment["canonicalJson"])["animationCadence"] == "adaptive"


def test_incompatible_style_preserves_request_but_does_not_emit_cadence_prose():
    treatment = parse_creative_treatment({
        "schemaVersion": 2,
        "visualLanguage": "live_action_cinematic",
        "animationCadence": "twos",
    })
    assert treatment["animationCadence"] == "twos"
    assert treatment["animationCadenceApplied"] is False
    assert ANIMATION_CADENCE_CHOICES["twos"] not in treatment["dimensions"]["editing_and_pacing"]
    assert "inactive" in treatment_warnings(treatment)[0].casefold()


def test_cadence_never_backports_into_legacy_v1_or_accepts_unknown_values():
    with pytest.raises(ValueError, match="native schema v2"):
        parse_creative_treatment({"schemaVersion": 1, "animationCadence": "twos"})
    with pytest.raises(ValueError, match="Unsupported animation cadence"):
        parse_creative_treatment({"schemaVersion": 2, "animationCadence": "every_other_frame"})


def test_compatibility_catalog_is_explicit_and_excludes_live_action_and_3d():
    assert "anime_general" in ANIMATION_CADENCE_COMPATIBLE_VISUAL_LANGUAGES
    assert "stop_motion_handcrafted" in ANIMATION_CADENCE_COMPATIBLE_VISUAL_LANGUAGES
    assert "supermarionation" in ANIMATION_CADENCE_COMPATIBLE_VISUAL_LANGUAGES
    assert "live_action_cinematic" not in ANIMATION_CADENCE_COMPATIBLE_VISUAL_LANGUAGES
    assert "stylized_3d_animation" not in ANIMATION_CADENCE_COMPATIBLE_VISUAL_LANGUAGES


def test_frontend_exposes_cadence_as_advanced_experimental_not_as_fps():
    root = Path(__file__).parents[1]
    backend = (root / "web" / "backend_toggle.js").read_text(encoding="utf-8")
    look = (root / "web" / "studio" / "tab_camera_look.js").read_text(encoding="utf-8")
    assert '["adaptive", "Adaptive (no cadence request)"]' in backend
    assert 'key: "animationCadence"' in backend
    assert 'new Set(["contentFormat", "titleScreenStyle", "animationCadence"])' in look
    assert "It changes neither FPS nor duration" in look
    assert "no cadence prose will be emitted" in look
