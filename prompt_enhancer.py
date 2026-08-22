# SPDX-License-Identifier: GPL-3.0-only
"""Provider-neutral OpenAI-compatible MiniMax H3 prompt enhancement."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from .content_formats import CONTENT_FORMAT_CATALOG_VERSION, resolve_content_format
    from .creative_treatments import build_shots_package, normalize_title_screen_style_signature, parse_cinematography, parse_creative_treatment, parse_shot_plan, resolve_treatment_conflicts, resolve_visual_style, title_screen_requested, title_screen_roles, title_screen_text_authorized, treatment_warnings
    from .media_manifest import generation_profile, parse_media_manifest, parse_media_project
    from .planning_context import compile_planning_context
    from .prompt_guides import INSTRUMENTAL_STYLE_CATALOG_VERSION, append_lora_trigger_words, INSTRUMENTAL_STYLE_CONTRACTS, _build_user_request_compiled, _validate_prompt_compiled, _LANGUAGE_ALIASES, _detect_language, _dialogue_authoring_request, _dialogue_lexical_key, _source_dialogue_contracts, instrumental_style_digest, instrumental_style_signature, normalize_audio_policy, normalize_audio_section_sentence_limits, normalize_content_format_signature, normalize_dialogue_tags, normalize_first_shot_marker, normalize_instrumental_style_signature, normalize_multishot_audio_policy, normalize_multishot_output, normalize_reference_definitions, normalize_section_headers, normalize_shot_timeline, normalize_shot_timestamps, normalize_source_dialogue, normalize_unassigned_subjects, normalize_visual_medium_anchor, normalize_visual_style_signature, planning_manifest_context, resolve_mode, strip_markdown_fence, system_prompt_for_mode
except ImportError:  # pragma: no cover - direct test/import compatibility
    from content_formats import CONTENT_FORMAT_CATALOG_VERSION, resolve_content_format
    from creative_treatments import build_shots_package, normalize_title_screen_style_signature, parse_cinematography, parse_creative_treatment, parse_shot_plan, resolve_treatment_conflicts, resolve_visual_style, title_screen_requested, title_screen_roles, title_screen_text_authorized, treatment_warnings
    from media_manifest import generation_profile, parse_media_manifest, parse_media_project
    from planning_context import compile_planning_context
    from prompt_guides import INSTRUMENTAL_STYLE_CATALOG_VERSION, append_lora_trigger_words, INSTRUMENTAL_STYLE_CONTRACTS, _build_user_request_compiled, _validate_prompt_compiled, _LANGUAGE_ALIASES, _detect_language, _dialogue_authoring_request, _dialogue_lexical_key, _source_dialogue_contracts, instrumental_style_digest, instrumental_style_signature, normalize_audio_policy, normalize_audio_section_sentence_limits, normalize_content_format_signature, normalize_dialogue_tags, normalize_first_shot_marker, normalize_instrumental_style_signature, normalize_multishot_audio_policy, normalize_multishot_output, normalize_reference_definitions, normalize_section_headers, normalize_shot_timeline, normalize_shot_timestamps, normalize_source_dialogue, normalize_unassigned_subjects, normalize_visual_medium_anchor, normalize_visual_style_signature, planning_manifest_context, resolve_mode, strip_markdown_fence, system_prompt_for_mode


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


_NATIVE_CHAT_SUPPORT: dict[str, bool] = {}
_NATIVE_CHAT_LOCK = threading.Lock()
_AUTH_HTTP_CODES = frozenset({401, 403, 407})


def _reset_native_chat_cache() -> None:
    """Forget every probed LM Studio native-endpoint result (test helper)."""
    with _NATIVE_CHAT_LOCK:
        _NATIVE_CHAT_SUPPORT.clear()


def _native_chat_supported(native_root: str) -> bool:
    """Unprobed roots are optimistic; only a recorded failure skips the native attempt."""
    with _NATIVE_CHAT_LOCK:
        return _NATIVE_CHAT_SUPPORT.get(native_root, True)


def _record_native_chat_support(native_root: str, supported: bool) -> None:
    with _NATIVE_CHAT_LOCK:
        _NATIVE_CHAT_SUPPORT[native_root] = supported


def _is_missing_native_endpoint(error: Exception) -> bool:
    """Tell "this server has no native chat route" apart from credential or transport failures.

    _request_json embeds the HTTP status in its RuntimeError message. A 404/405/400 answers the
    endpoint-shape question, so the root is remembered as non-native. Authentication failures and
    unreachable-endpoint errors say nothing about the shape and leave the cache untouched.
    """
    match = re.search(r"returned HTTP (\d{3})", str(error))
    return bool(match) and int(match.group(1)) not in _AUTH_HTTP_CODES


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


def _native_chat_content(answer: dict) -> str:
    """Read the assistant text out of an LM Studio native /api/v1/chat answer."""
    for item in answer.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if isinstance(content, list):
            content = "".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
        text = str(content or "").strip()
        if text:
            return text
    return ""


def _completion(root: str, model: str, messages: list[dict], api_key: str,
                temperature: float, max_tokens: int, timeout: int,
                disable_thinking: bool = True,
                prefer_lm_studio_native: bool = True) -> str:
    native_root = root[:-3] if root.endswith("/v1") else root
    if disable_thinking and prefer_lm_studio_native and _native_chat_supported(native_root):
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
        # The native route is the only one that reliably silences reasoning on
        # LM Studio; the OpenAI-compatible payload below merely requests it.
        try:
            answer = _request_json(native_root + "/api/v1/chat", native_payload, api_key, timeout)
        except RuntimeError as exc:
            if _is_missing_native_endpoint(exc):
                _record_native_chat_support(native_root, False)
        else:
            _record_native_chat_support(native_root, True)
            content = _native_chat_content(answer)
            if content:
                return strip_markdown_fence(content)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "stream": False,
    }
    if disable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
        payload["reasoning_effort"] = "low"
    response = _request_json(root + "/chat/completions", payload, api_key, timeout)
    try:
        msg = response["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        if not content and msg.get("reasoning_content"):
            content = str(msg.get("reasoning_content")).strip()
            # If the reasoning content has a final output, extract it
            if "\n\n" in content:
                parts = content.split("\n\n")
                content = parts[-1].strip() if parts[-1].strip() else content
        # Strip XML/think tags if present
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        content = re.sub(r"^Thinking Process:.*?(?=\n\n|\Z)", "", content, flags=re.DOTALL).strip()
        return strip_markdown_fence(content)
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
        language = re.sub(r"[\[\]]", "", language).strip()
        text = re.sub(r"\s+", " ", text).strip()
        if not language:
            raise ValueError(f"ledger line {index} has an invalid language")
        canonical_ledger = _LANGUAGE_ALIASES.get(language.casefold(), language.capitalize())
        canonical_req = _LANGUAGE_ALIASES.get(requested_language.casefold(), requested_language.capitalize())
        if requested_language.casefold() not in {"auto", "original language"} and canonical_ledger.casefold() != canonical_req.casefold():
            raise ValueError(
                f"ledger line {index} must use {requested_language}, observed {language or 'no language'}"
            )
        if requested_language.casefold() not in {"auto", "original language"}:
            language = canonical_req
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
    # verbatim_source cannot ride on enhance_description because bool("verbatim_source") is
    # True, which would hand the strictest profile the widest latitude. Sits before
    # lora_trigger_words to keep the append-only trailing order the compatibility test pins.
    creative_latitude: str | None = None,
    lora_trigger_words: str = "",
) -> tuple[str, dict, dict]:
    """Apply the common MiniMax guide, normalization, validation, and repair loop."""
    basic_prompt = str(basic_prompt).strip()
    if not basic_prompt:
        raise ValueError("basic_prompt cannot be empty")
    parsed_manifest_preflight = parse_media_manifest(media_manifest)
    compiled_media_project = parse_media_project(media_manifest)
    preflight_errors = compiled_media_project.get("errors", parsed_manifest_preflight.get("errors", ()))
    if preflight_errors:
        raise ValueError("Invalid media_manifest: " + "; ".join(preflight_errors))
    resolved_mode = resolve_mode(mode, reference_context, basic_prompt, media_manifest, editing_intent=editing_intent)
    generation = generation_profile(duration_seconds, aspect_ratio, frame_count)
    effective_duration = generation["effectiveDurationSeconds"]
    creative_treatment = parse_creative_treatment(
        creative_treatment_json, enabled=bool(enhance_description),
    )
    cinematography = parse_cinematography(cinematography_json)
    explicit_shot_plan = parse_shot_plan(
        shot_plan_json, effective_duration, 0, resolved_mode,
    )
    compiled_planning = compile_planning_context(
        compiled_media_project, explicit_shot_plan, effective_duration, mode=resolved_mode,
    )
    if compiled_planning.get("applied") and not compiled_planning.get("valid"):
        messages = [
            item.get("message", item.get("code", "Invalid planning configuration"))
            for item in compiled_planning.get("diagnosticReport", {}).get("diagnostics", ())
            if item.get("blocks", {}).get("valid")
        ]
        raise ValueError("Invalid media/shot planning configuration: " + "; ".join(messages))
    treatment_notes = treatment_warnings(creative_treatment, cinematography, explicit_shot_plan)
    opening_format_selected = creative_treatment.get("contentFormat") == "opening_title_sequence"
    if (creative_treatment.get("titleScreenStyle") != "none"
            and not title_screen_requested(basic_prompt)
            and not opening_format_selected):
        treatment_notes.append(
            "Title screen style is saved but not applied because the Basic prompt does not explicitly request a "
            "title screen, title card, opening/end title, or intertitle."
        )
    elif (creative_treatment.get("titleScreenStyle") != "none"
          and not title_screen_text_authorized(basic_prompt)):
        treatment_notes.append(
            "Title screen style is saved but not applied because no exact quoted visible title text is locally "
            "bound to the requested title screen."
        )
    creative_treatment, treatment_conflicts = resolve_treatment_conflicts(creative_treatment, cinematography)
    resolved_visual_style = resolve_visual_style(creative_treatment, cinematography)
    resolved_content_format = resolve_content_format(
        creative_treatment.get("contentFormat", "none"), enabled=bool(enhance_description),
        source_prompt=basic_prompt, voice_performance=voice_performance,
        background_score_policy=background_score_policy, mode=resolved_mode,
        duration_seconds=effective_duration,
    )
    treatment_notes.extend(str(item) for item in resolved_content_format.get("warnings", ()) if str(item))
    if resolved_content_format.get("requested") and not resolved_content_format.get("applied"):
        treatment_notes.append(
            "Content / production format was saved but not applied: "
            + str(resolved_content_format.get("notAppliedReason") or "requirements_not_met")
            + "."
        )
    dialogue_authoring, resolved_dialogue_language = _dialogue_authoring_request(
        basic_prompt, override_language=dialogue_language
    )
    user_request = _build_user_request_compiled(
        basic_prompt, mode, duration_seconds, reference_context, enhance_description,
        ambience_foley_policy, background_score_policy, voice_performance, instrumental_description,
        aspect_ratio, media_manifest, multishot_shot_count, frame_count,
        multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
        (), creative_treatment_json, shot_plan_json, cinematography_json, instrumental_style,
        acoustic_space, dialogue_coverage, dialogue_language=dialogue_language,
        editing_intent=editing_intent,
        invent_scene=invent_scene,
        compiled_planning_context=compiled_planning,
    )
    dialogue_ledger: tuple[tuple[str, str], ...] = ()
    dialogue_planning_repairs = 0
    if dialogue_authoring and voice_performance == "audible":
        dialogue_ledger, dialogue_planning_repairs = _plan_dialogue_ledger(
            basic_prompt,
            resolved_dialogue_language,
            effective_duration,
            (
                explicit_shot_plan.get("generationCount", explicit_shot_plan["shotCount"])
                if resolved_mode == "chained_multishot" and explicit_shot_plan["provided"]
                else multishot_shot_count if resolved_mode == "chained_multishot" else 1
            ),
            completion,
            repair_attempts,
        )
        user_request = _build_user_request_compiled(
            basic_prompt, mode, duration_seconds, reference_context, enhance_description,
            ambience_foley_policy, background_score_policy, voice_performance, instrumental_description,
            aspect_ratio, media_manifest, multishot_shot_count, frame_count,
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock, dialogue_ledger,
            creative_treatment_json, shot_plan_json, cinematography_json, instrumental_style,
            acoustic_space, dialogue_coverage, dialogue_language=dialogue_language,
            editing_intent=editing_intent,
            invent_scene=invent_scene,
            compiled_planning_context=compiled_planning,
        )
    effective_reference_context = "\n".join(
        part for part in (
            str(reference_context).strip(),
            "\n\n".join(
                str(item.get("context", ""))
                for item in compiled_planning.get("generations", {}).values()
                if item.get("context")
            ) if compiled_planning.get("applied") else planning_manifest_context(
                media_manifest, explicit_shot_plan,
            ),
        ) if part
    )
    base_messages = [
        {"role": "system", "content": system_prompt_for_mode(
            resolved_mode,
            "verbatim_source" if creative_latitude == "verbatim_source" else bool(enhance_description),
            invent_scene)},
        {"role": "user", "content": user_request},
    ]
    messages = list(base_messages)
    context_size = int(manifest.get("contextSize") or 0)
    max_output_tokens = int(manifest.get("maxTokens") or 0)
    if context_size and max_output_tokens:
        estimated_input_tokens = (sum(len(item["content"]) for item in base_messages) + 2) // 3
        required_context = estimated_input_tokens + max_output_tokens * (2 if int(repair_attempts) else 1)
        if required_context > context_size:
            raise ValueError(
                f"context_size={context_size} is too small for approximately {estimated_input_tokens} input tokens "
                f"plus max_tokens={max_output_tokens}"
                + (" and one bounded repair response" if int(repair_attempts) else "")
                + f"; use at least {required_context} or reduce prompt/output budgets"
            )
    def normalize_candidate(candidate: str) -> str:
        if resolved_mode == "chained_multishot":
            value = normalize_multishot_output(candidate, (
                multishot_identity_lock, multishot_voice_lock, multishot_setting_lock,
            ))
            value = normalize_multishot_audio_policy(
                value, ambience_foley_policy, background_score_policy, voice_performance,
                basic_prompt + "\n" + effective_reference_context,
            )
            value = normalize_visual_style_signature(value, resolved_mode, resolved_visual_style)
            value = normalize_visual_medium_anchor(
                value, resolved_mode, creative_treatment, basic_prompt,
            )
            value = normalize_content_format_signature(value, resolved_mode, resolved_content_format)
            value = normalize_instrumental_style_signature(
                value, resolved_mode, background_score_policy, instrumental_style,
            )
            value = normalize_title_screen_style_signature(value, creative_treatment, basic_prompt)
            return normalize_audio_section_sentence_limits(value, resolved_mode)
        value = normalize_section_headers(candidate)
        value = normalize_dialogue_tags(value)
        value = normalize_first_shot_marker(value, resolved_mode)
        value = normalize_shot_timestamps(value)
        value = normalize_shot_timeline(value, resolved_mode, effective_duration, explicit_shot_plan)
        value = normalize_reference_definitions(value, basic_prompt, effective_reference_context)
        value = normalize_unassigned_subjects(value, basic_prompt, effective_reference_context)
        value = normalize_source_dialogue(value, basic_prompt, resolved_mode, voice_performance)
        value = normalize_audio_policy(
            value, ambience_foley_policy, background_score_policy, voice_performance,
            basic_prompt + "\n" + effective_reference_context,
        )
        value = normalize_visual_style_signature(value, resolved_mode, resolved_visual_style)
        value = normalize_visual_medium_anchor(
            value, resolved_mode, creative_treatment, basic_prompt,
        )
        value = normalize_content_format_signature(value, resolved_mode, resolved_content_format)
        value = normalize_instrumental_style_signature(
            value, resolved_mode, background_score_policy, instrumental_style,
        )
        value = normalize_title_screen_style_signature(value, creative_treatment, basic_prompt)
        return normalize_audio_section_sentence_limits(value, resolved_mode)

    enhanced = normalize_candidate(completion(messages))
    validation = _validate_prompt_compiled(
        enhanced, mode, duration_seconds, basic_prompt, effective_reference_context,
        ambience_foley_policy, background_score_policy, voice_performance,
        aspect_ratio, media_manifest, multishot_shot_count, frame_count,
        multishot_identity_lock, multishot_voice_lock, multishot_setting_lock, dialogue_ledger,
        creative_treatment_json, shot_plan_json, cinematography_json,
        enhance_description=bool(enhance_description), delivery_target=delivery_target,
        instrumental_description=instrumental_description, instrumental_style=instrumental_style,
        acoustic_space=acoustic_space, dialogue_coverage=dialogue_coverage,
        dialogue_language=dialogue_language,
        editing_intent=editing_intent,
        invent_scene=invent_scene,
        compiled_planning_context=compiled_planning,
    )
    best_enhanced = enhanced
    best_validation = validation

    def repair_issues(report: dict) -> list[str]:
        structured = report.get("diagnosticReport", {}).get("diagnostics", ())
        structured_repairs = [
            item.get("repair", {}).get("instruction")
            for item in structured
            if item.get("repair", {}).get("eligible") and item.get("repair", {}).get("instruction")
        ]
        official_shape_warnings = [
            warning for warning in report.get("warnings", ())
            if str(warning) in {
                "overall_soundscape should contain 1-4 English sentences in one paragraph",
                "non_diegetic_music should contain 1-3 English sentences",
            }
            or "repeats the same descriptive sentence three or more times" in str(warning)
        ]
        return [
            *structured_repairs,
            *report.get("errors", ()),
            *report.get("coverageGaps", ()),
            *report.get("styleCoverageGaps", ()),
            *report.get("contentFormatCoverageGaps", ()),
            *official_shape_warnings,
        ]

    def candidate_score(report: dict) -> tuple[int, int, int, int]:
        diagnostics = report.get("diagnosticReport", {}).get("diagnostics", ())
        valid_blockers = sum(
            max(1, int(item.get("repair", {}).get("priority", 0)))
            for item in diagnostics if item.get("blocks", {}).get("valid")
        )
        quality_blockers = sum(
            max(1, int(item.get("repair", {}).get("priority", 0)))
            for item in diagnostics if item.get("blocks", {}).get("quality")
        )
        # Legacy validators remain authoritative during the staged migration,
        # but their score no longer depends on English message substrings.
        valid_blockers += 100 * len(report.get("errors", ()))
        quality_blockers += 50 * (
            len(report.get("coverageGaps", ()))
            + len(report.get("styleCoverageGaps", ()))
            + len(report.get("contentFormatCoverageGaps", ()))
        )
        contract_warnings = sum(
            item.get("severity") == "warning" and item.get("category") != "coach"
            for item in diagnostics
        ) + len(report.get("warnings", ()))
        return valid_blockers, quality_blockers, contract_warnings, len(diagnostics)

    attempts = 0
    while repair_issues(validation) and attempts < int(repair_attempts):
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
        issues = repair_issues(validation)
        messages = [*base_messages,
            {"role": "assistant", "content": enhanced},
            {"role": "user", "content": (
                "Repair the prompt. Return the complete corrected prompt only. Preserve all source facts, exact "
                "quoted content, reference roles, and resolved style fields. Follow the selected mode's exact output "
                "contract and active enhancement profile. Fix these structural, fidelity, or coverage issues:\n- "
                + "\n- ".join(issues)
                + dialogue_authoring_repair
            )},
        ]
        enhanced = normalize_candidate(completion(messages))
        validation = _validate_prompt_compiled(
            enhanced, mode, duration_seconds, basic_prompt, effective_reference_context,
            ambience_foley_policy, background_score_policy, voice_performance,
            aspect_ratio, media_manifest, multishot_shot_count, frame_count,
            multishot_identity_lock, multishot_voice_lock, multishot_setting_lock, dialogue_ledger,
            creative_treatment_json, shot_plan_json, cinematography_json,
            enhance_description=bool(enhance_description), delivery_target=delivery_target,
            instrumental_description=instrumental_description, instrumental_style=instrumental_style,
            acoustic_space=acoustic_space, dialogue_coverage=dialogue_coverage,
            editing_intent=editing_intent,
            invent_scene=invent_scene,
            compiled_planning_context=compiled_planning,
        )
        if candidate_score(validation) < candidate_score(best_validation):
            best_enhanced = enhanced
            best_validation = validation
    enhanced = best_enhanced
    # After validation on purpose: a trigger token is not English prose, so it must not be seen by
    # a check that expects prose nor rewritten by a repair pass.
    enhanced = append_lora_trigger_words(enhanced, lora_trigger_words, resolved_mode)
    validation = best_validation
    shots_package = build_shots_package(
        enhanced, resolved_mode, explicit_shot_plan, bool(validation.get("qualityValid")),
    )
    if shots_package.get("schemaVersion") == 2 and compiled_planning.get("applied"):
        for generation_id, generation in shots_package.get("generations", {}).items():
            planned_generation = compiled_planning.get("generations", {}).get(generation_id, {})
            generation.update({
                "inputMap": planned_generation.get("inputMap", {}),
                "activeAssetIds": planned_generation.get("activeAssetIds", []),
                "stateDigest": planned_generation.get("stateDigest", generation.get("stateDigest", "")),
                "authorityDigest": planned_generation.get(
                    "authorityDigest", generation.get("authorityDigest", ""),
                ),
            })
    result_manifest = {
        **manifest,
        "mode": validation["mode"],
        "durationSeconds": float(duration_seconds),
        "repairAttemptsUsed": attempts,
        "descriptionEnhanced": bool(enhance_description),
        "enhancementProfile": validation.get("enhancementProfile"),
        "qualityValid": bool(validation.get("qualityValid")),
        "deliveryTarget": delivery_target,
        "apiCompatible": bool(validation.get("apiCompatible")),
        "referenceSemanticsVersion": 3 if compiled_media_project.get("schemaVersion") == 2 else 2,
        "audioPolicyVersion": 1,
        "promptContractVersion": 3,
        "creativeTreatmentSchemaVersion": creative_treatment["schemaVersion"],
        "creativeProfileCatalogVersion": creative_treatment["catalogVersion"],
        "contentFormatCatalogVersion": CONTENT_FORMAT_CATALOG_VERSION,
        "titleScreenStyleCatalogVersion": creative_treatment["titleScreenStyleCatalogVersion"],
        "titleScreenStyleRequested": creative_treatment["titleScreenStyle"],
        "titleScreenStyleApplied": bool(
            creative_treatment.get("applied")
            and creative_treatment.get("titleScreenStyle") != "none"
            and title_screen_requested(basic_prompt)
            and title_screen_text_authorized(basic_prompt)
        ),
        "titlePresentationRoles": list(title_screen_roles(basic_prompt)),
        "cinematographySchemaVersion": cinematography["schemaVersion"],
        "cinematographyCatalogVersion": cinematography["catalogVersion"],
        "shotPlanSchemaVersion": explicit_shot_plan["schemaVersion"],
        "shotsPackageSchemaVersion": shots_package.get("schemaVersion", 1),
        "mediaManifestSchemaVersion": compiled_media_project.get("schemaVersion", 1),
        "mediaManifestDigest": compiled_media_project.get("digest", "") or (
            hashlib.sha256(str(media_manifest).encode("utf-8")).hexdigest()
            if str(media_manifest).strip() else ""
        ),
        "diagnosticsDigest": validation.get("diagnosticsDigest", ""),
        "planningDigest": compiled_planning.get("digest", ""),
        "planningSummary": (
            compiled_planning.get("planningSummary", {})
            if compiled_planning.get("applied") else {
                "generationCount": len(compiled_media_project.get("generations", ())),
                "shotCount": explicit_shot_plan.get("shotCount", 0),
                "diagnosticCount": len(validation.get("diagnosticReport", {}).get("diagnostics", ())),
            }
        ),
        "aspectRatio": aspect_ratio,
        "multishotPromptCount": validation.get("promptCount", 0),
        "creativeTreatment": creative_treatment,
        "contentFormat": resolved_content_format,
        "cinematography": cinematography,
        "resolvedVisualStyle": resolved_visual_style,
        "treatmentConflicts": treatment_conflicts,
        "treatmentWarnings": treatment_notes,
        "shotPlan": explicit_shot_plan,
        "shotsPackage": shots_package,
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
        "instrumentalStyleRequested": instrumental_style,
        "instrumentalStyleApplied": (
            instrumental_style if background_score_policy == "add_instrumental" else "none"
        ),
        "resolvedInstrumentalStyleContract": (
            INSTRUMENTAL_STYLE_CONTRACTS.get(instrumental_style, "")
            if background_score_policy == "add_instrumental" else ""
        ),
        "instrumentalStyleCatalogVersion": INSTRUMENTAL_STYLE_CATALOG_VERSION,
        "instrumentalStyleProfileVersion": 1 if instrumental_style != "none" else 0,
        "instrumentalStyleDigest": (
            instrumental_style_digest(instrumental_style) if instrumental_style != "none" else ""
        ),
        "instrumentalStyleSignature": (
            instrumental_style_signature(instrumental_style)
            if background_score_policy == "add_instrumental" else ""
        ),
        "instrumentalStyleInjected": bool(
            background_score_policy == "add_instrumental" and instrumental_style != "none"
        ),
        "instrumentalStyleObserved": bool(
            background_score_policy == "add_instrumental"
            and instrumental_style != "none"
            and instrumental_style_signature(instrumental_style) in enhanced
        ),
        "acousticSpace": acoustic_space,
        "dialogueCoverage": dialogue_coverage,
        "dialogueLanguage": (
            resolved_dialogue_language if dialogue_authoring
            else (
                _LANGUAGE_ALIASES.get(dialogue_language.casefold(), dialogue_language.capitalize())
                if dialogue_language and dialogue_language != "auto"
                else (
                    source_contracts[0][0] if (source_contracts := _source_dialogue_contracts(basic_prompt))
                    else _detect_language(basic_prompt)
                )
            )
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
                   multishot_voice_lock: str = "", multishot_setting_lock: str = "",
                   creative_treatment_json: str = "", shot_plan_json: str = "",
                   cinematography_json: str = "",
                   instrumental_style: str = "none",
                   acoustic_space: str = "none",
                   dialogue_coverage: str = "off",
                   delivery_target: str = "local",
                   dialogue_language: str = "auto",
                   editing_intent: str = "none",
                   invent_scene: bool = False,
                   creative_latitude: str | None = None,
                   lora_trigger_words: str = "") -> tuple[str, dict, dict]:
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
        creative_latitude=creative_latitude,
        lora_trigger_words=lora_trigger_words,
    )
