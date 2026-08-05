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
    normalize_shot_timestamps,
    normalize_shot_timeline,
    normalize_section_headers,
    resolve_mode,
    strip_markdown_fence,
    system_prompt_for_mode,
    validate_prompt,
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
    assert "[reference generation] A presenter reveals an object." in fixed
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
