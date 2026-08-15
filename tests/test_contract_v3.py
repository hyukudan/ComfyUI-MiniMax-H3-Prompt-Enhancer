import json

from media_manifest import generation_profile, manifest_context, manifest_dialogue, parse_media_manifest
from prompt_enhancer import enhance_prompt_with_completion
from prompt_enhancer_node import MiniMaxH3MediaManifestValidator
from prompt_guides import (
    build_user_request,
    normalize_multishot_output,
    normalize_reference_definitions,
    resolve_mode,
    normalize_source_dialogue,
    validate_prompt,
)


def test_ref2va_summary_uses_current_official_task_names_and_plus_separator():
    generated = """subject_definitions:
placeholder
summary:
[editing/continuation] placeholder
retention_analysis:
placeholder
detailed_description:
[Shot 1] placeholder
overall_soundscape:
N/A
non_diegetic_music:
N/A"""
    fixed = normalize_reference_definitions(generated, "Continue video 1 and copy audio 2.")
    assert "[video continuation + audio reuse]" in fixed
    assert "reference generation" not in fixed.split("summary:", 1)[1].split("retention_analysis:", 1)[0]
    assert "[continuation]" not in fixed


def test_official_flexible_dialogue_grammar_accepts_replies_and_group_shouts():
    single = """integrated_multimodal_description: [Shot 1] Live-action, a medium shot frames a woman. The calm woman (S1) turns toward camera and replies, <d>[English] Hello.</d>
overall_soundscape: Quiet room tone.
non_diegetic_music: N/A"""
    assert validate_prompt(single, "t2va", 5, 'The woman replies in English "Hello."')["valid"]

    group = single.replace(
        "The calm woman (S1) turns toward camera and replies, <d>[English] Hello.</d>",
        "The two children (S1,S2) shout together, <d>[English] Hello.</d>",
    ).replace("a woman", "two children")
    assert validate_prompt(group, "t2va", 5, 'The children shout in English "Hello."')["valid"]

    delivered = single.replace(
        "turns toward camera and replies,",
        "turns toward camera and replies in a firm, clear tone",
    )
    assert validate_prompt(delivered, "t2va", 5, 'The woman replies in English "Hello."')["valid"]


def test_media_manifest_assigns_effective_labels_and_video_soundtrack_audio_order():
    manifest = {"items": [
        {"type": "video", "duration": 6, "audio_mode": "paired", "role": "video editing"},
        {"type": "audio", "duration": 4, "role": "voice", "transcript": {"language": "Spanish", "text": "Hola."}},
        {"type": "picture", "role": "identity"},
    ]}
    parsed = parse_media_manifest(manifest)
    assert parsed["items"][0]["label"] == "<Video 1>"
    assert parsed["items"][0]["soundtrack_label"] == "<Audio 1>"
    assert parsed["items"][1]["label"] == "<Audio 2>"
    assert parsed["items"][2]["label"] == "<Picture 1>"
    assert manifest_dialogue(manifest) == [("<Audio 2>", "Spanish", "Hola.")]
    assert resolve_mode("auto", media_manifest=json.dumps(manifest)) == "ref2va"
    assert resolve_mode("auto", media_manifest=json.dumps({
        "items": [{"type": "picture", "role": "last_frame"}],
    })) == "l2va"


def test_auto_mode_does_not_treat_generic_keyframes_as_base_frame_modes():
    assert resolve_mode("auto", media_manifest=json.dumps({
        "items": [{"type": "picture", "role": "keyframe"}],
    })) == "ref2va"
    assert resolve_mode("auto", media_manifest=json.dumps({"items": [
        {"type": "picture", "role": "first_frame"},
        {"type": "picture", "role": "last_frame"},
    ]})) == "fl2va"


def test_manifest_rejects_audio_only_and_limits():
    parsed = parse_media_manifest({"items": [{"type": "audio", "duration": 1}]})
    assert any("only reference modality" in error for error in parsed["errors"])
    assert any("2-15s" in error for error in parsed["errors"])


def test_manifest_repairs_only_unambiguous_legacy_aspect_ratio_values():
    for legacy_value in ("auto", "16:9", "9:16"):
        parsed = parse_media_manifest(legacy_value)
        assert parsed["errors"] == []
        assert parsed["items"] == []
        assert any("migrated aspect-ratio" in warning for warning in parsed["warnings"])
    assert parse_media_manifest("not json")["errors"]
    assert parse_media_manifest("   ")["errors"] == []


def test_frame_grid_and_effective_duration_profile():
    good = generation_profile(5, "16:9", 243)
    assert good["valid"]
    assert good["effectiveDurationSeconds"] == 243 / 24
    assert any("overrides duration_seconds" in warning for warning in good["warnings"])
    assert not generation_profile(5, "16:9", 244)["valid"]
    assert not generation_profile(3, "16:9", 0)["valid"]
    long_generation = generation_profile(31, "16:9", 0)
    assert long_generation["valid"]
    assert any("trained range" in warning for warning in long_generation["warnings"])
    assert generation_profile(150, "16:9", 0)["valid"]
    assert not generation_profile(150.01, "16:9", 0)["valid"]


def test_disabled_video_audio_does_not_import_transcript_and_enabled_audio_is_normalized():
    disabled = {"items": [{"type": "video", "duration": 4, "audio_mode": "off", "transcript": "Hello"}]}
    assert manifest_dialogue(disabled) == []
    paired = {"items": [{"type": "video", "duration": 4, "audio_mode": "paired", "transcript": "Hello~~~"}]}
    assert manifest_dialogue(paired) == [("<Audio 1>", "English", "Hello.")]


def test_manifest_supports_many_to_many_authoritative_subjects():
    manifest = {"items": [
        {"type": "picture", "role": "identity"},
        {"type": "picture", "role": "alternate_view"},
    ], "subjects": [
        {"id": 1, "description": "the woman in the red coat", "sources": ["<Picture 1>", "<Picture 2>"]},
        {"id": 2, "description": "the black dog", "sources": ["<Picture 1>"]},
    ]}
    parsed = parse_media_manifest(manifest)
    assert not parsed["errors"]
    context = manifest_context(manifest)
    assert "<Subject 1> is the woman in the red coat from <Picture 1>, <Picture 2>." in context
    assert "<Subject 2> is the black dog from <Picture 1>." in context


def test_multishot_normalization_validation_and_budget_warning():
    canonical = normalize_multishot_output("first autonomous prompt\n---\nsecond autonomous prompt")
    assert json.loads(canonical) == {"prompts": ["first autonomous prompt", "second autonomous prompt"]}
    report = validate_prompt(canonical, "chained_multishot", 10.1, "two scenes", multishot_shot_count=2)
    assert report["valid"]
    assert report["promptCount"] == 2
    invalid = validate_prompt('{"prompts":["[Shot 1] bad"]}', "chained_multishot", 10, multishot_shot_count=2)
    assert not invalid["valid"]


def test_multishot_continuity_locks_are_applied_deterministically():
    canonical = normalize_multishot_output('{"prompts":["action one","action two"]}', ("red coat", "warm voice"))
    prompts = json.loads(canonical)["prompts"]
    assert all("red coat" in item and "warm voice" in item for item in prompts)
    assert validate_prompt(
        canonical, "chained_multishot", 10, multishot_shot_count=2,
        multishot_identity_lock="red coat", multishot_voice_lock="warm voice",
    )["valid"]


def test_multishot_preserves_spoken_words_without_invention():
    assert validate_prompt(
        '{"prompts":["She says \\"Exact line.\\""]}', "chained_multishot", 5,
        'She says "Exact line."', multishot_shot_count=1,
    )["valid"]
    assert not validate_prompt(
        '{"prompts":["She says \\"Changed.\\""]}', "chained_multishot", 5,
        'She says "Exact line."', multishot_shot_count=1,
    )["valid"]


def test_multishot_allows_delivery_punctuation_but_preserves_dialogue_allocation():
    source = 'A god says "power up!". Cut scene. The god says "power up!" again.'
    correctly_allocated = '{"prompts":["A god forcefully says \\"power up\\".","The god says \\"power up!\\" again."]}'
    assert validate_prompt(
        correctly_allocated, "chained_multishot", 10, source, multishot_shot_count=2,
    )["valid"]

    moved_to_first_item = '{"prompts":["A god says \\"power up!\\" and repeats \\"power up!\\".","The god remains silent."]}'
    assert not validate_prompt(
        moved_to_first_item, "chained_multishot", 10, source, multishot_shot_count=2,
    )["valid"]


def test_multishot_authors_requested_spanish_dialogue_in_its_scene_beats():
    source = (
        "In scene 1 an influencer explains the Alhambra garden in Spanish. Cut scene to the fountain, where she "
        "explains why the water matters in Spanish. Generate concrete dialogue for both scenes."
    )
    prompt = json.dumps({"prompts": [
        "The influencer (S1) says brightly: <d>[Spanish] Este jardín parece tejido con agua y luz.</d>.",
        "Beside the fountain, the influencer (S1) explains softly: <d>[Spanish] El agua refresca y ordena todo el patio.</d>.",
    ]})
    report = validate_prompt(
        prompt, "chained_multishot", 8, source, multishot_shot_count=2,
    )
    assert report["valid"], report

    missing_tags = json.dumps({"prompts": [
        'The influencer says "Este jardín es precioso."',
        "She silently studies the fountain.",
    ]})
    report = validate_prompt(
        missing_tags, "chained_multishot", 8, source, multishot_shot_count=2,
    )
    assert any("dialogue authoring request" in error.lower() for error in report["errors"])


def test_dialogue_repair_reuses_speaker_id_for_same_named_actor_and_pronoun():
    source = 'The woman says "One." Then she replies "Two."'
    generated = """integrated_multimodal_description:
[Shot 1] The woman says <d>[English] One.</d>. She replies softly <d>[English] Two.</d>.
overall_soundscape: Quiet room tone.
non_diegetic_music: N/A"""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert repaired.count("(S1)") == 2
    assert "replies softly" in repaired


def test_dialogue_repair_moves_a_late_speaker_id_before_the_vocal_action():
    source = 'She replies in Spanish "Hola."'
    generated = """integrated_multimodal_description:
[Shot 1] She replies in a firm, clear tone (S1) <d>[Spanish] Hola.</d>.
overall_soundscape: Quiet room tone.
non_diegetic_music: N/A"""
    repaired = normalize_source_dialogue(generated, source, "t2va")
    assert "She (S1) replies in a firm, clear tone" in repaired
    assert validate_prompt(repaired, "t2va", 5, source)["valid"]


def test_multishot_pipeline_uses_json_contract_and_manifest_v3():
    def completion(_messages):
        return "one fluent prompt\n---\ntwo fluent prompts"

    prompt, report, manifest = enhance_prompt_with_completion(
        "Make two scenes", "chained_multishot", 10.1, "", completion, 0, {"provider": "test"},
        multishot_shot_count=2,
    )
    assert json.loads(prompt)["prompts"] == [
        "one fluent prompt No non-diegetic music is audible.",
        "two fluent prompts No non-diegetic music is audible.",
    ]
    assert report["valid"]
    assert manifest["promptContractVersion"] == 3


def test_request_includes_aspect_frame_and_authoritative_manifest():
    manifest = json.dumps({"items": [{"type": "picture", "role": "first_frame", "analysis": "red coat"}]})
    request = build_user_request("She walks", "auto", 5, aspect_ratio="9:16", media_manifest=manifest, frame_count=90)
    assert "TARGET ASPECT RATIO: 9:16" in request
    assert "TARGET FRAME COUNT: 90" in request
    assert "<Picture 1> has role: first frame; analysis: red coat" in request


def test_media_manifest_validator_node_returns_normalized_context():
    result = MiniMaxH3MediaManifestValidator().validate('{"items":[{"type":"picture","role":"identity"}]}')["result"]
    assert result[1] is True
    assert "<Picture 1>" in result[3]


def test_copied_audio_transcript_can_be_the_vocal_source_without_invented_speaker():
    manifest = json.dumps({"items": [
        {"type": "picture", "role": "identity", "analysis": "woman in red coat"},
        {"type": "audio", "duration": 4, "role": "voice", "reuse_mode": "copied",
         "transcript": {"language": "Spanish", "text": "Hola."}},
    ]})
    prompt = """subject_definitions:
<Subject 1> is the woman in a red coat from <Picture 1>.
<Audio 1> is the copied voice track.
summary:
[reference generation + audio reuse] The woman appears while the copied voice track plays.
retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - identity and red coat remain.
<Audio 1>: partially_copy - the spoken phrase is copied.
detailed_description:
Cinematic live-action. [Shot 1] A medium shot frames <Subject 1>. When <Audio 1> reaches <d>[Spanish] Hola.</d>, she turns without becoming a speaker.
overall_soundscape:
Quiet room tone under the copied voice from <Audio 1>.
non_diegetic_music:
N/A"""
    assert validate_prompt(prompt, "ref2va", 5, media_manifest=manifest)["valid"]


def test_reference_audio_score_is_valid_in_music_section_without_visual_timeline_use():
    context = "<Audio 1> is an audience-only score reference."
    prompt = """subject_definitions:
<Audio 1> is an audience-only score reference.
summary:
[audio reference] The target video uses the referenced audience-only score.
retention_analysis:
<Audio 1>: reference - its instrumentation and rhythm guide the score without copying the signal.
detailed_description:
Cinematic live-action style.
[Shot 1] A wide shot frames an empty station platform in steady rain.
overall_soundscape:
Rain taps the canopy and water drains along the platform edge.
non_diegetic_music:
<Audio 1> is used as the audience-only instrumentation and rhythm reference."""
    assert validate_prompt(prompt, "ref2va", 5, reference_context=context)["valid"]
