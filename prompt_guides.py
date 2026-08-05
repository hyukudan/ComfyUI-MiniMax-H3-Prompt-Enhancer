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
_ALL_SECTIONS = tuple(dict.fromkeys((*BASE_SECTIONS, *REFERENCE_SECTIONS)))
_SECTION_PATTERN = "|".join(map(re.escape, _ALL_SECTIONS))
_SECTION_RE = re.compile(rf"(?m)^({_SECTION_PATTERN}):\s*")
_SHOT_RE = re.compile(r"\[Shot\s+(\d+)\](?:\s+At\s+(\d{2}):(\d{2})\.(\d{3}),)?", re.IGNORECASE)
_REFERENCE_RE = re.compile(r"<(?:Subject|Picture|Video|Audio)\s+\d+>", re.IGNORECASE)
_ASSET_REFERENCE_RE = re.compile(
    r"\b(image|imagen|picture|foto|video|vídeo|audio)\s*(?:number\s*|n[uú]mero\s*|#\s*)?(\d+)\b",
    re.IGNORECASE,
)
_ROLE_REFERENCE_RE = re.compile(
    r"\b(?:the|a|an|el|la|los|las|un|una)\s+"
    r"([\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,4})\s+"
    r"(?:in|en|from|de)\s+(image|imagen|picture|foto)\s*(\d+)\b",
    re.IGNORECASE,
)
_QUOTED_RE = re.compile(r'["“]([^"”\r\n]+)["”]')
_INTERNAL_MONOLOGUE_CUE_RE = re.compile(
    r"\b(?:think|thinks|thinking|thought|inner\s+monologue|internal\s+monologue|"
    r"piensa|pensando|pensamiento|mon[oó]logo\s+interno|reflexiona|reflexionando)\b",
    re.IGNORECASE,
)
_SPEECH_CUE_RE = re.compile(
    r"\b(?:say|says|said|saying|state|states|ask|asks|asking|shout|shouts|shouting|"
    r"whisper|whispers|whispering|speak|speaks|speaking|dice|dijo|diciendo|pregunta|"
    r"preguntando|grita|gritando|susurra|susurrando|habla|hablando|think|thinks|thinking|"
    r"thought|piensa|pensando|pensamiento|reflexiona|reflexionando|mon[oó]logo)\b",
    re.IGNORECASE,
)
_LANGUAGE_ALIASES = {
    "catalonian": "Catalan",
    "catalan": "Catalan",
    "catalán": "Catalan",
    "catala": "Catalan",
    "català": "Catalan",
    "castilian": "Spanish",
    "castellano": "Spanish",
    "español": "Spanish",
}


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
  for voiceover or narration. Treat a quoted thought or internal monologue as audible off-screen internal monologue:
  preserve it in <d>, identify its thinker as a speaker, and state that the character's lips remain closed. Use
  <scenetrans> across cuts and <cutoff> only for intentionally truncated speech.
- Put visible text in straight English double quotes exactly as supplied.
- Positional source references are immutable bindings: image/imagen/picture N always means <Picture N>, video N
  means <Video N>, and audio N means <Audio N>. They name user-provided assets, never generated shots or moments.
  Preserve the referenced person's identity or object's exact visible design wherever it appears. Never invent a
  Picture, Video, or Audio label that the request/reference context did not provide. Do not reveal an object before
  the action or spoken cue where the user explicitly says it first becomes visible.
- Preserve every referenced object's concrete noun, subtype, visible attributes, materials, markings, proportions,
  and identity. Do not silently replace a supplied object with a generic or semantically related alternative.
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


def _plain_asset_bindings(source_prompt: str) -> dict[str, str]:
    kind_map = {"image": "Picture", "imagen": "Picture", "picture": "Picture", "foto": "Picture",
                "video": "Video", "vídeo": "Video", "audio": "Audio"}
    bindings: dict[str, str] = {}
    for kind, number in _ASSET_REFERENCE_RE.findall(source_prompt or ""):
        label = f"<{kind_map[kind.lower()]} {int(number)}>"
        bindings[label] = f"the exact user-provided {kind.lower()} {int(number)}"
    for role, kind, number in _ROLE_REFERENCE_RE.findall(source_prompt or ""):
        label = f"<Picture {int(number)}>"
        bindings[label] = (
            f"the exact user-provided {kind.lower()} {int(number)}, whose referenced visible role is {role.strip()}"
        )
    return bindings


def _plain_picture_roles(source_prompt: str) -> dict[int, str]:
    roles: dict[int, str] = {}
    for role, _kind, number in _ROLE_REFERENCE_RE.findall(source_prompt or ""):
        roles[int(number)] = role.strip()
    return roles


def _explicit_reveal(source_prompt: str) -> tuple[str, list[str]] | None:
    reveal = re.search(
        r"\b(?:when|cuando)\s+(?:[^\"“”\r\n]{0,40}?)(?:says?|dice)\s*[\"“]([^\"”\r\n]+)[\"”]",
        source_prompt or "",
        flags=re.IGNORECASE,
    )
    if not reveal:
        return None
    object_labels = []
    for role, _kind, number in _ROLE_REFERENCE_RE.findall(source_prompt or ""):
        if not re.search(r"\b(?:person|persona|man|woman|hombre|mujer|actor|actress)\b", role, re.IGNORECASE):
            object_labels.append(f"<Picture {int(number)}>")
    return reveal.group(1), list(dict.fromkeys(object_labels))


def _positional_reference_contract(source_prompt: str) -> str:
    bindings = _plain_asset_bindings(source_prompt)
    if not bindings:
        return ""
    canonical = _ASSET_REFERENCE_RE.sub(
        lambda match: f"<{ {'image': 'Picture', 'imagen': 'Picture', 'picture': 'Picture', 'foto': 'Picture', 'video': 'Video', 'vídeo': 'Video', 'audio': 'Audio'}[match.group(1).lower()] } {int(match.group(2))}>",
        source_prompt,
    )
    lines = [
        "POSITIONAL REFERENCE CONTRACT (authoritative; labels identify input assets, not timeline moments):",
        *[f"- {label} is {description}. Preserve its identity, shape, proportions, colors, materials, markings, and distinctive details."
          for label, description in bindings.items()],
        *[f"- <Subject {number}> is the reusable {role} shown in <Picture {number}>. Use <Subject {number}> for that entity throughout detailed_description and <Picture {number}> as its immutable source anchor."
          for number, role in _plain_picture_roles(source_prompt).items()],
        "- Do not create any additional <Picture N>, <Video N>, or <Audio N> labels unless explicitly supplied.",
        "- Clauses such as 'the person in image 1 ... the object in image 2' bind source identity/design only; "
        "they do not make the object visible at the start. A later explicit reveal action or spoken cue overrides them.",
        "CANONICALIZED SOURCE WORDING:\n" + canonical,
    ]
    reveal = _explicit_reveal(source_prompt)
    if reveal:
        cue, labels = reveal
        for label in labels:
            lines.insert(-1, (
                f"- REVEAL LOCK: {label} must remain completely concealed and must not be named in "
                f"detailed_description before the spoken cue {cue!r}. At that exact cue, reveal the exact source "
                f"asset {label}; never show or present it earlier."
            ))
    return "\n".join(lines)


def normalize_reference_definitions(text: str, source_prompt: str) -> str:
    """Make positional asset definitions factual even when a small LLM turns them into story beats."""
    bindings = _plain_asset_bindings(source_prompt)
    if not bindings:
        return str(text)
    definitions = _section_body(str(text), "subject_definitions")
    if not definitions:
        return str(text)
    for label, description in bindings.items():
        canonical = (
            f"{label} is {description}; preserve its exact visible identity/design, shape, proportions, colors, "
            "materials, markings, and distinctive details."
        )
        pattern = re.compile(rf"(?im)^{re.escape(label)}\s*:?\s*.*$")
        if pattern.search(definitions):
            definitions = pattern.sub(canonical, definitions, count=1)
        else:
            definitions = canonical + "\n" + definitions
    for number, role in _plain_picture_roles(source_prompt).items():
        subject_label = f"<Subject {number}>"
        canonical = (
            f"{subject_label} is the reusable {role} shown in <Picture {number}>; preserve the exact identity/design "
            "from that supplied source asset whenever the subject appears."
        )
        pattern = re.compile(rf"(?im)^{re.escape(subject_label)}\s*:?\s*.*$")
        if pattern.search(definitions):
            definitions = pattern.sub(canonical, definitions, count=1)
        else:
            definitions = canonical + "\n" + definitions
    section_match = re.search(
        rf"(?ms)(^subject_definitions:\s*)(.*?)(?=^(?:{_SECTION_PATTERN}):\s*|\Z)",
        str(text),
    )
    if not section_match:
        return str(text)
    return str(text)[:section_match.start()] + section_match.group(1) + definitions.strip() + "\n\n" + str(text)[section_match.end():].lstrip()


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
                       reference_context: str = "", enhance_description: bool = True) -> str:
    resolved = resolve_mode(mode, reference_context)
    alignment = alignment_instruction(resolved, duration_seconds)
    parts = [
        f"TASK MODE: {resolved.upper()}",
        f"TARGET DURATION: {float(duration_seconds):.3f} seconds",
        "BASIC USER PROMPT (authoritative; preserve its intent and exact quoted content):\n" + basic_prompt.strip(),
    ]
    if bool(enhance_description):
        parts.append(
            "ACTIVE DIRECTORIAL ENHANCEMENT (develop the request, without changing it):\n"
            "- Turn terse wording into a concrete, vivid audiovisual sequence across the full target duration.\n"
            "- Improve composition, blocking, facial performance, lighting, materials, atmosphere, camera motion, "
            "action continuity, pacing, physical sound, and requested musical treatment.\n"
            "- Make causal beats and important reveals easy to follow. Allocate enough screen time for each requested "
            "action and spoken line.\n"
            "- Add a cut only when it creates a meaningful change of viewpoint, time, location, scale, or information; "
            "otherwise prefer a motivated continuous camera move.\n"
            "- Default to one continuous shot when the source describes one simultaneous moment or action. Do not "
            "invent inserts, cutaways, or extra shots merely to dramatize an object, impact, or already-visible action.\n"
            "- Express absolute cut times only in [Shot N] headers. Do not add competing numeric timestamps inside a "
            "shot, and never create another shot or vocal cue to repeat or continue the same short line.\n"
            "- Enrich delivery around quoted speech, but never rewrite, extend, translate, censor, or replace its words.\n"
            "- Do not invent new characters, plot events, dialogue, branded objects, reference assets, or an ending that "
            "changes the user's intent."
        )
    else:
        parts.append(
            "CONSERVATIVE FORMAT ADAPTATION:\n"
            "Convert the request into the required MiniMax H3 structure with only the detail needed for coherent "
            "generation. Do not creatively expand its staging, story, shot design, or sound. Preserve the user's "
            "level of specificity."
        )
    dialogue_contracts = []
    for match in _QUOTED_RE.finditer(basic_prompt or ""):
        cue_window = (basic_prompt or "")[max(0, match.start() - 180):match.start()]
        if _SPEECH_CUE_RE.search(cue_window):
            dialogue_contracts.append(
                f'- <d>[{_source_dialogue_language(basic_prompt, match)}] {match.group(1)}</d>'
            )
    if dialogue_contracts:
        parts.append(
            "MANDATORY DIALOGUE CONTRACT (copy each block verbatim into the shot where it is spoken; "
            "do not omit, translate, censor, or move it to soundscape):\n" + "\n".join(dialogue_contracts)
        )
    if reference_context.strip():
        parts.append("REFERENCE CONTEXT (authoritative labels and roles):\n" + reference_context.strip())
    positional_contract = _positional_reference_contract(basic_prompt)
    if positional_contract:
        parts.append(positional_contract)
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


def _source_dialogue_language(source_prompt: str, quote_match) -> str:
    window = (source_prompt or "")[max(0, quote_match.start() - 180):quote_match.start()]
    matches = re.findall(
        r"\b(?:in|en)\s+(?:(?:the\s+)?([\wÀ-ÿ-]+)\s+(?:language|idioma)|"
        r"(?:language|idioma)\s+([\wÀ-ÿ-]+))",
        window,
        flags=re.IGNORECASE,
    )
    if matches:
        raw = next((part for part in matches[-1] if part), "").strip()
        return _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize()) or "Original language"
    known = re.findall(
        r"\b(?:in|en)\s+(english|spanish|french|german|italian|portuguese|japanese|korean|"
        r"chinese|russian|arabic|hindi|dutch|polish|turkish|catalonian|catalan|catalán|català|"
        r"español|castilian|castellano)\b",
        window,
        flags=re.IGNORECASE,
    )
    if known:
        raw = known[-1]
        return _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize())
    quote = quote_match.group(1)
    if re.search(r"[¿¡]|\b(?:quién|qué|cuál|cuándo|dónde|cómo|por qué)\b", quote, re.IGNORECASE):
        return "Spanish"
    return "Original language"


def _source_quote_is_internal_monologue(source_prompt: str, quote_match) -> bool:
    window = (source_prompt or "")[max(0, quote_match.start() - 180):quote_match.start()]
    return bool(_INTERNAL_MONOLOGUE_CUE_RE.search(window))


def _remove_internal_monologue_placeholders(text: str) -> str:
    """Remove vague duplicate vocal cues before restoring one exact thought line."""
    parts = re.split(r"(?<=[.!?])(?=\s+|\Z)", str(text))
    cleaned = []
    for sentence in parts:
        has_dialogue = "<d>" in sentence
        if not has_dialogue and re.search(
            r"\b(?:speaks?|says?|utters?)\b[^.!?]*\b(?:focus|concentrat|killer|thought)",
            sentence,
            flags=re.IGNORECASE,
        ):
            continue
        sentence = re.sub(
            r"\s+as\s+(?:he|she|they|the character|the detective)\s+"
            r"(?:delivers?\s+(?:his|her|their|the)\s+line|speaks?)\s*,?\s*(?:but\s+)?",
            " while ",
            sentence,
            flags=re.IGNORECASE,
        )
        if not has_dialogue:
            sentence = re.sub(
                r"\b(?:his|her|their|the detective's|the character's)?\s*internal monologue\b",
                "concentrated thought",
                sentence,
                flags=re.IGNORECASE,
            )
        cleaned.append(sentence)
    return "".join(cleaned)


def normalize_source_dialogue(text: str, source_prompt: str, mode: str) -> str:
    """Deterministically retain spoken source quotes and their requested language tags."""
    value = str(text)
    additions = []
    for match in _QUOTED_RE.finditer(source_prompt or ""):
        cue_window = (source_prompt or "")[max(0, match.start() - 180):match.start()]
        if not _SPEECH_CUE_RE.search(cue_window):
            continue
        quote = match.group(1)
        language = _source_dialogue_language(source_prompt, match)
        block = f"<d>[{language}] {quote}</d>"
        is_internal_monologue = _source_quote_is_internal_monologue(source_prompt, match)
        if is_internal_monologue:
            value = _remove_internal_monologue_placeholders(value)
        tagged = re.compile(
            rf"<d>\[[^\]]+\]\s*{re.escape(quote)}\s*</d>",
            flags=re.IGNORECASE,
        )
        if tagged.search(value):
            value = tagged.sub(block, value)
            continue
        quoted = re.compile(rf'["“]{re.escape(quote)}["”]')
        if quoted.search(value):
            value = quoted.sub(block, value, count=1)
            continue
        if quote in value:
            value = value.replace(quote, block, 1)
            continue
        if is_internal_monologue:
            additions.append(
                f"The thinking on-screen character (S1) says in an off-screen internal monologue: {block}, "
                "while the character's lips remain completely closed."
            )
        else:
            additions.append(f"The on-screen speaker (S1) delivers the requested line: {block}.")
    if not additions:
        return value
    section = "detailed_description" if mode == "ref2va" else "integrated_multimodal_description"
    match = re.search(
        rf"(?ms)(^{re.escape(section)}:\s*)(.*?)(?=^(?:{_SECTION_PATTERN}):\s*|\Z)",
        value,
    )
    if not match:
        return value
    body = match.group(2).rstrip() + " " + " ".join(additions)
    return value[:match.start(2)] + body + "\n\n" + value[match.end(2):].lstrip()


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


def normalize_shot_timeline(text: str, mode: str, duration_seconds: float) -> str:
    """Replace missing/placeholder later-shot times with deterministic in-duration cut points."""
    section = "detailed_description" if mode == "ref2va" else "integrated_multimodal_description"
    section_match = re.search(
        rf"(?ms)(^{re.escape(section)}:\s*)(.*?)(?=^(?:{_SECTION_PATTERN}):\s*|\Z)",
        str(text),
    )
    if not section_match:
        return str(text)
    body = section_match.group(2)
    markers = list(re.finditer(r"\[Shot\s+(\d+)\]", body, flags=re.IGNORECASE))
    if len(markers) < 2:
        return str(text)
    shot_count = max(int(item.group(1)) for item in markers)
    for shot_number in range(2, shot_count + 1):
        cut = float(duration_seconds) * (shot_number - 1) / shot_count
        minutes = int(cut // 60)
        seconds = cut - minutes * 60
        timestamp = f"{minutes:02d}:{seconds:06.3f}"
        pattern = re.compile(
            rf"\[Shot\s+{shot_number}\](?:\s+At\s+(?:\d{{2}}:[0-9Xx]{{2}}\.[0-9Xx]{{3}}|[0-9Xx]{{2}}:[0-9Xx]{{2}}\.[0-9Xx]{{3}}),?)?",
            re.IGNORECASE,
        )
        match = pattern.search(body)
        if match and not re.fullmatch(
            rf"\[Shot\s+{shot_number}\]\s+At\s+\d{{2}}:\d{{2}}\.\d{{3}},?",
            match.group(0), flags=re.IGNORECASE,
        ):
            body = body[:match.start()] + f"[Shot {shot_number}] At {timestamp}," + body[match.end():]
    return str(text)[:section_match.start()] + section_match.group(1) + body + str(text)[section_match.end():]


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
        rf"(?ms)^{re.escape(section)}:\s*(.*?)(?=^(?:{_SECTION_PATTERN}):\s*|\Z)",
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
        r"\b(?:voice[ -]?over|narrat(?:e|es|ed|ion)|off-screen voice|voz en off|narraci[oó]n|"
        r"think|thinks|thinking|thought|piensa|pensando|pensamiento|reflexiona|reflexionando|mon[oó]logo)\b",
        source_prompt or "",
        flags=re.IGNORECASE,
    )
    if re.search(r"\b(?:off-screen voiceover|voice[ -]?over|voz en off)\b", text, re.IGNORECASE) and not source_requests_voiceover:
        errors.append("Output invented voiceover although the source requested visible dialogue")

    required_refs = set(_REFERENCE_RE.findall(reference_context or ""))
    plain_bindings = _plain_asset_bindings(source_prompt or "")
    required_refs.update(plain_bindings)
    output_refs = set(_REFERENCE_RE.findall(text))
    absent_refs = sorted(required_refs - output_refs)
    if absent_refs:
        errors.append(f"Reference labels missing from output: {absent_refs}")
    if resolved == "ref2va":
        detail_match = re.search(
            r"(?ms)^detailed_description:\s*(.*?)(?=^overall_soundscape:)", text,
        )
        detail_words = len(re.findall(r"\b[\w'-]+\b", detail_match.group(1))) if detail_match else 0
        detail_text = detail_match.group(1) if detail_match else ""
        picture_roles = _plain_picture_roles(source_prompt or "")
        for label in plain_bindings:
            applied = label.lower() in detail_text.lower()
            picture_number = re.fullmatch(r"<Picture\s+(\d+)>", label, re.IGNORECASE)
            if picture_number and int(picture_number.group(1)) in picture_roles:
                applied = applied or f"<subject {int(picture_number.group(1))}>" in detail_text.lower()
            if not applied:
                errors.append(f"Positional reference {label} must be applied inside detailed_description")
        explicit_assets = {
            item.lower() for item in _REFERENCE_RE.findall(reference_context or "")
            if not item.lower().startswith("<subject")
        }
        allowed_assets = explicit_assets | {item.lower() for item in plain_bindings}
        output_assets = {
            item.lower() for item in output_refs if not item.lower().startswith("<subject")
        }
        invented_assets = sorted(output_assets - allowed_assets)
        if invented_assets:
            errors.append(f"Output invented reference assets not supplied by the user: {invented_assets}")
        definitions = _section_body(text, "subject_definitions")
        for label in plain_bindings:
            definition = re.search(
                rf"(?im)^{re.escape(label)}\s*:?\s*(.+)$", definitions,
            )
            if not definition:
                errors.append(f"{label} requires an explicit source-asset definition")
                continue
            line = definition.group(1)
            if not re.search(r"\b(?:source|provided|reference|input)\s+(?:image|picture|video|audio)\b", line, re.IGNORECASE):
                errors.append(f"{label} definition must identify it as the supplied source asset, not a generated moment")
            if re.search(r"\b(?:moment|final shot|initial setup|scene transition)\b", line, re.IGNORECASE):
                errors.append(f"{label} was reinterpreted as a timeline moment instead of an input asset")
        for number, role in picture_roles.items():
            subject_label = f"<Subject {number}>"
            binding = re.search(
                rf"(?im)^{re.escape(subject_label)}\s*:?\s*(.+)$", definitions,
            )
            if not binding or f"<picture {number}>" not in binding.group(1).lower():
                errors.append(f"{subject_label} must bind the source role {role!r} to <Picture {number}>")
            if subject_label.lower() not in detail_text.lower():
                errors.append(f"{subject_label} must be used for the referenced {role!r} in detailed_description")
        retention = _section_body(text, "retention_analysis")
        allowed_markers = {
            "fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference",
            "fully_copy", "partially_copy", "reference",
        }
        for marker in re.findall(r"(?m)^([a-z_]+):", retention):
            if marker not in allowed_markers:
                errors.append(f"Unsupported retention marker {marker!r}; use only documented visual/audio markers")
        reveal = _explicit_reveal(source_prompt or "")
        if reveal:
            cue, object_labels = reveal
            cue_position = detail_text.lower().find(cue.lower().rstrip("?.!"))
            visual_detail = re.sub(r"<d>.*?</d>", lambda match: " " * len(match.group(0)), detail_text,
                                   flags=re.IGNORECASE | re.DOTALL)
            for label in object_labels:
                picture_number = int(re.search(r"\d+", label).group())
                role = picture_roles.get(picture_number, "")
                candidates = [
                    position for position in (
                        detail_text.lower().find(label.lower()),
                        detail_text.lower().find(f"<subject {picture_number}>")
                    ) if position >= 0
                ]
                role_match = re.search(rf"\b{re.escape(role)}\b", visual_detail, re.IGNORECASE) if role else None
                if role_match:
                    candidates.append(role_match.start())
                first_reference = min(candidates) if candidates else -1
                if cue_position >= 0 and 0 <= first_reference < cue_position:
                    label_shots = list(_SHOT_RE.finditer(detail_text[:first_reference + 1]))
                    cue_shots = list(_SHOT_RE.finditer(detail_text[:cue_position + 1]))
                    label_shot = int(label_shots[-1].group(1)) if label_shots else 0
                    cue_shot = int(cue_shots[-1].group(1)) if cue_shots else 0
                    if label_shot != cue_shot:
                        errors.append(
                            f"{label} appears before the user-specified reveal cue {cue!r}"
                        )
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
