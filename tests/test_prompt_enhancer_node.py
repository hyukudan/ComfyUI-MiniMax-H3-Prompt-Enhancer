# SPDX-License-Identifier: GPL-3.0-only

import json

import prompt_enhancer_node
from prompt_enhancer_node import MiniMaxH3PromptEnhancer, MiniMaxH3PromptGuideBuilder


VALIDATION = {"valid": True, "errors": [], "mode": "t2va"}


def test_guide_builder_can_feed_an_existing_llm_node():
    system, user, mode, warnings = MiniMaxH3PromptGuideBuilder().build(
        'A detective enters a ramen shop and says "Good evening."', "t2va", 5.0, "",
    )
    assert "MiniMax H3" in system
    assert "TARGET DURATION: 5.000 seconds" in user
    assert '"Good evening."' in user
    assert mode == "t2va"
    assert warnings == ""


def test_main_enhancer_preserves_remote_defaults_and_appends_duration(monkeypatch):
    captured = {}

    def fake_remote(*args):
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

    def fake_gguf(*args):
        captured["args"] = args
        return "local prompt", VALIDATION, {"provider": "managed_llama_server"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    monkeypatch.setattr(
        prompt_enhancer_node,
        "enhance_prompt",
        lambda *_args: (_ for _ in ()).throw(AssertionError("remote backend must not run")),
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
    assert inputs["enhance_description"][1]["default"] is True
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
    assert MiniMaxH3PromptEnhancer.RETURN_NAMES[-3:] == (
        "duration_seconds", "aspect_ratio", "treatment_warnings",
    )
    assert MiniMaxH3PromptEnhancer.RETURN_TYPES[-3:] == ("FLOAT", "STRING", "STRING")


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

    def fake_gguf(*args):
        captured["args"] = args
        return "local prompt", VALIDATION, {"provider": "managed_llama_server"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    result = MiniMaxH3PromptEnhancer().enhance(
        "idea", "t2va", 5.0, "", "", "", "", 0.2, 4096, 300, 1,
        True, False, False, "model.gguf", "llama-server.exe", "auto", 0, 0, 0, False,
    )
    assert result[0] == "local prompt"
    assert captured["args"][8] == 16384
    assert captured["args"][13] == 180


def test_local_runtime_zero_is_accepted_as_an_auto_migration_value():
    optional = MiniMaxH3PromptEnhancer.INPUT_TYPES()["optional"]
    assert optional["context_size"][1]["min"] == 0
    assert optional["startup_timeout"][1]["min"] == 0


def test_non_numeric_shifted_local_runtime_values_fall_back_safely():
    assert prompt_enhancer_node._local_runtime_limits(
        r"D:\models\llama-server.exe", "follow_prompt",
    ) == (16384, 180)
