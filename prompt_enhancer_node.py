# SPDX-License-Identifier: GPL-3.0-only
"""ComfyUI nodes for guide-constrained MiniMax H3 prompt enhancement."""

from __future__ import annotations

import hashlib
import json
import math


DEFAULT_LOCAL_CONTEXT_SIZE = 32768
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


def _prompt_budget_ui(enhanced_prompt: str | None, report: dict, manifest: dict | str | None = None) -> dict | None:
    text = str(enhanced_prompt or "")
    if not text:
        return None
    parsed_manifest = manifest
    if isinstance(parsed_manifest, str):
        try:
            parsed_manifest = json.loads(parsed_manifest)
        except json.JSONDecodeError:
            parsed_manifest = {}
    section_names = report.get("sections", ())
    if not isinstance(section_names, (list, tuple)):
        section_names = ()
    starts = []
    for name in section_names:
        label = str(name or "").strip()
        marker = f"{label}:"
        line_offset = text.find(f"\n{marker}")
        offset = 0 if text.startswith(marker) else line_offset + 1 if line_offset >= 0 else -1
        if label and offset >= 0:
            starts.append((offset, label))
    starts.sort()
    sections = []
    if starts and starts[0][0] > 0:
        sections.append({"name": "Unsectioned", "characters": starts[0][0]})
    for index, (offset, label) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        sections.append({"name": label, "characters": end - offset})
    if not sections:
        sections = [{"name": "Full prompt", "characters": len(text)}]
    description_budget = report.get("descriptionBudget")
    return {
        "source": "local_estimate",
        "totalCharacters": len(text),
        "limitCharacters": 7000 if report.get("deliveryTarget") == "api_v2" else None,
        "sections": sections,
        "descriptionBudget": description_budget if isinstance(description_budget, dict) else None,
        "manifestAvailable": isinstance(parsed_manifest, dict) and bool(parsed_manifest),
    }


def _diagnostic_ui_payload(
    report: dict | str | None,
    enhanced_prompt: str | None = None,
    manifest: dict | str | None = None,
) -> list[str]:
    if isinstance(report, str):
        try:
            report = json.loads(report)
        except json.JSONDecodeError:
            report = {}
    report = report if isinstance(report, dict) else {}
    structured = report.get("diagnosticReport", report)
    if not isinstance(structured, dict):
        structured = {}
    compact = {
        "schemaVersion": structured.get("schemaVersion", 1),
        "summary": structured.get("summary", {
            "valid": bool(report.get("valid", False)),
            "qualityValid": bool(report.get("qualityValid", report.get("valid", False))),
        }),
        "diagnostics": structured.get("diagnostics", ()),
    }
    prompt_budget = _prompt_budget_ui(enhanced_prompt, report, manifest)
    if prompt_budget:
        compact["promptBudget"] = prompt_budget
    return [json.dumps(compact, ensure_ascii=False, separators=(",", ":"))]
CREATIVE_TREATMENT_PLACEHOLDER = '{"schemaVersion":2,"genre":"none","visualLanguage":"none","worldAesthetic":"none","tone":"none"}'
LORA_TRIGGER_PLACEHOLDER = "Trigger tokens for any LoRA in the graph, e.g. g0r3_style, ultrarealistic_v2…"
SHOT_PLAN_PLACEHOLDER = '{"schemaVersion":1,"timingMode":"auto","shots":[{"id":"s1","description":"..."}]}'
CINEMATOGRAPHY_PLACEHOLDER = '{"schemaVersion":2,"colorPalette":"none","cameraMotion":"none"}'
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
    from .creative_treatments import CREATIVE_TREATMENT_SCHEMA_VERSION, VISUAL_LANGUAGE_PROFILES
    from .prompt_enhancer import enhance_prompt
    from .media_manifest import ASPECT_RATIOS, MAX_GENERATION_SECONDS, generation_profile, manifest_context, parse_media_manifest, parse_media_project
    from .prompt_guides import ACOUSTIC_SPACE_CHOICES, ENHANCEMENT_PROFILES, DIALOGUE_COVERAGE_CHOICES, DIALOGUE_LANGUAGE_CHOICES, EDITING_INTENT_CHOICES, INSTRUMENTAL_STYLE_CHOICES, build_user_request, normalize_multishot_output, resolve_mode, system_prompt_for_mode, treatment_warning_report, validate_prompt
    from .title_credits import TITLE_ENERGIES, TITLE_RECIPES, TITLE_RECIPE_DISABLED, append_title_lock, title_briefing
    from .reference_director import REFERENCE_PROJECT_TYPE, build_reference_project, reference_context_for_project
    from .reference_media import load_generation_media
except ImportError:  # pragma: no cover - direct test/import compatibility
    from gguf_server import (
        available_gguf_models,
        available_llama_servers,
        enhance_prompt_with_gguf_server,
        unload_cached_server,
    )
    from creative_treatments import CREATIVE_TREATMENT_SCHEMA_VERSION, VISUAL_LANGUAGE_PROFILES
    from prompt_enhancer import enhance_prompt
    from media_manifest import ASPECT_RATIOS, MAX_GENERATION_SECONDS, generation_profile, manifest_context, parse_media_manifest, parse_media_project
    from prompt_guides import ACOUSTIC_SPACE_CHOICES, ENHANCEMENT_PROFILES, DIALOGUE_COVERAGE_CHOICES, DIALOGUE_LANGUAGE_CHOICES, EDITING_INTENT_CHOICES, INSTRUMENTAL_STYLE_CHOICES, build_user_request, normalize_multishot_output, resolve_mode, system_prompt_for_mode, treatment_warning_report, validate_prompt
    from title_credits import TITLE_ENERGIES, TITLE_RECIPES, TITLE_RECIPE_DISABLED, append_title_lock, title_briefing
    from reference_director import REFERENCE_PROJECT_TYPE, build_reference_project, reference_context_for_project
    from reference_media import load_generation_media


MODE_CHOICES = ["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va", "chained_multishot"]
GENERATION_DURATION_INPUT = {"default": 5.0, "min": 4.0, "max": MAX_GENERATION_SECONDS, "step": 0.01,
                             "tooltip": "4-150 seconds. H3 was trained around 5-15 seconds; longer generations are experimental and require much more memory."}
FRAME_COUNT_INPUT = {"default": 0, "min": 0, "max": 3600, "step": 1,
                     "tooltip": "Leave 0 to use Duration. A nonzero exact count must follow 17 × n + 5. Above about 362 frames (~15 s) is experimental."}
# Derivada del catalogo, no escrita a mano: la lista fija habia divergido hasta ofrecer
# "papercraft_stop_motion", que no existe como perfil y lanzaba ValueError al elegirlo,
# mientras 36 perfiles reales -entre ellos supermarionation y live_action_visceral_horror-
# no se podian seleccionar. Derivarla hace imposible que vuelvan a separarse.
VISUAL_STYLE_PRESET_CHOICES = ["none"] + sorted(
    name for name in VISUAL_LANGUAGE_PROFILES if name != "none"
)

H3_ASPECT_RATIO_DIMENSIONS = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (1080, 1080),
    "4:3": (960, 720),
    "3:4": (720, 960),
    "21:9": (1680, 720),
    "auto": (1280, 720),
}

H3_ASPECT_RATIO_VALUES = {
    "16:9": 16.0 / 9.0,
    "9:16": 9.0 / 16.0,
    "1:1": 1.0,
    "4:3": 4.0 / 3.0,
    "3:4": 3.0 / 4.0,
    "21:9": 21.0 / 9.0,
    "auto": 16.0 / 9.0,
}


def h3_dimensions_for_aspect_ratio(aspect_ratio: str, target_megapixels: float = 0.0, multiple_of: int = 16) -> tuple[int, int]:
    """Return aligned (width, height) pixel dimensions for MiniMax H3 aspect ratio and optional target megapixels."""
    ratio_str = str(aspect_ratio or "").strip().lower()
    try:
        mp = float(target_megapixels or 0.0)
    except (TypeError, ValueError):
        mp = 0.0
    if not math.isfinite(mp) or mp <= 0.0:
        return H3_ASPECT_RATIO_DIMENSIONS.get(ratio_str, (1280, 720))

    r = H3_ASPECT_RATIO_VALUES.get(ratio_str, 16.0 / 9.0)
    total_pixels = mp * 1_000_000.0
    h = math.sqrt(total_pixels / r)
    w = h * r

    w_aligned = max(multiple_of, int(round(w / multiple_of)) * multiple_of)
    h_aligned = max(multiple_of, int(round(h / multiple_of)) * multiple_of)
    return (w_aligned, h_aligned)


# Two booleans spanned four states for three meanings, and the spare one lied: enhance off with
# invent on showed a UI promising an invented scene while the node silently ran the most
# conservative profile there is. One ordered widget cannot express that state at all.
CREATIVE_LATITUDE_CHOICES = ENHANCEMENT_PROFILES
CREATIVE_LATITUDE_INPUT = (list(CREATIVE_LATITUDE_CHOICES), {
    "default": "enhanced_production",
    "tooltip": (
        "How far beyond your text the writer may go. verbatim_source: none - keep your wording, "
        "facts and terseness as written; only reformat into H3 sections, apply the selected style "
        "and translate delivery marks. conservative_grounded: only the minimum "
        "structure the H3 mode requires. enhanced_production: resolve unspecified production "
        "decisions - composition, blocking, lighting, micro-performance. invented_production: "
        "treat your text as a premise and build the world around it. Quoted dialogue, reference "
        "identities, duration, shot count, ending and gore level stay locked at every level."
    ),
})


def _normalize_latitude(creative_latitude) -> str:
    latitude = str(creative_latitude or "enhanced_production").strip().lower()
    return latitude if latitude in CREATIVE_LATITUDE_CHOICES else "enhanced_production"


def _latitude_flags(creative_latitude: str) -> tuple[bool, bool]:
    """Translate the widget back into the two flags the guide functions still take.

    The pair cannot express verbatim_source, which is why the resolved name is threaded
    separately to system_prompt_for_mode. Collapsing it here would silently downgrade the
    strictest profile to the second strictest.
    """
    latitude = _normalize_latitude(creative_latitude)
    return latitude not in ("conservative_grounded", "verbatim_source"), latitude == "invented_production"


def _resolved_latitude_name(creative_latitude=None, enhance_description=None, invent_scene=None) -> str:
    """The profile name to hand the guides, including the one the legacy pair cannot encode."""
    if creative_latitude is not None and not isinstance(creative_latitude, bool):
        return _normalize_latitude(creative_latitude)
    enhance, invent = _resolve_latitude(creative_latitude, enhance_description, invent_scene)
    if not enhance:
        return "conservative_grounded"
    return "invented_production" if invent else "enhanced_production"


def _resolve_latitude(creative_latitude=None, enhance_description=None, invent_scene=None):
    """Accept the widget, or the legacy pair still used by API callers and older workflows."""
    if creative_latitude is not None and not isinstance(creative_latitude, bool):
        return _latitude_flags(creative_latitude)
    # A workflow saved before the swap holds a boolean in this slot; honour what it meant.
    if isinstance(creative_latitude, bool):
        enhance_description = creative_latitude if enhance_description is None else enhance_description
    enhance = True if enhance_description is None else bool(enhance_description)
    return enhance, enhance and bool(invent_scene)


def _merge_visual_style_preset(creative_treatment_json: str, visual_style_preset: str = "none") -> str:
    preset = str(visual_style_preset or "none").strip().lower()
    if preset in ("none", ""):
        return creative_treatment_json or ""
    if not creative_treatment_json or not str(creative_treatment_json).strip():
        return json.dumps({"schemaVersion": CREATIVE_TREATMENT_SCHEMA_VERSION, "visualLanguage": preset})
    try:
        data = json.loads(creative_treatment_json)
        if data is None or data is False:
            return json.dumps({"schemaVersion": CREATIVE_TREATMENT_SCHEMA_VERSION, "visualLanguage": preset})
        if isinstance(data, dict):
            if data.get("visualLanguage", "none") in ("none", ""):
                source_version = data.get("schemaVersion")
                if type(source_version) is int and source_version in (1, CREATIVE_TREATMENT_SCHEMA_VERSION):
                    data["schemaVersion"] = CREATIVE_TREATMENT_SCHEMA_VERSION
                data["visualLanguage"] = preset
                return json.dumps(data)
    except Exception:
        pass
    return creative_treatment_json


class MiniMaxH3PromptGuideBuilder:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "build"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("system_prompt", "user_prompt", "resolved_mode", "treatment_warnings", "width", "height")
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
            "creative_latitude": CREATIVE_LATITUDE_INPUT,

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
            "creative_treatment_json": ("STRING", {"multiline": True, "default": "", "placeholder": CREATIVE_TREATMENT_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Stable schema-v2 storage for the optional creative-treatment selectors. Legacy v1 remains runtime-compatible; blank is neutral."}),
            "shot_plan_json": ("STRING", {"multiline": True, "default": "", "placeholder": SHOT_PLAN_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional authoritative shot plan. Schema v1 remains compatible; v2 adds generations, presence, states, environments and start/path/end camera. Blank preserves automatic planning."}),
            "cinematography_json": ("STRING", {"multiline": True, "default": "", "placeholder": CINEMATOGRAPHY_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v2 manual color, camera, optics, focus, texture, and motion-rendering controls. Legacy v1 remains runtime-compatible; blank is neutral."}),
            "instrumental_style": (list(INSTRUMENTAL_STYLE_CHOICES), {"default": "none", "tooltip": "When instrumental score is enabled, adapt its arrangement to this musical language while preserving compatible user direction."}),
            "acoustic_space": (list(ACOUSTIC_SPACE_CHOICES), {"default": "none", "tooltip": "Diegetic sound space for the permitted ambience, foley, and voices. It renders existing sounds; it never adds a source."}),
            "dialogue_coverage": (list(DIALOGUE_COVERAGE_CHOICES), {"default": "off", "tooltip": "Keep every speaking character's mouth and eyes unobstructed, in focus, and framed at medium close-up or tighter for the whole line."}),
            "dialogue_language": (list(DIALOGUE_LANGUAGE_CHOICES), {"default": "auto", "tooltip": "Target dialogue language. 'auto' automatically detects language from prompt context/dialogue."}),
            "visual_style_preset": (list(VISUAL_STYLE_PRESET_CHOICES), {"default": "none", "tooltip": "Quick visual style preset. When selected, automatically applies this visual language unless overridden in creative treatment JSON."}),
            "target_megapixels": ("FLOAT", {"default": 0.0, "step": 0.01, "tooltip": "Target resolution in Megapixels (MP), e.g. 0.2, 0.3, 0.5, 0.92 (720p), 2.0 (1080p). Leave 0.0 for standard defaults; Custom accepts any positive finite value."}),
            "editing_intent": (list(EDITING_INTENT_CHOICES), {"default": "none", "tooltip": "Quick video editing intent preset for Ref2VA (Character Swap, Wardrobe Transfer, Voice/Dialogue Swap, Background Change, Motion Transfer, Custom Editing). Automatically enforces video editing summary and retention policies."}),
            "lora_trigger_words": ("STRING", {"default": "", "placeholder": LORA_TRIGGER_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Trigger tokens for the LoRAs loaded elsewhere in the graph. Appended verbatim to the end of the description after enhancement and validation, so they never pass through the LLM and survive character for character."}),
            "reference_director_json": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False, "tooltip": "Prompt Studio physical-reference storage. Appended last for saved-workflow compatibility."}),
        }}

    def build(self, basic_prompt, mode, duration_seconds, reference_context, enhance_description=True,
              ambience_foley_policy="auto", background_score_policy="follow_prompt",
              voice_performance="audible", instrumental_description="", aspect_ratio="auto",
              media_manifest="", multishot_shot_count=0, frame_count=0,
              multishot_identity_lock="", multishot_voice_lock="", multishot_setting_lock="",
              show_advanced_controls=False, creative_treatment_json="", shot_plan_json="",
              cinematography_json="", instrumental_style="none", acoustic_space="none",
              dialogue_coverage="off", dialogue_language="auto", visual_style_preset="none",
              target_megapixels=0.0, editing_intent="none", invent_scene=False, creative_latitude=None,
              lora_trigger_words="", reference_director_json=""):
        latitude_name = _resolved_latitude_name(creative_latitude, enhance_description, invent_scene)
        enhance_description, invent_scene = _resolve_latitude(
            creative_latitude, enhance_description, invent_scene)
        if not str(basic_prompt).strip():
            raise ValueError("basic_prompt cannot be empty")
        resolved = resolve_mode(mode, reference_context, basic_prompt, media_manifest, editing_intent=editing_intent)
        merged_treatment = _merge_visual_style_preset(creative_treatment_json, visual_style_preset)
        width, height = h3_dimensions_for_aspect_ratio(aspect_ratio, target_megapixels)
        return (
            system_prompt_for_mode(resolved, latitude_name if latitude_name == "verbatim_source"
                                   else bool(enhance_description), invent_scene),
            build_user_request(
                basic_prompt, resolved, duration_seconds, reference_context, enhance_description,
                ambience_foley_policy, background_score_policy, voice_performance,
                instrumental_description,
                aspect_ratio, media_manifest, multishot_shot_count, frame_count,
                multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
                (), merged_treatment, shot_plan_json, cinematography_json, instrumental_style,
                acoustic_space, dialogue_coverage, dialogue_language=dialogue_language,
                editing_intent=editing_intent,
                invent_scene=invent_scene,
            ),
            resolved,
            treatment_warning_report(
                merged_treatment, cinematography_json, shot_plan_json, duration_seconds,
                frame_count, resolved, enhance_description,
            ),
            width,
            height,
        )


class MiniMaxH3PromptEnhancer:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "enhance_with_ui"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "FLOAT", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = (
        "enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds", "aspect_ratio",
        "treatment_warnings", "width", "height",
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
            "max_tokens": ("INT", {"default": 8192, "min": 512, "max": 32768, "step": 256}),
            "timeout_seconds": ("INT", {"default": 300, "min": 10, "max": 1800, "step": 10}),
            "repair_attempts": ("INT", {"default": 2, "min": 0, "max": 4, "step": 1}),
            "disable_thinking": ("BOOLEAN", {"default": True, "tooltip": "Faster, cleaner structured output on Qwen thinking models"}),
            "allow_remote_endpoint": ("BOOLEAN", {"default": False}),
        }, "optional": {
            "use_remote_model": ("BOOLEAN", {"default": True, "tooltip": "Use endpoint/model when enabled; use the selected local GGUF when disabled"}),
            "creative_latitude": CREATIVE_LATITUDE_INPUT,

            "ambience_foley_policy": (["auto", "ensure_audible", "off"], {"default": "auto", "tooltip": "Scene sounds other than speech or music: rain, wind, room tone, footsteps, clothing, doors, impacts, engines, breathing, and similar physical sounds."}),
            "background_score_policy": (["follow_prompt", "add_instrumental", "off"], {"default": "follow_prompt", "tooltip": "Background score: follow the prompt, add instrumental music, or force it off"}),
            "instrumental_description": ("STRING", {"multiline": True, "default": "", "placeholder": INSTRUMENTAL_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Describe concrete instrumentation, tempo, rhythm, and dynamics; mood words are translated into audible parameters."}),
            "voice_performance": (["audible", "silent_mouth_acting_experimental", "none"], {"default": "audible", "tooltip": "Silent mouth acting is experimental prompt guidance, not guaranteed lip sync or silence"}),
            "local_model": (available_gguf_models(), {"tooltip": "Text GGUF models found in ComfyUI/models/llm_gguf; the first discovered model is the default"}),
            "llama_server_path": (available_llama_servers(), {"tooltip": "Detected llama.cpp llama-server executable used to run the selected GGUF; this is not a separate model or API backend"}),
            "gpu_layers": ("STRING", {"default": "auto", "tooltip": "auto, all, -1, or an exact layer count"}),
            "context_size": ("INT", {"default": DEFAULT_LOCAL_CONTEXT_SIZE, "min": 0, "max": 131072, "step": 1024, "tooltip": "0 uses the safe 32768-token default (including migrated workflows)"}),
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
            "creative_treatment_json": ("STRING", {"multiline": True, "default": "", "placeholder": CREATIVE_TREATMENT_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Stable schema-v2 storage for genre, visual language, world aesthetic, and tone. Legacy v1 remains runtime-compatible; blank is neutral."}),
            "shot_plan_json": ("STRING", {"multiline": True, "default": "", "placeholder": SHOT_PLAN_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional authoritative shot plan. Schema v1 remains compatible; v2 adds generations, presence, states, environments and start/path/end camera. Blank preserves automatic planning."}),
            "cinematography_json": ("STRING", {"multiline": True, "default": "", "placeholder": CINEMATOGRAPHY_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v2 manual color, camera, optics, focus, texture, and motion-rendering controls. Legacy v1 remains runtime-compatible; blank is neutral."}),
            "instrumental_style": (list(INSTRUMENTAL_STYLE_CHOICES), {"default": "none", "tooltip": "When instrumental score is enabled, adapt its arrangement to this musical language while preserving compatible user direction."}),
            "acoustic_space": (list(ACOUSTIC_SPACE_CHOICES), {"default": "none", "tooltip": "Diegetic sound space for the permitted ambience, foley, and voices. It renders existing sounds; it never adds a source."}),
            "dialogue_coverage": (list(DIALOGUE_COVERAGE_CHOICES), {"default": "off", "tooltip": "Keep every speaking character's mouth and eyes unobstructed, in focus, and framed at medium close-up or tighter for the whole line."}),
            # Appended last on purpose: ComfyUI stores widget values positionally, so a new control
            # anywhere else would shift every saved workflow's widgets_values by one slot.
            "always_re_enhance": ("BOOLEAN", dict(ALWAYS_RE_ENHANCE_INPUT)),
            "delivery_target": (["local", "api_v2"], {"default": "local", "tooltip": "API v2 makes the 7000-character text-block limit repairable and hard."}),
            "dialogue_language": (list(DIALOGUE_LANGUAGE_CHOICES), {"default": "auto", "tooltip": "Target dialogue language. 'auto' automatically detects language from prompt context/dialogue."}),
            "visual_style_preset": (list(VISUAL_STYLE_PRESET_CHOICES), {"default": "none", "tooltip": "Quick visual style preset. When selected, automatically applies this visual language unless overridden in creative treatment JSON."}),
            "target_megapixels": ("FLOAT", {"default": 0.0, "step": 0.01, "tooltip": "Target resolution in Megapixels (MP), e.g. 0.2, 0.3, 0.5, 0.92 (720p), 2.0 (1080p). Leave 0.0 for standard defaults; Custom accepts any positive finite value."}),
            "editing_intent": (list(EDITING_INTENT_CHOICES), {"default": "none", "tooltip": "Quick video editing intent preset for Ref2VA (Character Swap, Wardrobe Transfer, Voice/Dialogue Swap, Background Change, Motion Transfer, Custom Editing). Automatically enforces video editing summary and retention policies."}),
            "lora_trigger_words": ("STRING", {"default": "", "placeholder": LORA_TRIGGER_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Trigger tokens for the LoRAs loaded elsewhere in the graph. Appended verbatim to the end of the description after enhancement and validation, so they never pass through the LLM and survive character for character."}),
            "title_sequence_recipe": ([TITLE_RECIPE_DISABLED, *TITLE_RECIPES], {"default": TITLE_RECIPE_DISABLED, "tooltip": "Turn the enhancer into a cinematic titles and credits director. Existing workflows remain disabled."}),
            "title_sequence_energy": (list(TITLE_ENERGIES), {"default": "balanced", "tooltip": "Overall motion, lighting, and sound intensity. Readable holds always remain still."}),
            "title_text": ("STRING", {"multiline": True, "default": "", "placeholder": "Exact main title; line breaks create one stacked composition.", "dynamicPrompts": False}),
            "credit_lines": ("STRING", {"multiline": True, "default": "", "placeholder": "One card per line: Role | Name", "dynamicPrompts": False}),
            "title_placement": (["after credits", "before credits"], {"default": "after credits"}),
            "reference_director_json": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False, "tooltip": "Prompt Studio physical-reference storage. Appended last for saved-workflow compatibility."}),
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
                gpu_layers="auto", context_size=DEFAULT_LOCAL_CONTEXT_SIZE, threads=0,
                startup_timeout=DEFAULT_LOCAL_STARTUP_TIMEOUT,
                keep_server_loaded=False, enhance_description=True, ambience_foley_policy="auto",
                background_score_policy="follow_prompt", voice_performance="audible",
                instrumental_description="", aspect_ratio="auto", media_manifest="",
                multishot_shot_count=0, frame_count=0, multishot_identity_lock="",
                multishot_voice_lock="", multishot_setting_lock="", show_advanced_controls=False,
                creative_treatment_json="", shot_plan_json="", cinematography_json="",
                instrumental_style="none", acoustic_space="none", dialogue_coverage="off",
                always_re_enhance=False, delivery_target="local", dialogue_language="auto",
                visual_style_preset="none", target_megapixels=0.0, editing_intent="none",
                invent_scene=False, creative_latitude=None,
                lora_trigger_words="", title_sequence_recipe=TITLE_RECIPE_DISABLED,
                title_sequence_energy="balanced", title_text="", credit_lines="",
                title_placement="after credits", reference_director_json=""):
        latitude_name = _resolved_latitude_name(creative_latitude, enhance_description, invent_scene)
        enhance_description, invent_scene = _resolve_latitude(
            creative_latitude, enhance_description, invent_scene)
        # always_re_enhance only drives IS_CHANGED caching; enhancement itself ignores it.
        creative_treatment_json = _merge_visual_style_preset(creative_treatment_json, visual_style_preset)
        width, height = h3_dimensions_for_aspect_ratio(aspect_ratio, target_megapixels)
        cards = []
        if title_sequence_recipe != TITLE_RECIPE_DISABLED:
            resolved_title_mode = resolve_mode(
                mode, reference_context, basic_prompt, media_manifest, editing_intent=editing_intent)
            if resolved_title_mode == "chained_multishot":
                raise ValueError(
                    "Cinematic titles and credits require auto, t2va, or ref2va mode; "
                    "chained_multishot returns JSON and cannot carry a title text lock."
                )
            title_duration = generation_profile(
                duration_seconds, aspect_ratio, frame_count)["effectiveDurationSeconds"]
            basic_prompt, cards = title_briefing(
                basic_prompt, title_sequence_recipe, title_sequence_energy, title_text, credit_lines,
                title_placement, title_duration, aspect_ratio,
            )
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
                    delivery_target != "local", dialogue_language != "auto", editing_intent != "none")):
                remote_args += (aspect_ratio, media_manifest, multishot_shot_count, frame_count,
                                multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
                                creative_treatment_json, shot_plan_json, cinematography_json,
                                instrumental_style, acoustic_space, dialogue_coverage, delivery_target,
                                dialogue_language, editing_intent)
            prompt, validation, manifest = enhance_prompt(
                *remote_args, invent_scene=invent_scene, lora_trigger_words=lora_trigger_words,
                creative_latitude=latitude_name)
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
                    delivery_target != "local", dialogue_language != "auto", editing_intent != "none")):
                local_args += (aspect_ratio, media_manifest, multishot_shot_count, frame_count,
                               multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
                               creative_treatment_json, shot_plan_json, cinematography_json,
                               instrumental_style, acoustic_space, dialogue_coverage, delivery_target,
                               dialogue_language, editing_intent)
            prompt, validation, manifest = enhance_prompt_with_gguf_server(
                *local_args, invent_scene=invent_scene, lora_trigger_words=lora_trigger_words,
                creative_latitude=latitude_name)
        if cards:
            prompt = append_title_lock(prompt, cards)
            manifest = dict(manifest)
            manifest["titleSequence"] = {
                "recipe": title_sequence_recipe,
                "energy": title_sequence_energy,
                "cardCount": len(cards),
            }
        return (
            prompt,
            json.dumps(validation, ensure_ascii=False, indent=2),
            json.dumps(manifest, ensure_ascii=False, indent=2),
            _effective_duration(validation, duration_seconds),
            str(aspect_ratio),
            "\n".join(manifest.get("treatmentWarnings", ())),
            width,
            height,
        )

    def enhance_with_ui(self, *args, **kwargs):
        result = self.enhance(*args, **kwargs)
        return {
            "ui": {"minimax_h3_diagnostics": _diagnostic_ui_payload(result[1], result[0], result[2])},
            "result": result,
        }


class MiniMaxH3GGUFPromptEnhancer:
    CATEGORY = "MiniMax H3/Prompting"
    FUNCTION = "enhance_with_ui"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "FLOAT", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = (
        "enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds", "aspect_ratio",
        "treatment_warnings", "width", "height",
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
            "context_size": ("INT", {"default": DEFAULT_LOCAL_CONTEXT_SIZE, "min": 0, "max": 131072, "step": 1024, "tooltip": "0 uses the safe 32768-token default"}),
            "threads": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1, "tooltip": "0 uses llama-server's default"}),
            "temperature": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 2.0, "step": 0.05}),
            "max_tokens": ("INT", {"default": 8192, "min": 512, "max": 32768, "step": 256}),
            "request_timeout": ("INT", {"default": 300, "min": 10, "max": 1800, "step": 10}),
            "startup_timeout": ("INT", {"default": DEFAULT_LOCAL_STARTUP_TIMEOUT, "min": 0, "max": 1800, "step": 10, "tooltip": "0 uses the safe 180-second default"}),
            "repair_attempts": ("INT", {"default": 2, "min": 0, "max": 4, "step": 1}),
            "disable_thinking": ("BOOLEAN", {"default": True}),
            "creative_latitude": CREATIVE_LATITUDE_INPUT,

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
            "creative_treatment_json": ("STRING", {"multiline": True, "default": "", "placeholder": CREATIVE_TREATMENT_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Stable schema-v2 storage for genre, visual language, world aesthetic, and tone. Legacy v1 remains runtime-compatible; blank is neutral."}),
            "shot_plan_json": ("STRING", {"multiline": True, "default": "", "placeholder": SHOT_PLAN_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional authoritative shot plan. Schema v1 remains compatible; v2 adds generations, presence, states, environments and start/path/end camera. Blank preserves automatic planning."}),
            "cinematography_json": ("STRING", {"multiline": True, "default": "", "placeholder": CINEMATOGRAPHY_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Optional schema-v2 manual color, camera, optics, focus, texture, and motion-rendering controls. Legacy v1 remains runtime-compatible; blank is neutral."}),
            "instrumental_style": (list(INSTRUMENTAL_STYLE_CHOICES), {"default": "none", "tooltip": "When instrumental score is enabled, adapt its arrangement to this musical language while preserving compatible user direction."}),
            "acoustic_space": (list(ACOUSTIC_SPACE_CHOICES), {"default": "none", "tooltip": "Diegetic sound space for the permitted ambience, foley, and voices. It renders existing sounds; it never adds a source."}),
            "dialogue_coverage": (list(DIALOGUE_COVERAGE_CHOICES), {"default": "off", "tooltip": "Keep every speaking character's mouth and eyes unobstructed, in focus, and framed at medium close-up or tighter for the whole line."}),
            # Appended last on purpose: ComfyUI stores widget values positionally, so a new control
            # anywhere else would shift every saved workflow's widgets_values by one slot.
            "always_re_enhance": ("BOOLEAN", dict(ALWAYS_RE_ENHANCE_INPUT)),
            "delivery_target": (["local", "api_v2"], {"default": "local", "tooltip": "API v2 makes the 7000-character text-block limit repairable and hard."}),
            "dialogue_language": (list(DIALOGUE_LANGUAGE_CHOICES), {"default": "auto", "tooltip": "Target dialogue language. 'auto' automatically detects language from prompt context/dialogue."}),
            "visual_style_preset": (list(VISUAL_STYLE_PRESET_CHOICES), {"default": "none", "tooltip": "Quick visual style preset. When selected, automatically applies this visual language unless overridden in creative treatment JSON."}),
            "target_megapixels": ("FLOAT", {"default": 0.0, "step": 0.01, "tooltip": "Target resolution in Megapixels (MP), e.g. 0.2, 0.3, 0.5, 0.92 (720p), 2.0 (1080p). Leave 0.0 for standard defaults; Custom accepts any positive finite value."}),
            "editing_intent": (list(EDITING_INTENT_CHOICES), {"default": "none", "tooltip": "Quick video editing intent preset for Ref2VA (Character Swap, Wardrobe Transfer, Voice/Dialogue Swap, Background Change, Motion Transfer, Custom Editing). Automatically enforces video editing summary and retention policies."}),
            "lora_trigger_words": ("STRING", {"default": "", "placeholder": LORA_TRIGGER_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Trigger tokens for the LoRAs loaded elsewhere in the graph. Appended verbatim to the end of the description after enhancement and validation, so they never pass through the LLM and survive character for character."}),
            "reference_director_json": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False, "tooltip": "Prompt Studio physical-reference storage. Appended last for saved-workflow compatibility."}),
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
                enhance_description=True, keep_server_loaded=False, ambience_foley_policy="auto",
                background_score_policy="follow_prompt", voice_performance="audible",
                instrumental_description="", aspect_ratio="auto", media_manifest="",
                multishot_shot_count=0, frame_count=0, multishot_identity_lock="",
                multishot_voice_lock="", multishot_setting_lock="", show_advanced_controls=False,
                creative_treatment_json="", shot_plan_json="", cinematography_json="",
                instrumental_style="none", acoustic_space="none", dialogue_coverage="off",
                always_re_enhance=False, delivery_target="local", dialogue_language="auto",
                visual_style_preset="none", target_megapixels=0.0, editing_intent="none",
                invent_scene=False, creative_latitude=None,
              lora_trigger_words="", reference_director_json=""):
        latitude_name = _resolved_latitude_name(creative_latitude, enhance_description, invent_scene)
        enhance_description, invent_scene = _resolve_latitude(
            creative_latitude, enhance_description, invent_scene)
        # always_re_enhance only drives IS_CHANGED caching; enhancement itself ignores it.
        context_size, startup_timeout = _local_runtime_limits(context_size, startup_timeout)
        creative_treatment_json = _merge_visual_style_preset(creative_treatment_json, visual_style_preset)
        width, height = h3_dimensions_for_aspect_ratio(aspect_ratio, target_megapixels)
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
            acoustic_space, dialogue_coverage, delivery_target, dialogue_language,
            editing_intent,
            invent_scene=invent_scene,
            # Without this the local backend sees only bool(enhance_description) and
            # verbatim_source degrades into ordinary enhancement.
            creative_latitude=latitude_name,
            lora_trigger_words=lora_trigger_words,
        )
        return (
            prompt,
            json.dumps(validation, ensure_ascii=False, indent=2),
            json.dumps(manifest, ensure_ascii=False, indent=2),
            _effective_duration(validation, duration_seconds),
            str(aspect_ratio),
            "\n".join(manifest.get("treatmentWarnings", ())),
            width,
            height,
        )

    def enhance_with_ui(self, *args, **kwargs):
        result = self.enhance(*args, **kwargs)
        return {
            "ui": {"minimax_h3_diagnostics": _diagnostic_ui_payload(result[1], result[0], result[2])},
            "result": result,
        }


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


class MiniMaxH3VisualReferenceDirector:
    """Compile, explain and decode one visual reference project."""

    CATEGORY = "MiniMax H3/References"
    FUNCTION = "build"
    RETURN_TYPES = (REFERENCE_PROJECT_TYPE, "STRING", "IMAGE", "IMAGE", "AUDIO", "STRING", "STRING")
    RETURN_NAMES = ("reference_project", "reference_context", "pictures", "videos", "audios", "wiring_report", "reference_project_json")
    OUTPUT_IS_LIST = (False, False, True, True, True, False, False)
    DESCRIPTION = (
        "Visual source of truth for H3 references: semantic prompt context, typed bundle and decoded "
        "picture/video/audio outputs in the exact compiled order."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "reference_director_json": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
            "media_project": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
            "shot_plan_json": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
        }, "optional": {
            "generation_id": ("STRING", {"default": "", "tooltip": "Blank selects the first generation."}),
        }}

    def build(self, reference_director_json="", media_project="", shot_plan_json="", generation_id=""):
        project = build_reference_project(reference_director_json, media_project, shot_plan_json)
        if project.get("issues"):
            raise ValueError("Reference project is not ready: " + " ".join(project["issues"]))
        loaded = load_generation_media(project, generation_id)
        context = reference_context_for_project(project, loaded["generationId"])
        inputs = len(project.get("inputsByGeneration", {}).get(loaded["generationId"], []))
        report = f"Generation {loaded['generationId'] or '(none)'} · {len(project['director']['sources'])} physical sources · {inputs} inputs"
        return (
            project,
            context,
            loaded["pictures"],
            loaded["videos"],
            loaded["audios"],
            report,
            json.dumps(project, ensure_ascii=False, indent=2),
        )


class MiniMaxH3ReferenceProjectInspector:
    """Turn the typed Director bundle into deterministic, inspectable file lists."""

    CATEGORY = "MiniMax H3/References"
    FUNCTION = "inspect"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("reference_project_json", "wiring_report", "picture_files", "video_files", "audio_files")
    DESCRIPTION = (
        "Inspect the typed reference_project output before connecting it to an H3 conditioning adapter. "
        "File lists preserve the same physical order used by the prompt labels."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"reference_project": (REFERENCE_PROJECT_TYPE,)}, "optional": {
            "generation_id": ("STRING", {"default": "", "tooltip": "Blank selects the first generation in the bundle."}),
        }}

    def inspect(self, reference_project, generation_id=""):
        if not isinstance(reference_project, dict) or reference_project.get("format") != "minimax-h3-reference-project":
            raise ValueError("Connect a MiniMax H3 reference_project output.")
        by_generation = reference_project.get("inputsByGeneration", {})
        selected_id = str(generation_id or "")
        if selected_id not in by_generation:
            selected_id = next(iter(by_generation), "")
        inputs = by_generation.get(selected_id, [])
        files = {"picture": [], "video": [], "audio": []}
        lines = [f"Generation: {selected_id or '(none)'}"]
        for item in inputs:
            source = item.get("source") or {}
            filename = source.get("file")
            media_type = item.get("mediaType")
            lines.append(f"{item.get('label') or '?'} ← {item.get('assetId') or '?'} ← {filename or 'MISSING'}")
            if filename and media_type in files:
                files[media_type].append(filename)
        lines.extend(f"Issue: {issue}" for issue in reference_project.get("issues", []))
        return (
            json.dumps(reference_project, ensure_ascii=False, indent=2),
            "\n".join(lines),
            json.dumps(files["picture"], ensure_ascii=False),
            json.dumps(files["video"], ensure_ascii=False),
            json.dumps(files["audio"], ensure_ascii=False),
        )


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
        compiled = parse_media_project(media_manifest)
        normalized = (
            compiled.get("canonicalJson", "")
            if compiled.get("schemaVersion") == 2 else
            json.dumps({key: value for key, value in parsed.items() if key not in {"warnings", "errors"}}, ensure_ascii=False, indent=2)
        )
        report = {
            "valid": bool(compiled.get("valid", not parsed["errors"])),
            "errors": list(compiled.get("errors", parsed["errors"])),
            "warnings": list(compiled.get("warnings", parsed["warnings"])),
            "counts": parsed.get("counts", {}),
        }
        report_text = json.dumps(report, ensure_ascii=False, indent=2)
        return {
            "ui": {
                "text": [report_text],
                "minimax_h3_diagnostics": _diagnostic_ui_payload({
                    **report,
                    "diagnostics": compiled.get("diagnostics", ()),
                }),
            },
            "result": (normalized, report["valid"], report_text, manifest_context(media_manifest)),
        }


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
        if not isinstance(package, dict) or package.get("schemaVersion") not in {1, 2}:
            raise ValueError("No supported schema-v1/v2 shotsPackage was found")
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
            "creative_latitude": CREATIVE_LATITUDE_INPUT,

            "delivery_target": (["local", "api_v2"], {"default": "local", "tooltip": "API v2 treats the 7000-character text-block limit as a hard error; local mode reports compatibility only."}),
            "instrumental_description": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
            "instrumental_style": (list(INSTRUMENTAL_STYLE_CHOICES), {"default": "none"}),
            "acoustic_space": (list(ACOUSTIC_SPACE_CHOICES), {"default": "none"}),
            "dialogue_coverage": (list(DIALOGUE_COVERAGE_CHOICES), {"default": "off"}),
            "dialogue_language": (list(DIALOGUE_LANGUAGE_CHOICES), {"default": "auto"}),
            "editing_intent": (list(EDITING_INTENT_CHOICES), {"default": "none"}),
            "lora_trigger_words": ("STRING", {"default": "", "placeholder": LORA_TRIGGER_PLACEHOLDER, "dynamicPrompts": False, "tooltip": "Trigger tokens for the LoRAs loaded elsewhere in the graph. Appended verbatim to the end of the description after enhancement and validation, so they never pass through the LLM and survive character for character."}),
        }}

    def validate(self, prompt, mode, duration_seconds, source_prompt, reference_context,
                 ambience_foley_policy="auto", background_score_policy="follow_prompt",
                 voice_performance="audible", aspect_ratio="auto", media_manifest="",
                 multishot_shot_count=0, frame_count=0, multishot_identity_lock="",
                 multishot_voice_lock="", multishot_setting_lock="", show_advanced_controls=False,
                 creative_treatment_json="", shot_plan_json="", cinematography_json="",
                 enhance_description=True, delivery_target="local", instrumental_description="",
                 instrumental_style="none", acoustic_space="none", dialogue_coverage="off",
                 dialogue_language="auto", editing_intent="none", invent_scene=False, creative_latitude=None,
              lora_trigger_words=""):
        # validate_prompt does not take the profile, so it is resolved only for its side effect
        # on enhance_description below.
        _resolved_latitude_name(creative_latitude, enhance_description, invent_scene)
        enhance_description, invent_scene = _resolve_latitude(
            creative_latitude, enhance_description, invent_scene)
        report = validate_prompt(
            prompt, mode, duration_seconds, source_prompt, reference_context,
            ambience_foley_policy, background_score_policy, voice_performance,
            aspect_ratio, media_manifest, multishot_shot_count, frame_count,
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
            (), creative_treatment_json, shot_plan_json, cinematography_json,
            enhance_description=bool(enhance_description), delivery_target=delivery_target,
            instrumental_description=instrumental_description, instrumental_style=instrumental_style,
            acoustic_space=acoustic_space, dialogue_coverage=dialogue_coverage,
            dialogue_language=dialogue_language,
            editing_intent=editing_intent,
        )
        report_text = json.dumps(report, ensure_ascii=False, indent=2)
        return {
            "ui": {
                "text": [str(prompt), report_text],
                "minimax_h3_diagnostics": _diagnostic_ui_payload(report, str(prompt)),
            },
            "result": (str(prompt), bool(report["valid"]), report_text),
        }
