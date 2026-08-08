# SPDX-License-Identifier: GPL-3.0-only
"""Provider-neutral OpenAI-compatible MiniMax H3 prompt enhancement."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from .media_manifest import generation_profile, manifest_context
    from .prompt_guides import _dialogue_authoring_request, _dialogue_lexical_key, _source_dialogue_contracts, build_user_request, normalize_audio_policy, normalize_dialogue_tags, normalize_first_shot_marker, normalize_multishot_output, normalize_reference_definitions, normalize_section_headers, normalize_shot_timeline, normalize_shot_timestamps, normalize_source_dialogue, normalize_unassigned_subjects, resolve_mode, strip_markdown_fence, system_prompt_for_mode, validate_prompt
except ImportError:  # pragma: no cover - direct test/import compatibility
    from media_manifest import generation_profile, manifest_context
    from prompt_guides import _dialogue_authoring_request, _dialogue_lexical_key, _source_dialogue_contracts, build_user_request, normalize_audio_policy, normalize_dialogue_tags, normalize_first_shot_marker, normalize_multishot_output, normalize_reference_definitions, normalize_section_headers, normalize_shot_timeline, normalize_shot_timestamps, normalize_source_dialogue, normalize_unassigned_subjects, resolve_mode, strip_markdown_fence, system_prompt_for_mode, validate_prompt


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


def _parse_dialogue_ledger(candidate: str, requested_language: str, max_lines: int,
                           max_words: int, source_prompt: str) -> tuple[tuple[str, str], ...]:
    try:
        data = json.loads(strip_markdown_fence(candidate))
    except json.JSONDecodeError as exc:
        raise ValueError(f"ledger must be valid JSON: {exc.msg}") from exc
    lines = data.get("lines") if isinstance(data, dict) else None
    if not isinstance(lines, list) or not lines:
        raise ValueError('ledger must be an object with a non-empty "lines" array')
    if len(lines) > max_lines:
        raise ValueError(f"ledger has {len(lines)} lines; maximum is {max_lines}")
    source_keys = {
        _dialogue_lexical_key(text) for _language, text, _internal in _source_dialogue_contracts(source_prompt)
    }
    seen = set()
    ledger = []
    total_words = 0
    for index, item in enumerate(lines, start=1):
        if isinstance(item, str):
            language = requested_language
            text = item
            tagged = re.match(r"^\s*\[([^\]]+)\]\s+(.+)$", text, flags=re.DOTALL)
            if tagged:
                language, text = tagged.groups()
        elif isinstance(item, dict):
            language = str(item.get("language") or requested_language).strip()
            text = next((str(item[key]) for key in ("text", "line", "dialogue") if item.get(key)), "")
        else:
            raise ValueError(f"ledger line {index} must be a string or object")
        language = language.strip()
        text = re.sub(r"\s+", " ", text).strip()
        if not language or "[" in language or "]" in language:
            raise ValueError(f"ledger line {index} has an invalid language")
        if requested_language != "Original language" and language.casefold() != requested_language.casefold():
            raise ValueError(
                f"ledger line {index} must use {requested_language}, observed {language or 'no language'}"
            )
        if requested_language != "Original language":
            language = requested_language
        if not text or "<d>" in text.casefold() or "</d>" in text.casefold():
            raise ValueError(f"ledger line {index} must contain plain spoken words without <d> tags")
        if re.fullmatch(
            r"(?:\[.*?\]|<.*?>|dialogue|dialog|line|speech|spoken words?|to be (?:written|generated)|"
            r"di[aá]logo|l[ií]nea|frase|palabras)",
            text,
            flags=re.IGNORECASE,
        ):
            raise ValueError(f"ledger line {index} is a placeholder, not concrete dialogue")
        key = _dialogue_lexical_key(text)
        if key in source_keys:
            raise ValueError(f"ledger line {index} duplicates source-provided dialogue")
        if key in seen:
            raise ValueError(f"ledger line {index} duplicates another planned line")
        seen.add(key)
        total_words += len(re.findall(r"\b[\wÀ-ÿ'-]+\b", text))
        ledger.append((language, text))
    if total_words > max_words:
        raise ValueError(f"ledger has {total_words} spoken words; maximum is {max_words}")
    return tuple(ledger)


def _plan_dialogue_ledger(basic_prompt: str, requested_language: str, duration_seconds: float,
                          segment_count: int, completion: Callable[[list[dict]], str],
                          repair_attempts: int) -> tuple[tuple[tuple[str, str], ...], int]:
    segments = max(1, int(segment_count or 1))
    source_words = sum(
        len(re.findall(r"\b[\wÀ-ÿ'-]+\b", text))
        for _language, text, _internal in _source_dialogue_contracts(basic_prompt)
    )
    max_lines = min(12, max(1, math.ceil(float(duration_seconds) / 4.0) * segments))
    max_words = max(1, round(float(duration_seconds) * 2.5) * segments - source_words)
    messages = [
        {"role": "system", "content": (
            "You are a dialogue planner. Return only compact valid JSON, with no Markdown or explanation, shaped "
            'exactly as {"lines":[{"language":"Spanish","text":"Natural spoken line."}]}. Write only the new '
            "concrete words requested by the scenario. Do not include camera directions, speaker labels, delivery, "
            "<d> tags, placeholders, or source-provided quoted lines."
        )},
        {"role": "user", "content": (
            f"SCENARIO:\n{basic_prompt}\n\nREQUESTED LANGUAGE: {requested_language}\n"
            f"MAXIMUM LINES: {max_lines}\nMAXIMUM TOTAL SPOKEN WORDS: {max_words}\n"
            "Plan the smallest useful set of concise natural lines, in causal scenario order."
        )},
    ]
    last_error = ""
    repairs = max(0, int(repair_attempts))
    for attempt in range(repairs + 1):
        candidate = completion(messages)
        try:
            ledger = _parse_dialogue_ledger(
                candidate, requested_language, max_lines, max_words, basic_prompt,
            )
            return ledger, attempt
        except ValueError as exc:
            last_error = str(exc)
            if attempt >= repairs:
                break
            messages.extend([
                {"role": "assistant", "content": candidate},
                {"role": "user", "content": (
                    "Repair the dialogue ledger. Return the complete JSON object only. Fix this error: " + last_error
                )},
            ])
    raise RuntimeError(f"Dialogue planning failed: {last_error}")


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
    resolved_mode = resolve_mode(mode, reference_context, basic_prompt, media_manifest)
    dialogue_authoring, dialogue_language = _dialogue_authoring_request(basic_prompt)
    user_request = build_user_request(
        basic_prompt, mode, duration_seconds, reference_context, enhance_description,
        ambience_foley_policy, background_score_policy, voice_performance, instrumental_description,
        aspect_ratio, media_manifest, multishot_shot_count, frame_count,
        multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
    )
    dialogue_ledger: tuple[tuple[str, str], ...] = ()
    dialogue_planning_repairs = 0
    if dialogue_authoring and voice_performance == "audible":
        effective_duration = generation_profile(duration_seconds, aspect_ratio, frame_count)["effectiveDurationSeconds"]
        dialogue_ledger, dialogue_planning_repairs = _plan_dialogue_ledger(
            basic_prompt,
            dialogue_language,
            effective_duration,
            multishot_shot_count if resolved_mode == "chained_multishot" else 1,
            completion,
            repair_attempts,
        )
        user_request = build_user_request(
            basic_prompt, mode, duration_seconds, reference_context, enhance_description,
            ambience_foley_policy, background_score_policy, voice_performance, instrumental_description,
            aspect_ratio, media_manifest, multishot_shot_count, frame_count,
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock, dialogue_ledger,
        )
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
        multishot_identity_lock, multishot_voice_lock, multishot_setting_lock, dialogue_ledger,
    )
    best_enhanced = enhanced
    best_validation = validation

    def candidate_score(report: dict) -> tuple[int, int]:
        errors = report.get("errors", ())
        critical_markers = (
            "Explicit ", "Quoted source", "Required spoken dialogue", "invented reference labels",
            "Planned dialogue", "outside the planned ledger", "missing from output", "must remain",
            "terminal consequence",
        )
        weighted_errors = sum(
            10 if any(marker.casefold() in str(error).casefold() for marker in critical_markers) else 1
            for error in errors
        )
        return (weighted_errors, len(report.get("warnings", ())))

    attempts = 0
    while validation["errors"] and attempts < int(repair_attempts):
        attempts += 1
        dialogue_authoring_repair = ""
        if dialogue_ledger:
            dialogue_authoring_repair = (
                "\nMANDATORY DIALOGUE LEDGER REPAIR: Copy each of these exact blocks once, with no changes or "
                "additional spoken words:\n"
                + "\n".join(f"- <d>[{language}] {text}</d>" for language, text in dialogue_ledger)
            )
        elif any(
            "explicit dialogue authoring request" in str(error).casefold()
            or "affirmative speaking cues outside" in str(error).casefold()
            for error in validation["errors"]
        ):
            dialogue_authoring_repair = (
                "\nMANDATORY DIALOGUE AUTHORING REPAIR: The user explicitly authorized you to write the spoken "
                "content. Replace every vague description such as 'speaks', 'explains', or 'continues speaking' "
                "with actual natural utterances. Emit at least one concrete <d>[requested language] actual words"
                "</d> block, and use a stable (S1) plus an explicit vocal action in that same sentence. The words "
                "inside <d> must be newly written for the supplied scenario, not a placeholder, summary, or "
                "description of speech. If speech occurs in multiple timeline beats, write a distinct concise line "
                "at each relevant beat. This requirement overrides the default rule against unrequested dialogue."
            )
        messages.extend([
            {"role": "assistant", "content": enhanced},
            {"role": "user", "content": (
                "Repair the prompt. Return the complete corrected prompt only. Preserve all source facts and exact "
                "quoted content. Follow the selected mode's exact output contract. Fix these validation errors:\n- "
                + "\n- ".join(validation["errors"])
                + dialogue_authoring_repair
            )},
        ])
        enhanced = normalize_candidate(completion(messages))
        validation = validate_prompt(
            enhanced, mode, duration_seconds, basic_prompt, effective_reference_context,
            ambience_foley_policy, background_score_policy, voice_performance,
            aspect_ratio, media_manifest, multishot_shot_count, frame_count,
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock, dialogue_ledger,
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
        "dialogueLedgerLineCount": len(dialogue_ledger),
        "dialogueLedgerDigest": (
            hashlib.sha256(json.dumps(dialogue_ledger, ensure_ascii=False).encode("utf-8")).hexdigest()
            if dialogue_ledger else ""
        ),
        "dialoguePlanningRepairAttemptsUsed": dialogue_planning_repairs,
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
