# SPDX-License-Identifier: GPL-3.0-only

from prompt_guides import (
    BASE_SECTIONS,
    REFERENCE_SECTIONS,
    alignment_instruction,
    build_user_request,
    normalize_audio_policy,
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
    _explicit_source_fact_errors,
    _source_dialogue_contracts,
)


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


def test_long_post_dialogue_timeline_requires_concrete_nonverbal_audio_occupancy():
    source = 'La mujer dice "tranquilo, no estás solo" y después aparecen lentamente tres portales.'
    visual_tail = " ".join(["Three figures gradually emerge while the camera pans deeper into the chamber."] * 8)
    prompt = f"""integrated_multimodal_description:
[Shot 1] The elderly woman with a calm feminine voice (S1) says: <d>[Spanish] tranquilo, no estás solo</d>. She closes her lips. {visual_tail}

overall_soundscape:
Laboratory ambience continues.

non_diegetic_music:
N/A"""
    report = validate_prompt(prompt, "t2va", 15.0, source)
    assert any("at least two concrete non-verbal sounds" in item for item in report["errors"])

    occupied = prompt.replace(
        "She closes her lips.",
        "She closes her lips. A machinery hum and electrical crackles occupy the entire remaining timeline.",
    )
    report = validate_prompt(occupied, "t2va", 15.0, source)
    assert not any("at least two concrete non-verbal sounds" in item for item in report["errors"])


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
    assert "CONSERVATIVE FORMAT ADAPTATION" in conservative
    assert '<d>[Original language] Do not move.</d>' in enhanced
    assert '<d>[Original language] Do not move.</d>' in conservative


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
    assert "summary:\n[reference generation]\n" in fixed
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
    assert "summary:\n[reference generation]\n" in fixed
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
    assert "summary:\n[reference generation]\n" in fixed_bracketed


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
