# SPDX-License-Identifier: GPL-3.0-only

from prompt_guides import (
    BASE_SECTIONS,
    REFERENCE_SECTIONS,
    alignment_instruction,
    build_user_request,
    normalize_dialogue_tags,
    normalize_first_shot_marker,
    normalize_shot_timestamps,
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
