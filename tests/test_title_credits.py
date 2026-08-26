# SPDX-License-Identifier: GPL-3.0-only

import json

import pytest

import prompt_enhancer_node
from prompt_enhancer_node import MiniMaxH3PromptEnhancer
from title_credits import TITLE_RECIPES, append_title_lock, plan_title_beats, title_briefing, title_cards


def test_every_recipe_builds_a_complete_deterministic_briefing():
    for recipe in TITLE_RECIPES:
        briefing, cards = title_briefing(
            "A mysterious premium archive in midnight blue and warm brass.",
            recipe,
            "balanced",
            "THE SIGNAL",
            "A FILM BY | MALAK",
            "after credits",
            10.0,
            "16:9",
        )
        assert f"CREATIVE RECIPE - {recipe}" in briefing
        assert "Formation" in briefing
        assert "Readable hold" in briefing
        assert "A FILM BY" in briefing
        assert "MALAK" in briefing
        assert "THE SIGNAL" in briefing
        assert len(cards) == 2


def test_planner_is_monotonic_and_final_card_has_no_transition():
    cards = title_cards("THE SIGNAL", "A FILM BY | MALAK", "after credits")
    beats = plan_title_beats(cards, 10.0, "16:9", "balanced")

    assert beats[0][0] == 0.0
    assert beats[-1][1] == 10.0
    assert all(start < end for start, end, _description in beats)
    assert all(left[1] == right[0] for left, right in zip(beats, beats[1:]))
    assert "Transition" not in beats[-1][2]
    assert "final frame" in beats[-1][2]


def test_title_validation_rejects_unreadable_requests():
    with pytest.raises(ValueError, match="too short"):
        title_briefing("", "Auto director", "balanced", "THE SIGNAL",
                       "DIRECTED BY | MALAK\nPRODUCED BY | COMFY", "after credits", 4.0, "16:9")
    with pytest.raises(ValueError, match="too wide for 9:16"):
        title_briefing("", "Auto director", "balanced", "A" * 37, "", "after credits", 10.0, "9:16")


def test_text_lock_preserves_hierarchical_cards_and_exact_title():
    cards = title_cards('THE "SIGNAL"', "A FILM BY | MÁLAK", "after credits")
    output = append_title_lock("locally enhanced prompt", cards)

    assert output.startswith("locally enhanced prompt")
    assert output.count("STRICT ON-SCREEN TEXT LOCK") == 1
    assert "A FILM BY" in output
    assert "MÁLAK" in output
    assert '\\"SIGNAL\\"' in output
    assert "role and name remain together" in output


def test_main_node_routes_title_briefing_through_local_gguf_and_restores_text_lock(monkeypatch):
    captured = {}

    def fake_gguf(*args, **kwargs):
        captured["basic_prompt"] = args[0]
        return "locally enhanced H3 prompt", {"valid": True, "mode": "t2va"}, {"provider": "local"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    monkeypatch.setattr(
        prompt_enhancer_node,
        "enhance_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("remote backend must not run")),
    )
    result = MiniMaxH3PromptEnhancer().enhance(
        "A premium mechanical mystery.", "t2va", 10.0, "", "", "", "", 0.2,
        8192, 300, 1, True, False,
        use_remote_model=False,
        local_model="model.gguf",
        llama_server_path="llama-server.exe",
        aspect_ratio="16:9",
        title_sequence_recipe="Precision apparatus",
        title_sequence_energy="balanced",
        title_text="THE SIGNAL",
        credit_lines="A FILM BY | MALAK",
        title_placement="after credits",
    )

    assert "CREATIVE RECIPE - Precision apparatus" in captured["basic_prompt"]
    assert "STRICT ON-SCREEN TEXT LOCK" in result[0]
    assert "THE SIGNAL" in result[0]
    assert json.loads(result[2])["titleSequence"] == {
        "recipe": "Precision apparatus",
        "energy": "balanced",
        "cardCount": 2,
    }


def test_main_node_uses_frame_count_duration_for_title_timing(monkeypatch):
    captured = {}

    def fake_gguf(*args, **kwargs):
        captured["basic_prompt"] = args[0]
        return "locally enhanced H3 prompt", {"valid": True, "mode": "t2va"}, {"provider": "local"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    MiniMaxH3PromptEnhancer().enhance(
        "A premium mechanical mystery.", "t2va", 10.0, "", "", "", "", 0.2,
        8192, 300, 1, True, False,
        use_remote_model=False,
        local_model="model.gguf",
        llama_server_path="llama-server.exe",
        aspect_ratio="16:9",
        frame_count=413,
        title_sequence_recipe="Precision apparatus",
        title_text="THE SIGNAL",
    )

    assert "17.2083-second" in captured["basic_prompt"]


def test_main_node_rejects_title_lock_for_chained_multishot():
    with pytest.raises(ValueError, match="chained_multishot returns JSON"):
        MiniMaxH3PromptEnhancer().enhance(
            "A premium mechanical mystery.", "chained_multishot", 10.0, "", "", "", "", 0.2,
            8192, 300, 1, True, False,
            use_remote_model=False,
            local_model="model.gguf",
            llama_server_path="llama-server.exe",
            title_sequence_recipe="Precision apparatus",
            title_text="THE SIGNAL",
        )


def test_disabled_title_mode_preserves_existing_prompt(monkeypatch):
    captured = {}

    def fake_remote(*args, **kwargs):
        captured["basic_prompt"] = args[0]
        return "ordinary enhanced prompt", {"valid": True, "mode": "t2va"}, {"provider": "remote"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt", fake_remote)
    result = MiniMaxH3PromptEnhancer().enhance(
        "An ordinary scene.", "t2va", 5.0, "", "http://127.0.0.1:1234/v1", "", "", 0.2,
        8192, 300, 1, True, False,
    )

    assert captured["basic_prompt"] == "An ordinary scene."
    assert result[0] == "ordinary enhanced prompt"
    assert "titleSequence" not in json.loads(result[2])


def test_schema_and_frontend_expose_conditional_title_controls():
    optional = MiniMaxH3PromptEnhancer.INPUT_TYPES()["optional"]
    assert optional["title_sequence_recipe"][0] == ["none", *TITLE_RECIPES]
    assert optional["title_sequence_recipe"][1]["default"] == "none"
    assert optional["title_sequence_energy"][1]["default"] == "balanced"

    frontend = (prompt_enhancer_node.__file__.rsplit("\\", 1)[0] + "\\web\\backend_toggle.js")
    source = open(frontend, encoding="utf-8").read()
    assert 'widget.name === "title_sequence_recipe"' in source
    assert '"title_text", "credit_lines", "title_placement"' in source
