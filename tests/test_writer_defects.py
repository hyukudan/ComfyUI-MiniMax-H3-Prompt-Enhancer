# SPDX-License-Identifier: GPL-3.0-only
"""Two defects found by reading real generated prompts rather than by the suite.

Both looked like the writer misbehaving. One was ours.
"""

import prompt_guides as guides

BODY = "integrated_multimodal_description:\nA woman walks.\n\noverall_soundscape:\nRain."


def test_none_typed_into_lora_triggers_is_not_appended_as_a_token():
    """It was ours: "none" is how every other axis spells absent.

    Taken literally it landed as a stray line at the end of the description, which H3 then had to
    interpret as content.
    """
    for spelling in ("none", "None", "NONE", "n/a", "-", "  "):
        assert guides.append_lora_trigger_words(BODY, spelling) == BODY, spelling


def test_real_triggers_still_survive_verbatim():
    out = guides.append_lora_trigger_words(BODY, "g0r3_style, ultrarealistic_v2")
    assert "g0r3_style, ultrarealistic_v2" in out
    # Inside the description body, never after the last section, where it would be read as music.
    assert out.index("g0r3_style") < out.index("overall_soundscape")


def test_speaker_id_gaps_are_rejected():
    # The observed failure: one character was (S2) on one line and (S4) on the next, with no S1
    # or S3 anywhere. The old rule only checked that an ID was present, so this passed.
    errors = guides._speaker_id_numbering_errors("he (S2) replies, then he (S4) says")
    assert errors and "no gaps" in errors[0]
    assert "S2, S4" in errors[0]


def test_well_formed_numbering_passes():
    for prompt in (
        "(S1) asks and (S2) replies",
        "(S1,S2) shout together",
        "no speaker ids at all",
        "(S1) speaks twice, then (S1) again",
    ):
        assert guides._speaker_id_numbering_errors(prompt) == [], prompt


def test_two_characters_sharing_one_id_is_rejected():
    """Tightening the numbering rule produced the opposite failure.

    Every line came back as (S1): no gaps, so the numbering check passed, while two people were
    merged into one voice — worse than the gap it replaced, since H3 keys voice off the ID.
    """
    errors = guides._shared_speaker_id_errors(
        "The detective (S1) speaks: <d>[English] a</d>. The suspect (S1) responds: <d>[English] b</d>."
    )
    assert errors and "more than one character" in errors[0]
    assert "detective" in errors[0] and "suspect" in errors[0]


def test_one_character_may_keep_their_id_across_lines():
    for prompt in (
        "The detective (S1) speaks: <d>[English] a</d>. The detective (S1) adds: <d>[English] b</d>.",
        # A pronoun on a later line is the same person, not a second one.
        "The detective (S1) speaks: <d>[English] a</d>. He (S1) adds: <d>[English] b</d>.",
        "The detective (S1) speaks: <d>[English] a</d>. The suspect (S2) responds: <d>[English] b</d>.",
    ):
        assert guides._shared_speaker_id_errors(prompt) == [], prompt


def test_validator_reports_the_gap():
    leaked = (
        "integrated_multimodal_description: [Shot 1] He (S2) replies, <d>[English] one</d>. "
        "She (S4) says, <d>[English] two</d>.\n\noverall_soundscape: Rain.\n\nnon_diegetic_music: N/A"
    )
    errors = guides.validate_prompt(leaked, "t2va", 5.0)["errors"]
    assert any("numbered from S1" in error for error in errors)
