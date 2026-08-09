# SPDX-License-Identifier: GPL-3.0-only
"""MiniMax H3 prompt construction and validation rules.

The rule set is an original implementation derived from MiniMax's public
T2VA/I2VA/FL2VA/L2VA and full-reference prompt-writing guides.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import json
import re
from typing import Any

try:
    from .creative_treatments import (
        cinematography_instruction,
        creative_treatment_instruction,
        parse_cinematography,
        parse_creative_treatment,
        parse_shot_plan,
        shot_plan_instruction,
    )
    from .media_manifest import ASPECT_RATIOS, generation_profile, manifest_context, manifest_dialogue, parse_media_manifest
except ImportError:  # pragma: no cover - direct test/import compatibility
    from creative_treatments import (
        cinematography_instruction,
        creative_treatment_instruction,
        parse_cinematography,
        parse_creative_treatment,
        parse_shot_plan,
        shot_plan_instruction,
    )
    from media_manifest import ASPECT_RATIOS, generation_profile, manifest_context, manifest_dialogue, parse_media_manifest


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
TASK_MODES = ("auto", "t2va", "i2va", "fl2va", "l2va", "ref2va", "chained_multishot")
AMBIENCE_FOLEY_POLICIES = ("auto", "ensure_audible", "off")
BACKGROUND_SCORE_POLICIES = ("follow_prompt", "add_instrumental", "off")
VOICE_PERFORMANCES = ("audible", "silent_mouth_acting_experimental", "none")
INSTRUMENTAL_STYLE_CHOICES = (
    "none",
    "cinematic_orchestral",
    "hybrid_orchestral_electronic",
    "action_cinematic",
    "mystery_investigation",
    "suspense_build",
    "combat_rhythmic",
    "chinese_martial_arts",
    "ambient_atmospheric",
    "electronic_modern",
    "synthwave",
    "rock_instrumental",
    "jazz",
    "classical_chamber",
    "folk_acoustic",
    "hip_hop_instrumental",
    "funk_disco",
    "horror_tension",
    "horror_intense",
)
INSTRUMENTAL_STYLE_CONTRACTS = {
    "cinematic_orchestral": (
        "Arrange the supplied musical idea as cinematic orchestra: coherent instrumental families, thematic development, "
        "controlled register, dynamic arcs, and scene-synchronized orchestral density. Do not default to heroic brass, "
        "ostinatos, trailer percussion, choir, or a huge climax."
    ),
    "hybrid_orchestral_electronic": (
        "Blend acoustic orchestral roles with designed electronic pulse, bass, texture, or percussion as one integrated "
        "hybrid score. Keep the balance and transitions purposeful; do not add trailer braams, risers, impacts, choir, or vocals."
    ),
    "action_cinematic": (
        "Turn the supplied musical idea into a forward-driving cinematic action cue with a clearly readable pulse, "
        "short propulsive figures, controlled low-end weight, and event-synchronized rises and releases. Scale density "
        "to action that is actually present; do not invent a chase, fight, danger, trailer braams, choir, or wall-to-wall percussion."
    ),
    "mystery_investigation": (
        "Shape the supplied idea as an investigative mystery underscore with sparse question-and-answer motifs, selective "
        "harmonic ambiguity, transparent texture, and deliberate gaps that leave dialogue and physical clues audible. Do not "
        "imply guilt, crime, danger, supernatural causes, revelation stings, detective pastiche, or a solved mystery."
    ),
    "suspense_build": (
        "Develop the supplied idea as a controlled suspense arc: begin with low event density, establish a stable restrained "
        "pulse or harmonic pressure, and increase register, subdivision, or density only alongside events already requested. "
        "Do not add a threat, countdown, heartbeat, ticking clock, jump-scare sting, braam, scream, or false climax."
    ),
    "combat_rhythmic": (
        "Arrange the supplied idea around physically legible combat rhythm using concise percussion, accented rests, changing "
        "metrical pressure, and synchronized emphasis for contacts that the scene already contains. Preserve movement clarity and "
        "dynamic headroom; do not invent blows, weapons, crowds, victory, chanting, impacts, or continuous maximal intensity."
    ),
    "chinese_martial_arts": (
        "Adapt the supplied idea as an instrumental Chinese martial-arts film score using an intentional, non-tokenistic balance "
        "of Chinese instrumental colors and compatible orchestral or percussive roles, agile phrasing, breath-shaped pauses, and "
        "precise synchronization to movement already present. Do not infer a dynasty, location, folklore, comedy, wire-fu, combat, "
        "gong hits, chanting, or a fixed instrument roster unless the user or scene supports it."
    ),
    "ambient_atmospheric": (
        "Translate the idea into sparse atmospheric instrumental music with slowly evolving timbre, restrained harmonic "
        "motion, spacious register, and low event density. Preserve audible musical structure without becoming room tone, "
        "sound design, drone-only filler, or vocal ambience."
    ),
    "electronic_modern": (
        "Arrange the idea with contemporary instrumental synthesis, programmed rhythm where requested, controlled low end, "
        "clear timbral layers, and deliberate automation. Do not add club conventions, drops, glitches, arpeggios, or aggressive bass unless supported by the user's direction."
    ),
    "synthwave": (
        "Use a restrained retro-synth vocabulary with period-compatible analog-style timbres, gated or electronic percussion "
        "only when rhythmically appropriate, melodic bass, and clear harmonic progression. Do not add vocals, nostalgia effects, "
        "VHS noise, arcade sounds, or force a fast neon-action mood."
    ),
    "rock_instrumental": (
        "Arrange the idea as instrumental rock through a coherent rhythm section, guitar or compatible lead roles, playable "
        "phrasing, section contrast, and controlled amplification. Do not add vocals, crowd sound, virtuoso solos, distortion, "
        "double-kick intensity, or anthem structure unless requested."
    ),
    "jazz": (
        "Adapt the idea through jazz-informed harmony, voicing, articulation, rhythmic placement, ensemble interaction, and "
        "measured improvisational space while retaining the requested tempo and dramatic function. Do not automatically add swing, "
        "saxophone, walking bass, big-band brass, nightclub ambience, or extended solos."
    ),
    "classical_chamber": (
        "Arrange the idea for a small acoustic classical ensemble with transparent counterpoint, playable phrasing, controlled "
        "dynamics, and clearly differentiated instrumental roles. Do not expand into full orchestra, virtuoso concerto writing, "
        "period pastiche, choir, or operatic gesture."
    ),
    "folk_acoustic": (
        "Translate the idea into an intimate acoustic folk arrangement with human-scale pulse, playable phrasing, restrained "
        "ensemble layers, and natural instrumental dynamics. Do not infer a nationality, tradition, rustic setting, vocals, "
        "handclaps, stomps, or celebratory character."
    ),
    "hip_hop_instrumental": (
        "Arrange the idea as an instrumental hip-hop beat using intentional groove, drum programming, bass relationship, sample-like "
        "or played texture, and section variation. Use no rapping, spoken samples, vocal chops, copyrighted sampling, producer tags, "
        "turntable effects, or genre-specific aggression unless explicitly requested."
    ),
    "funk_disco": (
        "Adapt the idea through syncopated instrumental groove, interlocking rhythm-section roles, concise harmonic rhythm, and "
        "controlled bright accents. Do not force four-on-the-floor, slap bass, wah guitar, strings, brass, dancefloor ambience, "
        "camp performance, or vocals unless requested."
    ),
    "horror_tension": (
        "Shape the supplied idea as a restrained instrumental tension underscore using controlled dissonance, register, pulse, "
        "silence, timbral friction, and dynamic restraint tied to events already present. Do not invent danger, jump-scare stingers, "
        "screams, heartbeat, chanting, reversed voices, impacts, or supernatural meaning."
    ),
    "horror_intense": (
        "Build an intense instrumental horror cue from the supplied idea through unstable harmony, abrasive but controlled timbre, "
        "extreme register contrast, ruptured pulse, and sharply bounded dynamic peaks tied only to existing events. Keep speech and "
        "important physical sound intelligible; do not invent gore, monsters, danger, screams, whispers, chanting, jump scares, "
        "heartbeat, reversed voices, or impacts."
    ),
}
REF2VA_TASK_TYPES = (
    "keyframe completion", "reference generation", "video editing", "video continuation",
    "audio reuse", "audio reference",
)
LEGACY_REF2VA_TASK_ALIASES = {
    "generation": "reference generation", "editing": "video editing", "continuation": "video continuation",
}
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
    r"([\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,9}?)\s+"
    r"(?:in|en|from|de|que\s+(?:es|aparece\s+en|corresponde\s+a))\s+"
    r"(image|imagen|picture|foto)\s*(\d+)\b",
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
    r"reply|replies|replied|replying|respond|responds|sing|sings|singing|chant|chants|"
    r"call|calls|exclaim|exclaims|whisper|whispers|whispering|speak|speaks|speaking|"
    r"explain|explains|explaining|narrate|narrates|narrating|describe|describes|describing|comment|comments|commenting|"
    r"dice|dijo|diciendo|responde|contest[ao]|canta|cantando|pregunta|"
    r"preguntando|grita|gritando|susurra|susurrando|habla|hablando|think|thinks|thinking|"
    r"explica|explicando|narra|narrando|describe|describiendo|comenta|comentando|cuenta|contando|"
    r"thought|hear|hears|heard|hearing|piensa|pensando|pensamiento|reflexiona|reflexionando|"
    r"mon[oó]logo|oye|oyen|o[ií]r|escucha|escuchan)\b",
    re.IGNORECASE,
)
_UNTAGGED_SPEECH_ACTION_RE = re.compile(
    r"\b(?:speaks?|speaking|talks?|talking|says?|saying|asks?|asking|repl(?:y|ies|ying)|"
    r"responds?|repeats?|repeating|sing(?:s|ing)?|chants?|exclaims?|booms?|booming|utters?|uttering|"
    r"explains?|explaining|narrates?|narrating|describes?|describing|comments?|commenting|"
    r"continues?\s+(?:to\s+)?(?:speak|talk)|finishes?\s+(?:speaking|talking)|"
    r"delivers?\s+(?:(?:his|her|their|the|required)\s+)?(?:line|dialogue|words?))\b",
    re.IGNORECASE,
)
_EXPLICIT_CUT_RE = re.compile(
    r"\b(?:hard\s+cut|smash\s+cut|match\s+cut|cut\s+scene(?:\s+to)?|cut(?:s|ting)?\s+to|cutaway|insert\s+shot|"
    r"montage|shot\s+\d+|scene\s+\d+|plano\s+\d+|escena\s+\d+|corta\s+a|corte\s+a)\b|"
    r"\d{1,2}:\d{2}(?:\.\d{1,3})?",
    re.IGNORECASE,
)
_CUT_COMMAND_RE = re.compile(
    r"\b(?:(?:hard|smash|match)\s+cut(?:\s+to)?|cut\s+scene(?:\s+to)?|cut(?:s|ting)?\s+to|"
    r"corta\s+a|corte\s+a)\b",
    re.IGNORECASE,
)
_CONTINUOUS_PROGRESSION_RE = re.compile(
    r"\b(?:gradually|progressively|slowly|little\s+by\s+little|poco\s+a\s+poco|"
    r"gradualmente|progresivamente|lentamente|emerge|emerges|emerging|aparece|aparecen|"
    r"apareciendo|materializa|materializan|materializándose|coalesce|coalesces)\b",
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
_DIALOGUE_LANGUAGE_PATTERN = (
    r"english|spanish|french|german|italian|portuguese|japanese|korean|chinese|russian|arabic|"
    r"hindi|dutch|polish|turkish|catalonian|catalan|catalán|català|español|castilian|castellano"
)
_DIALOGUE_AUTHORING_RE = re.compile(
    r"\b(?:generate|write|create|invent|compose|provide|draft|author|make\s+up|come\s+up\s+with|"
    r"genera(?:r)?|escribe|escribir|crea(?:r)?|inventa(?:r)?|comp[oó]n|componer|redacta(?:r)?|"
    r"proporciona(?:r)?|a[nñ]ade|a[nñ]adir|haz)\b"
    r"(?:(?![.!?]).){0,96}\b(?:dialogue|dialog|lines?|spoken\s+words?|speech|script|voice[ -]?over|"
    r"narration|di[aá]logo|l[ií]neas?|frases?|palabras|discurso|gui[oó]n|voz\s+en\s+off|narraci[oó]n)\b",
    re.IGNORECASE,
)
_UNSCRIPTED_SPEECH_RE = re.compile(
    r"\b(?:explains?|narrates?|describes?|comments?|reports?|tells?\s+(?:the\s+viewer|the\s+audience|us)\b|"
    r"talks?\s+(?:about|through)|speaks?\s+about|explica|narra|describe|comenta|relata|cuenta\s+(?:al\s+"
    r"espectador|al\s+p[uú]blico|lo\s+que)|habla\s+(?:de|sobre))\b",
    re.IGNORECASE,
)
_DIALOGUE_PROHIBITION_RE = re.compile(
    r"\b(?:no|without|zero|omit|avoid|never|sin|ning[uú]n|ninguna|omite|evita|nunca)\b"
    r"(?:(?![.!?]).){0,48}\b(?:dialogue|dialog|speech|spoken\s+words?|voice[ -]?over|narration|"
    r"di[aá]logo|habla|voz\s+en\s+off|narraci[oó]n|palabras\s+inteligibles)\b",
    re.IGNORECASE,
)


def _dialogue_authoring_request(source_prompt: str) -> tuple[bool, str]:
    """Return whether the source authorizes new spoken words and their requested language."""
    source = str(source_prompt or "")

    def negated(match: re.Match[str]) -> bool:
        prefix = source[max(0, match.start() - 40):match.start()]
        matched = match.group(0)
        return bool(
            re.search(
                r"(?:\b(?:do\s+not|don't|never|avoid|omit|without|no\s+need\s+to|"
                r"no|nunca|evita|omite|sin|no\s+hace\s+falta)\s*)$",
                prefix,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b(?:generate|write|create|provide|genera(?:r)?|escribe|crea(?:r)?|proporciona(?:r)?)\s+"
                r"(?:absolutely\s+|ning[uú]n\s+|ninguna\s+)?(?:no|zero|ning[uú]n|ninguna|sin)\s+",
                matched,
                flags=re.IGNORECASE,
            )
        )

    def already_scripted(match: re.Match[str]) -> bool:
        following = []
        quote = _QUOTED_RE.search(source, match.end())
        tagged = re.search(r"<d>.*?</d>", source[match.end():], flags=re.DOTALL | re.IGNORECASE)
        if quote:
            following.append(quote.start())
        if tagged:
            following.append(match.end() + tagged.start())
        if not following:
            return False
        return not re.search(r"[.!?;]", source[match.end():min(following)])

    direct = [match for match in _DIALOGUE_AUTHORING_RE.finditer(source) if not negated(match)]
    unscripted = [
        match for match in _UNSCRIPTED_SPEECH_RE.finditer(source)
        if not negated(match) and not already_scripted(match)
    ]
    if not direct and (_DIALOGUE_PROHIBITION_RE.search(source) or not unscripted):
        return False, "Original language"

    language_mentions = []
    language_patterns = (
        rf"\b(?:in|en)\s+(?:(?:the\s+)?(?:language|idioma)\s+)?({_DIALOGUE_LANGUAGE_PATTERN})\b",
        rf"\b({_DIALOGUE_LANGUAGE_PATTERN})\s+(?:language\s+)?(?:dialogue|dialog|lines?|voice[ -]?over|"
        rf"narration|speech|di[aá]logo|l[ií]neas?|voz\s+en\s+off|narraci[oó]n)\b",
    )
    for pattern in language_patterns:
        for match in re.finditer(pattern, source, flags=re.IGNORECASE):
            language_mentions.append((match.start(), match.group(1)))
    if not language_mentions:
        return True, "Original language"
    raw = max(language_mentions, key=lambda item: item[0])[1]
    return True, _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize())


def _source_requests_offscreen_voice(source_prompt: str) -> bool:
    """Recognize positive narration/voiceover/thought cues without treating prohibitions as requests."""
    source = str(source_prompt or "")
    cue = re.compile(
        r"\b(?:voice[ -]?over|narrat(?:e|es|ed|ing|ion)|off-screen\s+(?:voice|narrator)|voz\s+en\s+off|"
        r"narraci[oó]n|voice\s+in\s+off|mon[oó]logo)\b",
        re.IGNORECASE,
    )
    for match in cue.finditer(source):
        clause_start = 0
        for boundary in re.finditer(r"[.!?;]|\b(?:but|however|except|pero|sino)\b", source[:match.start()], re.IGNORECASE):
            clause_start = boundary.end()
        prefix = source[clause_start:match.start()]
        if re.search(
            r"\b(?:no|not|without|never|avoid|omit|exclude|sin|nunca|evita|omite|excluye)\b",
            prefix,
            flags=re.IGNORECASE,
        ):
            continue
        return True
    return False


SYSTEM_PROMPT = """You rewrite basic user requests into production-ready MiniMax H3 audiovisual prompts.

Return only the finished prompt, without Markdown fences, commentary, preamble, or a trailing explanation. Write
all structural prose in English. Preserve the original language only inside dialogue/lyrics and visible on-screen
text. Never translate, paraphrase, censor, soften, or extend quoted dialogue, lyrics, or visible text. Do not invent
new dialogue unless the authoritative user prompt explicitly asks you to write/generate dialogue or gives an
unscripted speech/narration brief such as what a character explains. In that case, write concrete, natural,
speakable lines in the requested language; do not return a dialogue placeholder or merely describe that speech
happens. If the request includes an AUTHORITATIVE DIALOGUE LEDGER, copy every ledger line exactly once and author no
additional words. Keep requested identities, actions, camera behavior, timing, reference roles, and ending intact.

Shared timeline rules:
- Make every added detail concretely visible or audible. Develop the timeline in playback order through style,
  initial composition, subject appearance and position, environment and key props, actions and reactions, observable
  state changes, camera, and synchronized diegetic sound. Preserve concrete spatial relationships and causality.
- At a subject's first clear appearance, establish only source-supported identity, appearance, frame position, and
  current action; later mentions must remain consistent without repeatedly redefining the subject. Allocate detail
  according to each shot's information load rather than padding every shot equally.
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
- For visible audible dialogue, keep the identity, stable speaker ID, explicit vocal action, delivery, and matching
  <d> block in one sentence. Natural official forms include says, replies, asks, shouts, whispers, sings, and group
  speech with compound IDs such as (S1,S2). Explains and narrates are also valid when they name the requested
  informational delivery. Put only language plus exact words inside <d>; keep all action and
  delivery outside it. Do not use vague "speaks" or "delivers the line" cues that imply unspecified extra words.
- Name every off-screen vocal source explicitly. If the referenced character owns the voiceover, write
  "<Subject N> (Sx) says in an off-screen voiceover" and reuse that same Sx for the character's later visible
  dialogue. Otherwise write "An off-screen narrator (Sx)". Never use an unresolved phrase such as "the voice in off".
- Every positive speaking/talking/saying/asking/booming/finishing-speech cue must be in the same sentence as its corresponding
  <d> block. Outside those tagged sentences, describe gaze, gesture, expression, and silence without implying continued
  or additional speech. A source-provided short quoted line is spoken once in its assigned shot. When dialogue
  authoring was explicitly requested, distribute distinct concrete lines among the corresponding timeline beats;
  do not collapse them all into the opening/final shot, repeat a line as filler, or insert a no-more-speech closure
  before a later authored line.
- The explicit audio policies in the user request override the shared audible-dialogue and sound defaults. Silent
  mouth acting and voice-off modes must omit <d>, speaker IDs, lexical dialogue, narration, and voiceover entirely.
- Put visible text in straight English double quotes exactly as supplied.
- Positional source references are immutable bindings: image/imagen/picture N always means <Picture N>, video N
  means <Video N>, and audio N means <Audio N>. They name user-provided assets, never generated shots or moments.
  Preserve the referenced person's identity or object's exact visible design wherever it appears. Never invent a
  Picture, Video, or Audio label that the request/reference context did not provide. Do not reveal an object before
  the action or spoken cue where the user explicitly says it first becomes visible.
- A generated character or object that is not explicitly bound to a supplied asset remains ordinary descriptive
  content. Never assign it a new <Subject N>, <Picture N>, <Video N>, or <Audio N> label merely because it appears in
  the story.
- Preserve every referenced object's concrete noun, subtype, visible attributes, materials, markings, proportions,
  and identity. Do not silently replace a supplied object with a generic or semantically related alternative.
- When the source explicitly requires someone or something to fly, be propelled, or move off-screen/out of frame,
  stage the complete consequence as visible motion in a sufficiently wide shot. Name the moving subject, show a
  readable airborne or displaced trajectory, and keep the camera on that action until the subject fully exits the
  frame. Do not replace the requested movement with a cut, disappearance, implied aftermath, close-up, or mere fall.
- overall_soundscape is one continuous paragraph of 1-4 sentences covering ambience, physical sounds, and
  non-verbal human sounds. Do not repeat dialogue or audience-only music there.
- non_diegetic_music is 1-3 sentences describing only audience-only music through instrumentation, tempo, rhythm,
  and dynamics. Use N/A when none is requested.

Base-mode output has exactly these three sections in order:
integrated_multimodal_description, overall_soundscape, non_diegetic_music.
Each section name must be followed by a literal colon, for example integrated_multimodal_description:.
T2VA begins directly with the sections. I2VA begins with the exact first-frame alignment sentence supplied in the
request, establishes the referenced style, subjects, composition, and scene anchors, then follows first-frame anchor
to action onset, continuous development, and visible result or reaction. FL2VA begins with the exact first/last
alignment sentence supplied in the request and normally uses one continuous shot that moves through observable
intermediate changes, progressively narrows the differences, and visibly reaches the last-frame anchor. L2VA begins
with the exact last-frame alignment sentence supplied in the request and moves from a plausible preceding state
through an explicit transition path to gradual convergence and a visible final-frame landing.

Ref2VA output has exactly these six sections in order:
subject_definitions, summary, retention_analysis, detailed_description, overall_soundscape, non_diegetic_music.
Use stable <Subject N>, <Picture N>, <Video N>, and <Audio N> meanings. Subject labels describe reusable visible
content; Picture labels are concrete frame/composition anchors; Video labels describe whole-video edit, continuation,
or temporal structure; Audio labels describe copied or referenced signals. The summary starts with bracketed task
types chosen from keyframe completion, reference generation, video editing, video continuation, audio reuse, and
audio reference. Join multiple task types with the exact separator " + ". retention_analysis uses only the documented visual markers fully_preserved, partially_preserved,
attribute_transfer, weak_reference and audio markers fully_copy, partially_copy, reference, weak_reference.
When verbal content belongs only to a copied soundtrack or BGM, attribute its <d> block to <Audio N> without
inventing a speaker ID. A concrete person, narrator, or independent vocal source uses a stable (Sx); an Audio
reference bound to that speaker reuses the same ID. Timbre-, rhythm-, or delivery-only references never import words.
Use [unclear] for an explicitly unintelligible transcribed span rather than guessing it.
For generation tasks, make detailed_description explicit and normally 350-500 English words. Establish style in one
or two sentences before Shot 1, then describe composition, appearance, environment, lighting, actions, state changes,
camera, sound, and where each reference takes effect in playback order.
"""


MULTISHOT_SYSTEM_PROMPT = """You turn a user request into a chain of autonomous MiniMax H3 audiovisual prompts.

Return only valid JSON in this exact shape: {"prompts":["shot prompt 1","shot prompt 2"]}. Do not use Markdown,
comments, section headers, [Shot N] markers, or timestamps inside a segment. Each array item is sent through a
separate H3 conditioning pass, so write it as fluent standalone English prose and never rely on words such as
"same", "as before", or "continues" without restating the concrete information they replace.

Repeat the stable identity, wardrobe, environment, visual style, and voice description verbatim in every segment
where they remain applicable. Prefer six to eight concrete identity attributes when the source provides enough
facts, but never invent attributes merely to reach a count. Preserve exact source-provided dialogue only when the
explicit voice policy permits audible speech; always preserve exact visible text. Author new spoken words only when
the voice policy is audible and the user explicitly requests dialogue writing or supplies an unscripted
speech/narration brief; then write concrete natural lines in the requested language and place each line in its
corresponding segment. An AUTHORITATIVE DIALOGUE LEDGER fixes the exact new words: copy every ledger line once and
author no others. Allocate spoken material to the requested segment only; do not duplicate it. End each segment in a concrete visible state
that can serve as the chained first frame of the next segment, and begin the next segment compatibly with that state.
    Apply ambience, physical sound, score, and voice only as permitted by the explicit user policies. Do not use the base three-section or Ref2VA
six-section formats: those contracts describe a single generation, while this output drives independent passes.
"""


def system_prompt_for_mode(mode: str) -> str:
    """Return only the output-contract rules relevant to the resolved H3 mode."""
    if mode == "chained_multishot":
        return MULTISHOT_SYSTEM_PROMPT
    base_marker = "\nBase-mode output has exactly these three sections in order:"
    ref_marker = "\nRef2VA output has exactly these six sections in order:"
    common, mode_rules = SYSTEM_PROMPT.split(base_marker, 1)
    base_rules, ref_rules = mode_rules.split(ref_marker, 1)
    if mode == "ref2va":
        return common + ref_marker + ref_rules
    return common + base_marker + base_rules


def resolve_mode(mode: str, reference_context: str = "", basic_prompt: str = "",
                 media_manifest: str = "") -> str:
    mode = str(mode).strip().lower()
    if mode not in TASK_MODES:
        raise ValueError(f"Unsupported MiniMax H3 prompt mode {mode!r}")
    if mode != "auto":
        return mode
    parsed = parse_media_manifest(media_manifest)
    manifest_mode = parsed.get("mode", "")
    if manifest_mode in TASK_MODES and manifest_mode != "auto":
        return manifest_mode
    counts = parsed.get("counts", {})
    if parsed.get("items"):
        pictures = int(counts.get("picture", 0))
        videos = int(counts.get("video", 0))
        audios = int(counts.get("audio", 0))
        roles = set()
        for item in parsed["items"]:
            raw_roles = item.get("role", item.get("roles", item.get("purpose", "")))
            roles.update(str(role).lower() for role in (raw_roles if isinstance(raw_roles, list) else [raw_roles]))
        if pictures == 1 and not videos and not audios and roles and roles <= {"first_frame", "first frame"}:
            return "i2va"
        if pictures == 1 and not videos and not audios and roles <= {"last_frame", "last frame", "final_frame", "final frame"}:
            return "l2va"
        if (pictures == 2 and not videos and not audios
                and bool(roles & {"first_frame", "first frame"})
                and bool(roles & {"last_frame", "last frame", "final_frame", "final frame"})
                and all(role in {"first_frame", "first frame", "last_frame", "last frame", "final_frame", "final frame"}
                        for role in roles)):
            return "fl2va"
        return "ref2va"
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
        r"(?im)^\s*(<(?:Subject|Picture|Video|Audio)\s+\d+>)\s*(?::|\bis\b|\bcomes?\s+from\b|\bfrom\b)",
        text or "",
    )))


def _official_reference_model(source_prompt: str, reference_context: str = "") -> dict[str, Any]:
    """Build high-confidence Ref2VA semantics without equating asset and Subject ordinals."""
    source = source_prompt or ""
    combined_context = source + "\n" + (reference_context or "")
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
        # When a sentence begins with another actor ("the woman tells the person in image 2"), bind the
        # reference to the nearest noun phrase rather than the sentence-leading subject.
        nested_determiners = list(re.finditer(r"\b(?:the|a|an|el|la|los|las|un|una)\s+", role, re.IGNORECASE))
        if nested_determiners:
            role = role[nested_determiners[-1].end():].strip()
        role = re.sub(
            r"^.*\b(?:appear|appears|appearing|emerge|emerges|show|shows|reveal|reveals|"
            r"aparece|aparecen|apareciendo|emerge|emergen|vemos|son)\s+",
            "",
            role,
            flags=re.IGNORECASE,
        ).strip()
        pieces = re.split(r"\s+(?:and|y)\s+", role, flags=re.IGNORECASE)
        for piece in pieces:
            if piece.strip():
                picture_roles.append((piece.strip(), _asset_label(kind, number)))
    for asset, role, analysis in re.findall(
        r"Connected asset\s+(<Picture\s+\d+>)\s+has role:\s*([^;\r\n]+)(?:;\s*analysis:\s*([^\r\n]+))?",
        reference_context or "", flags=re.IGNORECASE,
    ):
        role_text = role.strip()
        if analysis.strip() and re.search(r"\b(?:identity|subject|character|person|object|prop|style)\b", role_text, re.IGNORECASE):
            role_text = f"{role_text} {analysis.strip()}"
        picture_roles.append((role_text, asset))

    picture_assets = [label for label in assets if label.lower().startswith("<picture")]
    video_assets = [label for label in assets if label.lower().startswith("<video")]
    audio_assets = [label for label in assets if label.lower().startswith("<audio")]
    def role_family(role: str) -> str:
        lowered = role.casefold()
        if re.search(r"\b(?:style|look|aesthetic|palette|lighting|estilo)\b", lowered):
            return "style"
        if re.search(
            r"\b(?:person|persona|people|man|men|woman|women|boy|girl|hombre|hombres|mujer|"
            r"actor|actress|presenter|driver|identity|face|body|character|version|versi[oó]n)\b",
            lowered,
        ):
            return "identity"
        return "design"

    generic_role_words = {
        "the", "a", "an", "el", "la", "los", "las", "un", "una", "person", "persona",
        "people", "man", "men", "hombre", "hombres", "character", "version", "versión",
    }

    def role_specificity(role: str) -> tuple[int, int]:
        words = [item.casefold() for item in re.findall(r"[\wÀ-ÿ'-]+", role)]
        return (sum(item not in generic_role_words for item in words), len(words))

    # Repeated aliases for the same human/style/object in one asset are one reusable Subject.  Keep the most
    # specific source phrase (for example "version ejercito nazi" rather than the generic "hombres").
    grouped_roles: dict[tuple[str, str], str] = {}
    group_order: list[tuple[str, str]] = []
    for role, asset in picture_roles:
        key = (asset.casefold(), role_family(role))
        if key not in grouped_roles:
            grouped_roles[key] = role
            group_order.append(key)
        elif role_specificity(role) > role_specificity(grouped_roles[key]):
            grouped_roles[key] = role

    subjects = []
    used_assets = set()
    primary_identity_label = None
    for key in group_order:
        role = grouped_roles[key]
        asset = next(item for item in picture_assets if item.casefold() == key[0])
        contribution = key[1]
        if contribution == "style":
            description = (
                f"the reusable visual style abstracted from {asset}, including its palette, rendering treatment, "
                "lighting language, and characteristic surface treatment"
            )
            marker = "attribute_transfer"
        elif contribution == "identity":
            informative = role_specificity(role)[0] > 0
            if primary_identity_label is not None and re.search(r"\b(?:version|versi[oó]n)\b", role, re.IGNORECASE):
                description = (
                    f"an alternate version of {primary_identity_label}, identified by the source as {role!r}, whose "
                    f"identity and intrinsic physical appearance come from {asset}; wardrobe, styling, pose, and "
                    "state follow explicit source instructions whenever they override the reference"
                )
            else:
                canonical_role = {
                    "persona": "person", "personas": "people", "hombre": "person", "hombres": "people",
                    "mujer": "woman", "mujeres": "women",
                }.get(role.casefold(), role)
                if not informative and canonical_role.casefold() in {"person", "people", "man", "men"}:
                    canonical_role = "person"
                description = (
                    f"the reusable {canonical_role} whose identity and intrinsic physical appearance come from "
                    f"{asset}; wardrobe, styling, pose, and state follow explicit source instructions whenever they "
                    "override the reference"
                )
            marker = "fully_preserved"
        else:
            description = (
                f"the reusable {role} whose exact visible design, proportions, materials, colors, and markings "
                f"come from {asset}"
            )
            marker = "fully_preserved"
        subjects.append({"role": role, "asset": asset, "contribution": contribution,
                         "description": description, "marker": marker})
        if contribution == "identity" and primary_identity_label is None:
            # Labels are assigned in this same stable order below.
            primary_identity_label = f"<Subject {len(subjects)}>"
        used_assets.add(asset)

    independent = {}
    for asset in picture_assets:
        number = re.search(r"\d+", asset).group()
        token = rf"(?:image|imagen|picture|foto)\s*(?:number\s*|n[uú]mero\s*|#\s*)?{number}"
        anchor = re.search(
            rf"(?:{token}.{{0,60}}(?:exact\s+)?(?:first|last|final|key)\s*frame|"
            rf"(?:exact\s+)?(?:first|last|final|key)\s*frame.{{0,60}}{token}|"
            rf"{token}.{{0,60}}(?:storyboard|composition anchor)|"
            rf"{re.escape(asset)}.{{0,80}}(?:first_frame|last_frame|first frame|last frame|keyframe|storyboard|composition))",
            combined_context,
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
            combined_context,
            flags=re.IGNORECASE,
        )
        global_role = re.search(
            rf"(?:continue|continuation|edit|editing|structure|timing|ritmo|continuar).{{0,40}}{token}|"
            rf"{token}.{{0,40}}(?:continue|continuation|edit|editing|structure|timing|ritmo|continuar)",
            combined_context,
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
        exact_copy = bool(re.search(
            r"\b(?:copy|copied|reuse|reused|reutiliza|copiar|paired)\b", combined_context, re.IGNORECASE,
        ))
        independent[asset] = {
            "description": (
                f"the supplied audio signal {'copied as a synchronized audio layer' if exact_copy else 'used as an audio reference for voice, delivery, rhythm, or sound texture'}"
            ),
            "marker": "partially_copy" if exact_copy else "reference",
        }
        used_assets.add(asset)

    # A connected image without an authoritative role is not automatically a
    # person/object Subject. Guessing here can silently bind an unrelated image
    # to a source character. Keep it available but unassigned until the source,
    # reference notes, or media manifest states the relationship.
    unassigned_assets = {asset for asset in picture_assets if asset not in used_assets}

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
        "provenance_assets": {subject["asset"] for subject in subjects},
        "independent_assets": set(independent),
        "unassigned_assets": unassigned_assets,
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
    for asset in sorted(model.get("unassigned_assets", ())):
        lines.append(
            f"- UNASSIGNED ASSET: {asset} has no authoritative role. Do not invent a Subject or bind it to a "
            "character/object unless the source or reference context supplies that relationship."
        )
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


def normalize_ref_task_prefix(text: str) -> str:
    """Migrate legacy Ref2VA task names and separators to the current official form."""
    value = str(text)
    match = re.search(r"(?ms)(^summary:\s*)\[([^\]\r\n]+)\]", value)
    if not match:
        return value
    pieces = re.split(r"\s*(?:\+|/)\s*", match.group(2).strip())
    normalized = [LEGACY_REF2VA_TASK_ALIASES.get(piece.casefold(), piece.casefold()) for piece in pieces]
    if any(piece not in REF2VA_TASK_TYPES for piece in normalized):
        return value
    prefix = " + ".join(dict.fromkeys(normalized))
    return value[:match.start()] + match.group(1) + f"[{prefix}]" + value[match.end():]


def normalize_reference_definitions(text: str, source_prompt: str, reference_context: str = "") -> str:
    """Apply official Ref2VA definitions without overwriting explicit user mappings."""
    text = normalize_ref_task_prefix(text)
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
    task_types = []
    if "video" in kinds and re.search(r"\b(?:continue|continuation|continuar|extend|resume)\b", source_prompt, re.IGNORECASE):
        task_types.append("video continuation")
    elif "video" in kinds and re.search(r"\b(?:edit|editing|replace|modify|editar|reemplazar)\b", source_prompt, re.IGNORECASE):
        task_types.append("video editing")
    if any(item["kind"] == "picture" for item in model["definitions"]):
        task_types.append("keyframe completion")
    if any(item["kind"] in {"subject", "picture", "video"} for item in model["definitions"]):
        task_types.append("reference generation")
    audio_items = [item for item in model["definitions"] if item["kind"] == "audio"]
    if audio_items:
        task_types.append("audio reuse" if any(
            item["marker"] in {"fully_copy", "partially_copy"} for item in audio_items
        ) else "audio reference")
    task_type = " + ".join(dict.fromkeys(task_types or ["reference generation"]))
    # The canonical task prefix is the whole summary. A free-form tail often
    # repeats stale task names (or unsupported markers) from the raw LLM output.
    value = _replace_section_body(value, "summary", f"[{task_type}]")
    return value


def _ordinary_generated_character_descriptors(source_prompt: str) -> list[str]:
    """Extract strongly specified people that are not introduced as media references."""
    source = source_prompt or ""
    descriptors: list[str] = []
    pattern = re.compile(
        r"\b(?:a|an|the)\s+((?:little\s+)?\d{1,3}\s*[- ]?\s*years?\s*[- ]?\s*old\s+"
        r"(?:girl|boy|child|woman|man|person)"
        r"(?:\s+with\s+[^,.;]+?)?(?:\s+in\s+(?:a\s+)?(?:wheelchair|walker))?)"
        r"(?=\s*(?:,|\.|;|\bwhile\b|\bwhen\b|\bwho\b|$))",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(source):
        if _ASSET_REFERENCE_RE.search(match.group(0)):
            continue
        descriptor = re.sub(r"\s+", " ", match.group(1)).strip()
        descriptors.append("the " + descriptor)
    return list(dict.fromkeys(descriptors))


def normalize_unassigned_subjects(text: str, source_prompt: str, reference_context: str = "") -> str:
    """Replace invented Subject labels with literal generated-character descriptions."""
    value = str(text)
    model = _official_reference_model(source_prompt, reference_context)
    allowed_subjects = {
        item["label"].casefold() for item in model["definitions"] if item["kind"] == "subject"
    }
    observed = list(dict.fromkeys(_REFERENCE_RE.findall(value)))
    orphan_subjects = [
        label for label in observed
        if label.casefold().startswith("<subject ") and label.casefold() not in allowed_subjects
    ]
    descriptors = _ordinary_generated_character_descriptors(source_prompt)
    for label, descriptor in zip(orphan_subjects, descriptors):
        value = re.sub(re.escape(label), descriptor, value, flags=re.IGNORECASE)
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


def _requires_single_continuous_progression(source_prompt: str) -> bool:
    """Keep one gradually developing place/time/action as one shot unless the user explicitly requested an edit."""
    source = source_prompt or ""
    return bool(_CONTINUOUS_PROGRESSION_RE.search(source) and not _EXPLICIT_CUT_RE.search(source))


def _implicit_shot_limit(source_prompt: str) -> int | None:
    """Limit LLM-authored cuts when the source itself supplied no editorial structure."""
    source = source_prompt or ""
    if _EXPLICIT_CUT_RE.search(source):
        return None
    if _requires_single_continuous_progression(source):
        return 1
    return 2


def _required_explicit_shot_count(source_prompt: str) -> int | None:
    """Translate literal cut commands/numbered shots into a minimum authored shot plan."""
    source = source_prompt or ""
    cut_count = len(_CUT_COMMAND_RE.findall(source))
    numbered = [
        int(number)
        for number in re.findall(r"\b(?:shot|scene|plano|escena)\s+(\d+)\b", source, re.IGNORECASE)
    ]
    required = max([cut_count + 1 if cut_count else 0, *numbered], default=0)
    return required or None


def _explicit_shot_segments(source_prompt: str) -> list[str]:
    """Return authoritative source spans separated by literal cut commands."""
    source = source_prompt or ""
    if not _CUT_COMMAND_RE.search(source):
        return []
    segments = []
    for part in _CUT_COMMAND_RE.split(source):
        cleaned = re.sub(r"\bthen\s*$", "", part.strip(), flags=re.IGNORECASE).strip(" ,;:-")
        if cleaned:
            segments.append(cleaned)
    return segments


def _source_dialogue_shot_indices(source_prompt: str) -> list[int]:
    """Map each quoted spoken occurrence to its user-authored explicit shot."""
    source = source_prompt or ""
    indices = []
    for match in _QUOTED_RE.finditer(source):
        cue_window = source[max(0, match.start() - 180):match.start()]
        if _SPEECH_CUE_RE.search(cue_window):
            indices.append(1 + len(list(_CUT_COMMAND_RE.finditer(source, 0, match.start()))))
    return indices


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


def _explicit_age_fact_errors(source_prompt: str, output: str) -> list[str]:
    """Protect explicit coarse age categories that small LLMs commonly soften or shift."""
    source = source_prompt or ""
    text = output or ""
    requirements = (
        (
            r"\b(?:older|elderly|senior|aged)\s+woman\b|\bmujer\s+mayor\b|\banciana\b",
            r"\b(?:older|elderly|senior|aged)\s+woman\b",
            r"\b(?:young|middle-aged)\s+woman\b",
            "older woman",
        ),
        (
            r"\b(?:older|elderly|senior|aged)\s+man\b|\bhombre\s+mayor\b|\banciano\b",
            r"\b(?:older|elderly|senior|aged)\s+man\b",
            r"\b(?:young|middle-aged)\s+man\b",
            "older man",
        ),
        (
            r"\bmiddle-aged\s+woman\b|\bmujer\s+de\s+mediana\s+edad\b",
            r"\bmiddle-aged\s+woman\b",
            r"\b(?:young|older|elderly|senior|aged)\s+woman\b",
            "middle-aged woman",
        ),
        (
            r"\bmiddle-aged\s+man\b|\bhombre\s+de\s+mediana\s+edad\b",
            r"\bmiddle-aged\s+man\b",
            r"\b(?:young|older|elderly|senior|aged)\s+man\b",
            "middle-aged man",
        ),
    )
    errors = []
    for source_pattern, required_pattern, forbidden_pattern, label in requirements:
        if not re.search(source_pattern, source, re.IGNORECASE):
            continue
        if not re.search(required_pattern, text, re.IGNORECASE) or re.search(forbidden_pattern, text, re.IGNORECASE):
            errors.append(f"Explicit source age category must remain {label!r}")
    return errors


def _explicit_source_fact_errors(source_prompt: str, output: str) -> list[str]:
    """Protect concrete source attributes and terminal consequences from silent omission."""
    source = source_prompt or ""
    text = output or ""
    errors = _explicit_age_fact_errors(source, text)

    for age in re.findall(r"\b(\d{1,3})\s*[- ]?\s*years?\s*[- ]?\s*old\b", source, re.IGNORECASE):
        if not re.search(rf"\b{re.escape(age)}\s*[- ]?\s*years?\s*[- ]?\s*old\b", text, re.IGNORECASE):
            errors.append(f"Explicit numeric age must remain {age}-year-old")

    hair_facts = re.findall(
        r"\b(golden|blond(?:e)?|black|brown|red|white|gr[ae]y|silver)\s+"
        r"((?:(?:long|short|curly|straight|wavy)\s+)?(?:hair|locks|curls|braids))\b",
        source,
        flags=re.IGNORECASE,
    )
    for color, hair in hair_facts:
        hair_noun = re.search(r"(?:hair|locks|curls|braids)$", hair, re.IGNORECASE).group(0)
        if not re.search(
            rf"\b{re.escape(color)}\b.{{0,30}}\b(?:{re.escape(hair_noun)}|hair|locks|curls|braids)\b",
            text,
            flags=re.IGNORECASE,
        ):
            errors.append(f"Explicit hair attribute must remain {color} {hair}")

    for aid in ("wheelchair", "crutches", "walker", "cane"):
        if re.search(rf"\b{aid}\b", source, re.IGNORECASE) and not re.search(rf"\b{aid}\b", text, re.IGNORECASE):
            errors.append(f"Explicit mobility aid must remain {aid!r}")

    source_has_forced_exit = re.search(
        r"\b(?:fly|flies|flying|goes?\s+flying|is\s+sent|propelled|hurled|flung|knocked|thrown)\b"
        r".{0,140}\b(?:off[- ]?screen|out\s+of\s+(?:the\s+)?frame)\b",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    output_has_forced_exit = re.search(
        r"\b(?:fly|flies|flying|goes?\s+flying|is\s+sent|propelled|hurled|flung|knocked|thrown)\b"
        r".{0,140}\b(?:off[- ]?screen|out\s+of\s+(?:the\s+)?frame)\b",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if source_has_forced_exit and not output_has_forced_exit:
        errors.append("Explicit terminal consequence must preserve the forced movement out of frame")
    return errors


def _source_fidelity_contract(source_prompt: str) -> str:
    """Expose easily dropped immutable facts to the writer before prose expansion."""
    source = source_prompt or ""
    facts: list[str] = []
    for match in re.finditer(r"\b\d{1,3}\s*[- ]?\s*years?\s*[- ]?\s*old\b", source, re.IGNORECASE):
        facts.append(f"Preserve the exact numeric age: {match.group(0)!r}.")
    for match in re.finditer(
        r"\b(?:golden|blond(?:e)?|black|brown|red|white|gr[ae]y|silver)\s+"
        r"(?:(?:long|short|curly|straight|wavy)\s+)?(?:hair|locks|curls|braids)\b",
        source,
        flags=re.IGNORECASE,
    ):
        facts.append(f"Preserve the exact hair attribute: {match.group(0)!r}.")
    for aid in ("wheelchair", "crutches", "walker", "cane"):
        if re.search(rf"\b{aid}\b", source, re.IGNORECASE):
            facts.append(f"Preserve the explicit mobility aid: {aid!r}.")
    for sentence in re.split(r"(?<=[.!?])\s+", source):
        if re.search(
            r"\b(?:off[- ]?screen|out\s+of\s+(?:the\s+)?frame)\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            facts.append(
                "Preserve this terminal consequence in visible action: "
                f"{sentence.strip()!r} Keep the named subject and its trajectory readable in a wide enough shot, "
                "and do not cut away or move to a close-up until the subject has fully exited the frame."
            )
    if not facts:
        return ""
    return "MANDATORY LOSSLESS SOURCE FACTS (all must appear in the visual timeline):\n- " + "\n- ".join(
        dict.fromkeys(facts)
    )


def build_user_request(basic_prompt: str, mode: str, duration_seconds: float,
                       reference_context: str = "", enhance_description: bool = True,
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
                       authored_dialogue_ledger: tuple[tuple[str, str], ...] = (),
                       creative_treatment_json: str = "",
                       shot_plan_json: str = "",
                       cinematography_json: str = "",
                       instrumental_style: str = "none") -> str:
    if ambience_foley_policy not in AMBIENCE_FOLEY_POLICIES:
        raise ValueError(f"Unsupported ambience/foley policy {ambience_foley_policy!r}")
    if background_score_policy not in BACKGROUND_SCORE_POLICIES:
        raise ValueError(f"Unsupported background-score policy {background_score_policy!r}")
    if voice_performance not in VOICE_PERFORMANCES:
        raise ValueError(f"Unsupported voice performance {voice_performance!r}")
    if instrumental_style not in INSTRUMENTAL_STYLE_CHOICES:
        raise ValueError(f"Unsupported instrumental style {instrumental_style!r}")
    if aspect_ratio not in ASPECT_RATIOS:
        raise ValueError(f"Unsupported aspect ratio {aspect_ratio!r}")
    resolved = resolve_mode(mode, reference_context, basic_prompt, media_manifest)
    dialogue_authoring, dialogue_authoring_language = _dialogue_authoring_request(basic_prompt)
    profile = generation_profile(duration_seconds, aspect_ratio, frame_count)
    effective_duration = profile["effectiveDurationSeconds"]
    creative_treatment = parse_creative_treatment(
        creative_treatment_json, enabled=bool(enhance_description),
    )
    cinematography = parse_cinematography(cinematography_json)
    explicit_shot_plan = parse_shot_plan(
        shot_plan_json, effective_duration, 0, resolved,
    )
    if explicit_shot_plan["provided"] and int(multishot_shot_count or 0):
        if resolved == "chained_multishot" and int(multishot_shot_count) != explicit_shot_plan["shotCount"]:
            raise ValueError(
                "multishot_shot_count conflicts with the explicit shot_plan_json shot count "
                f"({int(multishot_shot_count)} versus {explicit_shot_plan['shotCount']})"
            )
    source_explicit_count = _required_explicit_shot_count(basic_prompt)
    if (explicit_shot_plan["provided"] and source_explicit_count
            and source_explicit_count != explicit_shot_plan["shotCount"]):
        raise ValueError(
            "shot_plan_json conflicts with explicit cut commands in basic_prompt "
            f"({explicit_shot_plan['shotCount']} planned versus {source_explicit_count} required)"
        )
    alignment = alignment_instruction(resolved, effective_duration)
    parts = [
        f"TASK MODE: {resolved.upper()}",
        f"TARGET DURATION: {effective_duration:.3f} seconds",
        f"TARGET FRAME COUNT: {int(frame_count)}" if int(frame_count or 0) else "TARGET FRAME COUNT: automatic",
        f"TARGET ASPECT RATIO: {aspect_ratio}",
        "BASIC USER PROMPT (authoritative; preserve its intent and exact quoted content):\n" + basic_prompt.strip(),
    ]
    if aspect_ratio != "auto":
        parts.append(
            f"AUTHORITATIVE COMPOSITION FRAME — {aspect_ratio}: Compose every shot or autonomous segment for this "
            "target frame. Keep required subjects, interactions, contact points, movement paths, and visible text "
            "readable inside the frame; choose shot scale, placement, and negative space that use this geometry. "
            "Do not invent letterboxing, cropping, a second canvas, or story changes to fill the aspect ratio."
        )
    fidelity_contract = _source_fidelity_contract(basic_prompt)
    if fidelity_contract:
        parts.append(fidelity_contract)
    parsed_manifest = parse_media_manifest(media_manifest)
    connected_context = manifest_context(media_manifest)
    if connected_context:
        parts.append(connected_context)
    if parsed_manifest["errors"]:
        parts.append("MEDIA MANIFEST ERRORS (do not conceal or work around these):\n- " + "\n- ".join(parsed_manifest["errors"]))
    if dialogue_authoring and voice_performance == "audible":
        if authored_dialogue_ledger:
            parts.append(
                "AUTHORITATIVE DIALOGUE LEDGER — AUDIBLE: A dedicated planning pass already wrote the new dialogue. "
                "Copy every block below exactly once into the audiovisual timeline, including its language and "
                "punctuation. Give each vocal source a stable (Sx), an explicit vocal action, and natural delivery in "
                "the same sentence. Place the blocks at their corresponding scenario beats; they may occur in early, "
                "middle, or final shots. Do not translate, paraphrase, omit, duplicate, merge, extend, or add any "
                "other spoken words. Do not insert a no-more-speech closure before a later ledger block. Exact "
                "source-provided quotations remain separate immutable anchors.\n"
                + "\n".join(f"- <d>[{language}] {text}</d>" for language, text in authored_dialogue_ledger)
            )
        else:
            parts.append(
                "DIALOGUE AUTHORING REQUEST — AUDIBLE (explicit user authorization): The user asked you to write the "
                "spoken content rather than merely describe a speaking performance. Create concise, concrete, natural "
                f"lines based only on the supplied scenario. Use <d>[{dialogue_authoring_language}] concrete authored "
                "words</d> for every new line, replacing 'concrete authored words' with the actual speakable text. Give "
                "each vocal source a stable (Sx), an explicit vocal action, and natural delivery in the same sentence. "
                "Place dialogue beats in the shots where the corresponding speech occurs and keep their causal order; "
                "a line may occur in an early, middle, or final shot. Do not use placeholders, summarize what the person "
                "would say, repeat lines as filler, move every line to the first/final shot, or add a closure that forbids "
                "later requested speech. Exact source-provided quotations remain immutable and do not consume this "
                "authorization to write the additionally requested lines."
            )
    elif dialogue_authoring:
        parts.append(
            "DIALOGUE AUTHORING REQUEST — SUPPRESSED BY VOICE POLICY: The source asks for authored spoken content, "
            "but the selected voice policy overrides it. Emit no lexical dialogue, <d> blocks, speaker IDs, "
            "narration, voiceover, or intelligible vocal sound."
        )
    treatment_contract = creative_treatment_instruction(creative_treatment)
    if treatment_contract:
        parts.append(
            treatment_contract
            + "\nSELECTED AUDIO CONTROLS (authoritative over every treatment sound suggestion): "
            f"ambience_foley_policy={ambience_foley_policy}; "
            f"background_score_policy={background_score_policy}; "
            f"voice_performance={voice_performance}."
        )
    cinematography_contract = cinematography_instruction(cinematography)
    if cinematography_contract:
        parts.append(cinematography_contract)
    explicit_plan_contract = shot_plan_instruction(explicit_shot_plan, resolved)
    if explicit_plan_contract:
        parts.append(explicit_plan_contract)
    if reference_context.strip():
        parts.append("REFERENCE CONTEXT (authoritative labels and roles):\n" + reference_context.strip())
    positional_contract = _official_reference_contract(basic_prompt, reference_context)
    if positional_contract:
        parts.append(positional_contract)

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
            "source does not request it, generate no audience-only music: use non_diegetic_music: N/A in structured "
            "single-generation output and omit score from autonomous chained prose. Never invent a score."
        ),
        "add_instrumental": (
            "NON-DIEGETIC MUSIC POLICY — REQUIRED: Create an audience-only instrumental score appropriate to the "
            "scene and describe instrumentation, tempo, rhythm, and dynamics. Add no vocals or lyrics."
        ),
        "off": (
            "NON-DIEGETIC MUSIC POLICY — OFF: No audience-only background music, score, or instrumental underscore "
            "is audible anywhere in the output. Use non_diegetic_music: N/A in structured single-generation output."
        ),
    }
    parts.extend((ambience_contracts[ambience_foley_policy], score_contracts[background_score_policy]))
    requested_instrumental = str(instrumental_description or "").strip()
    if background_score_policy == "add_instrumental" and instrumental_style != "none":
        parts.append(
            "INSTRUMENTAL MUSIC GENRE / STYLE — AUTHORITATIVE ARRANGEMENT GRAMMAR: Adapt the user's score "
            "description and the scene's dramatic function into the selected musical language. Preserve explicit tempo, "
            "meter, rhythmic events, dynamics, structural timing, entry/exit points, and requested instruments wherever "
            "compatible; re-orchestrate only what is necessary to make the selection coherent. Express the result as "
            "concrete audible musical parameters, not as a genre label. The score remains audience-only and strictly "
            "instrumental, with no singing, lyrics, speech, chants, choir, or vocal samples.\n"
            f"Selected style: {instrumental_style}.\n"
            + INSTRUMENTAL_STYLE_CONTRACTS[instrumental_style]
            + "\nOUTPUT INTEGRATION — MANDATORY: In structured single-generation output, write the resolved "
            "instrumentation, tempo, rhythm, harmony, texture, structure, and dynamics as concrete audible prose in "
            "non_diegetic_music. Do not output only the genre name, style ID, preset label, or a statement that the "
            "style is applied. Where an autonomous chained item carries score direction, restate the same resolved "
            "musical signature compactly so it does not depend on hidden selector metadata."
        )
    if background_score_policy == "add_instrumental" and requested_instrumental:
        parts.append(
            "USER-SPECIFIED INSTRUMENTAL SCORE (authoritative): Use the following musical direction for the "
            "audience-only score and adapt its arrangement to the selected instrumental style when one is active. "
            "Preserve concrete instrumentation, tempo, rhythm, and dynamics wherever compatible. Translate any "
            "abstract mood wording into those audible musical parameters instead of repeating the mood label. "
            "Resolve only genuine omissions needed for coherence. It remains strictly instrumental, with no "
            "singing, lyrics, or vocal samples:\n" + requested_instrumental
        )
    if resolved == "chained_multishot":
        if bool(enhance_description):
            parts.append(
                "ACTIVE DIRECTORIAL ENHANCEMENT — AUTONOMOUS SEGMENTS (develop the request, without changing it):\n"
                "- Turn each terse item into concrete, vivid standalone audiovisual prose across its full target "
                "duration. Every added detail must be visibly observable or audibly motivated.\n"
                "- Establish visual style and opening composition, then source-supported subject appearance and frame "
                "position, environment and key props, blocking, actions and reactions, observable state changes, "
                "lighting, material response, atmosphere, camera behavior, and physical sound permitted by the selected "
                "audio policy in playback "
                "order. Preserve spatial relationships, causality, action count, and the requested ending.\n"
                "- Make action mechanics, contacts, weight transfer, eyelines, expressions, and consequences readable "
                "where the source supports them. Allocate enough screen time for every requested action and spoken line; "
                "do not pad the segment with generic cinematic adjectives or unrelated background activity.\n"
                "- Begin from a concrete opening state and finish in a concrete visible state suitable for chaining. "
                "Develop camera movement and staging inside the item without inventing an edit, extra event, dialogue, "
                "character, prop, reference, light source, weather change, damage, or stronger explicitness."
            )
        else:
            parts.append(
                "CONSERVATIVE FORMAT ADAPTATION — AUTONOMOUS SEGMENTS:\n"
                "Convert each requested item into self-contained H3 prose with only the detail needed for continuity "
                "and valid chaining. Preserve the source's level of specificity; do not creatively expand staging, "
                "performance, production design, camera, lighting, atmosphere, story, or sound."
            )
        count = (
            explicit_shot_plan["shotCount"]
            if explicit_shot_plan["provided"] else max(0, int(multishot_shot_count or 0))
        )
        locks = [
            ("IDENTITY LOCK", multishot_identity_lock),
            ("VOICE LOCK", multishot_voice_lock),
            ("SETTING LOCK", multishot_setting_lock),
        ]
        for label, lock in locks:
            if str(lock).strip():
                parts.append(f"{label} (repeat verbatim in every prompt item):\n{str(lock).strip()}")
        shot_segments = _explicit_shot_segments(basic_prompt)
        if not explicit_shot_plan["provided"] and shot_segments and (not count or len(shot_segments) == count):
            parts.append(
                "AUTHORITATIVE MULTISHOT ITEM PLAN: Each source cut creates the next independent prompt item. "
                "Do not move actions, dialogue occurrences, reactions, transformations, or wardrobe states between "
                "items. Develop each span audiovisually while preserving its causal order:\n"
                + "\n".join(
                    f"- Prompt item {index}: {segment}"
                    for index, segment in enumerate(shot_segments, start=1)
                )
            )
        dialogue_contracts = _source_dialogue_contracts(basic_prompt)
        dialogue_items = _source_dialogue_shot_indices(basic_prompt)
        if (voice_performance == "audible" and dialogue_contracts
                and len(dialogue_items) == len(dialogue_contracts)):
            parts.append(
                "MULTISHOT DIALOGUE LEDGER: Keep every occurrence in its assigned item. Terminal punctuation such as "
                "an exclamation mark controls emphasis and may be expressed through forceful delivery, but never omit "
                "or change the lexical words:\n"
                + "\n".join(
                    f"- Prompt item {item}: <d>[{language}] {quote}</d>"
                    for item, (language, quote, _internal) in zip(dialogue_items, dialogue_contracts)
                )
            )
        if voice_performance == "audible":
            parts.append(
                "VOICE POLICY — AUDIBLE: Preserve every exact source or planned dialogue occurrence once in its "
                "assigned item using a stable vocal source and <d>[Language] exact words</d>. Author no additional "
                "speech unless the explicit dialogue-authoring contract permits it."
            )
        elif voice_performance == "silent_mouth_acting_experimental":
            profiles = []
            for language, quote, internal in dialogue_contracts:
                word_count = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", quote))
                pauses = len(re.findall(r"[,;:…]|\.\.\.", quote))
                profiles.append(
                    f"- {'Internal/off-screen thought' if internal else 'Visible speech'}: {language}; approximately "
                    f"{word_count} words; {pauses} marked pause(s)."
                )
            profile_text = ("\n" + "\n".join(profiles)) if profiles else ""
            parts.append(
                "VOICE POLICY — SILENT MOUTH ACTING (EXPERIMENTAL): Emit no dialogue words, quotations, <d> blocks, "
                "speaker IDs, narration, voiceover, singing, whispering, or intelligible vocal sound. For visible "
                "source speech, describe only silent natural mouth/jaw acting through language, approximate word "
                "count, cadence, and pauses; internal or off-screen speech keeps lips closed."
                + profile_text
            )
        else:
            parts.append(
                "VOICE POLICY — NONE: Emit no dialogue words, quotations, <d> blocks, speaker IDs, narration, "
                "voiceover, singing, whispering, intelligible background speech, or speech-like mouth performance. "
                "Preserve only associated non-vocal visible actions and expressions."
            )
        parts.extend([
            "CHAINED MULTISHOT CONTRACT:\n"
            "- Each JSON array item is an independent H3 conditioning pass and must be self-contained fluent prose.\n"
            "- Repeat supplied stable identity, wardrobe, environment, style, and voice facts verbatim where applicable.\n"
            "- End each segment in a concrete chainable visual state and make the following segment compatible with it.\n"
            "- Preserve every dialogue occurrence permitted by the voice policy; obey the ambience, score, and voice "
            "policies independently in every segment; use no section/shot labels.\n"
            "- Treat 2.5 spoken words per second only as a diagnostic planning heuristic, never as permission to "
            + ("write beyond the explicit dialogue-authoring brief." if dialogue_authoring else "invent dialogue."),
            (f"OUTPUT EXACTLY {count} PROMPT ITEMS." if count else
             "Infer the smallest useful number of prompt items from explicit scene/segment structure; default to one."),
            "Return only valid JSON shaped exactly as {\"prompts\":[\"...\"]}.",
        ])
        return "\n\n".join(parts)
    if explicit_shot_plan["provided"]:
        edit_enhancement_guidance = (
            "- Treat the supplied explicit shot plan as the entire edit map. Develop camera movement, staging, and "
            "information inside each listed shot, but do not add, remove, merge, split, reorder, or relocate a cut.\n"
        )
    else:
        edit_enhancement_guidance = (
            "- Add a cut only when it creates a meaningful change of viewpoint, time, location, scale, or information; "
            "otherwise prefer a motivated continuous camera move.\n"
            "- Default to one continuous shot when the source describes one simultaneous moment or action. Do not "
            "invent inserts, cutaways, or extra shots merely to dramatize an object, impact, or already-visible action.\n"
        )
    if bool(enhance_description):
        parts.append(
            "ACTIVE DIRECTORIAL ENHANCEMENT (develop the request, without changing it):\n"
            "- Turn terse wording into a concrete, vivid audiovisual sequence across the full target duration.\n"
            "- Improve composition, blocking, facial performance, lighting, materials, atmosphere, camera behavior, "
            "action continuity, and pacing only within explicit source, shot-plan, reference, Cinematography, and audio "
            "constraints. Develop physical sound only as permitted by the ambience/foley policy; musical treatment is "
            "governed exclusively by the background-score policy.\n"
            "- At the beginning of every shot, establish a useful shot scale and the current frame positions, "
            "orientation, eyelines, and relevant prop states. Across cuts preserve screen direction, handed contact, "
            "object possession, pose continuity, and states such as open/closed or intact/changed unless the requested "
            "action visibly changes them.\n"
            "- When the source contains physical interaction, describe the actor, limb or manipulated object, point of "
            "contact, physically readable response, and resulting state. Complete requested actions and let their "
            "visible results register before the final frame unless the source explicitly requests interruption.\n"
            "- Prefer observable geometry, materials, position, movement, and cause-and-effect over generic cinematic "
            "adjectives or unrelated background activity.\n"
            "- Make causal beats and important reveals easy to follow. Allocate enough screen time for each requested "
            "action and spoken line.\n"
            "- Treat repeated action/trigger/transformation cycles as a state ladder. For every cycle, preserve the "
            "exact action count, show the trigger at its requested moment, then describe the new visible body, wardrobe, "
            "expression, and performance state before advancing. Never collapse distinct escalation stages together.\n"
            "- Make explicit repetitions visually countable through complete start-to-finish motion cycles. Keep causal "
            "order literal: an effect requested after a line or action starts only after that cue has completed.\n"
            "- For an explicit fly/propel/move-offscreen consequence, keep a sufficiently wide view on the named "
            "subject's readable trajectory until it fully exits the frame; a cut, disappearance, close-up, implied "
            "aftermath, or simple fall does not satisfy that requested action.\n"
            + edit_enhancement_guidance +
            "- Express absolute cut times only in [Shot N] headers. Do not add competing numeric timestamps inside a "
            "shot, and never create another shot or vocal cue to repeat or continue the same short line.\n"
            "- Enrich delivery around quoted speech, but never rewrite, extend, translate, censor, or replace its words.\n"
            "- Preserve explicit age category, gender, character count, identity relationships, wardrobe, object subtype, "
            "and spatial/chronological relationships literally. For example, older/elderly must not become middle-aged "
            "or young, and multiple variants of one person must not become unrelated people.\n"
            "- Do not invent new characters, plot events, branded objects, reference assets, or an ending that "
            "changes the user's intent. "
            + (
                "Author dialogue only within the explicit dialogue-writing brief above. "
                if dialogue_authoring and voice_performance == "audible" else
                "Do not invent dialogue. "
            )
            + "Do not increase gore, damage, or explicitness beyond the source."
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
        dialogue_totals = Counter(
            (language, _dialogue_lexical_key(quote), internal)
            for language, quote, internal in dialogue_contracts
        )
        dialogue_seen: Counter[tuple[str, str, bool]] = Counter()
        dialogue_lines = []
        for contract in dialogue_contracts:
            language, quote, internal = contract
            dialogue_key = (language, _dialogue_lexical_key(quote), internal)
            dialogue_seen[dialogue_key] += 1
            occurrence = (
                f"Occurrence {dialogue_seen[dialogue_key]} of {dialogue_totals[dialogue_key]}: "
                if dialogue_totals[dialogue_key] > 1 else ""
            )
            dialogue_lines.append(f"- {occurrence}<d>[{language}] {quote}</d>")
        authored_dialogue_note = (
            " The listed source blocks are immutable anchors, but do not add a no-more-speech closure: the explicit "
            "dialogue-authoring contract may place additional concrete lines at later requested beats."
            if dialogue_authoring else
            " After the final tagged line, describe only silent facial acting, gaze, gesture, and physical action. "
            "When a short line is followed by a long visual continuation, explicitly state that the speaker closes "
            "their lips or leaves the frame, then name at least two concrete non-verbal sounds that continuously "
            "occupy the remainder of the timeline. No character speaks additional words."
        )
        parts.append(
            "VOICE POLICY — AUDIBLE (official): Assign stable speaker IDs and copy each block exactly once into the "
            "timeline. Do not omit, translate, censor, duplicate, or move it to soundscape. Every affirmative vocal "
            "cue must be in the same sentence as its matching <d> block. For visible dialogue, use a short natural "
            "official vocal sentence with identity, stable ID, action/delivery, and <d>; says, replies, asks, shouts, "
            "whispers, sings, booms, and compound group IDs are valid. Never use vague 'speaks' or 'delivers the line' cues."
            + authored_dialogue_note +
            " Never spread one short line across shots. Repeated identical blocks listed below are intentional "
            "separate utterances at their distinct source beats, not duplicates; keep their recurring source on the "
            "same stable speaker ID:\n" + "\n".join(dialogue_lines)
        )
        repeated_dialogue = any(count > 1 for count in dialogue_totals.values())
        if repeated_dialogue and re.search(r"\b(?:god|godlike|divine|deity|dios|divina?)\b", basic_prompt, re.IGNORECASE):
            parts.append(
                "OFF-SCREEN RECURRING VOICE LOCK: Attribute every repeated divine cue exactly as an off-screen "
                "godlike voice (S1) with an explicit vocal action such as 'booms' in the same sentence as its <d> "
                "block. Reuse S1 every time; never rename it as an echo, sound, phrase, or unseen unresolved source."
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

    required_explicit_shots = _required_explicit_shot_count(basic_prompt)
    simultaneous_single_shot = (
        False if explicit_shot_plan["provided"]
        else _requires_single_simultaneous_shot(basic_prompt, duration_seconds)
    )
    continuous_progression = (
        False if explicit_shot_plan["provided"]
        else _requires_single_continuous_progression(basic_prompt)
    )
    single_shot = simultaneous_single_shot or continuous_progression
    if explicit_shot_plan["provided"]:
        # The complete plan was already injected before the mode fork.  Do not
        # append inferred or source-derived edit guidance that could compete
        # with its exact boundaries.
        pass
    elif required_explicit_shots:
        shot_segments = _explicit_shot_segments(basic_prompt)
        parts.append(
            f"EXPLICIT EDIT PLAN: Use exactly {required_explicit_shots} shots because the source contains "
            f"{required_explicit_shots - 1} mandatory cut command(s). Preserve every cut in source order: Shot 1 "
            "has no timestamp and each later shot begins with a strictly increasing [Shot N] At MM:SS.mmm header. "
            "A requested close-up after a cut is a new shot, not a reframing inside the previous take. Do not move an "
            "action, dialogue occurrence, reaction, transformation stage, or wardrobe state across these boundaries.\n"
            + "\n".join(
                f"- Shot {index} authoritative source span: {segment}"
                for index, segment in enumerate(shot_segments, start=1)
            )
        )
    elif single_shot:
        parts.append(
            "SHOT PLAN: Exactly one continuous shot. Treat gradual reveals, sequential beats in the same place, and "
            "camera reframing as choreography within Shot 1, not as new shots. Do not add inserts, cutaways, periodic "
            "three-second divisions, or additional [Shot N] headers.\n"
            + (
                "SIMULTANEITY LOCK: The actions joined by while/mientras occur continuously at the same time. Camera "
                "motion, framing, and depth of field must never isolate or obscure either requested action."
                if simultaneous_single_shot else
                "CONTINUOUS REVEAL LOCK: Preserve the gradual progression in real time. Use a motivated pan, dolly, "
                "rack focus, or blocking change inside the same take rather than cutting at each reveal beat."
            )
        )
    elif _implicit_shot_limit(basic_prompt) == 2:
        parts.append(
            "SHOT BUDGET: The source supplied no explicit cut or montage structure. Prefer one continuous shot and use "
            "at most two shots only if one motivated cut materially improves viewpoint or information. Never divide the "
            "duration into evenly spaced shots merely to fill time; actions and reveals are beats inside a shot."
        )
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
    dialogue_check = (
        "preserve every exact source-provided line and copy every dialogue-ledger line exactly once"
        if authored_dialogue_ledger and voice_performance == "audible" else
        "preserve every exact source-provided line and write the additionally requested concrete dialogue"
        if dialogue_authoring and voice_performance == "audible" else
        "use each exact quoted spoken line once and only once"
        if voice_performance == "audible" else
        "emit zero audible dialogue and zero lexical source-dialogue text"
    )
    dialogue_scope_check = (
        "author no dialogue beyond the exact ledger and do not invent music"
        if authored_dialogue_ledger and voice_performance == "audible" and background_score_policy != "add_instrumental" else
        "author no dialogue beyond the exact ledger and do not invent musical vocals"
        if authored_dialogue_ledger and voice_performance == "audible" else
        "write dialogue only within the explicit authoring brief and do not invent music"
        if dialogue_authoring and voice_performance == "audible" and background_score_policy != "add_instrumental" else
        "write dialogue only within the explicit authoring brief and do not invent musical vocals"
        if dialogue_authoring and voice_performance == "audible" else
        "do not invent dialogue or music"
        if background_score_policy != "add_instrumental" else
        "do not invent dialogue or musical vocals"
    )
    final_checks = [
        "preserve every immutable source fact",
        dialogue_check,
        dialogue_scope_check,
        "use numeric cut times only in later [Shot N] headers",
    ]
    if explicit_shot_plan["provided"]:
        final_checks.insert(0, f"use exactly {explicit_shot_plan['shotCount']} shots in the supplied order")
        if explicit_shot_plan["timingMode"] == "exact":
            final_checks.append("use every exact supplied shot boundary")
    elif required_explicit_shots:
        final_checks.insert(0, f"use exactly {required_explicit_shots} shots and preserve every explicit source cut")
    elif single_shot:
        final_checks.insert(0, "exactly one continuous shot")
        final_checks.append(
            "keep the simultaneous actions visible together" if simultaneous_single_shot
            else "keep the gradual reveal inside that single take"
        )
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
        value = re.sub(
            rf"(?m)^{re.escape(section)}:(?=\S)",
            f"{section}:\n",
            value,
        )
    return value


def normalize_dialogue_tags(text: str) -> str:
    """Keep dialogue parseable when a small LLM omits only the required language marker."""
    value = re.sub(
        r"<d>\s*(?!\[[^\]]+\])",
        "<d>[Original language] ",
        str(text),
        flags=re.IGNORECASE,
    )
    value = re.sub(r"(<d>\[[^\]]+\])\s*", r"\1 ", value, flags=re.IGNORECASE)
    # The official <d> block is the quotation boundary. Extra prose quotes
    # around it can trap later repair text inside a spoken string.
    return re.sub(
        r'["“]\s*(<d>.*?</d>)([.!?,;:]?)\s*["”]',
        r"\1\2",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _source_dialogue_language(source_prompt: str, quote_match) -> str:
    window = (source_prompt or "")[max(0, quote_match.start() - 180):quote_match.start()]
    trailing = (source_prompt or "")[quote_match.end():quote_match.end() + 80]
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
    trailing_known = re.match(
        r"^\s*(?:,\s*)?(?:in|en)\s+(english|spanish|french|german|italian|portuguese|japanese|"
        r"korean|chinese|russian|arabic|hindi|dutch|polish|turkish|catalonian|catalan|catalán|"
        r"català|español|castilian|castellano)\b",
        trailing,
        flags=re.IGNORECASE,
    )
    if trailing_known:
        raw = trailing_known.group(1)
        return _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize())
    quote = quote_match.group(1)
    if re.search(
        r"[¿¡áéíóúñ]|\b(?:quién|qué|cuál|cuándo|dónde|cómo|por qué|tranquilo|tranquila|"
        r"estás|está|quiero|queréis|cabrones|asesino|cargadores)\b",
        quote,
        re.IGNORECASE,
    ):
        return "Spanish"
    return "Original language"


def _source_quote_is_internal_monologue(source_prompt: str, quote_match) -> bool:
    window = (source_prompt or "")[max(0, quote_match.start() - 180):quote_match.start()]
    return bool(_INTERNAL_MONOLOGUE_CUE_RE.search(window))


def _dialogue_lexical_key(quote: str) -> str:
    """Match repeated cues despite terminal emphasis while preserving authored text later."""
    value = re.sub(r"\s+", " ", str(quote)).strip().casefold()
    return re.sub(r"[.!?…]+$", "", value).strip()


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
        contracts.append((language.strip(), quote.strip(), False))

    # "Again" commonly repeats a short quoted cue without restating its
    # language. Carry an explicit language across identical occurrences while
    # retaining their multiplicity and timeline order.
    explicit_languages: dict[str, str] = {}
    for language, quote, _internal in contracts:
        if language.casefold() != "original language":
            explicit_languages.setdefault(_dialogue_lexical_key(quote), language)
    return [
        (explicit_languages.get(_dialogue_lexical_key(quote), language), quote, internal)
        for language, quote, internal in contracts
    ]


def _deduplicate_source_dialogue(text: str, source_prompt: str) -> str:
    expected = Counter(
        f"[{language}] {quote}".casefold() for language, quote, _internal in _source_dialogue_contracts(source_prompt)
    )
    seen: Counter[str] = Counter()

    def replace(match):
        inner = re.sub(r"\s+", " ", match.group(1).strip()).casefold()
        if inner in expected:
            seen[inner] += 1
            if seen[inner] > expected[inner]:
                return ""
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


def _finalize_audible_dialogue(text: str, source_prompt: str) -> str:
    """Repair audible dialogue and close only a literal source-dialogue envelope."""
    value = str(text)
    source_contracts = _source_dialogue_contracts(source_prompt)
    dialogue_authoring, _language = _dialogue_authoring_request(source_prompt)
    if not source_contracts and not dialogue_authoring:
        return value
    # Resolve model-authored speaker placeholders before identity tracking.
    # Use the smallest free positive ID so an existing (S2) does not turn an
    # earlier narrator placeholder into an arbitrary (S3).
    used_speaker_ids = {int(item) for item in re.findall(r"\(S(\d+)\)", value, flags=re.IGNORECASE)}

    def resolve_speaker_placeholder(_match: re.Match[str]) -> str:
        speaker_id = 1
        while speaker_id in used_speaker_ids:
            speaker_id += 1
        used_speaker_ids.add(speaker_id)
        return f"(S{speaker_id})"

    value = re.sub(r"\(Sx\)", resolve_speaker_placeholder, value, flags=re.IGNORECASE)
    value = re.sub(
        r"\bAn off-screen voiceover\b(?=\s*(?:\(S\d+\)\s*)?"
        r"(?:says?|asks?|replies|shouts?|whispers?|speaks?|delivers?))",
        "An off-screen narrator",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\bAs\s+(?:he|she|they|the\s+[\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,3})\s+"
        r"(?:finishes|continues)\s+(?:speaking|talking)\b",
        "After the exact tagged line ends",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\bwhile\s+(?:(?:he|she|they|the\s+[\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,2})\s+)?"
        r"(?:speaks?|speaking|talks?|talking)(?:\s+(?:his|her|their|the)\s+(?:line|words?))?\b",
        "during the exact tagged line",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\bAs\s+(?:he|she|they|the\s+[\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,3})\s+"
        r"(?:speaks|talks)\b",
        "During the exact tagged line",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\b(He|She|They|The\s+[\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,3})\s+speaks\s+directly\s+to\s+"
        r"([^,.;]+),\s*(?:maintaining\s+eye\s+contact\s+with\s+(?:him|her|them)\s+)?while\s+",
        r"\1 maintains eye contact with \2 while ",
        value,
        flags=re.IGNORECASE,
    )
    # MiniMax's official format assigns a stable speaker ID to every audible
    # source. Small local LLMs sometimes preserve <d> perfectly but omit the
    # ID, which makes the audio model more prone to treating later descriptive
    # prose as another voice. Repair the common visible-speaker forms here.
    dialogue_matches = list(re.finditer(r"<d>.*?</d>", value, flags=re.DOTALL | re.IGNORECASE))
    existing_ids = [int(item) for item in re.findall(r"\(S(\d+)\)", value, flags=re.IGNORECASE)]
    next_speaker_id = max(existing_ids, default=0) + 1
    identity_ids: dict[str, int] = {}
    last_concrete_identity = ""
    repairs: list[tuple[int, int, str]] = []
    vocal_action = (
        r"(?:says?|asks?|replies|responds?|exclaims?|shouts?|whispers?|sings?|chants?|calls?|"
        r"booms?|repeats?|speaks?|explains?|narrates?|describes?|comments?|"
        r"delivers?\s+(?:the\s+)?(?:line|words?))"
    )
    for dialogue in dialogue_matches:
        sentence_start = max(
            value.rfind(".", 0, dialogue.start()),
            value.rfind("!", 0, dialogue.start()),
            value.rfind("?", 0, dialogue.start()),
            value.rfind("[Shot", 0, dialogue.start()),
        )
        sentence_start = 0 if sentence_start < 0 else sentence_start + 1
        prefix = value[sentence_start:dialogue.start()]
        subject_matches = list(re.finditer(r"<Subject\s+\d+>", prefix, flags=re.IGNORECASE))
        actor_match = re.search(
            rf"\b((?:The|An?|This)\s+[\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){{0,4}}|He|She|They)\s+"
            rf"(?={vocal_action}\b)",
            prefix,
            flags=re.IGNORECASE,
        )
        if subject_matches:
            identity = subject_matches[-1].group(0).casefold()
            last_concrete_identity = identity
        elif actor_match and actor_match.group(1).casefold() not in {"he", "she", "they"}:
            identity = re.sub(r"\s+", " ", actor_match.group(1).casefold())
            last_concrete_identity = identity
        elif actor_match and last_concrete_identity:
            identity = last_concrete_identity
        else:
            identity = f"event:{dialogue.start()}"

        explicit = re.search(r"\(S(\d+)(?:\s*,\s*S\d+)*\)", prefix, flags=re.IGNORECASE)
        if explicit:
            original_prefix = prefix
            repair_recorded = False
            explicit_id = int(explicit.group(1))
            canonical_id = identity_ids.get(identity)
            if canonical_id is None:
                identity_ids[identity] = explicit_id
            elif canonical_id != explicit_id:
                prefix = prefix[:explicit.start()] + f"(S{canonical_id})" + prefix[explicit.end():]
                explicit_id = canonical_id
            action_match = re.search(vocal_action, prefix, flags=re.IGNORECASE)
            if action_match and explicit.start() > action_match.start() and (subject_matches or actor_match):
                cleaned = (prefix[:explicit.start()] + prefix[explicit.end():]).rstrip() + " "
                clean_subjects = list(re.finditer(r"<Subject\s+\d+>", cleaned, flags=re.IGNORECASE))
                clean_actor = re.search(
                    rf"\b((?:The|An?|This)\s+[\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){{0,4}}|He|She|They)\s+"
                    rf"(?={vocal_action}\b)",
                    cleaned,
                    flags=re.IGNORECASE,
                )
                if clean_subjects:
                    anchor = clean_subjects[-1]
                    repaired = cleaned[:anchor.end()] + f" (S{explicit_id})" + cleaned[anchor.end():]
                elif clean_actor:
                    repaired = cleaned[:clean_actor.end(1)] + f" (S{explicit_id})" + cleaned[clean_actor.end(1):]
                else:
                    repaired = prefix
                if repaired != prefix:
                    repairs.append((sentence_start, dialogue.start(), repaired))
                    repair_recorded = True
            if not repair_recorded and prefix != original_prefix:
                repairs.append((sentence_start, dialogue.start(), prefix))
            continue
        speaker_id = identity_ids.get(identity)
        if speaker_id is None:
            speaker_id = next_speaker_id
            next_speaker_id += 1
            identity_ids[identity] = speaker_id
        if subject_matches:
            subject = subject_matches[-1]
            repaired = prefix[:subject.end()] + f" (S{speaker_id})" + prefix[subject.end():]
        elif actor_match:
            repaired = prefix[:actor_match.end(1)] + f" (S{speaker_id})" + prefix[actor_match.end(1):]
        else:
            repaired = prefix
        if repaired != prefix:
            repairs.append((sentence_start, dialogue.start(), repaired))
    for start, end, repaired in reversed(repairs):
        value = value[:start] + repaired + value[end:]

    # When the source explicitly says a short cue happens "again", identical
    # lexical lines belong to the same recurring voice. Models often rename the
    # source slightly at every beat and consequently drift from S1 to S2/S3.
    repeated_keys = {
        key for key, count in Counter(_dialogue_lexical_key(quote) for _lang, quote, _internal in source_contracts).items()
        if count > 1
    }
    if repeated_keys and re.search(r"\b(?:again|repeats?|repeated|de\s+nuevo|otra\s+vez)\b", source_prompt, re.IGNORECASE):
        dialogue_matches = list(re.finditer(r"<d>.*?</d>", value, flags=re.DOTALL | re.IGNORECASE))
        canonical_ids: dict[str, int] = {}
        id_repairs: list[tuple[int, int, str]] = []
        for contract, dialogue in zip(source_contracts, dialogue_matches):
            key = _dialogue_lexical_key(contract[1])
            if key not in repeated_keys:
                continue
            sentence_start = max(
                value.rfind(".", 0, dialogue.start()), value.rfind("!", 0, dialogue.start()),
                value.rfind("?", 0, dialogue.start()), value.rfind("[Shot", 0, dialogue.start()),
            )
            sentence_start = 0 if sentence_start < 0 else sentence_start + 1
            prefix = value[sentence_start:dialogue.start()]
            explicit = re.search(r"\(S(\d+)(?:\s*,\s*S\d+)*\)", prefix, flags=re.IGNORECASE)
            if not explicit:
                continue
            observed_id = int(explicit.group(1))
            canonical_id = canonical_ids.setdefault(key, observed_id)
            if observed_id != canonical_id:
                repaired = prefix[:explicit.start()] + f"(S{canonical_id})" + prefix[explicit.end():]
                id_repairs.append((sentence_start, dialogue.start(), repaired))
        for start, end, repaired in reversed(id_repairs):
            value = value[:start] + repaired + value[end:]

    # Replace earlier repair/template closure prose with one minimal,
    # idempotent boundary. Do not force every mouth closed: voiceover and
    # non-verbal vocalizations remain compatible with no additional dialogue.
    value = re.sub(
        r"\s*The speaker immediately closes their mouth\.", "", value, flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\s*After the final tagged line, no character speaks any additional words[.;]?",
        "", value, flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\s*From this point through the final frame, every character keeps their mouth closed"
        r"(?:;\s*the (?:single )?tagged lines? (?:is|are) the only intelligible speech in the video)?[.;]?",
        "", value, flags=re.IGNORECASE,
    )
    value = re.sub(r"\s*,\s*and the scene\b", " The scene", value, flags=re.IGNORECASE)
    value = re.sub(
        r"(\bthe\s+[^,.;]{1,140}\s+in\s+a\s+wheelchair),\s+(?:who\s+is\s+)?seated\s+in\s+"
        r"(?:her|his|a)\s+wheelchair",
        r"\1",
        value,
        flags=re.IGNORECASE,
    )
    matches = list(re.finditer(r"</d>(?:[.,])?", value, flags=re.IGNORECASE))
    canonical_boundary = "After the final tagged line, no character speaks any additional words."
    if matches and not dialogue_authoring and canonical_boundary not in value:
        end = matches[-1].end()
        value = (
            value[:end]
            + " " + canonical_boundary
            + value[end:]
        )
    # In Ref2VA prompts, a local LLM may repeat human-readable reference aliases
    # after dialogue (for example "the beret-wearing version"). H3 can mistake
    # those timeline labels for narration even though they are outside <d>.
    # The canonical <Subject N> already carries the exact visual binding, so
    # remove only meta alias appositives after the last spoken line.
    timeline_section = "detailed_description" if "detailed_description:" in value else "integrated_multimodal_description"
    timeline = _section_body(value, timeline_section)
    final_dialogue = list(re.finditer(r"</d>", timeline, flags=re.IGNORECASE))
    if final_dialogue:
        split = final_dialogue[-1].end()
        before, after = timeline[:split], timeline[split:]

        def drop_vocalizable_alias(match: re.Match[str]) -> str:
            alias = match.group(2)
            if re.search(r"\b(?:version|variant|identified|called|named|known)\b", alias, flags=re.IGNORECASE):
                return match.group(1) + ("." if match.group(3) == "." else "")
            return match.group(0)

        after = re.sub(
            r"(<Subject\s+\d+>)\s*,\s*((?:(?!<Subject\s+\d+>)[^,.]){1,120})([,.])",
            drop_vocalizable_alias,
            after,
            flags=re.IGNORECASE,
        )
        value = _replace_section_body(value, timeline_section, before + after)
    soundscape = _section_body(value, "overall_soundscape").strip()
    soundscape = re.sub(
        r"\s*The (?:(?:single|one|two|three|four|five|\d+)\s+)?tagged lines? (?:is|are) the only intelligible "
        r"(?:voice|speech); after (?:it|they|the final line) ends?, only non-verbal ambience and physical sounds remain, "
        r"with no narration, whispers, or additional words\.",
        "",
        soundscape,
        flags=re.IGNORECASE,
    ).strip()
    dialogue_count = len(re.findall(r"<d>.*?</d>", value, flags=re.DOTALL | re.IGNORECASE))
    if soundscape and dialogue_count and not dialogue_authoring:
        count_label = {1: "The tagged line is", 2: "The two tagged lines are", 3: "The three tagged lines are"}.get(
            dialogue_count, f"The {dialogue_count} tagged lines are",
        )
        boundary = (
            f"{count_label} the only intelligible speech; after the final line ends, only non-verbal ambience and "
            "physical sounds remain, with no narration, whispers, or additional words."
        )
        value = _replace_section_body(value, "overall_soundscape", (soundscape + " " + boundary).strip())
    return value


def _untagged_speech_actions(timeline: str) -> list[str]:
    """Return affirmative vocal cues that are not anchored to an exact <d> block."""
    found = []
    for sentence in re.split(r"(?<=[.!?])\s+", timeline or ""):
        if "<d>" in sentence.casefold():
            continue
        if re.search(
            r"\b(?:no\s+(?:one|character|person)|nobody)\s+speaks?\b|"
            r"\b(?:does|do)\s+not\s+(?:speak|talk|say)\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            continue
        match = _UNTAGGED_SPEECH_ACTION_RE.search(sentence)
        if match:
            found.append(match.group(0))
    return found


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
        r"explains?|explaining|narrates?|narrating|describes?|describing|comments?|commenting|"
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
    contracts = _source_dialogue_contracts(source_prompt)
    if not contracts:
        return _finalize_audible_dialogue(value, source_prompt)
    if any(internal for _language, _quote, internal in contracts):
        value = _remove_internal_monologue_placeholders(value)
        value = re.sub(
            r"says in an off-screen internal monologue",
            "says in an off-screen voiceover, as a concentrated internal monologue",
            value,
            flags=re.IGNORECASE,
        )

    remaining = list(contracts)

    def take_contract(candidate: str):
        key = _dialogue_lexical_key(candidate)
        for index, contract in enumerate(remaining):
            if _dialogue_lexical_key(contract[1]) == key:
                return remaining.pop(index)
        return None

    def canonicalize_tag(match: re.Match[str]) -> str:
        inner = re.sub(r"^\s*\[[^\]]+\]\s*", "", match.group(1), flags=re.IGNORECASE)
        contract = take_contract(inner)
        if not contract:
            return match.group(0)
        language, quote, _internal = contract
        return f"<d>[{language}] {quote}</d>"

    # Canonicalize whole blocks first. Replacing raw substrings before this step
    # can create invalid nested <d> tags when punctuation differs.
    value = re.sub(r"<d>(.*?)</d>", canonicalize_tag, value, flags=re.DOTALL | re.IGNORECASE)

    def canonicalize_quote(match: re.Match[str]) -> str:
        contract = take_contract(match.group(1))
        if not contract:
            return match.group(0)
        language, quote, _internal = contract
        return f"<d>[{language}] {quote}</d>"

    value = _QUOTED_RE.sub(canonicalize_quote, value)
    additions = []
    # A single completely omitted line can be restored safely. With repeated
    # lines, guessing one insertion point would destroy their causal placement;
    # leave them missing so the validation/LLM repair pass restores each beat.
    if remaining and len(contracts) == 1:
        language, quote, is_internal_monologue = remaining.pop(0)
        block = f"<d>[{language}] {quote}</d>"
        if is_internal_monologue:
            additions.append(
                f"The thinking on-screen character (S1) says in an off-screen voiceover, as a concentrated internal "
                f"monologue: {block}, while the character's lips remain completely closed."
            )
        else:
            additions.append(f"The on-screen speaker (S1) delivers the requested line: {block}.")
    if not additions:
        return _finalize_audible_dialogue(_deduplicate_source_dialogue(value, source_prompt), source_prompt)
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
    return _finalize_audible_dialogue(_deduplicate_source_dialogue(value, source_prompt), source_prompt)


def _replace_section_body(text: str, section: str, body: str) -> str:
    match = re.search(
        rf"(?ms)(^{re.escape(section)}:\s*)(.*?)(?=^(?:{_SECTION_PATTERN}):\s*|\Z)", str(text),
    )
    if not match:
        return str(text)
    return str(text)[:match.start(2)] + body.strip() + "\n\n" + str(text)[match.end(2):].lstrip()


def normalize_audio_policy(text: str, ambience_foley_policy: str = "auto",
                           background_score_policy: str = "follow_prompt",
                           voice_performance: str = "audible",
                           source_context: str = "") -> str:
    value = str(text)
    force_no_music = background_score_policy == "off" or (
        background_score_policy == "follow_prompt" and not _source_requests_music(source_context)
    )
    if force_no_music and _section_body(value, "non_diegetic_music").strip().casefold() != "n/a":
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


def normalize_shot_timeline(text: str, mode: str, duration_seconds: float,
                            explicit_shot_plan: Mapping[str, Any] | None = None) -> str:
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
    plan = explicit_shot_plan or {}
    shot_count = max(int(item.group(1)) for item in markers)
    exact_cuts = list(plan.get("expectedCutTimesSeconds", ())) if plan.get("timingMode") == "exact" else []
    for shot_number in range(2, shot_count + 1):
        cut = (
            float(exact_cuts[shot_number - 2])
            if shot_number - 2 < len(exact_cuts)
            else float(duration_seconds) * (shot_number - 1) / shot_count
        )
        minutes = int(cut // 60)
        seconds = cut - minutes * 60
        timestamp = f"{minutes:02d}:{seconds:06.3f}"
        pattern = re.compile(
            rf"\[Shot\s+{shot_number}\](?:\s+At\s+(?:\d{{2}}:[0-9Xx]{{2}}\.[0-9Xx]{{3}}|[0-9Xx]{{2}}:[0-9Xx]{{2}}\.[0-9Xx]{{3}}),?)?",
            re.IGNORECASE,
        )
        match = pattern.search(body)
        valid_complete_header = bool(match and re.fullmatch(
            rf"\[Shot\s+{shot_number}\]\s+At\s+\d{{2}}:\d{{2}}\.\d{{3}},?",
            match.group(0), flags=re.IGNORECASE,
        ))
        if match and (exact_cuts or not valid_complete_header):
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


def normalize_multishot_output(text: str, required_locks: tuple[str, ...] = ()) -> str:
    """Canonicalize JSON or --- separated multishot output for the sampler."""
    value = strip_markdown_fence(str(text)).strip()
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        prompts = [part.strip() for part in re.split(r"(?m)^\s*---\s*$", value) if part.strip()]
        data = {"prompts": prompts}
    if isinstance(data, list):
        data = {"prompts": data}
    prompts = data.get("prompts", []) if isinstance(data, dict) else []
    prompts = [str(item).strip() for item in prompts if str(item).strip()]
    locks = [str(lock).strip() for lock in required_locks if str(lock).strip()]
    prompts = [" ".join([*(lock for lock in locks if lock not in prompt), prompt]).strip() for prompt in prompts]
    return json.dumps({"prompts": prompts}, ensure_ascii=False, separators=(",", ":"))


def _validate_multishot(prompt: str, duration_seconds: float, source_prompt: str,
                        shot_count: int = 0, required_locks: tuple[str, ...] = (),
                        voice_performance: str = "audible",
                        authored_dialogue_ledger: tuple[tuple[str, str], ...] = ()) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = json.loads(str(prompt))
    except json.JSONDecodeError as exc:
        return {"valid": False, "mode": "chained_multishot", "errors": [f"Multishot output must be valid JSON: {exc.msg}"], "warnings": []}
    prompts = data.get("prompts") if isinstance(data, dict) else None
    if not isinstance(prompts, list) or not prompts or not all(isinstance(item, str) and item.strip() for item in prompts):
        errors.append("Multishot output requires a non-empty JSON prompts array of strings")
        prompts = []
    if int(shot_count or 0) and len(prompts) != int(shot_count):
        errors.append(f"Multishot output requires exactly {int(shot_count)} prompt items")
    forbidden = re.compile(r"(?im)^\s*(?:integrated_multimodal_description|subject_definitions|summary|retention_analysis|detailed_description|overall_soundscape|non_diegetic_music):|\[Shot\s+\d+\]")
    for index, item in enumerate(prompts, start=1):
        if forbidden.search(item):
            errors.append(f"Multishot item {index} must be fluent standalone prose without H3 section or shot labels")
        dialogue_words = sum(len(re.findall(r"\b[\wÀ-ÿ'-]+\b", quote)) for quote in _QUOTED_RE.findall(item))
        capacity = max(1, round(float(duration_seconds) * 2.5))
        if dialogue_words > capacity * 1.2:
            warnings.append(f"Multishot item {index} has {dialogue_words} quoted words; ~{capacity} words is a planning heuristic for {duration_seconds:g}s")
        for lock in (str(value).strip() for value in required_locks if str(value).strip()):
            if lock not in item:
                errors.append(f"Multishot item {index} is missing an exact required continuity lock: {lock!r}")
    source_facts = [token.casefold() for token in re.findall(r"\b[\wÀ-ÿ'-]{5,}\b", source_prompt or "")]
    if len(prompts) > 1 and source_facts:
        common = [token for token in dict.fromkeys(source_facts) if all(token in item.casefold() for item in prompts)]
        if len(common) < min(4, len(set(source_facts))):
            warnings.append("Few concrete source attributes repeat across independent prompts; identity or scene continuity may drift")
    source_contracts = _source_dialogue_contracts(source_prompt)
    expected_source_contracts = source_contracts if voice_performance == "audible" else []
    spoken_keys = {_dialogue_lexical_key(quote) for _language, quote, _internal in source_contracts}
    dialogue_authoring, dialogue_authoring_language = _dialogue_authoring_request(source_prompt)
    dialogue_authoring = dialogue_authoring and voice_performance == "audible"

    def item_spoken_keys(item: str) -> list[str]:
        raw = [_dialogue_lexical_key(quote) for quote in _QUOTED_RE.findall(item)]
        tagged = [
            _dialogue_lexical_key(re.sub(r"^\s*\[[^\]]+\]\s*", "", inner))
            for inner in re.findall(r"<d>(.*?)</d>", item, flags=re.DOTALL | re.IGNORECASE)
        ]
        return [key for key in raw + tagged if key in spoken_keys]

    expected_spoken = Counter(
        _dialogue_lexical_key(quote) for _language, quote, _internal in expected_source_contracts
    )
    observed_spoken = Counter(key for item in prompts for key in item_spoken_keys(item))
    if observed_spoken != expected_spoken:
        missing = list((expected_spoken - observed_spoken).elements())
        extra = list((observed_spoken - expected_spoken).elements())
        if missing:
            errors.append(f"Chained prompts omitted or changed spoken dialogue occurrences: {missing}")
        if extra:
            errors.append(f"Chained prompts invented or duplicated spoken dialogue occurrences: {extra}")

    authored_blocks = []
    unexpected_blocks = []
    for item_number, item in enumerate(prompts, start=1):
        for match in re.finditer(r"<d>(.*?)</d>", item, flags=re.DOTALL | re.IGNORECASE):
            inner = match.group(1).strip()
            spoken = re.sub(r"^\[[^\]]+\]\s*", "", inner)
            if _dialogue_lexical_key(spoken) in spoken_keys:
                continue
            if dialogue_authoring:
                authored_blocks.append((item_number, inner))
            else:
                unexpected_blocks.append(spoken)
    if unexpected_blocks:
        errors.append(f"Chained prompts invented dialogue without an explicit authoring request: {unexpected_blocks}")
    if dialogue_authoring and not authored_blocks:
        errors.append(
            "Explicit dialogue authoring request requires at least one concrete language-tagged <d> line in the "
            "chained prompts"
        )
    for item_number, inner in authored_blocks:
        match = re.match(r"\[([^\]]+)\]\s+(.*)", inner, flags=re.DOTALL)
        if not match:
            errors.append(f"Authored dialogue in chained prompt item {item_number} requires a language tag")
            continue
        language, words = match.groups()
        if (dialogue_authoring_language != "Original language"
                and language.strip().casefold() != dialogue_authoring_language.casefold()):
            errors.append(
                f"Authored dialogue in chained prompt item {item_number} must use "
                f"[{dialogue_authoring_language}], observed [{language.strip()}]"
            )
        if re.fullmatch(
            r"(?:\[.*?\]|<.*?>|dialogue|dialog|line|speech|spoken words?|concrete authored words|"
            r"to be (?:written|generated)|di[aá]logo|l[ií]nea|frase|palabras)",
            re.sub(r"\s+", " ", words).strip(),
            flags=re.IGNORECASE,
        ):
            errors.append(f"Authored dialogue in chained prompt item {item_number} must use concrete speakable words")
    if authored_dialogue_ledger:
        expected_ledger = Counter(
            (language.casefold(), re.sub(r"\s+", " ", text).strip())
            for language, text in authored_dialogue_ledger
        )
        observed_ledger = Counter()
        for _item_number, inner in authored_blocks:
            match = re.match(r"\[([^\]]+)\]\s+(.*)", inner, flags=re.DOTALL)
            if match:
                observed_ledger[(match.group(1).strip().casefold(), re.sub(r"\s+", " ", match.group(2)).strip())] += 1
        if observed_ledger != expected_ledger:
            missing = list((expected_ledger - observed_ledger).elements())
            extra = list((observed_ledger - expected_ledger).elements())
            if missing:
                errors.append(f"Planned dialogue ledger lines are missing or changed in chained prompts: {missing}")
            if extra:
                errors.append(f"Chained prompts added dialogue outside the planned ledger: {extra}")

    dialogue_items = _source_dialogue_shot_indices(source_prompt)
    if (voice_performance == "audible" and prompts and len(dialogue_items) == len(source_contracts)
            and _explicit_shot_segments(source_prompt)):
        expected_by_item: dict[int, Counter[str]] = {}
        for item_number, (_language, quote, _internal) in zip(dialogue_items, source_contracts):
            expected_by_item.setdefault(item_number, Counter())[_dialogue_lexical_key(quote)] += 1
        for item_number, item in enumerate(prompts, start=1):
            observed = Counter(item_spoken_keys(item))
            expected = expected_by_item.get(item_number, Counter())
            if observed != expected:
                errors.append(
                    f"Chained prompt item {item_number} must retain its source-authored dialogue occurrences: "
                    f"expected {dict(expected)}, observed {dict(observed)}"
                )

    # Non-spoken quoted text remains exact; punctuation flexibility applies only
    # to dialogue delivery, never to visible titles, signs, or labels.
    source_quotes = Counter(_QUOTED_RE.findall(source_prompt or ""))
    source_visible_quotes = source_quotes - Counter(quote for _language, quote, _internal in source_contracts)
    output_visible_quotes = Counter(
        quote for item in prompts for quote in _QUOTED_RE.findall(item)
        if _dialogue_lexical_key(quote) not in spoken_keys
    )
    missing_visible = list((source_visible_quotes - output_visible_quotes).elements())
    extra_visible = list((output_visible_quotes - source_visible_quotes).elements())
    if missing_visible:
        errors.append(f"Chained prompts omitted or changed exact visible quoted text: {missing_visible}")
    if extra_visible:
        errors.append(f"Chained prompts invented quoted visible text: {extra_visible}")
    return {"valid": not errors, "mode": "chained_multishot", "errors": errors, "warnings": warnings, "promptCount": len(prompts)}


_GRADING_ONLY_PALETTE_PATTERNS = {
    "cold_steel_blue": (
        r"\b(?:steel[- ]?blue|blue|cyan)(?:[- ]biased)?\s+(?:light(?:ing)?|glow|emission|illumination|reflection)s?\b",
    ),
    "sterile_white_cyan": (
        r"\bcyan\s+(?:light(?:ing)?|glow|emission|illumination|reflection|luminous fixture)s?\b",
        r"\bluminous\s+(?:cyan\s+)?fixtures?\b",
    ),
    "neon_cyan_magenta": (
        r"\bneon\s+(?:tube|sign|light|lighting|glow|emission|fixture)s?\b",
        r"\b(?:cyan|magenta|cyan[- ]magenta|colored)\s+(?:light(?:ing)?|glow|emission|illumination|reflection)s?\b",
        r"\b(?:saturated|neon)\s+glow\b",
        r"\bglow(?:ing)?\b",
    ),
}


def _positive_pattern_matches(value: str, pattern: str) -> list[re.Match[str]]:
    """Return positive mentions while ignoring nearby explicit negation."""
    matches = []
    for match in re.finditer(pattern, value or "", flags=re.IGNORECASE):
        prefix = (value or "")[max(0, match.start() - 48):match.start()]
        if re.search(r"\b(?:no|not|without|avoid|forbid|forbids|do not|does not)\b[^.!?;]{0,40}$", prefix, re.IGNORECASE):
            continue
        matches.append(match)
    return matches


def _cinematography_literal_adherence_errors(
    source_prompt: str, output_prompt: str, cinematography: Mapping[str, Any],
) -> list[str]:
    """Catch bounded presentation controls being turned into invented scene lighting.

    This intentionally covers only palettes whose contracts explicitly define them
    as grading/presentation. It is a repair trigger, not an aesthetic quality score.
    """
    palette = str(cinematography.get("colorPalette", "none"))
    patterns = _GRADING_ONLY_PALETTE_PATTERNS.get(palette, ())
    if not patterns:
        return []
    source = source_prompt or ""
    violations = []
    for pattern in patterns:
        output_matches = _positive_pattern_matches(output_prompt, pattern)
        if output_matches and not _positive_pattern_matches(source, pattern):
            violations.extend(match.group(0) for match in output_matches)
    if not violations:
        return []
    observed = ", ".join(repr(item) for item in dict.fromkeys(violations))
    return [
        f"Selected colorPalette={palette} is a grading-only presentation control, but the output invented "
        f"diegetic colored lighting or glow absent from the source ({observed}). Rewrite it as image color "
        "treatment, channel separation, or material color response under the source's existing illumination."
    ]


def _creative_literal_adherence_errors(output_prompt: str, treatment: Mapping[str, Any]) -> list[str]:
    """Prevent internal profile identifiers from leaking into the H3-facing prose."""
    leaked = []
    for profile_id in treatment.get("profileIds", ()):
        axis, _, value = str(profile_id).partition(":")
        patterns = (re.escape(str(profile_id)), rf"\b{re.escape(axis)}\s*:\s*{re.escape(value)}\b")
        if any(re.search(pattern, output_prompt or "", flags=re.IGNORECASE) for pattern in patterns):
            leaked.append(str(profile_id))
    if not leaked:
        return []
    return [
        "The output exposed internal creative profile identifier(s) "
        f"{leaked!r}. Rewrite them as concrete self-contained visual, editorial, performance, and sound prose; "
        "the final H3 prompt must not name selector IDs or control metadata."
    ]


def validate_prompt(prompt: str, mode: str, duration_seconds: float,
                    source_prompt: str = "", reference_context: str = "",
                    ambience_foley_policy: str = "auto",
                    background_score_policy: str = "follow_prompt",
                    voice_performance: str = "audible",
                    aspect_ratio: str = "auto",
                    media_manifest: str = "",
                    multishot_shot_count: int = 0,
                    frame_count: int = 0,
                    multishot_identity_lock: str = "",
                    multishot_voice_lock: str = "",
                    multishot_setting_lock: str = "",
                    authored_dialogue_ledger: tuple[tuple[str, str], ...] = (),
                    creative_treatment_json: str = "",
                    shot_plan_json: str = "",
                    cinematography_json: str = "") -> dict[str, Any]:
    resolved = resolve_mode(mode, reference_context, source_prompt, media_manifest)
    reference_context = "\n".join(
        part for part in (str(reference_context).strip(), manifest_context(media_manifest)) if part
    )
    configuration_errors: list[str] = []
    try:
        selected_creative_treatment = parse_creative_treatment(creative_treatment_json)
    except ValueError as exc:
        configuration_errors.append(str(exc))
        selected_creative_treatment = parse_creative_treatment("")
    try:
        selected_cinematography = parse_cinematography(cinematography_json)
    except ValueError as exc:
        configuration_errors.append(str(exc))
        selected_cinematography = parse_cinematography("")
    profile = generation_profile(duration_seconds, aspect_ratio, frame_count)
    try:
        explicit_shot_plan = parse_shot_plan(
            shot_plan_json, profile["effectiveDurationSeconds"], 0, resolved,
        )
    except ValueError as exc:
        configuration_errors.append(str(exc))
        explicit_shot_plan = parse_shot_plan("", profile["effectiveDurationSeconds"], 0, resolved)
    if resolved == "chained_multishot":
        locks = (multishot_identity_lock, multishot_voice_lock, multishot_setting_lock)
        expected_count = (
            explicit_shot_plan["shotCount"]
            if explicit_shot_plan["provided"] else multishot_shot_count
        )
        if (explicit_shot_plan["provided"] and int(multishot_shot_count or 0)
                and int(multishot_shot_count) != explicit_shot_plan["shotCount"]):
            configuration_errors.append(
                "multishot_shot_count conflicts with the explicit shot_plan_json shot count"
            )
        report = _validate_multishot(
            prompt, profile["effectiveDurationSeconds"], source_prompt, expected_count, locks,
            voice_performance, authored_dialogue_ledger,
        )
        parsed = parse_media_manifest(media_manifest)
        report["errors"].extend(configuration_errors)
        report["errors"].extend(parsed["errors"])
        report["warnings"].extend(parsed["warnings"])
        report["errors"].extend(profile["errors"])
        report["errors"].extend(_cinematography_literal_adherence_errors(
            source_prompt, prompt, selected_cinematography,
        ))
        report["errors"].extend(_creative_literal_adherence_errors(
            prompt, selected_creative_treatment,
        ))
        report["warnings"].extend(profile["warnings"])
        report["valid"] = not report["errors"]
        report["aspectRatio"] = aspect_ratio
        report["generationProfile"] = profile
        report["mediaManifest"] = parsed
        report["shotPlan"] = explicit_shot_plan
        return report
    text = str(prompt).strip()
    errors: list[str] = list(configuration_errors)
    warnings: list[str] = []
    parsed_manifest = parse_media_manifest(media_manifest)
    errors.extend(parsed_manifest["errors"])
    warnings.extend(parsed_manifest["warnings"])
    errors.extend(profile["errors"])
    warnings.extend(profile["warnings"])
    duration_seconds = profile["effectiveDurationSeconds"]
    for item in parsed_manifest["items"]:
        for label in (item.get("label"), item.get("soundtrack_label")):
            if label and label not in text:
                warnings.append(f"Connected reference {label} is not mentioned in the prompt and may bleed into output")
    expected = REFERENCE_SECTIONS if resolved == "ref2va" else BASE_SECTIONS
    observed = tuple(match.group(1) for match in _SECTION_RE.finditer(text))
    if observed != expected:
        errors.append(f"Expected sections in order {expected}, observed {observed}")
    if text.startswith("```") or text.endswith("```"):
        errors.append("Output must not use a Markdown code fence")
    errors.extend(_explicit_source_fact_errors(source_prompt, text))
    errors.extend(_cinematography_literal_adherence_errors(
        source_prompt, text, selected_cinematography,
    ))
    errors.extend(_creative_literal_adherence_errors(text, selected_creative_treatment))

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
        if explicit_shot_plan["provided"] and explicit_shot_plan["timingMode"] == "exact":
            expected_cuts = list(explicit_shot_plan["expectedCutTimesSeconds"])
            # Headers are rendered to milliseconds, so exact boundaries can be
            # checked much more strictly than the one-frame tolerance used for
            # accepting the sum of user-entered shot durations.
            tolerance = 0.0015
            if len(cut_times) == len(expected_cuts):
                mismatches = [
                    (expected, observed)
                    for expected, observed in zip(expected_cuts, cut_times)
                    if abs(expected - observed) > tolerance
                ]
                if mismatches:
                    errors.append(
                        "Explicit shot-plan cut timestamps do not match the exact requested boundaries: "
                        + repr(mismatches)
                    )
    if explicit_shot_plan["provided"] and len(shots) != explicit_shot_plan["shotCount"]:
        errors.append(
            f"Explicit shot_plan_json requires exactly {explicit_shot_plan['shotCount']} shots; "
            f"observed {len(shots)}"
        )
    if (not explicit_shot_plan["provided"]
            and _requires_single_simultaneous_shot(source_prompt, duration_seconds) and len(shots) != 1):
        errors.append("The short simultaneous source requires exactly one continuous shot")
    if (not explicit_shot_plan["provided"]
            and _requires_single_continuous_progression(source_prompt) and len(shots) != 1):
        errors.append("The gradual continuous progression requires exactly one continuous shot")
    required_explicit_shots = _required_explicit_shot_count(source_prompt)
    if required_explicit_shots and len(shots) != required_explicit_shots:
        errors.append(
            f"The source contains mandatory cut commands and requires exactly {required_explicit_shots} shots; "
            f"observed {len(shots)}"
        )
    implicit_limit = None if explicit_shot_plan["provided"] else _implicit_shot_limit(source_prompt)
    if implicit_limit is not None and len(shots) > implicit_limit:
        errors.append(
            f"The source supplied no explicit edit structure; use at most {implicit_limit} shot(s), observed {len(shots)}"
        )
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
    def has_picture(value: str, number: int) -> bool:
        return bool(re.search(rf"<?Picture\s+{number}>?", value, re.IGNORECASE))

    if resolved == "i2va" and not has_picture(timeline, 1):
        errors.append("I2VA Shot 1 must explicitly develop forward from <Picture 1>")
    if resolved == "fl2va":
        if not has_picture(timeline, 1) or not has_picture(timeline, 2):
            errors.append("FL2VA must explicitly connect <Picture 1> to <Picture 2>")
        final_body = timeline[shots[-1].start():] if shots else timeline
        if not has_picture(final_body, 2):
            errors.append("FL2VA must reach <Picture 2> in the final shot")
        if len(shots) > 1 and source_prompt and not _EXPLICIT_CUT_RE.search(source_prompt):
            errors.append("FL2VA should use one continuous shot unless the source explicitly requests edits")
    if resolved == "l2va":
        final_body = timeline[shots[-1].start():] if shots else timeline
        if not has_picture(final_body, 1):
            errors.append("L2VA must converge to <Picture 1> in the final shot")

    if text.count("<d>") != text.count("</d>"):
        errors.append("Dialogue tags are unbalanced")
    if timeline.count("<scenetrans>") % 2:
        errors.append("<scenetrans> must appear at both connecting points when dialogue crosses a cut")
    if "<cutoff>" in timeline:
        last_dialogue_end = timeline.lower().rfind("</d>")
        if last_dialogue_end < 0 or timeline.lower().rfind("<cutoff>") > last_dialogue_end:
            errors.append("<cutoff> must occur inside the final dialogue block truncated by the video ending")
    all_dialogue = re.findall(r"<d>(.*?)</d>", text, flags=re.DOTALL | re.IGNORECASE)
    timeline_dialogue = re.findall(r"<d>(.*?)</d>", timeline, flags=re.DOTALL | re.IGNORECASE)
    for dialogue in all_dialogue:
        if not re.match(r"\[[^\]]+\]\s+\S", dialogue.strip()):
            errors.append("Every <d> block must begin with a language tag and contain dialogue")

    source_contracts = _source_dialogue_contracts(source_prompt)
    contracts = source_contracts if voice_performance == "audible" else []
    dialogue_authoring, dialogue_authoring_language = _dialogue_authoring_request(source_prompt)
    reference_dialogue = manifest_dialogue(media_manifest)

    def dialogue_text(item: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"^\[[^\]]+\]\s*", "", item.strip()))

    dialogue_match_objects = list(re.finditer(r"<d>.*?</d>", timeline, flags=re.DOTALL | re.IGNORECASE))
    internal_remaining = Counter(
        _dialogue_lexical_key(quote) for _language, quote, internal in contracts if internal
    )
    reference_remaining = Counter(
        _dialogue_lexical_key(transcript) for _source, _language, transcript in reference_dialogue
    )
    for dialogue_match in dialogue_match_objects:
        spoken = dialogue_text(re.sub(r"^<d>|</d>$", "", dialogue_match.group(0), flags=re.IGNORECASE))
        spoken_key = _dialogue_lexical_key(spoken)
        if internal_remaining[spoken_key]:
            internal_remaining[spoken_key] -= 1
            continue
        if reference_remaining[spoken_key]:
            reference_remaining[spoken_key] -= 1
            continue
        sentence_start = max(
            timeline.rfind(".", 0, dialogue_match.start()),
            timeline.rfind("!", 0, dialogue_match.start()),
            timeline.rfind("?", 0, dialogue_match.start()),
            timeline.rfind("[Shot", 0, dialogue_match.start()),
        )
        prefix = timeline[(0 if sentence_start < 0 else sentence_start + 1):dialogue_match.start()]
        if re.search(r"says\s+in\s+an\s+off-screen\s+voiceover", prefix, flags=re.IGNORECASE):
            if not re.search(r"\(S\d+\).*?says\s+in\s+an\s+off-screen\s+voiceover", prefix, flags=re.IGNORECASE):
                errors.append("Every authored off-screen voiceover must keep a stable (Sx) ID beside its named source")
            continue
        if not re.search(
            r"\(S\d+(?:\s*,\s*S\d+)*\).*?\b(?:say|says|reply|replies|shout|shouts|whisper|whispers|"
            r"ask|asks|sing|sings|chant|chants|call|calls|exclaim|exclaims|respond|responds|"
            r"boom|booms|repeat|repeats|speak|speaks|explain|explains|narrate|narrates|describe|describes|"
            r"comment|comments|deliver|delivers)\b[^.!?]*$",
            prefix, flags=re.IGNORECASE,
        ):
            errors.append(
                "Visible dialogue must keep a stable (Sx) ID and an explicit vocal action in the same sentence as <d>"
            )
    if contracts and not dialogue_authoring and dialogue_match_objects and float(duration_seconds) >= 8.0:
        post_dialogue = timeline[dialogue_match_objects[-1].end():]
        if len(re.findall(r"\b[\wÀ-ÿ'-]+\b", post_dialogue)) >= 35:
            sound_cues = set(re.findall(
                r"\b(?:hum|crackle|static|whoosh|wind|rain|traffic|footsteps?|rustle|impact|machinery|"
                r"metallic|vibration|room\s+tone|ambience|breathing|panting|strain|fabric|tear|howl|"
                r"clank|grunt|airflow|engine|alarm|buzz)\w*\b",
                post_dialogue + " " + _section_body(text, "overall_soundscape"),
                flags=re.IGNORECASE,
            ))
            if len(sound_cues) < 2:
                errors.append(
                    "A long visual continuation after short dialogue must name at least two concrete non-verbal "
                    "sounds in the remaining timeline"
                )
    untagged_speech = _untagged_speech_actions(timeline) if (contracts or dialogue_authoring) else []
    if untagged_speech:
        errors.append(
            "Affirmative speaking cues outside their exact <d> sentence can create extra dialogue: "
            + repr(untagged_speech)
        )

    normalized_expected = Counter(quote for _language, quote, _internal in contracts)
    normalized_expected.update(text for _source, _language, text in reference_dialogue)
    normalized_timeline = Counter(dialogue_text(item) for item in timeline_dialogue)
    if dialogue_authoring and voice_performance == "audible":
        missing = list((normalized_expected - normalized_timeline).elements())
        if missing:
            errors.append(f"Required spoken dialogue is missing or duplicated incorrectly: {missing}")
        duplicated_required = [
            text
            for text, observed_count in normalized_timeline.items()
            if text in normalized_expected and observed_count > normalized_expected[text]
            for _index in range(observed_count - normalized_expected[text])
        ]
        if duplicated_required:
            errors.append(
                "Required source/reference dialogue was duplicated beyond its authored occurrences: "
                f"{duplicated_required}"
            )
        remaining_expected = normalized_expected.copy()
        authored_blocks = []
        for item in timeline_dialogue:
            spoken = dialogue_text(item)
            if remaining_expected[spoken]:
                remaining_expected[spoken] -= 1
            elif spoken not in normalized_expected:
                authored_blocks.append(item)
        if not authored_blocks:
            errors.append(
                "Explicit dialogue authoring request requires at least one concrete language-tagged <d> line"
            )
        requested_tag = dialogue_authoring_language.casefold()
        wrong_language = []
        placeholders = []
        for item in authored_blocks:
            match = re.match(r"\[([^\]]+)\]\s+(.*)", item.strip(), flags=re.DOTALL)
            if not match:
                continue
            if requested_tag != "original language" and match.group(1).strip().casefold() != requested_tag:
                wrong_language.append(match.group(1).strip())
            words = re.sub(r"\s+", " ", match.group(2)).strip()
            if re.fullmatch(
                r"(?:\[.*?\]|<.*?>|dialogue|dialog|line|speech|spoken words?|concrete authored words|"
                r"to be (?:written|generated)|di[aá]logo|l[ií]nea|frase|palabras)",
                words,
                flags=re.IGNORECASE,
            ):
                placeholders.append(words)
        if wrong_language:
            errors.append(
                f"Explicit dialogue authoring request requires [{dialogue_authoring_language}] on every newly "
                f"authored line; observed {wrong_language}"
            )
        if placeholders:
            errors.append(f"Authored dialogue must contain concrete speakable words, not placeholders: {placeholders}")
        if authored_dialogue_ledger:
            expected_ledger = Counter(
                (language.casefold(), re.sub(r"\s+", " ", text).strip())
                for language, text in authored_dialogue_ledger
            )
            observed_ledger = Counter()
            for item in authored_blocks:
                match = re.match(r"\[([^\]]+)\]\s+(.*)", item.strip(), flags=re.DOTALL)
                if match:
                    observed_ledger[(
                        match.group(1).strip().casefold(),
                        re.sub(r"\s+", " ", match.group(2)).strip(),
                    )] += 1
            if observed_ledger != expected_ledger:
                missing = list((expected_ledger - observed_ledger).elements())
                extra = list((observed_ledger - expected_ledger).elements())
                if missing:
                    errors.append(f"Planned dialogue ledger lines are missing or changed: {missing}")
                if extra:
                    errors.append(f"Dialogue outside the planned ledger is not allowed: {extra}")
    elif normalized_timeline != normalized_expected:
        missing = list((normalized_expected - normalized_timeline).elements())
        extra = list((normalized_timeline - normalized_expected).elements())
        if missing:
            errors.append(f"Required spoken dialogue is missing or duplicated incorrectly: {missing}")
        if extra:
            errors.append(f"Invented or duplicated dialogue is not allowed: {extra}")
    dialogue_shot_indices = _source_dialogue_shot_indices(source_prompt)
    if shots and len(dialogue_shot_indices) == len(contracts) and _required_explicit_shot_count(source_prompt):
        expected_by_shot: dict[int, Counter[str]] = {}
        for shot_number, (_language, quote, _internal) in zip(dialogue_shot_indices, contracts):
            expected_by_shot.setdefault(shot_number, Counter())[quote] += 1
        for index, shot in enumerate(shots):
            shot_number = int(shot.group(1))
            end = shots[index + 1].start() if index + 1 < len(shots) else len(timeline)
            observed_shot_dialogue = Counter(
                dialogue_text(item)
                for item in re.findall(r"<d>(.*?)</d>", timeline[shot.end():end], flags=re.DOTALL | re.IGNORECASE)
            )
            expected_shot_dialogue = expected_by_shot.get(shot_number, Counter())
            if observed_shot_dialogue != expected_shot_dialogue:
                errors.append(
                    f"Required spoken dialogue must remain in its source-authored shot {shot_number}: "
                    f"expected {dict(expected_shot_dialogue)}, observed {dict(observed_shot_dialogue)}"
                )
    if Counter(dialogue_text(item) for item in all_dialogue) != normalized_timeline:
        errors.append("Dialogue blocks must appear only inside the timeline section")

    for source_label, language, transcript in reference_dialogue:
        block = re.search(
            rf"<d>\[{re.escape(language)}\]\s+{re.escape(transcript)}</d>", timeline,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not block:
            continue
        sentence_start = max(
            timeline.rfind(".", 0, block.start()), timeline.rfind("!", 0, block.start()),
            timeline.rfind("?", 0, block.start()), timeline.rfind("[Shot", 0, block.start()),
        )
        prefix = timeline[(0 if sentence_start < 0 else sentence_start + 1):block.start()]
        if source_label.startswith("<Audio") and source_label not in prefix and not re.search(r"\(S\d+", prefix):
            errors.append(f"Reference transcript {transcript!r} must be attributed to {source_label} or a concrete speaker")

    expected_language_blocks = Counter(
        f"[{language}] {quote}" for language, quote, _internal in contracts
        if language != "Original language"
    )
    observed_language_blocks = Counter(re.sub(r"\s+", " ", item.strip()) for item in timeline_dialogue)
    for exact, expected_count in expected_language_blocks.items():
        if observed_language_blocks[exact] != expected_count:
            errors.append(
                f"Dialogue must preserve its requested language marker exactly {expected_count} time(s): {exact!r}"
            )

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
    source_requests_voiceover = (
        _source_requests_offscreen_voice(source_prompt)
        or any(internal for _language, _quote, internal in source_contracts)
    )
    if (re.search(r"\b(?:off-screen voiceover|voice[ -]?over|voz en off)\b", text, re.IGNORECASE)
            and (not source_requests_voiceover or voice_performance != "audible")):
        errors.append("Output invented voiceover although the source requested visible dialogue")
    if source_requests_voiceover and voice_performance == "audible" and not re.search(
        r"says\s+in\s+an\s+off-screen\s+voiceover",
        timeline,
        flags=re.IGNORECASE,
    ):
        errors.append("Requested voiceover must use the exact phrase 'says in an off-screen voiceover' and name its source")
    if re.search(
        r"\b(?:an?\s+(?:(?:unseen|unidentified|anonymous|off-screen)\s+)?voice|"
        r"(?:unseen|unidentified|anonymous|off-screen)\s+voice|voice\s+from\s+off-screen)\s*\(S\d+\)",
        timeline,
        flags=re.IGNORECASE,
    ):
        errors.append(
            "Every off-screen voice must identify its source as a named narrator or referenced Subject, not an unresolved voice"
        )

    music = _section_body(text, "non_diegetic_music").strip()
    if background_score_policy == "off" and music.casefold() != "n/a":
        errors.append("non_diegetic_music must be N/A when background score is off")
    elif (background_score_policy == "follow_prompt"
          and not _source_requests_music((source_prompt or "") + "\n" + (reference_context or ""))
          and music.casefold() != "n/a"):
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
    explicit_total_silence = re.search(
        r"\b(?:complete silence|silent throughout|total silence|silencio total|completamente en silencio)\b",
        source_prompt or "", flags=re.IGNORECASE,
    )
    if soundscape.casefold() == "n/a" and ambience_foley_policy == "auto" and not explicit_total_silence:
        warnings.append("overall_soundscape should be N/A only when the source explicitly requests complete silence")

    def sentence_count(value: str) -> int:
        return len([part for part in re.split(r"(?<=[.!?])\s+", value.strip()) if part.strip()])

    if soundscape.casefold() != "n/a" and not 1 <= sentence_count(soundscape) <= 4:
        warnings.append("overall_soundscape should contain 1-4 English sentences in one paragraph")
    if music.casefold() != "n/a" and not 1 <= sentence_count(music) <= 3:
        warnings.append("non_diegetic_music should contain 1-3 English sentences")
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
        style_opening = detail_text.split("[Shot 1]", 1)[0].strip()
        if not style_opening or not 1 <= sentence_count(style_opening) <= 2:
            warnings.append("Ref2VA detailed_description should establish style in 1-2 English sentences before [Shot 1]")
        definitions = _section_body(text, "subject_definitions")
        output_refs = {item.casefold() for item in _REFERENCE_RE.findall(text)}
        allowed_refs = {item.casefold() for item in (*reference_model["assets"], *reference_model["definition_labels"])}
        invented = sorted(output_refs - allowed_refs)
        if invented:
            errors.append(f"Output invented reference labels not supplied or derived by the contract: {invented}")
        required_refs = {
            item.casefold()
            for item in (*reference_model["definition_labels"], *reference_model["provenance_assets"])
        }
        absent = sorted(required_refs - output_refs)
        if absent:
            errors.append(f"Reference labels missing from output: {absent}")
        for label in sorted(reference_model.get("unassigned_assets", ())):
            if label.casefold() in output_refs:
                warnings.append(
                    f"Unassigned connected reference {label} is mentioned without an authoritative role; "
                    "provide Reference notes or media_manifest metadata before binding it to a Subject"
                )

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
            if label.casefold().startswith("<audio"):
                continue
            if label.casefold() not in detail_text.casefold():
                errors.append(f"Independent reference {label} must be applied inside detailed_description")

        retention = _section_body(text, "retention_analysis")
        if re.search(r"\(S\d+(?:\s*,\s*S\d+)*\)", retention, re.IGNORECASE):
            errors.append("retention_analysis must not contain speaker IDs")
        subject_speakers: dict[str, set[str]] = {}
        speaker_subjects: dict[str, set[str]] = {}
        for subject, speaker in re.findall(
            r"(<Subject\s+\d+>)\s*\((S\d+)\)", detail_text, flags=re.IGNORECASE,
        ):
            subject_speakers.setdefault(subject.casefold(), set()).add(speaker.casefold())
            speaker_subjects.setdefault(speaker.casefold(), set()).add(subject.casefold())
        if any(len(ids) > 1 for ids in subject_speakers.values()):
            errors.append("Each referenced Subject must reuse one stable speaker ID across all vocal events")
        if any(len(subjects) > 1 for subjects in speaker_subjects.values()):
            errors.append("A speaker ID cannot be assigned to multiple referenced Subjects")
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
            allowed = audio_markers if label.casefold().startswith("<audio") or (item and item["kind"] == "audio") else visual_markers
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
        official_prefix = re.match(
            r"\[(?:reference generation|keyframe completion|video editing|video continuation|audio reuse|audio reference)"
            r"(?:\s*\+\s*(?:reference generation|keyframe completion|video editing|video continuation|audio reuse|audio reference))*\]",
            summary,
            flags=re.IGNORECASE,
        )
        if not official_prefix:
            legacy_prefix = re.match(
                r"\[(?:generation|editing|continuation|reference generation|keyframe completion|audio reuse|audio reference)"
                r"(?:\s*/\s*(?:generation|editing|continuation|reference generation|keyframe completion|audio reuse|audio reference))*\]",
                summary, flags=re.IGNORECASE,
            )
            if legacy_prefix:
                warnings.append("Legacy Ref2VA summary task names/separator should be normalized to current names joined by ' + '")
            else:
                errors.append("summary must begin with documented bracketed Ref2VA task type(s)")
        elif re.search(
            r"\[(?:reference generation|keyframe completion|video editing|video continuation|audio reuse|audio reference)\]",
            summary[official_prefix.end():],
            flags=re.IGNORECASE,
        ):
            errors.append("summary must use one canonical bracketed task prefix, not multiple bracket groups")

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
        "aspectRatio": aspect_ratio,
        "mediaManifest": parsed_manifest,
        "generationProfile": profile,
        "shotPlan": explicit_shot_plan,
    }
