# SPDX-License-Identifier: GPL-3.0-only
"""Managed llama-server backend for existing local GGUF models."""

from __future__ import annotations

import os
import atexit
import secrets
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .prompt_enhancer import _completion, enhance_prompt_with_completion
except ImportError:  # pragma: no cover - direct test/import compatibility
    from prompt_enhancer import _completion, enhance_prompt_with_completion


_SERVER_NAMES = {"llama-server", "llama-server.exe"}
_SERVER_MODEL_ALIAS = "minimax-h3-managed-gguf"
NO_GGUF_MODELS = "(no GGUF models found)"
NO_LLAMA_SERVER = "(llama-server not found)"
_SERVER_LOCK = threading.RLock()
_CACHED_SERVER = None


def _split_roots(value: str) -> list[str]:
    return [item.strip() for item in str(value).replace("\n", os.pathsep).split(os.pathsep) if item.strip()]


def registered_model_roots(additional_roots: str = "") -> list[Path]:
    """Return normalized model roots known to ComfyUI or explicitly registered by the user."""
    candidates: list[str | os.PathLike] = []
    try:
        import folder_paths

        candidates.append(folder_paths.models_dir)
        for paths, _extensions in folder_paths.folder_names_and_paths.values():
            candidates.extend(paths)
    except ImportError:
        pass

    # LM Studio's cache is a model directory, not a runtime dependency.
    candidates.append(Path.home() / ".cache" / "lm-studio" / "models")
    candidates.extend(_split_roots(os.getenv("MINIMAX_H3_GGUF_MODEL_DIRS", "")))
    candidates.extend(_split_roots(additional_roots))

    roots: list[Path] = []
    for candidate in candidates:
        try:
            root = Path(candidate).expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if root not in roots:
            roots.append(root)
    return roots


def available_gguf_models() -> list[str]:
    """Discover text GGUF files in ComfyUI's dedicated LLM directory."""
    candidates: list[Path] = []
    try:
        import folder_paths

        candidates.append(Path(folder_paths.models_dir) / "llm_gguf")
    except ImportError:
        pass
    configured = os.getenv("MINIMAX_H3_GGUF_MODEL_DIRS", "")
    candidates.extend(Path(item).expanduser() for item in _split_roots(configured))
    models: list[str] = []
    for root in candidates:
        if not root.is_dir():
            continue
        for path in root.rglob("*.gguf"):
            if path.is_file() and "mmproj" not in path.name.lower():
                resolved = str(path.resolve())
                if resolved not in models:
                    models.append(resolved)
    return sorted(models, key=str.casefold) if models else [NO_GGUF_MODELS]


def available_llama_servers() -> list[str]:
    """Discover explicitly configured, PATH, and ComfyUI-managed llama-server executables."""
    candidates: list[Path] = []
    configured = os.getenv("MINIMAX_H3_LLAMA_SERVER", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    executable = shutil.which("llama-server") or shutil.which("llama-server.exe")
    if executable:
        candidates.append(Path(executable))
    try:
        import folder_paths

        runtime_root = Path(folder_paths.models_dir) / "prompt_enhancers" / "runtimes"
        if runtime_root.is_dir():
            candidates.extend(runtime_root.rglob("llama-server.exe" if os.name == "nt" else "llama-server"))
    except ImportError:
        pass
    servers: list[str] = []
    for path in candidates:
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError):
            continue
        value = str(resolved)
        if resolved.is_file() and resolved.name.lower() in _SERVER_NAMES and value not in servers:
            servers.append(value)
    return servers or [NO_LLAMA_SERVER]


def validate_gguf_path(model_path: str, additional_roots: str = "") -> Path:
    value = str(model_path).strip()
    if not value:
        raise ValueError("gguf_model_path is required")
    path = Path(value).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".gguf":
        raise ValueError(f"gguf_model_path must be an existing .gguf file: {path}")
    roots = registered_model_roots(additional_roots)
    if not any(path == root or root in path.parents for root in roots):
        rendered = os.pathsep.join(str(root) for root in roots) or "(none)"
        raise ValueError(
            "GGUF model is outside registered model directories. Move it under a ComfyUI/LM Studio model "
            f"directory or register its parent explicitly. Registered roots: {rendered}"
        )
    return path


def validate_llama_server_path(server_path: str) -> Path:
    value = str(server_path).strip()
    if not value:
        raise ValueError("llama_server_path is required; install llama.cpp separately and select llama-server")
    path = Path(value).expanduser().resolve()
    if not path.is_file() or path.name.lower() not in _SERVER_NAMES:
        raise ValueError("llama_server_path must point to an existing llama-server or llama-server.exe file")
    return path


def _gpu_layers_value(value) -> str:
    selected = str(value).strip().lower()
    if selected in {"auto", "all"}:
        return selected
    try:
        number = int(selected)
    except ValueError as exc:
        raise ValueError("gpu_layers must be auto, all, -1, or a non-negative integer") from exc
    if number < -1:
        raise ValueError("gpu_layers must be auto, all, -1, or a non-negative integer")
    return str(number)


def _loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _server_log_tail(log_file, limit: int = 4000) -> str:
    try:
        log_file.flush()
        log_file.seek(0, os.SEEK_END)
        size = log_file.tell()
        log_file.seek(max(0, size - limit))
        return log_file.read().decode("utf-8", errors="replace").strip()
    except (OSError, ValueError):
        return ""


def _wait_until_ready(process, health_url: str, startup_timeout: float, log_file) -> None:
    deadline = time.monotonic() + float(startup_timeout)
    last_error = ""
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            detail = _server_log_tail(log_file)
            suffix = f" Last server output: {detail}" if detail else ""
            raise RuntimeError(f"llama-server exited during startup with code {return_code}.{suffix}")
        try:
            with urlopen(Request(health_url, headers={"Accept": "application/json"}), timeout=1) as response:
                if 200 <= int(response.status) < 300:
                    return
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(0.1)
    detail = _server_log_tail(log_file)
    suffix = f" Last server output: {detail}" if detail else ""
    raise RuntimeError(
        f"llama-server did not become ready within {float(startup_timeout):g} seconds. "
        f"Last health error: {last_error or 'no response'}.{suffix}"
    )


def _stop_server(process, shutdown_timeout: float = 10.0) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=float(shutdown_timeout))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=float(shutdown_timeout))


def _stop_session(session) -> None:
    if not session:
        return
    try:
        _stop_server(session["process"])
    finally:
        try:
            session["log_file"].close()
        except (OSError, ValueError):
            pass


def unload_cached_server() -> bool:
    """Stop and forget the optional persistent GGUF server."""
    global _CACHED_SERVER
    with _SERVER_LOCK:
        session, _CACHED_SERVER = _CACHED_SERVER, None
        _stop_session(session)
        return session is not None


atexit.register(unload_cached_server)


_JOB_HANDLE = None


def _kill_on_close_job():
    """A Windows job that takes its children down with it.

    unload_cached_server is wired to atexit, which covers a clean shutdown and nothing else. A hard
    crash -- ComfyUI died in torch_cpu.dll with an access violation -- or a forced kill skips
    atexit entirely, and the llama-server carries on holding VRAM: one was found five hours old,
    sitting on 5.5 GB of the card ComfyUI was about to load a model onto. Assigning children to a
    kill-on-close job makes the operating system do the cleanup that a dead process cannot.
    """
    global _JOB_HANDLE
    if os.name != "nt":
        return None
    if _JOB_HANDLE is not None:
        return _JOB_HANDLE
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None

        class _BASIC(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _EXTENDED(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BASIC),
                ("IoInfo", ctypes.c_byte * 48),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        info = _EXTENDED()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            kernel32.CloseHandle(job)
            return None
        _JOB_HANDLE = job
        return job
    except Exception:
        # Never let bookkeeping stop the enhancer from running; atexit still covers clean exits.
        return None


def _assign_to_job(process) -> None:
    job = _kill_on_close_job()
    if not job:
        return
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x001F0FFF, False, process.pid)
        if handle:
            kernel32.AssignProcessToJobObject(job, handle)
            kernel32.CloseHandle(handle)
    except Exception:
        pass


def _launch_server(command: list[str], root: str, api_key: str, startup_timeout: int, signature):
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    log_file = tempfile.TemporaryFile(mode="w+b")
    process = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            shell=False,
            creationflags=creationflags,
        )
        _assign_to_job(process)
        _wait_until_ready(process, root[:-3] + "/health", startup_timeout, log_file)
        return {
            "process": process,
            "root": root,
            "api_key": api_key,
            "log_file": log_file,
            "signature": signature,
        }
    except Exception:
        _stop_server(process)
        log_file.close()
        raise


def enhance_prompt_with_gguf_server(
    basic_prompt: str,
    mode: str,
    duration_seconds: float,
    reference_context: str,
    llama_server_path: str,
    gguf_model_path: str,
    registered_model_dirs: str,
    gpu_layers,
    context_size: int,
    threads: int,
    temperature: float,
    max_tokens: int,
    request_timeout: int,
    startup_timeout: int,
    repair_attempts: int,
    disable_thinking: bool = True,
    keep_server_loaded: bool = False,
    enhance_description: bool = True,
    ambience_foley_policy: str = "auto",
    background_score_policy: str = "follow_prompt",
    voice_performance: str = "audible",
    instrumental_description: str = "",
    aspect_ratio: str = "auto",
    media_manifest: str = "",
    multishot_shot_count: int = 0,
    frame_count: int = 0,
    multishot_identity_lock: str = "",
    multishot_voice_lock: str = "",
    multishot_setting_lock: str = "",
    creative_treatment_json: str = "",
    shot_plan_json: str = "",
    cinematography_json: str = "",
    instrumental_style: str = "none",
    acoustic_space: str = "none",
    dialogue_coverage: str = "off",
    delivery_target: str = "local",
    dialogue_language: str = "auto",
    editing_intent: str = "none",
    invent_scene: bool = False,
    creative_latitude: str | None = None,
    lora_trigger_words: str = "",
) -> tuple[str, dict, dict]:
    """Run enhancement through a private llama-server, optionally caching the process."""
    global _CACHED_SERVER
    server = validate_llama_server_path(llama_server_path)
    model = validate_gguf_path(gguf_model_path, registered_model_dirs)
    selected_gpu_layers = _gpu_layers_value(gpu_layers)
    port = _loopback_port()
    root = f"http://127.0.0.1:{port}/v1"
    api_key = secrets.token_urlsafe(32)
    command = [
        str(server),
        "--host", "127.0.0.1",
        "--port", str(port),
        "--model", str(model),
        "--alias", _SERVER_MODEL_ALIAS,
        "--api-key", api_key,
        "--ctx-size", str(int(context_size)),
        "--parallel", "1",
        "--jinja",
    ]
    if selected_gpu_layers != "auto":
        command.extend(["--n-gpu-layers", selected_gpu_layers])
    if int(threads) > 0:
        command.extend(["--threads", str(int(threads))])

    signature = (
        str(server), str(model), selected_gpu_layers, int(context_size), int(threads)
    )
    with _SERVER_LOCK:
        session = None
        reused = False
        try:
            if bool(keep_server_loaded):
                if _CACHED_SERVER and (
                    _CACHED_SERVER["signature"] != signature
                    or _CACHED_SERVER["process"].poll() is not None
                ):
                    unload_cached_server()
                if _CACHED_SERVER is None:
                    _CACHED_SERVER = _launch_server(
                        command, root, api_key, startup_timeout, signature
                    )
                else:
                    reused = True
                session = _CACHED_SERVER
            else:
                unload_cached_server()
                session = _launch_server(command, root, api_key, startup_timeout, signature)

            def complete(messages: list[dict]) -> str:
                return _completion(
                    session["root"],
                    _SERVER_MODEL_ALIAS,
                    messages,
                    session["api_key"],
                    temperature,
                    max_tokens,
                    request_timeout,
                    disable_thinking,
                    False,
                )

            return enhance_prompt_with_completion(
                basic_prompt,
                mode,
                duration_seconds,
                reference_context,
                complete,
                repair_attempts,
                {
                    "provider": "managed_llama_server",
                    "modelPath": str(model),
                    "serverExecutable": str(server),
                    "serverEndpoint": session["root"],
                    "gpuLayers": selected_gpu_layers,
                    "contextSize": int(context_size),
                    "threads": int(threads),
                    "temperature": float(temperature),
                    "maxTokens": int(max_tokens),
                    "thinkingDisabled": bool(disable_thinking),
                    "loopbackOnly": True,
                    "serverKeptLoaded": bool(keep_server_loaded),
                    "serverReused": reused,
                    "serverUnloadedAfterRun": not bool(keep_server_loaded),
                },
                enhance_description,
                ambience_foley_policy,
                background_score_policy,
                voice_performance,
                instrumental_description,
                aspect_ratio,
                media_manifest,
                multishot_shot_count,
                frame_count,
                multishot_identity_lock,
                multishot_voice_lock,
                multishot_setting_lock,
                creative_treatment_json,
                shot_plan_json,
                cinematography_json,
                instrumental_style,
                acoustic_space,
                dialogue_coverage,
                delivery_target,
                dialogue_language,
                editing_intent,
                invent_scene,
                # Keyword, not positional: this tail is exactly where an inserted parameter
                # silently shifts every argument after it, which is how lora_trigger_words
                # started arriving as creative_latitude.
                creative_latitude=creative_latitude,
                lora_trigger_words=lora_trigger_words,
            )
        finally:
            if not bool(keep_server_loaded):
                _stop_session(session)
