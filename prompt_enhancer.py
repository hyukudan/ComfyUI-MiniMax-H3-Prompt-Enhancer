# SPDX-License-Identifier: GPL-3.0-only
"""Provider-neutral OpenAI-compatible MiniMax H3 prompt enhancement."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from .media_manifest import manifest_context
    from .prompt_guides import build_user_request, normalize_audio_policy, normalize_dialogue_tags, normalize_first_shot_marker, normalize_multishot_output, normalize_reference_definitions, normalize_section_headers, normalize_shot_timeline, normalize_shot_timestamps, normalize_source_dialogue, normalize_unassigned_subjects, resolve_mode, strip_markdown_fence, system_prompt_for_mode, validate_prompt
except ImportError:  # pragma: no cover - direct test/import compatibility
    from media_manifest import manifest_context
    from prompt_guides import build_user_request, normalize_audio_policy, normalize_dialogue_tags, normalize_first_shot_marker, normalize_multishot_output, normalize_reference_definitions, normalize_section_headers, normalize_shot_timeline, normalize_shot_timestamps, normalize_source_dialogue, normalize_unassigned_subjects, resolve_mode, strip_markdown_fence, system_prompt_for_mode, validate_prompt


def _api_root(endpoint: str) -> str:
    value = str(endpoint).strip().rstrip("/")
    if not value:
        raise ValueError("OpenAI-compatible endpoint is required")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Endpoint must be an absolute http(s) URL")
    return value[:-17] if value.endswith("/chat/completions") else value


def _require_allowed_endpoint(endpoint: str, allow_remote_endpoint: bool) -> None:
    host = (urlparse(endpoint).hostname or "").lower()
    local = host in {"localhost", "::1"} or host.startswith("127.")
    if not local and not allow_remote_endpoint:
        raise ValueError("Remote LLM endpoints are disabled; enable allow_remote_endpoint explicitly")


def _request_json(url: str, payload: dict | None, api_key: str, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        with urlopen(Request(url, data=body, headers=headers), timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"LLM endpoint returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Cannot reach LLM endpoint {url}: {exc.reason}") from exc


def available_models(root: str, api_key: str = "", timeout: int = 30) -> list[str]:
    """List chat-capable candidates while excluding obvious embedding/reranking endpoints."""
    payload = _request_json(root + "/models", None, api_key, timeout)
    ids = [str(item.get("id", "")).strip() for item in (payload.get("data") or [])]
    return [item for item in ids if item and not any(token in item.lower() for token in ("embedding", "embed-", "rerank"))]


def discover_models(endpoint: str, api_key: str = "", allow_remote_endpoint: bool = False,
                    timeout: int = 15) -> list[str]:
    """Safely discover selectable chat models for the ComfyUI frontend."""
    root = _api_root(endpoint)
    _require_allowed_endpoint(root, bool(allow_remote_endpoint))
    return available_models(root, str(api_key or ""), max(3, min(int(timeout), 60)))


def _compact_model_rank(model_id: str) -> tuple[int, int]:
    """Prefer a small local instruct model for auto mode instead of accidentally loading a 30B model."""
    value = model_id.lower()
    compact = bool(re.search(r"(?:^|[-_/])(?:0[._]?\d+|[1-8])b(?:$|[-_/])", value) or "e4b" in value)
    instruct = any(token in value for token in ("instruct", "-it", "heretic", "abliterated"))
    return (0 if compact else 1, 0 if instruct else 1)


def _model_name(root: str, requested: str, api_key: str, timeout: int) -> str:
    if str(requested).strip():
        return str(requested).strip()
    models = available_models(root, api_key, timeout)
    if not models:
        raise ValueError("No model was supplied and the endpoint returned no loaded models")
    return min(enumerate(models), key=lambda item: (_compact_model_rank(item[1]), item[0]))[1]


def _completion(root: str, model: str, messages: list[dict], api_key: str,
                temperature: float, max_tokens: int, timeout: int,
                disable_thinking: bool = True,
                prefer_lm_studio_native: bool = True) -> str:
    if disable_thinking and prefer_lm_studio_native:
        native_root = root[:-3] if root.endswith("/v1") else root
        native_payload = {
            "model": model,
            "system_prompt": "\n\n".join(
                str(item.get("content", "")) for item in messages if item.get("role") == "system"
            ),
            "input": "\n\n".join(
                f"{str(item.get('role', 'user')).upper()}:\n{str(item.get('content', ''))}"
                for item in messages if item.get("role") != "system"
            ),
            "temperature": float(temperature),
            "max_output_tokens": int(max_tokens),
            "reasoning": "off",
            "store": False,
        }
        try:
            native_response = _request_json(
                native_root + "/api/v1/chat", native_payload, api_key, timeout
            )
            content = "\n".join(
                str(item.get("content", ""))
                for item in (native_response.get("output") or [])
                if item.get("type") == "message" and item.get("content")
            ).strip()
            if content:
                return strip_markdown_fence(content)
        except RuntimeError:
            # Non-LM-Studio OpenAI-compatible servers do not expose this endpoint.
            pass

    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "stream": False,
    }
    if disable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    response = _request_json(root + "/chat/completions", payload, api_key, timeout)
    try:
        return strip_markdown_fence(response["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("LLM endpoint returned no choices[0].message.content") from exc


def enhance_prompt_with_completion(
    basic_prompt: str,
    mode: str,
    duration_seconds: float,
    reference_context: str,
    completion: Callable[[list[dict]], str],
    repair_attempts: int,
    manifest: dict,
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
) -> tuple[str, dict, dict]:
    """Apply the common MiniMax guide, normalization, validation, and repair loop."""
    basic_prompt = str(basic_prompt).strip()
    if not basic_prompt:
        raise ValueError("basic_prompt cannot be empty")
    user_request = build_user_request(
        basic_prompt, mode, duration_seconds, reference_context, enhance_description,
        ambience_foley_policy, background_score_policy, voice_performance, instrumental_description,
        aspect_ratio, media_manifest, multishot_shot_count, frame_count,
        multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
    )
    resolved_mode = resolve_mode(mode, reference_context, basic_prompt, media_manifest)
    effective_reference_context = "\n".join(
        part for part in (str(reference_context).strip(), manifest_context(media_manifest)) if part
    )
    messages = [
        {"role": "system", "content": system_prompt_for_mode(resolved_mode)},
        {"role": "user", "content": user_request},
    ]
    def normalize_candidate(candidate: str) -> str:
        if resolved_mode == "chained_multishot":
            return normalize_multishot_output(candidate, (
                multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
            ))
        value = normalize_section_headers(candidate)
        value = normalize_dialogue_tags(value)
        value = normalize_first_shot_marker(value, resolved_mode)
        value = normalize_shot_timestamps(value)
        value = normalize_shot_timeline(value, resolved_mode, duration_seconds)
        value = normalize_reference_definitions(value, basic_prompt, effective_reference_context)
        value = normalize_unassigned_subjects(value, basic_prompt, effective_reference_context)
        value = normalize_source_dialogue(value, basic_prompt, resolved_mode, voice_performance)
        return normalize_audio_policy(
            value, ambience_foley_policy, background_score_policy, voice_performance,
            basic_prompt + "\n" + effective_reference_context,
        )

    enhanced = normalize_candidate(completion(messages))
    validation = validate_prompt(
        enhanced, mode, duration_seconds, basic_prompt, effective_reference_context,
        ambience_foley_policy, background_score_policy, voice_performance,
        aspect_ratio, media_manifest, multishot_shot_count, frame_count,
        multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
    )
    best_enhanced = enhanced
    best_validation = validation

    def candidate_score(report: dict) -> tuple[int, int]:
        errors = report.get("errors", ())
        critical_markers = (
            "Explicit ", "Quoted source", "Required spoken dialogue", "invented reference labels",
            "missing from output", "must remain", "terminal consequence",
        )
        weighted_errors = sum(
            10 if any(marker.casefold() in str(error).casefold() for marker in critical_markers) else 1
            for error in errors
        )
        return (weighted_errors, len(report.get("warnings", ())))

    attempts = 0
    while validation["errors"] and attempts < int(repair_attempts):
        attempts += 1
        messages.extend([
            {"role": "assistant", "content": enhanced},
            {"role": "user", "content": (
                "Repair the prompt. Return the complete corrected prompt only. Preserve all source facts and exact "
                "quoted content. Follow the selected mode's exact output contract. Fix these validation errors:\n- "
                + "\n- ".join(validation["errors"])
            )},
        ])
        enhanced = normalize_candidate(completion(messages))
        validation = validate_prompt(
            enhanced, mode, duration_seconds, basic_prompt, effective_reference_context,
            ambience_foley_policy, background_score_policy, voice_performance,
            aspect_ratio, media_manifest, multishot_shot_count, frame_count,
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
        )
        if candidate_score(validation) < candidate_score(best_validation):
            best_enhanced = enhanced
            best_validation = validation
    enhanced = best_enhanced
    validation = best_validation
    result_manifest = {
        **manifest,
        "mode": validation["mode"],
        "durationSeconds": float(duration_seconds),
        "repairAttemptsUsed": attempts,
        "descriptionEnhanced": bool(enhance_description),
        "referenceSemanticsVersion": 2,
        "audioPolicyVersion": 1,
        "promptContractVersion": 3,
        "mediaManifestSchemaVersion": 1,
        "mediaManifestDigest": (
            hashlib.sha256(str(media_manifest).encode("utf-8")).hexdigest()
            if str(media_manifest).strip() else ""
        ),
        "aspectRatio": aspect_ratio,
        "multishotPromptCount": validation.get("promptCount", 0),
        "frameCount": int(frame_count or 0),
        "effectiveDurationSeconds": validation.get("generationProfile", {}).get("effectiveDurationSeconds", float(duration_seconds)),
        "multishotLocksApplied": sum(bool(str(value).strip()) for value in (
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
        )),
        "ambienceFoleyPolicy": ambience_foley_policy,
        "backgroundScorePolicy": background_score_policy,
        "instrumentalDescription": (
            str(instrumental_description).strip() if background_score_policy == "add_instrumental" else ""
        ),
        "voicePerformance": voice_performance,
        "silentMouthActingExperimental": voice_performance == "silent_mouth_acting_experimental",
        "suppressedDialogueCount": (
            len(re.findall(r'[\"“][^\"”\r\n]+[\"”]', basic_prompt)) if voice_performance != "audible" else 0
        ),
        "voiceControlGuarantee": (
            "best_effort_prompt_only" if voice_performance == "silent_mouth_acting_experimental" else "documented"
        ),
        "valid": validation["valid"],
    }
    return enhanced, validation, result_manifest


def enhance_prompt(basic_prompt: str, mode: str, duration_seconds: float,
                   reference_context: str, endpoint: str, model: str, api_key: str,
                   temperature: float, max_tokens: int, timeout: int,
                   repair_attempts: int, allow_remote_endpoint: bool,
                   disable_thinking: bool = True,
                   enhance_description: bool = True,
                   ambience_foley_policy: str = "auto",
                   background_score_policy: str = "follow_prompt",
                   voice_performance: str = "audible",
                   instrumental_description: str = "", aspect_ratio: str = "auto",
                   media_manifest: str = "", multishot_shot_count: int = 0,
                   frame_count: int = 0, multishot_identity_lock: str = "",
                   multishot_voice_lock: str = "", multishot_setting_lock: str = "") -> tuple[str, dict, dict]:
    basic_prompt = str(basic_prompt).strip()
    if not basic_prompt:
        raise ValueError("basic_prompt cannot be empty")
    root = _api_root(endpoint)
    _require_allowed_endpoint(root, bool(allow_remote_endpoint))
    secret = str(api_key).strip() or os.getenv("MINIMAX_H3_PROMPT_ENHANCER_API_KEY", "")
    selected_model = _model_name(root, model, secret, int(timeout))

    def complete(messages: list[dict]) -> str:
        return _completion(
            root, selected_model, messages, secret, temperature, max_tokens, timeout, disable_thinking
        )

    return enhance_prompt_with_completion(
        basic_prompt,
        mode,
        duration_seconds,
        reference_context,
        complete,
        repair_attempts,
        {
            "provider": "local_chat_api",
            "endpoint": root,
            "model": selected_model,
            "temperature": float(temperature),
            "maxTokens": int(max_tokens),
            "thinkingDisabled": bool(disable_thinking),
            "lmStudioNativePreferred": bool(disable_thinking),
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
    )
