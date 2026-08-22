# SPDX-License-Identifier: GPL-3.0-only

from creative_treatments import VISUAL_LANGUAGE_PROFILES, compose_creative_treatment, creative_treatment_instruction


NEW_VISUAL_LANGUAGES = {
    "vintage_rubberhose_2d": "Mascot characters",
    "cable_angular_graphic_comedy": "Jokes",
    "contemporary_vector_2d": "Corporate mascots",
    "manga_monochrome_print": "Panels",
    "anime_1960s70s_limited_cel": "Robots",
    "mecha_super_robot_cel": "Robots",
    "anime_ova_mechanical_detail": "military hardware",
    "anime_1990s_broadcast_cel": "Opening or ending sequences",
    "anime_digital_compositing": "Unmotivated particles",
}


def test_brand_safe_visual_language_additions_are_complete_and_guarded():
    assert len(NEW_VISUAL_LANGUAGES) == 9
    for token, guardrail in NEW_VISUAL_LANGUAGES.items():
        profile = VISUAL_LANGUAGE_PROFILES[token]
        for dimension in (
            "editing_and_pacing", "camera_and_framing", "lighting_and_color", "production_design",
            "blocking_and_performance", "sound_treatment", "may_fill_unspecified", "must_not_invent",
        ):
            assert profile[dimension], f"{token} has no {dimension}"
        assert guardrail in " ".join(profile["must_not_invent"])


def test_new_visual_languages_reach_the_style_bible_and_forbidden_output():
    for token in NEW_VISUAL_LANGUAGES:
        treatment = compose_creative_treatment(visual_language=token)
        instruction = creative_treatment_instruction(treatment)
        assert treatment["profileIds"] == [f"visual_language:{token}"]
        assert treatment["dimensions"]["production_design"]
        assert treatment["dimensions"]["must_not_invent"]
        assert "SECONDARY CREATIVE TREATMENT" in instruction
        assert "MUST NOT INVENT" in instruction
        assert treatment["dimensions"]["production_design"][0][:60] in instruction


def test_new_visual_language_names_are_brand_safe_tokens():
    forbidden = {"disney", "fleischer", "warner", "cartoon network", "pixar", "ghibli", "tezuka", "gainax"}
    for token in NEW_VISUAL_LANGUAGES:
        assert not any(name in token.lower() for name in forbidden)
