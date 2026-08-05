# SPDX-License-Identifier: GPL-3.0-only

import json

import prompt_enhancer_node
from prompt_enhancer_node import MiniMaxH3PromptEnhancer, MiniMaxH3PromptGuideBuilder


VALIDATION = {"valid": True, "errors": [], "mode": "t2va"}


def test_guide_builder_can_feed_an_existing_llm_node():
    system, user, mode = MiniMaxH3PromptGuideBuilder().build(
        'A detective enters a ramen shop and says "Good evening."', "t2va", 5.0, "",
    )
    assert "MiniMax H3" in system
    assert "TARGET DURATION: 5.000 seconds" in user
    assert '"Good evening."' in user
    assert mode == "t2va"


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
    assert captured["args"][-1] is True


def test_main_enhancer_exposes_backend_toggle_and_duration_output(monkeypatch):
    monkeypatch.setattr(prompt_enhancer_node, "available_gguf_models", lambda: ["model.gguf"])
    monkeypatch.setattr(prompt_enhancer_node, "available_llama_servers", lambda: ["llama-server"])
    inputs = MiniMaxH3PromptEnhancer.INPUT_TYPES()["optional"]
    assert inputs["use_remote_model"][1]["default"] is True
    assert inputs["enhance_description"][1]["default"] is True
    assert inputs["local_model"][0] == ["model.gguf"]
    assert inputs["llama_server_path"][0] == ["llama-server"]
    assert inputs["keep_server_loaded"][1]["default"] is False
    assert MiniMaxH3PromptEnhancer.RETURN_NAMES[-1] == "duration_seconds"
    assert MiniMaxH3PromptEnhancer.RETURN_TYPES[-1] == "FLOAT"


def test_main_enhancer_allows_stale_hidden_dynamic_combo_values():
    assert MiniMaxH3PromptEnhancer.VALIDATE_INPUTS(
        local_model="stale-model.gguf",
        llama_server_path="stale-llama-server.exe",
    ) is True
