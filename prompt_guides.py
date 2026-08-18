# SPDX-License-Identifier: GPL-3.0-only
"""MiniMax H3 prompt construction and validation rules.

The rule set is an original implementation derived from MiniMax's public
T2VA/I2VA/FL2VA/L2VA and full-reference prompt-writing guides.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import json
import hashlib
import re
import unicodedata
from typing import Any

try:
    from .content_formats import content_format_instruction, content_format_signatures, resolve_content_format
    from .creative_treatments import (
        parse_cinematography,
        parse_creative_treatment,
        parse_shot_plan,
        resolved_visual_style_instruction,
        resolve_visual_style,
        resolve_treatment_conflicts,
        shot_plan_instruction,
        title_screen_style_adherence_errors,
        title_screen_style_instruction,
        treatment_warnings,
    )
    from .media_manifest import ASPECT_RATIOS, generation_profile, manifest_context, manifest_dialogue, parse_media_manifest
except ImportError:  # pragma: no cover - direct test/import compatibility
    from content_formats import content_format_instruction, content_format_signatures, resolve_content_format
    from creative_treatments import (
        parse_cinematography,
        parse_creative_treatment,
        parse_shot_plan,
        resolved_visual_style_instruction,
        resolve_visual_style,
        resolve_treatment_conflicts,
        shot_plan_instruction,
        title_screen_style_adherence_errors,
        title_screen_style_instruction,
        treatment_warnings,
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
ENHANCEMENT_PROFILES = ("conservative_grounded", "enhanced_production", "invented_production")
DELIVERY_TARGETS = ("local", "api_v2")
# The official MiniMax API v2 accepts at most 7000 characters per text block.
# Ref2VA's 350-500-word generation range is a soft baseline that expands with
# dialogue, references, and shot complexity; Base mode has no matching minimum.
_API_V2_TEXT_BLOCK_CHARACTER_LIMIT = 7000
_API_V2_TEXT_BLOCK_SOFT_PRESSURE = 6300
_BASE_DESCRIPTION_WORD_WARNING_LIMIT = 600
DIALOGUE_COVERAGE_CHOICES = ("off", "on")
DIALOGUE_COVERAGE_CONTRACT = (
    "Keep each speaking character's mouth and eyes unobstructed and in focus for the full duration of their line, "
    "at medium close-up or tighter, with a stable eyeline."
)
DIALOGUE_LANGUAGE_CHOICES = (
    "auto",
    "Spanish",
    "English",
    "French",
    "German",
    "Italian",
    "Portuguese",
    "Japanese",
    "Chinese",
    "Korean",
    "Russian",
    "Arabic",
    "Cantonese",
    "Catalan",
    "Dutch",
    "Polish",
    "Turkish",
    "Hindi",
)
EDITING_INTENT_CHOICES = (
    "none",
    "character_swap",
    "wardrobe_transfer",
    "voice_dialogue_swap",
    "environment_background",
    "motion_transfer",
    "custom_editing",
)
EDITING_INTENT_CONTRACTS = {
    "character_swap": (
        "EDITING INTENT — CHARACTER / ACTOR SWAP: <Video 1> provides timing, body motion, and camera trajectory. "
        "<Picture 1> (or defined <Subject 1>) provides the new character's facial features and appearance. "
        "In retention_analysis, mark <Video 1> as weak_reference (retain motion and camera, discard original face) "
        "and <Subject 1> as fully_preserved (retain new face, hair, and wardrobe from <Picture 1>). "
        "In summary, declare [video editing + character swap]."
    ),
    "wardrobe_transfer": (
        "EDITING INTENT — WARDROBE / OUTFIT TRANSFER: <Video 1> provides the actor's facial identity, expressions, "
        "and motion. <Picture 1> provides the new outfit, costume, or armor. "
        "In retention_analysis, mark <Video 1> as partially_preserved (keep original face and motion) "
        "and <Picture 1> as attribute_transfer (apply outfit and materials onto character). "
        "In summary, declare [video editing + wardrobe transfer]."
    ),
    "voice_dialogue_swap": (
        "EDITING INTENT — VOICE & DIALOGUE SWAP: Replace the spoken dialogue in <Video 1> with new speech wrapped in "
        "<d>[Language] ...</d> tags. If <Audio 1> is present, set retention_analysis for <Audio 1> to reference "
        "(use exclusively as voice timbre and delivery conditioning for the speaker). "
        "In summary, declare [video editing + audio reference]."
    ),
    "environment_background": (
        "EDITING INTENT — BACKGROUND / ENVIRONMENT REPLACEMENT: Preserve the subject and action from <Video 1> while "
        "replacing the environment or background setting as described in the prompt and reference images. "
        "In retention_analysis, mark <Video 1> as partially_preserved and the new setting reference as attribute_transfer or weak_reference. "
        "In summary, declare [video editing]."
    ),
    "motion_transfer": (
        "EDITING INTENT — MOTION TRANSFER: Use <Video 1> strictly as a motion, timing, and camera trajectory guide. "
        "The subject and environment come from <Picture 1> and the prompt text. "
        "In retention_analysis, mark <Video 1> as weak_reference. "
        "In summary, declare [video editing + motion reference]."
    ),
    "custom_editing": (
        "EDITING INTENT — GENERAL VIDEO EDITING: The generated output is an edited version of <Video 1>. "
        "In summary, declare [video editing] and specify explicit retention_analysis policies for all referenced media."
    ),
}
ACOUSTIC_SPACE_CHOICES = (
    "none",
    "small_reflective_interior",
    "large_reverberant_interior",
    "damped_interior",
    "open_exterior",
    "urban_exterior",
    "underwater_muffled",
)
ACOUSTIC_SPACE_CONTRACTS = {
    "small_reflective_interior": (
        "Render sound in a small hard-surfaced room: short bright early reflections, close mic perspective, footsteps "
        "and object contact clearly localized."
    ),
    "large_reverberant_interior": (
        "Render sound in a large hard-surfaced interior: a long decaying reverb tail, delayed distinct reflections, "
        "voices and impacts arriving with audible distance, and detail softened by the space rather than by filtering."
    ),
    "damped_interior": (
        "Render sound in a soft furnished interior: almost no reverb tail, absorbed high frequencies, intimate close "
        "perspective, and clearly separated nearby physical sounds."
    ),
    "open_exterior": (
        "Render sound as a wide exterior: no reverb tail, distant sounds attenuated and diffuse, wind noise only if "
        "wind is visible."
    ),
    "urban_exterior": (
        "Render sound as a built-up exterior: slap-back reflections from facades, a continuous distant traffic and "
        "city floor, and near sources staying dry and precise against it."
    ),
    "underwater_muffled": (
        "Render sound as heard underwater: strongly attenuated high frequencies, a low pressurized rumble, muffled "
        "and poorly localized distant events, and body-borne movement sounds close and dull."
    ),
}
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
    "science_fiction_electronic",
    "chiptune_16bit",
    "western_frontier",
    "golden_age_studio",
    "retro_1980s_television",
    "latin_melodrama",
    "commercial_minimal",
)
INSTRUMENTAL_STYLE_CATALOG_VERSION = 2
INSTRUMENTAL_PRODUCTION_BIBLE = (
    "INSTRUMENTATION: Preserve every explicitly requested instrument. Assign melody, counterline, harmony, pulse, "
    "bass, and accent roles through the selected musical language; fill a missing role only when necessary and do "
    "not replace a compatible user choice.\n"
    "TEMPO AND METER: Preserve explicit BPM, meter, groove, timing, and entry or exit points. When absent, describe "
    "a concrete pulse or absence of pulse without inventing a scene event.\n"
    "RHYTHM: Tie accents and changes only to events already present; never create impacts, cuts, threats, or climaxes "
    "to justify the score.\n"
    "HARMONY AND TONALITY: State concrete tonal, modal, chromatic, or atonal behavior; do not substitute an abstract "
    "mood or narrative claim.\n"
    "TEXTURE: Define register, density, foreground and supporting layers; keep the arrangement readable instead of "
    "stacking every characteristic instrument.\n"
    "DYNAMICS: Define entry level, development, bounded peak or release, and final level inside the clip; avoid "
    "wall-to-wall maximum intensity.\n"
    "STRUCTURE AND ENDING: Write one continuous cue across the video, with no restart at shot boundaries, and finish "
    "inside the clip unless continuation is explicitly requested.\n"
    "MIX: Keep audience-only music below audible dialogue and reactions, thin or duck voice-band content during "
    "speech, yield transient space to important foley and effects, and retain unclipped headroom.\n"
    "VOICE AND FOLEY RELATION: Instrumental only: no lyrics, singing, speech, chants, choir, or vocal samples. Music "
    "must not replace, duplicate, or invent ambience, foley, reactions, or dialogue.\n"
    "CONTINUITY: Preserve motif, tempo or pulse, tonal center, instrumental roles, timbral palette, and mix perspective "
    "across shots; chained items restate the audible signature without claiming waveform-identical continuity.\n"
    "PROHIBITIONS: Do not invent performers, audible sources, locations, story events, copyrighted melodies, genre "
    "cliches, or synchronization points absent from the request."
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
    "science_fiction_electronic": (
        "Use precise synthetic pulses, evolving spectral layers, controlled sub-bass, spacious register, clear automation, and temporally stable timbres. Do not add alarms, lasers, spaceship hums, braams, threat, or vocal textures."
    ),
    "chiptune_16bit": (
        "Use a limited chip-style voice set, stepped envelopes, compact pulse-and-noise percussion, loop-legible tonal writing, and clear channel separation. Do not add modern supersaws, cinematic orchestra, fake cartridge noise, arcade SFX, or vocals."
    ),
    "western_frontier": (
        "Use sparse plucked strings, restrained acoustic winds or low strings, open intervals, dry spacious rhythm, and measured phrase endings. Do not assume whistles, gunshots, galloping rhythm, saloon piano, heroic duels, or vocals."
    ),
    "golden_age_studio": (
        "Use mid-century studio-orchestral voicing, lyrical thematic phrasing, functional harmony, broad controlled dynamics, and period-compatible recording depth. Do not add modern trailer percussion, synth bass, choir, or exaggerated parody."
    ),
    "retro_1980s_television": (
        "Use a compact broadcast-scale ensemble, warm analogue keyboards, restrained electronic drums, a short memorable motif, and a controlled period-compatible mix. Do not force synthwave arpeggios, neon imagery, arena-scale climax, or vocals."
    ),
    "latin_melodrama": (
        "Use lyrical strings, piano, or a compatible small ensemble, clear harmonic turns, held suspensions, and one bounded revelation cadence. Do not infer nationality, castanets, mariachi, an exaggerated sting, parody, or vocals."
    ),
    "commercial_minimal": (
        "Use a very small instrumental palette, immediate motif, stable pulse, clean frequency separation, and a concise branded-length ending. Do not invent a sonic logo, product claim, celebratory climax, vocals, or advertising copy."
    ),
}


def instrumental_style_signature(style: str) -> str:
    """One exact audible lock; IDs and catalog metadata never enter the H3 prompt."""
    contract = INSTRUMENTAL_STYLE_CONTRACTS.get(str(style), "").strip()
    if not contract:
        return ""
    first = re.split(r"(?<=\.)\s+(?=Do not\b)", contract, maxsplit=1)[0].strip()
    return first


def instrumental_style_digest(style: str) -> str:
    payload = json.dumps({
        "catalogVersion": INSTRUMENTAL_STYLE_CATALOG_VERSION,
        "profileVersion": 1,
        "style": str(style),
        "productionBible": INSTRUMENTAL_PRODUCTION_BIBLE,
        "contract": INSTRUMENTAL_STYLE_CONTRACTS.get(str(style), ""),
        "signature": instrumental_style_signature(style),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
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
    r"\b(image|imagen|picture|foto|video|vídeo|audio|voice|voz)\s*"
    r"(?:number\s*|n[uú]mero\s*|#\s*)?(\d+)\b",
    re.IGNORECASE,
)
_ROLE_REFERENCE_RE = re.compile(
    r"\b(?:the|a|an|el|la|los|las|un|una|al|del)\s+"
    r"([\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,9}?)\s+"
    r"(?:in|en|from|de|que\s+(?:es|aparece\s+en|corresponde\s+a))\s+(?:la\s+|el\s+|the\s+)?"
    r"(image|imagen|picture|foto)\s*(\d+)\b",
    re.IGNORECASE,
)
# A source often names its characters instead of describing them: "Rastas, in image 1, and
# Primo, in image 2". _ROLE_REFERENCE_RE requires a determiner, so those pictures stayed
# unassigned and the writer invented <Subject 2>/<Subject 3> with nothing defining them.
# The name must be capitalized and must not already carry a determiner, which is what keeps
# this from swallowing the noun phrases the determiner pattern already owns.
_NAMED_ROLE_REFERENCE_RE = re.compile(
    r"(?:(?P<determiner>\b(?:the|a|an|el|la|los|las|un|una|al|del)\s+))?"
    r"(?P<name>[A-ZÁÉÍÓÚÑÜ][\wÀ-ÿ'-]*(?:\s+[A-ZÁÉÍÓÚÑÜ][\wÀ-ÿ'-]*){0,2})"
    r"\s*,?\s+(?:in|en|from|de)\s+(?:la\s+|el\s+|the\s+)?(?P<kind>image|imagen|picture|foto)\s*(?P<number>\d+)\b",
)

_COORDINATED_ROLE_REFERENCE_RE = re.compile(
    r"\b(?:the|a|an|el|la|los|las|un|una)\s+"
    r"([\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,4}?)\s+(?:and|y)\s+"
    r"(?:the|a|an|el|la|los|las|un|una)\s+"
    r"([\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,4}?)\s+"
    r"(?:in|en|from|de)\s+(image|imagen|picture|foto)\s*(\d+)\b",
    re.IGNORECASE,
)
_ROLE_AFTER_REFERENCE_RE = re.compile(
    r"\b(?:in|en|from|de)\s+(?:the\s+|la\s+|el\s+)?(image|imagen|picture|foto)\s*(?:number\s*|n[uú]mero\s*|#\s*)?(\d+)\s*"
    r"(?:,\s*)?(?:aparece\s+|hay\s+|is\s+|there\s+is\s+|we\s+see\s+|vemos\s+|tenemos\s+|stands?\s+|sits?\s+)?"
    r"(?:the|a|an|el|la|los|las|un|una)\s+([\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){0,9}?)(?=[,;.!\n]|(?:\s+(?:with|con|in|en|who|que|y|and)\b))",
    re.IGNORECASE,
)
_QUOTED_RE = re.compile(
    r'(?:(?<![\wÀ-ÿ])["“]([^"”\r\n]+)["”]|«([^»\r\n]+)»|„([^“”"\r\n]+)[“”"]|「([^」\r\n]+)」|『([^』\r\n]+)』|["“]([^"”\r\n]+)["”])'
)
# Source prose occasionally arrives with a stray closing straight quote (for
# example ``when he says his phrase", ... says "Hello"``). Pairing every quote
# by alternation turns the intervening scene directions into dialogue and also
# shifts all later, valid quotations. For source dialogue extraction require
# an opening straight quote to begin at a token boundary. Unambiguous quotes
# («...», “...”, „...“, 「...」, 『...』) match directly across European/Asian scripts.
_SOURCE_QUOTED_RE = re.compile(
    r'(?:(?<![\wÀ-ÿ])["“]([^"”\r\n]+)["”]|«([^»\r\n]+)»|„([^“”"\r\n]+)[“”"]|「([^」\r\n]+)」|『([^』\r\n]+)』)'
)


def _extract_quote_string(match: re.Match[str]) -> str:
    """Return the first matched non-None group from multi-quote alternations."""
    return next((g for g in match.groups() if g is not None), "").strip()


def _extract_source_quotes(text: str) -> list[str]:
    """Extract all quoted string contents from text using _SOURCE_QUOTED_RE."""
    results = []
    for match in _SOURCE_QUOTED_RE.finditer(text or ""):
        s = _extract_quote_string(match)
        if s:
            results.append(s)
    return results


def _extract_output_quotes(text: str) -> list[str]:
    """Extract all quoted string contents from text using _QUOTED_RE."""
    results = []
    for match in _QUOTED_RE.finditer(text or ""):
        s = _extract_quote_string(match)
        if s:
            results.append(s)
    return results


_INTERNAL_MONOLOGUE_CUE_RE = re.compile(
    r"\b(?:think|thinks|thinking|thought|inner\s+monologue|internal\s+monologue|"
    r"piensa|piensan|pensando|pensamiento|mon[oó]logo\s+interno|reflexiona|reflexionan|reflexionando|"
    r"pense|pensait|pensent|pensant|monologue\s+int[eé]rieur|"
    r"denkt|dachte|dachten|denkend|innerer\s+monolog|"
    r"pensava|pensam|pensamento|mon[oó]logo\s+interior)\b",
    re.IGNORECASE,
)
_SPEECH_CUE_RE = re.compile(
    r"\b(?:say|says|said|saying|state|states|stated|stating|ask|asks|asked|asking|shout|shouts|shouted|shouting|"
    r"reply|replies|replied|replying|respond|responds|responded|responding|finish(?:es|ed|ing)?\s+with|sing|sings|sang|singing|chant|chants|chanted|chanting|"
    r"call|calls|called|calling|exclaim|exclaims|exclaimed|exclaiming|whisper|whispers|whispered|whispering|speak|speaks|spoke|spoken|speaking|"
    r"explain|explains|explained|explaining|narrate|narrates|narrated|narrating|describe|describes|described|describing|comment|comments|commented|commenting|"
    r"tell|tells|told|telling|hear|hears|heard|hearing|is\s+heard|are\s+heard|was\s+heard|were\s+heard|sound|sounds|sounding|sounded|boom|booms|boomed|booming|voice|voices|"
    r"dice|dicen|dijo|dijeron|diciendo|responde|responden|respondi[oó]|respondieron|respondiendo|contest[ao]|contestan|contest[oó]|contestaron|contestando|"
    r"canta|cantan|cant[oó]|cantaron|cantando|pregunta|preguntan|pregunt[oó]|preguntaron|preguntando|"
    r"grita|gritan|grit[oó]|gritaron|gritando|susurra|susurran|susurr[oó]|susurraron|susurrando|"
    r"habla|hablan|habl[oó]|hablaron|hablando|explica|explican|explic[oó]|explicaron|explicando|"
    r"narra|narran|narr[oó]|narraron|narrando|describe|describen|describi[oó]|describieron|describiendo|"
    r"comenta|comentan|coment[oó]|comentaron|comentando|cuenta|cuentan|cont[oó]|contaron|contando|"
    r"dit|disent|disait|disant|parle|parlent|parlait|parlant|demande|demandent|demandait|demandant|répond|repond|répondent|repondent|répondait|repondait|répondant|repondant|crie|crient|criait|criant|chuchote|chuchotent|chuchotait|chuchotant|"
    r"sagt|sagte|sagten|sagend|spricht|sprechen|sprach|sprachen|sprechend|fragt|fragte|fragten|fragend|antwortet|antwortete|antworteten|antwortend|schreit|schrie|schrien|schreiend|flüstert|flüsterte|flüsterten|flüsternd|"
    r"diz|dizem|disse|disseram|dizendo|fala|falam|falou|falaram|falando|pergunta|perguntam|perguntou|perguntaram|perguntando|responde|respondem|respondeu|responderam|respondendo|grita|gritam|gritou|gritaram|gritando|sussurra|sussurram|sussurrou|sussurraram|sussurrando|"
    r"diu|diuen|va\s+dir|dient|parla|parlen|parlant|crida|criden|cridant|xiuxiueja|xiuxiuegen|xiuxiuejant|"
    r"zegt|zeggen|zei|zeiden|zeggend|spreekt|spreken|sprak|spraken|sprekend|vraagt|vragen|vroeg|vroegen|antwoordt|antwoorden|antwoordde|antwoordden|roept|roepen|riep|riepen|fluistert|fluisteren|fluisterde|fluisterden|"
    r"piensa|piensan|pensando|pensamiento|mon[oó]logo|reflexiona|reflexionan|reflexionando|oye|oyen|o[ií]r|escucha|escuchan)\b|"
    r"(?:言う|言った|叫ぶ|呟く|話す|答える|と語る|と叫ぶ|と言う|说|道|喊|大喊|喊道|叫道|呼喊|低语|回答|问道|讲述|解释)",
    re.IGNORECASE,
)
_UNTAGGED_SPEECH_ACTION_RE = re.compile(
    r"\b(?:speaks?|speaking|talks?|talking|says?|saying|asks?|asking|repl(?:y|ies|ying)|"
    r"responds?|repeats?|repeating|sing(?:s|ing)?|chants?|exclaims?|booms?|booming|utters?|uttering|"
    r"explains?|explaining|narrates?|narrating|describes?|describing|comments?|commenting|"
    r"continues?\s+(?:to\s+)?(?:speak|talk)|finishes?\s+(?:speaking|talking)|"
    r"delivers?\s+(?:(?:his|her|their|the|required)\s+)?(?:line|dialogue|words?)|"
    r"dice|dicen|habla|hablan|explica|explican|narra|narran|grita|gritan|susurra|susurran|"
    r"dit|disent|parle|parlent|demande|demandent|sagt|sagte|spricht|sprechen|diz|dizem|fala|falam|"
    r"diu|diuen|crida|criden)\b",
    re.IGNORECASE,
)
_VISIBLE_TEXT_RE = re.compile(
    r"\b(?:sign|title\s+card|caption|subtitle|shirt|t-shirt|screen|label|poster|placard|book|page|cover|"
    r"door|wall|window|board|billboard|banner|card|paper|note|badge|tag|box|hammer|weapon|object|"
    r"vehicle|car|boat|plane|building|shop|bar|store|storefront|entrance|facade|package|can|bottle|cup|"
    r"header|heading|intertitle|display|overlay|"
    r"letrero|cartel|t[ií]tulo|tarjeta|subt[ií]tulo|camiseta|pantalla|etiqueta|p[oó]ster|placa|libro|"
    r"p[aá]gina|portada|puerta|pared|muro|ventana|pizarra|valla|pancarta|papel|nota|chapa|caja|martillo|"
    r"arma|objeto|veh[ií]culo|coche|edificio|tienda|bar|fachada|paquete|lata|botella|vaso|cabecera|"
    r"intert[ií]tulo|r[oó]tulo)\b[^\r\n.!?;]{0,80}"
    r"\b(?:reads?|reading|says?|saying|shows?|showing|displays?|displaying|written|inscribed|engraved|"
    r"printed|painted|marked|labeled|spelling|spells?|spelled|"
    r"dice|diciendo|reza|rezando|muestra|mostrando|pone|poniendo|escrito|grabado|impreso|pintado|marcado|etiquetado)\s*$",
    re.IGNORECASE,
)


def _is_visible_text_quote(source_prompt: str, match: re.Match[str]) -> bool:
    """Return true when a quoted string represents on-screen visual text rather than spoken dialogue."""
    source = source_prompt or ""
    prefix = source[:match.start()]
    boundary = max([prefix.rfind(mark) for mark in ".!?;\n\"”»“„」"] + [-1])
    cue_window = prefix[boundary + 1:]
    trailing_candidates = [i for i in [source.find(mark, match.end()) for mark in ".!?;\n\"”»“„」"] if i != -1]
    trailing_boundary = min(trailing_candidates) if trailing_candidates else len(source)
    trailing_window = source[match.end():trailing_boundary]
    if _VISIBLE_TEXT_RE.search(cue_window):
        return True
    if re.search(
        r"\b(?:written|printed|painted|marked|inscribed|labeled|escrito|impreso|pintado|marcado)\s+(?:on|in|en)\b",
        cue_window, re.IGNORECASE,
    ):
        return True
    if re.search(
        r"^\s*(?:written|printed|painted|marked|inscribed|labeled|escrito|impreso|pintado|marcado)\s+(?:on|in|en)\b",
        trailing_window, re.IGNORECASE,
    ):
        return True
    return False


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
# A continuation take inherits whatever was still moving when the previous take ended. These are
# the phrasings users write when the new prompt must extend an existing clip instead of opening a
# fresh scene; only then is an opening completion verb suspicious.
_CONTINUATION_CONTEXT_RE = re.compile(
    r"\bcontinu(?:e|es|ing)\s+(?:seamlessly|directly|smoothly|exactly)?\s*from\b|"
    r"\bcontinu(?:e|es|ing)\s+(?:seamlessly|directly|smoothly)\b|"
    r"\bcontinuation\b|"
    r"\b(?:preceding|previous|prior|earlier|last)\s+(?:take|shot|clip|video|segment)\b|"
    r"\bsupplied\s+by\s+the\s+(?:preceding|previous|prior)\b|"
    r"\bsame\s+[^.\n]{0,60}?\bpositions\s+supplied\b|"
    r"\bextend(?:s|ing)?\s+the\s+(?:take|shot|clip|video)\b|"
    r"\bpicks?\s+up\s+(?:exactly\s+)?where\b|"
    r"\bcontinuaci[oó]n\b|\btoma\s+anterior\b",
    re.IGNORECASE,
)
# Completion/settling verbs attached to an open noun phrase. The noun side stays deliberately
# unenumerated: any scene element can carry an inherited transient. The trailing marker (a
# determiner, an -ly adverb, a directional word, or clause-final punctuation) keeps nominal uses
# such as "a matte finish on the bar" out.
_TRANSIENT_COMPLETION_RE = re.compile(
    r"\b(?:the|its|their|his|her|a|an|both)\s+(?:[\w-]+\s+){0,3}"
    r"(?:finish(?:es|ing)?|settl(?:e|es|ing)|complet(?:e|es|ing)|"
    r"stop(?:s|ping)?\s+(?:moving|swinging|swaying|rocking|spinning|rotating|sliding|falling)|"
    r"clos(?:e|es|ing)\s+(?:fully|completely|shut)|"
    r"com(?:e|es|ing)\s+to\s+(?:a\s+)?(?:rest|stop|standstill|halt))"
    r"(?:\s+(?:the|a|an|its|their|his|her|into|onto|back|behind|against|down|shut|closed|flush)\b|"
    r"\s+\w+ly\b|(?=\s*[,.;]))"
    r"(?:\s+[\w-]+){0,3}",
    re.IGNORECASE,
)
# Roughly the first second of a single-shot timeline: long enough to hold the opening beat, short
# enough that a transient completing late in the shot is not flagged.
_CONTINUATION_OPENING_CHARACTERS = 350
# Continuity phrasings that must accompany a <scenetrans> pair. The official guide lists four
# phrases as examples of how continuity "may be expressed", so natural variants of the same four
# families are accepted; stating continuity at all stays mandatory. Plural subjects ("her words
# continue seamlessly...") conjugate the same phrases, so the verb number is free.
_SCENETRANS_CONTINUITY_RE = re.compile(
    r"continues?\s+(?:seamlessly\s+)?across\s+the\s+(?:cut|transition)|"
    r"continues?\s+uninterrupted(?:\s+into\s+the\s+next\s+shot)?|"
    r"(?:carries|carry|carrying)\s+over(?:\s+from\s+the\s+previous\s+shot)?|"
    r"remains?\s+audible\s+(?:across|through|throughout)\s+the\s+(?:cut|transition)|"
    r"without\s+interruption\s+across\s+the\s+(?:cut|transition)",
    re.IGNORECASE,
)
# H3 documents stable dialogue for Arabic, Chinese, English, French, German, Italian, Japanese,
# Korean, Portuguese, Russian, and Spanish. Only endonyms and variants whose .capitalize() would
# not already produce the canonical <d>[Language] name need an entry. Cantonese stays Cantonese:
# folding it into Chinese would silently change the spoken language the user asked for.
_LANGUAGE_ALIASES = {
    "catalonian": "Catalan",
    "catalan": "Catalan",
    "catalán": "Catalan",
    "catala": "Catalan",
    "català": "Catalan",
    "valencian": "Catalan",
    "valenciano": "Catalan",
    "valencià": "Catalan",
    "valencia": "Catalan",
    "castilian": "Spanish",
    "castellano": "Spanish",
    "español": "Spanish",
    "espanol": "Spanish",
    "español de españa": "Spanish",
    "espanol de espana": "Spanish",
    "español latino": "Spanish",
    "espanol latino": "Spanish",
    "español de américa": "Spanish",
    "español de america": "Spanish",
    "español neutro": "Spanish",
    "espanol neutro": "Spanish",
    "español de méxico": "Spanish",
    "espanol de mexico": "Spanish",
    "castellano de españa": "Spanish",
    "castellano de espana": "Spanish",
    "latin spanish": "Spanish",
    "latam spanish": "Spanish",
    "mexican spanish": "Spanish",
    "peninsular spanish": "Spanish",
    "français": "French",
    "francais": "French",
    "quebecois": "French",
    "québécois": "French",
    "canadian french": "French",
    "français canadien": "French",
    "francais canadien": "French",
    "deutsch": "German",
    "austrian german": "German",
    "swiss german": "German",
    "schweizerdeutsch": "German",
    "italiano": "Italian",
    "português brasileiro": "Portuguese",
    "portugues brasileiro": "Portuguese",
    "brazilian portuguese": "Portuguese",
    "português do brasil": "Portuguese",
    "portugues do brasil": "Portuguese",
    "português": "Portuguese",
    "portugues": "Portuguese",
    "brasileiro": "Portuguese",
    "nihongo": "Japanese",
    "日本語": "Japanese",
    "hangugeo": "Korean",
    "한국어": "Korean",
    "mandarin": "Chinese",
    "mandarin chinese": "Chinese",
    "standard chinese": "Chinese",
    "simplified chinese": "Chinese",
    "traditional chinese": "Chinese",
    "putonghua": "Chinese",
    "guoyu": "Chinese",
    "中文": "Chinese",
    "汉语": "Chinese",
    "普通话": "Chinese",
    "yue": "Cantonese",
    "粤语": "Cantonese",
    "廣東話": "Cantonese",
    "cantonés": "Cantonese",
    "cantones": "Cantonese",
    "guangdonghua": "Cantonese",
    "russkiy": "Russian",
    "русский": "Russian",
    "العربية": "Arabic",
    "hindi": "Hindi",
    "dutch": "Dutch",
    "flemish": "Dutch",
    "vlaams": "Dutch",
    "flamenco": "Dutch",
    "holandés": "Dutch",
    "holandes": "Dutch",
    "nederlands": "Dutch",
    "polish": "Polish",
    "polski": "Polish",
    "turkish": "Turkish",
    "türkçe": "Turkish",
    "turkce": "Turkish",
    "vietnamese": "Vietnamese",
    "tiếng việt": "Vietnamese",
    "tieng viet": "Vietnamese",
}
# Spaced scripts (Latin, Cyrillic, Arabic) keep letter boundaries; CJK and Hangul aliases are
# written without separators and agglutinate particles, so \b-style assertions never hold there.
_SPACED_DIALOGUE_LANGUAGES = (
    "english", "spanish", "french", "german", "italian", "portuguese", "japanese", "korean",
    "chinese", "cantonese", "russian", "arabic", "hindi", "dutch", "polish", "turkish", "vietnamese",
    "catalonian", "catalan", "catalán", "català", "catala", "valencian", "valenciano", "valencià", "valencia",
    "español", "espanol", "castilian", "castellano",
    "español de españa", "espanol de espana", "español latino", "espanol latino",
    "español de américa", "español de america", "español neutro", "espanol neutro",
    "español de méxico", "espanol de mexico", "castellano de españa", "castellano de espana",
    "latin spanish", "latam spanish", "mexican spanish", "peninsular spanish",
    "français", "francais", "quebecois", "québécois", "canadian french", "français canadien", "francais canadien",
    "deutsch", "austrian german", "swiss german", "schweizerdeutsch", "italiano",
    "português brasileiro", "portugues brasileiro", "brazilian portuguese", "português do brasil", "portugues do brasil",
    "português", "portugues", "nihongo", "hangugeo", "putonghua", "guoyu",
    "mandarin chinese", "standard chinese", "simplified chinese", "traditional chinese",
    "yue", "cantonés", "cantones", "guangdonghua",
    "flemish", "vlaams", "flamenco", "holandés", "holandes", "nederlands", "polski", "türkçe", "turkce",
    "tiếng việt", "tieng viet", "russkiy", "русский", "العربية",
)
_UNSPACED_DIALOGUE_LANGUAGES = ("日本語", "한국어", "普通话", "汉语", "中文", "粤语", "廣東話")
# "mandarin" also names a collar, a jacket, a duck and a fruit, and bare "brasileiro" is an
# ordinary demonym, so neither may sit in the plain alternation: "dressed in mandarin collar"
# used to tag English dialogue as [Chinese].  "mandarin" keeps a guarded alternative below;
# "brasileiro" survives only inside its "português brasileiro" forms.  Both stay in
# _LANGUAGE_ALIASES so an explicitly named language still resolves to its canonical tag.
_MANDARIN_LANGUAGE_SENSE = r"mandarin(?!\s+(?:collars?|jackets?|dress|gown|robe|duck|oranges?))"


def _language_alternation(names: tuple[str, ...]) -> str:
    parts = [re.escape(name) for name in sorted(names, key=len, reverse=True) if name]
    assert parts, "language alternation must not be empty: an empty branch matches everywhere"
    return "|".join(parts)


# The group carries its own boundaries, so call sites must not wrap it in \b.
_DIALOGUE_LANGUAGE_PATTERN = (
    r"(?<![^\W\d_])(?:" + _language_alternation(_SPACED_DIALOGUE_LANGUAGES)
    + r"|" + _MANDARIN_LANGUAGE_SENSE + r")(?![^\W\d_])|"
    + _language_alternation(_UNSPACED_DIALOGUE_LANGUAGES)
)
# A language may be qualified by its regional variety.  H3's tag still wants the
# canonical language (for example [Spanish]), while delivery prose may retain the
# variety ("Spain's Spanish", "British English", "Canadian French", etc.).
# Keep the prefix deliberately constrained: accepting arbitrary adjectives here
# would misread scene descriptions such as "in a Spanish tavern" as dialogue cues.
_DIALOGUE_VARIETY_PREFIX_PATTERN = (
    r"(?:[\wÀ-ÿ-]+(?:['’]s)|Spain|European|Peninsular|Latin(?:[ -]American)?|Mexican|Argentinian|"
    r"Colombian|British|American|US|U\.S\.|UK|U\.K\.|Australian|Canadian|Irish|Scottish|Indian|"
    r"Metropolitan|Quebec|Québécois|Belgian|Swiss|Brazilian|Portugal|Austrian|Modern Standard|"
    r"Egyptian|Levantine|Gulf)"
)
_QUALIFIED_DIALOGUE_LANGUAGE_PATTERN = (
    rf"(?:{_DIALOGUE_VARIETY_PREFIX_PATTERN}\s+){{1,2}}({_DIALOGUE_LANGUAGE_PATTERN})"
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

_LANGUAGE_KEYWORDS = {
    "Spanish": {
        "chars": set("¿¡ñáéíóú"),
        "words": {
            "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "en", "y", "que", "por", "para", "con",
            "como", "su", "sus", "al", "se", "es", "son", "dice", "dicen", "dijo", "dijeron", "habla", "hablan", "explica", "explican",
            "narra", "narran", "grita", "gritan", "susurra", "susurran", "hola", "adiós", "buenos", "días", "tarde", "noche",
            "amigo", "amiga", "caballero", "plano", "secuencia", "cámara", "vídeo", "video", "escena", "personaje", "pero",
            "más", "aquí", "ahora", "todo", "todos", "toda", "todas", "esta", "este", "estos", "estas", "está", "están", "vamos", "tenemos",
            "puedo", "quiero", "tenéis", "queréis", "venceremos", "moriremos", "pasará", "pasarás", "nadie", "quien", "quién",
            "anda", "ahí", "ahi", "socorro", "ayudadme", "policías", "policias", "alto", "disparo", "queda", "quedan", "tiempo",
            "nos", "nosotros", "vosotros", "ellos", "ellas", "casa", "tierra", "fuego", "agua", "espada", "rey", "vida", "muerte",
            "amor", "mundo", "hombre", "mujer", "chico", "chica", "niño", "niña", "siempre", "nunca", "nada", "algo", "alguien",
            "bueno", "buena", "bien", "mal", "tranquilo", "tranquila", "estás", "cabrones", "asesino", "cargadores"
        }
    },
    "French": {
        "chars": set("çœæàèùéêëîïôû"),
        "words": {
            "le", "la", "les", "un", "une", "des", "du", "dans", "en", "sur", "avec", "pour", "qui", "que", "est", "sont",
            "dit", "disent", "parle", "parlent", "bonjour", "merci", "oui", "non", "ici", "tout", "tous", "plan", "séquence",
            "caméra", "vidéo", "homme", "femme", "nous", "vous", "ils", "elles", "au", "aux", "monde", "temps", "chambre",
            "vie", "mort", "ami", "amie", "chose", "bien", "très", "ne", "pas", "plus", "ce", "cette", "ces", "mon", "ma",
            "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur", "leurs", "faire", "fait",
            "va", "vont", "bon", "bonne", "police", "arrive", "bougez", "arrêtez", "regarde", "regardez", "voici", "voilà",
            "pourquoi", "comment", "quand", "où", "jamais", "rien", "personne"
        }
    },
    "German": {
        "chars": set("äöüß"),
        "words": {
            "der", "die", "das", "dem", "den", "des", "ein", "eine", "einen", "einem", "einer", "und", "in", "von", "mit",
            "für", "auf", "ist", "sind", "nicht", "sagt", "sagte", "sagten", "spricht", "sprach", "hallo", "danke", "guten", "tag",
            "morgen", "abend", "wir", "ihr", "sie", "es", "video", "kamera", "mann", "frau", "mein", "freund", "zeit",
            "welt", "leben", "tod", "hier", "jetzt", "gut", "sehr", "bleiben", "stehen", "kommen", "kommt", "bitte", "ja",
            "nein", "kein", "keine", "alles", "immer", "nie"
        }
    },
    "Italian": {
        "chars": set("àèéìòù"),
        "words": {
            "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "in", "con", "su", "per", "tra", "fra", "di", "da",
            "del", "dello", "della", "dei", "degli", "delle", "che", "è", "sono", "dice", "dicono", "disse", "parla", "parlano",
            "ciao", "grazie", "buongiorno", "arrivederci", "andiamo", "piano", "sequenza", "video", "uomo", "donna", "tutto",
            "tutti", "subito", "tempo", "mondo", "amico", "amica", "casa", "vita", "morte", "bene", "molto", "questo", "questa",
            "qui", "qua", "non", "più", "sempre", "mai", "niente"
        }
    },
    "Portuguese": {
        "chars": set("ãõçáéíóúâêô"),
        "words": {
            "o", "a", "os", "as", "um", "uma", "uns", "umas", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
            "com", "para", "que", "é", "são", "diz", "dizem", "disse", "fala", "falam", "olá", "obrigado", "obrigada", "bom", "dia",
            "boa", "noite", "vamos", "plano", "sequência", "vídeo", "homem", "mulher", "tudo", "todos", "amigo", "amiga",
            "tempo", "vida", "morte", "aqui", "agora", "bem", "muito", "este", "esta", "não", "mais", "sempre", "nunca", "nada"
        }
    },
    "Catalan": {
        "chars": set("àçèéíòóúïü"),
        "words": {
            "el", "la", "els", "les", "un", "una", "uns", "unes", "en", "amb", "per", "que", "és", "són", "diu", "diuen",
            "va", "parla", "parlen", "hola", "gràcies", "adeu", "flaó", "aquest", "aquesta", "aquests", "aquestes", "pla",
            "seqüència", "vídeo", "home", "dona", "tot", "tots", "totes", "cabrons", "aqui", "ara", "més", "molt", "ben",
            "sempre", "mai", "res"
        }
    },
    "English": {
        "chars": set(),
        "words": {
            "the", "a", "an", "and", "in", "on", "at", "of", "to", "for", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "says", "said", "speaks", "spoke", "explains", "narrates", "shouts", "whispers", "shot", "camera",
            "video", "scene", "character", "man", "woman", "we", "they", "this", "that", "these", "those", "pilot", "target",
            "acquired", "world", "time", "friend", "life", "death", "here", "now", "well", "very", "first", "batch", "no",
            "music", "score", "sound", "sounds", "audio", "open", "opens", "door", "walk", "walks", "enter", "enters",
            "looking", "looks", "good", "morning", "evening", "night", "hello", "proceed", "stop", "move", "fine"
        }
    }
}


# High-frequency conversational vocabulary. A <d> line is short, so detection rests on a
# handful of tokens: any language missing its everyday verbs and pronouns loses to a neighbour
# that has them. Shared entries are fine — _language_marker_index discounts them automatically.
_LANGUAGE_KEYWORDS_EXTRA = {
    "Spanish": {
        "no", "sí", "si", "me", "te", "lo", "le", "les", "mi", "tu", "muy", "porque", "cuando",
        "donde", "dónde", "cómo", "qué", "pienso", "piensa", "decir", "digo", "dije", "dices",
        "hacer", "hago", "tengo", "tiene", "tienes", "eres", "soy", "estoy", "estaba", "esperaba",
        "quiero", "quieres", "puedo", "puedes", "hablar", "hablo", "contigo", "conmigo", "déjame",
        "dejame", "paz", "eso", "esa", "ese", "esto", "allí", "alli", "ya", "aún", "aun", "sé",
        "sabes", "vas", "voy", "vino", "hay", "había", "habia", "fue", "era", "sin", "sobre",
        "también", "tambien", "entonces", "ahora", "luego", "otra", "otro", "mismo", "mejor",
    },
    "Portuguese": {
        "não", "nao", "sim", "eu", "você", "voce", "vou", "vai", "dizer", "digo", "disse",
        "sei", "sabe", "onde", "esteve", "estou", "está", "esta", "estava", "tenho", "tem",
        "quero", "quer", "posso", "pode", "falar", "comigo", "contigo", "isso", "isto", "aquilo",
        "ainda", "então", "entao", "depois", "antes", "muito", "porque", "quando", "como",
        "embora", "consigo", "mesmo", "melhor", "sobre", "sem", "foi", "era", "havia",
    },
    "Italian": {
        "niente", "dire", "dico", "detto", "dove", "stato", "stata", "quella", "quello", "notte",
        "sembra", "voglio", "vuoi", "posso", "puoi", "parlare", "sono", "sei", "siamo", "ho",
        "hai", "abbiamo", "adesso", "ancora", "allora", "dopo", "prima", "perché", "perche",
        "quando", "come", "cosa", "anche", "stesso", "meglio", "senza", "era", "stato",
    },
    "Catalan": {
        "res", "amb", "vaig", "vas", "nit", "pense", "penso", "dir", "dic", "fer", "faig",
        "tinc", "tens", "vull", "vols", "puc", "pots", "parlar", "estic", "estàs", "estas",
        "això", "aixo", "aquell", "aquella", "encara", "llavors", "després", "despres",
        "abans", "perquè", "perque", "quan", "com", "també", "tambe", "millor", "sense",
    },
    "French": {
        "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "rien", "sais", "sait",
        "dire", "dis", "dirai", "veux", "veut", "peux", "peut", "parler", "suis", "était",
        "etait", "etais", "étais", "encore", "alors", "après", "apres", "avant", "pourquoi",
        "quand", "comment", "aussi", "même", "meme", "mieux", "sans", "chose", "nuit",
    },
    "English": {
        "not", "know", "knew", "where", "were", "night", "saying", "anything", "nothing",
        "something", "there", "here", "then", "than", "when", "what", "who", "why", "how",
        "want", "wants", "can", "cannot", "will", "would", "could", "should", "have", "has",
        "had", "does", "did", "doing", "going", "about", "again", "still", "just", "because",
        "talk", "talking", "tell", "told", "look", "looks", "make", "made", "come", "came",
    },
}

for _language, _extra in _LANGUAGE_KEYWORDS_EXTRA.items():
    if _language in _LANGUAGE_KEYWORDS:
        _LANGUAGE_KEYWORDS[_language]["words"] = set(
            _LANGUAGE_KEYWORDS[_language]["words"]
        ) | _extra


# Word endings that belong to one Romance language where its neighbours use another form:
# -ción/-ção/-ció/-tion/-zione, -ico/-ic/-ique, -mente vs -ment. These decide cases where every
# function word in the line is shared.
_LANGUAGE_SUFFIXES = (
    (r"\w+ción\b", "Spanish"),
    (r"\w+dad\b", "Spanish"),
    (r"\w+ico\b", "Spanish"),
    (r"\w+ção\b", "Portuguese"),
    (r"\w+ções\b", "Portuguese"),
    (r"\w+ade\b", "Portuguese"),
    (r"\w+inho\b", "Portuguese"),
    (r"\w+ció\b", "Catalan"),
    (r"\w+tat\b", "Catalan"),
    (r"\w+ic\b", "Catalan"),
    (r"\w+ntica\b", "Catalan"),
    (r"\w+tion\b", "French"),
    (r"\w+ique\b", "French"),
    (r"\w+eux\b", "French"),
    (r"\w+zione\b", "Italian"),
    (r"\w+ità\b", "Italian"),
    (r"\w+etto\b", "Italian"),
)

# Deterministic tie-break for lines whose every marker is shared between close neighbours.
_LANGUAGE_TIE_ORDER = (
    "Spanish", "English", "Portuguese", "French", "Italian", "German", "Catalan",
)

_LANGUAGE_MARKER_INDEX: tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]] | None = None


def _language_marker_index() -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    """Invert the keyword tables into marker -> languages, so shared markers can be discounted."""
    global _LANGUAGE_MARKER_INDEX
    if _LANGUAGE_MARKER_INDEX is not None:
        return _LANGUAGE_MARKER_INDEX
    words: dict[str, list[str]] = {}
    chars: dict[str, list[str]] = {}
    for lang, data in _LANGUAGE_KEYWORDS.items():
        for word in data.get("words", ()):  # type: ignore[union-attr]
            words.setdefault(str(word).casefold(), []).append(lang)
        for char in data.get("chars", ()):  # type: ignore[union-attr]
            chars.setdefault(str(char).casefold(), []).append(lang)
    _LANGUAGE_MARKER_INDEX = (
        {word: tuple(owners) for word, owners in words.items()},
        {char: tuple(owners) for char, owners in chars.items()},
    )
    return _LANGUAGE_MARKER_INDEX


def _detect_language(text: str, default: str = "English") -> str:
    """Detect natural language of text returning canonical MiniMax H3 language name."""
    if not text or not str(text).strip():
        return default
    s = str(text)
    if re.search(r"[\u3040-\u30ff]", s):
        return "Japanese"
    if re.search(r"[\uac00-\ud7af]", s):
        return "Korean"
    if re.search(r"[\u4e00-\u9fff]", s):
        if re.search(r"[唔咁哋咗諗睇邊]", s) or "粤语" in s or "廣東話" in s:
            return "Cantonese"
        return "Chinese"
    if re.search(r"[\u0400-\u04ff]", s):
        return "Russian"
    if re.search(r"[\u0600-\u06ff]", s):
        return "Arabic"
    if re.search(r"[\u0900-\u097f]", s):
        return "Hindi"

    lower = s.lower()
    word_index, char_index = _language_marker_index()
    scores = {lang: 0.0 for lang in _LANGUAGE_KEYWORDS}

    # Evidence is weighted by how many languages claim the marker. "no" belongs to Spanish and
    # Portuguese alike, so it must not decide between them; "pienso" or "dizer" belong to one
    # and should. Without this, one shared function word settles a short line of dialogue.
    for char in set(lower):
        owners = char_index.get(char)
        if owners:
            for lang in owners:
                scores[lang] += 4.0 / len(owners)
    for word in re.findall(r"\b[\wÀ-ÿ'-]+\b", lower):
        owners = word_index.get(word)
        if owners:
            for lang in owners:
                scores[lang] += 2.0 / len(owners)

    # Morphology separates the Romance languages where shared function words cannot: the
    # ending of a content word is far more diagnostic than "un" or "la".
    for suffix, lang in _LANGUAGE_SUFFIXES:
        scores[lang] += 1.5 * len(re.findall(suffix, lower))

    best_score = max(scores.values())
    if best_score <= 0:
        return default
    # Resolve a tie by a fixed order rather than by dict insertion, which is what decided
    # "hola" (Spanish and Catalan both claim it) before. Ties happen when every marker in the
    # line is shared between mutually intelligible neighbours, so the order runs from the
    # broadest language to the narrowest.
    tied = [lang for lang, score in scores.items() if score >= best_score * 0.999]
    best_lang = min(tied, key=lambda lang: _LANGUAGE_TIE_ORDER.index(lang)
                    if lang in _LANGUAGE_TIE_ORDER else len(_LANGUAGE_TIE_ORDER))
    runner_up = max(
        (score for lang, score in scores.items() if lang not in tied), default=0.0,
    )
    if best_score < 1.0 or best_score < runner_up * 1.15:
        return default
    return best_lang


def _dialogue_authoring_request(source_prompt: str, override_language: str = "auto") -> tuple[bool, str]:
    """Return whether the source authorizes new spoken words and their requested language."""
    source = str(source_prompt or "")

    def clause(match: re.Match[str]) -> str:
        start = max(source.rfind(mark, 0, match.start()) for mark in ".!?;") + 1
        ends = [source.find(mark, match.end()) for mark in ".!?;" if source.find(mark, match.end()) >= 0]
        end = min(ends) if ends else len(source)
        return source[start:end]

    def negated(match: re.Match[str]) -> bool:
        prefix = source[max(0, match.start() - 40):match.start()]
        matched = match.group(0)
        local_clause = clause(match)
        target_match = re.search(
            r"dialogue|dialog|lines?|spoken\s+words?|speech|script|voice[ -]?over|narration|"
            r"di[aá]logo|l[ií]neas?|frases?|palabras|discurso|gui[oó]n|voz\s+en\s+off|narraci[oó]n",
            matched, re.IGNORECASE,
        )
        requested_text = target_match.group(0).casefold() if target_match else "dialogue"
        requested = "dialogue"
        if re.search(r"voice[ -]?over|voz\s+en\s+off", requested_text):
            requested = "voiceover"
        elif re.search(r"narration|narraci[oó]n", requested_text):
            requested = "narration"
        elif re.search(r"speech|spoken\s+words?|discurso|palabras", requested_text):
            requested = "speech"
        prohibitions = [item.group(0).casefold() for item in _DIALOGUE_PROHIBITION_RE.finditer(local_clause)]
        same_target_prohibited = any(
            requested == "speech"
            or (requested == "dialogue" and re.search(r"dialogue|dialog|di[aá]logo|spoken\s+words?|palabras", item))
            or (requested == "voiceover" and re.search(r"voice[ -]?over|voz\s+en\s+off|spoken\s+words?|palabras", item))
            or (requested == "narration" and re.search(r"narration|narraci[oó]n|spoken\s+words?|palabras", item))
            for item in prohibitions
        )
        return bool(
            same_target_prohibited
            or
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

    if override_language and override_language.casefold() not in {"auto", "none", "original language"}:
        return True, _LANGUAGE_ALIASES.get(override_language.casefold(), override_language.capitalize())

    language_mentions = []
    language_patterns = (
        rf"\b(?:in|en)\s+(?:(?:the\s+)?(?:language|idioma)\s+)?({_DIALOGUE_LANGUAGE_PATTERN})",
        rf"\b(?:in|en)\s+(?:(?:the\s+)?(?:language|idioma)\s+)?"
        rf"{_QUALIFIED_DIALOGUE_LANGUAGE_PATTERN}",
        rf"({_DIALOGUE_LANGUAGE_PATTERN})\s+(?:language\s+)?(?:dialogue|dialog|lines?|voice[ -]?over|"
        rf"narration|speech|di[aá]logo|l[ií]neas?|voz\s+en\s+off|narraci[oó]n)\b",
    )
    for pattern in language_patterns:
        for match in re.finditer(pattern, source, flags=re.IGNORECASE):
            language_mentions.append((match.start(), match.group(1)))
    if not language_mentions:
        return True, _detect_language(source, default="English")
    raw = re.sub(r"\s+", " ", max(language_mentions, key=lambda item: item[0])[1]).strip()
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

DIRECTION IN, DESCRIPTION OUT — THIS GOVERNS EVERY BLOCK BELOW:
H3 has no settings: it reads the finished prompt as a description of what the camera sees and the
microphone hears, so that is all it may contain. Every block below is direction addressed to you.
Execute it, never reproduce it. Wording aimed at a filmmaker ("use patience", "do not invent
monsters") becomes scene content once it lands in the output, and H3 renders it. Convert each block
into what is visible and audible here, drop any this scene cannot show with the supplied elements,
and never emit a preset ID or selector label.

This applies to the user's request too: it mixes what happens with how to shoot it ("we must see
the head fly", "the impact must be heavy and very strong"). The requirement binds, the phrasing
does not. So test every sentence you write, rather than matching it against a list of banned
words: could a camera and a microphone have recorded exactly this, and would a second viewer
agree it happened? A demand ("must", "we see"), a rating with nothing to measure it against
("very strong", "highly detailed"), a claim about the effect rather than its cause ("reads as",
"is visibly registered", "emphasizing"), and a label summarising what just happened ("after this
violent action") all fail that test: each states your intent instead of the shot, and H3 renders
the words. Replace each one with the evidence that earned it — what separates, how far and where
it travels, what recoils, sprays or deforms, and how it sounds.

Return only the finished prompt, without Markdown fences, commentary, preamble, or a trailing explanation.
Write all structural prose, section headers, shot timeline descriptions, camera motions, lighting, atmosphere,
actions, and soundscape strictly in English. If the user request is written in Spanish, French, German, Chinese,
Japanese, or any other language, translate all visual, narrative, and soundscape descriptions into fluent English prose.
Preserve or author the intended language ONLY inside dialogue/lyrics and visible on-screen text.
For dialogue/lyrics, format every spoken block strictly as <d>[Language] spoken text</d> where [Language] is the
canonical English name of the language (for example, [Spanish], [English], [French], [German], [Italian], [Portuguese],
[Russian], [Japanese], [Chinese], [Korean], [Arabic], [Cantonese], [Catalan]). Never emit [Original language], [Language],
or placeholder brackets. Never translate, paraphrase, censor, soften, or extend quoted dialogue, lyrics, or visible text.
Do not invent new dialogue unless the authoritative user prompt explicitly asks you to write/generate dialogue or gives an
unscripted speech/narration brief such as what a character explains; in that case, author concrete, natural, speakable
lines in the character's intended language inside <d>[Language] ...</d>. If the request includes an
AUTHORITATIVE DIALOGUE LEDGER, copy every ledger line exactly once and author no additional words. Keep requested
identities, actions, camera behavior, timing, reference roles, and ending intact.

Shared timeline rules:
- Make every added detail concretely visible or audible. Develop the timeline in playback order through style,
  initial composition, subject appearance and position, environment and key props, actions and reactions, observable
  state changes, camera, and synchronized diegetic sound. Preserve concrete spatial relationships and causality.
- At a subject's first clear appearance, establish only source-supported identity, appearance, frame position, and
  current action; later mentions must remain consistent without repeatedly redefining the subject. Allocate detail
  according to each shot's information load rather than padding every shot equally.
- Shot 1 has no timestamp. Later shots are sequential and begin with strictly increasing [Shot N] At MM:SS.mmm,
  cut times inside the requested duration.
- Describe style and initial composition at Shot 1. Write camera motion as a natural action inside the shot: motion
  type plus, only when meaningful, "with small amplitude"/"with large amplitude" and "at slow speed"/"at fast speed";
  omit medium amplitude and normal speed. Cut with "the camera cuts to", "the shot cuts to",
  "the shot transitions to", "the shot changes to", or "the shot switches to", and use cross-dissolve, fade, or
  wipe only when the user asks. A cut must add new subject, space, state, viewpoint, or time information; prefer
  camera movement over a cut that reveals none.
- Give each actual vocal source a stable (S1), (S2), ... ID. At a speaker's first appearance, establish a stable
  vocal identity outside <d> from source-supported context such as character type, age, gender, on- or off-screen
  presence, pitch, timbre, speaking rate, or accent. Put only the exact spoken words and a language tag
  inside <d>[Language] ...</d>. Dialogue is spoken on screen by default: the speaker is visible and its mouth
  moves with the words. Voiceover is the exception and only the source can ask for it; never on your own
  initiative. When it does ask, say "says in an off-screen voiceover" and state that the visible character's
  lips remain completely closed, and then never also describe that same mouth moving, which contradicts it in
  the same breath. Treat a quoted thought or internal monologue as audible voiceover: use
  the exact phrase "says in an off-screen voiceover", preserve it in <d>, identify its thinker as a speaker,
  describe it as an internal monologue outside the tag, and state that the character's
  lips remain completely closed. When one line of dialogue or lyrics crosses a cut, keep the full line in a
  single <d> block in the shot where it begins, never split across two <d> blocks; place <scenetrans> outside
  <d> at the connecting point in both shots, and state that the audio continues across the cut with
  "continues seamlessly across the cut", "continues uninterrupted into the next shot",
  "carries over from the previous shot", or "remains audible across the transition".
  Use <cutoff> only when speech is truncated by the end of the video.
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
- When the request continues a previous take, every transient that was still in progress starts mid-motion at its
  incoming state and speed and is never already completed at the first frame; it may finish only later inside the shot.
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
  and dynamics, never through abstract mood words or the score's emotional function. Music the characters can hear
  (singing, played instruments, radio, television, phone) is a diegetic event that belongs in the timeline instead.
  Use N/A when none is requested.

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
or temporal structure; Audio labels describe copied or referenced signals.
subject_definitions must account for every character who appears or speaks, so that nothing in the later blocks
refers to someone never introduced. Give each one line naming the assets assigned to it, since that binding is what
H3 has to act on: "<Subject 1> is <Picture 1>'s man, ... ; <Audio 1> supplies his voice." A <Subject N> label is
only available to a character a supplied Picture or Video actually depicts — inventing one for a character the
source describes in prose makes H3 look for a reference that does not exist. Define that character in this block
too, but by a stable description carrying its own (Sx) instead of a Subject label, and reuse that exact description
at every later mention: "The very old man, bald with a long white beard and a tortoise shell on his back, (S1);
<Audio 1> supplies his voice." Never leave a speaking character undefined because it has no asset. The summary starts with bracketed task
types chosen from keyframe completion, reference generation, video editing, video continuation, audio reuse, and
audio reference. Join multiple task types with the exact separator " + ". A video editing summary continues right
after that prefix with "The target video is an edited version of <Video 1>." The summary reuses only already defined
labels and introduces no new one. retention_analysis uses only the documented visual markers fully_preserved, partially_preserved,
attribute_transfer, weak_reference and audio markers fully_copy, partially_copy, reference, weak_reference.
When verbal content belongs only to a copied soundtrack or BGM, attribute its <d> block to <Audio N> without
inventing a speaker ID. A concrete person, narrator, or independent vocal source uses a stable (Sx); an Audio
reference bound to that speaker reuses the same ID. Timbre-, rhythm-, or delivery-only references never import words.
Use [unclear] for an explicitly unintelligible transcribed span rather than guessing it.
For generation tasks, make detailed_description explicit and allocate detail according to information load. Establish
style in one or two sentences before Shot 1, then describe composition, appearance, environment, lighting, actions,
state changes, camera, sound, and where each reference takes effect in playback order.
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


def enhancement_profile(enhance_description: bool, invent_scene: bool = False) -> str:
    """conservative < enhanced < invented, en latitud creativa creciente.

    invent_scene solo tiene efecto con la mejora activa: inventar sobre un contrato que pide
    minimo ejecutable seria contradictorio.
    """
    if not bool(enhance_description):
        return "conservative_grounded"
    return "invented_production" if bool(invent_scene) else "enhanced_production"


EMOTIONAL_PERFORMANCE_CONTRACT = """EMOTIONAL PERFORMANCE TRANSLATION — SOURCE-GATED:
- Apply this only when the authoritative source, dialogue, shot plan, reference role, or selected treatment already establishes an emotion, reaction, hesitation, suppression, or mixed inner state. This does not authorize a new emotion, motive, relationship, story beat, or intensity.
- Do not leave an established emotional beat as an abstract label alone. Translate it into the smallest sufficient sequence of observable acting: an initial facial or body state, one or two physically plausible changes in gaze, eyelids, brows, mouth, jaw, breath, posture, or hands, and a readable held or settled state. Preserve the source's emotional meaning and intensity.
- Use partial, asymmetric, overlapping, or conflicting reactions only when the source supports restraint, ambivalence, concealment, mixed emotion, or an attempted social mask. State which reactions coexist; do not manufacture contradiction merely to make acting look complex.
- Interrupt or suppress a gesture only when the source explicitly implies hesitation, resistance, concealment, an aborted action, or a struggle not to react. Suppression does not authorize the suppressed action or its sound; for example, trying not to cry does not by itself authorize sobbing. Otherwise complete every requested action and preserve its resulting state.
- Fit performance to the available duration and authorized framing. Micro-expression detail belongs only where the face is readable; in wider framing, express the same established beat through gaze direction, breath, posture, weight shift, or hand tension. Never add a cut, push-in, close-up, camera move, or lighting change merely to expose it when the shot plan, reference anchor, or cinematography does not permit that choice.
- Use timing only when it clarifies a meaningful transition and fits inside the containing shot, expressed as an approximate duration or ordered phase rather than a false absolute timestamp. Avoid millimeter or centimeter measurements, pseudo-biometric precision, exhaustive muscle lists, and stacked simultaneous instructions. Prefer relational descriptions such as one mouth corner, a briefly held breath, a blink delayed until after the line, or a source-supported gesture that begins and then stops.
- Around dialogue, preserve every word and its assigned timing. Acting may precede, overlap, or follow the line only where causally compatible, and must not obstruct required mouth or eye visibility or imply extra speech. Put any vocal action in the same sentence as its <d> block; outside that sentence prepare or react through breath, gaze, posture, or hands without standalone speaking, talking, or saying cues.
- Adapt the observable cue to the selected visual language without overriding its performance grammar, identity lock, reference state, action order, or final-frame anchor. Source facts, quoted dialogue, and reference anchors outrank the explicit shot plan and timing, which outrank explicit cinematography, selected treatment, and this execution-only translation."""


def system_prompt_for_mode(mode: str, enhance_description: bool | None = None,
                           invent_scene: bool = False) -> str:
    """Return only the output-contract rules relevant to the resolved H3 mode."""
    if mode == "chained_multishot":
        prompt = MULTISHOT_SYSTEM_PROMPT
    else:
        base_marker = "\nBase-mode output has exactly these three sections in order:"
        ref_marker = "\nRef2VA output has exactly these six sections in order:"
        common, mode_rules = SYSTEM_PROMPT.split(base_marker, 1)
        base_rules, ref_rules = mode_rules.split(ref_marker, 1)
        prompt = common + ref_marker + ref_rules if mode == "ref2va" else common + base_marker + base_rules
    if enhance_description is None:
        return prompt
    if enhance_description == "invented_production" or invent_scene:
        return prompt + (
            "\n\nENHANCEMENT PROFILE — INVENTED_PRODUCTION: The user asked you to build the scene, not just to "
            "photograph what they wrote. Treat the source as a premise: invent the concrete world around it — "
            "supporting subjects, props, set dressing, wardrobe, weather, secondary action, background life, and "
            "the physically caused sound of everything you add — until the shot reads as a finished piece. Every "
            "invention must be causally compatible with the source and with what is already on screen; do not "
            "contradict a stated fact or reference. Four things stay locked because they are the user's, not "
            "yours: quoted dialogue word for word, the identity and role of every supplied reference, the "
            "requested duration and shot count, and the requested ending. Invent nothing that would need a cut, "
            "a new location, or a time jump the source did not ask for."
        )
    if enhance_description:
        return prompt + (
            "\n\nENHANCEMENT PROFILE — ENHANCED_PRODUCTION: Decide how the supplied elements look, move and sound; "
            "never add another one. Composition, blocking, screen direction, camera, focus, source-consistent "
            "lighting, material response, micro-performance and physically caused sound are yours to choose when "
            "they make the requested action more legible. The inventory is not yours: introduce no object, surface, "
            "structure, weather, creature or background feature the source did not put there, beyond what its own "
            "setting unavoidably contains — a room has a floor and a street has a road surface, but neither "
            "acquires a steam grate. Add no new subject, goal, plot beat, branded object, reference role, salient "
            "event, dialogue, or endpoint. Building the world around the request is the next profile up, not this one."
        )
    return prompt + (
        "\n\nENHANCEMENT PROFILE — CONSERVATIVE_GROUNDED: Do not preserve source terseness when the selected H3 "
        "mode requires an opening state, spatial relation, causal transition, final state, or frame/reference anchor. "
        "Add only that minimum executable structure, neutral continuity, and directly caused sound; do not add "
        "decorative styling, set dressing, new props, events, or sound sources."
    )


def resolve_mode(mode: str, reference_context: str = "", basic_prompt: str = "",
                 media_manifest: str = "", editing_intent: str = "none") -> str:
    mode = str(mode).strip().lower()
    if mode not in TASK_MODES:
        raise ValueError(f"Unsupported MiniMax H3 prompt mode {mode!r}")
    if mode != "auto":
        return mode
    if editing_intent in EDITING_INTENT_CHOICES and editing_intent != "none":
        return "ref2va"
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
    plain_context = str(reference_context or "")
    plain_assets = [_asset_label(kind, number) for kind, number in _ASSET_REFERENCE_RE.findall(plain_context)]
    picture_assets = [item for item in plain_assets if item.startswith("<Picture")]
    first_role = bool(re.search(r"\b(?:first|initial|primer)\s+(?:frame|fotograma)\b", plain_context, re.IGNORECASE))
    last_role = bool(re.search(r"\b(?:last|final|último|ultimo)\s+(?:frame|fotograma)\b", plain_context, re.IGNORECASE))
    if len(set(picture_assets)) == 1 and first_role and not last_role:
        return "i2va"
    if len(set(picture_assets)) == 1 and last_role and not first_role:
        return "l2va"
    if len(set(picture_assets)) == 2 and first_role and last_role:
        return "fl2va"
    has_reference = (
        _REFERENCE_RE.search(reference_context or "")
        or _ASSET_REFERENCE_RE.search(reference_context or "")
        or _ASSET_REFERENCE_RE.search(basic_prompt or "")
    )
    return "ref2va" if has_reference else "t2va"


def _asset_label(kind: str, number: str | int) -> str:
    canonical = {
        "image": "Picture", "imagen": "Picture", "picture": "Picture", "foto": "Picture",
        "video": "Video", "vídeo": "Video", "audio": "Audio", "voice": "Audio", "voz": "Audio",
    }
    return f"<{canonical[str(kind).lower()]} {int(number)}>"


def _definition_labels(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(
        r"(?im)^\s*(<(?:Subject|Picture|Video|Audio)\s+\d+>)\s*(?::|\bis\b|\bcomes?\s+from\b|\bfrom\b)",
        text or "",
    )))


def _renumber_zero_indexed_assets(source_prompt: str) -> str:
    """Shift a whole asset kind up by one when the source counts it from zero.

    Connected media is numbered from 1, so "audio 0" names nothing and silently
    costs the generation a voice. A source that says audio 0 and audio 1 is
    counting from zero throughout, so the repair that preserves the author's
    intent is to shift that kind as a block rather than to guess per mention.
    """
    source = source_prompt or ""
    for kinds in (("image", "imagen", "picture", "foto"), ("audio", "voice", "voz"), ("video", "vídeo")):
        pattern = r"\b(" + "|".join(kinds) + r")\s*(?:number\s*|n[uú]mero\s*|#\s*)?(\d+)\b"
        numbers = {int(number) for _kind, number in re.findall(pattern, source, flags=re.IGNORECASE)}
        if 0 not in numbers:
            continue
        source = re.sub(
            pattern,
            lambda match: f"{match.group(1)} {int(match.group(2)) + 1}",
            source,
            flags=re.IGNORECASE,
        )
    return source


def _official_reference_model(source_prompt: str, reference_context: str = "") -> dict[str, Any]:
    """Build high-confidence Ref2VA semantics without equating asset and Subject ordinals."""
    source = _renumber_zero_indexed_assets(source_prompt)
    canonical_reference_context = _ASSET_REFERENCE_RE.sub(
        lambda match: _asset_label(*match.groups()), reference_context or "",
    )
    combined_context = source + "\n" + canonical_reference_context
    explicit_definitions = _definition_labels(canonical_reference_context)
    assets = list(dict.fromkeys(
        [_asset_label(kind, number) for kind, number in _ASSET_REFERENCE_RE.findall(source)]
        + _REFERENCE_RE.findall(canonical_reference_context)
        + _REFERENCE_RE.findall(source)
    ))
    assets = [label for label in assets if not label.casefold().startswith("<subject")]
    # Connected media is numbered from 1, so "audio 0" names nothing. Defining it
    # anyway hands the writer a phantom asset it will happily spend a voice on.
    assets = [label for label in assets if not re.search(r"\s0>$", label)]
    if explicit_definitions:
        return {
            "explicit": True,
            "assets": assets,
            "definitions": [],
            "definition_labels": explicit_definitions,
            "provenance_assets": set(),
            "independent_assets": {label for label in explicit_definitions if not label.lower().startswith("<subject")},
            "subjects": [],
            "text_speakers": [],
            "reveal": None,
        }

    picture_roles = []
    binding_metadata: dict[tuple[str, str], dict[str, Any]] = {}
    for first_role, second_role, kind, number in _COORDINATED_ROLE_REFERENCE_RE.findall(source):
        # This pattern is for two roles sharing one image ("the man and the woman
        # in image 1"). When a role carries its own reference the coordination is
        # between two separately sourced characters, and pinning both to the last
        # image invents a subject and misbinds the first.
        if _ASSET_REFERENCE_RE.search(first_role) or _ASSET_REFERENCE_RE.search(second_role):
            continue
        asset = _asset_label(kind, number)
        picture_roles.extend(((first_role.strip(), asset), (second_role.strip(), asset)))
    # Named characters are collected before the determiner pattern so a picture that carries a
    # name is bound to it; the determiner pattern still wins later by role specificity when the
    # source also describes the same picture with a noun phrase.
    named_assets, named_roles = set(), set()
    for match in _NAMED_ROLE_REFERENCE_RE.finditer(source):
        # An article means the noun-phrase pattern already owns this reference ("the Uzi in
        # image 2"), and letting both claim it would split one picture across two Subjects.
        # "a" is excluded from that test on purpose: Spanish marks a personal object with it
        # ("Vemos a Marta, en la imagen 1"), so treating it as an article would discard every
        # named character.
        determiner = (match.group("determiner") or "").strip().casefold()
        if determiner and determiner != "a":
            continue
        name = match.group("name").strip()
        kind, number = match.group("kind"), match.group("number")
        # Sentence-leading connectives are capitalized too and are never character names.
        if name.casefold() in {
            "then", "and", "but", "we", "he", "she", "they", "it", "this", "that", "there",
            "first", "next", "later", "after", "before", "now", "here", "also", "luego",
            "entonces", "despues", "después", "ahora", "aqui", "aquí", "el", "la", "ellos",
        }:
            continue
        asset = _asset_label(kind, number)
        picture_roles.append((name, asset))
        named_assets.add(asset)
        named_roles.add(name)
    for match in _ROLE_REFERENCE_RE.finditer(source):
        role, kind, number = match.groups()
        role = role.strip()
        # When a sentence begins with another actor ("the woman tells the person in image 2"), bind the
        # reference to the nearest noun phrase rather than the sentence-leading subject.
        nested_determiners = list(re.finditer(r"\b(?:the|a|an|el|la|los|las|un|una|al|del)\s+", role, re.IGNORECASE))
        if nested_determiners:
            role = role[nested_determiners[-1].end():].strip()
        if not role or re.search(r"^(?:audio|voice|voz|video|vídeo|image|imagen|picture|foto)\s*\d+\b", role, re.IGNORECASE):
            continue
        # A place is not a character. Claiming it here would shadow the setting detector
        # and give the location a Subject number, inviting the writer to give it agency.
        if re.fullmatch(
            r"(?:scenario|setting|environment|surroundings|background|location|place|scene|"
            r"escenario|entorno|fondo|lugar|escena)", role, re.IGNORECASE,
        ):
            continue
        role_was_main_typo = role.casefold() == "main"
        if role_was_main_typo:
            role = "man"
        # Repair a frequent source typo only in the inferred role label.  The
        # original prompt remains authoritative and is never rewritten.
        role = re.sub(r"\bcihinese\b", "Chinese", role, flags=re.IGNORECASE)
        role = re.sub(
            r"^.*\b(?:appear|appears|appearing|emerge|emerges|show|shows|reveal|reveals|"
            r"aparece|aparecen|apareciendo|emerge|emergen|vemos|son)\s+",
            "",
            role,
            flags=re.IGNORECASE,
        ).strip()
        asset = _asset_label(kind, number)
        # Preserve the user's literal local binding rather than guessing which kind of
        # entity it describes. This works equally for people, objects, vehicles, styles,
        # late reveals, wardrobe clauses, and other explicit image associations.
        trailing = re.split(r"[.;\r\n]", source[match.end():match.end() + 180], maxsplit=1)[0]
        cue_stopwords = {
            "image", "imagen", "picture", "foto", "subject", "person", "persona", "people",
            "character", "personaje", "thing", "object", "the", "this", "that", "then", "than",
            "with", "from", "into", "inside", "outside", "where", "when", "while", "only", "very",
            "como", "para", "desde", "donde", "cuando", "mientras", "este", "esta", "esto", "that",
            "can't", "cannot",
        }
        generic_binding_roles = {
            "person", "persona", "people", "character", "personaje", "thing", "object", "objeto",
        }
        descriptor_tail = ""
        if re.match(
            r"\s*(?:(?:,\s*)?(?:as|como|wearing|dressed|holding|carrying|with|"
            r"vestido|vestida|llevando|sosteniendo|con|who|que)\b|,\s*(?:a|an|un|una)\b)",
            trailing,
            flags=re.IGNORECASE,
        ):
            descriptor_tail = trailing
        # ``with the voice in Audio N`` is a cross-modal binding, not a visual
        # descriptor of the Picture subject.  Let the dedicated audio mapping
        # below retain it without swallowing the rest of the scene sentence.
        if re.match(
            r"\s*,?\s*(?:with|using|usando|con)\s+(?:the\s+|la\s+|el\s+)?"
            r"(?:voice|voz)\s+(?:in|of|from|en|de)\s+(?:audio|voice|voz)\s*\d+\b",
            descriptor_tail,
            flags=re.IGNORECASE,
        ):
            descriptor_tail = ""
        binding_excerpt = re.sub(
            r"\s+", " ", source[match.start():match.end()] + descriptor_tail,
        ).strip(" ,")
        binding_excerpt = _ASSET_REFERENCE_RE.sub(lambda item: _asset_label(*item.groups()), binding_excerpt)
        if role_was_main_typo:
            binding_excerpt = re.sub(r"\bmain\b", "man", binding_excerpt, count=1, flags=re.IGNORECASE)
        binding_excerpt = re.sub(r"\bcihinese\b", "Chinese", binding_excerpt, flags=re.IGNORECASE)
        cue_text = role
        if role.casefold() in generic_binding_roles:
            cue_text = descriptor_tail
        elif descriptor_tail:
            cue_text += " " + descriptor_tail
        binding_cues = tuple(dict.fromkeys(
            word.casefold() for word in re.findall(r"[\wÀ-ÿ'-]{4,}", cue_text)
            if word.casefold() not in cue_stopwords
        ))
        pieces = re.split(r"\s+(?:and|y)\s+", role, flags=re.IGNORECASE)
        for piece in pieces:
            if piece.strip():
                clean_piece = piece.strip()
                picture_roles.append((clean_piece, asset))
                binding_metadata.setdefault((clean_piece.casefold(), asset.casefold()), {
                    "excerpt": binding_excerpt,
                    "cues": binding_cues,
                })
    for match in _ROLE_AFTER_REFERENCE_RE.finditer(source):
        kind, number, role = match.groups()
        role = role.strip()
        nested_determiners = list(re.finditer(r"\b(?:the|a|an|el|la|los|las|un|una|al|del)\s+", role, re.IGNORECASE))
        if nested_determiners:
            role = role[nested_determiners[-1].end():].strip()
        if not role or re.search(r"^(?:audio|voice|voz|video|vídeo|image|imagen|picture|foto)\s*\d+\b", role, re.IGNORECASE):
            continue
        role_was_main_typo = role.casefold() == "main"
        if role_was_main_typo:
            role = "man"
        role = re.sub(r"\bcihinese\b", "Chinese", role, flags=re.IGNORECASE)
        role = re.sub(
            r"^.*\b(?:appear|appears|appearing|emerge|emerges|show|shows|reveal|reveals|"
            r"aparece|aparecen|apareciendo|emerge|emergen|vemos|son)\s+",
            "",
            role,
            flags=re.IGNORECASE,
        ).strip()
        asset = _asset_label(kind, number)
        pieces = re.split(r"\s+(?:and|y)\s+", role, flags=re.IGNORECASE)
        for piece in pieces:
            if piece.strip():
                clean_piece = piece.strip()
                picture_roles.append((clean_piece, asset))
    for asset, role, analysis in re.findall(
        r"Connected asset\s+(<Picture\s+\d+>)\s+has role:\s*([^;\r\n]+)(?:;\s*analysis:\s*([^\r\n]+))?",
        reference_context or "", flags=re.IGNORECASE,
    ):
        role_text = role.strip()
        if analysis.strip() and re.search(r"\b(?:identity|subject|character|person|object|prop|style)\b", role_text, re.IGNORECASE):
            role_text = f"{role_text} {analysis.strip()}"
        picture_roles.append((role_text, asset))
    for asset, role in re.findall(
        r"(<Picture\s+\d+>)\s+(?:supplies|provides|gives|aporta|proporciona|suministra)\s+"
        r"(?:the\s+|la\s+|el\s+)?([^.;\r\n]+)",
        canonical_reference_context, flags=re.IGNORECASE,
    ):
        picture_roles.append((role.strip(), asset))

    picture_assets = [label for label in assets if label.lower().startswith("<picture")]
    video_assets = [label for label in assets if label.lower().startswith("<video")]
    audio_assets = [label for label in assets if label.lower().startswith("<audio")]
    def role_family(role: str) -> str:
        lowered = role.casefold()
        if re.search(r"\b(?:style|look|aesthetic|palette|lighting|estilo)\b", lowered):
            return "style"
        if re.search(
            r"\b(?:identity|identidad|person|persona|people|man|men|woman|women|boy|girl|hombre|hombres|mujer|"
            r"actor|actress|presenter|driver|identity|face|body|character|version|versi[oó]n)\b",
            lowered,
        ):
            return "identity"
        # A proper name identifies a character, so it belongs with identity rather than with the
        # object branch, whose wording ("exact visible design, proportions, materials, colors,
        # and markings") describes a prop and would read as one for a named person.
        if role in named_roles:
            return "identity"
        return "design"

    generic_role_words = {
        "the", "a", "an", "el", "la", "los", "las", "un", "una", "person", "persona",
        "people", "man", "men", "hombre", "hombres", "character", "version", "versión",
    }

    def role_specificity(role: str) -> tuple[int, int]:
        words = [item.casefold() for item in re.findall(r"[\wÀ-ÿ'-]+", role)]
        return (sum(item not in generic_role_words for item in words), len(words))

    # Distinct people or objects can come from the same asset. Deduplicate only demonstrable aliases whose
    # normalized role text is the same; grouping only by asset/family silently dropped coordinated entities.
    grouped_roles: dict[tuple[str, str, str], str] = {}
    group_order: list[tuple[str, str, str]] = []
    for role, asset in picture_roles:
        role_words = re.findall(r"[\wÀ-ÿ'-]+", role.casefold())
        alias_key = " ".join(
            word for word in role_words
            if word not in {"the", "a", "an", "el", "la", "los", "las", "un", "una", "same", "mismo", "misma"}
        )
        # Generic singular/plural labels in prose commonly refer back to the same person. Collapse
        # those demonstrable aliases, but retain coordinated concrete roles such as woman + man.
        family = role_family(role)
        if family == "identity" and (
            all(word in generic_role_words for word in role_words)
            or re.search(r"\b(?:version|versi[oó]n)\b", role, re.IGNORECASE)
        ):
            alias_key = "__generic_identity__"
        key = (asset.casefold(), family, alias_key)
        if key not in grouped_roles:
            grouped_roles[key] = role
            group_order.append(key)
        elif role_specificity(role) > role_specificity(grouped_roles[key]):
            grouped_roles[key] = role

    subjects = []
    setting_assets: dict[str, dict[str, Any]] = {}
    used_assets = set()
    primary_identity_label = None
    for key in group_order:
        role = grouped_roles[key]
        asset = next(item for item in picture_assets if item.casefold() == key[0])
        contribution = key[1]
        binding = binding_metadata.get((role.casefold(), asset.casefold()), {})
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
        if binding.get("excerpt"):
            description += (
                f"; this label applies only to the entity explicitly bound by the source wording "
                f"{binding['excerpt']!r}"
            )
        subjects.append({"role": role, "asset": asset, "contribution": contribution,
                         "description": description, "marker": marker,
                         "binding_excerpt": binding.get("excerpt", ""),
                         "binding_cues": binding.get("cues", ())})
        if contribution == "identity" and primary_identity_label is None:
            # Labels are assigned in this same stable order below.
            primary_identity_label = f"<Subject {len(subjects)}>"
        used_assets.add(asset)

    independent = {}

    # Infer only explicit local Picture/Audio pairings such as
    # ``the man in image 2 ... with the voice in audio 2``.  For each voice
    # clause, the nearest preceding Picture in the same bounded span wins;
    # conflicting pairings are deliberately left unbound.
    audio_subject_candidates: dict[str, set[str]] = {}
    known_picture_roles_map = {s["asset"].casefold(): s["role"].casefold() for s in subjects}
    clauses = re.split(r"[,;.!\n]|\s+(?:y|and)\s+", source)
    for clause in clauses:
        clause_audios = list(_ASSET_REFERENCE_RE.finditer(clause))
        clause_audios = [m for m in clause_audios if m.group(1).casefold() in {"audio", "voice", "voz"}]
        clause_pics = list(_ASSET_REFERENCE_RE.finditer(clause))
        clause_pics = [m for m in clause_pics if m.group(1).casefold() in {"image", "imagen", "picture", "foto"}]
        if clause_audios:
            for a_match in clause_audios:
                audio_asset = _asset_label(a_match.group(1), a_match.group(2))
                if clause_pics:
                    pic_asset = _asset_label(clause_pics[0].group(1), clause_pics[0].group(2))
                    taken = any(
                        pic_asset in pics
                        for other, pics in audio_subject_candidates.items()
                        if other != audio_asset
                    )
                    if not taken:
                        audio_subject_candidates.setdefault(audio_asset, set()).add(pic_asset)
                else:
                    matched_pic = None
                    for p_asset, p_role in known_picture_roles_map.items():
                        role_words = [w for w in re.findall(r"[\wÀ-ÿ'-]+", p_role) if w not in {"the", "a", "an", "el", "la", "un", "una"}]
                        if any(w in clause.lower() for w in role_words):
                            matched_pic = next((s["asset"] for s in subjects if s["asset"].casefold() == p_asset), None)
                            break
                    already_paired = any(
                        matched_pic in pics
                        for other, pics in audio_subject_candidates.items()
                        if other != audio_asset
                    )
                    if matched_pic and not already_paired:
                        audio_subject_candidates.setdefault(audio_asset, set()).add(matched_pic)

    voice_binding_re = re.compile(
        r"\b(?:with|using|use|uses|usando|usa|utiliza|con|tiene|teniendo|has|having|gives|giving|su|his|her|their|whose|cuya|cuyo)\s+"
        r"(?:the\s+|la\s+|el\s+|su\s+|his\s+|her\s+|their\s+)?(?:voice|voz)(?:\s+(?:in|of|from|en|de|del|is|es|proviene\s+de|viene\s+de|as|como|being))?\s*"
        r"(audio|voice|voz)\s*(?:number\s*|n[uú]mero\s*|#\s*)?(\d+)\b",
        re.IGNORECASE,
    )
    picture_mentions = [
        (match.start(), _asset_label(match.group(1), match.group(2)))
        for match in _ASSET_REFERENCE_RE.finditer(source)
        if match.group(1).casefold() in {"image", "imagen", "picture", "foto"}
    ]
    # A Picture already paired with one voice cannot lend its identity to a
    # second voice: two audios in the same source describe two speakers, and the
    # extra ones belong to characters that exist only in the text. Binding them
    # by mere proximity would silently give one Subject both voices.
    claimed_pictures = {
        pic for pics in audio_subject_candidates.values() for pic in pics
    }
    for voice_match in voice_binding_re.finditer(source):
        audio_asset = _asset_label(voice_match.group(1), voice_match.group(2))
        if audio_asset not in audio_subject_candidates:
            preceding = [
                (position, asset) for position, asset in picture_mentions
                if 0 <= voice_match.start() - position <= 420
                and asset not in claimed_pictures
            ]
            if preceding:
                nearest = max(preceding)[1]
                audio_subject_candidates.setdefault(audio_asset, set()).add(nearest)
                claimed_pictures.add(nearest)
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
        number = re.search(r"\d+", asset).group()
        token = rf"(?:audio\s*(?:number\s*|n[uú]mero\s*|#\s*)?{number}|{re.escape(asset)})"
        # The source text has not been canonicalized yet at this point, so
        # preserve voice/voz aliases while detecting voice-cloning intent.
        voice_token = rf"(?:{token}|(?:voice|voz)\s*(?:number\s*|n[uú]mero\s*|#\s*)?{number})"
        copy_match = re.search(
            rf"(?:\b(?:copy|copied|reuse|reused|reutiliza|copiar|paired)\b.{{0,60}}{token}|"
            rf"{token}.{{0,60}}\b(?:copy|copied|reuse|reused|reutiliza|copiar|paired)\b)",
            combined_context,
            re.IGNORECASE,
        )
        exact_copy = bool(copy_match)
        if copy_match:
            # A prohibition such as "do not copy the original words from
            # Audio 1" must never be inverted into synchronized audio reuse.
            local_copy_context = combined_context[max(0, copy_match.start() - 30):copy_match.end() + 30]
            if re.search(
                r"\b(?:do\s+not|don't|never|without|no)\s+(?:fully\s+|directly\s+)?"
                r"(?:copy|reuse|reutiliza|copiar)\b",
                local_copy_context,
                re.IGNORECASE,
            ):
                exact_copy = False
        voice_reference = bool(re.search(
            rf"(?:\b(?:voice|voz|timbre|speaker|delivery)\b.{{0,70}}{voice_token}|"
            rf"{voice_token}.{{0,70}}\b(?:voice|voz|timbre|speaker|delivery)\b|"
            rf"\b(?:using|use|uses|with|usando|usa|utiliza|con|pon|ponle|poner|asigna|asignar)\s+(?:the\s+|la\s+|el\s+|al\s+|a\s+)?{voice_token})",
            combined_context,
            re.IGNORECASE,
        )) or asset in audio_subject_candidates
        independent[asset] = {
            "description": (
                f"the supplied audio signal {'copied as a synchronized audio layer' if exact_copy else 'used exclusively as the voice-timbre and delivery reference for the speaking character; its original words and unrelated sounds are not copied' if voice_reference else 'used as an audio reference for voice, delivery, rhythm, or sound texture'}"
            ),
            "marker": "partially_copy" if exact_copy else "reference",
            "voice_reference": voice_reference,
            "bound_subject_asset": (
                next(iter(audio_subject_candidates.get(asset, ())))
                if len(audio_subject_candidates.get(asset, ())) == 1 else None
            ),
        }
        used_assets.add(asset)

    # A connected image without an authoritative role is not automatically a
    # person/object Subject. Guessing here can silently bind an unrelated image
    # to a source character. Keep it available but unassigned until the source,
    # reference notes, or media manifest states the relationship.
    unassigned_assets = {asset for asset in picture_assets if asset not in used_assets}

    # A source can state a non-subject role just as authoritatively: "enters the scenario of
    # <Picture 2>" binds that image to the setting, not to a character. Detecting only subject
    # roles left such an asset undefined while the writer still referenced it, so H3 received a
    # label with nothing behind it. This reads the stated role; it never guesses one.
    for asset in sorted(unassigned_assets):
        number = re.search(r"\d+", asset).group()
        token = rf"(?:(?:picture|image|imagen|foto)\s*(?:number\s*|n[uú]mero\s*|#\s*)?{number}|{re.escape(asset)})"
        place = (r"scenario|setting|environment|surroundings|background|location|place|scene|"
                 r"escenario|entorno|fondo|lugar|escena")
        # The link must be explicit and directional: the place word has to govern this asset.
        # A looser window matched "imagen 1 entra en el escenario", turning the subject's own
        # picture into the setting, so proximity alone is not evidence.
        article = r"(?:the|a|an|el|la|los|las|un|una)\s+"
        stated = re.search(
            rf"\b(?:{place})\b\s+(?:of|from|in|de|del|en)\s+(?:{article})?{token}\b"
            rf"|\b(?:enters?|entering|walks?\s+into|steps?\s+into|inside|within)\s+(?:{article})?{token}\b"
            rf"|\b(?:entra|entrando|camina)\s+(?:en|dentro\s+de)\s+(?:{article})?{token}\b",
            combined_context, re.IGNORECASE,
        )
        if not stated:
            continue
        setting_assets[asset] = {
            "description": (
                "the reusable setting supplying the location, architecture, surfaces, and lighting conditions "
                "of the scene; subjects and actions enter this environment without altering its identity"
            ),
            "marker": "fully_preserved",
            "excerpt": stated.group(0).strip(),
        }
    unassigned_assets -= set(setting_assets)

    definitions = []
    for index, subject in enumerate(subjects, 1):
        subject["label"] = f"<Subject {index}>"
        definitions.append({
            "label": subject["label"], "line": f"{subject['label']} is {subject['description']}.",
            "marker": subject["marker"], "asset": subject["asset"], "kind": "subject",
            "role": subject["role"],
        })
    # The setting keeps its own asset label rather than becoming a Subject: it is a place, and
    # numbering it as a Subject would invite the writer to give it agency.
    for asset in sorted(setting_assets):
        item = setting_assets[asset]
        definitions.append({
            "label": asset, "line": f"{asset} is {item['description']}.",
            "marker": item["marker"], "asset": asset, "kind": "setting",
            "role": "setting", "binding_excerpt": item.get("excerpt", ""),
        })
    subject_labels_by_asset: dict[str, list[str]] = {}
    for subject in subjects:
        subject_labels_by_asset.setdefault(subject["asset"].casefold(), []).append(subject["label"])
    for item in independent.values():
        bound_asset = item.get("bound_subject_asset")
        labels = subject_labels_by_asset.get(str(bound_asset).casefold(), []) if bound_asset else []
        if item.get("voice_reference") and len(labels) == 1:
            item["bound_subject"] = labels[0]
            s_match = re.search(r'\d+', labels[0])
            s_num = s_match.group() if s_match else "1"
            item["description"] = (
                f"the supplied audio signal used exclusively as the voice-timbre and delivery reference for "
                f"{labels[0]} (S{s_num})'s newly generated dialogue; its original "
                "words and unrelated sounds are not copied"
            )

    # A voice reference left over after every Subject is served belongs to a
    # character the source only describes in prose.  The guide binds it to a
    # stable voice description rather than to a Subject label, so consume the
    # prose speakers in the order the source introduces them.
    text_speakers = _text_only_speaker_descriptors(
        source, tuple(subject.get("binding_excerpt", "") for subject in subjects),
    )
    spare_speakers = list(text_speakers)
    for label in audio_assets:
        item = independent.get(label)
        if not item or not item.get("voice_reference") or item.get("bound_subject"):
            continue
        # A copied signal is reused wholesale; it is not a timbre reference that
        # needs an owner, and its description must survive untouched.
        if item.get("marker") != "reference":
            continue
        if not spare_speakers:
            # No descriptor could be recovered, but the audio still cannot belong
            # to a Subject that already owns a voice. Say so rather than leaving
            # the generic wording, which reads as an invitation to reuse (S1).
            item["unowned_voice"] = True
            item["description"] = (
                "the supplied audio signal used exclusively as the voice-timbre and delivery reference for a "
                "speaker who has no reference asset of their own and who therefore carries a stable voice "
                "description plus their own speaker ID, never the speaker ID of a defined Subject; its "
                "original words and unrelated sounds are not copied"
            )
            continue
        descriptor = spare_speakers.pop(0)
        item["bound_voice_descriptor"] = descriptor
        item["description"] = (
            f"the supplied audio signal used exclusively as the voice-timbre and delivery reference for "
            f"{descriptor}, a speaker the source describes only in prose and who therefore carries a stable "
            "voice description plus a speaker ID instead of a Subject label; its original words and unrelated "
            "sounds are not copied"
        )

    for label, item in independent.items():
        definitions.append({
            "label": label, "line": f"{label} is {item['description']}.",
            "marker": item["marker"], "asset": label, "kind": label[1:].split()[0].lower(),
            "voice_reference": bool(item.get("voice_reference")),
            "bound_subject": item.get("bound_subject"),
            "bound_voice_descriptor": item.get("bound_voice_descriptor"),
            "unowned_voice": bool(item.get("unowned_voice")),
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
        "text_speakers": text_speakers,
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
    for subject in model["subjects"]:
        binding = subject.get("binding_excerpt") or subject["role"]
        lines.append(
            f"- BINDING LOCK: {subject['label']} maps only to the entity, object, or visual concept explicitly "
            f"linked to {subject['asset']} in the user's source wording {binding!r}. Attach the reference to that "
            "grammatical referent—not to an earlier, nearby, speaking, or more prominent subject. Its first use in "
            "detailed_description must identify that exact referent."
        )
    for descriptor in model.get("text_speakers", ()):
        lines.append(
            f"- PROSE SPEAKER: {descriptor} speaks but has no reference asset. Do not invent a <Subject N> label "
            f"for this character. Introduce it as a stable voice description reused verbatim at every vocal "
            f"event, followed by its own speaker ID, and never reuse the speaker ID of a defined Subject."
        )
    for item in model["definitions"]:
        descriptor = item.get("bound_voice_descriptor")
        if item["kind"] == "audio" and descriptor:
            lines.append(
                f"- VOICE BINDING LOCK: {item['label']} belongs exclusively to {descriptor}, not to any defined "
                f"Subject. Every line that character speaks must identify {item['label']} as its timbre/delivery "
                f"reference and reuse that character's own stable speaker ID. Never attach this voice to a "
                "<Subject N> or to another speaker."
            )
            continue
        if item["kind"] == "audio" and item.get("unowned_voice"):
            lines.append(
                f"- VOICE BINDING LOCK: {item['label']} belongs to a speaker with no reference asset. Introduce "
                f"that character with a stable voice description reused verbatim at every vocal event, give them "
                f"their own speaker ID, and identify {item['label']} as their timbre/delivery reference. Never "
                "attach this voice to a defined Subject and never reuse a Subject's speaker ID for it."
            )
            continue
        bound_subject = item.get("bound_subject")
        if item["kind"] != "audio" or not bound_subject:
            continue
        speaker_id = re.search(r"\d+", bound_subject).group()
        lines.append(
            f"- VOICE BINDING LOCK: infer this relationship from the user's full grammatical context, not from "
            f"matching asset ordinals: {item['label']} belongs exclusively to {bound_subject} (S{speaker_id}). "
            f"Every newly generated line spoken by {bound_subject} must use the exact stable speaker ID "
            f"(S{speaker_id}) and explicitly identify {item['label']} as its timbre/delivery reference. Never "
            "transfer that voice to another Subject, and never assign a different S-number to this Subject."
        )
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
    canonical = _ASSET_REFERENCE_RE.sub(
        lambda match: _asset_label(*match.groups()), _renumber_zero_indexed_assets(source_prompt),
    )
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


def _reference_task_types(model: Mapping[str, Any], source_prompt: str,
                          reference_context: str) -> list[str]:
    context = (source_prompt or "") + "\n" + (reference_context or "")
    kinds = {item["kind"] for item in model["definitions"]}
    task_types: list[str] = []
    if "video" in kinds and re.search(
        r"\b(?:continue|continuation|continuar|extend|resume)\b", context, re.IGNORECASE,
    ):
        task_types.append("video continuation")
    elif "video" in kinds and re.search(
        r"\b(?:edit|editing|replace|modify|editar|reemplazar)\b", context, re.IGNORECASE,
    ):
        task_types.append("video editing")
    if any(
        item["kind"] == "picture" and re.search(r"frame|composition", item["line"], re.IGNORECASE)
        for item in model["definitions"]
    ):
        task_types.append("keyframe completion")
    if model["subjects"] or (
        not any(item.startswith("video ") for item in task_types)
        and any(item["kind"] in {"picture", "video"} for item in model["definitions"])
    ):
        task_types.append("reference generation")
    audio_items = [item for item in model["definitions"] if item["kind"] == "audio"]
    if audio_items:
        task_types.append("audio reuse" if any(
            item["marker"] in {"fully_copy", "partially_copy"} for item in audio_items
        ) else "audio reference")
    return list(dict.fromkeys(task_types or ["reference generation"]))


def _default_retention_line(item: Mapping[str, Any]) -> str:
    label = item["label"]
    marker = item["marker"]
    asset = item["asset"]
    if item["kind"] == "subject":
        return (
            f"{label}: {marker} - carry the {item.get('kind', 'subject')} identity/design derived from {asset} "
            "into every shot where this Subject appears, while explicit source changes still win."
        )
    if item["kind"] == "audio":
        action = "copy the synchronized signal" if marker in {"fully_copy", "partially_copy"} else "use only its stated audio attributes"
        return f"{label}: {marker} - {action} at the source-specified moments; do not import unrelated words or sounds."
    return (
        f"{label}: {marker} - apply its stated {item['kind']} role at the specified timeline positions and preserve "
        "the concrete source relationship described above."
    )


def _reference_summary_tail(model: Mapping[str, Any], task_types: list[str]) -> str:
    clauses = []
    if "video editing" in task_types:
        video = next((item["label"] for item in model["definitions"] if item["kind"] == "video"), "<Video 1>")
        clauses.append(f"The target video is an edited version of {video}.")
    elif "video continuation" in task_types:
        video = next((item["label"] for item in model["definitions"] if item["kind"] == "video"), "<Video 1>")
        clauses.append(f"The target video continues {video} while preserving its incoming temporal state.")
    subject_relations = [
        f"{item['label']} derives its reusable {subject['contribution']} from {subject['asset']}"
        for item in model["definitions"] if item["kind"] == "subject"
        for subject in model["subjects"] if subject["label"] == item["label"]
    ]
    if subject_relations:
        clauses.append("; ".join(subject_relations) + ".")
    independent = [
        item["label"] for item in model["definitions"] if item["kind"] != "subject"
    ]
    if independent:
        clauses.append("Independent reference roles are supplied by " + ", ".join(independent) + ".")
    return " ".join(clauses) or "The target applies the defined references only in their stated roles."


def normalize_reference_definitions(text: str, source_prompt: str, reference_context: str = "") -> str:
    """Complete inferred Ref2VA mappings without discarding valid generated analysis."""
    text = normalize_ref_task_prefix(text)
    model = _official_reference_model(source_prompt, reference_context)
    if model["explicit"] or not model["definitions"]:
        return str(text)
    value = str(text)
    if not _section_body(value, "subject_definitions"):
        return str(text)
    existing_definitions: dict[str, str] = {}
    for line in _section_body(value, "subject_definitions").splitlines():
        match = re.match(r"\s*(<(?:Subject|Picture|Video|Audio)\s+\d+>)", line, re.IGNORECASE)
        if match and match.group(1).casefold() not in existing_definitions:
            existing_definitions[match.group(1).casefold()] = line.strip()

    # If the model split one source person into an extra Subject but its own
    # definition cites a Picture that has exactly one authoritative Subject,
    # fold the orphan label back into that canonical Subject everywhere before
    # rebuilding the reference sections.  Do not guess when one Picture is
    # intentionally bound to multiple distinct entities.
    canonical_by_asset: dict[str, list[str]] = {}
    for item in model["definitions"]:
        if item["kind"] == "subject":
            canonical_by_asset.setdefault(item["asset"].casefold(), []).append(item["label"])
    expected_labels = {item["label"].casefold() for item in model["definitions"]}
    for orphan_key, line in tuple(existing_definitions.items()):
        if not orphan_key.startswith("<subject ") or orphan_key in expected_labels:
            continue
        assets = {item.casefold() for item in re.findall(r"<Picture\s+\d+>", line, re.IGNORECASE)}
        targets = {
            labels[0] for asset in assets
            for labels in (canonical_by_asset.get(asset, []),) if len(labels) == 1
        }
        if len(targets) == 1:
            orphan_label = re.match(r"\s*(<Subject\s+\d+>)", line, re.IGNORECASE).group(1)
            value = re.sub(re.escape(orphan_label), next(iter(targets)), value, flags=re.IGNORECASE)
    existing_definitions = {}
    for line in _section_body(value, "subject_definitions").splitlines():
        match = re.match(r"\s*(<(?:Subject|Picture|Video|Audio)\s+\d+>)", line, re.IGNORECASE)
        if match and match.group(1).casefold() not in existing_definitions:
            existing_definitions[match.group(1).casefold()] = line.strip()
    merged_definitions = []
    semantically_replaced: set[str] = set()
    for item in model["definitions"]:
        line = existing_definitions.get(item["label"].casefold(), item["line"])
        if item["kind"] == "subject":
            expected_role = str(item.get("role", "")).strip()
            subject_model = next(
                (subject for subject in model["subjects"] if subject["label"] == item["label"]),
                {},
            )
            expected_cues = tuple(subject_model.get("binding_cues", ()))
            role_words = re.findall(r"[\wÀ-ÿ'-]+", expected_role.casefold())
            role_is_specific = any(word not in {
                "the", "a", "an", "el", "la", "los", "las", "un", "una", "person", "persona",
                "people", "man", "men", "hombre", "hombres", "character", "personaje",
            } for word in role_words)
            cue_matches = [cue for cue in expected_cues if cue in line.casefold()]
            obvious_man_typo = (
                expected_role.casefold() == "man"
                and bool(re.search(r"\bmain\b", line, re.IGNORECASE))
            )
            if (obvious_man_typo
                    or (expected_cues and not cue_matches)
                    or (not expected_cues and role_is_specific and expected_role.casefold() not in line.casefold())):
                # Provenance alone is insufficient: an LLM may cite the right Picture while
                # assigning it to the wrong person.  Replace only a semantically mismatched
                # inferred definition; retain richer correct definitions and analysis.
                line = item["line"]
                semantically_replaced.add(item["label"].casefold())
            elif item["asset"].casefold() not in line.casefold():
                line = line.rstrip(". ") + f"; its source provenance is {item['asset']}."
        elif item["kind"] == "audio" and item.get("bound_subject"):
            if item["bound_subject"].casefold() not in line.casefold():
                line = item["line"]
        merged_definitions.append(line)
    value = _replace_section_body(value, "subject_definitions", "\n".join(merged_definitions))

    existing_retention: dict[str, str] = {}
    for line in _section_body(value, "retention_analysis").splitlines():
        match = re.match(r"\s*(<(?:Subject|Picture|Video|Audio)\s+\d+>)", line, re.IGNORECASE)
        if match and match.group(1).casefold() not in existing_retention:
            existing_retention[match.group(1).casefold()] = line.strip()
    merged_retention = []
    for item in model["definitions"]:
        line = existing_retention.get(item["label"].casefold(), "")
        marker_match = re.search(r"(:\s*)([a-z_]+)\b", line, re.IGNORECASE)
        if item["label"].casefold() in semantically_replaced:
            line = _default_retention_line(item)
        elif line and marker_match:
            line = line[:marker_match.start(2)] + item["marker"] + line[marker_match.end(2):]
        else:
            line = _default_retention_line(item)
        merged_retention.append(line)
    value = _replace_section_body(value, "retention_analysis", "\n".join(merged_retention))

    task_types = _reference_task_types(model, source_prompt, reference_context)
    summary = _section_body(value, "summary").strip()
    summary_tail = re.sub(r"^\[[^\]\r\n]+\]\s*", "", summary).strip()
    summary_tail = re.sub(
        r"^(?:(?:\+|/)\s*)?\[(?:reference generation|keyframe completion|video editing|"
        r"video continuation|audio reuse|audio reference)\]\s*",
        "",
        summary_tail,
        flags=re.IGNORECASE,
    ).strip()
    stale_task_tail = (
        r"(?:reference generation|keyframe completion|video editing|video continuation|audio reuse|audio reference)"
        r"(?:\s*(?:\+|/)\s*(?:reference generation|keyframe completion|video editing|video continuation|"
        r"audio reuse|audio reference))*[.!]?"
    )
    hallucinates_video = (
        not any(item["kind"] == "video" for item in model["definitions"])
        and bool(re.search(
            r"\bvideo\b[^.\r\n]{0,48}\b(?:edit(?:ed|ing)?|continuation|continues?)\b|<Video\s+\d+>",
            summary_tail,
            re.IGNORECASE,
        ))
    )
    if hallucinates_video or summary_tail.casefold() in {"placeholder", "n/a"} or re.fullmatch(
        stale_task_tail, summary_tail, re.IGNORECASE,
    ):
        summary_tail = ""
    if not summary_tail:
        summary_tail = _reference_summary_tail(model, task_types)
    value = _replace_section_body(value, "summary", f"[{' + '.join(task_types)}] {summary_tail}")
    voice_references = [
        item["label"] for item in model["definitions"]
        if item["kind"] == "audio" and item.get("voice_reference")
    ]
    if voice_references:
        detail = _section_body(value, "detailed_description")
        def _bound_lock(item):
            if item.get("unowned_voice"):
                return (
                    f"{item['label']} is the exclusive voice-timbre and delivery reference for a speaker who has "
                    "no reference asset; that character carries a stable voice description and its own speaker "
                    "ID, never the speaker ID of a defined Subject. Preserve that speaker identity without "
                    "copying the audio's original words or unrelated sounds."
                )
            if item.get("bound_voice_descriptor"):
                return (
                    f"{item['label']} is the exclusive voice-timbre and delivery reference for "
                    f"{item['bound_voice_descriptor']}, a speaker described only in prose who carries a stable "
                    "voice description and its own speaker ID rather than a Subject label; preserve that speaker "
                    "identity without copying the audio's original words or unrelated sounds."
                )
            if item.get("bound_subject"):
                m = re.search(r'\d+', item['bound_subject'])
                num = m.group() if m else "1"
                return (
                    f"{item['label']} is the exclusive voice-timbre and delivery reference for "
                    f"{item['bound_subject']} (S{num})'s newly generated "
                    "dialogue; preserve that speaker identity without copying the audio's original words or unrelated sounds."
                )
            return (
                f"{item['label']} is the exclusive voice-timbre and delivery reference for the speaking character's "
                "newly generated dialogue; preserve its speaker identity without copying its original words or unrelated sounds."
            )
        locks = " ".join(
            _bound_lock(item)
            for item in model["definitions"]
            if item["kind"] == "audio" and item.get("voice_reference")
        )
        detail = re.sub(
            r"\b(?:with\s+)?(?:a\s+)?(?:synthesi[sz]ed|synthetic|robotic|mechanical)"
            r"(?:,?\s+(?:slightly\s+)?(?:rough|metallic|processed))?\s+(?:voice|timbre)\b",
            "with the referenced voice timbre",
            detail,
            flags=re.IGNORECASE,
        )
        # Avoid assigning one tagged line twice (for example, "He speaks ...:
        # Arnold shouts, <d>..."). A duplicate attribution can weaken which
        # speaker is meant to inherit the reference voice.
        detail = re.sub(
            r"(\b(?:speaks?|says?|shouts?|whispers?)\b[^:\n]{0,180}:\s*)"
            r"[^<:\n]{1,100}\b(?:speaks?|says?|shouts?|whispers?)\s*,?\s*(?=<d>)",
            r"\1",
            detail,
            flags=re.IGNORECASE,
        )
        if locks not in detail:
            detail = locks + "\n" + detail.lstrip()
        value = _replace_section_body(value, "detailed_description", detail)
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


_TEXT_SPEAKER_VOCAL_ACTION = (
    r"(?:says?|said|asks?|asked|replies|replied|responds?|exclaims?|shouts?|screams?|whispers?|"
    r"sings?|calls?|adds?|answers?|speaks?|spoke|"
    r"dice|dicen|dijo|grita|gritan|responde|contesta|exclama|pregunta|susurra)"
)
# Scene nouns that routinely head an indefinite phrase near a speech verb. A
# speaker is a who, and none of these can be one.
_NON_SPEAKER_HEAD_NOUNS = frozenset({
    "table", "chair", "bed", "desk", "bench", "stool", "door", "window", "wall", "floor",
    "ceiling", "room", "building", "house", "hospital", "street", "road", "comic", "book",
    "magazine", "scroll", "page", "cover", "poster", "sign", "screen", "phone", "lamp",
    "light", "candle", "fire", "sword", "knife", "gun", "arm", "hand", "leg", "head", "face",
    "eye", "mouth", "voice", "sound", "noise", "song", "moment", "second", "minute", "hour",
    "day", "night", "scene", "shot", "camera", "mesa", "silla", "puerta", "ventana", "pared",
    "suelo", "sala", "edificio", "cama", "libro", "espada", "brazo", "mano", "voz",
})


_WEAK_DESCRIPTOR_WORDS = frozenset({
    "very", "big", "huge", "large", "the", "a", "an", "his", "her", "their", "its", "and", "with",
    "then", "first", "him", "them", "muy", "gran", "el", "la", "un", "una", "su", "y", "con",
})


def _definite_speaker_introduction(region: str, preceding: str) -> str:
    """Resolve "The old man ... says" back to the phrase that introduced him.

    A definite phrase at the speech verb is normally an asset-bound subject pointing back at its
    reference, which is why the indefinite scan skips it. But a source that defines its cast up
    front -- "a very old man, ... and a bulky very muscled man. ... The old man approaches him and
    says" -- refers back definitely from then on, and no reference asset is involved. Without this
    the speaker is simply lost, and the audio reference falls through to a description of the
    labelling rule itself, which H3 then renders as scene content.
    """
    definite = None
    for match in re.finditer(r"\b(?:the|el|la|los|las)\s+([\wÀ-ÿ'’-]+(?:\s+[\wÀ-ÿ'’-]+){0,3})",
                             region, flags=re.IGNORECASE):
        # Trailing predicate words are harmless here -- they simply score nothing against the
        # introductions -- so this only has to cut the connectives that would run two characters
        # together ("the old man and the doorman").
        phrase = re.split(
            rf"\s+(?:{_TEXT_SPEAKER_VOCAL_ACTION}|and|y|who|que|which|while|mientras)\b",
            match.group(1), maxsplit=1, flags=re.IGNORECASE,
        )[0].strip(" ,;:")
        if phrase and phrase.split()[0].casefold() not in _NON_SPEAKER_HEAD_NOUNS:
            definite = phrase
            break
    if not definite:
        return ""
    # Score the introductions by shared words rather than demanding an exact containment: the
    # definite phrase trails off into its predicate ("the bulky man opens the door") and no list of
    # verbs to cut at stays complete. The winner must be unambiguous, so a tie resolves to nothing
    # rather than to whichever character was introduced first.
    wanted = {word for word in re.findall(r"[\wÀ-ÿ'’-]+", definite.casefold())
              if word not in _WEAK_DESCRIPTOR_WORDS}
    ranked: list[tuple[int, str]] = []
    for match in re.finditer(r"\b(?:a|an|un|una)\s+([\wÀ-ÿ'’-]+(?:\s+[\wÀ-ÿ'’-]+){0,4})",
                             preceding, flags=re.IGNORECASE):
        candidate = re.split(r"\s*[,;]", match.group(1))[0].strip()
        words = {word.casefold() for word in re.findall(r"[\wÀ-ÿ'’-]+", candidate)}
        overlap = len(wanted & words)
        if overlap:
            ranked.append((overlap, candidate))
    if not ranked:
        return ""
    ranked.sort(key=lambda item: (-item[0], -len(item[1])))
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return ""
    # The word cap can land mid-modifier, and a dangling function word makes an unusable
    # voice description.
    return re.sub(r"(?:\s+(?:with|on|in|of|at|from|to|for|and|the|a|an|his|her|their|its|"
                  r"con|en|de|del|la|el|los|las|un|una|y|su))+$", "", ranked[0][1],
                  flags=re.IGNORECASE)


def _text_only_speaker_descriptors(
    source_prompt: str, bound_excerpts: tuple[str, ...] = (),
) -> list[str]:
    """Speakers the source introduces in prose only, with no reference asset.

    The official Ref2VA guide does not give these characters a ``<Subject N>``
    label: an audio whose speaker "does not correspond to a defined subject"
    takes "a stable voice description followed by ``(Sx)``" instead.  So they
    need a descriptor stable enough to reuse verbatim at every vocal event.

    The speaker is taken as the first indefinite noun phrase standing before the
    sentence's speech verb.  Indefinite because a definite phrase in a Ref2VA
    source normally points back at an asset-bound subject; before the verb
    because a phrase introduced afterwards ("says while holding a sword") is a
    prop of the utterance rather than its author.  Arbitrary distance is allowed
    between the two: a character is routinely introduced with a long trailing
    description before the sentence gets to what they say.
    """
    source = source_prompt or ""
    # Spoken content carries noun phrases of its own ("Es una herida superficial"),
    # and none of them is ever the speaker.
    masked = re.sub(
        r"[\"“”«»„][^\"“”«»„]*[\"“”«»„]", lambda match: " " * len(match.group(0)), source,
    )
    descriptors: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", masked):
        speech = None
        for candidate in re.finditer(
            rf"\b{_TEXT_SPEAKER_VOCAL_ACTION}\b", sentence, flags=re.IGNORECASE,
        ):
            # "the cover that says ..." is writing on a prop, not a character
            # speaking, and the noun phrase before it is scenery.
            if re.search(
                r"\b(?:that|which|who|que)\s*$|"
                r"\b(?:cover|sign|label|poster|screen|text|title|note|letter|banner|page|"
                r"portada|cartel|letrero)\s+\w*\s*$",
                sentence[:candidate.start()],
                flags=re.IGNORECASE,
            ):
                continue
            speech = candidate
            break
        if not speech:
            continue
        region = sentence[:speech.start()]
        # Scan determiner by determiner rather than matching whole phrases: a
        # rejected candidate must not consume the words after it, or "from a
        # doorway a soldier appears and says" loses the soldier with the doorway.
        for determiner in re.finditer(r"\b(?:a|an|un|una)\b", region, flags=re.IGNORECASE):
            # A noun phrase governed by a locative preposition is where the scene
            # happens, not who speaks in it.
            if re.search(
                r"\b(?:on|at|in|into|onto|over|under|behind|near|by|from|to|with|inside|beside|"
                r"en|desde|sobre|bajo|junto|tras|hacia|entre|delante|detr[aá]s)\s+$",
                region[:determiner.start()],
                flags=re.IGNORECASE,
            ):
                continue
            tail = re.match(
                r"\s+((?:[\wÀ-ÿ'’-]+)(?:\s+[\wÀ-ÿ'’-]+){0,4})", region[determiner.end():],
            )
            if not tail:
                continue
            # Stop at the predicate: the speaker is the noun phrase, not the
            # clause it goes on to perform.
            phrase = re.split(
                rf"\s+(?:{_TEXT_SPEAKER_VOCAL_ACTION}|and|y|who|que|which|while|mientras|"
                r"arrives?|appears?|enters?|runs?|walks?|comes?|steps?|stumbles?|staggers?|"
                r"llega|entra|aparece|camina|corre)\b",
                tail.group(1), maxsplit=1, flags=re.IGNORECASE,
            )[0]
            phrase = re.sub(r"\s+", " ", phrase).strip(" ,;:")
            # The word cap can land mid-modifier ("the man with a scar on"); a
            # dangling function word makes an unusable voice description.
            while re.search(
                r"\s+(?:with|on|in|of|at|from|to|for|and|the|a|an|his|her|their|its|"
                r"con|en|de|del|la|el|los|las|un|una|y|su)$", phrase, flags=re.IGNORECASE,
            ):
                phrase = re.sub(
                    r"\s+(?:with|on|in|of|at|from|to|for|and|the|a|an|his|her|their|its|"
                    r"con|en|de|del|la|el|los|las|un|una|y|su)$", "", phrase, flags=re.IGNORECASE,
                )
            if not phrase or _ASSET_REFERENCE_RE.search(phrase) or _REFERENCE_RE.search(phrase):
                continue
            if phrase.split()[0].casefold() in _NON_SPEAKER_HEAD_NOUNS:
                continue
            # "with the voice in audio 2" describes the delivery, not the speaker.
            if re.search(r"\b(?:voice|voz|timbre|tone|accent)\b", phrase, re.IGNORECASE):
                continue
            if any(phrase.casefold() in excerpt.casefold() for excerpt in bound_excerpts):
                continue
            descriptors.append("the " + phrase.casefold())
            break
        else:
            # Nothing indefinite before the verb: the speaker may still be a prose character the
            # source introduced earlier and now refers back to definitely.
            introduction = _definite_speaker_introduction(region, masked[:masked.index(sentence)])
            if introduction:
                descriptors.append("the " + introduction.casefold())
    return list(dict.fromkeys(descriptors))


def normalize_unassigned_subjects(text: str, source_prompt: str, reference_context: str = "") -> str:
    """Replace invented Subject labels with literal generated-character descriptions."""
    value = str(text)
    model = _official_reference_model(source_prompt, reference_context)
    if model["explicit"]:
        # Authoritative definitions carry no inferred subject list, so every label
        # would read as an orphan here and be rewritten away.
        return value
    allowed_subjects = {
        item["label"].casefold() for item in model["definitions"] if item["kind"] == "subject"
    }
    observed = list(dict.fromkeys(_REFERENCE_RE.findall(value)))
    orphan_subjects = [
        label for label in observed
        if label.casefold().startswith("<subject ") and label.casefold() not in allowed_subjects
    ]
    descriptors = _ordinary_generated_character_descriptors(source_prompt)
    # A prose-only speaker is a legitimate character that simply has no asset, so
    # its own descriptor stands in for the label the writer should never have used.
    descriptors += [
        descriptor for descriptor in model.get("text_speakers", ())
        if descriptor not in descriptors
    ]
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


def _implicit_shot_limit(source_prompt: str, mode: str = "t2va",
                         enhance_description: bool | None = None) -> int | None:
    """Keep strict continuity modes narrow without imposing a universal two-shot cap."""
    source = source_prompt or ""
    if _EXPLICIT_CUT_RE.search(source):
        return None
    if (mode == "fl2va" and enhance_description is not None) or _requires_single_continuous_progression(source):
        return 1
    if enhance_description is False or enhance_description is None:
        return 2
    return None


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
    for match in _SOURCE_QUOTED_RE.finditer(source):
        if _is_visible_text_quote(source, match):
            continue
        cue_window = source[max(0, match.start() - 180):match.start()]
        trailing_window = source[match.end():match.end() + 60]
        if (
            _SPEECH_CUE_RE.search(cue_window)
            or _INTERNAL_MONOLOGUE_CUE_RE.search(cue_window)
            or _SPEECH_CUE_RE.search(trailing_window)
        ):
            indices.append(1 + len(list(_CUT_COMMAND_RE.finditer(source, 0, match.start()))))
    return indices


def _source_requests_music(source_prompt: str) -> bool:
    source = source_prompt or ""
    if re.search(
        r"\b(?:no|without|avoid|omit|never|do\s+not\s+(?:add|use|include)|don't\s+(?:add|use|include)|"
        r"sin|evita|omite|nunca|no\s+(?:a[nñ]adas?|uses?|incluyas?))\b"
        r"[^.!?;]{0,48}\b(?:background\s+|non[- ]diegetic\s+)?(?:m[uú]sic|score|soundtrack|banda\s+sonora)\b",
        source, re.IGNORECASE,
    ):
        return False
    return bool(re.search(
        r"\b(?:background\s+music|non[- ]diegetic\s+music|audience[- ]only\s+music|m[uú]sica\s+de\s+fondo|"
        r"music|m[uú]sica|song|canci[oó]n|score|soundtrack|banda\s+sonora|underscore)\b",
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


_APPEARANCE_INTRODUCERS = r"wearing|dressed\s+in|carrying|holding|with|in|sporting|llevando|con|vestido\s+de"
_APPEARANCE_STOP_NOUNS = frozenset({
    "man", "woman", "boy", "girl", "person", "people", "character", "guy", "lady", "figure",
    "back", "front", "side", "hand", "hands", "head", "face", "left", "right", "one", "two",
    "voice", "scene", "shot", "camera", "video", "subject", "subjects", "door", "club",
    "hombre", "mujer", "chico", "chica", "persona", "escena", "voz", "puerta",
})


def _omitted_appearance_attributes(source_prompt: str, output: str) -> list[str]:
    """Concrete appearance nouns the source attached to a character and the output dropped.

    The explicit-fact checks are a catalogue -- numeric age, hair colour, mobility aid, intact
    object -- so they only ever notice what someone already thought to add. A bald head, a long
    white moustache and beard, a pink Hawaiian shirt and a tortoise shell went missing without a
    single complaint, because no rule named them. Deriving the attributes from the source instead
    needs no extending: whatever the user bothered to describe is what has to survive.

    Only the head noun of each fragment is required, so the writer stays free to rephrase around
    it, and the result is reported as a coverage gap the repair pass can close rather than a hard
    failure.
    """
    source = re.sub(r"[\"“”«»„][^\"“”«»„]*[\"“”«»„]", " ", source_prompt or "")
    text = (output or "").casefold()
    attributes: list[str] = []
    for fragment in re.finditer(
        rf"\b(?:{_APPEARANCE_INTRODUCERS})\s+([^.;!?]{{0,160}})", source, flags=re.IGNORECASE,
    ):
        for part in re.split(r",|\band\b|\by\b", fragment.group(1), flags=re.IGNORECASE):
            # "a huge tortoise shell on his back" is a shell, not a back: where the thing sits is
            # not the thing, and the body part it sits on is what the head-noun rule would take.
            part = re.split(
                r"\b(?:on|in|at|over|under|behind|around|across|sobre|en|bajo)\s+"
                r"(?:his|her|its|their|the|a|an|su|el|la)\b",
                part, maxsplit=1, flags=re.IGNORECASE,
            )[0]
            words = re.findall(r"[\wÀ-ÿ'’-]+", part)
            if not words:
                continue
            head = words[-1].casefold()
            if len(head) < 4 or head in _APPEARANCE_STOP_NOUNS or head in _NON_SPEAKER_HEAD_NOUNS:
                continue
            if head not in attributes:
                attributes.append(head)
    # A bare appositive carries no introducer at all -- "a very old man, bald, with ..." -- and is
    # exactly the kind of single distinctive word that goes missing without one.
    for appositive in re.finditer(
        rf"\b(?:{'|'.join(sorted(_APPEARANCE_STOP_NOUNS))})\s*,\s*([\wÀ-ÿ'’-]+)\s*,",
        source, flags=re.IGNORECASE,
    ):
        head = appositive.group(1).casefold()
        if len(head) >= 4 and head not in _APPEARANCE_STOP_NOUNS and head not in attributes:
            attributes.append(head)
    missing = [
        attribute for attribute in attributes
        if not re.search(rf"\b{re.escape(attribute)}(?:s|es)?\b", text)
        and not re.search(rf"\b{re.escape(attribute.rstrip('s'))}(?:s|es)?\b", text)
    ]
    if not missing:
        return []
    return [
        "Source appearance detail dropped: describe "
        + ", ".join(missing[:8])
        + " on the character the source attached them to"
    ]


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

    intact_owners = re.findall(
        r"\b(?:intact|undamaged)\s+(?:(?:black|blue|brown|green|gr[ae]y|red|silver|white|yellow)\s+)?"
        r"([\wÀ-ÿ'-]+)\b",
        source,
        re.IGNORECASE,
    )
    for owner in intact_owners:
        if not re.search(
            rf"(?:\b(?:intact|undamaged)\b.{{0,35}}\b{re.escape(owner)}\b|"
            rf"\b{re.escape(owner)}\b.{{0,50}}\b(?:intact|undamaged)\b)",
            text,
            re.IGNORECASE,
        ):
            errors.append(f"Explicit intact state must remain attached to {owner!r}")

    damage_owners = {
        owner.casefold()
        for _modifier, owner in re.findall(
            r"\b([\wÀ-ÿ]+-damaged)\s+([\wÀ-ÿ'-]+)\b", source, re.IGNORECASE,
        )
    }
    if damage_owners:
        transfer_patterns = (
            r"\b([\wÀ-ÿ'-]+)\b,\s*which\b[^.!?\r\n]{0,80}\b(?:shows?|bears?|has)\s+"
            r"(?:visible\s+|clear\s+)?(?:signs?\s+of\s+)?(?:minor\s+|storm\s+)?(?:damage|weathering|wear)\b",
            r"\b([\wÀ-ÿ'-]+)\b(?:,\s*which)?\s+(?:shows?|bears?|has)\s+"
            r"(?:visible\s+|clear\s+)?(?:signs?\s+of\s+)?(?:minor\s+|storm\s+)?(?:damage|weathering|wear)\b",
            r"\b([\wÀ-ÿ'-]+)\b\s+is\s+(?:visibly\s+|slightly\s+|also\s+|similarly\s+)?"
            r"(?:damaged|weathered)\b",
            r"\b(?:damage|weathering)\s+(?:on|to|of)\s+(?:the\s+)?([\wÀ-ÿ'-]+)\b",
        )
        unauthorized_targets = set()
        for pattern in transfer_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                target = match.group(1)
                if target.casefold() in {"also", "still", "similarly", "which", "it", "this", "that"}:
                    continue
                clause_start = max(
                    text.rfind(".", 0, match.start()), text.rfind("!", 0, match.start()),
                    text.rfind("?", 0, match.start()), text.rfind("\n", 0, match.start()),
                )
                clause_prefix = text[clause_start + 1:match.start()].casefold()
                if target.casefold() not in damage_owners and not any(
                    re.search(rf"\b{re.escape(owner)}\b", clause_prefix) for owner in damage_owners
                ):
                    unauthorized_targets.add(target)
        unauthorized = sorted(unauthorized_targets)
        if unauthorized:
            errors.append(
                "A source-owned damage state was transferred to an unauthorized subject or object: "
                + repr(unauthorized)
                + "; keep damage attached only to " + repr(sorted(damage_owners))
            )

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
    for match in re.finditer(
        r"\b(?:intact|undamaged)\s+(?:(?:black|blue|brown|green|gr[ae]y|red|silver|white|yellow)\s+)?"
        r"([\wÀ-ÿ'-]+)\b",
        source,
        re.IGNORECASE,
    ):
        facts.append(
            f"Preserve the explicit intact state of {match.group(1)!r}; do not add damage, weathering, wear, "
            "breakage, dents, scratches, or missing parts to it."
        )
    for match in re.finditer(
        r"\b([\wÀ-ÿ]+-(?:damaged|haired|colou?red|painted|covered|stained|marked|scarred|"
        r"worn|weathered|broken|lit))\s+([\wÀ-ÿ'-]+)\b",
        source,
        flags=re.IGNORECASE,
    ):
        modifier, owner = match.groups()
        facts.append(
            f"Preserve exact attribute ownership: {modifier!r} modifies only {owner!r}. Do not transfer that "
            "condition, appearance, damage, wear, color, or material state to any other person, garment, object, "
            "vehicle, prop, or location merely because it shares the scene."
        )
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
                       instrumental_style: str = "none",
                       acoustic_space: str = "none",
                       dialogue_coverage: str = "off",
                       dialogue_language: str = "auto",
                       editing_intent: str = "none",
                       invent_scene: bool = False) -> str:
    if ambience_foley_policy not in AMBIENCE_FOLEY_POLICIES:
        raise ValueError(f"Unsupported ambience/foley policy {ambience_foley_policy!r}")
    if background_score_policy not in BACKGROUND_SCORE_POLICIES:
        raise ValueError(f"Unsupported background-score policy {background_score_policy!r}")
    if voice_performance not in VOICE_PERFORMANCES:
        raise ValueError(f"Unsupported voice performance {voice_performance!r}")
    if instrumental_style not in INSTRUMENTAL_STYLE_CHOICES:
        raise ValueError(f"Unsupported instrumental style {instrumental_style!r}")
    if acoustic_space not in ACOUSTIC_SPACE_CHOICES:
        raise ValueError(f"Unsupported acoustic space {acoustic_space!r}")
    if dialogue_coverage not in DIALOGUE_COVERAGE_CHOICES:
        raise ValueError(f"Unsupported dialogue coverage {dialogue_coverage!r}")
    if aspect_ratio not in ASPECT_RATIOS:
        raise ValueError(f"Unsupported aspect ratio {aspect_ratio!r}")
    if editing_intent not in EDITING_INTENT_CHOICES:
        raise ValueError(f"Unsupported editing intent {editing_intent!r}")
    resolved = resolve_mode(mode, reference_context, basic_prompt, media_manifest, editing_intent=editing_intent)
    active_enhancement_profile = enhancement_profile(enhance_description, invent_scene)
    dialogue_authoring, dialogue_authoring_language = _dialogue_authoring_request(
        basic_prompt, override_language=dialogue_language
    )
    profile = generation_profile(duration_seconds, aspect_ratio, frame_count)
    effective_duration = profile["effectiveDurationSeconds"]
    creative_treatment = parse_creative_treatment(
        creative_treatment_json, enabled=bool(enhance_description),
    )
    content_format = resolve_content_format(
        creative_treatment.get("contentFormat", "none"),
        enabled=bool(enhance_description), source_prompt=basic_prompt,
        voice_performance=voice_performance, background_score_policy=background_score_policy,
        mode=resolved, duration_seconds=effective_duration,
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
        f"ENHANCEMENT PROFILE: {active_enhancement_profile}",
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
    creative_treatment, _treatment_conflicts = resolve_treatment_conflicts(creative_treatment, cinematography)
    resolved_style = resolve_visual_style(creative_treatment, cinematography)
    style_contract = resolved_visual_style_instruction(resolved_style, cinematography, resolved)
    if style_contract:
        parts.append(
            style_contract
            + "\nSELECTED AUDIO CONTROLS (authoritative over every style-bible sound suggestion): "
            f"ambience_foley_policy={ambience_foley_policy}; "
            f"background_score_policy={background_score_policy}; "
            f"voice_performance={voice_performance}."
        )
    format_contract = content_format_instruction(content_format)
    if format_contract:
        parts.append(
            format_contract
            + "\nSELECTED AUDIO CONTROLS (authoritative over format sound suggestions): "
            f"ambience_foley_policy={ambience_foley_policy}; "
            f"background_score_policy={background_score_policy}; "
            f"voice_performance={voice_performance}."
        )
    title_style_contract = title_screen_style_instruction(creative_treatment, basic_prompt)
    if title_style_contract:
        parts.append(title_style_contract)
    explicit_plan_contract = shot_plan_instruction(explicit_shot_plan, resolved)
    if explicit_plan_contract:
        parts.append(explicit_plan_contract)
    if reference_context.strip():
        parts.append("REFERENCE CONTEXT (authoritative labels and roles):\n" + reference_context.strip())
    positional_contract = _official_reference_contract(
        basic_prompt,
        "\n".join(part for part in (str(reference_context).strip(), connected_context) if part),
    )
    if positional_contract:
        parts.append(positional_contract)
    if editing_intent in EDITING_INTENT_CONTRACTS:
        parts.append(EDITING_INTENT_CONTRACTS[editing_intent])

    ambience_contracts = {
        "auto": (
            "AMBIENCE AND FOLEY POLICY — AUTO: Preserve requested ambience, physical sounds, and non-verbal human "
            "sounds. With description enhancement, add only coherent physically motivated non-vocal sounds."
        ),
        "ensure_audible": (
            "AMBIENCE AND FOLEY POLICY — REQUIRED: Create a coherent non-vocal soundscape across the duration using "
            "room tone, environmental ambience, physically motivated foley, impacts with concrete material resonance "
            "(solid wood, metallic ring, glass shatter, surface friction), movement, and appropriate non-verbal human sounds. "
            "Do not invent intelligible background speech."
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
    if acoustic_space != "none":
        parts.append(
            "DIEGETIC ACOUSTIC SPACE — AUTHORITATIVE OVER EVERY TREATMENT SOUND SUGGESTION: Render the diegetic "
            "sound that the ambience/foley and voice policies already permit inside the selected acoustic space. It "
            "changes how existing sounds are heard; it may not add a sound source, room, location, weather, event, "
            "or dialogue, and it never re-enables a disabled audio layer.\n"
            f"Selected acoustic space: {acoustic_space}.\n"
            + ACOUSTIC_SPACE_CONTRACTS[acoustic_space]
            + "\nACOUSTIC SPACE OUTPUT: Write the resulting reflections, decay, distance, localization, and "
            "frequency response as concrete audible prose in overall_soundscape, or compactly inside every autonomous "
            "chained item. Do not name the preset, repeat its ID, or state that an acoustic space is applied."
        )
    if dialogue_coverage == "on" and voice_performance != "none":
        parts.append(
            "DIALOGUE COVERAGE — REQUIRED: " + DIALOGUE_COVERAGE_CONTRACT + " Achieve it inside the existing shot "
            "boundaries through framing, blocking, and focus; do not add a cut, character, line, or camera control "
            "that the authoritative content and explicit controls do not allow."
        )
    requested_instrumental = str(instrumental_description or "").strip()
    if background_score_policy == "add_instrumental" and instrumental_style != "none":
        parts.append(
            "INSTRUMENTAL MUSIC GENRE / STYLE — AUTHORITATIVE ARRANGEMENT GRAMMAR: Adapt the user's score "
            "description and the scene's dramatic function into the selected musical language. Preserve explicit tempo, "
            "meter, rhythmic events, dynamics, structural timing, entry/exit points, and requested instruments wherever "
            "compatible; re-orchestrate only what is necessary to make the selection coherent. Express the result as "
            "concrete audible musical parameters, not as a genre label. The score remains audience-only and strictly "
            "instrumental, with no singing, lyrics, speech, chants, choir, or vocal samples.\n"
            + INSTRUMENTAL_PRODUCTION_BIBLE + "\n"
            + "MUSICAL-LANGUAGE OVERLAY:\n" + INSTRUMENTAL_STYLE_CONTRACTS[instrumental_style]
            + "\nThe overlay above is the arrangement grammar you execute, never text to emit: H3 reads "
            "non_diegetic_music as a description of the audible score, so reproducing a directive there "
            "would hand it instructions instead of music.\n"
            + "SCORE OUTPUT: In structured single-generation output, write the resolved "
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
    if bool(enhance_description):
        # Keep this after source, reference, shot-plan, cinematography and audio authority have been
        # established, but before the chained early return so every output mode receives it once.
        parts.append(EMOTIONAL_PERFORMANCE_CONTRACT)
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
        dialogue_contracts = _source_dialogue_contracts(basic_prompt, override_language=dialogue_language)
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
            "ACTIVE DIRECTORIAL ENHANCEMENT — ENHANCED_PRODUCTION (develop the request, without changing it):\n"
            "- Preserve every locked fact, identity, reference role, spoken line, visible text, endpoint, and explicit "
            "control. You are explicitly allowed to choose missing non-narrative production details that make the "
            "requested action legible: composition, blocking, screen direction, shot scale, lens and focus, "
            "source-consistent lighting and grade, material behavior, micro-performance, and physically caused sound.\n"
            "- Ordinary background detail may establish space, scale, atmosphere, or continuity only when it remains "
            "subordinate and does not become a new subject, prop, event, light source, or sound cue. Develop physical "
            "sound only as permitted by the ambience/foley policy; musical treatment is governed exclusively by the "
            "background-score policy.\n"
            "- At the beginning of every shot, establish a useful shot scale and the current frame positions, "
            "orientation, eyelines, and relevant prop states. Across cuts preserve screen direction, handed contact, "
            "object possession, pose continuity, and states such as open/closed or intact/changed unless the requested "
            "action visibly changes them.\n"
            "- When the source contains physical interaction, describe the actor, limb or manipulated object, point of "
            "contact, physically readable response, and resulting state. Complete requested actions and let their "
            "visible results register before the final frame unless the source explicitly requests interruption.\n"
            "- Prefer observable geometry, materials, position, movement, and cause-and-effect over generic cinematic "
            "adjectives or unrelated background activity.\n"
            "- Spend descriptive detail in this order: source-supported subject and prop identity; readable spatial "
            "layout; the opening state; action mechanics and contact; visible material response; reaction and final "
            "state; then camera, focus, lighting, and atmosphere that make those facts easier to read. Describe scale, "
            "surface, rigidity, weight, reflection, deformation, particles, or weather only when already implied by "
            "the source or when they clarify an existing object's behavior.\n"
            "- Give important actions a causal envelope: preparation, onset, contact or turning point, immediate "
            "response, and settling consequence, fitted to the available duration. Synchronize permitted diegetic "
            "sound to the visible cause and resulting space without adding a new source or event.\n"
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
            # Under invented_production this blanket ban contradicted the profile that had just
            # asked for supporting subjects and background life, and being the nearer, more concrete
            # instruction it won: the toggle changed a label and nothing else. What stays locked is
            # what belongs to the user -- reference identity, quoted words, the ending -- not the
            # existence of a passer-by the profile was invited to add.
            + (
                "- " if active_enhancement_profile == "invented_production" else
                "- Do not invent new characters, plot events, branded objects, reference assets, or an "
                "ending that changes the user's intent. "
            )
            + (
                "Author dialogue only within the explicit dialogue-writing brief above. "
                if dialogue_authoring and voice_performance == "audible" else
                "Do not invent dialogue. "
            )
            + "Do not increase gore, damage, or explicitness beyond the source."
        )
        if resolved == "ref2va":
            parts.append(
                "REF2VA ADAPTIVE DESCRIPTION BUDGET: For ordinary generation, 350-500 English words in "
                "detailed_description is a soft target, never a ceiling. Exceed 500 when complete dialogue, more than "
                "two information-bearing shots, multiple independent reference roles, repeated transformations, or "
                "complex source timing genuinely require it. Video editing scales with source complexity and has no "
                "word target. Stop adding detail when coverage is complete; stay within 7000 characters only when the "
                "delivery target is MiniMax API v2. "
                "Spend the available budget on exact reference application, composition, "
                "source-supported appearance, spatial continuity, action mechanics, observable state changes, "
                "audio-visual synchronization, and the final state in playback order. Do not count "
                "subject_definitions, summary, retention_analysis, soundscape, or music toward this target. Never "
                "pad with synonyms, repeated definitions, decorative lore, extra subjects, actions, sounds, shots, "
                "or camera moves."
            )
        else:
            parts.append(
                "BASE DESCRIPTION DEPTH — USEFUL DENSITY, NO WORD-COUNT TARGET: Make "
                "integrated_multimodal_description detailed enough to stage every requested beat and its visible "
                "result, but do not force it to 350-500 words and do not aim to fill the 7000-character API ceiling. "
                "A simple single action may remain compact; use more detail only when duration, interaction, dialogue, "
                "continuity, or transformation creates more information to resolve. Remove any sentence that does not "
                "clarify an authoritative fact, spatial relationship, causal beat, material response, performance, "
                "camera decision, or permitted sound."
            )
    else:
        parts.append(
            "CONSERVATIVE FORMAT ADAPTATION — CONSERVATIVE_GROUNDED:\n"
            "Do not preserve terseness when H3 needs missing executable structure. Add only the smallest "
            "non-narrative information required by the selected mode: opening composition and spatial relations; "
            "initial body, object, and frame-anchor state; each requested action in order; visible causal transition "
            "and result; neutral camera continuity; and requested or directly caused sound. Do not choose decorative "
            "styling, set dressing, new props, new events, new light sources, or new sound sources. Keep creative "
            "treatment disabled, but apply explicit cinematography, shot-plan, reference, and audio controls literally."
        )
    dialogue_contracts = _source_dialogue_contracts(basic_prompt, override_language=dialogue_language)
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
            "their lips or leaves the frame, then continue only requested ambience or non-verbal sound directly "
            "caused by existing visible actions. Do not invent extra sound sources merely to fill time. No character "
            "speaks additional words."
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
    elif _implicit_shot_limit(basic_prompt, resolved, enhance_description) == 2:
        parts.append(
            "SHOT BUDGET: The source supplied no explicit cut or montage structure. Prefer one continuous shot and use "
            "at most two shots only if one motivated cut materially improves viewpoint or information. Never divide the "
            "duration into evenly spaced shots merely to fill time; actions and reveals are beats inside a shot."
        )
    elif not explicit_shot_plan["provided"] and bool(enhance_description):
        parts.append(
            "ADAPTIVE SHOT BUDGET: Infer the smallest sufficient shot plan from duration and information load. There "
            "is no automatic two-shot ceiling: use an additional cut only when it contributes a distinct viewpoint, "
            "time, location, scale, reference application, or state transition that a motivated continuous move "
            "cannot show clearly. FL2VA and explicit continuous-progressions remain single-take constraints."
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


def treatment_warning_report(creative_treatment_json: str = "", cinematography_json: str = "",
                             shot_plan_json: str = "", duration_seconds: float = 0.0,
                             frame_count: int = 0, mode: str = "t2va",
                             enhance_description: bool = True) -> str:
    """Render every creative-direction note as the plain text a node output can show."""
    treatment = parse_creative_treatment(creative_treatment_json, enabled=bool(enhance_description))
    cinematography = parse_cinematography(cinematography_json)
    profile = generation_profile(duration_seconds, "auto", frame_count)
    plan = parse_shot_plan(shot_plan_json, profile["effectiveDurationSeconds"], 0, mode)
    return "\n".join(treatment_warnings(treatment, cinematography, plan))


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
    # H3 reads these markers literally, so a shouted <SCENETRANS>/<CUTOFF> is canonicalized
    # rather than left to evade the pairing and placement checks.
    value = re.sub(
        r"<(scenetrans|cutoff)>",
        lambda match: f"<{match.group(1).lower()}>",
        str(text),
        flags=re.IGNORECASE,
    )
    def _add_detected_tag(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        lang = _detect_language(inner, default="English")
        return f"<d>[{lang}] {inner}</d>"

    value = re.sub(
        r"<d>\s*(?!\[[^\]]+\])(.*?)\s*</d>",
        _add_detected_tag,
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    def _replace_original_language(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        lang = _detect_language(inner, default="English")
        return f"<d>[{lang}] {inner}</d>"

    value = re.sub(
        r"<d>\s*\[(?:original\s+language|language)\]\s*(.*?)\s*</d>",
        _replace_original_language,
        value,
        flags=re.IGNORECASE | re.DOTALL,
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


def _source_dialogue_language(source_prompt: str, quote_match, quote_text: str = "", override_language: str = "auto") -> str:
    if override_language and override_language.casefold() not in {"auto", "none", "original language"}:
        return _LANGUAGE_ALIASES.get(override_language.casefold(), override_language.capitalize())
    # A delivery/language clause can govern a short sequence of interrupted
    # lines (line, sigh, pause, line, cut, line).  Keep enough preceding prose
    # to retain that scope without looking beyond the current paragraph.
    paragraph_start = (source_prompt or "").rfind("\n", 0, quote_match.start()) + 1
    window = (source_prompt or "")[max(paragraph_start, quote_match.start() - 700):quote_match.start()]
    trailing = (source_prompt or "")[quote_match.end():quote_match.end() + 80]
    matches = re.findall(
        r"\b(?:in|en|auf|em|in\s+het|in\s+'t)\s+(?:(?:the\s+|het\s+|das\s+)?([\wÀ-ÿ-]+)\s+(?:language|idioma|taal|sprache)|"
        r"(?:language|idioma|taal|sprache)\s+([\wÀ-ÿ-]+))",
        window,
        flags=re.IGNORECASE,
    )
    if matches:
        raw = re.sub(r"\s+", " ", next((part for part in matches[-1] if part), "")).strip()
        return _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize()) or "English"
    known = re.findall(
        rf"\b(?:in|en|auf|em|in\s+het|in\s+'t|en\s+el|en\s+la)\s+({_DIALOGUE_LANGUAGE_PATTERN})",
        window,
        flags=re.IGNORECASE,
    )
    if known:
        raw = re.sub(r"\s+", " ", known[-1]).strip()
        return _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize()) or "English"
    qualified = re.findall(
        rf"\b(?:in|en|auf|em|in\s+het|in\s+'t|en\s+el|en\s+la)\s+(?:the\s+|het\s+|das\s+)?{_QUALIFIED_DIALOGUE_LANGUAGE_PATTERN}",
        window,
        flags=re.IGNORECASE,
    )
    if qualified:
        raw = re.sub(r"\s+", " ", qualified[-1]).strip()
        return _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize()) or "English"
    trailing_known = re.match(
        rf"^\s*(?:,\s*)?(?:in|en|auf|em|in\s+het|in\s+'t|en\s+el|en\s+la)\s+({_DIALOGUE_LANGUAGE_PATTERN})",
        trailing,
        flags=re.IGNORECASE,
    )
    if trailing_known:
        raw = trailing_known.group(1)
        return _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize())
    trailing_qualified = re.match(
        rf"^\s*(?:,\s*)?(?:in|en|auf|em|in\s+het|in\s+'t|en\s+el|en\s+la)\s+(?:the\s+|het\s+|das\s+)?{_QUALIFIED_DIALOGUE_LANGUAGE_PATTERN}",
        trailing,
        flags=re.IGNORECASE,
    )
    if trailing_qualified:
        raw = trailing_qualified.group(1)
        return _LANGUAGE_ALIASES.get(raw.casefold(), raw.capitalize())

    quote = quote_text or _extract_quote_string(quote_match)
    detected_from_quote = _detect_language(quote, default="")
    if detected_from_quote and detected_from_quote != "English":
        return detected_from_quote
    detected_from_prompt = _detect_language(source_prompt, default="English")
    if detected_from_prompt != "English":
        return detected_from_prompt
    return detected_from_quote or "English"


def _source_quote_is_internal_monologue(source_prompt: str, quote_match) -> bool:
    window = (source_prompt or "")[max(0, quote_match.start() - 180):quote_match.start()]
    thought_cues = list(_INTERNAL_MONOLOGUE_CUE_RE.finditer(window))
    if not thought_cues:
        return False
    # "he seems to think for a bit and then says ..." describes a visible
    # pause before ordinary speech, not an internal-monologue voiceover.  A
    # later explicit vocal verb therefore closes the thought-cue scope.
    later_speech = _SPEECH_CUE_RE.search(window, thought_cues[-1].end())
    return not bool(later_speech)


def _dialogue_lexical_key(quote: str) -> str:
    """Recognize an authored cue through the drift a writer model introduces.

    A local model retyping Spanish routinely drops accents or adds a comma, and an
    exact key then fails to recognize its own source line: the quote stays
    untagged, the validator objects, and every repair attempt reproduces the same
    near-miss. Only this lookup key is loosened -- the authored wording is
    restored verbatim from the contract, so a match repairs the drift rather than
    blessing it.
    """
    value = unicodedata.normalize("NFD", str(quote)).casefold()
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^\w\s]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _source_dialogue_contracts(source_prompt: str, override_language: str = "auto") -> list[tuple[str, str, bool]]:
    contracts = []
    for match in _SOURCE_QUOTED_RE.finditer(source_prompt or ""):
        if _is_visible_text_quote(source_prompt, match):
            continue
        prefix = (source_prompt or "")[:match.start()]
        boundary = max(prefix.rfind(mark) for mark in ".!?;\n")
        cue_window = prefix[boundary + 1:]
        quote_text = _extract_quote_string(match)
        trailing_window = (source_prompt or "")[match.end():match.end() + 60]
        repeated_previous = bool(
            contracts
            and (
                re.search(r"\b(?:again|otra\s+vez|de\s+nuevo)\b", cue_window, re.IGNORECASE)
                or re.search(r"\b(?:again|otra\s+vez|de\s+nuevo)\b", trailing_window, re.IGNORECASE)
            )
            and _dialogue_lexical_key(contracts[-1][1]) == _dialogue_lexical_key(quote_text)
        )
        has_speech_cue = bool(
            _SPEECH_CUE_RE.search(cue_window)
            or _INTERNAL_MONOLOGUE_CUE_RE.search(cue_window)
            or _SPEECH_CUE_RE.search(trailing_window)
            or _INTERNAL_MONOLOGUE_CUE_RE.search(trailing_window)
            or repeated_previous
        )
        if has_speech_cue:
            contracts.append((
                _source_dialogue_language(source_prompt, match, quote_text=quote_text, override_language=override_language),
                quote_text,
                _source_quote_is_internal_monologue(source_prompt, match),
            ))
    for language, quote in re.findall(
        r"<d>\s*\[([^\]]+)\]\s*(.*?)\s*</d>", source_prompt or "", flags=re.DOTALL | re.IGNORECASE,
    ):
        lang = _LANGUAGE_ALIASES.get(language.strip().casefold(), language.strip().capitalize())
        contracts.append((lang, quote.strip(), False))

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
        shot_start = value.rfind("[Shot", 0, dialogue.start())
        shot_start = 0 if shot_start < 0 else shot_start
        prior_shot_subjects = list(re.finditer(
            r"<Subject\s+\d+>", value[shot_start:sentence_start], flags=re.IGNORECASE,
        ))
        actor_match = re.search(
            rf"\b((?:The|An?|This)\s+[\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){{0,4}}|He|She|They)\s+"
            rf"(?:\(S\d+(?:\s*,\s*S\d+)*\)\s*)?(?={vocal_action}\b)",
            prefix,
            flags=re.IGNORECASE,
        )
        if subject_matches:
            identity = subject_matches[-1].group(0).casefold()
            last_concrete_identity = identity
        elif actor_match and actor_match.group(1).casefold() not in {"he", "she", "they"}:
            identity = re.sub(r"\s+", " ", actor_match.group(1).casefold())
            last_concrete_identity = identity
        elif actor_match and prior_shot_subjects:
            # Resolve a pronoun from the nearest explicit Subject in the same
            # shot.  This prevents an LLM-authored ``He (S5)`` from escaping
            # canonical Subject/Speaker numbering merely because the Subject
            # name was in the preceding sentence.
            identity = prior_shot_subjects[-1].group(0).casefold()
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
            subject_number = re.fullmatch(r"<subject\s+(\d+)>", identity, flags=re.IGNORECASE)
            canonical_id = int(subject_number.group(1)) if subject_number else identity_ids.get(identity)
            if canonical_id is None:
                identity_ids[identity] = explicit_id
            elif canonical_id != explicit_id:
                prefix = prefix[:explicit.start()] + f"(S{canonical_id})" + prefix[explicit.end():]
                explicit_id = canonical_id
                identity_ids[identity] = canonical_id
            action_match = re.search(vocal_action, prefix, flags=re.IGNORECASE)
            if action_match and explicit.start() > action_match.start() and (subject_matches or actor_match):
                cleaned = (prefix[:explicit.start()] + prefix[explicit.end():]).rstrip() + " "
                clean_subjects = list(re.finditer(r"<Subject\s+\d+>", cleaned, flags=re.IGNORECASE))
                clean_actor = re.search(
                    rf"\b((?:The|An?|This)\s+[\wÀ-ÿ'-]+(?:\s+[\wÀ-ÿ'-]+){{0,4}}|He|She|They)\s+"
                    rf"(?:\(S\d+(?:\s*,\s*S\d+)*\)\s*)?(?={vocal_action}\b)",
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
        subject_number = re.fullmatch(r"<subject\s+(\d+)>", identity, flags=re.IGNORECASE)
        speaker_id = int(subject_number.group(1)) if subject_number else identity_ids.get(identity)
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
        # A tagged line is routinely mid-sentence -- "S2 says <d>...</d>, his deep voice resonating
        # against the backdrop." -- so anchoring the boundary to the tag cuts that sentence in two
        # and its second half travels to H3 as a stray fragment. Anchor it to the end of the
        # sentence the tag sits in instead.
        tail = value[end:]
        if not re.match(r"\s*(?:$|\n)", tail) and not value[:end].rstrip().endswith((".", "!", "?")):
            terminator = re.search(r"[.!?](?=\s|$)", tail)
            if terminator:
                end += terminator.end()
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
    # Drop an accidental raw-source suffix from the soundscape.  Small local
    # models occasionally concatenate their input after a truncated final
    # sentence (``...physicalScene in ...``).  Match a substantial source
    # prefix so ordinary shared wording cannot trigger this repair.
    source_prefix = re.sub(r"\s+", " ", (source_prompt or "").strip())[:64].strip()
    if len(source_prefix) >= 40:
        echo_pattern = re.escape(source_prefix).replace(r"\ ", r"\s+")
        echo = re.search(echo_pattern, soundscape, flags=re.IGNORECASE)
        if echo:
            soundscape = soundscape[:echo.start()].rstrip()
            if soundscape and soundscape[-1] not in ".!?":
                last_boundary = max(soundscape.rfind("."), soundscape.rfind("!"), soundscape.rfind("?"))
                soundscape = soundscape[:last_boundary + 1].rstrip() if last_boundary >= 0 else ""
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
    expected_keys = {_dialogue_lexical_key(quote) for _language, quote, _internal in contracts}

    def repair_swallowed_directions(match: re.Match[str]) -> str:
        inner = re.sub(r"^\s*\[[^\]]+\]\s*", "", match.group(1), flags=re.IGNORECASE).strip()
        if _dialogue_lexical_key(inner) in expected_keys:
            return match.group(0)
        looks_like_scene_prose = bool(
            len(inner) >= 120
            and re.search(r"\b(?:image|picture|shot|scene)\s*\d+\b", inner, re.IGNORECASE)
            and _SPEECH_CUE_RE.search(inner)
        )
        if not looks_like_scene_prose:
            return match.group(0)
        # This exact corruption is caused by an orphan source quote shifting
        # every later quote boundary.  Restore only source-authorized words, in
        # their original order; the repair pass can still improve placement.
        return " ".join(f"<d>[{language}] {quote}</d>" for language, quote, _internal in contracts)

    value = re.sub(
        r"<d>(.*?)</d>", repair_swallowed_directions, value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if any(internal for _language, _quote, internal in contracts):
        value = _remove_internal_monologue_placeholders(value)
        value = re.sub(
            r"says in an off-screen internal monologue",
            "says in an off-screen voiceover, as a concentrated internal monologue",
            value,
            flags=re.IGNORECASE,
        )

    # Temporal references to the one exact line are not additional vocal actions. Canonicalize the
    # common phrases local models emit so validation does not mistake "after speaking" for a second,
    # untagged line; concrete vocal delivery still belongs in the sentence containing <d>.
    value = re.sub(r"\bafter\s+speaking\b", "after the tagged line", value, flags=re.IGNORECASE)
    value = re.sub(r"\bbefore\s+speaking\b", "before the tagged line", value, flags=re.IGNORECASE)
    value = re.sub(r"\bwhile\s+speaking\b", "during the tagged line", value, flags=re.IGNORECASE)

    remaining = list(contracts)

    def take_contract(candidate: str):
        key = _dialogue_lexical_key(candidate)
        for index, contract in enumerate(remaining):
            if _dialogue_lexical_key(contract[1]) == key:
                return remaining.pop(index)
        return None

    def canonicalize_tag(match: re.Match[str]) -> str:
        inner = re.sub(r"^\s*\[[^\]]+\]\s*", "", match.group(1), flags=re.IGNORECASE).strip()
        contract = take_contract(inner)
        if contract:
            language, quote, _internal = contract
            return f"<d>[{language}] {quote}</d>"
        if any(
            _dialogue_lexical_key(inner) == _dialogue_lexical_key(_extract_quote_string(m))
            for m in _SOURCE_QUOTED_RE.finditer(source_prompt or "")
            if _is_visible_text_quote(source_prompt, m)
        ):
            return f'"{inner}"'
        tag_match = re.match(r"^\s*\[([^\]]+)\]\s*(.*)", match.group(1).strip(), flags=re.DOTALL)
        if tag_match and tag_match.group(1).strip().casefold() == "original language":
            detected = _detect_language(tag_match.group(2).strip(), default="English")
            return f"<d>[{detected}] {tag_match.group(2).strip()}</d>"
        return match.group(0)

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


def normalize_multishot_audio_policy(text: str, ambience_foley_policy: str = "auto",
                                     background_score_policy: str = "follow_prompt",
                                     voice_performance: str = "audible",
                                     source_context: str = "") -> str:
    """Apply the same audio gates to every autonomous chained prompt item."""
    try:
        data = json.loads(str(text))
    except json.JSONDecodeError:
        return str(text)
    prompts = data.get("prompts") if isinstance(data, dict) else None
    if not isinstance(prompts, list):
        return str(text)
    force_no_music = background_score_policy == "off" or (
        background_score_policy == "follow_prompt" and not _source_requests_music(source_context)
    )
    normalized = []
    for raw in prompts:
        item = str(raw).strip()
        if force_no_music and not re.search(r"\bno non[- ]diegetic music\b", item, re.IGNORECASE):
            item += " No non-diegetic music is audible."
        elif background_score_policy == "add_instrumental" and not re.search(
            r"\b(?:instrumental|score|soundtrack|music)\b", item, re.IGNORECASE,
        ):
            item += " The requested audience-only instrumental score continues with no vocals or lyrics."
        if ambience_foley_policy == "off" and not re.search(
            r"\bno ambience, foley, or non-verbal human sound\b", item, re.IGNORECASE,
        ):
            item += " No ambience, foley, or non-verbal human sound is audible."
        if voice_performance != "audible" and not re.search(
            r"\bno intelligible speech\b", item, re.IGNORECASE,
        ):
            item += " No intelligible speech, vocalization, whispering, or voice is audible."
        normalized.append(re.sub(r"\s+", " ", item).strip())
    return json.dumps({"prompts": normalized}, ensure_ascii=False, separators=(",", ":"))


def normalize_shot_timestamps(text: str) -> str:
    """Add the guide-required comma when the model supplied a complete timestamp but omitted punctuation."""
    value = re.sub(
        r"At\s+(\d{2}:\d{2}\.\d{3})\s+(\[Shot\s+(\d+)\])",
        r"\2 At \1,",
        str(text),
        flags=re.IGNORECASE,
    )
    # Remove a redundant model echo such as
    # ``[Shot 2] At 00:02.500, At [Shot 2], ...`` while preserving the one
    # canonical numbered header and timestamp.
    value = re.sub(
        r"(\[Shot\s+(\d+)\]\s+At\s+\d{2}:\d{2}\.\d{3},)\s*At\s+\[Shot\s+\2\]\s*,?",
        r"\1",
        value,
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
    """Bracket an unambiguous timeline-leading `Shot 1` without touching keyframe prose, or prefix if omitted."""
    section = "detailed_description" if mode == "ref2va" else "integrated_multimodal_description"
    pattern = re.compile(
        rf"(?ms)(^{re.escape(section)}:\s*)(.*?)(?=^[a-z_]+:\s*|\Z)"
    )
    match = pattern.search(str(text))
    if not match or re.search(r"\[Shot\s+1\]", match.group(2), re.IGNORECASE):
        return str(text)
    if re.search(r"\bShot\s+1\b", match.group(2), re.IGNORECASE):
        body = re.sub(r"\bShot\s+1\b", "[Shot 1]", match.group(2), count=1, flags=re.IGNORECASE)
    else:
        body = "[Shot 1] " + match.group(2).lstrip()
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


def append_lora_trigger_words(text: str, trigger_words: str, mode: str = "t2va") -> str:
    """Append LoRA trigger tokens verbatim to the end of the description block.

    These are not prose and must not be treated as such: a trigger is an exact token the LoRA was
    trained on, so "g0r3_style" has to survive character for character. Routing it through the LLM
    would translate it into fluent English like everything else, and it would fail the rule that
    every sentence name something a camera could record -- correctly, because a token is not
    something a camera can record. So this runs after validation, where the tokens can neither be
    rewritten by a repair pass nor confuse a check that expects English.

    They go inside the description body rather than after the final section: a trailing line is
    parsed as part of non_diegetic_music and breaks the contract.
    """
    triggers = " ".join(str(trigger_words or "").split()).strip(" ,")
    if not triggers:
        return text
    section = "detailed_description" if str(mode) == "ref2va" else "integrated_multimodal_description"
    body = _section_body(text, section)
    if not body.strip():
        return text
    return _replace_section_body(text, section, body.rstrip() + "\n" + triggers)


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


def normalize_visual_style_signature(text: str, mode: str, style: Mapping[str, Any]) -> str:
    """Keep the visual style as input conditioning, never as emitted prompt text.

    The resolved contract reaches the writer through RESOLVED PRESENTATION CONTRACT in the
    user request, which now asks for it to be written out as observable shot description.
    Its own wording is direction to a filmmaker ("Use patience, withheld information...",
    "Maintain tension cadence..."), so H3 must never receive it: the delivered prompt is a
    description of what the camera sees. Strip the contract and its per-axis components when
    a model copies them back, leaving the stylistic prose the model authored.
    """
    value = str(text)
    signatures = [
        str(style.get("resolvedSignature") or style.get("visualSignature", "")).strip(),
        *(str(item).strip() for item in style.get("creativeSignatures", {}).values()),
        str(style.get("cinematographySignature", "")).strip(),
    ]
    signatures = [item for item in signatures if item]
    if not signatures:
        return value

    def _strip(body: str) -> str:
        for signature in signatures:
            if signature in body:
                body = body.replace(signature, " ")
        body = re.sub(r"[ \t]{2,}", " ", body)
        body = re.sub(r"(?m)^[ \t]+", "", body)
        # Removing a signature that sat on its own line leaves the section header followed by a
        # blank line; close it so the delivered prompt keeps H3's section shape.
        body = re.sub(r"(?m)^([A-Za-z_]+:)[ \t]*\r?\n(?:[ \t]*\r?\n)+", r"\1\n", body)
        return re.sub(r"\n{3,}", "\n\n", body).strip()

    if mode == "chained_multishot":
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return value
        prompts = data.get("prompts") if isinstance(data, dict) else None
        if not isinstance(prompts, list):
            return value
        normalized = [_strip(item) if isinstance(item, str) else item for item in prompts]
        if normalized == prompts:
            return value
        data["prompts"] = normalized
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    if not any(signature in value for signature in signatures):
        return value
    return re.sub(r"[ \t]{2,}", " ", _strip(value))


def normalize_content_format_signature(text: str, mode: str, content_format: Mapping[str, Any]) -> str:
    """Keep the format arc as input conditioning, never as emitted prompt text.

    The arc says how to order the supplied events ("Organize only the supplied events as a
    compact causal short..."), which is editorial direction rather than anything the camera
    can show. It is executed by the shape of the timeline; quoting it would hand H3 a stage
    note to render. Strip it when a model copies it back.
    """
    value = str(text)
    signature = str(content_format.get("signature", "")).strip()
    if not signature:
        return value

    def _strip(body: str, marker: str) -> str:
        if marker not in body:
            return body
        cleaned = re.sub(r"[ \t]{2,}", " ", body.replace(marker, " "))
        cleaned = re.sub(r"(?m)^([A-Za-z_]+:)[ \t]*\r?\n(?:[ \t]*\r?\n)+", r"\1\n", cleaned)
        return re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if mode == "chained_multishot":
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return value
        prompts = data.get("prompts") if isinstance(data, dict) else None
        if not isinstance(prompts, list):
            return value
        signatures = content_format_signatures(content_format, len(prompts))
        normalized = [
            _strip(item, role_signature) if isinstance(item, str) else item
            for item, role_signature in zip(prompts, signatures)
        ]
        if normalized == prompts:
            return value
        data["prompts"] = normalized
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if signature not in value:
        return value
    return _strip(value, signature)


def content_format_coverage_gaps(text: str, mode: str,
                                 content_format: Mapping[str, Any]) -> list[str]:
    """Check the arc was realized as a timeline, not that its wording was reproduced.

    Presence of the sentence used to stand in for compliance, which a model satisfied by
    pasting it. Observable realization is the property that actually matters, and it is what
    the writer is now asked for.
    """
    signature = str(content_format.get("signature", "")).strip()
    if not content_format.get("applied") or not signature:
        return []
    if mode == "chained_multishot":
        try:
            prompts = json.loads(str(text)).get("prompts", [])
        except (json.JSONDecodeError, AttributeError):
            return ["Content-format arc could not be checked in chained output"]
        signatures = content_format_signatures(content_format, len(prompts))
        return [
            f"Chained item {index} does not observably realize the content-format arc"
            for index, (item, role_signature) in enumerate(zip(prompts, signatures), start=1)
            if not _style_signature_observed(str(item), role_signature)
        ]
    return [] if _style_signature_observed(str(text), signature) else [
        "The content-format arc is not observably realized in the timeline"
    ]


def _strip_instrumental_signature(body: str, signature: str) -> str:
    """Drop an echoed musical-language directive, keeping the observable score prose."""
    if not signature or signature not in body:
        return body
    cleaned = body.replace(signature, " ")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]*[;,][ \t]*", "", cleaned)
    return cleaned.strip()


def normalize_instrumental_style_signature(text: str, mode: str, policy: str, style: str) -> str:
    """Keep the musical language as input conditioning, never as emitted prompt text.

    The selected style already reaches the writer through MUSICAL-LANGUAGE OVERLAY in the
    user request. Its wording is a directive ("Build an intense instrumental horror cue...",
    "do not invent gore, monsters"), not audible description, so H3 must never receive it:
    prompt_guides requires non_diegetic_music to describe instrumentation, tempo, rhythm and
    dynamics in 1-3 sentences. Echoing the directive both blows that budget and feeds H3
    negative instructions. Strip it when a model copies it back.
    """
    value = str(text)
    if policy != "add_instrumental" or style == "none":
        return value
    signature = instrumental_style_signature(style)
    if not signature:
        return value
    if mode == "chained_multishot":
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return value
        prompts = data.get("prompts") if isinstance(data, dict) else None
        if not isinstance(prompts, list):
            return value
        normalized = [
            _strip_instrumental_signature(item, signature) if isinstance(item, str) else item
            for item in prompts
        ]
        if normalized == prompts:
            return value
        data["prompts"] = normalized
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    body = _section_body(value, "non_diegetic_music")
    if signature not in body:
        return value
    return value.replace(body, _strip_instrumental_signature(body, signature), 1)


def normalize_audio_section_sentence_limits(text: str, mode: str) -> str:
    """Keep H3's documented sound and music sections within their sentence budgets."""
    if mode == "chained_multishot":
        return str(text)
    value = str(text)
    for section, maximum in (("overall_soundscape", 4), ("non_diegetic_music", 3)):
        body = _section_body(value, section).strip()
        if not body or body.casefold() == "n/a":
            continue
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", body) if part.strip()]
        if len(sentences) <= maximum:
            continue
        head = sentences[:maximum - 1]
        tail = "; ".join(sentence.rstrip(".!? ") for sentence in sentences[maximum - 1:]) + "."
        value = _replace_section_body(value, section, " ".join([*head, tail]))
    return value


def _validate_multishot(prompt: str, duration_seconds: float, source_prompt: str,
                        shot_count: int = 0, required_locks: tuple[str, ...] = (),
                        voice_performance: str = "audible",
                        authored_dialogue_ledger: tuple[tuple[str, str], ...] = (),
                        ambience_foley_policy: str = "auto",
                        background_score_policy: str = "follow_prompt",
                        instrumental_style: str = "none") -> dict[str, Any]:
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
        dialogue_words = sum(len(re.findall(r"\b[\wÀ-ÿ'-]+\b", quote)) for quote in _extract_output_quotes(item))
        capacity = max(1, round(float(duration_seconds) * 2.5))
        if dialogue_words > capacity * 1.2:
            warnings.append(f"Multishot item {index} has {dialogue_words} quoted words; ~{capacity} words is a planning heuristic for {duration_seconds:g}s")
        for lock in (str(value).strip() for value in required_locks if str(value).strip()):
            if lock not in item:
                errors.append(f"Multishot item {index} is missing an exact required continuity lock: {lock!r}")
        positive = re.sub(r"\bno\b[^.!?]{0,80}\b(?:music|score|soundtrack|ambience|foley|speech|voice)\b", "", item,
                          flags=re.IGNORECASE)
        force_no_music = background_score_policy == "off" or (
            background_score_policy == "follow_prompt" and not _source_requests_music(source_prompt)
        )
        if force_no_music and re.search(r"\b(?:non[- ]diegetic music|score|soundtrack)\b", positive, re.IGNORECASE):
            errors.append(f"Multishot item {index} violates the no-score policy")
        if background_score_policy == "add_instrumental" and not re.search(
            r"\b(?:instrumental|score|soundtrack|music)\b", item, re.IGNORECASE,
        ):
            errors.append(f"Multishot item {index} omitted the requested instrumental score")
        signature = instrumental_style_signature(instrumental_style)
        if (background_score_policy == "add_instrumental" and instrumental_style != "none"
                and signature not in item):
            errors.append(f"Multishot item {index} omitted the canonical instrumental-style signature")
        if ambience_foley_policy == "off" and re.search(
            r"\b(?:ambience|foley|footsteps?|impact|room tone|traffic|wind|rain)\b", positive, re.IGNORECASE,
        ):
            errors.append(f"Multishot item {index} violates the ambience/foley off policy")
        if voice_performance != "audible" and re.search(
            r"<d>|\b(?:says?|speaks?|whispers?|shouts?|voiceover|narration)\b", positive, re.IGNORECASE,
        ):
            errors.append(f"Multishot item {index} contains intelligible voice although voice is suppressed")
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
        raw = [_dialogue_lexical_key(quote) for quote in _extract_output_quotes(item)]
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
    source_quotes = Counter(_extract_source_quotes(source_prompt or ""))
    source_visible_quotes = source_quotes - Counter(quote for _language, quote, _internal in source_contracts)
    output_visible_quotes = Counter(
        quote for item in prompts for quote in _extract_output_quotes(item)
        if _dialogue_lexical_key(quote) not in spoken_keys
    )
    missing_visible = list((source_visible_quotes - output_visible_quotes).elements())
    extra_visible = list((output_visible_quotes - source_visible_quotes).elements())
    if missing_visible:
        errors.append(f"Chained prompts omitted or changed exact visible quoted text: {missing_visible}")
    if extra_visible:
        errors.append(f"Chained prompts invented quoted visible text: {extra_visible}")
    return {"valid": not errors, "mode": "chained_multishot", "errors": errors, "warnings": warnings, "promptCount": len(prompts)}


# Only stylized palettes whose catalog contract defines them as a colour grade may
# be guarded here, and only with patterns naming that palette's own hues.  The
# neutral/naturalistic palettes (natural, warm, cool, restrained, vibrant,
# monochrome) are deliberately absent: they authorize an overall colour bias, so any
# "warm light"/"cool light" pattern would reject legitimate wording about the
# source's own illumination.  midcentury_dye_transfer and saturated_slide_film are
# also absent because they name no hue whose invention as a practical could be
# recognized; their real failure mode is invented print/projection damage, which the
# catalog text already forbids explicitly.
# Only nouns naming a light SOURCE may appear in these guards.  "cast", "wash" and
# "filter" name the colour grade itself, which is exactly what the palette authorizes,
# so guarding them rejected legitimate wording ("a sepia cast holds the frame").  Hue
# groups that belong to different senses are also split into separate entries: the
# source-exemption below disables a whole matching pattern, so one shared source phrase
# should not unlock every hue the palette owns.
_GRADING_ONLY_PALETTE_PATTERNS = {
    "two_color_process": (
        r"\b(?:red[- ]orange|orange[- ]red|cyan[- ]blue[- ]green|cyan|turquoise)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|tubes?|beams?|practicals?)s?\b",
    ),
    "bleach_bypass": (
        # "silver" is dropped entirely: desaturated metallic tone is the look itself.
        r"\b(?:blue|cyan|steel[- ]?blue)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|tubes?|beams?|practicals?)s?\b",
    ),
    "teal_orange": (
        r"\b(?:teal|orange|amber|cyan)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|beams?|practicals?)s?\b",
        # "orange-washed" is grade-adjacent wording the palette authorizes; only a lit
        # scene claim is an invented practical.
        r"\b(?:teal|orange)[- ]lit\b",
    ),
    "cross_processed": (
        r"\blight\s+leaks?\b",
        r"\b(?:magenta|green)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|tubes?|beams?|practicals?)s?\b",
        r"\b(?:cyan|yellow)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|tubes?|beams?|practicals?)s?\b",
    ),
    "sepia": (
        r"\b(?:sepia|amber|brown)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|beams?|practicals?)s?\b",
        r"\bochre\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|beams?|practicals?)s?\b",
    ),
    "classic_western_earth_sky": (
        # Bare "sunset"/"dusk" wording is deliberately not guarded: the palette
        # preserves the supplied time of day, so a source-established sunset may be
        # described. Only the invented golden-hour look is caught.
        r"\bgolden[- ]hour\s+(?:light(?:ing)?|glow|sun|illumination)s?\b",
        # "ochre" is omitted here: this palette's contract names it as a material colour.
        r"\b(?:golden|amber)\s+(?:light(?:ing)?|glow)s?\b",
    ),
    "revisionist_western_earth": (
        r"\b(?:dirty\s+)?(?:yellow|amber|olive)\s+"
        r"(?:light(?:ing)?|glow|illumination)s?\b",
    ),
    "telenovela_broadcast_color": (
        r"\bneon\s+(?:tube|sign|light|lighting|glow|emission|fixture)s?\b",
        # "green" is omitted: a green light is a common diegetic object (traffic signal).
        r"\b(?:orange|yellow)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|tubes?|beams?|practicals?)s?\b",
    ),
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
    # soft_pastel is guarded, but narrowly: the palette authorizes lifted low-saturation
    # candy tints as a grade, so "pastel wash", "pink cast" and "pastel tint" stay legal
    # wording. Only the palette's own hues attached to a light SOURCE ("a pink glow",
    # "pastel lamps") are an invented practical, which is exactly the failure this catches.
    "soft_pastel": (
        r"\b(?:pastel|pink|lilac|mint)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|tubes?|beams?|practicals?)s?\b",
    ),
    # day_for_night: "moonlight" and "blue" name the interpretation itself, so they are
    # only guarded when attached to a source noun. The second entry catches the invented
    # celestial source the palette explicitly forbids; it is a separate group so a source
    # prompt that legitimately mentions blue light does not unlock an invented moon.
    "day_for_night": (
        r"\b(?:blue|cyan|steel[- ]?blue)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|tubes?|beams?|practicals?)s?\b",
        r"\b(?:moonlight|moonlit)\s+(?:glow|emission|illumination|lamps?|beams?|shafts?|practicals?)s?\b",
        r"\bmoonbeams?\b",
        r"\b(?:full|crescent|rising)\s+moon\b|\bstarry\s+(?:sky|night)\b",
    ),
    # infrared_aerochrome: red/magenta on foliage IS the false-color response the palette
    # authorizes, so only red/magenta attached to a light source is guarded, plus the
    # invented infrared emitter.
    "infrared_aerochrome": (
        r"\b(?:red|magenta|crimson|pink)\s+"
        r"(?:light(?:ing)?|glow|emission|illumination|lamps?|tubes?|beams?|practicals?)s?\b",
        r"\binfrared\s+(?:lamps?|illuminators?|emitters?|beams?|light(?:ing)?)s?\b",
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
    errors = []
    if leaked:
        errors.append(
            "The output exposed internal creative profile identifier(s) "
            f"{leaked!r}. Rewrite them as concrete self-contained visual, editorial, performance, and sound prose; "
            "the final H3 prompt must not name selector IDs or control metadata."
        )
    selected = {str(profile_id) for profile_id in treatment.get("profileIds", ())}
    if "visual_language:anime_retro_gag_family" in selected:
        required = {
            "round head/cheek construction": r"\b(?:circular|round(?:ed)?|softly[- ]squared)\s+(?:head|face|cheek)s?\b|\brounded\s+cheeks?\b",
            "large simple oval eyes": r"\blarge\s+(?:simple\s+)?(?:oval|round(?:ed)?)\s+eyes?\b|\b(?:oval|round(?:ed)?)\s+eyes?\s+with\s+(?:small|dark)\s+pupils?\b",
        }
        absent = [label for label, pattern in required.items() if not re.search(
            pattern, output_prompt or "", flags=re.IGNORECASE,
        )]
        if absent:
            errors.append(
                "The retro family gag-anime profile is missing its defining character design: "
                f"{', '.join(absent)}. State these visible traits concretely while preserving identity and adult age."
            )
        forbidden_print = re.findall(
            r"\b(?:ukiyo-e|woodblock(?:[- ]print)?|calligraphic brush|paper grain|Edo[- ]period)\b",
            output_prompt or "", flags=re.IGNORECASE,
        )
        if forbidden_print:
            errors.append(
                "The retro family gag-anime profile must not be rendered as Japanese print art; remove "
                f"{list(dict.fromkeys(forbidden_print))!r} and use crisp television cel character design instead."
            )
    if "visual_language:pixel_art_16bit" in selected:
        incompatible = []
        for pattern in (
            r"(?<!non-)(?<!non )\bphotorealistic\b",
            r"\blive[- ]action\b",
            r"\bsmooth(?:ly)?\s+(?:photographic\s+)?gradients?\b",
            r"\bsoft\s+(?:focus|bokeh|edges?)\b",
            r"\bsubpixel\s+(?:movement|motion|edges?|interpolation)\b",
            r"\banti[- ]?alias(?:ed|ing)?\b",
            r"\bcontinuous\s+(?:photographic\s+)?motion blur\b",
            r"\bphotographic\s+material(?:s| response)?\b",
        ):
            incompatible.extend(match.group(0) for match in _positive_pattern_matches(output_prompt, pattern))
        if incompatible:
            errors.append(
                "The pixel-art profile was contradicted by photographic or subpixel rendering language "
                f"({list(dict.fromkeys(incompatible))!r}). Keep one fixed low-resolution integer grid, hard "
                "nearest-neighbor clusters, discrete palette ramps, and stepped grid-aligned motion."
            )
    return errors


def _continuation_opening_window(timeline: str) -> str:
    """Return the opening span where a continuation must still be carrying the previous take's motion."""
    shots = list(_SHOT_RE.finditer(timeline or ""))
    if len(shots) > 1:
        return timeline[shots[0].end():shots[1].start()]
    return (timeline or "")[:_CONTINUATION_OPENING_CHARACTERS]


def _continuation_transient_warnings(source_prompt: str, timeline: str) -> list[str]:
    """Warn when a continuation opens by finishing a transient the previous take left in progress."""
    if not _CONTINUATION_CONTEXT_RE.search(source_prompt or ""):
        return []
    fragments = list(dict.fromkeys(
        re.sub(r"\s+", " ", match.group(0)).strip()
        for match in _TRANSIENT_COMPLETION_RE.finditer(_continuation_opening_window(timeline))
    ))
    if not fragments:
        return []
    return [
        "Continuation prompt resolves an in-progress transient instantly: "
        + ", ".join(f"'{fragment}'" for fragment in fragments)
        + ". Describe it as still mid-motion at the start (e.g. 'the doors are mid-swing and keep returning at "
        "their current speed') so the first frames continue the previous take instead of snapping to the "
        "finished state."
    ]


def _repeated_sentence_warning(section_name: str, text: str) -> str:
    sentences = [
        re.sub(r"\W+", " ", item).strip().casefold()
        for item in re.split(r"(?<=[.!?])\s+", text or "")
        if len(re.findall(r"\b[\w'-]+\b", item)) >= 6
    ]
    repeated = [sentence for sentence, count in Counter(sentences).items() if sentence and count >= 3]
    if not repeated:
        return ""
    return (
        f"{section_name} repeats the same descriptive sentence three or more times; remove repetition before "
        "compressing unique staging, causal, reference, dialogue, or style detail"
    )


def _adaptive_description_budget(source_prompt: str, reference_context: str,
                                 shot_count: int, profile_name: str) -> dict[str, Any]:
    combined = (source_prompt or "") + "\n" + (reference_context or "")
    editing = bool(re.search(r"\b(?:video editing|edit|editing|editar|reemplazar)\b", combined, re.IGNORECASE))
    dialogue_words = sum(
        len(re.findall(r"\b[\wÀ-ÿ'-]+\b", spoken))
        for _language, spoken, _internal in _source_dialogue_contracts(source_prompt)
    )
    reference_count = len(set(_REFERENCE_RE.findall(combined)))
    transformation_count = len(re.findall(
        r"\b(?:transform(?:s|ed|ation)?|changes? into|becomes?|cycle|stage|phase|trigger)\b",
        source_prompt or "", re.IGNORECASE,
    ))
    if editing:
        return {
            "kind": "source_coverage",
            "softMinWords": None,
            "softMaxWords": None,
            "reason": "video editing scales with source timeline complexity rather than a word range",
        }
    expansion = (
        max(0, int(shot_count) - 2) * 75
        + max(0, reference_count - 2) * 50
        + max(0, dialogue_words - 60)
        + min(150, transformation_count * 35)
    )
    return {
        "kind": "adaptive_generation",
        "softMinWords": 350 if profile_name in ("enhanced_production", "invented_production") else None,
        "softMaxWords": 500 + expansion,
        "baselineWords": [350, 500],
        "extraWords": expansion,
        "dialogueWords": dialogue_words,
        "referenceCount": reference_count,
        "shotCount": int(shot_count),
    }


_STYLE_SIGNATURE_STOPWORDS = {
    "about", "already", "applicable", "camera", "concrete", "describe", "existing", "frame", "inside",
    "keep", "make", "only", "present", "preserve", "render", "resulting", "scene", "selected", "shot",
    "stable", "style", "subject", "through", "treatment", "using", "visible", "with", "without",
    # Instruction framing that addresses the writer and can never surface as shot description.
    "allow", "allowed", "allows", "avoid", "based", "compose", "grant", "grants", "instead",
    "invent", "never", "rather", "request", "requested", "require", "required", "source",
    "supplied", "supplies", "supply", "these", "those", "unless", "where", "whatever", "when",
    "whenever", "which", "while", "would", "should", "their", "there", "every",
}

# A word that appears across most profiles describes the vocabulary of the catalogue, not the
# identity of one look, so it cannot evidence that a specific style was realized. Deriving the
# list keeps it correct when profiles are edited, instead of drifting against a hand-kept set.
_STYLE_SIGNATURE_GENERIC_RATIO = 0.25
_STYLE_SIGNATURE_GENERIC_TOKENS: frozenset[str] | None = None


def _shorten(value: str, limit: int) -> str:
    """Trim a directive for a repair message without cutting mid-word."""
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0]
    return (clipped or text[:limit]).rstrip(",;:") + "…"


def _style_profile_catalogues() -> list[Mapping[str, Any]]:
    """Every creative-treatment catalogue, resolved lazily to avoid an import cycle."""
    try:  # pragma: no cover - packaging variance only
        from . import creative_treatments as _ct
    except ImportError:  # pragma: no cover - direct test/import compatibility
        import creative_treatments as _ct
    names = (
        "VISUAL_LANGUAGE_PROFILES", "GENRE_PROFILES",
        "TONE_PROFILES", "WORLD_AESTHETIC_PROFILES",
    )
    return [
        catalogue for catalogue in (getattr(_ct, name, None) for name in names)
        if isinstance(catalogue, Mapping)
    ]


def _style_signature_generic_tokens() -> frozenset[str]:
    global _STYLE_SIGNATURE_GENERIC_TOKENS
    if _STYLE_SIGNATURE_GENERIC_TOKENS is not None:
        return _STYLE_SIGNATURE_GENERIC_TOKENS
    counts: Counter[str] = Counter()
    profiles = 0
    for catalogue in _style_profile_catalogues():
        for profile in catalogue.values():
            if not isinstance(profile, Mapping):
                continue
            profiles += 1
            seen: set[str] = set()
            for field, value in profile.items():
                if field == "version":
                    continue
                items = [value] if isinstance(value, str) else (
                    list(value) if isinstance(value, (list, tuple)) else []
                )
                for item in items:
                    seen.update(
                        token.casefold()
                        for token in re.findall(r"\b[a-zA-Z][a-zA-Z-]{4,}\b", str(item))
                    )
            counts.update(seen)
    if profiles < 8:  # too small a catalogue to infer anything reliable
        _STYLE_SIGNATURE_GENERIC_TOKENS = frozenset()
        return _STYLE_SIGNATURE_GENERIC_TOKENS
    threshold = profiles * _STYLE_SIGNATURE_GENERIC_RATIO
    _STYLE_SIGNATURE_GENERIC_TOKENS = frozenset(
        token for token, count in counts.items() if count >= threshold
    )
    return _STYLE_SIGNATURE_GENERIC_TOKENS


# A profile line mixes three kinds of clause: what the shot must show, what it must not show,
# and prose about the style itself. Only the first can be evidenced in the delivered prompt, so
# demanding the others produces gaps no writer can ever close.
_STYLE_NEGATED_CLAUSE = re.compile(
    r"\b(?:never|no|not|nor|none|avoid|avoids|without|neither|refrain)\b", re.IGNORECASE,
)
_STYLE_META_CLAUSE = re.compile(
    r"\b(?:craft|grammar|language|vocabulary|idiom|register|tradition|convention|"
    r"aesthetic|approach|principle|philosophy|engine|mode)\b", re.IGNORECASE,
)


def _realizable_clauses(instruction: str) -> list[str]:
    """Split a profile line into the clauses that a shot description can actually evidence."""
    clauses = re.split(r"(?<=[.;:])\s+|\s+—\s+|\s+-\s+", str(instruction))
    realizable = [
        clause for clause in (item.strip() for item in clauses)
        if clause
        and not _STYLE_NEGATED_CLAUSE.search(clause)
        and not _STYLE_META_CLAUSE.search(clause)
    ]
    return realizable


def _style_directive_is_checkable(instruction: str) -> bool:
    return bool(_realizable_clauses(instruction))


def _style_signature_observed(text: str, instruction: str) -> bool:
    generic = _style_signature_generic_tokens()
    checkable = " ".join(_realizable_clauses(instruction)) or str(instruction)
    tokens = [
        token.casefold() for token in re.findall(r"\b[a-zA-Z][a-zA-Z-]{4,}\b", checkable)
        if token.casefold() not in _STYLE_SIGNATURE_STOPWORDS
        and token.casefold() not in generic
    ]
    # No positional cap: a directive often names its examples first and states the actual
    # requirement last ("...so the frame reads as layered, reflected, and geometrically
    # ornate"), so truncating to the head would test the examples and ignore the rule.
    distinctive = list(dict.fromkeys(tokens))
    if not distinctive:  # a wholly generic directive cannot be evidenced either way
        return True
    observed = (text or "").casefold()
    return sum(token in observed for token in distinctive) >= min(2, len(distinctive))


def _resolved_style_coverage_gaps(text: str, style: Mapping[str, Any]) -> list[str]:
    """Repairable gaps only: the explicit cinematography the user set field by field.

    The resolved contract is input conditioning and is deliberately absent from the delivered
    prompt, so it is checked by realization rather than by presence. Catalogue prose is not
    checked here: its lines mix requirements with prohibitions and with description of the
    style itself, so a missing one is not reliably actionable and is reported as a warning by
    _resolved_style_coverage_warnings instead of burning repair attempts.
    """
    if not style.get("applied"):
        return []
    gaps = []
    motion_fields = {"camera_motion", "camera_amplitude", "camera_speed"}
    checked_motion = False
    for item in style.get("cinematographyDirectives", ()):
        if item["field"] in motion_fields:
            if not checked_motion:
                checked_motion = True
                instruction = style.get("cameraMotionInstruction", "")
                if instruction and not _style_signature_observed(text, instruction):
                    gaps.append("Explicit camera motion, amplitude, or speed is not observably realized in the output")
            continue
        if not _style_signature_observed(text, item["instruction"]):
            gaps.append(f"Explicit visual-style field {item['field']} is not observably realized in the output")
    return gaps


def _resolved_style_coverage_warnings(text: str, style: Mapping[str, Any]) -> list[str]:
    """Advisory catalogue coverage: informative, never fed back as a repair instruction.

    Measured against 5 visual languages, repair closed none of these and made several worse
    while tripling generation time, because a catalogue line is not a self-contained
    instruction: it mixes what to show with what to avoid and with prose about the style. The
    writer already receives the contract up front, so this only reports what did not land.
    """
    if not style.get("applied"):
        return []
    warnings = []
    for dimension, lines in style.get("treatmentDimensions", {}).items():
        if dimension == "must_not_invent":
            continue
        missing = [
            line for line in lines
            if _style_directive_is_checkable(line) and not _style_signature_observed(text, line)
        ]
        if missing:
            quoted = "; ".join(_shorten(line, 140) for line in missing)
            warnings.append(
                f"Creative-treatment dimension {dimension} may be under-realized: {quoted}"
            )
    return warnings


def _description_coverage_gaps(timeline: str, mode: str, source_prompt: str,
                               profile_name: str, shot_count: int) -> list[str]:
    if profile_name not in ("enhanced_production", "invented_production") or not timeline.strip():
        return []
    words = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", timeline))
    minimum = 80 + max(0, int(shot_count) - 1) * 35
    if mode == "ref2va":
        minimum = max(minimum, 240)
    elif mode in {"i2va", "fl2va", "l2va"}:
        minimum = max(minimum, 100)
    gaps = []
    if words < minimum:
        gaps.append(
            f"Enhanced-production coverage is too sparse ({words} words; about {minimum} are needed for this "
            "mode/shot load without padding)"
        )
    signals = {
        "spatial opening/blocking": r"\b(?:foreground|background|left|right|center|beside|behind|across|position|composition|eyeline|screen direction)\b",
        "camera, framing, or focus": r"\b(?:camera|shot|frame|lens|focus|close-up|medium shot|wide shot|pan|dolly|track|static)\b",
        "causal response and settled result": r"\b(?:then|after|until|caus|respond|reaction|result|settle|finally|comes? to rest|ends? with|leav(?:e|es|ing))\w*\b",
    }
    for label, pattern in signals.items():
        if not re.search(pattern, timeline, re.IGNORECASE):
            gaps.append(f"Enhanced-production timeline is missing observable {label}")
    if mode == "fl2va" and not re.search(
        r"\b(?:intermediate|gradual|progress|narrow|converge|transition)\w*\b", timeline, re.IGNORECASE,
    ):
        gaps.append("FL2VA enhanced-production timeline does not describe observable intermediate convergence")
    if mode == "l2va" and not re.search(
        r"\b(?:converge|settle|arrive|resolve|final frame|last-frame)\w*\b", timeline, re.IGNORECASE,
    ):
        gaps.append("L2VA enhanced-production timeline does not visibly land on the final-frame state")
    return gaps


def _shot_plan_semantic_errors(items: list[str], plan: Mapping[str, Any]) -> list[str]:
    if not plan.get("provided"):
        return []
    errors = []
    stop = {
        "the", "and", "with", "from", "into", "then", "shot", "scene", "camera", "while",
        "first", "second", "third", "fourth", "beat", "plano", "escena", "primer", "segundo",
    }
    for index, planned in enumerate(plan.get("shots", ()), start=1):
        if index > len(items):
            break
        observed = items[index - 1].casefold()
        tokens = list(dict.fromkeys(
            token.casefold() for token in re.findall(r"\b[\wÀ-ÿ'-]{4,}\b", planned.get("description", ""))
            if token.casefold() not in stop
        ))
        needed = min(2, len(tokens))
        if needed and sum(token in observed for token in tokens) < needed:
            errors.append(f"Shot-plan item {index} dropped its authoritative description")
        motion = str(planned.get("cameraMotion", "none")).replace("_", " ")
        if motion != "none" and not any(part in observed for part in motion.split() if len(part) >= 4):
            errors.append(f"Shot-plan item {index} dropped cameraMotion={planned['cameraMotion']!r}")
        transition = str(planned.get("transitionIn", "cut")).replace("_", " ")
        if index > 1 and transition != "cut" and not any(
            part in observed for part in transition.split() if len(part) >= 4
        ):
            errors.append(f"Shot-plan item {index} dropped transitionIn={planned['transitionIn']!r}")
    return errors


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
                    cinematography_json: str = "",
                    enhance_description: bool | None = None,
                    delivery_target: str = "local",
                    instrumental_description: str = "",
                    instrumental_style: str = "none",
                    acoustic_space: str = "none",
                    dialogue_coverage: str = "off",
                    dialogue_language: str = "auto",
                    editing_intent: str = "none",
                    invent_scene: bool = False) -> dict[str, Any]:
    resolved = resolve_mode(mode, reference_context, source_prompt, media_manifest, editing_intent=editing_intent)
    profile_name = (
        enhancement_profile(enhance_description, invent_scene)
        if enhance_description is not None else "legacy_unprofiled"
    )
    reference_context = "\n".join(
        part for part in (str(reference_context).strip(), manifest_context(media_manifest)) if part
    )
    configuration_errors: list[str] = []
    if delivery_target not in DELIVERY_TARGETS:
        configuration_errors.append(
            f"Unsupported delivery target {delivery_target!r}; choose one of: {', '.join(DELIVERY_TARGETS)}"
        )
    try:
        selected_creative_treatment = parse_creative_treatment(
            creative_treatment_json, enabled=enhance_description is not False,
        )
    except ValueError as exc:
        configuration_errors.append(str(exc))
        selected_creative_treatment = parse_creative_treatment("")
    try:
        selected_cinematography = parse_cinematography(cinematography_json)
    except ValueError as exc:
        configuration_errors.append(str(exc))
        selected_cinematography = parse_cinematography("")
    selected_creative_treatment, _style_conflicts = resolve_treatment_conflicts(
        selected_creative_treatment, selected_cinematography,
    )
    resolved_visual_style = resolve_visual_style(selected_creative_treatment, selected_cinematography)
    profile = generation_profile(duration_seconds, aspect_ratio, frame_count)
    resolved_content_format = resolve_content_format(
        selected_creative_treatment.get("contentFormat", "none"),
        enabled=enhance_description is not False, source_prompt=source_prompt,
        voice_performance=voice_performance, background_score_policy=background_score_policy,
        mode=resolved, duration_seconds=profile["effectiveDurationSeconds"],
    )
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
            ambience_foley_policy, background_score_policy, instrumental_style,
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
        report["errors"].extend(title_screen_style_adherence_errors(
            prompt, selected_creative_treatment, source_prompt,
        ))
        report["errors"].extend(_explicit_source_fact_errors(source_prompt, prompt))
        report["warnings"].extend(profile["warnings"])
        try:
            prompt_items = json.loads(str(prompt)).get("prompts", [])
        except (json.JSONDecodeError, AttributeError):
            prompt_items = []
        prompt_items = [item for item in prompt_items if isinstance(item, str)]
        report["errors"].extend(_shot_plan_semantic_errors(prompt_items, explicit_shot_plan))
        api_compatible = all(len(item) <= _API_V2_TEXT_BLOCK_CHARACTER_LIMIT for item in prompt_items)
        for index, item in enumerate(prompt_items, 1):
            if len(item) > _API_V2_TEXT_BLOCK_CHARACTER_LIMIT:
                message = (
                    f"Multishot item {index} has {len(item)} characters; MiniMax API v2 accepts at most "
                    f"{_API_V2_TEXT_BLOCK_CHARACTER_LIMIT} per text block"
                )
                (report["errors"] if delivery_target == "api_v2" else report["warnings"]).append(message)
            elif delivery_target == "api_v2" and len(item) > _API_V2_TEXT_BLOCK_SOFT_PRESSURE:
                report["warnings"].append(
                    f"Multishot item {index} is approaching the API v2 text limit; preserve unique facts and remove "
                    "only repetition if compression becomes necessary"
                )
        coverage_gaps = [
            f"Multishot item {index}: {gap}"
            for index, item in enumerate(prompt_items, 1)
            for gap in _description_coverage_gaps(
                item, "chained_multishot", source_prompt, profile_name, 1,
            )
        ]
        style_coverage_gaps = [
            f"Multishot item {index}: {gap}"
            for index, item in enumerate(prompt_items, 1)
            for gap in _resolved_style_coverage_gaps(item, resolved_visual_style)
        ]
        report["warnings"].extend(
            f"Multishot item {index}: {warning}"
            for index, item in enumerate(prompt_items, 1)
            for warning in _resolved_style_coverage_warnings(item, resolved_visual_style)
        )
        content_format_gaps = content_format_coverage_gaps(
            prompt, "chained_multishot", resolved_content_format,
        )
        report["valid"] = not report["errors"]
        report["qualityValid"] = (
            report["valid"] and not coverage_gaps and not style_coverage_gaps
            and not content_format_gaps
        )
        report["coverageGaps"] = coverage_gaps
        report["styleCoverageGaps"] = style_coverage_gaps
        report["contentFormatCoverageGaps"] = content_format_gaps
        report["enhancementProfile"] = profile_name
        report["deliveryTarget"] = delivery_target
        report["apiCompatible"] = api_compatible
        report["resolvedVisualStyle"] = resolved_visual_style
        report["contentFormat"] = resolved_content_format
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
    errors.extend(title_screen_style_adherence_errors(
        text, selected_creative_treatment, source_prompt,
    ))

    timeline_section = "detailed_description" if resolved == "ref2va" else "integrated_multimodal_description"
    timeline = _section_body(text, timeline_section)
    api_compatible = len(text) <= _API_V2_TEXT_BLOCK_CHARACTER_LIMIT
    if len(text) > _API_V2_TEXT_BLOCK_CHARACTER_LIMIT:
        budget_message = (
            f"The final prompt is {len(text)} characters; the official MiniMax API v2 accepts at most "
            f"{_API_V2_TEXT_BLOCK_CHARACTER_LIMIT} characters per text block"
        )
        if delivery_target == "api_v2":
            errors.append(
                budget_message
                + "; compress repetition while preserving unique facts, dialogue, anchors, and references"
            )
        else:
            warnings.append(budget_message + "; Local open-weights inference is unaffected")
    elif delivery_target == "api_v2" and len(text) > _API_V2_TEXT_BLOCK_SOFT_PRESSURE:
        warnings.append(
            "The final prompt is approaching the API v2 text limit; preserve unique staging, dialogue, reference, "
            "and style detail and remove only repetition if compression becomes necessary"
        )
    # Ref2VA reports its documented 350-500 word target below. Base mode has no
    # equivalent target, so only flag unusually long bodies that commonly lose adherence.
    description_words = len(re.findall(r"\b[\w'-]+\b", timeline))
    if resolved != "ref2va" and description_words > _BASE_DESCRIPTION_WORD_WARNING_LIMIT:
        repetition_warning = _repeated_sentence_warning(timeline_section, timeline)
        if repetition_warning:
            warnings.append(repetition_warning)
    # A warning, not an error: the same phrasing is legitimate for a transient that completes late
    # in the shot, and the timing is not recoverable from the text.
    warnings.extend(_continuation_transient_warnings(source_prompt, timeline))
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
    if explicit_shot_plan["provided"]:
        shot_bodies = []
        for index, shot in enumerate(shots):
            end = shots[index + 1].start() if index + 1 < len(shots) else len(timeline)
            shot_bodies.append(timeline[shot.end():end])
        errors.extend(_shot_plan_semantic_errors(shot_bodies, explicit_shot_plan))
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
    implicit_limit = (
        None if explicit_shot_plan["provided"]
        else _implicit_shot_limit(source_prompt, resolved, enhance_description)
    )
    if implicit_limit is not None and len(shots) > implicit_limit:
        errors.append(
            f"The source supplied no explicit edit structure; use at most {implicit_limit} shot(s), observed {len(shots)}"
        )
    timeline_without_headers = _SHOT_RE.sub("", timeline)
    invented_inline_times = re.findall(
        r"\b(?:At|After)\s+(?:(?:\d{2}:)?\d{2}:\d{2}(?:\.\d{1,3})?|"
        r"\d+(?:\.\d+)?\s+seconds?|\d+\.\d{2,3})\b",
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
    canonical_source = _ASSET_REFERENCE_RE.sub(
        lambda match: _asset_label(*match.groups()), source_prompt or "",
    )
    zero_indexed = sorted(set(re.findall(
        r"<(?:Picture|Video|Audio|Subject)\s+0>", canonical_source, flags=re.IGNORECASE,
    )))
    if zero_indexed:
        warnings.append(
            f"The source references {', '.join(zero_indexed)}; connected media is numbered from 1, so that "
            "asset kind was shifted up by one for binding. Renumber the source from 1 to remove the guess"
        )
    if re.search(r"<(?:Picture|Video|Audio|Subject)\s+0>", text, flags=re.IGNORECASE):
        errors.append("Reference labels are numbered from 1; a label with index 0 names no connected asset")
    # Speech that cannot physically fit the clip gets truncated mid-word at render
    # time, so flag the overrun while the wording is still editable.  Natural
    # delivery sits near 2.5 words/second; stay conservative and warn only past it.
    spoken_words = sum(
        len(re.sub(r"^\s*\[[^\]]*\]", "", block).split())
        for block in re.findall(r"<d>(.*?)</d>", text, flags=re.DOTALL | re.IGNORECASE)
    )
    if spoken_words and duration_seconds:
        speech_seconds = spoken_words / 2.5
        if speech_seconds > float(duration_seconds):
            warnings.append(
                f"Tagged dialogue runs about {speech_seconds:.1f}s of natural speech but the clip is "
                f"{float(duration_seconds):.1f}s; shorten the lines or the delivery will be cut off"
            )
    # Case-insensitive throughout: a stray <SCENETRANS>/<CUTOFF> must not slip past these checks.
    scenetrans_markers = re.findall(r"(?i)<scenetrans>", timeline)
    if len(scenetrans_markers) % 2:
        errors.append("<scenetrans> must appear at both connecting points when dialogue crosses a cut")
    elif scenetrans_markers and not _SCENETRANS_CONTINUITY_RE.search(timeline):
        # The statement belongs at the natural end of a shot, arbitrarily far from either
        # marker, so the whole timeline is the window.
        errors.append(
            "<scenetrans> requires an explicit statement that the audio continues across the cut, such as "
            "'continues seamlessly across the cut'"
        )
    if re.search(r"(?i)<cutoff>", timeline):
        last_dialogue_end = timeline.lower().rfind("</d>")
        if last_dialogue_end < 0 or timeline.lower().rfind("<cutoff>") > last_dialogue_end:
            errors.append("<cutoff> must occur inside the final dialogue block truncated by the video ending")
    all_dialogue = re.findall(r"<d>(.*?)</d>", text, flags=re.DOTALL | re.IGNORECASE)
    timeline_dialogue = re.findall(r"<d>(.*?)</d>", timeline, flags=re.DOTALL | re.IGNORECASE)
    for dialogue in all_dialogue:
        if not re.match(r"\[[^\]]+\]\s+\S", dialogue.strip()):
            errors.append("Every <d> block must begin with a language tag and contain dialogue")

    source_contracts = _source_dialogue_contracts(source_prompt, override_language=dialogue_language)
    contracts = source_contracts if voice_performance == "audible" else []
    dialogue_authoring, dialogue_authoring_language = _dialogue_authoring_request(
        source_prompt, override_language=dialogue_language
    )
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
            if not re.search(r"\(S\d+(?:\s*,\s*S\d+)*\).*?says\s+in\s+an\s+off-screen\s+voiceover", prefix, flags=re.IGNORECASE):
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
    if (ambience_foley_policy == "ensure_audible" and contracts and not dialogue_authoring
            and dialogue_match_objects and float(duration_seconds) >= 8.0):
        post_dialogue = timeline[dialogue_match_objects[-1].end():]
        if len(re.findall(r"\b[\wÀ-ÿ'-]+\b", post_dialogue)) >= 35:
            sound_cues = set(re.findall(
                r"\b(?:hum|crackle|static|whoosh|wind|rain|traffic|footsteps?|rustle|impact|machinery|"
                r"metallic|vibration|room\s+tone|ambience|breathing|panting|strain|fabric|tear|howl|"
                r"clank|grunt|airflow|engine|alarm|buzz)\w*\b",
                post_dialogue + " " + _section_body(text, "overall_soundscape"),
                flags=re.IGNORECASE,
            ))
            if not sound_cues:
                errors.append(
                    "Required ambience/foley mode needs one continuous requested or physically caused non-verbal "
                    "sound after the final short dialogue line"
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
        if source_label.startswith("<Audio") and source_label not in prefix and not re.search(r"\(S\d+(?:\s*,\s*S\d+)*\)", prefix):
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

    missing_quotes = [quote for quote in _extract_source_quotes(source_prompt or "") if quote not in text]
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
    source_visible_quotes = Counter(_extract_source_quotes(source_prompt or ""))
    source_visible_quotes.subtract(quote for _language, quote, _internal in source_contracts)
    source_visible_quotes += Counter()  # discard zero and negative counts after subtracting dialogue
    output_visible_quotes = Counter(_extract_output_quotes(timeline))
    invented_visible_quotes = list((output_visible_quotes - source_visible_quotes).elements())
    if invented_visible_quotes:
        errors.append(
            "Visible quoted text was invented without source authorization: " + repr(invented_visible_quotes)
        )
    source_dialogue = re.findall(r"<d>(.*?)</d>", source_prompt or "", flags=re.DOTALL)
    missing_dialogue = [item for item in source_dialogue if item not in text]
    if missing_dialogue:
        errors.append("Source <d> dialogue was not preserved exactly")
    tagged_dialogue = "\n".join(re.findall(r"<d>(.*?)</d>", text, flags=re.DOTALL))
    for match in _SOURCE_QUOTED_RE.finditer(source_prompt or ""):
        quote_text = _extract_quote_string(match)
        cue_window = (source_prompt or "")[max(0, match.start() - 100):match.start()]
        if (
            voice_performance == "audible"
            and not _is_visible_text_quote(source_prompt or "", match)
            and (_SPEECH_CUE_RE.search(cue_window) or _INTERNAL_MONOLOGUE_CUE_RE.search(cue_window))
            and quote_text not in tagged_dialogue
        ):
            errors.append(f"Quoted spoken dialogue must appear inside a language-tagged <d> block: {quote_text!r}")
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
        r"(?:unseen|unidentified|anonymous|off-screen)\s+voice|voice\s+from\s+off-screen)\s*\(S\d+(?:\s*,\s*S\d+)*\)",
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
    if background_score_policy == "add_instrumental" and music.casefold() != "n/a":
        positive_music = re.sub(
            r"\b(?:no|without|exclude)\b[^.!?;]{0,80}\b(?:vocals?|lyrics?|singing|choir|speech)\b",
            "", music, flags=re.IGNORECASE,
        )
        if re.search(r"\b(?:singer|soprano|alto|tenor|baritone|choir|vocals?|lyrics?|singing)\b",
                     positive_music, re.IGNORECASE):
            errors.append("Instrumental score contains vocals, singing, choir, or lyrics")
        requested_description = str(instrumental_description).strip()
        if requested_description and not _style_signature_observed(music, requested_description):
            errors.append("Instrumental score dropped the requested instrumental description")
        signature = instrumental_style_signature(instrumental_style)
        if instrumental_style != "none" and signature not in music:
            errors.append("Instrumental score omitted the canonical instrumental-style signature")

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
    if acoustic_space not in ACOUSTIC_SPACE_CHOICES:
        errors.append(f"Unsupported acoustic_space {acoustic_space!r}")
    elif acoustic_space != "none" and soundscape.casefold() != "n/a":
        contract = ACOUSTIC_SPACE_CONTRACTS.get(acoustic_space, "")
        if contract and not _style_signature_observed(soundscape, contract):
            errors.append(f"overall_soundscape dropped the resolved acoustic space {acoustic_space!r}")
    if dialogue_coverage not in DIALOGUE_COVERAGE_CHOICES:
        errors.append(f"Unsupported dialogue_coverage {dialogue_coverage!r}")
    elif dialogue_coverage == "on" and voice_performance == "audible" and source_contracts:
        if not all(re.search(pattern, timeline, re.IGNORECASE) for pattern in (
            r"\b(?:mouth|lips)\b", r"\beyes?\b", r"\b(?:focus|in focus)\b",
            r"\b(?:medium close-up|close-up|tight close)\b",
        )):
            errors.append("Dialogue coverage requires visible mouth, eyes, focus, and close framing for every line")

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

    description_budget: dict[str, Any] = {
        "kind": "base_useful_density",
        "softMinWords": None,
        "softMaxWords": None,
        "actualWords": description_words,
    }
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
            elif subject.get("binding_cues"):
                first_use = detail_text.casefold().find(label.casefold())
                # Keep this deliberately local. A later correct appearance must not excuse an
                # earlier wrong assignment of the same label to somebody else.
                binding_context = detail_text[max(0, first_use - 60):first_use + len(label) + 120]
                observed_cues = [
                    cue for cue in subject["binding_cues"]
                    if cue in binding_context.casefold()
                ]
                if not observed_cues:
                    errors.append(
                        f"{label} is bound by the source wording {subject['binding_excerpt']!r} to "
                        f"{subject['asset']}; its first detailed_description use must identify that exact referent, "
                        "not an earlier or different subject"
                    )
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
        # Two voice references claiming one speaker is the signature of a voice
        # bleeding onto a character it was never bound to, and it is invisible in
        # detailed_description because only the definitions carry the claim.
        definition_voice_owners: dict[str, set[str]] = {}
        for audio_label, owner in re.findall(
            r"(?im)^\s*(<Audio\s+\d+>)[^\r\n]*?\((S\d+)\)", definitions,
        ):
            definition_voice_owners.setdefault(owner.casefold(), set()).add(audio_label.casefold())
        shared_voices = sorted(
            owner for owner, labels in definition_voice_owners.items() if len(labels) > 1
        )
        if shared_voices:
            errors.append(
                f"Each speaker ID accepts one voice reference; subject_definitions binds several to "
                f"{shared_voices}"
            )
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
        elif not summary[official_prefix.end():].strip():
            warnings.append("Ref2VA summary should briefly state the target/reference relationships after its task prefix")

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
        description_budget = _adaptive_description_budget(
            source_prompt, reference_context, len(shots), profile_name,
        )
        description_budget["actualWords"] = detail_words
    coverage_gaps = _description_coverage_gaps(
        timeline, resolved, source_prompt, profile_name, len(shots),
    )
    # A gap rather than an error: the writer can close it on the next pass, and an attribute it
    # genuinely cannot place should not sink an otherwise valid prompt.
    coverage_gaps.extend(_omitted_appearance_attributes(source_prompt, text))
    soft_minimum = description_budget.get("softMinWords")
    if (
        resolved == "ref2va"
        and soft_minimum is not None
        and description_budget.get("actualWords", 0) < soft_minimum
        and not any("too sparse" in gap for gap in coverage_gaps)
    ):
        coverage_gaps.append(
            f"Ref2VA enhanced-production detail is below its adaptive soft baseline "
            f"({description_budget.get('actualWords', 0)} words versus {soft_minimum}); add missing reference, "
            "spatial, causal, camera, or audio-visual coverage without padding"
        )
    style_coverage_gaps = _resolved_style_coverage_gaps(text, resolved_visual_style)
    warnings.extend(_resolved_style_coverage_warnings(text, resolved_visual_style))
    content_format_gaps = content_format_coverage_gaps(text, resolved, resolved_content_format)
    valid = not errors
    return {
        "valid": valid,
        "qualityValid": valid and not coverage_gaps and not style_coverage_gaps and not content_format_gaps,
        "mode": resolved,
        "errors": errors,
        "warnings": warnings,
        "coverageGaps": coverage_gaps,
        "styleCoverageGaps": style_coverage_gaps,
        "contentFormatCoverageGaps": content_format_gaps,
        "enhancementProfile": profile_name,
        "deliveryTarget": delivery_target,
        "apiCompatible": api_compatible,
        "descriptionBudget": description_budget,
        "resolvedVisualStyle": resolved_visual_style,
        "contentFormat": resolved_content_format,
        "sections": list(observed),
        "shotCount": len(shots),
        "aspectRatio": aspect_ratio,
        "mediaManifest": parsed_manifest,
        "generationProfile": profile,
        "shotPlan": explicit_shot_plan,
    }
