# SPDX-License-Identifier: GPL-3.0-only

from prompt_guides import (
    BASE_SECTIONS,
    REFERENCE_SECTIONS,
    alignment_instruction,
    build_user_request,
    normalize_dialogue_tags,
    normalize_source_dialogue,
    normalize_first_shot_marker,
    normalize_reference_definitions,
    normalize_shot_timestamps,
    normalize_shot_timeline,
    normalize_section_headers,
    resolve_mode,
    strip_markdown_fence,
    validate_prompt,
)


def test_auto_mode_is_conservative():
    assert resolve_mode("auto", "") == "t2va"
    assert resolve_mode("auto", "<Subject 1> comes from <Picture 1>") == "ref2va"


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
    assert "MANDATORY DIALOGUE CONTRACT" in request
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
    assert "MANDATORY DIALOGUE CONTRACT" in request
    assert '<d>[Spanish] Quién debe ser el asesino?</d>' in request

    generated = """integrated_multimodal_description:
[Shot 1] Detective Conan thinks intensely while a murder occurs behind him.

overall_soundscape:
Muffled sounds of struggle fill the room.

non_diegetic_music:
Slow noir jazz."""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert "says in an off-screen internal monologue" in repaired
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
    assert repaired.count("off-screen internal monologue") == 1
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
    assert repaired.count("off-screen internal monologue") == 1
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


def test_plain_image_numbers_become_immutable_picture_bindings():
    request = build_user_request(
        "The person in image 1 reveals the Uzi in image 2.", "ref2va", 5.0, "",
    )
    assert "<Picture 1> is the exact user-provided image 1" in request
    assert "visible role is person" in request
    assert "<Picture 2>" in request
    assert "visible role is Uzi" in request
    assert "Do not create any additional" in request


def test_positional_roles_are_generic_and_not_tied_to_the_regression_example():
    request = build_user_request(
        "The driver in image 1 puts on the yellow racing helmet in image 2 beside the car in image 3.",
        "ref2va", 6.0, "",
    )
    assert "<Subject 1> is the reusable driver shown in <Picture 1>" in request
    assert "<Subject 2> is the reusable yellow racing helmet shown in <Picture 2>" in request
    assert "<Subject 3> is the reusable car shown in <Picture 3>" in request


def test_plain_video_and_audio_ordinals_become_exact_asset_tags():
    request = build_user_request(
        "Continue video 1 while using audio 2 as a timing and voice reference.", "ref2va", 8.0, "",
    )
    assert "<Video 1> is the exact user-provided video 1" in request
    assert "<Audio 2> is the exact user-provided audio 2" in request
    assert "Continue <Video 1> while using <Audio 2>" in request


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
    assert any("invented reference assets" in item for item in report["errors"])
    assert any("timeline moment" in item for item in report["errors"])


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
    assert any("Unsupported retention marker" in item for item in report["errors"])


def test_object_reference_cannot_appear_before_explicit_spoken_reveal_cue():
    detail = " ".join(["The person from <Picture 1> waits beside the table."] * 50)
    detail += " The Uzi from <Picture 2> is visible. [Shot 2] At 00:02.000, the person says <d>[Spanish] como esta?</d>"
    prompt = f"""subject_definitions:
<Picture 1> is the provided source image 1 showing the person.
<Picture 2> is the provided source image 2 showing the Uzi.

summary:
[reference generation] A sales advertisement.

retention_analysis:
fully_preserved: Both references.

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
    detail = " ".join(["The person from <Picture 1> waits beside the table."] * 50)
    detail += " [Shot 2] At 00:02.000, the Uzi from <Picture 2> is revealed as the person says <d>[Spanish] como esta?</d>"
    prompt = f"""subject_definitions:
<Picture 1> is the provided source image 1 showing the person.
<Picture 2> is the provided source image 2 showing the Uzi.

summary:
[reference generation] A sales advertisement.

retention_analysis:
fully_preserved: Both references.

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
    assert "<Picture 1> is the exact user-provided image 1" in fixed
    assert "visible role is person" in fixed
    assert "<Picture 2> is the exact user-provided image 2" in fixed
    assert "visible role is Uzi" in fixed
    assert "<Subject 1> is the reusable person shown in <Picture 1>" in fixed
    assert "<Subject 2> is the reusable Uzi shown in <Picture 2>" in fixed


def test_placeholder_shot_times_are_distributed_inside_duration():
    raw = """detailed_description:
[Shot 1] Start. [Shot 2] At 00:0X.XXX, Middle. [Shot 3] At 00:XX.XXX, End.

overall_soundscape:
Room tone."""
    fixed = normalize_shot_timeline(raw, "ref2va", 5.0)
    assert "[Shot 2] At 00:01.667," in fixed
    assert "[Shot 3] At 00:03.333," in fixed
