# SPDX-License-Identifier: GPL-3.0-only
"""Structured reference-media context for MiniMax H3 prompt construction."""

from __future__ import annotations

import json
import re
from typing import Any


ASPECT_RATIOS = ("auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
MEDIA_TYPES = {"picture", "image", "video", "audio"}


def parse_media_manifest(value: str | dict | list | None) -> dict[str, Any]:
    """Parse the optional JSON manifest without guessing facts from prose."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return {"items": [], "mode": "", "warnings": [], "errors": []}
    if isinstance(value, str):
        # Builds before the structured manifest existed can deserialize the adjacent aspect-ratio
        # widget into this slot. Those enum values can never be manifest JSON, so repair only this
        # unambiguous migration case while continuing to reject every other malformed string.
        if value.strip().lower() in ASPECT_RATIOS:
            return {
                "items": [], "mode": "", "errors": [],
                "warnings": [f"Ignored migrated aspect-ratio value {value.strip()!r} in media_manifest"],
            }
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            return {"items": [], "mode": "", "warnings": [], "errors": [f"media_manifest is invalid JSON: {exc.msg}"]}
    else:
        data = value
    if isinstance(data, list):
        data = {"items": data}
    if not isinstance(data, dict):
        return {"items": [], "mode": "", "warnings": [], "errors": ["media_manifest must be a JSON object or array"]}
    raw_items = data.get("items", data.get("assets", data.get("media", [])))
    if not isinstance(raw_items, list):
        return {"items": [], "mode": "", "warnings": [], "errors": ["media_manifest.items must be an array"]}

    items: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    counters = {"picture": 0, "video": 0, "audio": 0}
    total_files = 0
    video_seconds = 0.0
    audio_seconds = 0.0
    for position, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            errors.append(f"media item {position} must be an object")
            continue
        if raw.get("enabled", True) is False:
            continue
        kind = str(raw.get("type", raw.get("kind", ""))).strip().lower()
        kind = "picture" if kind == "image" else kind
        if kind not in {"picture", "video", "audio"}:
            errors.append(f"media item {position} has unsupported type {kind!r}")
            continue
        total_files += 1
        raw_duration = raw.get("duration_seconds", raw.get("duration", 0))
        try:
            duration = float(raw_duration or 0)
        except (TypeError, ValueError):
            duration = 0.0
            errors.append(f"media item {position} duration must be numeric")
        if kind in {"video", "audio"} and duration:
            if not 2.0 <= duration <= 15.0:
                errors.append(f"media item {position} duration {duration:g}s is outside the documented 2-15s range")
            if kind == "video":
                video_seconds += duration
            else:
                audio_seconds += duration

        audio_mode = str(raw.get("audio_mode", "off")).strip().lower()
        soundtrack_label = ""
        if kind == "video" and audio_mode in {"paired", "alone"}:
            counters["audio"] += 1
            soundtrack_label = f"<Audio {counters['audio']}>"
            audio_seconds += duration
        counters[kind] += 1
        label = f"<{kind.title()} {counters[kind]}>"
        item = dict(raw)
        item.update({"type": kind, "label": label, "position": position, "duration_seconds": duration})
        if soundtrack_label:
            item["soundtrack_label"] = soundtrack_label
        items.append(item)

    if counters["picture"] > 9:
        errors.append("Ref2VA accepts at most 9 pictures")
    if counters["video"] > 3:
        errors.append("Ref2VA accepts at most 3 videos")
    if counters["audio"] > 3:
        errors.append("Ref2VA accepts at most 3 audio references, including enabled video soundtracks")
    if total_files > 12:
        errors.append("Ref2VA accepts at most 12 media files")
    if video_seconds > 15.0:
        errors.append(f"reference video duration totals {video_seconds:g}s; the documented maximum is 15s")
    if audio_seconds > 15.0:
        errors.append(f"reference audio duration totals {audio_seconds:g}s; the documented maximum is 15s")
    if counters["audio"] and not (counters["picture"] or counters["video"]):
        errors.append("Ref2VA audio cannot be the only reference modality")
    subjects: list[dict[str, Any]] = []
    raw_subjects = data.get("subjects", [])
    if not isinstance(raw_subjects, list):
        errors.append("media_manifest.subjects must be an array")
    else:
        available_labels = {
            label for item in items for label in (item.get("label"), item.get("soundtrack_label")) if label
        }
        for position, raw_subject in enumerate(raw_subjects, start=1):
            if not isinstance(raw_subject, dict):
                errors.append(f"manifest subject {position} must be an object")
                continue
            raw_id = raw_subject.get("id", raw_subject.get("subject_id", position))
            match = re.search(r"\d+", str(raw_id))
            if not match:
                errors.append(f"manifest subject {position} requires a numeric id")
                continue
            label = f"<Subject {int(match.group())}>"
            description = str(raw_subject.get("description", raw_subject.get("analysis", ""))).strip()
            sources = raw_subject.get("sources", raw_subject.get("source", []))
            sources = [sources] if isinstance(sources, str) else list(sources or [])
            sources = [str(source).strip() for source in sources if str(source).strip()]
            unknown = [source for source in sources if source not in available_labels]
            if not description:
                errors.append(f"{label} requires a concrete description")
            if not sources:
                errors.append(f"{label} requires at least one media source label")
            if unknown:
                errors.append(f"{label} has unknown source labels: {unknown}")
            subjects.append({"label": label, "description": description, "sources": sources})
    return {
        "items": items,
        "subjects": subjects,
        "mode": str(data.get("mode", "")).strip().lower(),
        "warnings": warnings,
        "errors": errors,
        "counts": counters,
        "totalFiles": total_files,
        "videoSeconds": video_seconds,
        "audioSeconds": audio_seconds,
    }


def manifest_context(value: str | dict | list | None) -> str:
    parsed = parse_media_manifest(value)
    if not parsed["items"]:
        return ""
    lines = ["CONNECTED MEDIA MANIFEST (labels below are authoritative and follow effective input order):"]
    for item in parsed["items"]:
        raw_role = item.get("role", item.get("roles", item.get("purpose", "unspecified role")))
        role = ", ".join(map(str, raw_role)) if isinstance(raw_role, list) else str(raw_role).strip()
        role = role.replace("_", " ")
        raw_analysis = item.get("analysis", item.get("description", ""))
        if isinstance(raw_analysis, dict):
            analysis = "; ".join(
                f"{key}={value}" for key, value in raw_analysis.items()
                if key != "transcript" and value not in (None, "", (), [])
            )
        else:
            analysis = str(raw_analysis).strip()
        extra = f"; analysis: {analysis}" if analysis else ""
        if item.get("reuse_mode"):
            extra += f"; reuse mode: {str(item['reuse_mode']).replace('_', ' ')}"
        lines.append(f"- Connected asset {item['label']} has role: {role}{extra}")
        if item.get("soundtrack_label"):
            lines.append(
                f"- Connected asset {item['soundtrack_label']} is the {item.get('audio_mode')} soundtrack from "
                f"{item['label']}"
            )
    if parsed.get("subjects"):
        lines.append("AUTHORITATIVE SUBJECT DEFINITIONS (supports multiple subjects per asset and multiple assets per subject):")
        for subject in parsed["subjects"]:
            sources = ", ".join(subject["sources"])
            lines.append(f"{subject['label']} is {subject['description']} from {sources}.")
    return "\n".join(lines)


def _detect_lang_fallback(text: str) -> str:
    try:
        from .prompt_guides import _detect_language
        return _detect_language(text, default="English")
    except Exception:
        try:
            from prompt_guides import _detect_language
            return _detect_language(text, default="English")
        except Exception:
            return "English"


def manifest_dialogue(value: str | dict | list | None) -> list[tuple[str, str, str]]:
    """Return authoritative transcribed reference-audio dialogue."""
    found: list[tuple[str, str, str]] = []
    for item in parse_media_manifest(value)["items"]:
        if item["type"] == "video" and not item.get("soundtrack_label"):
            continue
        if str(item.get("reuse_mode", "")).strip().lower() == "reference_only":
            continue
        analysis = item.get("analysis", {})
        transcript = item.get("transcript", analysis.get("transcript") if isinstance(analysis, dict) else None)
        if not transcript:
            continue
        entries = transcript if isinstance(transcript, list) else [transcript]
        for entry in entries:
            if isinstance(entry, str):
                cleaned = _normalize_transcript_text(entry)
                lang = _detect_lang_fallback(cleaned)
                found.append((
                    item.get("soundtrack_label", item["label"]),
                    lang,
                    cleaned,
                ))
            elif isinstance(entry, dict) and (entry.get("text") or entry.get("unclear")):
                if str(entry.get("reuse_mode", item.get("reuse_mode", ""))).strip().lower() == "reference_only":
                    continue
                transcript_text = "[unclear]" if entry.get("unclear") else _normalize_transcript_text(entry.get("text", ""))
                if not transcript_text:
                    transcript_text = "[unclear]"
                lang = str(entry.get("language") or _detect_lang_fallback(transcript_text))
                found.append((
                    str(entry.get("source", item.get("soundtrack_label", item["label"]))),
                    lang,
                    transcript_text,
                ))
    return found


def _normalize_transcript_text(value: Any) -> str:
    """Apply the official conservative transcript punctuation cleanup."""
    text = re.sub(r"[~～]{2,}", "", str(value or "")).strip()
    text = re.sub(r"^[\s•●▪◦*-]+", "", text).strip()
    text = re.sub(r"([!?.,])\1+", r"\1", text)
    if text and text != "[unclear]" and text[-1] not in ".?!":
        text += "."
    return text


MIN_GENERATION_SECONDS = 4.0
TRAINED_GENERATION_SECONDS = 15.0
MAX_GENERATION_SECONDS = 150.0


def generation_profile(duration_seconds: float, aspect_ratio: str = "auto", frame_count: int = 0) -> dict[str, Any]:
    """Validate H3 generation geometry and return the effective duration."""
    errors: list[str] = []
    warnings: list[str] = []
    frames = int(frame_count or 0)
    effective = float(duration_seconds)
    if frames:
        if frames < 5 or (frames - 5) % 17:
            errors.append("frame_count must lie on H3's 17k+5 frame grid")
        effective = frames / 24.0
        if abs(float(duration_seconds) - effective) > 0.5:
            warnings.append("frame_count overrides duration_seconds by more than 0.5s; effective duration follows frames/24")
    if not MIN_GENERATION_SECONDS <= effective <= MAX_GENERATION_SECONDS:
        errors.append(
            "MiniMax H3 single-generation duration must be within 4-150 seconds "
            "(the native ComfyUI node accepts up to 3600 frames)"
        )
    elif effective > TRAINED_GENERATION_SECONDS:
        warnings.append(
            "duration exceeds MiniMax H3's approximately 5-15 second trained range; "
            "longer single generations are supported by the native node but are untested and use substantially more memory"
        )
    if aspect_ratio not in ASPECT_RATIOS:
        errors.append(f"Unsupported aspect ratio {aspect_ratio!r}")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "durationSeconds": float(duration_seconds),
        "effectiveDurationSeconds": effective,
        "frameCount": frames,
        "aspectRatio": aspect_ratio,
    }
