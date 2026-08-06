# SPDX-License-Identifier: GPL-3.0-only
"""MiniMax H3 prompt construction and validation rules.

The rule set is an original implementation derived from MiniMax's public
T2VA/I2VA/FL2VA/L2VA and full-reference prompt-writing guides.
"""

from __future__ import annotations

from collections import Counter
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
AMBIENCE_FOLEY_POLICIES = ("auto", "ensure_audible", "off")
BACKGROUND_SCORE_POLICIES = ("follow_prompt", "add_instrumental", "off")
VOICE_PERFORMANCES = ("audible", "silent_mouth_acting_experimental", "none")
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
  for voiceover or narration. Treat a quoted thought or internal monologue as audible voiceover: use the exact phrase
  "says in an off-screen voiceover", preserve it in <d>, identify its thinker as a speaker, describe it as an internal
  monologue outside the tag, and state that the character's lips remain closed. Use
  <scenetrans> across cuts and <cutoff> only for intentionally truncated speech.
- The explicit audio policies in the user request override the shared audible-dialogue and sound defaults. Silent
  mouth acting and voice-off modes must omit <d>, speaker IDs, lexical dialogue, narration, and voiceover entirely.
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


def system_prompt_for_mode(mode: str) -> str:
    """Return only the output-contract rules relevant to the resolved H3 mode."""
    base_marker = "\nBase-mode output has exactly these three sections in order:"
    ref_marker = "\nRef2VA output has exactly these six sections in order:"
    common, mode_rules = SYSTEM_PROMPT.split(base_marker, 1)
    base_rules, ref_rules = mode_rules.split(ref_marker, 1)
    if mode == "ref2va":
        return common + ref_marker + ref_rules
    return common + base_marker + base_rules


def resolve_mode(mode: str, reference_context: str = "", basic_prompt: str = "") -> str:
    mode = str(mode).strip().lower()
    if mode not in TASK_MODES:
        raise ValueError(f"Unsupported MiniMax H3 prompt mode {mode!r}")
    if mode != "auto":
        return mode
    has_reference = _REFERENCE_RE.search(reference_context or "") or _ASSET_REFERENCE_RE.search(basic_prompt or "")
    return "ref2va" if has_reference else "t2va"


def _asset_label(kind: str, number: str | int) -> str:
    canonical = {
        "image": "Picture", "imagen": "Picture", "picture": "Picture", "foto": "Picture",
        "video": "Video", "vídeo": "Video", "audio": "Audio",
    }
    return f"<{canonical[str(kind).lower()]} {int(number)}>"


def _definition_labels(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(
        r"(?im)^\s*(<(?:Subject|Picture|Video|Audio)\s+\d+>)\s*(?::|\bis\b)", text or "",
    )))


def _official_reference_model(source_prompt: str, reference_context: str = "") -> dict[str, Any]:
    """Build high-confidence Ref2VA semantics without equating asset and Subject ordinals."""
    source = source_prompt or ""
    explicit_definitions = _definition_labels(reference_context)
    assets = list(dict.fromkeys(
        [_asset_label(kind, number) for kind, number in _ASSET_REFERENCE_RE.findall(source)]
        + _REFERENCE_RE.findall(reference_context or "")
        + _REFERENCE_RE.findall(source)
    ))
    assets = [label for label in assets if not label.casefold().startswith("<subject")]
    if explicit_definitions:
        return {
            "explicit": True,
            "assets": assets,
            "definitions": [],
            "definition_labels": explicit_definitions,
            "provenance_assets": set(),
            "independent_assets": {label for label in explicit_definitions if not label.lower().startswith("<subject")},
            "subjects": [],
            "reveal": None,
        }

    picture_roles = []
    for match in _ROLE_REFERENCE_RE.finditer(source):
        role, kind, number = match.groups()
        role = role.strip()
        pieces = re.split(r"\s+(?:and|y)\s+", role, flags=re.IGNORECASE)
        for piece in pieces:
            if piece.strip():
                picture_roles.append((piece.strip(), _asset_label(kind, number)))

    picture_assets = [label for label in assets if label.lower().startswith("<picture")]
    video_assets = [label for label in assets if label.lower().startswith("<video")]
    audio_assets = [label for label in assets if label.lower().startswith("<audio")]
    subjects = []
    used_assets = set()
    for role, asset in picture_roles:
        lowered = role.casefold()
        if re.search(r"\b(?:style|look|aesthetic|palette|lighting|estilo)\b", lowered):
            contribution = "style"
            description = (
                f"the reusable visual style abstracted from {asset}, including its palette, rendering treatment, "
                "lighting language, and characteristic surface treatment"
            )
            marker = "attribute_transfer"
        elif re.search(r"\b(?:person|persona|man|woman|boy|girl|hombre|mujer|actor|actress|presenter|driver|identity|face|body|character)\b", lowered):
            contribution = "identity"
            description = (
                f"the reusable {role} whose identity, appearance, and wardrobe come from {asset}"
            )
            marker = "fully_preserved"
        else:
            contribution = "design"
            description = (
                f"the reusable {role} whose exact visible design, proportions, materials, colors, and markings come from {asset}"
            )
            marker = "fully_preserved"
        subjects.append({"role": role, "asset": asset, "contribution": contribution,
                         "description": description, "marker": marker})
        used_assets.add(asset)

    independent = {}
    for asset in picture_assets:
        number = re.search(r"\d+", asset).group()
        token = rf"(?:image|imagen|picture|foto)\s*(?:number\s*|n[uú]mero\s*|#\s*)?{number}"
        anchor = re.search(
            rf"(?:{token}.{{0,60}}(?:exact\s+)?(?:first|last|final|key)\s*frame|"
            rf"(?:exact\s+)?(?:first|last|final|key)\s*frame.{{0,60}}{token}|"
            rf"{token}.{{0,60}}(?:storyboard|composition anchor))",
            source,
            flags=re.IGNORECASE,
        )
        if anchor:
            role = "exact first-frame" if re.search(r"first", anchor.group(), re.IGNORECASE) else "frame/composition"
            independent[asset] = {
                "description": f"the supplied image used as an independent {role} anchor",
                "marker": "fully_preserved",
            }
            used_assets.add(asset)

    for asset in video_assets:
        number = re.search(r"\d+", asset).group()
        token = rf"(?:video|vídeo)\s*(?:number\s*|n[uú]mero\s*|#\s*)?{number}"
        motion = re.search(
            rf"(?:motion|movement|action|pose|performance|movimiento|acci[oó]n).{{0,40}}{token}|"
            rf"{token}.{{0,40}}(?:motion|movement|action|pose|performance|movimiento|acci[oó]n)",
            source,
            flags=re.IGNORECASE,
        )
        global_role = re.search(
            rf"(?:continue|continuation|edit|editing|structure|timing|ritmo|continuar).{{0,40}}{token}|"
            rf"{token}.{{0,40}}(?:continue|continuation|edit|editing|structure|timing|ritmo|continuar)",
            source,
            flags=re.IGNORECASE,
        )
        if motion and not global_role:
            subjects.append({
                "role": "referenced motion pattern", "asset": asset, "contribution": "motion",
                "description": f"the reusable body-motion pattern from {asset}, including timing, posture changes, and movement cadence",
                "marker": "attribute_transfer",
            })
            used_assets.add(asset)
        else:
            independent[asset] = {
                "description": "the supplied video used for global edit, continuation, or temporal structure",
                "marker": "partially_preserved",
            }
            used_assets.add(asset)

    for asset in audio_assets:
        exact_copy = bool(re.search(r"\b(?:copy|reuse|reutiliza|copiar)\b", source, re.IGNORECASE))
        independent[asset] = {
            "description": (
                f"the supplied audio signal {'copied as a synchronized audio layer' if exact_copy else 'used as an audio reference for voice, delivery, rhythm, or sound texture'}"
            ),
            "marker": "partially_copy" if exact_copy else "reference",
        }
        used_assets.add(asset)

    for asset in picture_assets:
        if asset not in used_assets:
            subjects.append({
                "role": "referenced visual content", "asset": asset, "contribution": "visual",
                "description": f"the reusable visual content derived from {asset} without treating its composition as a frame anchor",
                "marker": "fully_preserved",
            })
            used_assets.add(asset)

    definitions = []
    for index, subject in enumerate(subjects, 1):
        subject["label"] = f"<Subject {index}>"
        definitions.append({
            "label": subject["label"], "line": f"{subject['label']} is {subject['description']}.",
            "marker": subject["marker"], "asset": subject["asset"], "kind": "subject",
        })
    for label, item in independent.items():
        definitions.append({
            "label": label, "line": f"{label} is {item['description']}.",
            "marker": item["marker"], "asset": label, "kind": label[1:].split()[0].lower(),
        })

    reveal_match = re.search(
        r"\b(?:when|cuando)\s+(?:[^\"“”\r\n]{0,60}?)(?:says?|dice)\s*[\"“]([^\"”\r\n]+)[\"”]",
        source,
        flags=re.IGNORECASE,
    )
    reveal = None
    if reveal_match:
        objects = [item["label"] for item in definitions if item["kind"] == "subject" and
                   not re.search(r"\b(?:person|persona|man|woman|boy|girl|hombre|mujer|presenter)\b",
                                 next((subject["role"] for subject in subjects if subject["label"] == item["label"]), ""),
                                 re.IGNORECASE)]
        if objects:
            reveal = (reveal_match.group(1), [objects[-1]])

    return {
        "explicit": False,
        "assets": assets,
        "definitions": definitions,
        "definition_labels": [item["label"] for item in definitions],
        "provenance_assets": set(assets) - set(independent),
        "independent_assets": set(independent),
        "subjects": subjects,
        "reveal": reveal,
    }


def _official_reference_contract(source_prompt: str, reference_context: str = "") -> str:
    model = _official_reference_model(source_prompt, reference_context)
    if not model["assets"] and not model["definition_labels"]:
        return ""
    if model["explicit"]:
        return (
            "OFFICIAL REF2VA REFERENCE CONTRACT:\n"
            "- REFERENCE CONTEXT definitions are authoritative. Preserve their labels, roles, numbering, and asset "
            "relationships exactly; do not create a competing inferred mapping.\n"
            "- Subjects are reusable visual content. Pictures are independent definitions only for frame, keyframe, "
            "storyboard, or composition anchors. Videos are independent only for global edit/continuation/temporal "
            "structure. Audio labels describe signals and reuse/reference behavior."
        )
    lines = [
        "OFFICIAL REF2VA REFERENCE CONTRACT (authoritative):",
        "- Subject numbering is independent from asset numbering. Assets used only as provenance appear inside a "
        "Subject definition and must not receive standalone Picture/Video definitions or retention lines.",
        *[f"- REQUIRED DEFINITION: {item['line']}" for item in model["definitions"]],
        *[f"- REQUIRED RETENTION: {item['label']}: {item['marker']} - preserve/apply the role stated above."
          for item in model["definitions"]],
        "- Use every defined Subject in detailed_description. Do not invent labels or reinterpret source assets as generated moments.",
    ]
    if model["reveal"]:
        cue, labels = model["reveal"]
        for label in labels:
            lines.append(
                f"- REVEAL LOCK: {label} remains completely concealed until the spoken cue {cue!r}; reveal that "
                "Subject at the cue, never before it, even within the same shot."
            )
    canonical = _ASSET_REFERENCE_RE.sub(lambda match: _asset_label(*match.groups()), source_prompt or "")
    lines.append("CANONICALIZED SOURCE WORDING:\n" + canonical)
    return "\n".join(lines)


def normalize_reference_definitions(text: str, source_prompt: str, reference_context: str = "") -> str:
    """Apply official Ref2VA definitions without overwriting explicit user mappings."""
    model = _official_reference_model(source_prompt, reference_context)
    if model["explicit"] or not model["definitions"]:
        return str(text)
    value = str(text)
    if not _section_body(value, "subject_definitions"):
        return str(text)
    definitions = "\n".join(item["line"] for item in model["definitions"])
    retention = "\n".join(
        f"{item['label']}: {item['marker']} - preserve/apply the role stated above."
        for item in model["definitions"]
    )
    value = _replace_section_body(value, "subject_definitions", definitions)
    value = _replace_section_body(value, "retention_analysis", retention)

    kinds = {item["kind"] for item in model["definitions"]}
    if kinds == {"audio"}:
        task_type = "audio reuse" if any(
            item["marker"] in {"fully_copy", "partially_copy"} for item in model["definitions"]
        ) else "audio reference"
    elif "video" in kinds and re.search(r"\b(?:continue|continuation|continuar)\b", source_prompt, re.IGNORECASE):
        task_type = "continuation"
    elif "video" in kinds and re.search(r"\b(?:edit|editing)\b", source_prompt, re.IGNORECASE):
        task_type = "editing"
    else:
        task_type = "reference generation"
    summary = _section_body(value, "summary").strip()
    summary = re.sub(r"^\[[^\]\r\n]+\]\s*", "", summary)
    value = _replace_section_body(value, "summary", f"[{task_type}] {summary}".rstrip())
    return value


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


def _requires_single_simultaneous_shot(source_prompt: str, duration_seconds: float) -> bool:
    if float(duration_seconds) > 5.0:
        return False
    source = source_prompt or ""
    simultaneous = re.search(
        r"\b(?:while|whilst|mientras|simultaneously|at the same time|al mismo tiempo)\b",
        source,
        flags=re.IGNORECASE,
    )
    explicit_edit = re.search(
        r"\b(?:cut(?:s|ting)?|shot\s+\d+|scene\s+\d+|then|afterwards|despu[eé]s|luego|"
        r"transition|montage|insert|cutaway)\b|\d{1,2}:\d{2}(?:\.\d{1,3})?",
        source,
        flags=re.IGNORECASE,
    )
    return bool(simultaneous and not explicit_edit)


def _source_requests_music(source_prompt: str) -> bool:
    source = source_prompt or ""
    if re.search(r"\b(?:no|without|sin)\s+(?:background\s+|non[- ]diegetic\s+)?m[uú]sic", source, re.IGNORECASE):
        return False
    return bool(re.search(
        r"\b(?:music|m[uú]sica|song|canci[oó]n|score|soundtrack|jazz|orchestra|orchestral|"
        r"piano|guitar|cello|violin|trumpet|drums?|synth)\b",
        source,
        flags=re.IGNORECASE,
    ))


def build_user_request(basic_prompt: str, mode: str, duration_seconds: float,
                       reference_context: str = "", enhance_description: bool = True,
                       ambience_foley_policy: str = "auto",
                       background_score_policy: str = "follow_prompt",
                       voice_performance: str = "audible",
                       instrumental_description: str = "") -> str:
    if ambience_foley_policy not in AMBIENCE_FOLEY_POLICIES:
        raise ValueError(f"Unsupported ambience/foley policy {ambience_foley_policy!r}")
    if background_score_policy not in BACKGROUND_SCORE_POLICIES:
        raise ValueError(f"Unsupported background-score policy {background_score_policy!r}")
    if voice_performance not in VOICE_PERFORMANCES:
        raise ValueError(f"Unsupported voice performance {voice_performance!r}")
    resolved = resolve_mode(mode, reference_context, basic_prompt)
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
            "action continuity, pacing, physical sound, and requested musical treatment. If the user did not request "
            "music, non_diegetic_music must be N/A.\n"
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
            "changes the user's intent. Do not increase gore, damage, or explicitness beyond the source."
        )
    else:
        parts.append(
            "CONSERVATIVE FORMAT ADAPTATION:\n"
            "Convert the request into the required MiniMax H3 structure with only the detail needed for coherent "
            "generation. Do not creatively expand its staging, story, shot design, or sound. Preserve the user's "
            "level of specificity."
        )
    dialogue_contracts = _source_dialogue_contracts(basic_prompt)
    if dialogue_contracts and voice_performance == "audible":
        parts.append(
            "VOICE POLICY — AUDIBLE (official): Assign stable speaker IDs and copy each block exactly once into the "
            "timeline. Do not omit, translate, censor, duplicate, or move it to soundscape:\n"
            + "\n".join(f"- <d>[{language}] {quote}</d>" for language, quote, _internal in dialogue_contracts)
        )
    elif dialogue_contracts and voice_performance == "silent_mouth_acting_experimental":
        profiles = []
        for language, quote, internal in dialogue_contracts:
            word_count = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", quote))
            pauses = len(re.findall(r"[,;:…]|\.\.\.", quote))
            profiles.append(
                f"- {'Internal/off-screen thought' if internal else 'Visible speech'}: {language}; approximately "
                f"{word_count} words; {pauses} marked pause(s)."
            )
        parts.append(
            "VOICE POLICY — SILENT MOUTH ACTING (EXPERIMENTAL, best effort only): Treat visible dialogue as visual "
            "performance guidance. In the final H3 prompt emit no <d>, speaker IDs, dialogue words, quotations, "
            "narration, voiceover, singing, whispering, or intelligible vocal sound. For visible speech, describe one "
            "silent natural mouth/jaw performance using only language, approximate word count, cadence, pauses, and "
            "delivery. For internal or off-screen speech, keep lips closed and retain only the acting beat. Exact "
            "phonetic lip sync and guaranteed silence are not documented H3 capabilities.\n" + "\n".join(profiles)
        )
    elif dialogue_contracts:
        parts.append(
            "VOICE POLICY — NONE: Omit all dialogue words, <d> blocks, speaker IDs, narration, voiceover, singing, "
            "whispering, intelligible background speech, and speech-like mouth performance. Preserve only the visual "
            "actions and expressions associated with the source."
        )

    ambience_contracts = {
        "auto": (
            "AMBIENCE AND FOLEY POLICY — AUTO: Preserve requested ambience, physical sounds, and non-verbal human "
            "sounds. With description enhancement, add only coherent physically motivated non-vocal sounds."
        ),
        "ensure_audible": (
            "AMBIENCE AND FOLEY POLICY — REQUIRED: Create a coherent non-vocal soundscape across the duration using "
            "room tone, environmental ambience, physically motivated foley, impacts, movement, and appropriate "
            "non-verbal human sounds. Do not invent intelligible background speech."
        ),
        "off": (
            "AMBIENCE AND FOLEY POLICY — OFF: Generate no ambience, room tone, environmental noise, foley, impacts, "
            "breathing, laughter, crowd chatter, or other non-musical sound."
        ),
    }
    score_contracts = {
        "follow_prompt": (
            "NON-DIEGETIC MUSIC POLICY — FOLLOW SOURCE: Preserve explicitly requested audience-only music. If the "
            "source does not request it, non_diegetic_music must be N/A. Never invent a score."
        ),
        "add_instrumental": (
            "NON-DIEGETIC MUSIC POLICY — REQUIRED: Create an audience-only instrumental score appropriate to the "
            "scene and describe instrumentation, tempo, rhythm, and dynamics. Add no vocals or lyrics."
        ),
        "off": (
            "NON-DIEGETIC MUSIC POLICY — OFF: No audience-only background music is audible. non_diegetic_music must "
            "be exactly N/A, with no score or instrumental underscore elsewhere."
        ),
    }
    parts.extend((ambience_contracts[ambience_foley_policy], score_contracts[background_score_policy]))
    requested_instrumental = str(instrumental_description or "").strip()
    if background_score_policy == "add_instrumental" and requested_instrumental:
        parts.append(
            "USER-SPECIFIED INSTRUMENTAL SCORE (authoritative): Use the following musical direction for the "
            "audience-only score. Preserve its requested mood, instrumentation, tempo, rhythm, and dynamics; "
            "resolve only genuine omissions needed for coherence. It remains strictly instrumental, with no "
            "singing, lyrics, or vocal samples:\n" + requested_instrumental
        )
    single_shot = _requires_single_simultaneous_shot(basic_prompt, duration_seconds)
    if single_shot:
        parts.append(
            "SHOT PLAN: Exactly one continuous shot. The source describes one simultaneous event; keep all requested "
            "foreground and background actions readable together. Do not add inserts, cutaways, or additional shots.\n"
            "SIMULTANEITY LOCK: The actions joined by while/mientras occur continuously at the same time. Camera motion, "
            "framing, and depth of field must never isolate or obscure either requested action."
        )
    if reference_context.strip():
        parts.append("REFERENCE CONTEXT (authoritative labels and roles):\n" + reference_context.strip())
    positional_contract = _official_reference_contract(basic_prompt, reference_context)
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
    final_checks = [
        "preserve every immutable source fact",
        ("use each exact quoted spoken line once and only once" if voice_performance == "audible"
         else "emit zero audible dialogue and zero lexical source-dialogue text"),
        ("do not invent dialogue or music" if background_score_policy != "add_instrumental"
         else "do not invent dialogue or musical vocals"),
        "use numeric cut times only in later [Shot N] headers",
    ]
    if single_shot:
        final_checks.insert(0, "exactly one continuous shot")
        final_checks.append("keep the simultaneous actions visible together")
    parts.append("FINAL CHECK: " + "; ".join(final_checks) + ".")
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


def _source_dialogue_contracts(source_prompt: str) -> list[tuple[str, str, bool]]:
    contracts = []
    for match in _QUOTED_RE.finditer(source_prompt or ""):
        cue_window = (source_prompt or "")[max(0, match.start() - 180):match.start()]
        if _SPEECH_CUE_RE.search(cue_window):
            contracts.append((
                _source_dialogue_language(source_prompt, match),
                match.group(1),
                _source_quote_is_internal_monologue(source_prompt, match),
            ))
    for language, quote in re.findall(
        r"<d>\s*\[([^\]]+)\]\s*(.*?)\s*</d>", source_prompt or "", flags=re.DOTALL | re.IGNORECASE,
    ):
        item = (language.strip(), quote.strip(), False)
        if item not in contracts:
            contracts.append(item)
    return contracts


def _deduplicate_source_dialogue(text: str, source_prompt: str) -> str:
    expected = {
        f"[{language}] {quote}".casefold() for language, quote, _internal in _source_dialogue_contracts(source_prompt)
    }
    seen: set[str] = set()

    def replace(match):
        inner = re.sub(r"\s+", " ", match.group(1).strip()).casefold()
        if inner in expected:
            if inner in seen:
                return ""
            seen.add(inner)
        return match.group(0)

    return re.sub(r"<d>(.*?)</d>", replace, str(text), flags=re.DOTALL | re.IGNORECASE)


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


def _insert_timeline_instruction(text: str, mode: str, instruction: str) -> str:
    section = "detailed_description" if mode == "ref2va" else "integrated_multimodal_description"
    match = re.search(
        rf"(?ms)(^{re.escape(section)}:\s*)(.*?)(?=^(?:{_SECTION_PATTERN}):\s*|\Z)", str(text),
    )
    if not match:
        return str(text)
    body = match.group(2)
    later_shot = re.search(r"\[Shot\s+[2-9]\d*\]", body, flags=re.IGNORECASE)
    insertion = later_shot.start() if later_shot else len(body)
    body = body[:insertion].rstrip() + " " + instruction + " " + body[insertion:].lstrip()
    return str(text)[:match.start(2)] + body.rstrip() + "\n\n" + str(text)[match.end(2):].lstrip()


def _normalize_suppressed_voice(text: str, source_prompt: str, mode: str, voice_performance: str) -> str:
    value = re.sub(r"<d>.*?</d>", "", str(text), flags=re.DOTALL | re.IGNORECASE)
    contracts = _source_dialogue_contracts(source_prompt)
    for _language, quote, _internal in contracts:
        value = re.sub(rf'["“]?{re.escape(quote)}["”]?', "", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\b(?:their|his|her|the character'?s|the presenter'?s)\s+mouth\s+(?:forming|shaping)\s+"
        r"(?:the\s+)?(?:shape|words?)\s*(?:for|of)?\s*[,;:]?",
        "the character's mouth and jaw articulating silently, ",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\bperforming\s+(?:the\s+)?(?:action\s+of\s+)?(?:the\s+)?(?:required|requested)\s+"
        r"(?:[A-Za-zÀ-ÿ-]+\s+)?(?:phrase|line)\b",
        "performing a silent non-lexical delivery beat",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\s*\(S\d+(?:\s*,\s*S\d+)*\)", "", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\s+in an off-screen voiceover(?:,?\s+as (?:a )?[^:,.]+)?",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\b(?:says?|speaks?|speaking|talks?|talking|asks?|shouts?|whispers?|utters?|"
        r"delivers?\s+(?:(?:his|her|their|the|required)\s+)?(?:line|phrase))\b\s*:?,?",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"The visible character silently performs natural speech-like lip and jaw articulation.*?"
        r"without preserving lexical text\.\s*",
        "",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    value = re.sub(
        r"No voice, whisper, narration, singing, or intelligible vocal sound is audible; exact phonetic lip sync "
        r"is not guaranteed\.\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\s+([,.;:])", r"\1", value)
    if not contracts:
        return value
    if voice_performance == "none":
        instruction = (
            "No dialogue, narration, voiceover, singing, whispering, intelligible speech, or speech-like mouth "
            "performance occurs; the requested visual actions and expressions continue without vocal performance."
        )
    else:
        visible = [(language, quote) for language, quote, internal in contracts if not internal]
        internal_count = sum(1 for _language, _quote, internal in contracts if internal)
        profiles = []
        for language, quote in visible:
            words = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", quote))
            pauses = len(re.findall(r"[,;:…]|\.\.\.", quote))
            profiles.append(
                f"a {language} phrase of approximately {words} words with {pauses} marked pause(s)"
            )
        instructions = []
        if profiles:
            instructions.append(
                "The visible character silently performs natural speech-like lip and jaw articulation for "
                + "; then ".join(profiles)
                + ", matching the intended cadence and expression without preserving lexical text."
            )
        if internal_count:
            instructions.append(
                "For the internal or off-screen thought, the character keeps their lips completely closed and only "
                "performs the intended expression."
            )
        instructions.append(
            "No voice, whisper, narration, singing, or intelligible vocal sound is audible; exact phonetic lip sync "
            "is not guaranteed."
        )
        instruction = " ".join(instructions)
    return _insert_timeline_instruction(value, mode, instruction)


def normalize_source_dialogue(text: str, source_prompt: str, mode: str,
                              voice_performance: str = "audible") -> str:
    """Deterministically retain spoken source quotes and their requested language tags."""
    if voice_performance != "audible":
        return _normalize_suppressed_voice(text, source_prompt, mode, voice_performance)
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
            value = re.sub(
                r"says in an off-screen internal monologue",
                "says in an off-screen voiceover, as a concentrated internal monologue",
                value,
                flags=re.IGNORECASE,
            )
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
                f"The thinking on-screen character (S1) says in an off-screen voiceover, as a concentrated internal "
                f"monologue: {block}, "
                "while the character's lips remain completely closed."
            )
        else:
            additions.append(f"The on-screen speaker (S1) delivers the requested line: {block}.")
    if not additions:
        return _deduplicate_source_dialogue(value, source_prompt)
    section = "detailed_description" if mode == "ref2va" else "integrated_multimodal_description"
    match = re.search(
        rf"(?ms)(^{re.escape(section)}:\s*)(.*?)(?=^(?:{_SECTION_PATTERN}):\s*|\Z)",
        value,
    )
    if not match:
        return value
    body = match.group(2)
    later_shot = re.search(r"\[Shot\s+[2-9]\d*\]", body, flags=re.IGNORECASE)
    insertion = later_shot.start() if later_shot else len(body)
    body = body[:insertion].rstrip() + " " + " ".join(additions) + " " + body[insertion:].lstrip()
    value = value[:match.start(2)] + body.rstrip() + "\n\n" + value[match.end(2):].lstrip()
    return _deduplicate_source_dialogue(value, source_prompt)


def _replace_section_body(text: str, section: str, body: str) -> str:
    match = re.search(
        rf"(?ms)(^{re.escape(section)}:\s*)(.*?)(?=^(?:{_SECTION_PATTERN}):\s*|\Z)", str(text),
    )
    if not match:
        return str(text)
    return str(text)[:match.start(2)] + body.strip() + "\n\n" + str(text)[match.end(2):].lstrip()


def normalize_audio_policy(text: str, ambience_foley_policy: str = "auto",
                           background_score_policy: str = "follow_prompt",
                           voice_performance: str = "audible") -> str:
    value = str(text)
    if background_score_policy == "off":
        value = _replace_section_body(value, "non_diegetic_music", "N/A")
    if ambience_foley_policy == "off":
        soundscape = (
            "N/A" if background_score_policy == "off" and voice_performance != "audible"
            else "No ambience, foley, or non-verbal human sound is audible."
        )
        value = _replace_section_body(value, "overall_soundscape", soundscape)
    elif voice_performance != "audible":
        body = _section_body(value, "overall_soundscape")
        sentences = re.split(r"(?<=[.!?])\s+", body.strip()) if body.strip() else []
        sentences = [item for item in sentences if not re.search(
            r"\b(?:voice|voices|speech|dialogue|spoken|speaking|whisper|narration|vocal|words)\b",
            item,
            re.IGNORECASE,
        )]
        sentences.append("No intelligible speech, vocalization, whispering, or voice is audible.")
        value = _replace_section_body(value, "overall_soundscape", " ".join(sentences))
    return value


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
                    source_prompt: str = "", reference_context: str = "",
                    ambience_foley_policy: str = "auto",
                    background_score_policy: str = "follow_prompt",
                    voice_performance: str = "audible") -> dict[str, Any]:
    resolved = resolve_mode(mode, reference_context, source_prompt)
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
    if _requires_single_simultaneous_shot(source_prompt, duration_seconds) and len(shots) != 1:
        errors.append("The short simultaneous source requires exactly one continuous shot")
    timeline_without_headers = _SHOT_RE.sub("", timeline)
    invented_inline_times = re.findall(
        r"\b(?:At|After)\s+(?:\d+(?:\.\d+)?\s+seconds?|\d+\.\d{2,3})\b",
        timeline_without_headers,
        flags=re.IGNORECASE,
    )
    if invented_inline_times and not any(item.casefold() in (source_prompt or "").casefold() for item in invented_inline_times):
        errors.append("Numeric event times may appear only in shot headers unless supplied by the user")
    final_shot = len(shots) if shots else 1
    alignment = alignment_instruction(resolved, duration_seconds, final_shot)
    if alignment and not text.startswith(alignment + "\n\n"):
        errors.append("Required keyframe alignment instruction is missing, incorrect, or is not the first line")
    if resolved == "t2va" and not text.startswith("integrated_multimodal_description:"):
        errors.append("T2VA must begin directly with integrated_multimodal_description")

    if text.count("<d>") != text.count("</d>"):
        errors.append("Dialogue tags are unbalanced")
    all_dialogue = re.findall(r"<d>(.*?)</d>", text, flags=re.DOTALL | re.IGNORECASE)
    timeline_dialogue = re.findall(r"<d>(.*?)</d>", timeline, flags=re.DOTALL | re.IGNORECASE)
    for dialogue in all_dialogue:
        if not re.match(r"\[[^\]]+\]\s+\S", dialogue.strip()):
            errors.append("Every <d> block must begin with a language tag and contain dialogue")

    source_contracts = _source_dialogue_contracts(source_prompt)
    contracts = source_contracts if voice_performance == "audible" else []

    def dialogue_text(item: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"^\[[^\]]+\]\s*", "", item.strip()))

    normalized_expected = Counter(quote for _language, quote, _internal in contracts)
    normalized_timeline = Counter(dialogue_text(item) for item in timeline_dialogue)
    if normalized_timeline != normalized_expected:
        missing = list((normalized_expected - normalized_timeline).elements())
        extra = list((normalized_timeline - normalized_expected).elements())
        if missing:
            errors.append(f"Required spoken dialogue is missing or duplicated incorrectly: {missing}")
        if extra:
            errors.append(f"Invented or duplicated dialogue is not allowed: {extra}")
    if Counter(dialogue_text(item) for item in all_dialogue) != normalized_timeline:
        errors.append("Dialogue blocks must appear only inside the timeline section")

    for language, quote, _internal in contracts:
        if language == "Original language":
            continue
        exact = f"[{language}] {quote}"
        if sum(re.sub(r"\s+", " ", item.strip()) == exact for item in timeline_dialogue) != 1:
            errors.append(f"Dialogue must preserve its requested language marker exactly: {exact!r}")

    if any(internal for _language, _quote, internal in contracts):
        if "says in an off-screen voiceover" not in timeline.lower():
            errors.append("Internal monologue must use the exact off-screen voiceover phrase")
        if not re.search(r"lips\s+remain\s+(?:completely\s+)?closed", timeline, re.IGNORECASE):
            errors.append("Internal monologue must state that the character's lips remain closed")

    missing_quotes = [quote for quote in _QUOTED_RE.findall(source_prompt or "") if quote not in text]
    if voice_performance != "audible":
        missing_quotes = []
        leaked = [quote for _language, quote, _internal in source_contracts if quote in text]
        if leaked:
            errors.append(f"Suppressed source dialogue leaked into the final prompt: {leaked}")
        if all_dialogue:
            errors.append("Voice-suppressed modes require zero <d> blocks")
        if re.search(r"\(S\d+(?:\s*,\s*S\d+)*\)", timeline, re.IGNORECASE):
            errors.append("Voice-suppressed modes must not retain speaker IDs")
        if voice_performance == "silent_mouth_acting_experimental":
            if source_contracts and "silently performs natural speech-like lip and jaw articulation" not in timeline:
                visible_contracts = [item for item in source_contracts if not item[2]]
                if visible_contracts:
                    errors.append("Silent mouth acting requires one non-lexical visual articulation instruction")
            warnings.append(
                "Silent mouth acting is experimental prompt-only guidance; silence and phonetic lip sync are not guaranteed"
            )
    if missing_quotes:
        errors.append("Quoted source text was not preserved exactly: " + repr(missing_quotes))
    source_dialogue = re.findall(r"<d>(.*?)</d>", source_prompt or "", flags=re.DOTALL)
    missing_dialogue = [item for item in source_dialogue if item not in text]
    if missing_dialogue:
        errors.append("Source <d> dialogue was not preserved exactly")
    tagged_dialogue = "\n".join(re.findall(r"<d>(.*?)</d>", text, flags=re.DOTALL))
    for match in _QUOTED_RE.finditer(source_prompt or ""):
        cue_window = (source_prompt or "")[max(0, match.start() - 100):match.start()]
        if voice_performance == "audible" and _SPEECH_CUE_RE.search(cue_window) and match.group(1) not in tagged_dialogue:
            errors.append(f"Quoted spoken dialogue must appear inside a language-tagged <d> block: {match.group(1)!r}")
    source_requests_voiceover = re.search(
        r"\b(?:voice[ -]?over|narrat(?:e|es|ed|ion)|off-screen voice|voz en off|narraci[oó]n|"
        r"think|thinks|thinking|thought|piensa|pensando|pensamiento|reflexiona|reflexionando|mon[oó]logo)\b",
        source_prompt or "",
        flags=re.IGNORECASE,
    )
    if (re.search(r"\b(?:off-screen voiceover|voice[ -]?over|voz en off)\b", text, re.IGNORECASE)
            and (not source_requests_voiceover or voice_performance != "audible")):
        errors.append("Output invented voiceover although the source requested visible dialogue")

    music = _section_body(text, "non_diegetic_music").strip()
    if background_score_policy == "off" and music.casefold() != "n/a":
        errors.append("non_diegetic_music must be N/A when background score is off")
    elif background_score_policy == "follow_prompt" and not _source_requests_music(source_prompt) and music.casefold() != "n/a":
        errors.append("non_diegetic_music must be N/A when the source did not request music")
    elif background_score_policy == "add_instrumental" and music.casefold() == "n/a":
        errors.append("An instrumental non-diegetic score is required by the selected audio policy")

    soundscape = _section_body(text, "overall_soundscape").strip()
    if ambience_foley_policy == "off" and soundscape.casefold() not in {
        "n/a", "no ambience, foley, or non-verbal human sound is audible."
    }:
        errors.append("overall_soundscape violates the ambience/foley off policy")
    if ambience_foley_policy == "ensure_audible" and soundscape.casefold() == "n/a":
        errors.append("A non-vocal ambience and foley soundscape is required by the selected audio policy")
    positive_soundscape = re.sub(
        r"\bNo intelligible speech, vocalization, whispering, or voice is audible\.?",
        "",
        soundscape,
        flags=re.IGNORECASE,
    )
    if voice_performance != "audible" and re.search(
        r"\b(?:dialogue|spoken words|audible voice|whispering|narration|singing)\b",
        positive_soundscape,
        re.IGNORECASE,
    ):
        errors.append("Voice-suppressed mode forbids intelligible vocal sound in overall_soundscape")

    if resolved == "ref2va":
        reference_model = _official_reference_model(source_prompt, reference_context)
        detail_match = re.search(
            r"(?ms)^detailed_description:\s*(.*?)(?=^overall_soundscape:)", text,
        )
        detail_words = len(re.findall(r"\b[\w'-]+\b", detail_match.group(1))) if detail_match else 0
        detail_text = detail_match.group(1) if detail_match else ""
        definitions = _section_body(text, "subject_definitions")
        output_refs = {item.casefold() for item in _REFERENCE_RE.findall(text)}
        allowed_refs = {item.casefold() for item in (*reference_model["assets"], *reference_model["definition_labels"])}
        invented = sorted(output_refs - allowed_refs)
        if invented:
            errors.append(f"Output invented reference labels not supplied or derived by the contract: {invented}")
        required_refs = allowed_refs
        absent = sorted(required_refs - output_refs)
        if absent:
            errors.append(f"Reference labels missing from output: {absent}")

        defined_labels = [item.casefold() for item in _definition_labels(definitions)]
        for label in reference_model["definition_labels"]:
            count = defined_labels.count(label.casefold())
            if count != 1:
                errors.append(f"{label} must have exactly one subject_definitions entry; observed {count}")
        for label in reference_model["provenance_assets"]:
            if label.casefold() in defined_labels:
                errors.append(f"{label} is provenance-only and must be cited inside a Subject, not defined independently")
        for subject in reference_model["subjects"]:
            label = subject["label"]
            definition = re.search(rf"(?im)^\s*{re.escape(label)}\s*:?.*$", definitions)
            if not definition or subject["asset"].casefold() not in definition.group(0).casefold():
                errors.append(f"{label} must cite its provenance asset {subject['asset']}")
            if label.casefold() not in detail_text.casefold():
                errors.append(f"{label} must be applied inside detailed_description")
        for label in reference_model["independent_assets"]:
            if label.casefold() not in detail_text.casefold():
                errors.append(f"Independent reference {label} must be applied inside detailed_description")

        retention = _section_body(text, "retention_analysis")
        visual_markers = {"fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference"}
        audio_markers = {"fully_copy", "partially_copy", "reference", "weak_reference"}
        expected_items = {item["label"].casefold(): item for item in reference_model["definitions"]}
        for line in [item.strip() for item in retention.splitlines() if item.strip()]:
            if not re.match(r"^<(?:Subject|Picture|Video|Audio)\s+\d+>", line, re.IGNORECASE):
                errors.append("Every retention_analysis line must begin with its defined reference label")
        for label in reference_model["definition_labels"]:
            lines = re.findall(rf"(?im)^\s*{re.escape(label)}[^\r\n]*$", retention)
            if len(lines) != 1:
                errors.append(f"{label} requires exactly one retention_analysis line; observed {len(lines)}")
                continue
            marker_match = re.search(r":\s*([a-z_]+)\b", lines[0], re.IGNORECASE)
            if not marker_match:
                errors.append(f"{label} retention line requires a documented marker")
                continue
            marker = marker_match.group(1).casefold()
            item = expected_items.get(label.casefold())
            allowed = audio_markers if item and item["kind"] == "audio" else visual_markers
            if marker not in allowed:
                errors.append(f"{label} uses incompatible retention marker {marker!r}")
            if item and marker != item["marker"]:
                errors.append(f"{label} retention marker must be {item['marker']!r}, observed {marker!r}")

        if re.search(r"(?im)^\s*<Audio\s+\d+>[^\r\n]*:\s*fully_copy\b", retention):
            if ambience_foley_policy == "off" or background_score_policy == "off" or voice_performance != "audible":
                errors.append(
                    "A fully copied Audio reference cannot be selectively stripped by ambience, music, or voice-off policies"
                )
        if voice_performance != "audible" and re.search(
            r"<Audio\s+\d+>[^\r\n]*(?:voice|timbre|speaker|delivery)",
            (reference_context or "") + "\n" + definitions,
            re.IGNORECASE,
        ):
            warnings.append("Voice-related Audio reference is unused while audible voice is suppressed")

        summary = _section_body(text, "summary").lstrip()
        if not re.match(
            r"\[(?:reference generation|generation|keyframe completion|editing|continuation|audio reuse|audio reference)(?:\s*/\s*(?:reference generation|generation|keyframe completion|editing|continuation|audio reuse|audio reference))*\]",
            summary,
            flags=re.IGNORECASE,
        ):
            errors.append("summary must begin with documented bracketed Ref2VA task type(s)")

        reveal = reference_model["reveal"]
        if reveal:
            cue, subject_labels = reveal
            cue_position = detail_text.lower().find(cue.lower().rstrip("?.!"))
            visual_detail = re.sub(r"<d>.*?</d>", lambda match: " " * len(match.group(0)), detail_text,
                                   flags=re.IGNORECASE | re.DOTALL)
            for label in subject_labels:
                before = visual_detail[:max(0, cue_position)] if cue_position >= 0 else ""
                before = before[:max(0, len(before) - 180)]
                role = next((item["role"] for item in reference_model["subjects"] if item["label"] == label), "")
                visible_before = re.search(
                    rf"(?:{re.escape(label)}[^.]*\b(?:visibl\w*|holds?|shows?|wears?|uses?|reveals?)\b|"
                    rf"\b(?:visibl\w*|holds?|shows?|wears?|uses?|reveals?)\b[^.]*{re.escape(label)}|"
                    rf"\b(?:holds?|shows?|wears?|uses?|reveals?)\b[^.]*\b{re.escape(role)}\b)",
                    before,
                    flags=re.IGNORECASE,
                )
                if visible_before:
                    errors.append(f"{label} becomes visible before the user-specified reveal cue {cue!r}")
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
