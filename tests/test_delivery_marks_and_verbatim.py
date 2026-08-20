# SPDX-License-Identifier: GPL-3.0-only
"""Delivery marks and the verbatim_source latitude.

Both features exist because H3 has no emotion-tag syntax and no pause syntax at all: its
published skill puts delivery in prose outside <d> and allows only language plus exact words
inside it. So a bracketed mark is authoring shorthand that must be resolved before the prompt
leaves this node, and never emitted.
"""

import prompt_enhancer_node as node
import prompt_guides as guides


def test_verbatim_source_is_a_distinct_profile_the_legacy_flag_pair_cannot_encode():
    assert guides.ENHANCEMENT_PROFILES[0] == "verbatim_source"
    # Both strictest levels collapse to the same legacy booleans, which is exactly why the
    # resolved name is threaded separately instead of being rebuilt from them.
    assert node._latitude_flags("verbatim_source") == (False, False)
    assert node._latitude_flags("conservative_grounded") == (False, False)
    assert node._resolved_latitude_name("verbatim_source") == "verbatim_source"

    verbatim = guides.system_prompt_for_mode("t2va", "verbatim_source")
    conservative = guides.system_prompt_for_mode("t2va", False)
    assert "VERBATIM_SOURCE" in verbatim
    assert "CONSERVATIVE_GROUNDED" in conservative
    assert verbatim != conservative
    # The distinguishing promise: conservative is required to expand, verbatim is required not to.
    assert "source terseness is deliberate" in verbatim
    assert "Do not preserve source terseness" in conservative


def test_legacy_callers_are_unaffected():
    assert node._resolved_latitude_name(None, True, False) == "enhanced_production"
    assert node._resolved_latitude_name(None, True, True) == "invented_production"
    assert node._resolved_latitude_name(None, False, False) == "conservative_grounded"


def test_emotion_mark_leaves_the_spoken_words_and_is_reported():
    cleaned, marks = guides.extract_delivery_marks("No me toques [enfadada] y vete")
    assert cleaned == "No me toques y vete"
    assert marks == ["angrily"]


def test_pause_mark_becomes_an_ellipsis_because_h3_documents_no_pause_syntax():
    cleaned, marks = guides.extract_delivery_marks("Vete [pausa] ahora")
    assert cleaned == "Vete… ahora"
    assert marks == ["a held beat of silence at that point"]


def test_official_h3_brackets_are_never_eaten():
    for markup in ("[Shot 2]", "[English]", "[unclear]"):
        cleaned, marks = guides.extract_delivery_marks(f"before {markup} after")
        assert markup in cleaned
        assert marks == []


def test_marks_do_not_survive_into_the_verbatim_dialogue_contract():
    source = 'She says, "No me toques [enfadada] y vete [pausa] ahora."'
    contracts = guides._source_dialogue_contracts(source)
    assert contracts, "the quoted line should still be detected as dialogue"
    _language, quote, _internal = contracts[0]
    assert "[enfadada]" not in quote
    assert "[pausa]" not in quote
    assert "…" in quote


def test_emoji_beside_a_line_attaches_to_that_line_not_the_next():
    source = 'A: \U0001f621 "Fuera de mi casa"\nB: \U0001f622 "No me dejes"'
    contract = guides._delivery_marks_contract(source)
    assert '- "Fuera de mi casa" → shouts' in contract
    assert '- "No me dejes" → in a low, unsteady voice, close to tears' in contract
    # The failure that matters: one line's emoji claimed by the other.
    assert "shouts" not in contract.split("No me dejes")[1]


def test_emoji_resolves_to_a_documented_verb_where_one_exists():
    for emoji, expected in (("\U0001f92b", "whispers"), ("\U0001f621", "shouts"), ("\U0001f3a4", "sings")):
        assert guides.DELIVERY_EMOJI[emoji] == (expected, "verb")
    # The official voiceover phrasing is fixed wording, not a paraphrase.
    assert guides.DELIVERY_EMOJI["\U0001f4e2"][0] == "says in an off-screen voiceover"


def test_every_mark_carries_a_visible_cue_except_the_off_screen_voiceover():
    # H3 renders picture and sound together, so a voice-only instruction leaves the face blank
    # while the line is delivered. The one exception is deliberate: the official contract requires
    # a voiceover speaker's lips to stay closed, so giving it a face would contradict the spec.
    missing = [e for e in guides.DELIVERY_EMOJI if e not in guides.DELIVERY_FACE]
    assert missing == ["\U0001f4e2"]


def test_visible_cue_is_attached_per_line_and_withheld_from_voiceover():
    contract = guides._delivery_marks_contract(
        'A: \U0001f621 "Fuera de mi casa"\nB: \U0001f4e2 "Nunca volvi"'
    )
    assert '- "Fuera de mi casa" → shouts; visible: jaw set, brows drawn hard down' in contract
    voiceover_line = [line for line in contract.splitlines() if "Nunca volvi" in line][0]
    assert "visible:" not in voiceover_line
    # The gate matters as much as the cue: without this the emotional-performance contract is
    # source-gated and a cautious writer treats a voice descriptor as audio-only.
    assert "the user establishing that emotion" in contract


def test_emoji_never_survives_into_the_spoken_words_or_the_echo():
    source = 'She says, "Ven aquí \U0001f92b ahora"'
    cleaned, marks = guides.extract_delivery_marks('Ven aquí \U0001f92b ahora')
    assert "\U0001f92b" not in cleaned
    assert marks == ["whispers"]
    request = guides.build_user_request(source, "t2va", 5.0)
    assert "\U0001f92b" not in request


def test_pause_note_only_appears_when_a_pause_was_requested():
    with_pause = guides._delivery_marks_contract('She says, "Vete ⏸️ ahora"')
    without = guides._delivery_marks_contract('She says, "Vete \U0001f621 ahora"')
    assert "ellipsis" in with_pause
    assert "ellipsis" not in without


def test_ordinary_speech_cues_are_recognised_as_source_dialogue():
    # Found by running a real generation: "He answers" was not a cue, so the user's own line went
    # undetected as source dialogue and validation then rejected it as *invented* dialogue.
    quotes = [
        quote for _language, quote, _internal in guides._source_dialogue_contracts(
            'She says "No me toques". He answers "Por favor".'
        )
    ]
    assert quotes == ["No me toques", "Por favor"]
    for cue in ("murmurs", "mutters", "yells", "screams", "insists", "begs", "pleads"):
        assert guides._source_dialogue_contracts(f'He {cue} "ven aqui".'), cue


def test_speech_cues_do_not_fire_on_ordinary_quoted_prose():
    # A cue only counts beside a quote, so a non-vocal verb near a quoted object stays silent.
    assert guides._source_dialogue_contracts(
        'He repeats the gesture and picks up "the red book" from the shelf.'
    ) == []


def _validate(prompt):
    return guides.validate_prompt(prompt, "t2va", 5.0)["errors"]


def test_validator_names_leaked_shorthand_instead_of_blaming_invented_dialogue():
    leaked = (
        "integrated_multimodal_description: [Shot 1] A woman \U0001f620 says: "
        "<d>[English] No me toques [enfadada]</d>\n\noverall_soundscape: Rain.\n\nnon_diegetic_music: N/A"
    )
    shorthand = [error for error in _validate(leaked) if "shorthand" in error]
    # Emoji and bracket are reported separately: only the bracket was ever caught before, and only
    # indirectly, as "invented dialogue", which points at the wrong cause.
    assert any("\U0001f620" in error for error in shorthand)
    assert any("[enfadada]" in error for error in shorthand)


def test_validator_does_not_flag_official_h3_brackets():
    clean = (
        "integrated_multimodal_description: [Shot 1] The woman (S1) says in a hard, angry voice: "
        "<d>[English] No me toques</d>\n\noverall_soundscape: Rain.\n\nnon_diegetic_music: N/A"
    )
    assert [error for error in _validate(clean) if "shorthand" in error] == []


def test_contract_actually_reaches_the_built_user_request():
    # Regression: the contract was first attached to an unreachable VOICE POLICY branch, so every
    # unit test passed while the model never saw a word of it. Assert on the real output.
    source = 'A woman turns and says, "No me toques [enfadada] y vete [pausa] ahora."'
    request = guides.build_user_request(source, "t2va", 5.0)
    assert "DELIVERY MARKS" in request
    assert "angrily" in request
    assert "[enfadada]" not in request
    assert "[pausa]" not in request


def test_contract_instructs_prose_outside_d_and_is_absent_when_unused():
    source = 'She says, "No me toques [enfadada] y vete [pausa] ahora."'
    contract = guides._delivery_marks_contract(source)
    assert "angrily" in contract
    assert "a held beat of silence at that point" in contract
    assert "OUTSIDE its <d>" in contract
    assert guides._delivery_marks_contract('She says, "Plain line."') == ""
