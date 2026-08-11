import json

import pytest

from content_formats import (
    CONTENT_FORMAT_DIMENSIONS,
    CONTENT_FORMAT_PROFILES,
    content_format_instruction,
    content_format_signatures,
    resolve_content_format,
)
from creative_treatments import compose_creative_treatment, parse_creative_treatment
from prompt_guides import (
    build_user_request,
    content_format_coverage_gaps,
    normalize_content_format_signature,
)


EXPECTED_FORMATS = {
    "narrative_animation_short",
    "brand_promo",
    "co_op_game_intro",
    "handdrawn_live_fusion",
    "minimalist_product_ad",
    "lyric_music_video",
    "progressive_metaphor_explainer",
    "mechanism_explainer",
    "general_educational_explainer",
    "product_demo_tutorial",
    "cinematic_teaser",
    "interview_mini_profile",
    "performance_music_video",
    "seamless_loop",
}


def resolved(name, **overrides):
    arguments = {
        "enabled": True,
        "source_prompt": "A supplied subject performs the supplied action and reaches the supplied ending.",
        "voice_performance": "audible",
        "background_score_policy": "follow_prompt",
        "mode": "t2va",
    }
    arguments.update(overrides)
    return resolve_content_format(name, **arguments)


def test_catalog_is_complete_and_every_format_has_a_deep_unique_bible():
    assert set(CONTENT_FORMAT_PROFILES) == {"none", *EXPECTED_FORMATS}
    signatures = set()
    for name in EXPECTED_FORMATS:
        profile = CONTENT_FORMAT_PROFILES[name]
        assert profile["signature"]
        assert profile["signature"] not in signatures
        signatures.add(profile["signature"])
        assert all(profile[dimension] for dimension in CONTENT_FORMAT_DIMENSIONS)


@pytest.mark.parametrize("name", sorted(EXPECTED_FORMATS))
def test_each_format_expands_full_instructions_not_its_label(name):
    item = resolved(
        name,
        source_prompt=(
            'The supplied speaker says "This is the exact supplied soundbite."'
            if name == "interview_mini_profile"
            else "A supplied subject performs the supplied action and reaches the supplied ending."
        ),
    )
    instruction = content_format_instruction(item)
    assert item["applied"] is True
    assert item["signature"] in instruction
    assert "STRUCTURE, NOT LOOK" in instruction
    assert f"content_format:{name}" not in instruction
    assert name not in instruction


def test_json_is_backward_compatible_and_content_format_is_canonical():
    legacy = parse_creative_treatment(
        '{"schemaVersion":1,"genre":"none","visualLanguage":"none",'
        '"worldAesthetic":"none","tone":"none"}'
    )
    assert legacy["contentFormat"] == "none"
    selected = compose_creative_treatment(content_format="brand_promo")
    assert selected["contentFormat"] == "brand_promo"
    assert json.loads(selected["canonicalJson"])["contentFormat"] == "brand_promo"


def test_unknown_content_format_fails_closed():
    with pytest.raises(ValueError, match="Unsupported content format"):
        parse_creative_treatment('{"schemaVersion":1,"contentFormat":"made_up"}')


def test_request_receives_the_expanded_bible_and_audio_precedence():
    request = build_user_request(
        "The supplied physical product opens and reaches its supplied final state.",
        "t2va",
        5.0,
        creative_treatment_json=json.dumps({
            "schemaVersion": 1,
            "contentFormat": "minimalist_product_ad",
        }),
        background_score_policy="off",
    )
    assert "SOURCE-GROUNDED CONTENT / PRODUCTION FORMAT" in request
    assert CONTENT_FORMAT_PROFILES["minimalist_product_ad"]["signature"] in request
    assert "background_score_policy=off" in request
    assert "minimalist_product_ad" not in request


def test_signature_normalization_is_idempotent_in_base_and_chained_modes():
    item = resolved("brand_promo")
    base = "integrated_multimodal_description:\nA product moves.\noverall_soundscape:\nN/A\nnon_diegetic_music:\nN/A"
    once = normalize_content_format_signature(base, "t2va", item)
    assert normalize_content_format_signature(once, "t2va", item) == once
    assert once.count(item["signature"]) == 1
    chained = '{"prompts":["First.","Second."]}'
    chained_once = normalize_content_format_signature(chained, "chained_multishot", item)
    assert normalize_content_format_signature(chained_once, "chained_multishot", item) == chained_once
    assert all(
        signature in value
        for signature, value in zip(
            content_format_signatures(item, 2), json.loads(chained_once)["prompts"]
        )
    )


def test_coverage_reports_missing_signature():
    item = resolved("mechanism_explainer")
    assert content_format_coverage_gaps("plain output", "t2va", item)
    assert not content_format_coverage_gaps(item["signature"], "t2va", item)


def test_source_gates_fail_closed_for_interview_and_music_policy():
    interview = resolved("interview_mini_profile", source_prompt="A woman sits in a room.")
    assert interview["requested"] is True
    assert interview["applied"] is False
    assert interview["notAppliedReason"] == "missing_attributed_soundbite"
    music = resolved("lyric_music_video", background_score_policy="off")
    assert music["applied"] is False
    assert music["notAppliedReason"] == "audio_policy_conflict"


def test_disabled_enhancement_records_selection_without_applying_it():
    item = resolved("cinematic_teaser", enabled=False)
    assert item["requested"] is True
    assert item["applied"] is False
    assert item["notAppliedReason"] == "description_enhancement_disabled"
    assert content_format_instruction(item) == ""


def test_frontend_has_every_backend_format():
    source = open("web/backend_toggle.js", encoding="utf-8").read()
    for name in EXPECTED_FORMATS:
        assert f'["{name}",' in source
