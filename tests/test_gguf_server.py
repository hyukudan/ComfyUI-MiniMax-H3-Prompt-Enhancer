# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import subprocess
import sys
import types

import pytest

import gguf_server


VALID_PROMPT = """integrated_multimodal_description: [Shot 1] Live-action, cinematic, a knight crosses a wet alley.

overall_soundscape: Rain falls while armor plates move with each step.

non_diegetic_music: N/A"""


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self.wait_timeouts = []

    def poll(self):
        return 0 if (self.terminated or self.killed) else None

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout):
        self.wait_timeouts.append(timeout)
        return 0


def _paths(tmp_path):
    server = tmp_path / "llama-server.exe"
    server.write_bytes(b"runtime")
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    model = model_dir / "gemma-nvfp4.gguf"
    model.write_bytes(b"GGUF")
    return server, model, model_dir


def _run(monkeypatch, tmp_path, completion, process_holder=None):
    server, model, model_dir = _paths(tmp_path)
    process = FakeProcess()
    if process_holder is not None:
        process_holder.append(process)
    popen_call = {}

    def fake_popen(command, **kwargs):
        popen_call.update({"command": command, **kwargs})
        return process

    monkeypatch.setattr(gguf_server.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(gguf_server, "_loopback_port", lambda: 45678)
    monkeypatch.setattr(
        gguf_server,
        "_wait_until_ready",
        lambda proc, url, timeout, log: (
            proc is process and url == "http://127.0.0.1:45678/health"
        ) or pytest.fail("unexpected readiness arguments"),
    )
    monkeypatch.setattr(gguf_server, "_completion", completion)
    result = gguf_server.enhance_prompt_with_gguf_server(
        "A knight crosses a wet alley. No music.",
        "t2va",
        5.0,
        "",
        str(server),
        str(model),
        str(model_dir),
        -1,
        16384,
        0,
        0.2,
        4096,
        300,
        180,
        0,
        True,
    )
    return result, process, popen_call, server, model


def test_managed_server_is_loopback_only_and_cleaned_up(monkeypatch, tmp_path):
    completion_call = {}

    def completion(*args):
        completion_call["args"] = args
        return VALID_PROMPT

    (result, validation, manifest), process, popen_call, server, model = _run(
        monkeypatch, tmp_path, completion
    )
    assert result == VALID_PROMPT
    assert validation["valid"]
    assert manifest["provider"] == "managed_llama_server"
    assert manifest["serverUnloadedAfterRun"] is True
    assert manifest["loopbackOnly"] is True
    assert process.terminated is True
    assert process.wait_timeouts == [10.0]

    command = popen_call["command"]
    assert command[0] == str(server)
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--port") + 1] == "45678"
    assert command[command.index("--model") + 1] == str(model)
    api_key = command[command.index("--api-key") + 1]
    assert api_key
    assert api_key not in str(manifest)
    assert popen_call["shell"] is False
    assert popen_call["stdin"] is subprocess.DEVNULL
    assert completion_call["args"][0] == "http://127.0.0.1:45678/v1"
    assert completion_call["args"][3] == api_key
    assert completion_call["args"][-1] is False  # Do not probe LM Studio's native endpoint.


def test_managed_server_is_cleaned_up_when_completion_fails(monkeypatch, tmp_path):
    def fail_completion(*_args):
        raise RuntimeError("generation failed")

    processes = []
    with pytest.raises(RuntimeError, match="generation failed"):
        _run(monkeypatch, tmp_path, fail_completion, processes)
    process = processes[0]
    assert process.terminated is True
    assert process.wait_timeouts == [10.0]


def test_managed_server_is_cleaned_up_when_startup_fails(monkeypatch, tmp_path):
    server, model, model_dir = _paths(tmp_path)
    process = FakeProcess()
    monkeypatch.setattr(gguf_server.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(gguf_server, "_loopback_port", lambda: 45678)
    monkeypatch.setattr(
        gguf_server,
        "_wait_until_ready",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("startup failed")),
    )
    with pytest.raises(RuntimeError, match="startup failed"):
        gguf_server.enhance_prompt_with_gguf_server(
            "prompt", "t2va", 5.0, "", str(server), str(model), str(model_dir),
            0, 4096, 1, 0.0, 512, 30, 10, 0,
        )
    assert process.terminated is True


def test_gguf_must_be_under_a_registered_root(tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    with pytest.raises(ValueError, match="outside registered model directories"):
        gguf_server.validate_gguf_path(str(model), str(unrelated))


def test_standard_lm_studio_cache_is_a_registered_model_root():
    expected = gguf_server.Path.home() / ".cache" / "lm-studio" / "models"
    assert expected.resolve() in gguf_server.registered_model_roots()


def test_discovery_lists_comfy_gguf_models_and_llama_server(monkeypatch, tmp_path):
    llm_root = tmp_path / "llm_gguf"
    llm_root.mkdir()
    model = llm_root / "model.gguf"
    model.write_bytes(b"GGUF")
    (llm_root / "mmproj-model.gguf").write_bytes(b"GGUF")
    server = tmp_path / "prompt_enhancers" / "runtimes" / "llama" / "llama-server.exe"
    server.parent.mkdir(parents=True)
    server.write_bytes(b"runtime")
    monkeypatch.setitem(sys.modules, "folder_paths", types.SimpleNamespace(
        models_dir=str(tmp_path), folder_names_and_paths={},
    ))
    assert gguf_server.available_gguf_models() == [str(model.resolve())]
    assert gguf_server.available_llama_servers() == [str(server.resolve())]


def test_server_path_rejects_arbitrary_executables(tmp_path):
    executable = tmp_path / "something-else.exe"
    executable.write_bytes(b"binary")
    with pytest.raises(ValueError, match="llama-server"):
        gguf_server.validate_llama_server_path(str(executable))


def test_stop_server_kills_process_that_ignores_terminate():
    class StuckProcess(FakeProcess):
        def poll(self):
            return 0 if self.killed else None

        def wait(self, timeout):
            self.wait_timeouts.append(timeout)
            if not self.killed:
                raise subprocess.TimeoutExpired("llama-server", timeout)
            return 0

    process = StuckProcess()
    gguf_server._stop_server(process, shutdown_timeout=0.01)
    assert process.terminated is True
    assert process.killed is True
    assert process.wait_timeouts == [0.01, 0.01]


def test_persistent_server_is_reused_until_explicit_unload(monkeypatch, tmp_path):
    gguf_server.unload_cached_server()
    server, model, model_dir = _paths(tmp_path)
    process = FakeProcess()
    launches = []

    def fake_popen(command, **kwargs):
        launches.append((command, kwargs))
        return process

    monkeypatch.setattr(gguf_server.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(gguf_server, "_loopback_port", lambda: 45678)
    monkeypatch.setattr(gguf_server, "_wait_until_ready", lambda *_args: None)
    monkeypatch.setattr(gguf_server, "_completion", lambda *_args: VALID_PROMPT)
    args = (
        "A knight crosses a wet alley. No music.", "t2va", 5.0, "", str(server), str(model),
        str(model_dir), "all", 16384, 0, 0.2, 4096, 300, 180, 0, True, True,
    )
    first = gguf_server.enhance_prompt_with_gguf_server(*args)
    second = gguf_server.enhance_prompt_with_gguf_server(*args)
    assert len(launches) == 1
    assert first[2]["serverReused"] is False
    assert second[2]["serverReused"] is True
    assert process.terminated is False
    assert gguf_server.unload_cached_server() is True
    assert process.terminated is True
