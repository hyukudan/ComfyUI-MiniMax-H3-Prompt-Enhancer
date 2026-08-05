# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json

import pytest

import prompt_enhancer


VALID_PROMPT = """integrated_multimodal_description: [Shot 1] Live-action, cinematic, a knight crosses a wet alley.

overall_soundscape: Rain falls while armor plates move with each step.

non_diegetic_music: N/A"""


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_enhancer_auto_discovers_model_and_never_puts_api_key_in_manifest(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        if request.full_url.endswith("/models"):
            return FakeResponse({"data": [{"id": "local-qwen"}]})
        if request.full_url.endswith("/api/v1/chat"):
            return FakeResponse({"output": [{"type": "message", "content": VALID_PROMPT}]})
        return FakeResponse({"choices": [{"message": {"content": VALID_PROMPT}}]})

    monkeypatch.setattr(prompt_enhancer, "urlopen", fake_urlopen)
    result, validation, manifest = prompt_enhancer.enhance_prompt(
        "A knight crosses a wet alley. No music.", "t2va", 5.0, "",
        "http://127.0.0.1:1234/v1", "", "super-secret", 0.2, 4096, 30, 1, False,
    )
    assert result == VALID_PROMPT
    assert validation["valid"]
    assert manifest["model"] == "local-qwen"
    assert "super-secret" not in json.dumps(manifest)
    assert len(calls) == 2


def test_auto_model_skips_embeddings_and_prefers_compact_instruct_model(monkeypatch):
    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/models"):
            return FakeResponse({"data": [
                {"id": "text-embedding-nomic-embed-text-v1.5"},
                {"id": "qwen3.6-27b"},
                {"id": "gemma-4-e4b-it-ultra-uncensored-heretic-nvfp4"},
            ]})
        if request.full_url.endswith("/api/v1/chat"):
            return FakeResponse({"output": [{"type": "message", "content": VALID_PROMPT}]})
        return FakeResponse({"choices": [{"message": {"content": VALID_PROMPT}}]})

    monkeypatch.setattr(prompt_enhancer, "urlopen", fake_urlopen)
    _result, _validation, manifest = prompt_enhancer.enhance_prompt(
        "A knight crosses a wet alley. No music.", "t2va", 5.0, "",
        "http://127.0.0.1:1234/v1", "", "", 0.2, 4096, 30, 0, False,
    )
    assert manifest["model"] == "gemma-4-e4b-it-ultra-uncensored-heretic-nvfp4"


def test_remote_endpoint_requires_explicit_opt_in():
    with pytest.raises(ValueError, match="Remote LLM endpoints are disabled"):
        prompt_enhancer.enhance_prompt(
            "A basic prompt", "t2va", 5.0, "", "https://example.com/v1", "model", "", 0.2,
            4096, 30, 0, False,
        )


def test_one_repair_attempt_fixes_invalid_first_completion(monkeypatch):
    payloads = iter([
        {"output": [{"type": "message", "content": "not structured"}]},
        {"output": [{"type": "message", "content": VALID_PROMPT}]},
    ])
    monkeypatch.setattr(prompt_enhancer, "urlopen", lambda *_args, **_kwargs: FakeResponse(next(payloads)))
    _result, validation, manifest = prompt_enhancer.enhance_prompt(
        "A knight crosses a wet alley. No music.", "t2va", 5.0, "",
        "http://localhost:8000/v1", "already-loaded", "", 0.2, 4096, 30, 1, False,
    )
    assert validation["valid"]
    assert manifest["repairAttemptsUsed"] == 1


def test_native_lm_studio_request_turns_reasoning_off(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured.update(json.loads(request.data.decode("utf-8")))
        return FakeResponse({"output": [{"type": "message", "content": VALID_PROMPT}]})

    monkeypatch.setattr(prompt_enhancer, "urlopen", fake_urlopen)
    result = prompt_enhancer._completion(
        "http://127.0.0.1:1234/v1", "qwen", [{"role": "system", "content": "rules"},
        {"role": "user", "content": "request"}], "", 0.1, 500, 30, True,
    )
    assert result == VALID_PROMPT
    assert captured["reasoning"] == "off"
    assert captured["store"] is False


def test_pipeline_restores_omitted_catalan_dialogue_before_validation():
    source = (
        'Luffy enters a restaurant and asks in catalonian language '
        '"A ver, cabrones, quiero flaó de ese".'
    )
    omitted = """integrated_multimodal_description:
[Shot 1] Live-action Luffy enters a restaurant in Ibiza with an arrogant expression.

overall_soundscape:
Restaurant chatter and clinking dishes.

non_diegetic_music:
N/A"""
    result, validation, _manifest = prompt_enhancer.enhance_prompt_with_completion(
        source, "t2va", 5.0, "", lambda _messages: omitted, 0, {"provider": "test"},
    )
    assert '<d>[Catalan] A ver, cabrones, quiero flaó de ese</d>' in result
    assert validation["valid"]
