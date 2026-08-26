# SPDX-License-Identifier: GPL-3.0-only

import json
import math

import prompt_enhancer_node
from prompt_enhancer_node import (
    MiniMaxH3GGUFPromptEnhancer,
    MiniMaxH3PromptEnhancer,
    MiniMaxH3PromptGuideBuilder,
    MiniMaxH3VisualReferenceDirector,
    MiniMaxH3ReferenceProjectInspector,
    MiniMaxH3UnloadGGUFServer,
)


VALIDATION = {"valid": True, "errors": [], "mode": "t2va"}


def test_guide_builder_can_feed_an_existing_llm_node():
    system, user, mode, warnings, width, height = MiniMaxH3PromptGuideBuilder().build(
        'A detective enters a ramen shop and says "Good evening."', "t2va", 5.0, "",
    )
    assert "MiniMax H3" in system
    assert "TARGET DURATION: 5.000 seconds" in user
    assert '"Good evening."' in user
    assert mode == "t2va"
    assert warnings == ""
    assert width == 1280
    assert height == 720


def test_main_enhancer_preserves_remote_defaults_and_appends_duration(monkeypatch):
    captured = {}

    def fake_remote(*args, **kwargs):
        captured["args"] = args
        return "remote prompt", VALIDATION, {"provider": "remote"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt", fake_remote)
    result = MiniMaxH3PromptEnhancer().enhance(
        "idea", "t2va", 7.5, "", "http://127.0.0.1:1234/v1", "model", "", 0.2,
        4096, 300, 1, True, False,
    )
    assert result[0] == "remote prompt"
    assert json.loads(result[1])["valid"] is True
    assert result[3] == 7.5
    assert captured["args"][4] == "http://127.0.0.1:1234/v1"


def test_main_enhancer_uses_dropdown_gguf_when_remote_is_disabled(monkeypatch, tmp_path):
    model = tmp_path / "local.gguf"
    server = tmp_path / "llama-server.exe"
    captured = {}

    def fake_gguf(*args, **kwargs):
        captured["args"] = args
        return "local prompt", VALIDATION, {"provider": "managed_llama_server"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    monkeypatch.setattr(
        prompt_enhancer_node,
        "enhance_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("remote backend must not run")),
    )
    result = MiniMaxH3PromptEnhancer().enhance(
        "idea", "t2va", 6.0, "", "ignored endpoint", "ignored model", "", 0.2,
        2048, 300, 0, True, False, False, str(model), str(server), "all", 8192, 4, 90, True,
    )
    assert result[0] == "local prompt"
    assert result[3] == 6.0
    assert captured["args"][4] == str(server)
    assert captured["args"][5] == str(model)
    assert captured["args"][-5] is True
    assert captured["args"][-4:] == ("auto", "follow_prompt", "audible", "")


def test_main_enhancer_exposes_backend_toggle_and_duration_output(monkeypatch):
    monkeypatch.setattr(prompt_enhancer_node, "available_gguf_models", lambda: ["model.gguf"])
    monkeypatch.setattr(prompt_enhancer_node, "available_llama_servers", lambda: ["llama-server"])
    inputs = MiniMaxH3PromptEnhancer.INPUT_TYPES()["optional"]
    assert inputs["use_remote_model"][1]["default"] is True
    assert inputs["creative_latitude"][1]["default"] == "enhanced_production"
    assert inputs["ambience_foley_policy"][0] == ["auto", "ensure_audible", "off"]
    assert inputs["background_score_policy"][0] == ["follow_prompt", "add_instrumental", "off"]
    assert inputs["instrumental_description"][1]["multiline"] is True
    assert inputs["instrumental_style"][1]["default"] == "none"
    assert "jazz" in inputs["instrumental_style"][0]
    assert "horror_tension" in inputs["instrumental_style"][0]
    assert "action_cinematic" in inputs["instrumental_style"][0]
    assert "mystery_investigation" in inputs["instrumental_style"][0]
    assert "suspense_build" in inputs["instrumental_style"][0]
    assert "combat_rhythmic" in inputs["instrumental_style"][0]
    assert "chinese_martial_arts" in inputs["instrumental_style"][0]
    assert "horror_intense" in inputs["instrumental_style"][0]
    assert inputs["voice_performance"][0][-1] == "none"
    assert inputs["local_model"][0] == ["model.gguf"]
    assert inputs["llama_server_path"][0] == ["llama-server"]
    assert inputs["keep_server_loaded"][1]["default"] is False
    assert MiniMaxH3PromptEnhancer.RETURN_NAMES[3:8] == (
        "duration_seconds", "aspect_ratio", "treatment_warnings", "width", "height",
    )
    assert MiniMaxH3PromptEnhancer.RETURN_TYPES[3:8] == ("FLOAT", "STRING", "STRING", "INT", "INT")
    assert MiniMaxH3PromptEnhancer.RETURN_NAMES[8:13] == (
        "reference_project", "pictures", "videos", "audios", "reference_project_json",
    )
    assert MiniMaxH3PromptEnhancer.RETURN_NAMES[13:] == (
        *(f"ref_image_{index}" for index in range(1, 10)),
        *(f"ref_video_{index}" for index in range(1, 4)),
        *(f"ref_video_audio_{index}" for index in range(1, 4)),
        *(f"ref_audio_{index}" for index in range(1, 4)),
    )


def test_specialized_gguf_node_accepts_current_comfyui_keyword_inputs(monkeypatch):
    captured = {}

    def fake_gguf(*args, **kwargs):
        captured["args"] = args
        return "local prompt", VALIDATION, {"provider": "managed_llama_server"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    result = MiniMaxH3GGUFPromptEnhancer().enhance(
        basic_prompt="idea",
        mode="t2va",
        duration_seconds=5.0,
        reference_context="",
        llama_server_path="llama-server.exe",
        gguf_model_path="model.gguf",
        registered_model_dirs="",
        gpu_layers="auto",
        context_size=16384,
        threads=0,
        temperature=0.2,
        max_tokens=4096,
        request_timeout=300,
        startup_timeout=180,
        repair_attempts=0,
        disable_thinking=True,
        creative_latitude="conservative_grounded",
        keep_server_loaded=False,
    )

    assert result[0] == "local prompt"
    assert captured["args"][16:18] == (False, False)


def test_empty_multiline_controls_expose_non_serialized_ux_placeholders():
    inputs = MiniMaxH3PromptEnhancer.INPUT_TYPES()
    required = inputs["required"]
    optional = inputs["optional"]
    assert "Describe the video" in required["basic_prompt"][1]["placeholder"]
    assert "Picture 1" in required["reference_context"][1]["placeholder"]
    assert "90 BPM" in optional["instrumental_description"][1]["placeholder"]
    assert '"items"' in optional["media_manifest"][1]["placeholder"]
    assert "Identity" in optional["multishot_identity_lock"][1]["placeholder"]
    for field in ("basic_prompt", "reference_context"):
        assert required[field][1]["default"] == ""
    for field in ("instrumental_description", "media_manifest", "multishot_identity_lock"):
        assert optional[field][1]["default"] == ""


def test_main_enhancer_allows_stale_hidden_dynamic_combo_values():
    assert MiniMaxH3PromptEnhancer.VALIDATE_INPUTS(
        local_model="stale-model.gguf",
        llama_server_path="stale-llama-server.exe",
    ) is True


def test_zero_filled_local_runtime_widgets_migrate_to_safe_defaults(monkeypatch):
    captured = {}

    def fake_gguf(*args, **kwargs):
        captured["args"] = args
        return "local prompt", VALIDATION, {"provider": "managed_llama_server"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    result = MiniMaxH3PromptEnhancer().enhance(
        "idea", "t2va", 5.0, "", "", "", "", 0.2, 4096, 300, 1,
        True, False, False, "model.gguf", "llama-server.exe", "auto", 0, 0, 0, False,
    )
    assert result[0] == "local prompt"
    assert captured["args"][8] == prompt_enhancer_node.DEFAULT_LOCAL_CONTEXT_SIZE
    assert captured["args"][13] == prompt_enhancer_node.DEFAULT_LOCAL_STARTUP_TIMEOUT


def test_local_runtime_zero_is_accepted_as_an_auto_migration_value():
    optional = MiniMaxH3PromptEnhancer.INPUT_TYPES()["optional"]
    assert optional["context_size"][1]["min"] == 0
    assert optional["startup_timeout"][1]["min"] == 0


def test_non_numeric_shifted_local_runtime_values_fall_back_safely():
    assert prompt_enhancer_node._local_runtime_limits(
        r"D:\models\llama-server.exe", "follow_prompt",
    ) == (prompt_enhancer_node.DEFAULT_LOCAL_CONTEXT_SIZE,
          prompt_enhancer_node.DEFAULT_LOCAL_STARTUP_TIMEOUT)


def test_identical_inputs_reuse_the_cached_enhancement():
    inputs = {"basic_prompt": "a knight", "mode": "t2va", "duration_seconds": 5.0, "repair_attempts": 2}
    digest = MiniMaxH3PromptEnhancer.IS_CHANGED(**inputs)
    assert digest == MiniMaxH3PromptEnhancer.IS_CHANGED(**inputs)
    assert len(digest) == 64
    assert digest != MiniMaxH3PromptEnhancer.IS_CHANGED(**{**inputs, "basic_prompt": "a pirate"})
    assert digest == MiniMaxH3GGUFPromptEnhancer.IS_CHANGED(**inputs)


def test_input_digest_ignores_keyword_ordering():
    assert MiniMaxH3PromptEnhancer.IS_CHANGED(
        basic_prompt="a knight", mode="t2va", duration_seconds=5.0,
    ) == MiniMaxH3PromptEnhancer.IS_CHANGED(
        duration_seconds=5.0, mode="t2va", basic_prompt="a knight",
    )


def test_missing_and_unserializable_inputs_still_produce_a_digest():
    assert len(MiniMaxH3PromptEnhancer.IS_CHANGED()) == 64
    unserializable = MiniMaxH3PromptEnhancer.IS_CHANGED(media_manifest=frozenset(("picture",)))
    assert unserializable == MiniMaxH3PromptEnhancer.IS_CHANGED(media_manifest=frozenset(("picture",)))
    assert unserializable != MiniMaxH3PromptEnhancer.IS_CHANGED()


def test_always_re_enhance_restores_the_uncacheable_nan_marker():
    for node in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer):
        marker = node.IS_CHANGED(basic_prompt="a knight", always_re_enhance=True)
        assert math.isnan(marker)
        assert marker != marker
    assert math.isnan(MiniMaxH3UnloadGGUFServer.IS_CHANGED(unload=True))


def test_new_controls_are_appended_without_shifting_saved_widget_order():
    for node in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer):
        optional = node.INPUT_TYPES()["optional"]
        expected_tail = ["always_re_enhance", "delivery_target", "dialogue_language", "visual_style_preset", "target_megapixels", "editing_intent", "lora_trigger_words"]
        if node is MiniMaxH3PromptEnhancer:
            expected_tail += ["title_sequence_recipe", "title_sequence_energy", "title_text", "credit_lines", "title_placement"]
        expected_tail += ["reference_director_json", "generation_id", "studio_project_json"]
        assert list(optional)[-len(expected_tail):] == expected_tail
        assert optional["always_re_enhance"][0] == "BOOLEAN"
        assert optional["always_re_enhance"][1]["default"] is False
        assert optional["editing_intent"][0] == list(prompt_enhancer_node.EDITING_INTENT_CHOICES)
        assert optional["editing_intent"][1]["default"] == "none"
    assert "always_re_enhance" not in MiniMaxH3PromptEnhancer.INPUT_TYPES()["required"]


def test_visual_reference_director_and_inspector_preserve_h3_order(monkeypatch):
    media = {
        "schemaVersion": 2, "mode": "ref2va",
        "assets": [{"id": "ana", "type": "picture", "name": "Ana"}],
        "subjects": [{"id": "subject.1", "h3Index": 1, "name": "Ana", "identityAssetIds": ["ana"]}], "environments": [],
        "generations": [{"id": "g1", "order": 1, "bindings": [{"assetId": "ana", "slotIndex": 1}], "subjectStates": [], "environmentStates": []}],
    }
    director = {
        "format": "minimax-h3-reference-director", "formatVersion": 1,
        "sources": {"ana": {
            "storage": "comfy_input", "file": "minimax_h3_reference_director/ana.webp [input]",
            "sha256": "a" * 64, "mediaType": "picture", "originalName": "ana.webp",
            "sizeBytes": 42, "mimeType": "image/webp",
        }},
    }
    monkeypatch.setattr(prompt_enhancer_node, "load_generation_media", lambda *_args, **_kwargs: {
        "generationId": "g1", "pictures": ["picture-tensor"], "videos": [], "audios": [],
    })
    reference_project, context, pictures_out, videos_out, audios_out, builder_report, bundle_json = MiniMaxH3VisualReferenceDirector().build(
        json.dumps(director), json.dumps(media), "",
    )
    assert reference_project["inputsByGeneration"]["g1"][0]["label"] == "<Picture 1>"
    assert json.loads(bundle_json)["digest"] == reference_project["digest"]
    assert "AUTHORITATIVE REFERENCE RELATIONSHIPS" in context
    assert "<Picture 1> supplies only the stable visual identity of Ana" in context
    assert pictures_out == ["picture-tensor"]
    assert videos_out == []
    assert audios_out == []
    assert "1 physical sources" in builder_report
    project_json, report, pictures, videos, audios = MiniMaxH3ReferenceProjectInspector().inspect(reference_project)
    assert json.loads(project_json)["digest"] == reference_project["digest"]
    assert "<Picture 1> ← ana" in report
    assert json.loads(pictures) == ["minimax_h3_reference_director/ana.webp [input]"]
    assert json.loads(videos) == []
    assert json.loads(audios) == []


def test_prompt_enhancer_natively_compiles_and_emits_its_compose_references(monkeypatch):
    media = {
        "schemaVersion": 2, "mode": "ref2va",
        "assets": [{"id": "ana", "type": "picture", "name": "Ana"}],
        "subjects": [{"id": "subject.1", "h3Index": 1, "name": "Ana", "identityAssetIds": ["ana"]}],
        "environments": [],
        "generations": [{"id": "g1", "order": 1, "bindings": [
            {"assetId": "ana", "slotIndex": 1}
        ], "subjectStates": [], "environmentStates": []}],
    }
    director = {
        "format": "minimax-h3-reference-director", "formatVersion": 1,
        "sources": {"ana": {
            "storage": "comfy_input", "file": "minimax_h3_reference_director/ana.webp [input]",
            "sha256": "a" * 64, "mediaType": "picture", "originalName": "ana.webp",
            "sizeBytes": 42, "mimeType": "image/webp",
        }},
    }
    captured = {}
    monkeypatch.setattr(prompt_enhancer_node, "load_generation_media", lambda *_args, **_kwargs: {
        "generationId": "g1", "pictures": ["ana-tensor"], "videos": [], "audios": [],
    })
    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt", lambda *args, **_kwargs: (
        captured.setdefault("context", args[3]) and "prompt",
        {"valid": True, "errors": [], "mode": "ref2va"},
        {"provider": "test"},
    ))
    result = MiniMaxH3PromptEnhancer().enhance(
        "Ana enters the room", "auto", 5.0, "manual production note",
        "http://127.0.0.1:1234/v1", "model", "", 0.2, 4096, 300, 0, True, False,
        media_manifest=json.dumps(media), reference_director_json=json.dumps(director), generation_id="g1",
    )
    assert "AUTHORITATIVE REFERENCE RELATIONSHIPS" in captured["context"]
    assert "manual production note" in captured["context"]
    assert result[8]["inputsByGeneration"]["g1"][0]["assetId"] == "ana"
    assert result[9:12] == (["ana-tensor"], [], [])
    assert json.loads(result[12])["digest"] == result[8]["digest"]


def test_compose_shots_supply_basic_prompt_when_manual_text_is_blank():
    studio = {
        "schemaVersion": 3,
        "project": {
            "name": "Visual-only prompt", "mode": "t2va", "timingMode": "auto",
            "look": {
                "creativeTreatment": {"schemaVersion": 2},
                "cinematography": {"schemaVersion": 2},
            },
        },
        "files": [],
        "subjects": [{
            "id": "ana", "name": "Ana", "description": "A woman with dark hair.",
            "identityFileIds": [],
        }],
        "environments": [],
        "generations": [{"id": "g1", "order": 1}],
        "shots": [{
            "id": "s1", "generationId": "g1", "action": "Ana opens the door.",
            "cast": [{"subjectId": "ana", "presence": "present"}],
            "actionBeats": [{
                "id": "b1", "at": 0.5,
                "dialogue": {"speakerId": "ana", "delivery": "whispers", "text": "Ya estoy aquí."},
            }],
        }],
        "links": [],
    }

    resolved = prompt_enhancer_node._studio_runtime_inputs(
        studio_project_json=json.dumps(studio), basic_prompt="",
    )

    assert resolved["basic_prompt"] == "Ana opens the door. Ana whispers “Ya estoy aquí.”"


def test_manual_basic_prompt_remains_authoritative_over_compose_summary():
    studio = {
        "schemaVersion": 3,
        "project": {"name": "Manual", "mode": "t2va", "timingMode": "auto", "look": {}},
        "files": [], "subjects": [], "environments": [],
        "generations": [{"id": "g1", "order": 1}],
        "shots": [{"id": "s1", "generationId": "g1", "action": "Visual action."}],
        "links": [],
    }

    resolved = prompt_enhancer_node._studio_runtime_inputs(
        studio_project_json=json.dumps(studio), basic_prompt="Manual direction.",
    )

    assert resolved["basic_prompt"] == "Manual direction."


def test_api_key_widget_documents_the_environment_variable_fallback():
    tooltip = MiniMaxH3PromptEnhancer.INPUT_TYPES()["required"]["api_key"][1]["tooltip"]
    assert "MINIMAX_H3_PROMPT_ENHANCER_API_KEY" in tooltip
    assert "no longer saved into workflow" in tooltip


def test_numbered_reference_outputs_match_native_h3_slot_order():
    outputs = prompt_enhancer_node._numbered_reference_outputs({
        "pictures": ["image"], "videos": ["video"],
        "videoAudios": ["video-audio"], "standaloneAudios": ["audio"],
    })
    assert len(outputs) == 18
    assert outputs[0] == "image"
    assert outputs[9] == "video"
    assert outputs[12] == "video-audio"
    assert outputs[15] == "audio"
    assert outputs[1:9] == (None,) * 8


def test_enhance_accepts_the_caching_flag_without_changing_the_result(monkeypatch):
    monkeypatch.setattr(
        prompt_enhancer_node, "enhance_prompt",
        lambda *_args, **_kwargs: ("remote prompt", VALIDATION, {"provider": "remote"}),
    )
    result = MiniMaxH3PromptEnhancer().enhance(
        "idea", "t2va", 7.5, "", "http://127.0.0.1:1234/v1", "model", "", 0.2,
        4096, 300, 1, True, False, always_re_enhance=True,
    )
    assert result[0] == "remote prompt"
    assert result[6] == 1280
    assert result[7] == 720


def test_h3_dimensions_for_various_aspect_ratios_and_megapixels():
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("16:9") == (1280, 720)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("9:16") == (720, 1280)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("1:1") == (1080, 1080)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("4:3") == (960, 720)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("3:4") == (720, 960)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("21:9") == (1680, 720)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("auto") == (1280, 720)
    # Custom Megapixel scaling (0.2, 0.3, 0.5, 2.0 MP)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("16:9", 0.2) == (592, 336)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("16:9", 0.3) == (736, 416)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("16:9", 0.5) == (944, 528)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("16:9", 2.0) == (1888, 1056)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("9:16", 0.3) == (416, 736)
    assert prompt_enhancer_node.h3_dimensions_for_aspect_ratio("1:1", 0.5) == (704, 704)


def test_visual_style_preset_merges_into_guide_builder():
    _sys, req, _mode, _warn, w, h = MiniMaxH3PromptGuideBuilder().build(
        "A samurai stands in rain.", "t2va", 5.0, "",
        visual_style_preset="anime_ultradetailed_cinematic",
        aspect_ratio="9:16",
    )
    assert w == 720 and h == 1280
    assert "visualLanguage:anime_ultradetailed_cinematic" in req or "Anime" in req or "cel" in req.lower() or "line" in req.lower()


def test_editing_intent_in_guide_builder():
    _sys, req, resolved_mode, _warn, _w, _h = MiniMaxH3PromptGuideBuilder().build(
        "Change the character walking into the room.", "auto", 6.0,
        reference_context="Video 1 is the walking motion. Picture 1 is the new character.",
        editing_intent="character_swap",
    )
    assert resolved_mode == "ref2va"
    assert "CHARACTER / ACTOR SWAP" in req
    assert "weak_reference" in req
    assert "[video editing + character swap]" in req or "character swap" in req.lower()
