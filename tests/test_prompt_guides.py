# SPDX-License-Identifier: GPL-3.0-only

import json

import pytest

from prompt_guides import (
    ACOUSTIC_SPACE_CHOICES,
    ACOUSTIC_SPACE_CONTRACTS,
    BASE_SECTIONS,
    DIALOGUE_COVERAGE_CHOICES,
    REFERENCE_SECTIONS,
    SYSTEM_PROMPT,
    alignment_instruction,
    build_user_request,
    instrumental_style_signature,
    normalize_audio_policy,
    normalize_audio_section_sentence_limits,
    normalize_dialogue_tags,
    normalize_source_dialogue,
    normalize_first_shot_marker,
    normalize_reference_definitions,
    normalize_unassigned_subjects,
    normalize_shot_timestamps,
    normalize_shot_timeline,
    normalize_section_headers,
    resolve_mode,
    strip_markdown_fence,
    system_prompt_for_mode,
    validate_prompt,
    _official_reference_model,
    _dialogue_authoring_request,
    _explicit_source_fact_errors,
    _source_dialogue_contracts,
    _GRADING_ONLY_PALETTE_PATTERNS,
)
from creative_treatments import CINEMATOGRAPHY_CHOICES


def test_auto_mode_is_conservative():
    assert resolve_mode("auto", "") == "t2va"
    assert resolve_mode("auto", "<Subject 1> comes from <Picture 1>") == "ref2va"
    assert resolve_mode("auto", "", "The person in image 1 holds the object in image 2") == "ref2va"


def test_system_prompt_contains_only_the_resolved_mode_contract():
    base = system_prompt_for_mode("t2va")
    reference = system_prompt_for_mode("ref2va")
    assert "Base-mode output" in base
    assert "Ref2VA output" not in base
    assert "Ref2VA output" in reference
    assert "Base-mode output" not in reference


def test_build_request_carries_duration_source_and_alignment_template():
    request = build_user_request('She says "Hola."', "fl2va", 8.0, "")
    assert "TARGET DURATION: 8.000 seconds" in request
    assert 'She says "Hola."' in request
    assert "Picture 2 (from Shot N)" in request


def test_add_instrumental_carries_the_users_music_direction():
    request = build_user_request(
        "A car crosses a rainy city.", "t2va", 5.0, "", True,
        "auto", "add_instrumental", "audible",
        "Slow muted trumpet, brushed drums, and upright bass; restrained noir mood.",
    )
    assert "USER-SPECIFIED INSTRUMENTAL SCORE (authoritative)" in request
    assert "Slow muted trumpet, brushed drums, and upright bass" in request
    assert "no singing, lyrics, or vocal samples" in request


def test_unused_instrumental_description_is_not_sent_to_the_model():
    request = build_user_request(
        "A car crosses a rainy city.", "t2va", 5.0, "", True,
        "auto", "off", "audible", "Ignore this music description.",
    )
    assert "Ignore this music description" not in request


def test_valid_t2va_contract_and_exact_quoted_content():
    source = 'A baker says "First batch." No music.'
    prompt = """integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium-wide shot frames a baker opening a shop. The baker (S1) says: <d>[English] First batch.</d>

overall_soundscape: Wooden shutters scrape open while trays clink softly.

non_diegetic_music: N/A"""
    report = validate_prompt(prompt, "t2va", 5.0, source)
    assert report["valid"], report
    assert tuple(report["sections"]) == BASE_SECTIONS


def test_grading_only_palette_rejects_invented_colored_lighting_and_accepts_grade_language():
    cinematography = json.dumps({"schemaVersion": 1, "colorPalette": "neon_cyan_magenta"})
    invented = """integrated_multimodal_description: [Shot 1] A mechanic walks through a neutral workshop under saturated glow and cyan-magenta colored lighting.

overall_soundscape: Footsteps cross the concrete floor.

non_diegetic_music: N/A"""
    report = validate_prompt(
        invented, "t2va", 5.0, "A mechanic walks through a neutral workshop.",
        cinematography_json=cinematography,
    )
    assert not report["valid"]
    assert any("grading-only presentation control" in error for error in report["errors"])

    graded = invented.replace(
        "under saturated glow and cyan-magenta colored lighting",
        "with cyan-magenta channel separation as a stable image color treatment under the existing neutral illumination",
    )
    assert validate_prompt(
        graded, "t2va", 5.0, "A mechanic walks through a neutral workshop.",
        cinematography_json=cinematography,
    )["valid"]


def test_grading_palette_allows_colored_light_explicitly_present_in_source():
    cinematography = json.dumps({"schemaVersion": 1, "colorPalette": "cold_steel_blue"})
    prompt = """integrated_multimodal_description: [Shot 1] An astronaut walks beneath the existing cyan lighting in a spacecraft corridor.

overall_soundscape: Ventilation and footsteps remain audible.

non_diegetic_music: N/A"""
    report = validate_prompt(
        prompt, "t2va", 5.0, "An astronaut walks beneath cyan lighting in a spacecraft corridor.",
        cinematography_json=cinematography,
    )
    assert report["valid"], report


_GRADING_ONLY_SOURCE = "A mechanic walks through a neutral workshop."
_GRADING_ONLY_TEMPLATE = """integrated_multimodal_description: [Shot 1] A mechanic walks through a neutral workshop {body}.

overall_soundscape: Footsteps cross the concrete floor.

non_diegetic_music: N/A"""


def _grading_only_errors(palette, body, source=_GRADING_ONLY_SOURCE):
    report = validate_prompt(
        _GRADING_ONLY_TEMPLATE.format(body=body), "t2va", 5.0, source,
        cinematography_json=json.dumps({"schemaVersion": 1, "colorPalette": palette}),
    )
    return [error for error in report["errors"] if "grading-only presentation control" in error]


@pytest.mark.parametrize(
    ("palette", "invented", "legitimate"),
    (
        (
            "two_color_process",
            "under red-orange lighting thrown by a practical lamp",
            "with no red-orange lighting added, holding the constrained two-color reproduction as an image treatment",
        ),
        (
            "bleach_bypass",
            "under a blue glow spilling across the floor",
            "without any blue glow, keeping reduced chroma and dense metallic tones as a grade",
        ),
        (
            "teal_orange",
            "beneath teal lighting and orange lamps",
            "with no teal lighting invented, keeping complementary separation as a grade",
        ),
        (
            "cross_processed",
            "as light leaks streak the frame",
            "without light leaks, keeping the shadow-to-highlight hue crossover as a stable grade",
        ),
        (
            "sepia",
            "as a sepia glow rises from unseen lamps",
            "with no amber lighting added, keeping the warm monochrome separation as a grade",
        ),
        (
            "classic_western_earth_sky",
            "bathed in golden-hour light",
            "without golden-hour light, keeping ochre, sienna and umber material relationships as a grade",
        ),
        (
            "revisionist_western_earth",
            "under a dirty yellow glow from a swinging bulb",
            "with no yellow cast, keeping tobacco, umber and stone-gray relationships as a grade",
        ),
        (
            "telenovela_broadcast_color",
            "beside neon signs and orange lighting",
            "without neon signs or orange lighting, keeping luminous protected skin and open midtones as a grade",
        ),
        (
            "soft_pastel",
            "under a pink glow spilling from a tube overhead",
            "with no pink glow added, keeping the lifted low end and gentle candy tints as a grade",
        ),
        (
            "day_for_night",
            "beneath blue lighting and a full moon over the roofline",
            "with no blue lighting or moon invented, keeping the pulled-down exposure reading as night",
        ),
        (
            "infrared_aerochrome",
            "under magenta lighting thrown across the wall",
            "without magenta lighting, keeping foliage red-to-magenta as a false-color grade",
        ),
    ),
)
def test_stylized_grading_palettes_reject_invented_illumination_and_accept_grade_language(
    palette, invented, legitimate,
):
    violations = _grading_only_errors(palette, invented)
    assert violations
    assert all(f"colorPalette={palette}" in error for error in violations)
    assert not _grading_only_errors(palette, legitimate)


@pytest.mark.parametrize("palette", ("natural", "warm", "cool", "restrained", "vibrant", "monochrome"))
def test_neutral_palettes_carry_no_grading_only_guard(palette):
    # These authorize an overall colour bias, so guarding "warm light" style wording
    # would reject legitimate description of the source's own illumination.
    assert palette not in _GRADING_ONLY_PALETTE_PATTERNS
    assert not _grading_only_errors(palette, "under warm amber lighting and a cool blue glow")


def test_grading_only_guards_only_reference_catalogued_palettes():
    assert set(_GRADING_ONLY_PALETTE_PATTERNS) <= set(CINEMATOGRAPHY_CHOICES["color_palette"])


@pytest.mark.parametrize(
    ("palette", "body"),
    (
        # "cast", "wash" and "filter" name the colour grade the palette already authorizes,
        # so they must never be read as invented diegetic light.
        ("sepia", "while a sepia cast holds the whole frame"),
        ("sepia", "while an ochre wash settles over the walls"),
        ("bleach_bypass", "while a silver wash sits on the metalwork"),
        ("cross_processed", "while a green cast settles into the shadows"),
        ("classic_western_earth_sky", "while an ochre wash covers the rock face"),
        ("revisionist_western_earth", "in olive wash coveralls"),
        ("teal_orange", "along an orange-washed corridor"),
        # A traffic signal is a diegetic object, not a grade the palette invented.
        ("telenovela_broadcast_color", "as the traffic signal turns green"),
        # The new grading palettes name their own hues; only a claimed light source is
        # an invented practical, so grade vocabulary and material colour stay legal.
        ("soft_pastel", "while a pastel wash settles over the walls"),
        ("soft_pastel", "in a pink overall he keeps buttoned"),
        ("day_for_night", "while the daylight shadows read as moonlight in the grade"),
        ("day_for_night", "under a deep blue cast that holds the whole frame"),
        ("infrared_aerochrome", "as the foliage outside renders red and magenta"),
        ("infrared_aerochrome", "while a red cast settles into the leaves"),
    ),
)
def test_grading_only_guards_accept_grade_vocabulary_and_ordinary_objects(palette, body):
    assert not _grading_only_errors(palette, body)


def test_teal_orange_guard_allows_colored_light_supplied_by_the_source():
    source = "A mechanic walks through a neutral workshop lit by an orange lamp."
    assert not _grading_only_errors(
        "teal_orange", "under that orange lamp while cooler environmental tones stay separated", source,
    )


def test_selected_creative_profile_id_must_not_leak_into_final_prompt():
    treatment = json.dumps({"schemaVersion": 1, "visualLanguage": "anime_ultradetailed_cinematic"})
    leaked = """integrated_multimodal_description: [Shot 1] The scene uses visual_language:anime_ultradetailed_cinematic style as a woman walks across a room.

overall_soundscape: Footsteps cross the floor.

non_diegetic_music: N/A"""
    report = validate_prompt(
        leaked, "t2va", 5.0, "A woman walks across a room.",
        creative_treatment_json=treatment,
    )
    assert not report["valid"]
    assert any("internal creative profile identifier" in error for error in report["errors"])

    translated = leaked.replace(
        "visual_language:anime_ultradetailed_cinematic style",
        "high-precision hand-drawn cinematic anime with stable cel shading and richly painted depth",
    )
    assert validate_prompt(
        translated, "t2va", 5.0, "A woman walks across a room.",
        creative_treatment_json=treatment,
    )["valid"]


def test_retro_family_gag_profile_requires_round_heads_and_large_simple_eyes_not_print_art():
    treatment = json.dumps({"schemaVersion": 1, "visualLanguage": "anime_retro_gag_family"})
    base = """integrated_multimodal_description: [Shot 1] An adult worker with {design} walks across an office.

overall_soundscape: Footsteps cross the floor.

non_diegetic_music: N/A"""
    vague = validate_prompt(
        base.format(design="a compact rounded silhouette"), "t2va", 5.0,
        "An adult worker walks across an office.", creative_treatment_json=treatment,
    )
    assert not vague["valid"]
    assert any("defining character design" in error for error in vague["errors"])

    print_like = validate_prompt(
        base.format(design="a circular head, rounded cheeks, large simple oval eyes, and woodblock-print texture"),
        "t2va", 5.0, "An adult worker walks across an office.", creative_treatment_json=treatment,
    )
    assert not print_like["valid"]
    assert any("must not be rendered as Japanese print art" in error for error in print_like["errors"])

    correct = validate_prompt(
        base.format(design="a circular head, rounded cheeks, large simple oval eyes with small pupils, and crisp cel fills"),
        "t2va", 5.0, "An adult worker walks across an office.", creative_treatment_json=treatment,
    )
    assert correct["valid"], correct


def test_fl2va_alignment_uses_actual_last_shot_number():
    first = alignment_instruction("fl2va", 8.0, 2)
    prompt = f"""{first}

integrated_multimodal_description: [Shot 1] A cyclist begins from Picture 1. [Shot 2] At 00:04.000, the shot cuts to the cyclist settling into Picture 2.

overall_soundscape: Rain falls and the bicycle chain turns.

non_diegetic_music: N/A"""
    assert validate_prompt(prompt, "fl2va", 8.0)["valid"]
    wrong = prompt.replace("Shot 2) aligns", "Shot 1) aligns", 1)
    assert not validate_prompt(wrong, "fl2va", 8.0)["valid"]


def test_ref2va_six_section_contract_tracks_all_labels():
    detail = " ".join(["The camera observes <Subject 1> beside <Picture 1>."] * 50)
    prompt = f"""subject_definitions:
<Subject 1> is the armored pilot in <Picture 1>.

summary:
[reference generation] The target video follows <Subject 1>.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - the armor is retained.

detailed_description:
The target video uses a live-action cinematic style with low-key lighting.
[Shot 1] {detail}

overall_soundscape:
Low room tone and synchronized armor movement continue throughout.

non_diegetic_music:
N/A"""
    report = validate_prompt(
        prompt, "ref2va", 5.0, reference_context="<Subject 1> comes from <Picture 1>",
    )
    assert report["valid"], report
    assert tuple(report["sections"]) == REFERENCE_SECTIONS


def test_ref2va_can_exceed_500_words_without_a_false_range_warning():
    detail = " ".join([
        "The camera observes <Subject 1> beside <Picture 1> as the existing armor settles into its final position."
    ] * 70)
    prompt = f"""subject_definitions:
<Subject 1> is the armored pilot in <Picture 1>.

summary:
[reference generation] The target video follows <Subject 1>.

retention_analysis:
<Subject 1>: fully_preserved - retain the pilot identity and armor from <Picture 1>.

detailed_description:
The target uses a live-action cinematic style with low-key lighting.
[Shot 1] {detail}

overall_soundscape:
Low room tone and synchronized armor movement continue throughout.

non_diegetic_music:
N/A"""
    report = validate_prompt(
        prompt, "ref2va", 5.0, reference_context="<Subject 1> comes from <Picture 1>",
        enhance_description=True,
    )
    assert report["valid"], report
    assert report["descriptionBudget"]["actualWords"] > 500
    assert not any("350-500" in warning for warning in report["warnings"])


def test_invalid_cut_time_and_unbalanced_dialogue_are_reported():
    prompt = """integrated_multimodal_description: [Shot 1] A room. [Shot 2] At 00:06.000, a speaker (S1) says <d>[English] Hello.
overall_soundscape: Room tone.
non_diegetic_music: N/A"""
    report = validate_prompt(prompt, "t2va", 5.0)
    assert not report["valid"]
    assert any("duration" in item for item in report["errors"])
    assert any("unbalanced" in item for item in report["errors"])


def test_markdown_fence_is_removed_only_when_it_wraps_whole_answer():
    assert strip_markdown_fence("```text\nhello\n```") == "hello"
    assert strip_markdown_fence("prefix ```text\nhello\n```") != "hello"


def test_normalize_section_headers_adds_only_missing_colons():
    raw = "integrated_multimodal_description\n[Shot 1] A room.\noverall_soundscape:\nRoom tone.\nnon_diegetic_music\nN/A"
    fixed = normalize_section_headers(raw)
    assert fixed.startswith("integrated_multimodal_description:")
    assert "overall_soundscape:" in fixed
    assert "non_diegetic_music:\nN/A" in fixed


def test_spoken_source_quote_requires_dialogue_tags():
    prompt = """integrated_multimodal_description: [Shot 1] A detective says: \"Everything is under control.\"

overall_soundscape: Room tone.

non_diegetic_music: N/A"""
    report = validate_prompt(prompt, "t2va", 5.0, 'A detective says "Everything is under control."')
    assert not report["valid"]
    assert any("<d>" in item for item in report["errors"])


def test_missing_dialogue_language_marker_gets_non_translating_fallback():
    assert normalize_dialogue_tags("<d>Hola.</d>") == "<d>[Original language] Hola.</d>"
    assert normalize_dialogue_tags("<d>[Spanish] Hola.</d>") == "<d>[Spanish] Hola.</d>"
    assert normalize_dialogue_tags("<d>[Spanish]Hola.</d>") == "<d>[Spanish] Hola.</d>"


def test_explicit_dialogue_authoring_request_gets_a_concrete_spanish_contract():
    source = (
        "An arabic influencer with her cellphone goes back in time to the Alhambra at Granada during 1492, "
        "and explains in spanish what she sees. She walks around the garden and the fountain, although some "
        "muslim men look at her suspiciously. Generate the dialogue for her based on the scenario."
    )
    request = build_user_request(source, "t2va", 8.0)
    assert "DIALOGUE AUTHORING REQUEST — AUDIBLE" in request
    assert "<d>[Spanish] concrete authored words</d>" in request
    assert "dialogue beats in the shots where the corresponding speech occurs" in request

    literal_request = build_user_request('She explains in Spanish: "Hola."', "t2va", 5.0)
    assert "DIALOGUE AUTHORING REQUEST" not in literal_request
    assert "<d>[Spanish] Hola.</d>" in literal_request


def test_authored_dialogue_is_allowed_only_when_explicitly_requested():
    source = "Write natural Spanish narration for a named off-screen historian describing the Alhambra gardens."
    prompt = """integrated_multimodal_description:
[Shot 1] A named off-screen historian (S1) says in an off-screen voiceover: <d>[Spanish] El agua guía la mirada por todo el jardín.</d>, while the empty garden remains on screen.

overall_soundscape:
Water trickles through the channels while leaves rustle softly.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 5.0, source)
    assert report["valid"], report

    unrequested = validate_prompt(
        prompt, "t2va", 5.0,
        "A silent camera move crosses the empty Alhambra gardens.",
    )
    assert any("Invented or duplicated dialogue" in error for error in unrequested["errors"])

    visible_source = "Generate short Spanish dialogue for a visible presenter, with no narration or voiceover."
    visible_prompt = """integrated_multimodal_description:
[Shot 1] The visible presenter (S1) says warmly: <d>[Spanish] Bienvenidos al jardín.</d>.

overall_soundscape:
Water trickles nearby.

non_diegetic_music:
N/A"""
    visible_report = validate_prompt(visible_prompt, "t2va", 5.0, visible_source)
    assert visible_report["valid"], visible_report


def test_explicit_no_dialogue_does_not_become_a_narration_request():
    source = "A woman silently tours the garden. No dialogue, narration, voiceover, or intelligible speech."
    request = build_user_request(source, "t2va", 5.0)
    assert "DIALOGUE AUTHORING REQUEST" not in request
    prompt = """integrated_multimodal_description:
[Shot 1] A woman silently walks around the garden fountain with her lips closed.

overall_soundscape:
Water trickles and leaves rustle.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 5.0, source)
    assert report["valid"], report


def test_inline_section_content_is_moved_below_its_header():
    fixed = normalize_section_headers(
        "integrated_multimodal_description:\n[Shot 1] Action.\n"
        "overall_soundscape:Gym ambience.\nnon_diegetic_music:N/A"
    )
    assert "overall_soundscape:\nGym ambience." in fixed
    assert "non_diegetic_music:\nN/A" in fixed


def test_catalonian_language_request_becomes_exact_catalan_dialogue_contract():
    source = (
        'A live action Luffy enters a restaurant and asks in catalonian language '
        '"A ver, cabrones, quiero flaó de ese".'
    )
    request = build_user_request(source, "t2va", 5.0)
    assert "VOICE POLICY — AUDIBLE" in request
    assert '<d>[Catalan] A ver, cabrones, quiero flaó de ese</d>' in request


def test_missing_spoken_quote_is_restored_inside_language_tag():
    source = (
        'A live action Luffy enters a restaurant and asks in catalonian language '
        '"A ver, cabrones, quiero flaó de ese".'
    )
    generated = """integrated_multimodal_description:
[Shot 1] Live-action, Luffy enters a restaurant in Ibiza with an arrogant expression.

overall_soundscape:
Restaurant chatter and clinking dishes.

non_diegetic_music:
N/A"""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert '<d>[Catalan] A ver, cabrones, quiero flaó de ese</d>' in repaired
    report = validate_prompt(repaired, "t2va", 5.0, source)
    assert not any("dialogue" in error.lower() or "quoted" in error.lower() for error in report["errors"])


def test_quoted_thought_becomes_exact_spanish_internal_monologue():
    source = (
        'Detective Conan with his hand on his chin, thinking concentrated '
        '"Quién debe ser el asesino?", while a murder happens behind him.'
    )
    request = build_user_request(source, "t2va", 5.0)
    assert "VOICE POLICY — AUDIBLE" in request
    assert '<d>[Spanish] Quién debe ser el asesino?</d>' in request

    generated = """integrated_multimodal_description:
[Shot 1] Detective Conan thinks intensely while a murder occurs behind him.

overall_soundscape:
Muffled sounds of struggle fill the room.

non_diegetic_music:
Slow noir jazz."""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert "says in an off-screen voiceover, as a concentrated internal monologue" in repaired
    assert '<d>[Spanish] Quién debe ser el asesino?</d>' in repaired
    assert "lips remain completely closed" in repaired
    report = validate_prompt(repaired, "t2va", 5.0, source)
    assert not any("dialogue" in error.lower() or "quoted" in error.lower() for error in report["errors"])
    assert not any("invented voiceover" in error.lower() for error in report["errors"])


def test_internal_monologue_restoration_removes_duplicate_placeholder_speech():
    source = (
        'Detective Conan with his hand on his chin, thinking concentrated '
        '"Quién debe ser el asesino?", while a murder happens behind him.'
    )
    generated = """integrated_multimodal_description:
[Shot 1] Conan studies the scene. At 2.0 seconds, Conan speaks while maintaining intense focus on the unseen killer. [Shot 2] At 00:01.667, The camera remains focused on Conan as he delivers his line, but the background remains visible. A cut returns to the detective's internal monologue.

overall_soundscape:
Muffled struggle.

non_diegetic_music:
Slow noir jazz."""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert repaired.count("<d>") == 1
    assert repaired.count("Quién debe ser el asesino?") == 1
    assert repaired.count("off-screen voiceover") == 1
    assert "Conan speaks" not in repaired
    assert "delivers his line" not in repaired
    assert "detective's internal monologue" not in repaired


def test_existing_tagged_internal_monologue_also_removes_extra_speech_cue():
    source = 'Conan thinks "Quién debe ser el asesino?".'
    generated = """integrated_multimodal_description:
[Shot 1] Conan speaks while maintaining intense focus. Conan (S1) says in an off-screen internal monologue: <d>[Spanish] Quién debe ser el asesino?</d>, while his lips remain closed.

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert repaired.count("<d>") == 1
    assert repaired.count("off-screen voiceover") == 1
    assert "Conan speaks" not in repaired


def test_audible_dialogue_adds_speaker_id_and_closes_the_vocal_envelope():
    source = 'La mujer dice "tranquilo, no estás solo" y señala hacia los portales.'
    generated = """subject_definitions:
<Subject 1> is the person from <Picture 1>.

summary:
[reference generation] A laboratory reveal.

retention_analysis:
<Subject 1>: fully_preserved - preserve the person.

detailed_description:
[Shot 1] An elderly woman delivers the line: <d>[Spanish] tranquilo, no estás solo</d>. She points toward three figures emerging from portals.

overall_soundscape:
Machinery hums and the portals crackle.

non_diegetic_music:
N/A"""
    repaired = normalize_source_dialogue(generated, source, "ref2va")
    assert "elderly woman (S1) delivers the line:" in repaired
    assert repaired.count("After the final tagged line, no character speaks any additional words.") == 1
    assert "every character keeps their mouth closed" not in repaired
    assert "The tagged line is the only intelligible speech" in repaired
    assert repaired.count("<d>[Spanish] tranquilo, no estás solo</d>") == 1


def test_post_dialogue_reference_aliases_cannot_become_accidental_narration():
    source = 'La mujer dice "tranquilo, no estás solo" y aparecen las versiones de imagen 1, imagen 2 e imagen 3.'
    generated = """subject_definitions:
<Subject 1> is the person from <Picture 1>.
<Subject 2> is a military alternate from <Picture 2>.
<Subject 3> is a beret-wearing alternate from <Picture 3>.

summary:
[reference generation] A portal reveal.

retention_analysis:
<Subject 1>: fully_preserved - preserve the person.
<Subject 2>: fully_preserved - preserve the military alternate.
<Subject 3>: fully_preserved - preserve the beret-wearing alternate.

detailed_description:
[Shot 1] As the camera moves, the elderly woman speaks calmly: <d>[Spanish] tranquilo, no estás solo</d>. First <Subject 2>, the Nazi army version, appears. Then <Subject 3>, the version wearing a beret, emerges. The figures remain still.

overall_soundscape:
The portal crackles.

non_diegetic_music:
N/A"""
    repaired = normalize_source_dialogue(generated, source, "ref2va")
    detail = repaired.split("detailed_description:", 1)[1].split("overall_soundscape:", 1)[0]
    assert "woman (S1) speaks calmly:" in detail
    assert "Nazi army version" not in detail
    assert "version wearing a beret" not in detail
    assert "First <Subject 2> appears" in detail
    assert "Then <Subject 3> emerges" in detail


def test_long_post_dialogue_timeline_does_not_force_new_nonverbal_sources_in_auto_mode():
    source = 'La mujer dice "tranquilo, no estás solo" y después aparecen lentamente tres portales.'
    visual_tail = " ".join(["Three figures gradually emerge while the camera pans deeper into the chamber."] * 8)
    prompt = f"""integrated_multimodal_description:
[Shot 1] The elderly woman with a calm feminine voice (S1) says: <d>[Spanish] tranquilo, no estás solo</d>. She closes her lips. {visual_tail}

overall_soundscape:
Laboratory ambience continues.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 15.0, source)
    assert report["valid"], report
    assert not any("non-verbal sound" in item for item in report["errors"])

    occupied = prompt.replace(
        "She closes her lips.",
        "She closes her lips. A machinery hum and electrical crackles occupy the entire remaining timeline.",
    )
    report = validate_prompt(occupied, "t2va", 15.0, source)
    assert report["valid"], report


def test_unrelated_in_phrase_is_not_misread_as_language():
    source = 'A detective with his hand in his pocket says "Proceed."'
    request = build_user_request(source, "t2va", 5.0)
    assert '<d>[Original language] Proceed.</d>' in request
    assert "[His]" not in request


def test_description_enhancement_toggle_changes_direction_not_source_contract():
    source = 'A detective enters and says "Do not move."'
    enhanced = build_user_request(source, "t2va", 5.0, enhance_description=True)
    conservative = build_user_request(source, "t2va", 5.0, enhance_description=False)
    assert "ACTIVE DIRECTORIAL ENHANCEMENT" in enhanced
    assert "meaningful change of viewpoint" in enhanced
    assert "Give important actions a causal envelope" in enhanced
    assert "BASE DESCRIPTION DEPTH — USEFUL DENSITY, NO WORD-COUNT TARGET" in enhanced
    assert "do not force it to 350-500 words" in enhanced
    assert "CONSERVATIVE FORMAT ADAPTATION" in conservative
    assert "DESCRIPTION DEPTH" not in conservative
    assert '<d>[Original language] Do not move.</d>' in enhanced
    assert '<d>[Original language] Do not move.</d>' in conservative


@pytest.mark.parametrize("mode", ["t2va", "i2va", "fl2va", "l2va", "ref2va", "chained_multishot"])
def test_enhancement_translates_only_source_authorized_emotion_into_observable_acting(mode):
    kwargs = {"multishot_shot_count": 1} if mode == "chained_multishot" else {}
    source = 'She tries not to cry while saying "I am fine."'
    enhanced = build_user_request(source, mode, 5.0, enhance_description=True, **kwargs)
    conservative = build_user_request(source, mode, 5.0, enhance_description=False, **kwargs)
    heading = "EMOTIONAL PERFORMANCE TRANSLATION — SOURCE-GATED"
    assert enhanced.count(heading) == 1
    assert heading not in conservative
    assert "smallest sufficient sequence of observable acting" in enhanced
    assert "partial, asymmetric, overlapping, or conflicting reactions" in enhanced
    assert "only when the source explicitly implies hesitation" in enhanced
    assert "Never add a cut, push-in, close-up, camera move, or lighting change" in enhanced
    assert "Avoid millimeter or centimeter measurements" in enhanced
    assert "preserve every word and its assigned timing" in enhanced
    assert '<d>[Original language] I am fine.</d>' in enhanced


def test_emotional_performance_contract_does_not_authorize_incomplete_ordinary_actions():
    request = build_user_request(
        "She shakes her head and then opens the door.", "t2va", 5.0, enhance_description=True,
    )
    assert "Otherwise complete every requested action and preserve its resulting state" in request
    assert "do not manufacture contradiction merely to make acting look complex" in request


def test_dialogue_normalization_canonicalizes_temporal_speaking_cues_without_new_words():
    source = 'A woman says "I am fine."'
    generated = """integrated_multimodal_description:
[Shot 1] Before speaking, she holds her breath. She (S1) says <d>[English] I am fine.</d>. Several seconds after speaking, her jaw relaxes.

overall_soundscape:
The tagged line and one breath are audible.

non_diegetic_music:
N/A"""
    fixed = normalize_source_dialogue(generated, source, "t2va")
    assert "before the tagged line" in fixed.casefold()
    assert "after the tagged line" in fixed.casefold()
    assert "before speaking" not in fixed.casefold()
    assert "after speaking" not in fixed.casefold()


def test_ref2va_enhancement_targets_detailed_description_without_padding():
    request = build_user_request(
        "The mechanic in image 1 opens the workshop door.",
        "ref2va",
        6.0,
        "Picture 1 supplies the mechanic's identity.",
        enhance_description=True,
    )
    assert "REF2VA ADAPTIVE DESCRIPTION BUDGET" in request
    assert "350-500 English words" in request
    assert "soft target, never a ceiling" in request
    assert "Video editing scales with source complexity and has no word target" in request
    assert "Do not count subject_definitions" in request
    assert "Never pad with synonyms" in request
    assert "BASE DESCRIPTION DEPTH" not in request


def test_chained_description_enhancement_toggle_controls_segment_depth():
    source = "A mechanic walks to a car, opens the driver's door, and sits down."
    enhanced = build_user_request(
        source, "chained_multishot", 8.0, enhance_description=True, multishot_shot_count=2,
    )
    conservative = build_user_request(
        source, "chained_multishot", 8.0, enhance_description=False, multishot_shot_count=2,
    )
    assert "ACTIVE DIRECTORIAL ENHANCEMENT — AUTONOMOUS SEGMENTS" in enhanced
    assert "subject appearance and frame position" in enhanced
    assert "observable state changes" in enhanced
    assert "CONSERVATIVE FORMAT ADAPTATION — AUTONOMOUS SEGMENTS" not in enhanced
    assert "CONSERVATIVE FORMAT ADAPTATION — AUTONOMOUS SEGMENTS" in conservative
    assert "Preserve the source's level of specificity" in conservative
    assert "ACTIVE DIRECTORIAL ENHANCEMENT — AUTONOMOUS SEGMENTS" not in conservative
    assert 'OUTPUT EXACTLY 2 PROMPT ITEMS.' in enhanced
    assert 'OUTPUT EXACTLY 2 PROMPT ITEMS.' in conservative


def test_chained_receives_reference_and_independent_audio_voice_policies():
    request = build_user_request(
        'The woman in image 1 says in Spanish "Hola." while opening a door.',
        "chained_multishot",
        6.0,
        reference_context="Picture 1 supplies the woman's identity.",
        ambience_foley_policy="off",
        background_score_policy="add_instrumental",
        voice_performance="none",
        instrumental_description="Low strings, 80 BPM, sparse pulse, gradual crescendo.",
        multishot_shot_count=2,
    )
    assert "REFERENCE CONTEXT (authoritative labels and roles)" in request
    assert "Picture 1 supplies the woman's identity." in request
    assert "<Picture 1>" in request
    assert "AMBIENCE AND FOLEY POLICY — OFF" in request
    assert "NON-DIEGETIC MUSIC POLICY — REQUIRED" in request
    assert "USER-SPECIFIED INSTRUMENTAL SCORE" in request
    assert "VOICE POLICY — NONE" in request
    assert "MULTISHOT DIALOGUE LEDGER" not in request
    assert "synchronized physical sound" not in request


def test_chained_voice_none_accepts_omitted_source_dialogue_and_rejects_leakage():
    source = 'A woman says in Spanish "Hola." and then closes the door.'
    silent_output = json.dumps({"prompts": ["The woman silently closes the door."]})
    silent_report = validate_prompt(
        silent_output, "chained_multishot", 6.0, source, voice_performance="none",
        multishot_shot_count=1,
    )
    assert silent_report["valid"], silent_report

    leaked_output = json.dumps({"prompts": ["The woman says <d>[Spanish] Hola.</d> and closes the door."]})
    leaked_report = validate_prompt(
        leaked_output, "chained_multishot", 6.0, source, voice_performance="none",
        multishot_shot_count=1,
    )
    assert not leaked_report["valid"]
    assert any("invented or duplicated spoken dialogue" in error for error in leaked_report["errors"])


def test_enhancement_respects_static_camera_audio_off_and_required_score():
    cinematography = json.dumps({
        "schemaVersion": 1,
        "cameraMotion": "static",
    })
    request = build_user_request(
        "A woman studies a map.", "t2va", 5.0,
        enhance_description=True,
        ambience_foley_policy="off",
        background_score_policy="add_instrumental",
        cinematography_json=cinematography,
    )
    assert "The camera holds a locked static frame on the existing composition" in request
    assert "AMBIENCE AND FOLEY POLICY — OFF" in request
    assert "NON-DIEGETIC MUSIC POLICY — REQUIRED" in request
    assert "physical sound only as permitted" in request
    assert "musical treatment is governed exclusively" in request
    assert "If the user did not request music" not in request


def test_instrumental_style_adapts_user_direction_only_when_score_is_enabled():
    active = build_user_request(
        "A woman crosses an empty station.", "t2va", 5.0,
        background_score_policy="add_instrumental",
        instrumental_description="Cello, 72 BPM, a gradual crescendo in the final two seconds.",
        instrumental_style="jazz",
    )
    inactive = build_user_request(
        "A woman crosses an empty station.", "t2va", 5.0,
        background_score_policy="off",
        instrumental_description="Cello, 72 BPM.",
        instrumental_style="jazz",
    )
    assert "INSTRUMENTAL MUSIC GENRE / STYLE" in active
    assert "Selected style: jazz" not in active
    assert "HARMONY AND TONALITY:" in active
    assert instrumental_style_signature("jazz") in active
    assert "jazz-informed harmony" in active
    assert "Cello, 72 BPM" in active
    assert "adapt its arrangement to the selected instrumental style" in active
    assert "singing, lyrics, speech, chants, choir, or vocal samples" in active
    assert "write the resolved instrumentation, tempo, rhythm, harmony" in active
    assert "Do not output only the genre name" in active
    assert "INSTRUMENTAL MUSIC GENRE / STYLE" not in inactive
    assert "Cello, 72 BPM" not in inactive


def test_every_instrumental_style_has_a_concrete_non_vocal_contract():
    from prompt_guides import INSTRUMENTAL_STYLE_CHOICES

    for style in INSTRUMENTAL_STYLE_CHOICES[1:]:
        request = build_user_request(
            "A figure walks through fog.", "t2va", 5.0,
            background_score_policy="add_instrumental",
            instrumental_style=style,
        )
        assert f"Selected style: {style}" not in request
        assert "VOICE AND FOLEY RELATION:" in request
        assert instrumental_style_signature(style) in request
        assert "strictly instrumental" in request


def test_unknown_instrumental_style_is_rejected():
    with pytest.raises(ValueError, match="Unsupported instrumental style"):
        build_user_request(
            "A figure walks.", "t2va", 5.0,
            background_score_policy="add_instrumental",
            instrumental_style="pirate_polkas",
        )


def test_explicit_aspect_ratio_adds_composition_contract_but_auto_does_not():
    explicit = build_user_request("Two dancers cross paths.", "t2va", 5.0, aspect_ratio="9:16")
    automatic = build_user_request("Two dancers cross paths.", "t2va", 5.0, aspect_ratio="auto")
    assert "AUTHORITATIVE COMPOSITION FRAME — 9:16" in explicit
    assert "contact points, movement paths, and visible text" in explicit
    assert "Do not invent letterboxing" in explicit
    assert "AUTHORITATIVE COMPOSITION FRAME" not in automatic


def test_audio_policy_contracts_are_independent():
    request = build_user_request(
        'A presenter says "Hello there."', "t2va", 5.0, "", True,
        "ensure_audible", "add_instrumental", "silent_mouth_acting_experimental",
    )
    assert "AMBIENCE AND FOLEY POLICY — REQUIRED" in request
    assert "NON-DIEGETIC MUSIC POLICY — REQUIRED" in request
    assert "VOICE POLICY — SILENT MOUTH ACTING" in request
    assert "approximately 2 words" in request
    assert "<d>[" not in request


def test_silent_mouth_acting_removes_lexical_dialogue_and_speaker_ids():
    source = 'A presenter says in Spanish "Hola amigo."'
    generated = """integrated_multimodal_description:
[Shot 1] The presenter (S1) says <d>[Spanish] Hola amigo.</d> while smiling.

overall_soundscape:
The presenter's audible voice carries over room tone.

non_diegetic_music:
Soft piano."""
    silent = normalize_source_dialogue(
        generated, source, "t2va", "silent_mouth_acting_experimental",
    )
    silent = normalize_audio_policy(silent, "off", "off", "silent_mouth_acting_experimental")
    assert "<d>" not in silent
    assert "Hola amigo" not in silent
    assert "(S1)" not in silent
    assert "silently performs natural speech-like lip and jaw articulation" in silent
    assert "overall_soundscape:\nN/A" in silent
    assert "non_diegetic_music:\nN/A" in silent
    report = validate_prompt(
        silent, "t2va", 5.0, source, "", "off", "off",
        "silent_mouth_acting_experimental",
    )
    assert report["valid"], report
    assert any("experimental" in item.lower() for item in report["warnings"])


def test_voice_none_removes_speech_and_mouth_performance():
    source = 'A presenter says "Hello."'
    generated = """integrated_multimodal_description:
[Shot 1] The presenter says <d>[English] Hello.</d>.

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    quiet = normalize_source_dialogue(generated, source, "t2va", "none")
    assert "Hello" not in quiet
    assert "<d>" not in quiet
    assert "speech-like mouth performance" in quiet
    assert "silently performs" not in quiet


def test_forced_instrumental_and_ambience_policies_are_validated():
    prompt = """integrated_multimodal_description:
[Shot 1] A quiet empty room.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""
    report = validate_prompt(
        prompt, "t2va", 5.0, "", "", "ensure_audible", "add_instrumental", "audible",
    )
    assert any("instrumental" in item for item in report["errors"])


def test_short_simultaneous_prompt_gets_one_shot_and_visibility_contract():
    source = 'Conan thinks "Quién debe ser el asesino?" while an attack happens behind him.'
    request = build_user_request(source, "t2va", 5.0, enhance_description=True)
    assert "SHOT PLAN: Exactly one continuous shot" in request
    assert "SIMULTANEITY LOCK" in request
    assert "do not invent dialogue or music" in request


def test_duplicate_exact_dialogue_is_reduced_to_one_block():
    source = 'Conan thinks "Quién debe ser el asesino?".'
    generated = """integrated_multimodal_description:
[Shot 1] Conan (S1) says in an off-screen voiceover, as a concentrated internal monologue: <d>[Spanish] Quién debe ser el asesino?</d> while his lips remain closed. The same thought repeats: <d>[Spanish] Quién debe ser el asesino?</d>.

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert repaired.count("<d>") == 1
    assert repaired.count("Quién debe ser el asesino?") == 1


def test_repeated_heard_line_and_cut_scene_commands_remain_distinct_beats():
    source = (
        'After two repetitions, a godlike voice is heard saying "power up!" in English. '
        'Cut scene to a close-up. After two more repetitions we hear the "power up!" again. '
        'He does more repetitions and we hear the "power up!" again. Then cut scene, and his face transforms.'
    )
    contracts = _source_dialogue_contracts(source)
    assert contracts == [
        ("English", "power up!", False),
        ("English", "power up!", False),
        ("English", "power up!", False),
    ]

    request = build_user_request(source, "t2va", 15.0)
    assert "DIALOGUE AUTHORING REQUEST" not in request
    assert "EXPLICIT EDIT PLAN: Use exactly 3 shots" in request
    assert "Occurrence 1 of 3" in request
    assert "Occurrence 2 of 3" in request
    assert "Occurrence 3 of 3" in request
    assert "state ladder" in request
    assert "Shot 1 authoritative source span" in request
    assert "Shot 2 authoritative source span" in request
    assert "Shot 3 authoritative source span" in request


def test_repeated_source_dialogue_keeps_expected_count_but_removes_true_extra_copy():
    source = (
        'A voice says "power up!" in English. We hear "power up!" again. '
        'We hear "power up!" again.'
    )
    blocks = " ".join(
        "A divine voice (S1) booms: <d>[English] power up!</d>." for _ in range(4)
    )
    generated = f"""integrated_multimodal_description:
[Shot 1] {blocks}
overall_soundscape:
Echo and gym ambience.
non_diegetic_music:
N/A"""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert repaired.count("<d>[English] power up!</d>") == 3
    assert repaired.count("After the final tagged line") == 1


def test_validator_rejects_collapsing_explicit_cut_scene_commands_into_one_shot():
    source = "He lifts. Cut scene to a close-up. He lifts again. Then cut scene, his face transforms."
    prompt = """integrated_multimodal_description:
[Shot 1] He lifts, the camera moves closer, then his face transforms.
overall_soundscape:
Gym ambience.
non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 15.0, source)
    assert any("requires exactly 3 shots" in item for item in report["errors"])


def test_repeated_dialogue_cannot_move_across_explicit_cut_boundaries():
    source = (
        'A divine voice says "power up!". Cut scene to a close-up. '
        'We hear "power up!" again and then "power up!" again. Then cut scene, he transforms.'
    )
    prompt = """integrated_multimodal_description:
[Shot 1] A divine voice (S1) booms: <d>[Original language] power up!</d>. The divine voice (S1) booms: <d>[Original language] power up!</d>. The divine voice (S1) booms: <d>[Original language] power up!</d>.
[Shot 2] At 00:05.000, The camera moves close.
[Shot 3] At 00:10.000, He transforms.
overall_soundscape:
Echo, breathing, and transformation sounds.
non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 15.0, source)
    assert any("source-authored shot 1" in item for item in report["errors"])
    assert any("source-authored shot 2" in item for item in report["errors"])


def test_validator_rejects_extra_dialogue_music_inline_times_and_excess_shots():
    source = 'Conan thinks "Quién debe ser el asesino?" while an attack happens behind him.'
    prompt = """integrated_multimodal_description:
[Shot 1] At 2.0 seconds, Conan thinks. Conan (S1) says in an off-screen voiceover, as a concentrated internal monologue: <d>[Spanish] Quién debe ser el asesino?</d> while his lips remain completely closed. [Shot 2] At 00:02.500, the camera cuts closer and a voice says <d>[Spanish] Otra vez.</d>.

overall_soundscape:
Room tone.

non_diegetic_music:
Noir jazz."""
    report = validate_prompt(prompt, "t2va", 5.0, source)
    joined = "\n".join(report["errors"])
    assert "exactly one continuous shot" in joined
    assert "Numeric event times" in joined
    assert "Invented or duplicated dialogue" in joined
    assert "must be N/A" in joined


def test_validator_rejects_clock_form_inline_event_time_in_shot_body():
    source = "A woman tries to remain composed while holding eye contact."
    prompt = """integrated_multimodal_description:
[Shot 1] A woman holds eye contact. At 00:00.500, she takes a controlled breath and remains still.

overall_soundscape:
Quiet room tone and one controlled breath.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 5.0, source)
    assert any("Numeric event times" in item for item in report["errors"])


def test_base_validator_rejects_invented_visible_quoted_text():
    source = "A supplied pilot walks through the hangar and reaches the door."
    prompt = """integrated_multimodal_description:
[Shot 1] The supplied pilot crosses the hangar. A glowing title reads "SKY HEROES" before the pilot reaches the door.

overall_soundscape:
Footsteps in the hangar.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 5.0, source)
    assert any("Visible quoted text was invented" in item for item in report["errors"])


def test_dialogue_in_soundscape_does_not_satisfy_spoken_contract():
    source = 'A detective says "Stop."'
    prompt = """integrated_multimodal_description:
[Shot 1] A detective raises one hand.

overall_soundscape:
The detective says <d>[English] Stop.</d> over room tone.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 5.0, source)
    joined = "\n".join(report["errors"])
    assert "Required spoken dialogue" in joined
    assert "only inside the timeline" in joined


def test_only_timeline_shot_one_is_bracketed():
    raw = "integrated_multimodal_description: Shot 1 opens wide.\noverall_soundscape: Shot 1 reference.\nnon_diegetic_music: N/A"
    fixed = normalize_first_shot_marker(raw, "t2va")
    assert "integrated_multimodal_description: [Shot 1] opens wide." in fixed
    assert "overall_soundscape: Shot 1 reference." in fixed


def test_complete_timestamp_gets_required_comma_without_changing_time():
    assert normalize_shot_timestamps("[Shot 2] At 00:01.500 Medium") == "[Shot 2] At 00:01.500, Medium"
    assert normalize_shot_timestamps("[Shot 2] At 00:01.500, Medium") == "[Shot 2] At 00:01.500, Medium"
    assert normalize_shot_timestamps("At 00:01.500 [Shot 2] Medium") == "[Shot 2] At 00:01.500, Medium"


def test_visible_dialogue_cannot_be_silently_changed_to_voiceover():
    prompt = """integrated_multimodal_description: [Shot 1] A detective says in an off-screen voiceover: <d>[English] Hello.</d> His lips remain closed.

overall_soundscape: Room tone.

non_diegetic_music: N/A"""
    report = validate_prompt(prompt, "t2va", 5.0, 'A detective says "Hello."')
    assert not report["valid"]
    assert any("invented voiceover" in item for item in report["errors"])


def test_plain_image_roles_become_independent_subjects_with_picture_provenance():
    request = build_user_request(
        "The person in image 1 reveals the Uzi in image 2.", "ref2va", 5.0, "",
    )
    assert "<Subject 1> is the reusable person" in request
    assert "come from <Picture 1>" in request
    assert "<Subject 2> is the reusable Uzi" in request
    assert "come from <Picture 2>" in request
    assert "provenance appear inside a Subject definition" in request
    assert "REQUIRED DEFINITION: <Picture 1>" not in request


def test_positional_roles_are_generic_and_not_tied_to_the_regression_example():
    request = build_user_request(
        "The driver in image 1 puts on the yellow racing helmet in image 2 beside the car in image 3.",
        "ref2va", 6.0, "",
    )
    assert "<Subject 1> is the reusable driver" in request
    assert "come from <Picture 1>" in request
    assert "<Subject 2> is the reusable yellow racing helmet" in request
    assert "come from <Picture 2>" in request
    assert "<Subject 3> is the reusable car" in request
    assert "come from <Picture 3>" in request


def test_plain_video_and_audio_ordinals_become_exact_asset_tags():
    request = build_user_request(
        "Continue video 1 while using audio 2 as a timing and voice reference.", "ref2va", 8.0, "",
    )
    assert "<Video 1> is the supplied video used for global edit" in request
    assert "<Audio 2> is the supplied audio signal" in request
    assert "Continue <Video 1> while using <Audio 2>" in request


def test_style_picture_becomes_attribute_transfer_subject_not_picture_definition():
    request = build_user_request(
        "Render a new subject using the style from image 1.", "ref2va", 5.0, "",
    )
    assert "<Subject 1> is the reusable visual style abstracted from <Picture 1>" in request
    assert "<Subject 1>: attribute_transfer" in request
    assert "REQUIRED DEFINITION: <Picture 1>" not in request


def test_exact_first_frame_picture_remains_independent_anchor():
    request = build_user_request(
        "Use image 1 as the exact first frame and continue forward.", "ref2va", 5.0, "",
    )
    assert "REQUIRED DEFINITION: <Picture 1> is the supplied image used as an independent exact first-frame anchor" in request
    assert "<Picture 1>: fully_preserved" in request
    assert "<Subject 1>" not in request


def test_picture_identity_and_video_motion_become_separate_subjects():
    request = build_user_request(
        "Use the motion from video 1 with the subject identity from image 2.", "ref2va", 5.0, "",
    )
    assert "<Subject 1> is the reusable subject identity" in request
    assert "come from <Picture 2>" in request
    assert "<Subject 2> is the reusable body-motion pattern from <Video 1>" in request
    assert "REQUIRED DEFINITION: <Video 1>" not in request


def test_copied_voice_audio_is_independent_signal_with_audio_marker():
    request = build_user_request(
        "Copy the voice from audio 1 as the synchronized presenter voice.", "ref2va", 5.0, "",
    )
    assert "<Audio 1> is the supplied audio signal copied as a synchronized audio layer" in request
    assert "<Audio 1>: partially_copy" in request


def test_ref2va_rejects_invented_assets_and_timeline_picture_definitions():
    detail = " ".join(["The person from <Picture 1> holds the Uzi from <Picture 2>."] * 55)
    prompt = f"""subject_definitions:
<Subject 1> is a salesperson.
<Picture 1> The initial setup showing the salesperson.
<Picture 2> The moment the Uzi appears.
<Picture 3> The final shot.
<Video 1> The whole advertisement.

summary:
[reference generation] A product advertisement.

retention_analysis:
<Picture 1>: fully_preserved. <Picture 2>: fully_preserved.

detailed_description:
[Shot 1] {detail}

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    report = validate_prompt(
        prompt, "ref2va", 5.0,
        "The person in image 1 reveals the Uzi in image 2.", "",
    )
    assert not report["valid"]
    assert any("invented reference labels" in item for item in report["errors"])
    assert any("must have exactly one subject_definitions entry" in item for item in report["errors"])


def test_retention_markers_are_not_mistaken_for_sections_but_are_validated():
    detail = " ".join(["The source person remains visible."] * 70)
    prompt = f"""subject_definitions:
<Subject 1> is a person.

summary:
[generation] A portrait.

retention_analysis:
audio_markers_fully_copy: The generated voice.

detailed_description:
[Shot 1] {detail}

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "ref2va", 5.0)
    assert report["sections"] == list(REFERENCE_SECTIONS)
    assert any("retention_analysis line must begin" in item for item in report["errors"])


def test_object_reference_cannot_appear_before_explicit_spoken_reveal_cue():
    detail = " ".join(["<Subject 1> waits beside the table while <Subject 2> is visibly held up."] * 50)
    detail += " [Shot 2] At 00:02.000, <Subject 1> says <d>[Spanish] como esta?</d>"
    prompt = f"""subject_definitions:
<Subject 1> is the reusable person whose identity comes from <Picture 1>.
<Subject 2> is the reusable Uzi whose exact design comes from <Picture 2>.

summary:
[reference generation] A sales advertisement.

retention_analysis:
<Subject 1>: fully_preserved - identity retained.
<Subject 2>: fully_preserved - design retained.

detailed_description:
[Shot 1] {detail}

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    source = 'The person in image 1 pulls the Uzi in image 2 from under the table cuando dice "como esta?"'
    report = validate_prompt(prompt, "ref2va", 5.0, source)
    assert any("before the user-specified reveal cue" in item for item in report["errors"])


def test_reference_and_reveal_cue_may_share_the_same_shot():
    detail = " ".join(["<Subject 1> waits beside the table while <Subject 2> remains concealed."] * 50)
    detail += " [Shot 2] At 00:02.000, <Subject 1> reveals <Subject 2> as they say <d>[Spanish] como esta?</d>"
    prompt = f"""subject_definitions:
<Subject 1> is the reusable person whose identity comes from <Picture 1>.
<Subject 2> is the reusable Uzi whose exact design comes from <Picture 2>.

summary:
[reference generation] A sales advertisement.

retention_analysis:
<Subject 1>: fully_preserved - identity retained.
<Subject 2>: fully_preserved - design retained.

detailed_description:
[Shot 1] {detail}

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    source = 'The person in image 1 pulls the Uzi in image 2 from under the table cuando dice "como esta?"'
    report = validate_prompt(prompt, "ref2va", 5.0, source)
    assert not any("before the user-specified reveal cue" in item for item in report["errors"])


def test_bound_subject_applies_picture_without_repeating_picture_tag_in_detail():
    detail = " ".join(["<Subject 1> waits behind the counter while facing the camera."] * 55)
    detail += " [Shot 2] At 00:02.000, <Subject 1> reveals <Subject 2> while saying <d>[Spanish] como esta?</d>"
    prompt = f"""subject_definitions:
<Picture 1> is the exact provided source image 1 showing the person.
<Picture 2> is the exact provided source image 2 showing the Uzi.
<Subject 1> is the reusable person shown in <Picture 1>.
<Subject 2> is the reusable Uzi shown in <Picture 2>.

summary:
[reference generation] A sales advertisement.

retention_analysis:
fully_preserved: Both supplied pictures.

detailed_description:
[Shot 1] {detail}

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    source = 'The person in image 1 pulls the Uzi in image 2 from under the table cuando dice "como esta?"'
    report = validate_prompt(prompt, "ref2va", 5.0, source)
    assert not any("must be applied inside detailed_description" in item for item in report["errors"])


def test_plain_object_name_before_later_reveal_is_rejected():
    detail = " ".join(["<Subject 1> holds the Uzi while waiting behind the counter."] * 55)
    detail += " [Shot 2] At 00:02.000, <Subject 1> reveals <Subject 2> while saying <d>[Spanish] como esta?</d>"
    prompt = f"""subject_definitions:
<Picture 1> is the exact provided source image 1 showing the person.
<Picture 2> is the exact provided source image 2 showing the Uzi.
<Subject 1> is the reusable person shown in <Picture 1>.
<Subject 2> is the reusable Uzi shown in <Picture 2>.

summary:
[reference generation] A sales advertisement.

retention_analysis:
fully_preserved: Both supplied pictures.

detailed_description:
[Shot 1] {detail}

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    source = 'The person in image 1 pulls the Uzi in image 2 from under the table cuando dice "como esta?"'
    report = validate_prompt(prompt, "ref2va", 5.0, source)
    assert any("before the user-specified reveal cue" in item for item in report["errors"])


def test_object_name_in_dialogue_does_not_count_as_visual_reveal():
    detail = " ".join(["<Subject 1> waits and says <d>[Spanish] Queréis una uzi...</d>."] * 40)
    detail += " [Shot 2] At 00:02.000, <Subject 1> reveals <Subject 2> from <Picture 2> while saying <d>[Spanish] como esta?</d>"
    prompt = f"""subject_definitions:
<Picture 1> is the exact provided source image 1 showing the person.
<Picture 2> is the exact provided source image 2 showing the Uzi.
<Subject 1> is the reusable person shown in <Picture 1>.
<Subject 2> is the reusable Uzi shown in <Picture 2>.

summary:
[reference generation] A sales advertisement.

retention_analysis:
fully_preserved: Both supplied pictures.

detailed_description:
[Shot 1] {detail}

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    source = 'The person in image 1 asks "Queréis una uzi..." and pulls the Uzi in image 2 cuando dice "como esta?"'
    report = validate_prompt(prompt, "ref2va", 5.0, source)
    assert not any("before the user-specified reveal cue" in item for item in report["errors"])


def test_positional_asset_definitions_are_normalized_to_source_facts():
    raw = """subject_definitions:
<Picture 1> The opening setup.
<Picture 2> The reveal moment.

summary:
..."""
    fixed = normalize_reference_definitions(
        raw, "The person in image 1 reveals the Uzi in image 2.",
    )
    assert "<Picture 1> The opening setup" not in fixed
    assert "<Picture 2> The reveal moment" not in fixed
    assert "<Subject 1> is the reusable person" in fixed
    assert "come from <Picture 1>" in fixed
    assert "<Subject 2> is the reusable Uzi" in fixed
    assert "come from <Picture 2>" in fixed


def test_inferred_reference_normalization_replaces_extra_retention_and_summary_type():
    raw = """subject_definitions:
<Picture 1> A generated opening moment.
<Subject 1> A vague person.

summary:
[Visual Sequence] A presenter reveals an object.

retention_analysis:
<Subject 1>: weak_reference - vague.
fully_preserved: The action.
attribute_transfer: N/A

detailed_description:
[Shot 1] <Subject 1> reveals <Subject 2>.

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    fixed = normalize_reference_definitions(
        raw, "The person in image 1 reveals the product in image 2.",
    )
    assert "summary:\n[reference generation] A presenter reveals an object.\n" in fixed
    assert "<Subject 1> A vague person; its source provenance is <Picture 1>." in fixed
    assert "<Subject 1>: fully_preserved - vague." in fixed
    assert "<Picture 1> A generated opening moment." not in fixed
    assert "fully_preserved: The action." not in fixed
    assert "attribute_transfer: N/A" not in fixed
    assert fixed.count("<Subject 1>: fully_preserved") == 1
    assert fixed.count("<Subject 2>: fully_preserved") == 1


def test_bare_decimal_event_time_inside_shot_is_rejected():
    prompt = """integrated_multimodal_description:
[Shot 1] A presenter waits. At 2.500, the presenter smiles.

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 5.0)
    assert any("Numeric event times" in item for item in report["errors"])


def test_placeholder_shot_times_are_distributed_inside_duration():
    raw = """detailed_description:
[Shot 1] Start. [Shot 2] At 00:0X.XXX, Middle. [Shot 3] At 00:XX.XXX, End.

overall_soundscape:
Room tone."""
    fixed = normalize_shot_timeline(raw, "ref2va", 5.0)
    assert "[Shot 2] At 00:01.667," in fixed
    assert "[Shot 3] At 00:03.333," in fixed


def test_every_audio_policy_combination_builds_an_explicit_contract():
    ambience_labels = {"auto": "AUTO", "ensure_audible": "REQUIRED", "off": "OFF"}
    score_labels = {"follow_prompt": "FOLLOW SOURCE", "add_instrumental": "REQUIRED", "off": "OFF"}
    voice_labels = {
        "audible": "AUDIBLE",
        "silent_mouth_acting_experimental": "SILENT MOUTH ACTING",
        "none": "NONE",
    }
    for mode in ("t2va", "ref2va"):
        for ambience in ("auto", "ensure_audible", "off"):
            for score in ("follow_prompt", "add_instrumental", "off"):
                for voice in ("audible", "silent_mouth_acting_experimental", "none"):
                    request = build_user_request(
                        'A presenter says "Hello".', mode, 5.0, "", True,
                        ambience, score, voice,
                    )
                    assert f"AMBIENCE AND FOLEY POLICY — {ambience_labels[ambience]}" in request
                    assert f"NON-DIEGETIC MUSIC POLICY — {score_labels[score]}" in request
                    assert f"VOICE POLICY — {voice_labels[voice]}" in request


def test_silent_voice_normalization_repairs_dangling_spoken_phrase_grammar():
    raw = """integrated_multimodal_description:
[Shot 1] The presenter looks into camera, their mouth forming the shape for "Hello", then smiles.

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    fixed = normalize_source_dialogue(
        raw, 'The presenter says "Hello", then smiles.', "t2va",
        "silent_mouth_acting_experimental",
    )
    assert "forming the shape for" not in fixed
    assert "Hello" not in fixed
    assert "mouth and jaw articulating silently" in fixed


def test_fully_copied_audio_conflicts_with_selective_audio_suppression():
    detail = " ".join(["<Audio 1> remains synchronized with the new video."] * 65)
    prompt = f"""subject_definitions:
<Audio 1> is the supplied audio signal copied as a synchronized audio layer.

summary:
[audio reuse / generation] Reuse the source audio.

retention_analysis:
<Audio 1>: fully_copy - preserve the complete source signal.

detailed_description:
[Shot 1] {detail}

overall_soundscape:
N/A

non_diegetic_music:
N/A"""
    report = validate_prompt(
        prompt, "ref2va", 5.0, "Fully copy audio 1.", "", "off", "off", "none",
    )
    assert any("cannot be selectively stripped" in item for item in report["errors"])


INTERDIMENSIONAL_SOURCE = (
    'Escena de película de acción de superhéroes. El hombre en imagen 2 está en un laboratorio. '
    'La mujer le dice a la persona de imagen 2, con una voz femenina: "tranquilo, no estás solo", '
    'y le señala hacia el fondo. De entre las sombras aparecen poco a poco los hombres de imagen 1, '
    'imagen 3, imagen 4, versiones interdimensionales distintas de él: la version ejercito nazi de '
    'imagen 1, la version con boina que será boinaman en imagen 3, y la versión heavy que es imagen 4.'
)


def test_reference_aliases_and_variant_phrases_become_four_stable_subjects():
    model = _official_reference_model(INTERDIMENSIONAL_SOURCE)
    assert len(model["subjects"]) == 4
    assert [item["asset"] for item in model["subjects"]] == [
        "<Picture 2>", "<Picture 1>", "<Picture 3>", "<Picture 4>",
    ]
    lines = "\n".join(item["line"] for item in model["definitions"])
    assert "reusable hombre" not in lines
    assert "reusable la persona" not in lines
    assert "version ejercito nazi" in lines
    assert "version con boina" in lines
    assert "versión heavy" in lines
    assert "alternate version of <Subject 1>" in lines


def test_spanish_statement_dialogue_is_tagged_spanish_without_question_words():
    assert _source_dialogue_contracts(INTERDIMENSIONAL_SOURCE) == [
        ("Spanish", "tranquilo, no estás solo", False),
    ]


def test_gradual_reveal_requires_one_shot_and_rejects_periodic_multishot_output():
    request = build_user_request(INTERDIMENSIONAL_SOURCE, "ref2va", 15.0)
    assert "SHOT PLAN: Exactly one continuous shot" in request
    generated = """subject_definitions:
<Subject 1> is the person from <Picture 2>.
<Subject 2> is the variant from <Picture 1>.
<Subject 3> is the variant from <Picture 3>.
<Subject 4> is the variant from <Picture 4>.

summary:
[reference generation] A gradual laboratory reveal.

retention_analysis:
<Subject 1>: fully_preserved - preserve.
<Subject 2>: fully_preserved - preserve.
<Subject 3>: fully_preserved - preserve.
<Subject 4>: fully_preserved - preserve.

detailed_description:
[Shot 1] The woman says <d>[Spanish] tranquilo, no estás solo</d>. [Shot 2] At 00:03.000, She speaks directly to the man. [Shot 3] At 00:06.000, As she finishes speaking, portals form. [Shot 4] At 00:09.000, variants emerge. [Shot 5] At 00:12.000, the reveal completes.

overall_soundscape:
Laboratory hum.

non_diegetic_music:
N/A"""
    report = validate_prompt(generated, "ref2va", 15.0, INTERDIMENSIONAL_SOURCE)
    joined = "\n".join(report["errors"])
    assert "gradual continuous progression requires exactly one" in joined
    assert "Affirmative speaking cues outside" in joined


def test_dialogue_normalizer_closes_line_and_neutralizes_common_continuations():
    raw = """integrated_multimodal_description:
[Shot 1] A woman says <d>[Spanish] tranquilo, no estás solo</d>. [Shot 2] At 00:03.000, She speaks directly to the man, maintaining eye contact with him while gesturing. As she finishes speaking, she points into the shadows.

overall_soundscape:
Room tone.

non_diegetic_music:
N/A"""
    fixed = normalize_source_dialogue(raw, INTERDIMENSIONAL_SOURCE, "t2va")
    assert "speaks directly" not in fixed
    assert "finishes speaking" not in fixed
    assert "no character speaks any additional words" in fixed


def test_two_dialogues_use_stable_subject_id_and_plural_audio_boundary():
    source = 'The man says in an off-screen voiceover "First line". Then the man shouts "Second line".'
    generated = """subject_definitions:
<Subject 1> is the man from <Picture 1>.
summary:
[reference generation] A two-line scene.
retention_analysis:
<Subject 1>: fully_preserved - preserve him.
detailed_description:
[Shot 1] <Subject 1> (S1) says in an off-screen voiceover <d>[Original language] First line</d>. [Shot 2] At 00:03.000, <Subject 1> (S2) shouts <d>[Original language] Second line</d>. The speaker immediately closes their mouth. After the final tagged line, no character speaks any additional words. From this point through the final frame, every character keeps their mouth closed; the tagged line is the only intelligible speech in the video. The speaker immediately closes their mouth.
overall_soundscape:
Wind and footsteps. The single tagged line is the only intelligible voice; after it ends, only non-verbal ambience and physical sounds remain, with no narration, whispers, or additional words.
non_diegetic_music:
N/A"""
    fixed = normalize_source_dialogue(generated, source, "ref2va")
    assert fixed.count("<Subject 1> (S1)") == 2
    assert "<Subject 1> (S2)" not in fixed
    assert fixed.count("After the final tagged line, no character speaks any additional words.") == 1
    assert "The two tagged lines are the only intelligible speech" in fixed
    assert "single tagged line" not in fixed
    assert "keeps their mouth closed" not in fixed


def test_follow_prompt_normalizes_blank_music_to_na_when_source_has_no_music():
    prompt = """integrated_multimodal_description:
[Shot 1] A runner crosses a courtyard.
overall_soundscape:
Footsteps on concrete.
non_diegetic_music:
"""
    fixed = normalize_audio_policy(prompt, "auto", "follow_prompt", "audible", "A runner crosses a courtyard.")
    assert "non_diegetic_music:\nN/A" in fixed


def test_dialogue_tag_normalizer_removes_redundant_outer_quotes():
    fixed = normalize_dialogue_tags('She shouts "<d>[Spanish] Hola</d>."')
    assert fixed == "She shouts <d>[Spanish] Hola</d>."


def test_unassigned_picture_is_not_promoted_to_a_generic_subject():
    source = "The man in image 1 wears a green ninja costume."
    context = "Connected reference <Picture 2> has no declared role."
    model = _official_reference_model(source, context)
    assert [item["label"] for item in model["subjects"]] == ["<Subject 1>"]
    assert model["unassigned_assets"] == {"<Picture 2>"}
    assert "wardrobe, styling, pose, and state follow explicit source instructions" in model["definitions"][0]["line"]


def test_orphan_subject_for_generated_child_becomes_literal_source_description():
    source = (
        "The man in image 1 kicks a little 8 year old girl with golden locks in a wheelchair, "
        "while he shouts."
    )
    raw = "<Subject 1> kicks <Subject 2>. <Subject 2> flies offscreen."
    fixed = normalize_unassigned_subjects(
        raw, source, "Connected reference <Picture 2> has no declared role.",
    )
    assert "<Subject 2>" not in fixed
    assert "the little 8 year old girl with golden locks in a wheelchair" in fixed


def test_reference_summary_drops_stale_task_list_from_llm_body():
    raw = """subject_definitions:
<Subject 1> is a person from <Picture 1>.
<Subject 2> is generic content from <Picture 2>.
summary:
[reference generation] video continuation + reference generation
retention_analysis:
<Subject 1>: fully_preserved - preserve.
<Subject 2>: fully_preserved - preserve.
detailed_description:
[Shot 1] <Subject 1> waits beside <Subject 2>.
overall_soundscape:
Room tone.
non_diegetic_music:
N/A"""
    fixed = normalize_reference_definitions(
        raw,
        "The man in image 1 waits.",
        "Connected reference <Picture 2> has no declared role.",
    )
    assert "summary:\n[reference generation] " in fixed
    assert "video continuation + reference generation" not in fixed
    assert "<Subject 2>" not in fixed.split("summary:", 1)[0]

    bracketed = raw.replace(
        "[reference generation] video continuation + reference generation",
        "[reference generation] + [video continuation]",
    )
    fixed_bracketed = normalize_reference_definitions(
        bracketed,
        "The man in image 1 waits.",
        "Connected reference <Picture 2> has no declared role.",
    )
    assert "summary:\n[reference generation] " in fixed_bracketed
    assert "[video continuation]" not in fixed_bracketed


def test_explicit_child_attributes_and_forced_exit_are_critical_source_facts():
    source = (
        "He hits a little 8 year old girl with golden locks in a wheelchair. "
        "The girl goes flying hard offscreen after the hit."
    )
    incomplete = "He strikes a girl seated in her wheelchair."
    errors = _explicit_source_fact_errors(source, incomplete)
    assert any("8-year-old" in item for item in errors)
    assert any("golden locks" in item for item in errors)
    assert any("forced movement out of frame" in item for item in errors)


def test_forced_offscreen_outcome_contract_requires_visible_trajectory_before_cut():
    request = build_user_request(
        "The girl goes flying hard offscreen after the hit.",
        "t2va",
        6.0,
    )

    assert "trajectory readable in a wide enough shot" in request
    assert "do not cut away or move to a close-up" in request
    assert "until it fully exits the frame" in request


def test_compound_source_attributes_get_exact_ownership_locks():
    request = build_user_request(
        "A red-haired pilot crosses a storm-damaged hangar and stops beside a blue aircraft.",
        "t2va",
        6.0,
    )
    assert "'red-haired' modifies only 'pilot'" in request
    assert "'storm-damaged' modifies only 'hangar'" in request
    assert "Do not transfer that condition" in request

    transferred = (
        "A red-haired pilot crosses the storm-damaged hangar. The blue aircraft shows signs of minor damage."
    )
    errors = _explicit_source_fact_errors(
        "A red-haired pilot crosses a storm-damaged hangar and stops beside a blue aircraft.",
        transferred,
    )
    assert any("damage state was transferred" in error for error in errors)
    clean = "A red-haired pilot crosses the storm-damaged hangar and stops beside the intact blue aircraft."
    assert not any(
        "damage state was transferred" in error
        for error in _explicit_source_fact_errors(
            "A red-haired pilot crosses a storm-damaged hangar and stops beside a blue aircraft.", clean,
        )
    )

    intact_request = build_user_request(
        "The pilot stops beside a clean, intact blue aircraft inside a storm-damaged hangar.",
        "t2va", 5.0,
    )
    assert "Preserve the explicit intact state of 'aircraft'" in intact_request
    intact_errors = _explicit_source_fact_errors(
        "The pilot stops beside a clean, intact blue aircraft inside a storm-damaged hangar.",
        "The pilot stops beside a weathered blue aircraft inside the storm-damaged hangar.",
    )
    assert any("intact state" in error for error in intact_errors)


def test_audio_sentence_limits_compact_excess_without_dropping_content():
    prompt = """integrated_multimodal_description:
[Shot 1] Three rings align.

overall_soundscape:
First. Second. Third. Fourth. Fifth.

non_diegetic_music:
One. Two. Three. Four. Five."""
    normalized = normalize_audio_section_sentence_limits(prompt, "t2va")
    report = validate_prompt(normalized, "t2va", 5, "Three rings align with music.")
    assert not any("should contain 1-4" in warning for warning in report["warnings"])
    assert not any("should contain 1-3" in warning for warning in report["warnings"])
    assert "Fourth; Fifth." in normalized
    assert "Three; Four; Five." in normalized


def test_unresolved_offscreen_voice_is_rejected():
    prompt = """integrated_multimodal_description:
[Shot 1] An unseen voice (S1) says in an off-screen voiceover <d>[Original language] Hola</d>.
overall_soundscape:
Room tone.
non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 5, 'A voice in off says "Hola".')
    assert any("identify its source" in item for item in report["errors"])


def test_named_godlike_offscreen_voice_is_not_treated_as_unresolved():
    prompt = """integrated_multimodal_description:
[Shot 1] An off-screen godlike voice (S1) booms: <d>[English] power up!</d>.
overall_soundscape:
Divine echo and room ambience.
non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 5, 'A godlike voice is heard saying "power up!" in English.')
    assert not any("identify its source" in item for item in report["errors"])


def test_speaker_placeholder_uses_first_free_id_and_names_narrator():
    source = 'A voice in off says "First". Then the man says "Second".'
    generated = """integrated_multimodal_description:
[Shot 1] An off-screen voiceover (Sx) says in an off-screen voiceover <d>[Original language] First</d>. The man (S2) says <d>[Original language] Second</d>.
overall_soundscape:
Room tone.
non_diegetic_music:
N/A"""
    fixed = normalize_source_dialogue(generated, source, "t2va")
    assert "An off-screen narrator (S1) says in an off-screen voiceover" in fixed
    assert "(Sx)" not in fixed
    assert "The two tagged lines are the only intelligible speech" in fixed


def test_acoustic_space_catalog_is_complete_unique_and_individually_injected():
    assert ACOUSTIC_SPACE_CHOICES[0] == "none"
    assert set(ACOUSTIC_SPACE_CONTRACTS) == set(ACOUSTIC_SPACE_CHOICES) - {"none"}
    assert len(set(ACOUSTIC_SPACE_CONTRACTS.values())) == len(ACOUSTIC_SPACE_CONTRACTS)
    assert DIALOGUE_COVERAGE_CHOICES == ("off", "on")
    for space in ACOUSTIC_SPACE_CHOICES[1:]:
        request = build_user_request("A woman crosses a room.", "t2va", 5.0, acoustic_space=space)
        assert ACOUSTIC_SPACE_CONTRACTS[space] in request
        assert f"Selected acoustic space: {space}." in request


def test_acoustic_space_and_coverage_stay_deterministic_and_do_not_override_audio_gates():
    arguments = {
        "acoustic_space": "underwater_muffled",
        "dialogue_coverage": "on",
        "ambience_foley_policy": "off",
        "cinematography_json": json.dumps({
            "schemaVersion": 1, "shotScale": "close_up", "cameraMotion": "shake",
            "cameraAmplitude": "small",
        }),
    }
    first = build_user_request('A diver says "Now."', "t2va", 6.0, "", **arguments)
    second = build_user_request('A diver says "Now."', "t2va", 6.0, "", **arguments)
    assert first == second
    assert "AMBIENCE AND FOLEY POLICY — OFF" in first
    assert "it never re-enables a disabled audio layer" in first
    assert "The camera shakes with small amplitude, handheld-style" in first

def test_system_prompt_teaches_official_camera_amplitude_speed_and_cut_vocabulary():
    base = system_prompt_for_mode("t2va")
    assert '"with small amplitude"/"with large amplitude"' in base
    assert '"at slow speed"/"at fast speed"' in base
    assert "omit medium amplitude and normal speed" in base
    assert '"the shot transitions to"' in base
    assert "use cross-dissolve, fade, or" in base
    assert "wipe only when the user asks" in base


def test_system_prompt_no_longer_stacks_camera_labels_or_free_cut_wording():
    base = system_prompt_for_mode("t2va")
    assert "Write camera motion naturally using motion type" not in base
    assert "Write camera motion as a natural action inside the shot" in base


def test_system_prompt_teaches_scenetrans_pairs_and_continuity_phrasings():
    base = system_prompt_for_mode("t2va")
    reference = system_prompt_for_mode("ref2va")
    for contract in (base, reference):
        # The layout must stay compatible with the quote validator, which requires each
        # source line exactly once inside a single <d> block.
        flowed = " ".join(contract.split())
        assert "keep the full line in a single <d> block in the shot where it begins" in flowed
        assert "never split across two <d> blocks" in flowed
        assert "place <scenetrans> outside <d> at the connecting point in both shots" in flowed
        assert "continues seamlessly across the cut" in contract
        assert "continues uninterrupted into the next shot" in contract
        assert "carries over from the previous shot" in contract
        assert "remains audible across the transition" in contract


def test_system_prompt_uses_official_cutoff_semantics_not_intentional_truncation():
    base = system_prompt_for_mode("t2va")
    assert "Use <cutoff> only when speech is truncated by the end of the video" in base
    assert "only for intentionally truncated speech" not in base


def test_system_prompt_establishes_first_appearance_speaker_identity_outside_the_tag():
    base = system_prompt_for_mode("t2va")
    assert "At a speaker's first appearance, establish a stable" in base
    assert "vocal identity outside <d> from source-supported context" in base
    assert "pitch, timbre, speaking rate, or accent" in base


def test_system_prompt_uses_the_official_completely_closed_lips_wording():
    base = system_prompt_for_mode("t2va")
    assert base.count("lips remain completely closed") == 2
    assert "lips remain closed" not in base.replace("lips remain completely closed", "")


def test_non_diegetic_music_rule_bans_mood_words_and_relocates_diegetic_music():
    base = system_prompt_for_mode("t2va")
    assert "never through abstract mood words or the score's emotional function" in base
    assert "singing, played instruments, radio, television, phone" in base


def test_ref2va_contract_states_the_video_editing_summary_opener():
    reference = system_prompt_for_mode("ref2va")
    base = system_prompt_for_mode("t2va")
    assert 'The target video is an edited version of <Video 1>.' in reference
    assert "introduces no new one" in reference
    assert "edited version of <Video 1>" not in base


def _scenetrans_prompt(continuity: str) -> str:
    """A real line crossing a cut, laid out exactly as the system contract now teaches.

    The full quoted line stays in one <d> block in the shot where it begins, both
    <scenetrans> markers sit outside <d>, and the continuity statement lands at the
    natural end of the second shot - deliberately more than 300 characters after the
    second marker, which the old windowed check would have missed.
    """
    return (
        "integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium shot frames a woman beside "
        "a train window. The quiet young woman (S1), in her mid-twenties with a soft mid-range voice, "
        "says: <d>[Original language] I get off at the next "
        "station.</d> <scenetrans>\n\n"
        "[Shot 2] At 00:03.000, the camera cuts to the platform, <scenetrans> where the same woman (S1) is framed "
        "in a matching medium shot as she steps down onto wet concrete. The camera trucks right at slow speed, "
        "holding her at the same height in frame while the carriage windows slide past behind her and the "
        "overhead canopy lights streak along the wet ground. She keeps her gaze fixed on the exit stairs, one "
        "hand closed around the strap of her bag, her expression unchanged. "
        f"Her line {continuity}.\n\n"
        "overall_soundscape: Steady wheels hum beneath a low ventilation drone.\n\n"
        "non_diegetic_music: N/A"
    )


SCENETRANS_SOURCE = 'A woman says "I get off at the next station." No music.'


def test_scenetrans_pair_with_official_continuity_statement_is_accepted():
    report = validate_prompt(_scenetrans_prompt("continues seamlessly across the cut"), "t2va", 8.0,
                             SCENETRANS_SOURCE)
    assert report["valid"], report


@pytest.mark.parametrize("continuity", [
    "continues uninterrupted into the next shot",
    "carries over from the previous shot",
    "remains audible across the transition",
])
def test_every_official_continuity_phrasing_is_accepted(continuity):
    report = validate_prompt(_scenetrans_prompt(continuity), "t2va", 8.0, SCENETRANS_SOURCE)
    assert report["valid"], report


def test_scenetrans_pair_without_a_continuity_statement_is_rejected():
    report = validate_prompt(_scenetrans_prompt("ends there"), "t2va", 8.0, SCENETRANS_SOURCE)
    assert any("audio continues across the cut" in item for item in report["errors"])


def test_odd_scenetrans_count_still_reports_the_missing_connecting_point():
    prompt = _scenetrans_prompt("continues seamlessly across the cut").replace(" <scenetrans> where", " where")
    errors = validate_prompt(prompt, "t2va", 8.0, SCENETRANS_SOURCE)["errors"]
    assert any("both connecting points" in item for item in errors)
    assert not any("audio continues across the cut" in item for item in errors)


def test_continuity_statement_is_found_far_beyond_the_old_three_hundred_character_window():
    prompt = _scenetrans_prompt("continues seamlessly across the cut")
    second_marker = prompt.rindex("<scenetrans>")
    assert prompt.index("continues seamlessly across the cut") - second_marker > 300
    assert validate_prompt(prompt, "t2va", 8.0, SCENETRANS_SOURCE)["valid"]


def test_uppercase_scenetrans_is_canonicalized_and_still_counted():
    shouted = _scenetrans_prompt("continues seamlessly across the cut").replace("<scenetrans>", "<SCENETRANS>")
    normalized = normalize_dialogue_tags(shouted)
    assert "<SCENETRANS>" not in normalized
    assert normalized.count("<scenetrans>") == 2
    assert validate_prompt(normalized, "t2va", 8.0, SCENETRANS_SOURCE)["valid"]
    # Even unnormalized, a shouted marker must not evade the pairing check.
    odd = shouted.replace(" <SCENETRANS> where", " where")
    assert any("both connecting points" in item
               for item in validate_prompt(odd, "t2va", 8.0, SCENETRANS_SOURCE)["errors"])


def test_uppercase_cutoff_does_not_evade_the_placement_check():
    misplaced = _scenetrans_prompt("continues seamlessly across the cut").replace(
        "Her line continues", "<CUTOFF> Her line continues",
    )
    errors = validate_prompt(misplaced, "t2va", 8.0, SCENETRANS_SOURCE)["errors"]
    assert any("final dialogue block" in item for item in errors)


@pytest.mark.parametrize("continuity", [
    "continues across the cut",
    "continues uninterrupted",
    "carries over",
    "remains audible through the cut",
    "is heard without interruption across the transition",
])
def test_natural_variants_of_the_official_continuity_families_are_accepted(continuity):
    report = validate_prompt(_scenetrans_prompt(continuity), "t2va", 8.0, SCENETRANS_SOURCE)
    assert report["valid"], report


CUTOFF_SOURCE = (
    "A courier reaches a closed bridge. Write the dialogue in English; her final line is truncated by the end "
    "of the video. No music."
)
CUTOFF_PROMPT = """integrated_multimodal_description: [Shot 1] Live-action, cinematic, a wide shot frames a courier stopping at a closed bridge. The young courier with a clear, breathless voice (S1) says: <d>[English] The bridge is clo<cutoff></d>

overall_soundscape: Wind pushes across the empty deck while loose gravel shifts under her boots.

non_diegetic_music: N/A"""


def test_cutoff_inside_the_final_truncated_dialogue_block_is_accepted():
    report = validate_prompt(CUTOFF_PROMPT, "t2va", 6.0, CUTOFF_SOURCE)
    assert report["valid"], report


def test_cutoff_after_the_last_dialogue_block_is_rejected():
    prompt = CUTOFF_PROMPT.replace(
        "The bridge is clo<cutoff></d>",
        "The bridge is closed.</d> The signal light blinks <cutoff> long after her voice ends.",
    )
    errors = validate_prompt(prompt, "t2va", 6.0, CUTOFF_SOURCE)["errors"]
    assert any("<cutoff> must occur inside the final dialogue block" in item for item in errors)


@pytest.mark.parametrize("language", [
    "Arabic", "Chinese", "English", "French", "German", "Italian",
    "Japanese", "Korean", "Portuguese", "Russian", "Spanish", "Catalan",
])
def test_every_supported_dialogue_language_resolves_to_its_canonical_name(language):
    authorized, resolved = _dialogue_authoring_request(f"Write the dialogue in {language}.")
    assert authorized
    assert resolved == language


@pytest.mark.parametrize("request_text,expected", [
    ("genera el diálogo en français", "French"),
    ("escribe el diálogo en deutsch", "German"),
    ("escribe el diálogo en italiano", "Italian"),
    ("escribe el diálogo en português brasileiro", "Portuguese"),
    ("write the dialogue in 日本語", "Japanese"),
    ("write the dialogue in 한국어", "Korean"),
    ("write the dialogue in 中文", "Chinese"),
    ("write the dialogue in mandarin", "Chinese"),
    ("write the dialogue in русский", "Russian"),
    ("write the dialogue in العربية", "Arabic"),
    ("escribe el diálogo en castellano", "Spanish"),
    ("escribe el diálogo en català", "Catalan"),
    # Unaccented "catala" was an alias with no detection entry, so it never resolved.
    ("escribe el diálogo en catala", "Catalan"),
])
def test_endonym_dialogue_requests_resolve_to_the_canonical_tag_name(request_text, expected):
    authorized, resolved = _dialogue_authoring_request(request_text)
    assert authorized
    assert resolved == expected


def test_cantonese_is_not_folded_into_chinese():
    assert _dialogue_authoring_request("write the dialogue in cantonese")[1] == "Cantonese"


@pytest.mark.parametrize("garment", [
    "mandarin collar", "mandarin collars", "mandarin jacket", "mandarin dress",
    "mandarin gown", "mandarin robe", "mandarin duck", "mandarin oranges",
])
def test_garment_and_food_senses_of_mandarin_do_not_tag_dialogue_as_chinese(garment):
    # "dressed in mandarin collar" used to make an English line come back as [Chinese].
    source = f'A tailor dressed in {garment} says "Hold still, please."'
    assert _source_dialogue_contracts(source) == [("Original language", "Hold still, please.", False)]
    assert _dialogue_authoring_request(f"Write the dialogue. The tailor wears a {garment}.")[1] == (
        "Original language"
    )


def test_the_language_sense_of_mandarin_still_resolves_to_chinese():
    assert _dialogue_authoring_request("write the dialogue in mandarin")[1] == "Chinese"
    assert _source_dialogue_contracts('She says in mandarin: "你好。"') == [("Chinese", "你好。", False)]


def test_bare_brasileiro_is_not_read_as_a_requested_language():
    # It is an ordinary demonym; only the "português brasileiro" forms name a language.
    source = 'A brasileiro street vendor says "Two for one."'
    assert _source_dialogue_contracts(source) == [("Original language", "Two for one.", False)]
    assert _source_dialogue_contracts('Dice en português brasileiro: "Bom dia."') == [
        ("Portuguese", "Bom dia.", False)
    ]


def test_unspaced_endonyms_are_detected_without_ascii_word_boundaries():
    # 日本語 is immediately followed by another CJK character, where \b never holds.
    assert _source_dialogue_contracts('El personaje dice en 日本語写: "こんにちは。"') == [
        ("Japanese", "こんにちは。", False)
    ]
    assert _source_dialogue_contracts('He says in 中文写的台词: "你好。"') == [("Chinese", "你好。", False)]


def test_unknown_language_still_falls_through_to_capitalize():
    assert _source_dialogue_contracts('She says in the Swedish language: "Hej."') == [
        ("Swedish", "Hej.", False)
    ]
    # Lowercase aliased names keep using the plain .capitalize() fallthrough.
    assert _dialogue_authoring_request("write the dialogue in dutch")[1] == "Dutch"
    # An unlisted language keeps the pre-existing conservative authoring default.
    assert _dialogue_authoring_request("Write the dialogue in Swedish.")[1] == "Original language"


def test_endonym_language_reaches_the_dialogue_authoring_contract():
    request = build_user_request("Un vendedor abre su puesto. Genera el diálogo en français.", "t2va", 6.0)
    assert "<d>[French] concrete authored words</d>" in request


_BUDGET_SOURCE = "A mechanic walks through a workshop."


def _budget_prompt(body):
    return f"""integrated_multimodal_description: [Shot 1] {body}

overall_soundscape: Footsteps cross the concrete floor.

non_diegetic_music: N/A"""


def test_oversized_prompt_only_warns_about_the_official_api_text_block_limit():
    # ~11 chars/word keeps this above 7000 characters while staying under the word cap,
    # so the two budget advisories are proven independent.
    body = "A mechanic walks through a workshop. " + (
        "The characteristically methodical instrumentation demonstrates uncompromising "
        "professionalization throughout. " * 70
    )
    report = validate_prompt(_budget_prompt(body), "t2va", 5.0, _BUDGET_SOURCE)
    assert len(_budget_prompt(body)) > 7000
    assert report["valid"], report
    assert report["errors"] == []
    assert any("MiniMax API v2 accepts at most 7000 characters" in warning for warning in report["warnings"])
    assert any("Local open-weights inference is unaffected" in warning for warning in report["warnings"])
    assert not any("350-500 is recommended" in warning for warning in report["warnings"])


def test_overlong_base_description_warns_without_claiming_a_ref2va_word_target():
    body = "A mechanic walks through a workshop. " + (
        "The mechanic moves past a row of tools and the light stays even across the room. " * 45
    )
    report = validate_prompt(_budget_prompt(body), "t2va", 5.0, _BUDGET_SOURCE)
    assert report["valid"], report
    assert any("repeats the same descriptive sentence" in warning for warning in report["warnings"])
    assert not any("350-500" in warning for warning in report["warnings"])
    assert not any("MiniMax API v2" in warning for warning in report["warnings"])


def test_prompts_inside_both_budgets_raise_no_length_warning():
    report = validate_prompt(
        _budget_prompt("A mechanic walks through a workshop and stops beside a workbench."),
        "t2va", 5.0, _BUDGET_SOURCE,
    )
    assert report["valid"], report
    assert not any(
        "MiniMax API v2" in warning or "350-500 is recommended" in warning
        for warning in report["warnings"]
    )


def test_api_v2_delivery_target_makes_the_7000_character_cap_hard():
    body = "A mechanic crosses the workshop. " + ("Distinct calibrated machinery remains visible. " * 180)
    prompt = _budget_prompt(body)
    local = validate_prompt(prompt, "t2va", 5.0, _BUDGET_SOURCE, delivery_target="local")
    api = validate_prompt(prompt, "t2va", 5.0, _BUDGET_SOURCE, delivery_target="api_v2")
    assert local["valid"] and not local["apiCompatible"]
    assert not api["valid"] and not api["apiCompatible"]
    assert any("7000 characters" in error for error in api["errors"])


def test_enhanced_profile_has_no_universal_two_shot_cap_but_conservative_does():
    prompt = """integrated_multimodal_description:
[Shot 1] A mechanic waits beside a car.
[Shot 2] At 00:02.000, the camera cuts to the mechanic opening the door.
[Shot 3] At 00:04.000, the camera cuts to the mechanic seated inside as the door settles closed.

overall_soundscape:
Workshop room tone and the existing door movement remain audible.

non_diegetic_music:
N/A"""
    enhanced = validate_prompt(
        prompt, "t2va", 6.0, "A mechanic enters a car.", enhance_description=True,
    )
    conservative = validate_prompt(
        prompt, "t2va", 6.0, "A mechanic enters a car.", enhance_description=False,
    )
    assert enhanced["valid"], enhanced
    assert enhanced["enhancementProfile"] == "enhanced_production"
    assert any("at most 2 shot" in error for error in conservative["errors"])
    assert conservative["enhancementProfile"] == "conservative_grounded"


def test_reference_normalization_is_idempotent_and_keeps_specific_analysis():
    raw = """subject_definitions:
<Subject 1> is the grease-stained workshop mechanic whose identity comes from <Picture 1>.

summary:
[reference generation] The target keeps <Subject 1> beside the same workshop door.

retention_analysis:
<Subject 1>: fully_preserved - preserve the mechanic's face, overalls, and grease marks in every shot.

detailed_description:
[Shot 1] <Subject 1> opens the workshop door.

overall_soundscape:
Workshop room tone and the door hinge.

non_diegetic_music:
N/A"""
    source = "The mechanic in image 1 opens the workshop door."
    once = normalize_reference_definitions(raw, source)
    twice = normalize_reference_definitions(once, source)
    assert twice == once
    assert "grease-stained workshop mechanic" in once
    assert "face, overalls, and grease marks" in once
    assert "The target keeps <Subject 1> beside the same workshop door." in once


@pytest.mark.parametrize("source", [
    "Write a cinematic scene with no dialogue.",
    "Create a silent scene without spoken words.",
    "Make up the visual action, but no dialogue.",
    "Crea una escena sin diálogo.",
    "Haz una escena pero no añadas diálogo.",
    "Genera vídeo sin narración.",
])
def test_dialogue_prohibitions_never_authorize_new_spoken_words(source):
    assert _dialogue_authoring_request(source) == (False, "Original language")


def test_positive_dialogue_request_after_a_separate_prohibition_is_honored():
    source = "Keep the opening silent with no dialogue. Then write one Spanish dialogue line for the woman."
    assert _dialogue_authoring_request(source) == (True, "Spanish")


def test_visible_text_after_spoken_dialogue_is_not_reclassified_as_speech():
    source = 'A woman says "Hello." Behind her, a sign reads "EXIT".'
    assert _source_dialogue_contracts(source) == [("Original language", "Hello.", False)]
    assert _source_dialogue_contracts('A woman speaks to camera. Her shirt displays "OPENAI".') == []


@pytest.mark.parametrize("source, expected_roles", [
    ("The woman and the man in image 1 walk together.", ("woman", "man")),
    ("The older woman and the young boy in image 1 wait.", ("older woman", "young boy")),
    ("The red car and the blue motorcycle in image 1 move.", ("red car", "blue motorcycle")),
])
def test_distinct_entities_from_one_picture_remain_distinct_subjects(source, expected_roles):
    model = _official_reference_model(source)
    assert tuple(item["role"] for item in model["subjects"]) == expected_roles


@pytest.mark.parametrize("context", [
    "Picture 1 supplies the identity.",
    "Image 1 provides identity.",
    "Imagen 1 proporciona la identidad.",
])
def test_plain_reference_context_from_ui_activates_ref2va_and_identity(context):
    assert resolve_mode("auto", context, "A person waves.") == "ref2va"
    model = _official_reference_model("A person waves.", context)
    assert model["assets"] == ["<Picture 1>"]
    assert model["subjects"] and model["subjects"][0]["contribution"] == "identity"


def test_system_prompt_and_worst_case_user_request_stay_inside_their_token_budgets():
    # Measured 2026-08: SYSTEM_PROMPT 10523 chars, worst-case user request 31689 chars with every
    # control at its most verbose setting, including the shot-scale/angle/viewpoint axes, the
    # acoustic space, dialogue-coverage and source-gated emotional-performance clauses. Caps are
    # the measurement plus ~10-15%;
    # exceeding one means prompt growth that silently degrades small local GGUF models and must be
    # reviewed deliberately.
    assert len(SYSTEM_PROMPT) < 12000
    creative = json.dumps({
        "schemaVersion": 1, "genre": "sports_competition", "visualLanguage": "anime_shojo_pastel",
        "worldAesthetic": "analog_1980s", "tone": "pulp_heightened",
    })
    cinematography = json.dumps({
        "schemaVersion": 1, "colorPalette": "classic_western_earth_sky", "exposureContrast": "low_key",
        "shotScale": "extreme_close_up", "cameraAngle": "dutch_static",
        "cameraViewpoint": "mirror_or_reflection",
        "cameraMotion": "tracking", "cameraAmplitude": "large", "cameraSpeed": "fast",
        "optics": "compressed_telephoto", "depthOfField": "shallow", "imageTexture": "film_35mm",
        "lensEffects": "restrained_halation", "motionRendering": "energetic_blur",
    })
    shot_plan = json.dumps({
        "schemaVersion": 1, "timingMode": "exact",
        "shots": [
            {"id": f"s{index}", "description": f"Shot {index} description of the action.", "durationSeconds": 2.0}
            for index in range(1, 6)
        ],
    })
    manifest = json.dumps({
        "schemaVersion": 1,
        "assets": [
            {"label": "Image 1", "kind": "image", "role": "subject", "notes": "A woman in a red coat."},
            {"label": "Video 1", "kind": "video", "role": "scene", "notes": "Street plate."},
        ],
    })
    request = build_user_request(
        'A woman in a red coat walks to a car and says "I am leaving now." '
        "Write dialogue in English for the closing beat.",
        "fl2va", 10.0, "Image 1: a woman in a red coat.\nVideo 1: street plate.",
        True, "ensure_audible", "add_instrumental", "audible", "Slow trumpet and brushed drums.",
        "16:9", manifest, 5, 0, "Same woman", "Same voice", "Same street",
        (("English", "I am leaving now."),), creative, shot_plan, cinematography, "chinese_martial_arts",
        "large_reverberant_interior", "on",
    )
    assert len(request) < 35000


_CONTINUATION_SOURCE = (
    "Continue seamlessly from the exact same saloon interior, with the same character positions supplied "
    "by the preceding take. The batwing doors finish their existing return swing and settle naturally "
    "behind him as he walks toward the bar."
)
_FRESH_SOURCE = "A gunslinger pushes through the batwing doors of a saloon and walks to the bar."


def _saloon_prompt(timeline):
    return f"""integrated_multimodal_description: {timeline}

overall_soundscape: Boot heels knock against the plank floor and the door hinges creak.

non_diegetic_music: N/A"""


_SNAPPED_SHOT_1 = (
    "[Shot 1] A gunslinger in a dust-grey duster stands just inside a wooden saloon. The batwing doors "
    "finish their existing return swing and settle naturally behind him while he walks toward the bar."
)
_MID_MOTION_SHOT_1 = (
    "[Shot 1] A gunslinger in a dust-grey duster stands just inside a wooden saloon. Behind him the "
    "batwing doors are mid-swing and keep returning at their current speed, still travelling inward as "
    "he walks toward the bar."
)


def test_continuation_prompt_warns_when_shot_one_resolves_an_inherited_transient():
    report = validate_prompt(_saloon_prompt(_SNAPPED_SHOT_1), "t2va", 5.0, _CONTINUATION_SOURCE)
    assert report["errors"] == []
    matched = [
        warning for warning in report["warnings"]
        if "Continuation prompt resolves an in-progress transient instantly" in warning
    ]
    assert len(matched) == 1, report["warnings"]
    assert "'The batwing doors finish their existing return swing'" in matched[0]
    assert "the doors are mid-swing and keep returning at their current speed" in matched[0]


def test_continuation_prompt_accepts_a_transient_that_stays_mid_motion():
    report = validate_prompt(_saloon_prompt(_MID_MOTION_SHOT_1), "t2va", 5.0, _CONTINUATION_SOURCE)
    assert report["errors"] == []
    assert not any("in-progress transient" in warning for warning in report["warnings"])


def test_continuation_transient_advisory_ignores_completion_after_the_opening_shot():
    timeline = (
        "[Shot 1] A gunslinger in a dust-grey duster crosses the saloon floor while the batwing doors "
        "keep swinging behind him at their incoming speed. [Shot 2] At 00:02.000, the camera cuts to a "
        "low angle at the bar and the batwing doors settle naturally against their frame."
    )
    report = validate_prompt(_saloon_prompt(timeline), "t2va", 5.0, _CONTINUATION_SOURCE)
    assert report["errors"] == []
    assert not any("in-progress transient" in warning for warning in report["warnings"])


def test_completion_verbs_are_not_flagged_without_continuation_context():
    report = validate_prompt(_saloon_prompt(_SNAPPED_SHOT_1), "t2va", 5.0, _FRESH_SOURCE)
    assert report["errors"] == []
    assert not any("in-progress transient" in warning for warning in report["warnings"])


def test_ordinary_prompt_raises_no_continuation_transient_warning():
    report = validate_prompt(
        _budget_prompt("A mechanic walks through a workshop and stops beside a workbench."),
        "t2va", 5.0, _BUDGET_SOURCE,
    )
    assert report["valid"], report
    assert not any("in-progress transient" in warning for warning in report["warnings"])


def test_system_prompt_forbids_completing_an_inherited_transient_at_the_first_frame():
    assert "starts mid-motion at its" in SYSTEM_PROMPT
    assert "never already completed at the first frame" in SYSTEM_PROMPT
    assert "When the request continues a previous take" in SYSTEM_PROMPT
    assert "When the request continues a previous take" in system_prompt_for_mode("t2va")
    assert "When the request continues a previous take" in system_prompt_for_mode("ref2va")
    assert len(SYSTEM_PROMPT) < 12000


def test_title_screen_style_is_source_gated_and_validates_its_declarative_lock():
    source = 'Opening title screen displays the exact visible text "NIGHT RUN".'
    treatment = json.dumps({
        "schemaVersion": 1,
        "titleScreenStyle": "pixel_art_title",
    })
    request = build_user_request(
        source, "t2va", 5.0, enhance_description=True,
        creative_treatment_json=treatment,
    )
    lock = (
        "The requested title screen is native pixel art on one fixed low-resolution integer grid, with hard "
        "nearest-neighbor glyph clusters, a stable limited palette, no antialiasing, and a stepped grid-aligned reveal."
    )
    assert lock in request
    assert "pixel_art_title" not in request
    assert "SOURCE-AUTHORIZED TITLE SCREEN" in request

    unrelated = build_user_request(
        "A woman crosses a station.", "t2va", 5.0, enhance_description=True,
        creative_treatment_json=treatment,
    )
    assert lock not in unrelated
    assert "SOURCE-AUTHORIZED TITLE SCREEN" not in unrelated

    output = f"""integrated_multimodal_description:
{lock}
[Shot 1] A full-frame title screen displays the exact visible text "NIGHT RUN" in hard grid-aligned glyphs.

overall_soundscape:
N/A

non_diegetic_music:
N/A"""
    present = validate_prompt(
        output, "t2va", 5.0, source,
        creative_treatment_json=treatment,
        enhance_description=True,
    )
    assert not any("title screen is missing" in error for error in present["errors"])

    missing = validate_prompt(
        output.replace(lock + "\n", ""), "t2va", 5.0, source,
        creative_treatment_json=treatment,
        enhance_description=True,
    )
    assert any("title screen is missing" in error for error in missing["errors"])
