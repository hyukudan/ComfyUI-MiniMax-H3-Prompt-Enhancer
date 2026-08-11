import json

from creative_treatments import (
    CINEMATOGRAPHY_CHOICES,
    CINEMATOGRAPHY_JSON_KEYS,
    GENRE_PROFILES,
    TONE_PROFILES,
    VISUAL_LANGUAGE_PROFILES,
    WORLD_AESTHETIC_PROFILES,
    compose_creative_treatment,
    parse_cinematography,
    resolve_visual_style,
)
from prompt_enhancer import enhance_prompt_with_completion
from prompt_guides import build_user_request, normalize_visual_style_signature, validate_prompt


ANIME_JSON = json.dumps({
    "schemaVersion": 1,
    "genre": "none",
    "visualLanguage": "anime_general",
    "worldAesthetic": "none",
    "tone": "none",
})

SOURCE = "An elderly woman in a red coat walks slowly, then stops. No music."

BASE_OUTPUT = """integrated_multimodal_description:
[Shot 1] An elderly woman in a red coat walks slowly from left to right, then stops in a stable final pose.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""

REF_OUTPUT = """subject_definitions:
<Subject 1> is the elderly woman in a red coat from <Picture 1>.

summary:
[reference generation] The elderly woman walks slowly, then stops.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - identity, age, and red coat remain unchanged.

detailed_description:
[Shot 1] <Subject 1>, the elderly woman in a red coat from <Picture 1>, walks slowly from left to right, then stops in a stable final pose.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""


def _anime_style(cinematography=None):
    return resolve_visual_style(
        compose_creative_treatment(visual_language="anime_general"),
        cinematography or parse_cinematography(""),
    )


def test_anime_signature_is_executable_medium_specific_and_never_uses_negative_guards():
    style = _anime_style()
    signature = style["visualSignature"]

    assert "anime" in signature.casefold()
    assert "non-photorealistic" in signature.casefold()
    assert "2d" in signature.casefold()
    assert "cel-shading" in signature.casefold()
    assert "hand-authored" in signature.casefold()
    assert "live action" not in signature.casefold()
    assert "powers" not in signature.casefold()
    assert "auras" not in signature.casefold()
    assert "must_not_invent" not in style["visualLanguageLineIndexes"]
    assert "Visual style signature:" not in signature
    assert len(signature) < 600


def test_signature_is_compiled_after_cinematography_and_defers_to_explicit_controls():
    cinematography = parse_cinematography({
        "schemaVersion": 1,
        "cameraMotion": "tracking",
        "cameraAmplitude": "large",
        "cameraSpeed": "slow",
        "colorPalette": "vibrant",
    })
    style = _anime_style(cinematography)

    assert style["cameraMotionInstruction"]
    assert {item["field"] for item in style["cinematographyDirectives"]} >= {
        "camera_motion", "camera_amplitude", "camera_speed", "color_palette",
    }
    assert "explicit shot and cinematography controls" in style["creativeSignature"]
    assert "non-photorealistic hand-authored 2D anime" in style["visualSignature"]
    assert style["cameraMotionInstruction"] in style["cinematographySignature"]
    assert style["resolvedSignature"].endswith(style["cinematographySignature"])


def test_signature_normalization_is_idempotent_in_base_and_ref2va():
    style = _anime_style()
    signature = style["visualSignature"]

    base = normalize_visual_style_signature(BASE_OUTPUT, "t2va", style)
    ref = normalize_visual_style_signature(REF_OUTPUT, "ref2va", style)

    assert base.count(signature) == 1
    assert ref.count(signature) == 1
    assert base.index(signature) < base.index("[Shot 1]")
    assert ref.index(signature) < ref.index("[Shot 1]", ref.index("detailed_description:"))
    assert normalize_visual_style_signature(base, "t2va", style) == base
    assert normalize_visual_style_signature(ref, "ref2va", style) == ref
    assert "elderly woman in a red coat" in base
    assert "<Subject 1>" in ref


def test_signature_normalization_is_idempotent_in_every_chained_item():
    style = _anime_style()
    signature = style["visualSignature"]
    original = json.dumps({"prompts": [
        "An elderly woman in a red coat walks slowly from left to right.",
        "The elderly woman in the same red coat stops in a stable final pose.",
    ]})

    normalized = normalize_visual_style_signature(original, "chained_multishot", style)
    prompts = json.loads(normalized)["prompts"]

    assert all(item.count(signature) == 1 for item in prompts)
    assert "walks slowly" in prompts[0]
    assert "stops in a stable final pose" in prompts[1]
    assert normalize_visual_style_signature(normalized, "chained_multishot", style) == normalized


def test_validator_requires_canonical_signature_instead_of_every_visual_profile_line():
    missing = validate_prompt(
        BASE_OUTPUT, "t2va", 5.0, SOURCE,
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )
    assert missing["styleCoverageGaps"] == [
        "Canonical resolved presentation signature is missing or was changed"
    ]

    style = missing["resolvedVisualStyle"]
    normalized = normalize_visual_style_signature(BASE_OUTPUT, "t2va", style)
    present = validate_prompt(
        normalized, "t2va", 5.0, SOURCE,
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )
    assert present["styleCoverageGaps"] == []


def test_enhancer_delivers_signature_in_base_and_every_chained_item():
    base, base_report, base_manifest = enhance_prompt_with_completion(
        SOURCE, "t2va", 5.0, "", lambda _messages: BASE_OUTPUT, 0, {"provider": "test"},
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )
    signature = base_manifest["resolvedVisualStyle"]["visualSignature"]
    assert base.count(signature) == 1
    assert base_report["styleCoverageGaps"] == []

    chained_source = (
        "An elderly woman in a red coat walks slowly from left to right. "
        "The same elderly woman in the same red coat then stops in a stable final pose. No music."
    )
    generated = json.dumps({"prompts": [
        "An elderly woman in a red coat walks slowly from left to right.",
        "The same elderly woman in the same red coat stops in a stable final pose.",
    ]})
    chained, chained_report, _manifest = enhance_prompt_with_completion(
        chained_source, "chained_multishot", 5.0, "", lambda _messages: generated, 0,
        {"provider": "test"}, multishot_shot_count=2,
        creative_treatment_json=ANIME_JSON, enhance_description=True,
    )
    items = json.loads(chained)["prompts"]
    assert all(item.count(signature) == 1 for item in items)
    assert chained_report["styleCoverageGaps"] == []
    assert all("elderly woman" in item for item in items)
    assert all("red coat" in item for item in items)


def test_every_visual_language_has_one_unique_executable_signature_in_the_delivered_prompt():
    signatures = {}
    for visual_language in VISUAL_LANGUAGE_PROFILES:
        if visual_language == "none":
            continue
        treatment = json.dumps({
            "schemaVersion": 1,
            "genre": "none",
            "visualLanguage": visual_language,
            "worldAesthetic": "none",
            "tone": "none",
        })
        delivered, report, manifest = enhance_prompt_with_completion(
            SOURCE, "t2va", 5.0, "", lambda _messages: BASE_OUTPUT, 0,
            {"provider": "test"}, creative_treatment_json=treatment,
            enhance_description=True,
        )
        signature = manifest["resolvedVisualStyle"]["visualSignature"]
        assert signature
        assert delivered.count(signature) == 1
        assert report["styleCoverageGaps"] == []
        signatures.setdefault(signature, []).append(visual_language)

    assert len(signatures) == len(VISUAL_LANGUAGE_PROFILES) - 1
    assert all(len(profile_ids) == 1 for profile_ids in signatures.values())


def test_visual_language_is_not_applied_when_description_enhancement_is_off():
    delivered, report, manifest = enhance_prompt_with_completion(
        SOURCE, "t2va", 5.0, "", lambda _messages: BASE_OUTPUT, 0,
        {"provider": "test"}, creative_treatment_json=ANIME_JSON,
        enhance_description=False,
    )

    assert delivered == BASE_OUTPUT
    assert manifest["resolvedVisualStyle"]["visualSignature"] == ""
    assert report["styleCoverageGaps"] == []


def test_every_genre_world_aesthetic_and_tone_has_a_unique_required_signature():
    axes = (
        ("genre", "genre", GENRE_PROFILES),
        ("worldAesthetic", "world_aesthetic", WORLD_AESTHETIC_PROFILES),
        ("tone", "tone", TONE_PROFILES),
    )
    for external_axis, compose_axis, profiles in axes:
        signatures = {}
        for profile_id in profiles:
            if profile_id == "none":
                continue
            selections = {
                "genre": "none",
                "visual_language": "none",
                "world_aesthetic": "none",
                "tone": "none",
                compose_axis: profile_id,
            }
            style = resolve_visual_style(compose_creative_treatment(**selections), {})
            signature = style["creativeSignatures"][external_axis]
            assert signature
            assert signature in style["resolvedSignature"]
            assert "must_not_invent" not in signature
            signatures.setdefault(signature, []).append(profile_id)
        assert len(signatures) == len(profiles) - 1
        assert all(len(profile_ids) == 1 for profile_ids in signatures.values())


def test_all_four_creative_axes_and_cinematography_are_delivered_as_one_contract():
    treatment = json.dumps({
        "schemaVersion": 1,
        "genre": "action",
        "visualLanguage": "anime_general",
        "worldAesthetic": "cyberpunk",
        "tone": "tense",
    })
    cinematography = json.dumps({
        "schemaVersion": 1,
        "colorPalette": "vibrant",
        "cameraMotion": "tracking",
        "cameraAmplitude": "large",
        "cameraSpeed": "slow",
        "optics": "lens_35mm",
        "depthOfField": "balanced",
    })
    delivered, report, manifest = enhance_prompt_with_completion(
        SOURCE, "t2va", 5.0, "", lambda _messages: BASE_OUTPUT, 0,
        {"provider": "test"}, creative_treatment_json=treatment,
        cinematography_json=cinematography, enhance_description=True,
    )
    style = manifest["resolvedVisualStyle"]

    assert set(style["creativeSignatures"]) == {
        "genre", "visualLanguage", "worldAesthetic", "tone",
    }
    assert style["cameraMotionInstruction"] in style["cinematographySignature"]
    assert delivered.count(style["resolvedSignature"]) == 1
    assert report["styleCoverageGaps"] == []


def test_llm_receives_expanded_direction_without_private_preset_ids():
    treatment = json.dumps({
        "schemaVersion": 1,
        "genre": "action",
        "visualLanguage": "anime_general",
        "worldAesthetic": "cyberpunk",
        "tone": "tense",
    })
    request = build_user_request(
        SOURCE, "t2va", 5.0, enhance_description=True,
        creative_treatment_json=treatment,
    )

    for private_id in (
        "genre:action",
        "visual_language:anime_general",
        "world_aesthetic:cyberpunk",
        "tone:tense",
    ):
        assert private_id not in request
    for concrete_instruction in (
        "anticipation, action, impact, and recovery",
        "non-photorealistic hand-authored 2D anime",
        "high-tech/low-life material contrast",
        "controlled pauses, and anticipation",
    ):
        assert concrete_instruction in request


def test_every_creative_catalog_entry_is_expanded_before_the_llm_request():
    catalogs = {
        "genre": ("genre", GENRE_PROFILES),
        "visualLanguage": ("visual_language", VISUAL_LANGUAGE_PROFILES),
        "worldAesthetic": ("world_aesthetic", WORLD_AESTHETIC_PROFILES),
        "tone": ("tone", TONE_PROFILES),
    }
    for external_axis, (internal_axis, catalog) in catalogs.items():
        for profile_name in catalog:
            if profile_name == "none":
                continue
            treatment = {
                "schemaVersion": 1,
                "genre": "none",
                "visualLanguage": "none",
                "worldAesthetic": "none",
                "tone": "none",
                external_axis: profile_name,
            }
            treatment_json = json.dumps(treatment)
            style = resolve_visual_style(
                compose_creative_treatment(**{internal_axis: profile_name}),
                parse_cinematography(""),
            )
            signature = style["creativeSignatures"][external_axis]
            request = build_user_request(
                SOURCE, "t2va", 5.0, enhance_description=True,
                creative_treatment_json=treatment_json,
            )

            assert signature
            assert signature in request
            assert f"{internal_axis}:{profile_name}" not in request


def test_every_cinematography_choice_compiles_into_the_delivered_contract():
    external_keys = {internal: external for external, internal in CINEMATOGRAPHY_JSON_KEYS.items()}
    for field, choices in CINEMATOGRAPHY_CHOICES.items():
        default = "auto" if field in {"camera_amplitude", "camera_speed"} else "none"
        for choice in choices:
            if choice == default:
                continue
            payload = {"schemaVersion": 1, external_keys[field]: choice}
            if field in {"camera_amplitude", "camera_speed"}:
                payload["cameraMotion"] = "tracking"
            cinematography = parse_cinematography(payload)
            style = resolve_visual_style(compose_creative_treatment(), cinematography)
            signature = style["cinematographySignature"]
            assert signature
            if field == "camera_amplitude":
                assert f"{choice} amplitude" in signature
            elif field == "camera_speed":
                assert f"{choice} speed" in signature
            elif field != "camera_motion":
                assert CINEMATOGRAPHY_CHOICES[field][choice] in signature

            delivered = normalize_visual_style_signature(BASE_OUTPUT, "t2va", style)
            assert delivered.count(style["resolvedSignature"]) == 1
