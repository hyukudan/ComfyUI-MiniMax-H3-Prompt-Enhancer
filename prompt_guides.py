# SPDX-License-Identifier: GPL-3.0-only
"""MiniMax H3 prompt construction and validation rules.

The rule set is an original implementation derived from MiniMax's public
T2VA/I2VA/FL2VA/L2VA and full-reference prompt-writing guides.
"""

from __future__ import annotations

import re
from typing import Any


BASE_SECTIONS = (
    "integrated_multimodal_description",
    "overall_soundscape",
    "non_diegetic_music",
)
REFERENCE_SECTIONS = (
    "subject_definitions",
    "summary",
    "retention_analysis",
    "detailed_description",
    "overall_soundscape",
    "non_diegetic_music",
)
TASK_MODES = ("auto", "t2va", "i2va", "fl2va", "l2va", "ref2va")
_SECTION_RE = re.compile(r"(?m)^([a-z_]+):\s*")
_SHOT_RE = re.compile(r"\[Shot\s+(\d+)\](?:\s+At\s+(\d{2}):(\d{2})\.(\d{3}),)?", re.IGNORECASE)
_REFERENCE_RE = re.compile(r"<(?:Subject|Picture|Video|Audio)\s+\d+>", re.IGNORECASE)
_QUOTED_RE = re.compile(r'["“]([^"”\r\n]+)["”]')
_SPEECH_CUE_RE = re.compile(
    r"\b(?:say|says|said|state|states|ask|asks|shout|shouts|whisper|whispers|speak|speaks|"
    r"dice|dijo|pregunta|grita|susurra|habla)\b",
    re.IGNORECASE,
)


SYSTEM_PROMPT = """You rewrite basic user requests into production-ready MiniMax H3 audiovisual prompts.

Return only the finished prompt, without Markdown fences, commentary, preamble, or a trailing explanation. Write
all structural prose in English. Preserve the original language only inside dialogue/lyrics and visible on-screen
text. Never translate, paraphrase, censor, soften, or extend quoted dialogue, lyrics, or visible text. Do not invent
new dialogue. Keep requested identities, actions, camera behavior, timing, reference roles, and ending intact.

Shared timeline rules:
- Shot 1 has no timestamp. Later shots are sequential and begin with strictly increasing [Shot N] At MM:SS.mmm,
  cut times inside the requested duration.
- Describe style and initial composition at Shot 1. Write camera motion naturally using motion type and, only when
  useful, amplitude and speed. Prefer camera movement over a cut that reveals no new information.
- Give each actual vocal source a stable (S1), (S2), ... ID. Put only the exact spoken words and a language tag
  inside <d>[Language] ...</d>. For voiceover say "says in an off-screen voiceover" and state that the visible
  character's lips remain closed. Never convert visible dialogue into voiceover unless the source explicitly asks
  for voiceover or narration. Use <scenetrans> across cuts and <cutoff> only for intentionally truncated speech.
- Put visible text in straight English double quotes exactly as supplied.
- overall_soundscape is one continuous paragraph of 1-4 sentences covering ambience, physical sounds, and
  non-verbal human sounds. Do not repeat dialogue or audience-only music there.
- non_diegetic_music is 1-3 sentences describing only audience-only music through instrumentation, tempo, rhythm,
  and dynamics. Use N/A when none is requested.

Base-mode output has exactly these three sections in order:
integrated_multimodal_description, overall_soundscape, non_diegetic_music.
Each section name must be followed by a literal colon, for example integrated_multimodal_description:.
T2VA begins directly with the sections. I2VA begins with the exact first-frame alignment sentence supplied in the
request. FL2VA begins with the exact first/last alignment sentence supplied in the request and normally uses one
continuous shot that visibly connects both anchors. L2VA begins with the exact last-frame alignment sentence supplied
in the request and converges toward that final frame.

Ref2VA output has exactly these six sections in order:
subject_definitions, summary, retention_analysis, detailed_description, overall_soundscape, non_diegetic_music.
Use stable <Subject N>, <Picture N>, <Video N>, and <Audio N> meanings. Subject labels describe reusable visible
content; Picture labels are concrete frame/composition anchors; Video labels describe whole-video edit, continuation,
or temporal structure; Audio labels describe copied or referenced signals. The summary starts with bracketed task
types. retention_analysis uses only the documented visual markers fully_preserved, partially_preserved,
attribute_transfer, weak_reference and audio markers fully_copy, partially_copy, reference, weak_reference.
For generation tasks, make detailed_description explicit and normally 350-500 English words. Establish style in one
or two sentences before Shot 1, then describe composition, appearance, environment, lighting, actions, state changes,
camera, sound, and where each reference takes effect in playback order.
"""


def resolve_mode(mode: str, reference_context: str = "") -> str:
    mode = str(mode).strip().lower()
    if mode not in TASK_MODES:
        raise ValueError(f"Unsupported MiniMax H3 prompt mode {mode!r}")
    if mode != "auto":
        return mode
    return "ref2va" if _REFERENCE_RE.search(reference_context or "") else "t2va"


def alignment_instruction(mode: str, duration_seconds: float, final_shot: int | str = "N") -> str:
    duration = f"{float(duration_seconds):.2f}"
    if mode == "i2va":
        return "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
    if mode == "fl2va":
        return (
            "How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the "
            f"0.00-second mark of the target video; Picture 2 (from Shot {final_shot}) aligns with the {duration}-second mark "
            "of the target video."
        )
    if mode == "l2va":
        return (
            f"How the reference pictures align with the target video — <Picture 1> (from [Shot {final_shot}]) aligns with the "
            f"{duration}-second mark of the target video."
        )
    return ""


def build_user_request(basic_prompt: str, mode: str, duration_seconds: float,
                       reference_context: str = "") -> str:
    resolved = resolve_mode(mode, reference_context)
    alignment = alignment_instruction(resolved, duration_seconds)
    parts = [
        f"TASK MODE: {resolved.upper()}",
        f"TARGET DURATION: {float(duration_seconds):.3f} seconds",
        "BASIC USER PROMPT (authoritative; preserve its intent and exact quoted content):\n" + basic_prompt.strip(),
    ]
    if reference_context.strip():
        parts.append("REFERENCE CONTEXT (authoritative labels and roles):\n" + reference_context.strip())
    if alignment:
        label = "REQUIRED FIRST-LINE TEMPLATE (replace N with the actual final shot number):" if resolved in {"fl2va", "l2va"} else "REQUIRED FIRST LINE:"
        parts.append(label + "\n" + alignment)
    if resolved == "ref2va":
        parts.append(
            "EXACT OUTPUT SKELETON (replace every placeholder; retain names, colons, and order):\n"
            "subject_definitions:\n...\n\nsummary:\n...\n\nretention_analysis:\n...\n\n"
            "detailed_description:\n[Shot 1] ...\n\noverall_soundscape:\n...\n\nnon_diegetic_music:\n..."
        )
    else:
        parts.append(
            "EXACT OUTPUT SKELETON (replace every placeholder; retain names, colons, and order):\n"
            "integrated_multimodal_description:\n[Shot 1] ...\n\noverall_soundscape:\n...\n\n"
            "non_diegetic_music:\n..."
        )
    parts.append("Rewrite now using the exact section contract for this task mode.")
    return "\n\n".join(parts)


def strip_markdown_fence(text: str) -> str:
    value = str(text).strip()
    match = re.fullmatch(r"```(?:text)?\s*(.*?)\s*```", value, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else value


def normalize_section_headers(text: str) -> str:
    """Repair harmless LLM formatting drift without changing authored prompt content."""
    value = str(text).strip()
    for section in (*BASE_SECTIONS, *REFERENCE_SECTIONS):
        value = re.sub(rf"(?m)^{re.escape(section)}\s*$", f"{section}:", value)
    return value


def normalize_dialogue_tags(text: str) -> str:
    """Keep dialogue parseable when a small LLM omits only the required language marker."""
    value = re.sub(
        r"<d>\s*(?!\[[^\]]+\])",
        "<d>[Original language] ",
        str(text),
        flags=re.IGNORECASE,
    )
    return re.sub(r"(<d>\[[^\]]+\])\s*", r"\1 ", value, flags=re.IGNORECASE)


def normalize_shot_timestamps(text: str) -> str:
    """Add the guide-required comma when the model supplied a complete timestamp but omitted punctuation."""
    value = re.sub(
        r"At\s+(\d{2}:\d{2}\.\d{3})\s+(\[Shot\s+(\d+)\])",
        r"\2 At \1,",
        str(text),
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"(\[Shot\s+\d+\]\s+At\s+\d{2}:\d{2}\.\d{3})(?!,)",
        r"\1,",
        value,
        flags=re.IGNORECASE,
    )


def normalize_first_shot_marker(text: str, mode: str) -> str:
    """Bracket an unambiguous timeline-leading `Shot 1` without touching keyframe prose."""
    section = "detailed_description" if mode == "ref2va" else "integrated_multimodal_description"
    pattern = re.compile(
        rf"(?ms)(^{re.escape(section)}:\s*)(.*?)(?=^[a-z_]+:\s*|\Z)"
    )
    match = pattern.search(str(text))
    if not match or re.search(r"\[Shot\s+1\]", match.group(2), re.IGNORECASE):
        return str(text)
    body = re.sub(r"\bShot\s+1\b", "[Shot 1]", match.group(2), count=1, flags=re.IGNORECASE)
    return str(text)[:match.start()] + match.group(1) + body + str(text)[match.end():]


def _time_seconds(minutes: str, seconds: str, millis: str) -> float:
    return int(minutes) * 60 + int(seconds) + int(millis) / 1000.0


def _section_body(text: str, section: str) -> str:
    """Return one section body so labels mentioned in analysis are not parsed as timeline shots."""
    match = re.search(
        rf"(?ms)^{re.escape(section)}:\s*(.*?)(?=^[a-z_]+:\s*|\Z)",
        text,
    )
    return match.group(1) if match else ""


def validate_prompt(prompt: str, mode: str, duration_seconds: float,
                    source_prompt: str = "", reference_context: str = "") -> dict[str, Any]:
    resolved = resolve_mode(mode, reference_context)
    text = str(prompt).strip()
    errors: list[str] = []
    warnings: list[str] = []
    expected = REFERENCE_SECTIONS if resolved == "ref2va" else BASE_SECTIONS
    observed = tuple(match.group(1) for match in _SECTION_RE.finditer(text))
    if observed != expected:
        errors.append(f"Expected sections in order {expected}, observed {observed}")
    if text.startswith("```") or text.endswith("```"):
        errors.append("Output must not use a Markdown code fence")

    timeline_section = "detailed_description" if resolved == "ref2va" else "integrated_multimodal_description"
    timeline = _section_body(text, timeline_section)
    shots = list(_SHOT_RE.finditer(timeline))
    if not shots:
        errors.append("At least [Shot 1] is required")
    else:
        numbers = [int(item.group(1)) for item in shots]
        if numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"Shot numbers must be sequential from 1, observed {numbers}")
        if shots[0].group(2) is not None:
            errors.append("Shot 1 must not have a timestamp")
        cut_times = []
        for shot in shots[1:]:
            if shot.group(2) is None:
                errors.append(f"Shot {shot.group(1)} requires an At MM:SS.mmm timestamp")
                continue
            cut_times.append(_time_seconds(shot.group(2), shot.group(3), shot.group(4)))
        if cut_times != sorted(set(cut_times)):
            errors.append("Cut timestamps must be strictly increasing")
        if any(value <= 0 or value >= float(duration_seconds) for value in cut_times):
            errors.append("Every cut timestamp must fall strictly inside the target duration")
    final_shot = len(shots) if shots else 1
    alignment = alignment_instruction(resolved, duration_seconds, final_shot)
    if alignment and not text.startswith(alignment + "\n\n"):
        errors.append("Required keyframe alignment instruction is missing, incorrect, or is not the first line")
    if resolved == "t2va" and not text.startswith("integrated_multimodal_description:"):
        errors.append("T2VA must begin directly with integrated_multimodal_description")

    if text.count("<d>") != text.count("</d>"):
        errors.append("Dialogue tags are unbalanced")
    for dialogue in re.findall(r"<d>(.*?)</d>", text, flags=re.DOTALL):
        if not re.match(r"\[[^\]]+\]\s+\S", dialogue.strip()):
            errors.append("Every <d> block must begin with a language tag and contain dialogue")

    missing_quotes = [quote for quote in _QUOTED_RE.findall(source_prompt or "") if quote not in text]
    if missing_quotes:
        errors.append("Quoted source text was not preserved exactly: " + repr(missing_quotes))
    source_dialogue = re.findall(r"<d>(.*?)</d>", source_prompt or "", flags=re.DOTALL)
    missing_dialogue = [item for item in source_dialogue if item not in text]
    if missing_dialogue:
        errors.append("Source <d> dialogue was not preserved exactly")
    tagged_dialogue = "\n".join(re.findall(r"<d>(.*?)</d>", text, flags=re.DOTALL))
    for match in _QUOTED_RE.finditer(source_prompt or ""):
        cue_window = (source_prompt or "")[max(0, match.start() - 100):match.start()]
        if _SPEECH_CUE_RE.search(cue_window) and match.group(1) not in tagged_dialogue:
            errors.append(f"Quoted spoken dialogue must appear inside a language-tagged <d> block: {match.group(1)!r}")
    source_requests_voiceover = re.search(
        r"\b(?:voice[ -]?over|narrat(?:e|es|ed|ion)|off-screen voice|voz en off|narraci[oó]n)\b",
        source_prompt or "",
        flags=re.IGNORECASE,
    )
    if re.search(r"\b(?:off-screen voiceover|voice[ -]?over|voz en off)\b", text, re.IGNORECASE) and not source_requests_voiceover:
        errors.append("Output invented voiceover although the source requested visible dialogue")

    required_refs = set(_REFERENCE_RE.findall(reference_context or ""))
    output_refs = set(_REFERENCE_RE.findall(text))
    absent_refs = sorted(required_refs - output_refs)
    if absent_refs:
        errors.append(f"Reference labels missing from output: {absent_refs}")
    if resolved == "ref2va":
        detail_match = re.search(
            r"(?ms)^detailed_description:\s*(.*?)(?=^overall_soundscape:)", text,
        )
        detail_words = len(re.findall(r"\b[\w'-]+\b", detail_match.group(1))) if detail_match else 0
        if detail_words and not 350 <= detail_words <= 500:
            warnings.append(f"Ref2VA detailed_description has {detail_words} words; 350-500 is recommended")
    return {
        "valid": not errors,
        "mode": resolved,
        "errors": errors,
        "warnings": warnings,
        "sections": list(observed),
        "shotCount": len(shots),
    }
