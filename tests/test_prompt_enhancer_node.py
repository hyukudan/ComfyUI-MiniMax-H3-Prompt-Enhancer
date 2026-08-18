# SPDX-License-Identifier: GPL-3.0-only

import json
import math

import prompt_enhancer_node
from prompt_enhancer_node import (
    MiniMaxH3GGUFPromptEnhancer,
    MiniMaxH3PromptEnhancer,
    MiniMaxH3PromptGuideBuilder,
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
    assert MiniMaxH3PromptEnhancer.RETURN_NAMES[-5:] == (
        "duration_seconds", "aspect_ratio", "treatment_warnings", "width", "height",
    )
    assert MiniMaxH3PromptEnhancer.RETURN_TYPES[-5:] == ("FLOAT", "STRING", "STRING", "INT", "INT")


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


def test_always_re_enhance_is_appended_last_to_keep_saved_widget_order():
    for node in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer):
        optional = node.INPUT_TYPES()["optional"]
        assert list(optional)[-7:] == ["always_re_enhance", "delivery_target", "dialogue_language", "visual_style_preset", "target_megapixels", "editing_intent", "lora_trigger_words"]
        assert optional["always_re_enhance"][0] == "BOOLEAN"
        assert optional["always_re_enhance"][1]["default"] is False
        assert optional["editing_intent"][0] == list(prompt_enhancer_node.EDITING_INTENT_CHOICES)
        assert optional["editing_intent"][1]["default"] == "none"
    assert "always_re_enhance" not in MiniMaxH3PromptEnhancer.INPUT_TYPES()["required"]


def test_api_key_widget_documents_the_environment_variable_fallback():
    tooltip = MiniMaxH3PromptEnhancer.INPUT_TYPES()["required"]["api_key"][1]["tooltip"]
    assert "MINIMAX_H3_PROMPT_ENHANCER_API_KEY" in tooltip
    assert "no longer saved into workflow" in tooltip


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
