# SPDX-License-Identifier: GPL-3.0-only
"""ComfyUI nodes for guide-constrained MiniMax H3 prompt enhancement."""

from __future__ import annotations

import hashlib
import json


DEFAULT_LOCAL_CONTEXT_SIZE = 16384
DEFAULT_LOCAL_STARTUP_TIMEOUT = 180
BASIC_PROMPT_PLACEHOLDER = "Describe the video: subject, action, setting, camera, dialogue and sound…"
REFERENCE_PLACEHOLDER = "Example: Picture 1 supplies the identity; Audio 1 supplies the Spanish voice…"
INSTRUMENTAL_PLACEHOLDER = "Example: low strings, 90 BPM, sparse percussion, gradual crescendo…"
MANIFEST_PLACEHOLDER = '{"items":[{"type":"picture","role":"identity"}]}'
IDENTITY_LOCK_PLACEHOLDER = "Identity, wardrobe and appearance every chained prompt must preserve…"
VOICE_LOCK_PLACEHOLDER = "Voice, language and delivery every chained prompt must preserve…"
SETTING_LOCK_PLACEHOLDER = "Location, lighting and continuity every chained prompt must preserve…"
SOURCE_PROMPT_PLACEHOLDER = "Original request used to check preserved facts, dialogue and visible text…"
VALIDATION_PROMPT_PLACEHOLDER = "Paste the complete H3 prompt to validate…"
CREATIVE_TREATMENT_PLACEHOLDER = '{"schemaVersion":1,"genre":"none","visualLanguage":"none","worldAesthetic":"none","tone":"none"}'
SHOT_PLAN_PLACEHOLDER = '{"schemaVersion":1,"timingMode":"auto","shots":[{"id":"s1","description":"..."}]}'
CINEMATOGRAPHY_PLACEHOLDER = '{"schemaVersion":1,"colorPalette":"none","cameraMotion":"none"}'
ALWAYS_RE_ENHANCE_INPUT = {"default": False,
                           "tooltip": "Re-run the LLM on every queue even when the inputs are unchanged. "
                                      "Disabled reuses the cached enhancement, so requeueing an unchanged "
                                      "prompt no longer forces the H3 sampler to regenerate the video."}
API_KEY_TOOLTIP = ("Bearer token for the OpenAI-compatible endpoint. It is no longer saved into workflow "
                   "files, so it must be retyped after reloading. Set MINIMAX_H3_PROMPT_ENHANCER_API_KEY "
                   "instead for anything long-lived: enhance_prompt reads that environment variable "
                   "whenever this widget is blank.")


def _enhancement_digest(inputs):
    """Hash the resolved inputs so identical queues reuse the cached enhancement result."""
    payload = json.dumps(dict(inputs), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _local_runtime_limits(context_size, startup_timeout):
    """Migrate zero-filled widgets from workflows saved before local controls existed."""
    try:
        context = int(context_size or 0)
    except (TypeError, ValueError):
        context = 0
    try:
        startup = int(startup_timeout or 0)
    except (TypeError, ValueError):
        startup = 0
    return (
        context if context >= 4096 else DEFAULT_LOCAL_CONTEXT_SIZE,
        startup if startup >= 10 else DEFAULT_LOCAL_STARTUP_TIMEOUT,
    )


def _effective_duration(validation, requested):
    return float(validation.get("generationProfile", {}).get("effectiveDurationSeconds", requested))

try:
    from .gguf_server import (
        available_gguf_models,
        available_llama_servers,
        enhance_prompt_with_gguf_server,
        unload_cached_server,
    )
    from .prompt_enhancer import enhance_prompt
    from .media_manifest import ASPECT_RATIOS, MAX_GENERATION_SECONDS, manifest_context, parse_media_manifest
    from .prompt_guides import ACOUSTIC_SPACE_CHOICES, DIALOGUE_COVERAGE_CHOICES, INSTRUMENTAL_STYLE_CHOICES, build_user_request, normalize_multishot_output, resolve_mode, system_prompt_for_mode, treatment_warning_report, validate_prompt
except ImportError:  # pragma: no cover - direct test/import compatibility
    from gguf_server import (
        available_gguf_models,
        available_llama_servers,
        enhance_prompt_with_gguf_server,
        unload_cached_server,
    )
    from prompt_enhancer import enhance_prompt
    from media_manifest import ASPECT_RATIOS, MAX_GENERATION_SECONDS, manifest_context, parse_media_manifest
    from prompt_guides import ACOUSTIC_SPACE_CHOICES, DIALOGUE_COVERAGE_CHOICES, INSTRUMENTAL_STYLE_CHOICES, build_user_request, normalize_multishot_output, resolve_mode, system_prompt_for_mode, treatment_warning_report, validate_prompt


MODE_CHOICES = ["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va", "chained_multishot"]
GENERATION_DURATION_INPUT = {"default": 5.0, "min": 4.0, "max": MAX_GENERATION_SECONDS, "step": 0.01,
                             "tooltip": "4-150 seconds. H3 was trained around 5-15 seconds; longer generations are experimental and require much more memory."}
FRAME_COUNT_INPUT = {"default": 0, "min": 0, "max": 3600, "step": 1,
                     "tooltip": "Leave 0 to use Duration. A nonzero exact count must follow 17 × n + 5. Above about 362 frames (~15 s) is experimental."}


class MiniMaxH3PromptGuideBuilder:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "build"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("system_prompt", "user_prompt", "resolved_mode", "treatment_warnings")
    DESCRIPTION = (
        "Build the official MiniMax H3 rewriting instructions without running an LLM. Connect these outputs to "
        "QwenVL Prompt Enhancer, a GGUF node, Ollama, LM Studio, or any other text-generation node."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "basic_prompt": ("STRING", {"multiline": True, "default": "", "placeholder": BASIC_PROMPT_PLACEHOLDER}),
            "mode": (MODE_CHOICES, {"default": "auto"}),
            "duration_seconds": ("FLOAT", dict(GENERATION_DURATION_INPUT)),
            "reference_context": ("STRING", {"multiline": True, "default": "", "placeholder": REFERENCE_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional plain-language notes describing referenced pictures, videos, audio, identities, or roles. Usually needed only for Ref2VA."}),
        }, "optional": {
            "enhance_description": ("BOOLEAN", {"default": True, "tooltip": "Actively improve cinematic direction while preserving source facts and exact dialogue"}),
            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto", "tooltip": "Scene sounds other than speech or music: rain, wind, room tone, footsteps, clothing, doors, impacts, engines, breathing, and similar physical sounds."}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt", "tooltip": "Follow the source, add an instrumental score, or force no non-diegetic music"}),
            "instrumental_description": ("STRING", {"multiline": True, "default": "", "placeholder": INSTRUMENTAL_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Describe concrete instrumentation, tempo, rhythm, and dynamics; mood words are translated into audible parameters."}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible", "tooltip": "Experimental silent mouth acting is visual best-effort only; exact lip sync and silence are not guaranteed"}),
            "aspect_ratio": (list(ASPECT_RATIOS), {"default": "auto"}),
            "media_manifest": ("STRING", {"multiline": True, "default": "", "placeholder": MANIFEST_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Advanced alternative to reference notes: structured JSON describing connected media, roles, analysis, subjects, and transcripts."}),
            "multishot_shot_count": ("INT", {"default": 0, "min": 0, "max": 64, "step": 1, "tooltip": "Chained multishot only: 0 infers the count"}),
            "frame_count": ("INT", dict(FRAME_COUNT_INPUT)),
            "multishot_identity_lock": ("STRING", {"multiline": True, "default": "", "placeholder": IDENTITY_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "multishot_voice_lock": ("STRING", {"multiline": True, "default": "", "placeholder": VOICE_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "multishot_setting_lock": ("STRING", {"multiline": True, "default": "", "placeholder": SETTING_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "show_advanced_controls": ("BOOLEAN", {"default": False, "tooltip": "Show structured reference metadata and exact frame controls"}),
            "creative_treatment_json": ("STRING", {"multiline": True, "default": "", "placeholder": CREATIVE_TREATMENT_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Stable schema-v1 storage for the four optional creative-treatment selectors. Blank is neutral."}),
            "shot_plan_json": ("STRING", {"multiline": True, "default": "", "placeholder": SHOT_PLAN_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v1 authoritative shot plan. Blank preserves automatic shot planning."}),
            "cinematography_json": ("STRING", {"multiline": True, "default": "", "placeholder": CINEMATOGRAPHY_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v1 manual color, camera, optics, focus, texture, and motion-rendering controls. Blank is neutral."}),
            "instrumental_style": (list(INSTRUMENTAL_STYLE_CHOICES), {"default": "none", "tooltip": "When instrumental score is enabled, adapt its arrangement to this musical language while preserving compatible user direction."}),
            "acoustic_space": (list(ACOUSTIC_SPACE_CHOICES), {"default": "none", "tooltip": "Diegetic sound space for the permitted ambience, foley, and voices. It renders existing sounds; it never adds a source."}),
            "dialogue_coverage": (list(DIALOGUE_COVERAGE_CHOICES), {"default": "off", "tooltip": "Keep every speaking character's mouth and eyes unobstructed, in focus, and framed at medium close-up or tighter for the whole line."}),
        }}

    def build(self, basic_prompt, mode, duration_seconds, reference_context, enhance_description=True,
              ambience_foley_policy="auto", background_score_policy="follow_prompt",
              voice_performance="audible", instrumental_description="", aspect_ratio="auto",
              media_manifest="", multishot_shot_count=0, frame_count=0,
              multishot_identity_lock="", multishot_voice_lock="", multishot_setting_lock="",
              show_advanced_controls=False, creative_treatment_json="", shot_plan_json="",
              cinematography_json="", instrumental_style="none", acoustic_space="none",
              dialogue_coverage="off"):
        if not str(basic_prompt).strip():
            raise ValueError("basic_prompt cannot be empty")
        resolved = resolve_mode(mode, reference_context, basic_prompt, media_manifest)
        return (
            system_prompt_for_mode(resolved, bool(enhance_description)),
            build_user_request(
                basic_prompt, resolved, duration_seconds, reference_context, enhance_description,
                ambience_foley_policy, background_score_policy, voice_performance,
                instrumental_description,
                aspect_ratio, media_manifest, multishot_shot_count, frame_count,
                multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
                (), creative_treatment_json, shot_plan_json, cinematography_json, instrumental_style,
                acoustic_space, dialogue_coverage,
            ),
            resolved,
            treatment_warning_report(
                creative_treatment_json, cinematography_json, shot_plan_json, duration_seconds,
                frame_count, resolved, enhance_description,
            ),
        )


class MiniMaxH3PromptEnhancer:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "enhance"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "FLOAT", "STRING", "STRING")
    RETURN_NAMES = (
        "enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds", "aspect_ratio",
        "treatment_warnings",
    )
    DESCRIPTION = (
        "Rewrite a basic request into MiniMax H3's documented structure through an OpenAI-compatible endpoint "
        "or a local GGUF launched with an isolated llama-server process."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "basic_prompt": ("STRING", {"multiline": True, "default": "", "placeholder": BASIC_PROMPT_PLACEHOLDER}),
            "mode": (MODE_CHOICES, {"default": "auto"}),
            "duration_seconds": ("FLOAT", dict(GENERATION_DURATION_INPUT)),
            "reference_context": ("STRING", {"multiline": True, "default": "", "placeholder": REFERENCE_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional plain-language notes describing referenced pictures, videos, audio, identities, or roles. Usually needed only for Ref2VA."}),
            "endpoint": ("STRING", {"default": "http://127.0.0.1:1234/v1"}),
            "model": ("STRING", {"default": "", "tooltip": "Blank excludes embedding models and prefers a compact local instruct model from /v1/models"}),
            "api_key": ("STRING", {"default": "", "password": True, "tooltip": API_KEY_TOOLTIP}),
            "temperature": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 2.0, "step": 0.05}),
            "max_tokens": ("INT", {"default": 4096, "min": 512, "max": 32768, "step": 256}),
            "timeout_seconds": ("INT", {"default": 300, "min": 10, "max": 1800, "step": 10}),
            "repair_attempts": ("INT", {"default": 2, "min": 0, "max": 4, "step": 1}),
            "disable_thinking": ("BOOLEAN", {"default": True, "tooltip": "Faster, cleaner structured output on Qwen thinking models"}),
            "allow_remote_endpoint": ("BOOLEAN", {"default": False}),
        }, "optional": {
            "use_remote_model": ("BOOLEAN", {"default": True, "tooltip": "Use endpoint/model when enabled; use the selected local GGUF when disabled"}),
            "enhance_description": ("BOOLEAN", {"default": True, "tooltip": "Improve staging, cinematography, pacing, transitions, and sound without changing source facts or exact dialogue"}),
            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto", "tooltip": "Scene sounds other than speech or music: rain, wind, room tone, footsteps, clothing, doors, impacts, engines, breathing, and similar physical sounds."}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt", "tooltip": "Background score: follow the prompt, add instrumental music, or force it off"}),
            "instrumental_description": ("STRING", {"multiline": True, "default": "", "placeholder": INSTRUMENTAL_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Describe concrete instrumentation, tempo, rhythm, and dynamics; mood words are translated into audible parameters."}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible", "tooltip": "Silent mouth acting is experimental prompt guidance, not guaranteed lip sync or silence"}),
            "local_model": (available_gguf_models(), {"tooltip": "Text GGUF models found in ComfyUI/models/llm_gguf; the first discovered model is the default"}),
            "llama_server_path": (available_llama_servers(), {"tooltip": "Detected llama.cpp llama-server executable used to run the selected GGUF; this is not a separate model or API backend"}),
            "gpu_layers": ("STRING", {"default": "auto", "tooltip": "auto, all, -1, or an exact layer count"}),
            "context_size": ("INT", {"default": DEFAULT_LOCAL_CONTEXT_SIZE, "min": 0, "max": 131072, "step": 1024, "tooltip": "0 uses the safe 16384-token default (including migrated workflows)"}),
            "threads": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1}),
            "startup_timeout": ("INT", {"default": DEFAULT_LOCAL_STARTUP_TIMEOUT, "min": 0, "max": 1800, "step": 10, "tooltip": "0 uses the safe 180-second default (including migrated workflows)"}),
            "keep_server_loaded": ("BOOLEAN", {"default": False, "tooltip": "Keep the GGUF in memory for faster repeated enhancement; use the unload node before H3 if VRAM is needed"}),
            "aspect_ratio": (list(ASPECT_RATIOS), {"default": "auto"}),
            "media_manifest": ("STRING", {"multiline": True, "default": "", "placeholder": MANIFEST_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Advanced alternative to reference notes: structured JSON describing connected media and roles."}),
            "multishot_shot_count": ("INT", {"default": 0, "min": 0, "max": 64, "step": 1}),
            "frame_count": ("INT", dict(FRAME_COUNT_INPUT)),
            "multishot_identity_lock": ("STRING", {"multiline": True, "default": "", "placeholder": IDENTITY_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "multishot_voice_lock": ("STRING", {"multiline": True, "default": "", "placeholder": VOICE_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "multishot_setting_lock": ("STRING", {"multiline": True, "default": "", "placeholder": SETTING_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "show_advanced_controls": ("BOOLEAN", {"default": False, "tooltip": "Show structured reference metadata and exact frame controls"}),
            "creative_treatment_json": ("STRING", {"multiline": True, "default": "", "placeholder": CREATIVE_TREATMENT_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Stable schema-v1 storage for genre, visual language, world aesthetic, and tone. Blank is neutral."}),
            "shot_plan_json": ("STRING", {"multiline": True, "default": "", "placeholder": SHOT_PLAN_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v1 authoritative shot plan. Blank preserves automatic shot planning."}),
            "cinematography_json": ("STRING", {"multiline": True, "default": "", "placeholder": CINEMATOGRAPHY_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v1 manual color, camera, optics, focus, texture, and motion-rendering controls. Blank is neutral."}),
            "instrumental_style": (list(INSTRUMENTAL_STYLE_CHOICES), {"default": "none", "tooltip": "When instrumental score is enabled, adapt its arrangement to this musical language while preserving compatible user direction."}),
            "acoustic_space": (list(ACOUSTIC_SPACE_CHOICES), {"default": "none", "tooltip": "Diegetic sound space for the permitted ambience, foley, and voices. It renders existing sounds; it never adds a source."}),
            "dialogue_coverage": (list(DIALOGUE_COVERAGE_CHOICES), {"default": "off", "tooltip": "Keep every speaking character's mouth and eyes unobstructed, in focus, and framed at medium close-up or tighter for the whole line."}),
            # Appended last on purpose: ComfyUI stores widget values positionally, so a new control
            # anywhere else would shift every saved workflow's widgets_values by one slot.
            "always_re_enhance": ("BOOLEAN", dict(ALWAYS_RE_ENHANCE_INPUT)),
            "delivery_target": (["local", "api_v2"], {"default": "local", "tooltip": "API v2 makes the 7000-character text-block limit repairable and hard."}),
        }}

    @classmethod
    def IS_CHANGED(cls, always_re_enhance=False, **kwargs):
        """Reuse the previous enhancement while the inputs are identical."""
        if always_re_enhance:
            return float("nan")
        return _enhancement_digest(kwargs)

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
                background_score_policy="follow_prompt", voice_performance="audible",
                instrumental_description="", aspect_ratio="auto", media_manifest="",
                multishot_shot_count=0, frame_count=0, multishot_identity_lock="",
                multishot_voice_lock="", multishot_setting_lock="", show_advanced_controls=False,
                creative_treatment_json="", shot_plan_json="", cinematography_json="",
                instrumental_style="none", acoustic_space="none", dialogue_coverage="off",
                always_re_enhance=False, delivery_target="local"):
        # always_re_enhance only drives IS_CHANGED caching; enhancement itself ignores it.
        if bool(use_remote_model):
            remote_args = (
                basic_prompt, mode, duration_seconds, reference_context, endpoint, model, api_key,
                temperature, max_tokens, timeout_seconds, repair_attempts, allow_remote_endpoint,
                disable_thinking,
                enhance_description,
                ambience_foley_policy,
                background_score_policy,
                voice_performance,
                instrumental_description,
            )
            if any((aspect_ratio != "auto", media_manifest, multishot_shot_count, frame_count,
                    multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
                    creative_treatment_json, shot_plan_json, cinematography_json,
                    instrumental_style != "none", acoustic_space != "none", dialogue_coverage != "off",
                    delivery_target != "local")):
                remote_args += (aspect_ratio, media_manifest, multishot_shot_count, frame_count,
                                multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
                                creative_treatment_json, shot_plan_json, cinematography_json,
                                instrumental_style, acoustic_space, dialogue_coverage, delivery_target)
            prompt, validation, manifest = enhance_prompt(*remote_args)
        else:
            context_size, startup_timeout = _local_runtime_limits(context_size, startup_timeout)
            local_args = (
                basic_prompt, mode, duration_seconds, reference_context, llama_server_path, local_model,
                "", gpu_layers, context_size, threads, temperature, max_tokens, timeout_seconds,
                startup_timeout, repair_attempts, disable_thinking, keep_server_loaded,
                enhance_description,
                ambience_foley_policy,
                background_score_policy,
                voice_performance,
                instrumental_description,
            )
            if any((aspect_ratio != "auto", media_manifest, multishot_shot_count, frame_count,
                    multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
                    creative_treatment_json, shot_plan_json, cinematography_json,
                    instrumental_style != "none", acoustic_space != "none", dialogue_coverage != "off",
                    delivery_target != "local")):
                local_args += (aspect_ratio, media_manifest, multishot_shot_count, frame_count,
                               multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
                               creative_treatment_json, shot_plan_json, cinematography_json,
                               instrumental_style, acoustic_space, dialogue_coverage, delivery_target)
            prompt, validation, manifest = enhance_prompt_with_gguf_server(*local_args)
        return (
            prompt,
            json.dumps(validation, ensure_ascii=False, indent=2),
            json.dumps(manifest, ensure_ascii=False, indent=2),
            _effective_duration(validation, duration_seconds),
            str(aspect_ratio),
            "\n".join(manifest.get("treatmentWarnings", ())),
        )


class MiniMaxH3GGUFPromptEnhancer:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "enhance"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "FLOAT", "STRING", "STRING")
    RETURN_NAMES = (
        "enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds", "aspect_ratio",
        "treatment_warnings",
    )
    DESCRIPTION = (
        "Run an existing GGUF through a managed llama-server bound to loopback. No binary or model is "
        "downloaded, and the server is terminated after every queued invocation."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "basic_prompt": ("STRING", {"multiline": True, "default": "", "placeholder": BASIC_PROMPT_PLACEHOLDER}),
            "mode": (MODE_CHOICES, {"default": "auto"}),
            "duration_seconds": ("FLOAT", dict(GENERATION_DURATION_INPUT)),
            "reference_context": ("STRING", {"multiline": True, "default": "", "placeholder": REFERENCE_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional plain-language notes describing referenced pictures, videos, audio, identities, or roles. Usually needed only for Ref2VA."}),
            "llama_server_path": ("STRING", {"default": "", "tooltip": "Existing llama-server executable; never downloaded automatically"}),
            "gguf_model_path": ("STRING", {"default": "", "tooltip": "Existing GGUF under a registered model directory"}),
            "registered_model_dirs": ("STRING", {"default": "", "tooltip": "Optional additional roots separated by the OS path separator; ComfyUI and LM Studio model roots are automatic"}),
            "gpu_layers": ("STRING", {"default": "auto", "tooltip": "auto, all, -1, or an exact layer count"}),
            "context_size": ("INT", {"default": DEFAULT_LOCAL_CONTEXT_SIZE, "min": 0, "max": 131072, "step": 1024, "tooltip": "0 uses the safe 16384-token default"}),
            "threads": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1, "tooltip": "0 uses llama-server's default"}),
            "temperature": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 2.0, "step": 0.05}),
            "max_tokens": ("INT", {"default": 4096, "min": 512, "max": 32768, "step": 256}),
            "request_timeout": ("INT", {"default": 300, "min": 10, "max": 1800, "step": 10}),
            "startup_timeout": ("INT", {"default": DEFAULT_LOCAL_STARTUP_TIMEOUT, "min": 0, "max": 1800, "step": 10, "tooltip": "0 uses the safe 180-second default"}),
            "repair_attempts": ("INT", {"default": 2, "min": 0, "max": 4, "step": 1}),
            "disable_thinking": ("BOOLEAN", {"default": True}),
            "enhance_description": ("BOOLEAN", {"default": True}),
            "keep_server_loaded": ("BOOLEAN", {"default": False}),
        }, "optional": {
            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto", "tooltip": "Scene sounds other than speech or music: ambience plus physical action sounds such as footsteps, clothing, doors, impacts, and engines."}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt"}),
            "instrumental_description": ("STRING", {"multiline": True, "default": "", "placeholder": INSTRUMENTAL_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Describe concrete instrumentation, tempo, rhythm, and dynamics; mood words are translated into audible parameters."}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible"}),
            "aspect_ratio": (list(ASPECT_RATIOS), {"default": "auto"}),
            "media_manifest": ("STRING", {"multiline": True, "default": "", "placeholder": MANIFEST_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Advanced structured JSON for connected reference media."}),
            "multishot_shot_count": ("INT", {"default": 0, "min": 0, "max": 64, "step": 1}),
            "frame_count": ("INT", dict(FRAME_COUNT_INPUT)),
            "multishot_identity_lock": ("STRING", {"multiline": True, "default": "", "placeholder": IDENTITY_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "multishot_voice_lock": ("STRING", {"multiline": True, "default": "", "placeholder": VOICE_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "multishot_setting_lock": ("STRING", {"multiline": True, "default": "", "placeholder": SETTING_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "show_advanced_controls": ("BOOLEAN", {"default": False, "tooltip": "Show structured reference metadata and exact frame controls"}),
            "creative_treatment_json": ("STRING", {"multiline": True, "default": "", "placeholder": CREATIVE_TREATMENT_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Stable schema-v1 storage for genre, visual language, world aesthetic, and tone. Blank is neutral."}),
            "shot_plan_json": ("STRING", {"multiline": True, "default": "", "placeholder": SHOT_PLAN_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v1 authoritative shot plan. Blank preserves automatic shot planning."}),
            "cinematography_json": ("STRING", {"multiline": True, "default": "", "placeholder": CINEMATOGRAPHY_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v1 manual color, camera, optics, focus, texture, and motion-rendering controls. Blank is neutral."}),
            "instrumental_style": (list(INSTRUMENTAL_STYLE_CHOICES), {"default": "none", "tooltip": "When instrumental score is enabled, adapt its arrangement to this musical language while preserving compatible user direction."}),
            "acoustic_space": (list(ACOUSTIC_SPACE_CHOICES), {"default": "none", "tooltip": "Diegetic sound space for the permitted ambience, foley, and voices. It renders existing sounds; it never adds a source."}),
            "dialogue_coverage": (list(DIALOGUE_COVERAGE_CHOICES), {"default": "off", "tooltip": "Keep every speaking character's mouth and eyes unobstructed, in focus, and framed at medium close-up or tighter for the whole line."}),
            # Appended last on purpose: ComfyUI stores widget values positionally, so a new control
            # anywhere else would shift every saved workflow's widgets_values by one slot.
            "always_re_enhance": ("BOOLEAN", dict(ALWAYS_RE_ENHANCE_INPUT)),
            "delivery_target": (["local", "api_v2"], {"default": "local", "tooltip": "API v2 makes the 7000-character text-block limit repairable and hard."}),
        }}

    @classmethod
    def IS_CHANGED(cls, always_re_enhance=False, **kwargs):
        """Reuse the previous enhancement while the inputs are identical."""
        if always_re_enhance:
            return float("nan")
        return _enhancement_digest(kwargs)

    def enhance(self, basic_prompt, mode, duration_seconds, reference_context, llama_server_path,
                gguf_model_path, registered_model_dirs, gpu_layers, context_size, threads, temperature,
                max_tokens, request_timeout, startup_timeout, repair_attempts, disable_thinking,
                enhance_description, keep_server_loaded, ambience_foley_policy="auto",
                background_score_policy="follow_prompt", voice_performance="audible",
                instrumental_description="", aspect_ratio="auto", media_manifest="",
                multishot_shot_count=0, frame_count=0, multishot_identity_lock="",
                multishot_voice_lock="", multishot_setting_lock="", show_advanced_controls=False,
                creative_treatment_json="", shot_plan_json="", cinematography_json="",
                instrumental_style="none", acoustic_space="none", dialogue_coverage="off",
                always_re_enhance=False, delivery_target="local"):
        # always_re_enhance only drives IS_CHANGED caching; enhancement itself ignores it.
        context_size, startup_timeout = _local_runtime_limits(context_size, startup_timeout)
        prompt, validation, manifest = enhance_prompt_with_gguf_server(
            basic_prompt, mode, duration_seconds, reference_context, llama_server_path, gguf_model_path,
            registered_model_dirs, gpu_layers, context_size, threads, temperature, max_tokens,
            request_timeout, startup_timeout, repair_attempts, disable_thinking,
            keep_server_loaded,
            enhance_description,
            ambience_foley_policy,
            background_score_policy,
            voice_performance,
            instrumental_description,
            aspect_ratio, media_manifest, multishot_shot_count, frame_count,
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
            creative_treatment_json, shot_plan_json, cinematography_json, instrumental_style,
            acoustic_space, dialogue_coverage, delivery_target,
        )
        return (
            prompt,
            json.dumps(validation, ensure_ascii=False, indent=2),
            json.dumps(manifest, ensure_ascii=False, indent=2),
            _effective_duration(validation, duration_seconds),
            str(aspect_ratio),
            "\n".join(manifest.get("treatmentWarnings", ())),
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


class MiniMaxH3MediaManifestValidator:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "validate"
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("normalized_manifest", "valid", "validation_report", "reference_context")
    DESCRIPTION = "Validate and normalize an optional H3 reference-media manifest before prompt enhancement."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"media_manifest": ("STRING", {
            "multiline": True, "default": '{"items":[]}', "dynamicPrompts": False,
        })}}

    def validate(self, media_manifest):
        parsed = parse_media_manifest(media_manifest)
        normalized = json.dumps({key: value for key, value in parsed.items() if key not in {"warnings", "errors"}}, ensure_ascii=False, indent=2)
        report = {"valid": not parsed["errors"], "errors": parsed["errors"], "warnings": parsed["warnings"], "counts": parsed.get("counts", {})}
        report_text = json.dumps(report, ensure_ascii=False, indent=2)
        return {"ui": {"text": [report_text]}, "result": (normalized, report["valid"], report_text, manifest_context(media_manifest))}


class MiniMaxH3ChainedMultishotOutput:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "format"
    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "STRING", "FLOAT")
    RETURN_NAMES = ("multishot_script", "prompts_json", "valid", "validation_report", "total_duration_seconds")
    DESCRIPTION = "Validate canonical chained-multishot JSON and emit the --- separated script accepted by H3 multishot samplers."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompts_json": ("STRING", {"multiline": True, "default": '{"prompts":[]}'}),
            "duration_per_shot": ("FLOAT", dict(GENERATION_DURATION_INPUT)),
            "source_prompt": ("STRING", {"multiline": True, "default": "", "placeholder": SOURCE_PROMPT_PLACEHOLDER}),
        }, "optional": {
            "expected_shot_count": ("INT", {"default": 0, "min": 0, "max": 64, "step": 1}),
            "identity_lock": ("STRING", {"multiline": True, "default": "", "placeholder": IDENTITY_LOCK_PLACEHOLDER}),
            "voice_lock": ("STRING", {"multiline": True, "default": "", "placeholder": VOICE_LOCK_PLACEHOLDER}),
            "setting_lock": ("STRING", {"multiline": True, "default": "", "placeholder": SETTING_LOCK_PLACEHOLDER}),
        }}

    def format(self, prompts_json, duration_per_shot, source_prompt, expected_shot_count=0,
               identity_lock="", voice_lock="", setting_lock=""):
        canonical = normalize_multishot_output(prompts_json, (identity_lock, voice_lock, setting_lock))
        report = validate_prompt(
            canonical, "chained_multishot", duration_per_shot, source_prompt,
            multishot_shot_count=expected_shot_count,
            multishot_identity_lock=identity_lock,
            multishot_voice_lock=voice_lock,
            multishot_setting_lock=setting_lock,
        )
        try:
            prompts = json.loads(canonical).get("prompts", [])
        except (json.JSONDecodeError, AttributeError):
            prompts = []
        script = "\n---\n".join(str(item).strip() for item in prompts if str(item).strip())
        report_text = json.dumps(report, ensure_ascii=False, indent=2)
        return (script, canonical, bool(report["valid"]), report_text, float(duration_per_shot) * len(prompts))


class MiniMaxH3ShotSelector:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "select"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT", "BOOLEAN")
    RETURN_NAMES = (
        "shot_prompt", "timeline_body", "shot_description", "shot_id", "shot_count", "autonomous",
    )
    DESCRIPTION = (
        "Select one enhanced shot from an enhancement manifest or shotsPackage. shot_prompt is emitted only when "
        "the package marks it as a complete autonomous H3 prompt; timeline_body remains available for inspection."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "enhancement_manifest_or_package": ("STRING", {
                "multiline": True,
                "default": "",
                "dynamicPrompts": False,
                "tooltip": "Connect enhancement_manifest or paste its shotsPackage object.",
            }),
            "shot_index": ("INT", {"default": 1, "min": 1, "max": 64, "step": 1}),
        }}

    def select(self, enhancement_manifest_or_package, shot_index):
        try:
            data = json.loads(str(enhancement_manifest_or_package or ""))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Enhancement manifest/shotsPackage must be valid JSON: {exc.msg}") from exc
        if not isinstance(data, dict):
            raise ValueError("Enhancement manifest/shotsPackage must be a JSON object")
        package = data.get("shotsPackage", data)
        if not isinstance(package, dict) or package.get("schemaVersion") != 1:
            raise ValueError("No schema-v1 shotsPackage was found")
        shots = package.get("shots")
        if not isinstance(shots, list) or not shots:
            raise ValueError("shotsPackage contains no selectable shots")
        index = int(shot_index)
        if index < 1 or index > len(shots):
            raise ValueError(f"shot_index must be between 1 and {len(shots)}")
        shot = shots[index - 1]
        if not isinstance(shot, dict):
            raise ValueError(f"shotsPackage shot {index} is invalid")
        autonomous = bool(shot.get("autonomous"))
        full_prompt = str(shot.get("autonomousPrompt", shot.get("enhancedPrompt", ""))).strip() if autonomous else ""
        timeline_body = str(shot.get("timelineBody", "")).strip()
        description = str(shot.get("description", "")).strip()
        shot_id = str(shot.get("id", "")).strip()
        reason = str(shot.get("autonomyReason", "")).strip()
        status = (
            f"Selected autonomous shot {index}/{len(shots)} ({shot_id})."
            if autonomous else
            f"Shot {index}/{len(shots)} ({shot_id}) is not autonomous: {reason}"
        )
        return {
            "ui": {"text": [status]},
            "result": (full_prompt, timeline_body, description, shot_id, len(shots), autonomous),
        }


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
            "prompt": ("STRING", {"multiline": True, "default": "", "placeholder": VALIDATION_PROMPT_PLACEHOLDER}),
            "mode": (MODE_CHOICES, {"default": "auto"}),
            "duration_seconds": ("FLOAT", dict(GENERATION_DURATION_INPUT)),
            "source_prompt": ("STRING", {"multiline": True, "default": "", "placeholder": SOURCE_PROMPT_PLACEHOLDER}),
            "reference_context": ("STRING", {"multiline": True, "default": "", "placeholder": REFERENCE_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional plain-language notes describing referenced pictures, videos, audio, identities, or roles. Usually needed only for Ref2VA."}),
        }, "optional": {
            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto", "tooltip": "Scene sounds other than speech or music: ambience plus physical action sounds such as footsteps, clothing, doors, impacts, and engines."}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt"}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible"}),
            "aspect_ratio": (list(ASPECT_RATIOS), {"default": "auto"}),
            "media_manifest": ("STRING", {"multiline": True, "default": "", "placeholder": MANIFEST_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Advanced structured JSON for connected reference media."}),
            "multishot_shot_count": ("INT", {"default": 0, "min": 0, "max": 64, "step": 1}),
            "frame_count": ("INT", dict(FRAME_COUNT_INPUT)),
            "multishot_identity_lock": ("STRING", {"multiline": True, "default": "", "placeholder": IDENTITY_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "multishot_voice_lock": ("STRING", {"multiline": True, "default": "", "placeholder": VOICE_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "multishot_setting_lock": ("STRING", {"multiline": True, "default": "", "placeholder": SETTING_LOCK_PLACEHOLDER, "dynamicPrompts": False}),
            "show_advanced_controls": ("BOOLEAN", {"default": False, "tooltip": "Show structured reference metadata and exact frame controls"}),
            "creative_treatment_json": ("STRING", {"multiline": True, "default": "", "placeholder": CREATIVE_TREATMENT_PLACEHOLDER, "dynamicPrompts": False}),
            "shot_plan_json": ("STRING", {"multiline": True, "default": "", "placeholder": SHOT_PLAN_PLACEHOLDER, "dynamicPrompts": False}),
            "cinematography_json": ("STRING", {"multiline": True, "default": "", "placeholder": CINEMATOGRAPHY_PLACEHOLDER, "dynamicPrompts": False}),
            "enhance_description": ("BOOLEAN", {"default": True, "tooltip": "Validate enhanced-production coverage; disable for conservative-grounded coverage."}),
            "delivery_target": (["local", "api_v2"], {"default": "local", "tooltip": "API v2 treats the 7000-character text-block limit as a hard error; local mode reports compatibility only."}),
            "instrumental_description": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
            "instrumental_style": (list(INSTRUMENTAL_STYLE_CHOICES), {"default": "none"}),
            "acoustic_space": (list(ACOUSTIC_SPACE_CHOICES), {"default": "none"}),
            "dialogue_coverage": (list(DIALOGUE_COVERAGE_CHOICES), {"default": "off"}),
        }}

    def validate(self, prompt, mode, duration_seconds, source_prompt, reference_context,
                 ambience_foley_policy="auto", background_score_policy="follow_prompt",
                 voice_performance="audible", aspect_ratio="auto", media_manifest="",
                 multishot_shot_count=0, frame_count=0, multishot_identity_lock="",
                 multishot_voice_lock="", multishot_setting_lock="", show_advanced_controls=False,
                 creative_treatment_json="", shot_plan_json="", cinematography_json="",
                 enhance_description=True, delivery_target="local", instrumental_description="",
                 instrumental_style="none", acoustic_space="none", dialogue_coverage="off"):
        report = validate_prompt(
            prompt, mode, duration_seconds, source_prompt, reference_context,
            ambience_foley_policy, background_score_policy, voice_performance,
            aspect_ratio, media_manifest, multishot_shot_count, frame_count,
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
            (), creative_treatment_json, shot_plan_json, cinematography_json,
            enhance_description=bool(enhance_description), delivery_target=delivery_target,
            instrumental_description=instrumental_description, instrumental_style=instrumental_style,
            acoustic_space=acoustic_space, dialogue_coverage=dialogue_coverage,
        )
        report_text = json.dumps(report, ensure_ascii=False, indent=2)
        return {
            "ui": {"text": [str(prompt), report_text]},
            "result": (str(prompt), bool(report["valid"]), report_text),
        }
