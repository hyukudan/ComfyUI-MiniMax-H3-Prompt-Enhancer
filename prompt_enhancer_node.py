# SPDX-License-Identifier: GPL-3.0-only
"""ComfyUI nodes for guide-constrained MiniMax H3 prompt enhancement."""

from __future__ import annotations

import json

try:
    from .prompt_enhancer import enhance_prompt
    from .prompt_guides import SYSTEM_PROMPT, build_user_request, resolve_mode, validate_prompt
except ImportError:  # pragma: no cover - direct test/import compatibility
    from prompt_enhancer import enhance_prompt
    from prompt_guides import SYSTEM_PROMPT, build_user_request, resolve_mode, validate_prompt


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
        }}

    def build(self, basic_prompt, mode, duration_seconds, reference_context):
        if not str(basic_prompt).strip():
            raise ValueError("basic_prompt cannot be empty")
        resolved = resolve_mode(mode, reference_context)
        return (
            SYSTEM_PROMPT,
            build_user_request(basic_prompt, resolved, duration_seconds, reference_context),
            resolved,
        )


class MiniMaxH3PromptEnhancer:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "enhance"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("enhanced_prompt", "validation_report", "enhancement_manifest")
    DESCRIPTION = (
        "Rewrite a basic request into MiniMax H3's official base or full-reference structure using any "
        "OpenAI-compatible local LLM. Connect the result to any MiniMax H3 prompt input."
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
        }}

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    def enhance(self, basic_prompt, mode, duration_seconds, reference_context, endpoint, model, api_key,
                temperature, max_tokens, timeout_seconds, repair_attempts, disable_thinking, allow_remote_endpoint):
        prompt, validation, manifest = enhance_prompt(
            basic_prompt, mode, duration_seconds, reference_context, endpoint, model, api_key,
            temperature, max_tokens, timeout_seconds, repair_attempts, allow_remote_endpoint, disable_thinking,
        )
        return (
            prompt,
            json.dumps(validation, ensure_ascii=False, indent=2),
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )


class MiniMaxH3PromptValidator:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "validate"
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("prompt", "valid", "validation_report")
    DESCRIPTION = "Validate a manually authored or enhanced prompt against MiniMax H3's official structure."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "mode": (["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va"], {"default": "auto"}),
            "duration_seconds": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 60.0, "step": 0.01}),
            "source_prompt": ("STRING", {"multiline": True, "default": ""}),
            "reference_context": ("STRING", {"multiline": True, "default": ""}),
        }}

    def validate(self, prompt, mode, duration_seconds, source_prompt, reference_context):
        report = validate_prompt(prompt, mode, duration_seconds, source_prompt, reference_context)
        report_text = json.dumps(report, ensure_ascii=False, indent=2)
        return {
            "ui": {"text": [str(prompt), report_text]},
            "result": (str(prompt), bool(report["valid"]), report_text),
        }
