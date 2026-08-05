# SPDX-License-Identifier: GPL-3.0-only
"""ComfyUI nodes for guide-constrained MiniMax H3 prompt enhancement."""

from __future__ import annotations

import json

try:
    from .gguf_server import (
        available_gguf_models,
        available_llama_servers,
        enhance_prompt_with_gguf_server,
        unload_cached_server,
    )
    from .prompt_enhancer import enhance_prompt
    from .prompt_guides import build_user_request, resolve_mode, system_prompt_for_mode, validate_prompt
except ImportError:  # pragma: no cover - direct test/import compatibility
    from gguf_server import (
        available_gguf_models,
        available_llama_servers,
        enhance_prompt_with_gguf_server,
        unload_cached_server,
    )
    from prompt_enhancer import enhance_prompt
    from prompt_guides import build_user_request, resolve_mode, system_prompt_for_mode, validate_prompt


class MiniMaxH3PromptGuideBuilder:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "build"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("system_prompt", "user_prompt", "resolved_mode")
    DESCRIPTION = (
        "Build the official MiniMax H3 rewriting instructions without running an LLM. Connect these outputs to "
        "QwenVL Prompt Enhancer, a GGUF node, Ollama, LM Studio, or any other text-generation node."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "basic_prompt": ("STRING", {"multiline": True, "default": ""}),
            "mode": (["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va"], {"default": "auto"}),
            "duration_seconds": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 60.0, "step": 0.01}),
            "reference_context": ("STRING", {"multiline": True, "default": ""}),
        }, "optional": {
            "enhance_description": ("BOOLEAN", {"default": True, "tooltip": "Actively improve cinematic direction while preserving source facts and exact dialogue"}),
            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto", "tooltip": "Control non-vocal ambience and physically motivated sound effects"}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt", "tooltip": "Follow the source, add an instrumental score, or force no non-diegetic music"}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible", "tooltip": "Experimental silent mouth acting is visual best-effort only; exact lip sync and silence are not guaranteed"}),
        }}

    def build(self, basic_prompt, mode, duration_seconds, reference_context, enhance_description=True,
              ambience_foley_policy="auto", background_score_policy="follow_prompt",
              voice_performance="audible"):
        if not str(basic_prompt).strip():
            raise ValueError("basic_prompt cannot be empty")
        resolved = resolve_mode(mode, reference_context, basic_prompt)
        return (
            system_prompt_for_mode(resolved),
            build_user_request(
                basic_prompt, resolved, duration_seconds, reference_context, enhance_description,
                ambience_foley_policy, background_score_policy, voice_performance,
            ),
            resolved,
        )


class MiniMaxH3PromptEnhancer:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "enhance"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds")
    DESCRIPTION = (
        "Rewrite a basic request into MiniMax H3's documented structure through an OpenAI-compatible endpoint "
        "or a local GGUF launched with an isolated llama-server process."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "basic_prompt": ("STRING", {"multiline": True, "default": ""}),
            "mode": (["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va"], {"default": "auto"}),
            "duration_seconds": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 60.0, "step": 0.01}),
            "reference_context": ("STRING", {"multiline": True, "default": ""}),
            "endpoint": ("STRING", {"default": "http://127.0.0.1:1234/v1"}),
            "model": ("STRING", {"default": "", "tooltip": "Blank excludes embedding models and prefers a compact local instruct model from /v1/models"}),
            "api_key": ("STRING", {"default": "", "password": True}),
            "temperature": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 2.0, "step": 0.05}),
            "max_tokens": ("INT", {"default": 4096, "min": 512, "max": 32768, "step": 256}),
            "timeout_seconds": ("INT", {"default": 300, "min": 10, "max": 1800, "step": 10}),
            "repair_attempts": ("INT", {"default": 1, "min": 0, "max": 2, "step": 1}),
            "disable_thinking": ("BOOLEAN", {"default": True, "tooltip": "Faster, cleaner structured output on Qwen thinking models"}),
            "allow_remote_endpoint": ("BOOLEAN", {"default": False}),
        }, "optional": {
            "use_remote_model": ("BOOLEAN", {"default": True, "tooltip": "Use endpoint/model when enabled; use the selected local GGUF when disabled"}),
            "enhance_description": ("BOOLEAN", {"default": True, "tooltip": "Improve staging, cinematography, pacing, transitions, and sound without changing source facts or exact dialogue"}),
            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto", "tooltip": "Ambience & foley: automatic, explicitly required, or disabled"}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt", "tooltip": "Background score: follow the prompt, add instrumental music, or force it off"}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible", "tooltip": "Silent mouth acting is experimental prompt guidance, not guaranteed lip sync or silence"}),
            "local_model": (available_gguf_models(), {"tooltip": "GGUF models found in ComfyUI/models/llm_gguf"}),
            "llama_server_path": (available_llama_servers(), {"tooltip": "Detected standalone llama-server executable"}),
            "gpu_layers": ("STRING", {"default": "auto", "tooltip": "auto, all, -1, or an exact layer count"}),
            "context_size": ("INT", {"default": 16384, "min": 4096, "max": 131072, "step": 1024}),
            "threads": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1}),
            "startup_timeout": ("INT", {"default": 180, "min": 10, "max": 1800, "step": 10}),
            "keep_server_loaded": ("BOOLEAN", {"default": False, "tooltip": "Keep the GGUF in memory for faster repeated enhancement; use the unload node before H3 if VRAM is needed"}),
        }}

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, local_model=None, llama_server_path=None):
        """Allow dynamic choices to change without breaking remote workflows.

        The local backend still validates both paths strictly before launching.
        """
        return True

    def enhance(self, basic_prompt, mode, duration_seconds, reference_context, endpoint, model, api_key,
                temperature, max_tokens, timeout_seconds, repair_attempts, disable_thinking,
                allow_remote_endpoint, use_remote_model=True, local_model="", llama_server_path="",
                gpu_layers="auto", context_size=16384, threads=0, startup_timeout=180,
                keep_server_loaded=False, enhance_description=True, ambience_foley_policy="auto",
                background_score_policy="follow_prompt", voice_performance="audible"):
        if bool(use_remote_model):
            prompt, validation, manifest = enhance_prompt(
                basic_prompt, mode, duration_seconds, reference_context, endpoint, model, api_key,
                temperature, max_tokens, timeout_seconds, repair_attempts, allow_remote_endpoint,
                disable_thinking,
                enhance_description,
                ambience_foley_policy,
                background_score_policy,
                voice_performance,
            )
        else:
            prompt, validation, manifest = enhance_prompt_with_gguf_server(
                basic_prompt, mode, duration_seconds, reference_context, llama_server_path, local_model,
                "", gpu_layers, context_size, threads, temperature, max_tokens, timeout_seconds,
                startup_timeout, repair_attempts, disable_thinking, keep_server_loaded,
                enhance_description,
                ambience_foley_policy,
                background_score_policy,
                voice_performance,
            )
        return (
            prompt,
            json.dumps(validation, ensure_ascii=False, indent=2),
            json.dumps(manifest, ensure_ascii=False, indent=2),
            float(duration_seconds),
        )


class MiniMaxH3GGUFPromptEnhancer:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "enhance"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds")
    DESCRIPTION = (
        "Run an existing GGUF through a managed llama-server bound to loopback. No binary or model is "
        "downloaded, and the server is terminated after every queued invocation."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "basic_prompt": ("STRING", {"multiline": True, "default": ""}),
            "mode": (["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va"], {"default": "auto"}),
            "duration_seconds": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 60.0, "step": 0.01}),
            "reference_context": ("STRING", {"multiline": True, "default": ""}),
            "llama_server_path": ("STRING", {"default": "", "tooltip": "Existing llama-server executable; never downloaded automatically"}),
            "gguf_model_path": ("STRING", {"default": "", "tooltip": "Existing GGUF under a registered model directory"}),
            "registered_model_dirs": ("STRING", {"default": "", "tooltip": "Optional additional roots separated by the OS path separator; ComfyUI and LM Studio model roots are automatic"}),
            "gpu_layers": ("STRING", {"default": "auto", "tooltip": "auto, all, -1, or an exact layer count"}),
            "context_size": ("INT", {"default": 16384, "min": 4096, "max": 131072, "step": 1024}),
            "threads": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1, "tooltip": "0 uses llama-server's default"}),
            "temperature": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 2.0, "step": 0.05}),
            "max_tokens": ("INT", {"default": 4096, "min": 512, "max": 32768, "step": 256}),
            "request_timeout": ("INT", {"default": 300, "min": 10, "max": 1800, "step": 10}),
            "startup_timeout": ("INT", {"default": 180, "min": 10, "max": 1800, "step": 10}),
            "repair_attempts": ("INT", {"default": 1, "min": 0, "max": 2, "step": 1}),
            "disable_thinking": ("BOOLEAN", {"default": True}),
            "enhance_description": ("BOOLEAN", {"default": True}),
            "keep_server_loaded": ("BOOLEAN", {"default": False}),
        }, "optional": {
            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto"}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt"}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible"}),
        }}

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    def enhance(self, basic_prompt, mode, duration_seconds, reference_context, llama_server_path,
                gguf_model_path, registered_model_dirs, gpu_layers, context_size, threads, temperature,
                max_tokens, request_timeout, startup_timeout, repair_attempts, disable_thinking,
                enhance_description, keep_server_loaded, ambience_foley_policy="auto",
                background_score_policy="follow_prompt", voice_performance="audible"):
        prompt, validation, manifest = enhance_prompt_with_gguf_server(
            basic_prompt, mode, duration_seconds, reference_context, llama_server_path, gguf_model_path,
            registered_model_dirs, gpu_layers, context_size, threads, temperature, max_tokens,
            request_timeout, startup_timeout, repair_attempts, disable_thinking,
            keep_server_loaded,
            enhance_description,
            ambience_foley_policy,
            background_score_policy,
            voice_performance,
        )
        return (
            prompt,
            json.dumps(validation, ensure_ascii=False, indent=2),
            json.dumps(manifest, ensure_ascii=False, indent=2),
            float(duration_seconds),
        )


class MiniMaxH3UnloadGGUFServer:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "unload"
    OUTPUT_NODE = True
    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("unloaded", "status")
    DESCRIPTION = "Stop the persistent GGUF prompt-enhancer server and release its RAM/VRAM."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"unload": ("BOOLEAN", {"default": True})}}

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    def unload(self, unload):
        stopped = unload_cached_server() if bool(unload) else False
        status = "Persistent GGUF server unloaded." if stopped else "No persistent GGUF server was loaded."
        return {"ui": {"text": [status]}, "result": (stopped, status)}


class MiniMaxH3PromptValidator:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "validate"
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("prompt", "valid", "validation_report")
    DESCRIPTION = (
        "Validate a manually authored or enhanced prompt against MiniMax H3's documented audiovisual structure "
        "without calling an LLM. Structural validity does not guarantee generation quality."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "mode": (["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va"], {"default": "auto"}),
            "duration_seconds": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 60.0, "step": 0.01}),
            "source_prompt": ("STRING", {"multiline": True, "default": ""}),
            "reference_context": ("STRING", {"multiline": True, "default": ""}),
        }, "optional": {
            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto"}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt"}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible"}),
        }}

    def validate(self, prompt, mode, duration_seconds, source_prompt, reference_context,
                 ambience_foley_policy="auto", background_score_policy="follow_prompt",
                 voice_performance="audible"):
        report = validate_prompt(
            prompt, mode, duration_seconds, source_prompt, reference_context,
            ambience_foley_policy, background_score_policy, voice_performance,
        )
        report_text = json.dumps(report, ensure_ascii=False, indent=2)
        return {
            "ui": {"text": [str(prompt), report_text]},
            "result": (str(prompt), bool(report["valid"]), report_text),
        }
