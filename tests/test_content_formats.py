import json

import pytest

from content_formats import (
    CONTENT_FORMAT_DIMENSIONS,
    CONTENT_FORMAT_PROFILES,
    content_format_instruction,
    content_format_signatures,
    resolve_content_format,
)
from creative_treatments import (
    TITLE_SCREEN_STYLE_PROFILES,
    compose_creative_treatment,
    parse_creative_treatment,
)
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
    "opening_title_sequence",
    "procedural_how_to",
    "music_driven_visual_sequence",
    "seamless_loop",
}


def source_for(name):
    return {
        "interview_mini_profile": 'The supplied speaker says "This is the exact supplied soundbite."',
        "opening_title_sequence": (
            'Anime opening: three supplied heroes cross the supplied mountain while the exact title "SKY PATH" '
            "appears before the supplied final tableau."
        ),
        "procedural_how_to": "First fold the supplied cloth, then tie the supplied cord, and finally hold the knot.",
        "music_driven_visual_sequence": "The supplied shapes move against the authorized continuous music track.",
        "lyric_music_video": 'The authorized music track carries the exact lyric "Run into the light."',
        "performance_music_video": "The supplied quartet performs the authorized continuous music track.",
        "progressive_metaphor_explainer": "Use the supplied bridge as a visual metaphor for the supplied relationship.",
    }.get(name, "A supplied subject performs the supplied action and reaches the supplied ending.")


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
        source_prompt=source_for(name),
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


def test_echoed_format_arc_is_stripped_in_base_and_chained_modes():
    """The arc orders the timeline; quoting it would hand H3 a stage note to render."""
    item = resolved("brand_promo")
    base = (
        "integrated_multimodal_description:\n"
        f"{item['signature']}\nA product moves.\n"
        "overall_soundscape:\nN/A\nnon_diegetic_music:\nN/A"
    )
    once = normalize_content_format_signature(base, "t2va", item)
    assert item["signature"] not in once
    assert "A product moves." in once
    assert normalize_content_format_signature(once, "t2va", item) == once

    signatures = content_format_signatures(item, 2)
    chained = json.dumps({"prompts": [f"{signatures[0]} First.", f"{signatures[1]} Second."]})
    chained_once = normalize_content_format_signature(chained, "chained_multishot", item)
    assert normalize_content_format_signature(chained_once, "chained_multishot", item) == chained_once
    prompts = json.loads(chained_once)["prompts"]
    assert all(signature not in value for signature, value in zip(signatures, prompts))
    assert "First." in prompts[0] and "Second." in prompts[1]


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
    assert music["notAppliedReason"] == "missing_authorized_music"
    supplied_master = resolved(
        "lyric_music_video", background_score_policy="off",
        source_prompt='The supplied audio track contains the exact lyric "Hold on."',
    )
    assert supplied_master["applied"] is True


def test_new_format_gates_are_source_grounded_and_opening_without_title_stays_text_free():
    empty_opening = resolved("opening_title_sequence", source_prompt="Make an anime opening.")
    assert empty_opening["notAppliedReason"] == "missing_opening_anchor"
    visual_opening = resolved(
        "opening_title_sequence",
        source_prompt="Anime opening: the supplied red-haired pilot walks through the supplied hangar.",
        duration_seconds=5.0,
    )
    assert visual_opening["applied"] is True
    assert visual_opening["warnings"]
    assert "at most one distinct supplied beat" in " ".join(
        visual_opening["dimensions"]["editing_and_pacing"]
    )
    assert resolved("procedural_how_to", source_prompt="Show how to tie a knot.")["notAppliedReason"] == "missing_supplied_steps"
    assert resolved("procedural_how_to", source_prompt=source_for("procedural_how_to"))["applied"] is True
    assert resolved(
        "music_driven_visual_sequence", source_prompt="Three supplied shapes rotate in sequence.",
    )["notAppliedReason"] == "missing_authorized_music"
    assert resolved(
        "music_driven_visual_sequence", source_prompt=source_for("music_driven_visual_sequence"),
    )["applied"] is True


def test_opening_duration_guidance_scales_density_without_authorizing_cuts():
    short = resolved("opening_title_sequence", source_prompt=source_for("opening_title_sequence"), duration_seconds=5)
    medium = resolved("opening_title_sequence", source_prompt=source_for("opening_title_sequence"), duration_seconds=10)
    long = resolved("opening_title_sequence", source_prompt=source_for("opening_title_sequence"), duration_seconds=15)
    assert "at most one distinct supplied beat" in " ".join(short["dimensions"]["editing_and_pacing"])
    assert "one or two distinct supplied" in " ".join(medium["dimensions"]["editing_and_pacing"])
    assert "at most three or four distinct supplied beats" in " ".join(long["dimensions"]["editing_and_pacing"])
    for item in (short, medium, long):
        assert "beats never authorize cuts" in " ".join(item["dimensions"]["editing_and_pacing"]).lower()


def test_opening_defaults_to_integrated_title_after_establishing_the_anchor():
    item = resolved(
        "opening_title_sequence",
        source_prompt='Jason Voorhees walks down the street and title "Jason Kills" appears.',
        duration_seconds=5,
    )
    pacing = " ".join(item["dimensions"]["editing_and_pacing"])
    framing = " ".join(item["dimensions"]["camera_and_framing"])
    design = " ".join(item["dimensions"]["production_design"])
    assert item["profileVersion"] == 2
    assert "establish at least one supplied visual anchor" in pacing
    assert "never default to a detached first card" in pacing
    assert "hero graphic" in framing
    assert "purposeful foreground overlap or partial occlusion" in framing
    assert "subordinate credits in stable title-safe regions" in framing
    assert "resolved genre, visual language, world aesthetic, tone" in design


def test_opening_request_combines_full_format_and_visual_bibles_without_emitting_ids():
    request = build_user_request(
        source_for("opening_title_sequence"),
        "t2va",
        10.0,
        creative_treatment_json=json.dumps({
            "schemaVersion": 1,
            "contentFormat": "opening_title_sequence",
            "genre": "adventure",
            "visualLanguage": "anime_shonen",
            "worldAesthetic": "high_fantasy",
            "tone": "epic",
            "titleScreenStyle": "classic_cel",
        }),
    )
    assert CONTENT_FORMAT_PROFILES["opening_title_sequence"]["signature"] in request
    assert "non-photorealistic hand-authored 2D action-anime" in request
    assert "SOURCE-AUTHORIZED TITLE SCREEN" in request
    assert "Explicit Cinematography remains authoritative" in request
    assert "Preserve grammatical ownership and attachment exactly" in request
    assert "one or two distinct supplied" in request
    for identifier in ("opening_title_sequence", "anime_shonen", "high_fantasy", "classic_cel"):
        assert identifier not in request


def test_series_called_wording_sends_the_title_style_bible_to_the_llm():
    request = build_user_request(
        'Doraemon faces Jason Voorhees, for the series called "Jason Kills".',
        "t2va",
        10.0,
        creative_treatment_json=json.dumps({
            "schemaVersion": 1,
            "contentFormat": "opening_title_sequence",
            "titleScreenStyle": "classic_cel",
        }),
    )
    lock = TITLE_SCREEN_STYLE_PROFILES["classic_cel"]["deliveryLock"]
    assert "SOURCE-AUTHORIZED TITLE SCREEN" in request
    assert lock in request


def test_every_format_has_distinct_first_middle_final_chained_roles():
    for name in EXPECTED_FORMATS:
        item = resolved(name, source_prompt=source_for(name), mode="chained_multishot")
        signatures = content_format_signatures(item, 3)
        assert len(signatures) == 3
        assert len(set(signatures)) == 3
        assert item["signature"] not in signatures


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
