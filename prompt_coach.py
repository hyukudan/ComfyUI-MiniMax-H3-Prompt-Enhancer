# SPDX-License-Identifier: GPL-3.0-only
"""Conservative, non-repairing prompt advice for structured shot-plan v2."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

try:
    from .diagnostics import (
        Diagnostic,
        DiagnosticCode,
        DiagnosticCollector,
        DiagnosticLocation,
        LocationScope,
    )
except ImportError:  # pragma: no cover
    from diagnostics import (
        Diagnostic,
        DiagnosticCode,
        DiagnosticCollector,
        DiagnosticLocation,
        LocationScope,
    )


_STOP = {
    "a", "al", "an", "and", "at", "con", "de", "del", "el", "en", "from",
    "in", "la", "las", "los", "of", "on", "the", "to", "un", "una", "y",
}
_LEXICON = {
    "en": {
        "locomotion": {"walk", "walks", "run", "runs", "move", "moves", "cross", "crosses", "go", "goes", "enter", "enters", "exit", "exits"},
        "path": {"across", "along", "around", "between", "through", "toward", "towards", "into", "past", "from", "to"},
        "final": {"arrives", "reaches", "stops", "stands", "sits", "kneels", "ends", "remains"},
        "orientation": {"turn", "turns", "face", "faces", "look", "looks", "orient", "orients"},
        "direction": {"left", "right", "camera", "toward", "towards", "away", "front", "rear", "behind", "at"},
        "manipulation": {"grab", "grabs", "pick", "picks", "place", "places", "put", "puts", "open", "opens", "close", "closes", "throw", "throws", "push", "pushes", "pull", "pulls", "hold", "holds"},
        "contact": {"hand", "hands", "fingers", "grip", "grasps", "touches", "against", "onto"},
        "result": {"inside", "outside", "open", "closed", "rests", "lands", "releases", "holds", "remains"},
        "pronouns": {"he", "she", "him", "her", "his", "hers", "they", "them", "their"},
    },
    "es": {
        "locomotion": {"camina", "corre", "avanza", "cruza", "entra", "sale", "mueve", "desplaza"},
        "path": {"hacia", "hasta", "desde", "por", "entre", "atraves", "alrededor", "junto"},
        "final": {"llega", "alcanza", "detiene", "queda", "permanece", "sienta", "arrodilla"},
        "orientation": {"gira", "mira", "orienta", "encara"},
        "direction": {"izquierda", "derecha", "camara", "hacia", "lejos", "frente", "detras", "a"},
        "manipulation": {"agarra", "coge", "toma", "coloca", "pone", "abre", "cierra", "lanza", "empuja", "tira", "sostiene"},
        "contact": {"mano", "manos", "dedos", "agarre", "toca", "contra", "sobre"},
        "result": {"dentro", "fuera", "abierto", "cerrado", "descansa", "cae", "suelta", "sostiene", "queda"},
        "pronouns": {"el", "ella", "ellos", "ellas", "su", "sus", "le", "les"},
    },
}
_GENERIC_AESTHETIC = {
    "cinematic", "realistic", "photorealistic", "ultra", "detailed", "dramatic",
    "beautiful", "stunning", "epic", "masterpiece", "8k",
}


@dataclass(frozen=True)
class _Candidate:
    code: DiagnosticCode
    message: str
    confidence: float
    shot_index: int
    shot_id: str
    suggestions: tuple[str, ...] = ()


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", str(text)).casefold()
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?|\d+", normalized, flags=re.UNICODE)


def _informative(text: str) -> set[str]:
    return {token for token in _tokens(text) if token not in _STOP and len(token) > 1}


def _language(text: str, supplied: str | None) -> str | None:
    if supplied in _LEXICON:
        return supplied
    tokens = _tokens(text)
    if not tokens:
        return None
    signals = {
        "es": sum(token in {"hacia", "ella", "ellos", "camina", "cruza", "mira", "agarra", "abre", "cierra"} for token in tokens),
        "en": sum(token in {"toward", "she", "he", "they", "walks", "crosses", "looks", "grabs", "opens", "closes"} for token in tokens),
    }
    winner = max(signals, key=signals.get)
    return winner if signals[winner] >= 1 and signals[winner] > signals["es" if winner == "en" else "en"] else None


def _dice(left: set[str], right: set[str]) -> float:
    return 2 * len(left & right) / (len(left) + len(right)) if left and right else 0.0


def _weak_cut(previous: Mapping[str, Any], current: Mapping[str, Any], no_dialogue: bool) -> bool:
    if not no_dialogue or previous.get("generationId") != current.get("generationId"):
        return False
    if not previous.get("subjectPresenceComplete") or not current.get("subjectPresenceComplete"):
        return False
    if not previous.get("environment") or not current.get("environment"):
        return False
    cut = current.get("cutContext", {})
    if cut.get("timeRelation") in {None, "unknown"} or cut.get("purpose") != "unspecified":
        return False
    previous_frame = previous.get("cameraEnd") or previous.get("cameraStart") or {}
    current_frame = current.get("cameraStart") or {}
    for key in ("viewpoint", "primaryTarget"):
        if key not in previous_frame or previous_frame.get(key) != current_frame.get(key):
            return False
    previous_state = (previous.get("subjects"), previous.get("environment"))
    current_state = (current.get("subjects"), current.get("environment"))
    if previous_state != current_state:
        return False
    return _dice(_informative(previous.get("action", "")), _informative(current.get("openingState", ""))) >= 0.86


def run_prompt_coach(
    plan: Mapping[str, Any], *, language: str | None = None,
    no_dialogue_between: set[tuple[str, str]] | None = None,
    collector: DiagnosticCollector | None = None,
) -> DiagnosticCollector:
    """Append bounded advice; never alter the plan and never create repair work."""
    result = collector or DiagnosticCollector()
    if plan.get("schemaVersion") != 2 or not plan.get("provided", True):
        return result
    shots = list(plan.get("shots", ()))
    candidates: list[_Candidate] = []
    no_dialogue_between = no_dialogue_between or set()
    for index, shot in enumerate(shots):
        shot_id = str(shot.get("id", f"shot-{index + 1}"))
        opening = str(shot.get("openingState", ""))
        action = str(shot.get("action", ""))
        shot_language = _language(opening + " " + action, language)
        opening_tokens, action_tokens = _informative(opening), _informative(action)
        if len(opening_tokens) >= 4 and len(action_tokens) >= 4 and _dice(opening_tokens, action_tokens) >= 0.86:
            candidates.append(_Candidate(
                DiagnosticCode.COACH_OPENING_DUPLICATE,
                "The action nearly repeats the opening state instead of advancing it.",
                0.9, index, shot_id,
                ("Keep openingState as the first-frame condition and describe only the subsequent change in action.",),
            ))
        if shot_language:
            words = set(_tokens(action))
            lex = _LEXICON[shot_language]
            if words & lex["locomotion"] and not words & lex["path"] and not words & lex["final"]:
                candidates.append(_Candidate(
                    DiagnosticCode.COACH_LOCOMOTION_UNDER_SPECIFIED,
                    "The locomotion lacks both a route or destination and a visible final state.",
                    0.8, index, shot_id,
                    ("Add where the subject travels and the visible state reached by the end of the shot.",),
                ))
            if words & lex["orientation"] and not words & lex["direction"] and not words & lex["final"]:
                candidates.append(_Candidate(
                    DiagnosticCode.COACH_ORIENTATION_UNDER_SPECIFIED,
                    "The orientation change does not name a target, direction, or visible result.",
                    0.78, index, shot_id,
                    ("Name what the subject faces or where their body and gaze finish.",),
                ))
            if len(words) <= 14 and words & lex["manipulation"] and not words & lex["contact"] and not words & lex["path"] and not words & lex["result"]:
                candidates.append(_Candidate(
                    DiagnosticCode.COACH_MANIPULATION_UNDER_SPECIFIED,
                    "The object manipulation is short and lacks contact, trajectory, or object result.",
                    0.74, index, shot_id,
                    ("Add how contact happens and where the object ends.",),
                ))
            present = [item for item in shot.get("subjects", ()) if item.get("presence") != "absent"]
            if shot.get("subjectPresenceComplete") and len(present) >= 2 and words & lex["pronouns"]:
                subject_ids = {str(item.get("subjectId", "")).casefold() for item in present}
                if not subject_ids & words:
                    candidates.append(_Candidate(
                        DiagnosticCode.COACH_AMBIGUOUS_PRONOUN,
                        "A pronoun may have multiple present subject antecedents.",
                        0.7, index, shot_id,
                        ("Replace the ambiguous pronoun with the intended subject ID or name.",),
                    ))
        aesthetic_count = sum(Counter(_tokens(action))[word] for word in _GENERIC_AESTHETIC)
        if aesthetic_count >= 4:
            candidates.append(_Candidate(
                DiagnosticCode.COACH_AESTHETIC_NOISE,
                "The action contains a dense cluster of generic aesthetic modifiers that can weaken the selected visual language.",
                0.72, index, shot_id,
                ("Keep medium-specific visual language in the look controls and make the action concrete and observable.",),
            ))
        duration = shot.get("durationSeconds")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration > 0:
            dialogue_spans = re.findall(r"<d>\s*(.*?)\s*</d>", action, flags=re.IGNORECASE | re.DOTALL)
            if not dialogue_spans:
                dialogue_spans = [
                    left or right
                    for left, right in re.findall(r'"([^"\r\n]+)"|“([^”\r\n]+)”', action)
                ]
            spoken_words = sum(
                len(_tokens(re.sub(r"^\s*\[[^\]]+\]\s*", "", span)))
                for span in dialogue_spans
            )
            capacity = float(duration) * 2.5
            if spoken_words > capacity:
                candidates.append(_Candidate(
                    DiagnosticCode.COACH_DIALOGUE_TIMING_PRESSURE,
                    f"The shot contains about {spoken_words} spoken words for {float(duration):.3g} seconds; "
                    "2.5 words per second indicates likely timing pressure.",
                    min(0.9, 0.65 + (spoken_words - capacity) / max(capacity, 1) * 0.2),
                    index, shot_id,
                    ("Shorten the line, lengthen the explicitly timed shot, or move dialogue only if the story allocation permits it.",),
                ))
        if index and _weak_cut(shots[index - 1], shot, (shots[index - 1]["id"], shot_id) in no_dialogue_between):
            candidates.append(_Candidate(
                DiagnosticCode.COACH_WEAK_CUT,
                "The adjacent shot has equivalent state, environment, viewpoint, and focal target without a declared cut purpose.",
                0.76, index, shot_id,
                ("Declare the cut purpose or introduce an observable state, spatial, temporal, or viewpoint change.",),
            ))

    candidates.sort(key=lambda item: (-item.confidence, item.shot_index, item.code.value))
    emitted_per_shot: Counter[int] = Counter()
    emitted = 0
    suppressed = 0
    for candidate in candidates:
        if emitted >= 12 or emitted_per_shot[candidate.shot_index] >= 2:
            suppressed += 1
            continue
        location = DiagnosticLocation(
            LocationScope.CONFIGURATION,
            f"shot_plan_json.shots[{candidate.shot_index}].action",
            generation_id=str(shots[candidate.shot_index].get("generationId", "")) or None,
            shot_id=candidate.shot_id,
            shot_index=candidate.shot_index,
        )
        diagnostic = Diagnostic.create(
            candidate.code, candidate.message, location,
            confidence=candidate.confidence, suggestions=candidate.suggestions,
        )
        if result.add(diagnostic):
            emitted += 1
            emitted_per_shot[candidate.shot_index] += 1
    if suppressed:
        result.suppress_coach(suppressed)
    return result
