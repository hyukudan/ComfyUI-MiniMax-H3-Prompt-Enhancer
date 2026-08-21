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
from prompt_guides import (
    build_user_request,
    normalize_visual_medium_anchor,
    normalize_visual_style_signature,
    validate_prompt,
)


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


def test_echoed_signature_is_stripped_in_base_and_ref2va():
    """H3 receives shot description, so a copied contract is removed, not preserved."""
    style = _anime_style()
    signature = style["visualSignature"]
    echoed_base = BASE_OUTPUT.replace(
        "integrated_multimodal_description:\n",
        f"integrated_multimodal_description:\n{signature}\n",
    )
    echoed_ref = REF_OUTPUT.replace(
        "detailed_description:\n", f"detailed_description:\n{signature}\n",
    )

    base = normalize_visual_style_signature(echoed_base, "t2va", style)
    ref = normalize_visual_style_signature(echoed_ref, "ref2va", style)

    assert signature not in base
    assert signature not in ref
    assert normalize_visual_style_signature(base, "t2va", style) == base
    assert normalize_visual_style_signature(ref, "ref2va", style) == ref
    assert "elderly woman in a red coat" in base
    assert "<Subject 1>" in ref


def test_echoed_signature_is_stripped_in_every_chained_item():
    style = _anime_style()
    signature = style["visualSignature"]
    original = json.dumps({"prompts": [
        f"{signature} An elderly woman in a red coat walks slowly from left to right.",
        f"{signature} The elderly woman in the same red coat stops in a stable final pose.",
    ]})

    normalized = normalize_visual_style_signature(original, "chained_multishot", style)
    prompts = json.loads(normalized)["prompts"]

    assert all(signature not in item for item in prompts)
    assert "walks slowly" in prompts[0]
    assert "stops in a stable final pose" in prompts[1]
    assert normalize_visual_style_signature(normalized, "chained_multishot", style) == normalized


def test_catalogue_coverage_is_advisory_and_never_reaches_the_repair_loop():
    """Catalogue prose warns; only explicit cinematography is repairable.

    Measured across five visual languages, feeding catalogue lines back as repair issues
    closed no gap, made several outputs worse, and tripled generation time: those lines mix
    requirements with prohibitions and with description of the style, so a missing one is not
    an actionable instruction. Repair stays reserved for the fields the user set explicitly.
    """
    report = validate_prompt(
        BASE_OUTPUT, "t2va", 5.0, SOURCE,
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )

    assert report["styleCoverageGaps"] == [], "catalogue prose must not block repair"
    advisories = [
        warning for warning in report["warnings"]
        if "may be under-realized" in warning
    ]
    assert advisories, "an unstyled timeline must still be reported to the user"
    assert any("camera_and_framing" in warning for warning in advisories)
    assert all(
        "Canonical resolved presentation signature" not in warning for warning in advisories
    )

    # Copying the contract in verbatim must NOT satisfy coverage: it is stripped first.
    style = report["resolvedVisualStyle"]
    echoed = BASE_OUTPUT.replace(
        "integrated_multimodal_description:\n",
        f"integrated_multimodal_description:\n{style['resolvedSignature']}\n",
    )
    normalized = normalize_visual_style_signature(echoed, "t2va", style)
    assert style["resolvedSignature"] not in normalized


def test_explicit_cinematography_stays_repairable():
    """A field the user set by hand is precise, so failing to realize it is a real gap."""
    cinematography = json.dumps({"schemaVersion": 1, "cameraMotion": "push_in"})
    report = validate_prompt(
        BASE_OUTPUT, "t2va", 5.0, SOURCE,
        creative_treatment_json=ANIME_JSON,
        cinematography_json=cinematography,
        enhance_description=True,
    )
    assert any(
        "not observably realized" in gap for gap in report["styleCoverageGaps"]
    ), "explicit camera control must remain a repairable gap"


def test_enhancer_never_delivers_the_contract_verbatim_in_base_or_chained_items():
    base, _base_report, base_manifest = enhance_prompt_with_completion(
        SOURCE, "t2va", 5.0, "", lambda _messages: BASE_OUTPUT, 0, {"provider": "test"},
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )
    signature = base_manifest["resolvedVisualStyle"]["visualSignature"]
    assert signature not in base
    assert "elderly woman in a red coat" in base

    chained_source = (
        "An elderly woman in a red coat walks slowly from left to right. "
        "The same elderly woman in the same red coat then stops in a stable final pose. No music."
    )
    generated = json.dumps({"prompts": [
        "An elderly woman in a red coat walks slowly from left to right.",
        "The same elderly woman in the same red coat stops in a stable final pose.",
    ]})
    chained, _chained_report, _manifest = enhance_prompt_with_completion(
        chained_source, "chained_multishot", 5.0, "", lambda _messages: generated, 0,
        {"provider": "test"}, multishot_shot_count=2,
        creative_treatment_json=ANIME_JSON, enhance_description=True,
    )
    items = json.loads(chained)["prompts"]
    assert all(signature not in item for item in items)
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
        assert signature not in delivered
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


def test_latin_american_telenovela_is_explicit_and_wins_over_generic_drama_pacing():
    treatment = json.dumps({
        "schemaVersion": 1,
        "genre": "drama",
        "visualLanguage": "live_action_latin_american_telenovela",
        "worldAesthetic": "none",
        "tone": "none",
    })
    delivered, report, manifest = enhance_prompt_with_completion(
        SOURCE, "t2va", 5.0, "", lambda _messages: BASE_OUTPUT, 0,
        {"provider": "test"}, creative_treatment_json=treatment,
        enhance_description=True,
    )

    signature = manifest["resolvedVisualStyle"]["visualSignature"]
    assert "polished Latin American telenovela visual system" in signature
    # Precedence is resolved in the contract sent to the writer; the contract itself is
    # never emitted, so the delivered prompt carries neither winner nor loser wording.
    assert signature not in delivered
    assert "without melodramatic acceleration" not in delivered
    assert "naturalistic pacing" not in delivered
    assert any(
        item["loserProfile"] == "drama" and item["winnerProfile"] == "live_action_latin_american_telenovela"
        for item in manifest["treatmentConflicts"]
    )


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
    # All four axes plus cinematography compile into one contract for the writer, and that
    # contract stays out of the delivered prompt.
    assert style["resolvedSignature"]
    assert style["resolvedSignature"] not in delivered


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

            echoed = BASE_OUTPUT.replace(
                "integrated_multimodal_description:\n",
                f"integrated_multimodal_description:\n{style['resolvedSignature']}\n",
            )
            delivered = normalize_visual_style_signature(echoed, "t2va", style)
            assert style["resolvedSignature"] not in delivered


def test_pixel_medium_invariants_survive_every_cinematography_choice():
    external_keys = {internal: external for external, internal in CINEMATOGRAPHY_JSON_KEYS.items()}
    for field, choices in CINEMATOGRAPHY_CHOICES.items():
        for value in choices:
            if value == "none" or field in {"camera_amplitude", "camera_speed"}:
                continue
            cinema = {"schemaVersion": 1, external_keys[field]: value}
            if field == "camera_motion" and value != "static":
                cinema.update({"cameraAmplitude": "small", "cameraSpeed": "slow"})
            style = resolve_visual_style(
                compose_creative_treatment(visual_language="pixel_art_16bit"),
                parse_cinematography(cinema),
            )
            signature = style["resolvedSignature"]
            assert "native non-photorealistic 16-bit-style pixel art" in signature
            assert "hard pixel clusters" in signature
            assert style["suppressedTreatmentLines"] == []


def test_pixel_photographic_controls_are_adapted_to_the_integer_grid():
    cinema = parse_cinematography({
        "schemaVersion": 1,
        "cameraMotion": "tracking",
        "cameraAmplitude": "small",
        "cameraSpeed": "slow",
        "depthOfField": "shallow",
        "imageTexture": "film_35mm",
        "lensEffects": "subtle_diffusion",
        "motionRendering": "natural_blur",
    })
    style = resolve_visual_style(
        compose_creative_treatment(visual_language="pixel_art_16bit"), cinema,
    )
    signature = style["resolvedSignature"]

    assert "integer-pixel displacement" in signature
    assert "no optical blur, bokeh, or soft focus" in signature
    assert "grid-aligned pixel-cluster variation" in signature
    assert "hard-edged palette clusters" in signature
    assert "grid-aligned pixel smear poses" in signature
    assert "Use shallow depth of field" not in signature
    assert "physically plausible natural motion blur" not in signature


def test_explicit_cinematography_never_suppresses_must_not_invent_lines():
    cinema = parse_cinematography({
        "schemaVersion": 1,
        "colorPalette": "vibrant",
        "cameraMotion": "tracking",
        "cameraAmplitude": "small",
        "cameraSpeed": "slow",
        "lensEffects": "subtle_diffusion",
    })
    for axis, catalog in (
        ("genre", GENRE_PROFILES),
        ("visual_language", VISUAL_LANGUAGE_PROFILES),
        ("world_aesthetic", WORLD_AESTHETIC_PROFILES),
        ("tone", TONE_PROFILES),
    ):
        for name in catalog:
            if name == "none":
                continue
            style = resolve_visual_style(
                compose_creative_treatment(**{axis: name}), cinema,
            )
            assert not any(
                item["dimension"] == "must_not_invent"
                for item in style["suppressedTreatmentLines"]
            )


def test_conservative_mode_does_not_reactivate_creative_profiles_when_cinema_is_selected():
    treatment = json.dumps({
        "schemaVersion": 1,
        "genre": "action",
        "visualLanguage": "anime_general",
        "worldAesthetic": "cyberpunk",
        "tone": "tense",
    })
    cinema = json.dumps({"schemaVersion": 1, "colorPalette": "vibrant"})
    request = build_user_request(
        SOURCE, "t2va", 5.0, enhance_description=False,
        creative_treatment_json=treatment,
        cinematography_json=cinema,
    )

    assert "EXPLICIT CINEMATOGRAPHY" in request
    assert "SECONDARY CREATIVE TREATMENT" not in request
    assert "non-photorealistic hand-authored 2D anime" not in request
    assert "anticipation, action, impact, and recovery" not in request


def test_pixel_validator_rejects_photographic_subpixel_language_even_with_canonical_signature():
    treatment = json.dumps({
        "schemaVersion": 1,
        "genre": "none",
        "visualLanguage": "pixel_art_16bit",
        "worldAesthetic": "none",
        "tone": "none",
    })
    style = resolve_visual_style(
        compose_creative_treatment(visual_language="pixel_art_16bit"),
        parse_cinematography(""),
    )
    contradictory = """integrated_multimodal_description:
[Shot 1] Photorealistic live-action materials use smooth gradients, soft bokeh, and subpixel movement.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""
    normalized = normalize_visual_style_signature(contradictory, "t2va", style)
    report = validate_prompt(
        normalized, "t2va", 5.0, SOURCE,
        creative_treatment_json=treatment,
        enhance_description=True,
    )

    assert not report["valid"]
    assert any("pixel-art profile was contradicted" in error for error in report["errors"])


def test_anime_validator_rejects_realistic_skeleton_leak_and_requests_repair():
    leaked = """integrated_multimodal_description:
[Shot 1] Cinematic realistic style. An elderly woman in a red coat walks slowly, then stops.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""
    report = validate_prompt(
        leaked, "t2va", 5.0, SOURCE,
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )

    assert not report["valid"]
    assert any("anime visual language was contradicted" in error for error in report["errors"])


def test_anime_music_cannot_satisfy_an_unrealized_visual_language():
    visually_neutral = """integrated_multimodal_description:
[Shot 1] An elderly woman in a red coat walks slowly, then stops.

overall_soundscape:
Quiet room tone.

non_diegetic_music:
A bright anime opening theme plays at a fast tempo."""
    report = validate_prompt(
        visually_neutral, "t2va", 5.0, SOURCE,
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )

    assert not report["valid"]
    assert any("not observably realized in the visual description" in error for error in report["errors"])


def test_observable_anime_medium_anchor_satisfies_visual_language():
    visible_anime = BASE_OUTPUT.replace(
        "[Shot 1] ",
        "[Shot 1] Hand-authored 2D anime line art and stable cel-shaded value groups depict ",
    )
    report = validate_prompt(
        visible_anime, "t2va", 5.0, SOURCE,
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )

    assert not any("not observably realized in the visual description" in error for error in report["errors"])


def test_missing_visual_medium_is_deterministically_anchored_before_delivery():
    treatment = compose_creative_treatment(visual_language="stop_motion_handcrafted")
    anchored = normalize_visual_medium_anchor(BASE_OUTPUT, "t2va", treatment, SOURCE)

    assert "handcrafted stop-motion animation" in anchored
    assert anchored.index("handcrafted stop-motion animation") < anchored.index("elderly woman")


def test_supermarionation_gets_an_unmistakable_puppet_and_miniature_anchor():
    treatment = compose_creative_treatment(visual_language="supermarionation")
    anchored = normalize_visual_medium_anchor(BASE_OUTPUT, "t2va", treatment, SOURCE)

    assert "1960s Supermarionation craft" in anchored
    assert "visibly artificial marionette" in anchored
    assert "glossy sculpted head" in anchored
    assert "practical miniature" in anchored


def test_explicit_source_medium_outranks_incompatible_selector_anchor():
    treatment = compose_creative_treatment(visual_language="stop_motion_handcrafted")
    source = "A 1990s anime scene shows an elderly woman walking."
    anchored = normalize_visual_medium_anchor(BASE_OUTPUT, "t2va", treatment, source)

    assert anchored == BASE_OUTPUT


def test_anime_validator_preserves_explicitly_requested_live_action_hybrid():
    hybrid_source = "Render the scene as a live-action and anime hybrid. No music."
    hybrid = """integrated_multimodal_description:
[Shot 1] A live-action and hand-authored 2D anime hybrid shows an elderly woman walking, then stopping.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""
    report = validate_prompt(
        hybrid, "t2va", 5.0, hybrid_source,
        creative_treatment_json=ANIME_JSON,
        enhance_description=True,
    )

    assert not any("anime visual language was contradicted" in error for error in report["errors"])


def test_system_examples_do_not_hardcode_a_realistic_visual_style():
    from prompt_guides import MULTISHOT_SYSTEM_PROMPT, SYSTEM_PROMPT

    assert "Cinematic realistic style" not in SYSTEM_PROMPT
    assert "Cinematic realistic style" not in MULTISHOT_SYSTEM_PROMPT


def test_every_catalogue_profile_is_selectable_and_nothing_selectable_is_missing():
    """The hand-written preset list had drifted from the catalogue in both directions.

    It offered "papercraft_stop_motion", which is not a profile and raised ValueError the
    moment a user picked it, while 36 real profiles — supermarionation and
    live_action_visceral_horror among them — could not be selected at all. Deriving the list
    is what makes the two impossible to separate again.
    """
    import prompt_enhancer_node
    from creative_treatments import VISUAL_LANGUAGE_PROFILES

    presets = set(prompt_enhancer_node.VISUAL_STYLE_PRESET_CHOICES)
    catalogue = set(VISUAL_LANGUAGE_PROFILES)
    assert "none" in presets
    assert presets == catalogue | {"none"}
    for expected in ("supermarionation", "live_action_visceral_horror"):
        assert expected in presets
    assert "papercraft_stop_motion" not in presets


def test_every_preset_reaches_the_request_with_its_own_vocabulary():
    """Selecting a preset must deliver that profile's wording, not just a style header."""
    import prompt_enhancer_node
    from creative_treatments import VISUAL_LANGUAGE_PROFILES
    from prompt_enhancer_node import _merge_visual_style_preset

    for preset in prompt_enhancer_node.VISUAL_STYLE_PRESET_CHOICES:
        if preset == "none":
            continue
        request = build_user_request(
            "A girl walks through a forest.", "t2va", 10.0, "", True,
            creative_treatment_json=_merge_visual_style_preset("", preset),
        )
        assert "RESOLVED VISUAL STYLE BIBLE" in request, preset
        profile = VISUAL_LANGUAGE_PROFILES[preset]
        lines = [
            item for key, value in profile.items() if key not in ("version", "tags")
            for item in ([value] if isinstance(value, str)
                         else list(value) if isinstance(value, (list, tuple)) else [])
        ]
        assert any(str(line)[:60] in request for line in lines), preset


def test_character_performance_survives_the_compact_signature():
    """Set dressing cannot stand in for how a character moves.

    supermarionation anchors on production_design, so the signature carried miniature sets and
    dropped blocking_and_performance entirely — the finished prompt described a normal character
    standing in a model set, with none of the puppet artifice that is the whole point of the style.
    """
    from creative_treatments import VISUAL_LANGUAGE_PROFILES, _compact_profile_signature

    profile = VISUAL_LANGUAGE_PROFILES["supermarionation"]
    signature = _compact_profile_signature(
        "visual_language", {k: list(v) for k, v in profile.items() if isinstance(v, (list, tuple))}
    )
    assert "miniature" in signature
    assert "marionettes" in signature, "puppet performance dropped from the signature"

    for name, prof in VISUAL_LANGUAGE_PROFILES.items():
        blocking = [str(line) for line in prof.get("blocking_and_performance", ()) if str(line).strip()]
        if not blocking:
            continue
        sig = _compact_profile_signature(
            "visual_language", {k: list(v) for k, v in prof.items() if isinstance(v, (list, tuple))}
        )
        assert blocking[0].rstrip(" .")[:50] in sig, name


def test_forbidden_inventions_do_not_outrank_an_explicit_request():
    """A bare ban list reads as absolute and deletes what the user asked for.

    supermarionation forbids visible strings so the style cannot drag a puppet gag in by itself.
    Emitted with no framing, that same line told the writer to strip the strings from a request
    that explicitly asked for them — the profile overruling the prompt it exists to serve.
    """
    from prompt_enhancer_node import _merge_visual_style_preset

    request = build_user_request(
        "A minion eats a burger, visible strings running up from his hands to a rig above.",
        "t2va", 10.0, "", True,
        creative_treatment_json=_merge_visual_style_preset("", "supermarionation"),
    )
    heading = request.index("forbidden_inventions:")
    framing = request[heading:heading + 400]
    assert "on its own initiative" in framing
    assert "supplies explicitly is a fact" in framing
    assert framing.index("on its own initiative") < framing.index("Visible strings")


def test_invent_scene_is_not_cancelled_by_the_request_itself():
    """The toggle used to flip a label while the request still said the opposite.

    invented_production asks the writer to build the world around the premise, but the request
    carried a blanket "do not invent new characters, plot events..." line regardless of profile.
    Being nearer and more concrete, that line won, and the toggle changed nothing observable.
    """
    grounded = build_user_request("A minion eats a burger.", "t2va", 10.0, "", True,
                                  invent_scene=False)
    invented = build_user_request("A minion eats a burger.", "t2va", 10.0, "", True,
                                  invent_scene=True)
    assert "Do not invent new characters" in grounded
    assert "Do not invent new characters" not in invented
    # Silence, not a competing positive instruction: the invention contract already lives in the
    # system prompt, and restating it here would be one more clause to keep in step with it.
    # What is the user's stays locked in both.
    for request in (grounded, invented):
        assert "Do not invent dialogue." in request
        assert "beyond the source" in request
