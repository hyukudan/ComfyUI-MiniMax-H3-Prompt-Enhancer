"""H3 receives description, so no compiled contract may be ordered into the delivered prompt.

Three separate contracts drifted into telling the writer to reproduce a directive verbatim —
the visual style bible, the musical-language overlay and the content-format arc. Each was
internally consistent, so nothing failed; the damage only showed in the prompt H3 received,
where "do not invent gore, monsters" and "Use patience, withheld information" were read as
scene content. These tests pin the rule at the seam where it was broken each time.
"""
import json
import re

import pytest

from content_formats import CONTENT_FORMAT_PROFILES, content_format_instruction, resolve_content_format
from prompt_guides import (
    INSTRUMENTAL_STYLE_CHOICES,
    build_user_request,
    instrumental_style_signature,
)

SOURCE = 'Una mujer entra en un sotano y susurra: "Marta?"'
TREATMENT = json.dumps({
    "schemaVersion": 1, "genre": "horror", "visualLanguage": "giallo",
    "worldAesthetic": "none", "tone": "tense",
})

# Wording that orders the writer to reproduce text rather than realize it. Only affirmative
# orders count: the corrected blocks now say "never copy these words" and "DO NOT WRITE THIS
# SENTENCE", and a prohibition is the opposite of the defect being guarded against.
ECHO_ORDER = re.compile(
    r"(?<!do not )(?<!never )(?<!not )"
    r"(?:copy\s+(?:the|each|every)\b[^.]{0,80}\bverbatim"
    r"|include this exact"
    r"|reproduce (?:it|this|the)\b[^.]{0,40}\b(?:exactly|verbatim))",
    re.IGNORECASE,
)


def _request(**kwargs):
    return build_user_request(
        SOURCE, kwargs.pop("mode", "t2va"), 8.0, "", True, "auto",
        kwargs.pop("score", "follow_prompt"), "audible", "", "auto", "", 0, 0, "", "", "",
        (), kwargs.pop("treatment", ""), "", "",
        kwargs.pop("instrumental_style", "none"), "none", "off",
        dialogue_language="auto", editing_intent="none",
    )


@pytest.mark.parametrize("mode", ["t2va", "i2va", "ref2va", "chained_multishot"])
def test_no_block_orders_the_writer_to_echo_a_compiled_contract(mode):
    request = _request(mode=mode, treatment=TREATMENT,
                       score="add_instrumental", instrumental_style="horror_intense")
    offenders = [line for line in request.splitlines() if ECHO_ORDER.search(line)]
    assert not offenders, (
        "a compiled contract is being ordered into the delivered prompt; it must be executed "
        f"as observable description instead: {offenders}"
    )


@pytest.mark.parametrize("style", [s for s in INSTRUMENTAL_STYLE_CHOICES if s != "none"])
def test_musical_overlay_is_never_ordered_into_the_music_section(style):
    request = _request(score="add_instrumental", instrumental_style=style)
    signature = instrumental_style_signature(style)
    assert signature in request, "the style must still condition the writer"
    index = request.find(signature)
    preamble = request[max(0, index - 400):index]
    assert not ECHO_ORDER.search(preamble), (
        f"instrumental style {style!r} is introduced by an echo order"
    )


@pytest.mark.parametrize("name", [n for n in CONTENT_FORMAT_PROFILES if n != "none"])
def test_content_format_arc_is_never_ordered_into_the_timeline(name):
    resolved = resolve_content_format(
        name, enabled=True, source_prompt=SOURCE, voice_performance="audible",
        background_score_policy="follow_prompt", mode="t2va", duration_seconds=8.0,
    )
    if not resolved.get("applied"):
        pytest.skip(f"{name} is source-gated off for this prompt")
    instruction = content_format_instruction(resolved)
    assert not ECHO_ORDER.search(str(instruction)), (
        f"content format {name!r} orders its arc to be written into the timeline"
    )
