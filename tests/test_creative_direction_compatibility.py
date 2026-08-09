# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import gguf_server
import prompt_enhancer
import prompt_enhancer_node
from media_manifest import parse_media_manifest
from prompt_enhancer_node import (
    MiniMaxH3GGUFPromptEnhancer,
    MiniMaxH3PromptEnhancer,
    MiniMaxH3PromptGuideBuilder,
    MiniMaxH3ShotSelector,
)
from prompt_guides import build_user_request


FIXTURE = Path(__file__).with_name("fixtures") / "legacy_node_inputs_v050.json"
FRONTEND = Path(__file__).parents[1] / "web" / "backend_toggle.js"
README = Path(__file__).parents[1] / "README.md"
NEW_FIELDS = ["creative_treatment_json", "shot_plan_json", "cinematography_json", "instrumental_style"]
JSON_FIELDS = NEW_FIELDS[:-1]
VALIDATION = {"valid": True, "errors": [], "mode": "t2va"}
CREATIVE = '{"schemaVersion":1,"genre":"action","visualLanguage":"none","worldAesthetic":"none","tone":"none"}'
SHOTS = '{"schemaVersion":1,"timingMode":"auto","shots":[{"id":"s1","description":"One shot."}]}'
CINEMATOGRAPHY = '{"schemaVersion":1,"colorPalette":"warm","cameraMotion":"push_in","cameraAmplitude":"small","cameraSpeed":"slow"}'


def _input_names(node_class):
    inputs = node_class.INPUT_TYPES()
    return [*inputs["required"], *inputs.get("optional", {})]


def test_readme_minimal_media_manifest_example_is_valid():
    text = README.read_text(encoding="utf-8")
    match = re.search(r"The minimal manifest form is:\s*```json\s*(.*?)\s*```", text, flags=re.DOTALL)
    assert match, "README minimal media-manifest example is missing"
    example = json.loads(match.group(1))
    report = parse_media_manifest(example)
    assert report["errors"] == []


def test_new_serialized_inputs_are_appended_after_every_legacy_node_input():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    classes = {
        "MiniMaxH3PromptEnhancer": MiniMaxH3PromptEnhancer,
        "MiniMaxH3GGUFPromptEnhancer": MiniMaxH3GGUFPromptEnhancer,
        "MiniMaxH3PromptGuideBuilder": MiniMaxH3PromptGuideBuilder,
    }
    for name, node_class in classes.items():
        current = _input_names(node_class)
        legacy = fixture["nodes"][name]
        assert current[:len(legacy)] == legacy
        assert current[len(legacy):] == NEW_FIELDS


def test_new_serialized_inputs_have_neutral_migration_defaults():
    for node_class in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer, MiniMaxH3PromptGuideBuilder):
        optional = node_class.INPUT_TYPES()["optional"]
        assert list(optional)[-len(NEW_FIELDS):] == NEW_FIELDS
        for name in JSON_FIELDS:
            options = optional[name][1]
            assert options["default"] == ""
            assert options["multiline"] is True
            assert options["dynamicPrompts"] is False
        assert optional["instrumental_style"][1]["default"] == "none"


def test_generation_duration_matches_native_h3_ceiling_and_frontend_preserves_it():
    for node_class in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer, MiniMaxH3PromptGuideBuilder):
        inputs = node_class.INPUT_TYPES()
        assert inputs["required"]["duration_seconds"][1]["max"] == 150.0
        assert inputs["optional"]["frame_count"][1]["max"] == 3600
    frontend = FRONTEND.read_text(encoding="utf-8")
    assert 'const MAX_GENERATION_SECONDS = 150;' in frontend
    assert 'sanitizeNumberWidget(node, "duration_seconds", 5, 4, MAX_GENERATION_SECONDS);' in frontend
    assert 'panel.root.style.maxWidth = `${panelWidth}px`;' in frontend
    assert 'new ResizeObserver(() => scheduleCreativePanelLayout(node))' in frontend


def test_existing_outputs_keep_their_positions_and_new_outputs_are_appended():
    assert MiniMaxH3PromptGuideBuilder.RETURN_NAMES == ("system_prompt", "user_prompt", "resolved_mode")
    expected_enhancer_outputs = (
        "enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds", "aspect_ratio",
    )
    assert MiniMaxH3PromptEnhancer.RETURN_NAMES == expected_enhancer_outputs
    assert MiniMaxH3GGUFPromptEnhancer.RETURN_NAMES == expected_enhancer_outputs
    assert MiniMaxH3ShotSelector.RETURN_NAMES == (
        "shot_prompt", "timeline_body", "shot_description", "shot_id", "shot_count", "autonomous",
    )
    assert MiniMaxH3ShotSelector.RETURN_TYPES == (
        "STRING", "STRING", "STRING", "STRING", "INT", "BOOLEAN",
    )


def test_low_level_and_node_signatures_append_only_optional_neutral_fields():
    callables = (
        build_user_request,
        prompt_enhancer.enhance_prompt_with_completion,
        prompt_enhancer.enhance_prompt,
        gguf_server.enhance_prompt_with_gguf_server,
        MiniMaxH3PromptGuideBuilder.build,
        MiniMaxH3PromptEnhancer.enhance,
        MiniMaxH3GGUFPromptEnhancer.enhance,
    )
    for callable_ in callables:
        parameters = [
            parameter for parameter in inspect.signature(callable_).parameters.values()
            if parameter.name != "self"
        ]
        assert [parameter.name for parameter in parameters[-len(NEW_FIELDS):]] == NEW_FIELDS
        assert [parameter.default for parameter in parameters[-len(NEW_FIELDS):]] == ["", "", "", "none"]


def test_legacy_guide_builder_positional_call_still_uses_neutral_behavior():
    system, request, mode = MiniMaxH3PromptGuideBuilder().build(
        "A woman crosses a quiet station.", "t2va", 5.0, "",
    )
    assert "MiniMax H3" in system
    assert mode == "t2va"
    assert "SECONDARY CREATIVE TREATMENT" not in request
    assert "AUTHORITATIVE EXPLICIT SHOT PLAN" not in request


def test_legacy_main_node_positional_call_still_reaches_remote_backend(monkeypatch):
    captured = {}

    def fake_remote(*args):
        captured["args"] = args
        return "prompt", VALIDATION, {"provider": "test"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt", fake_remote)
    result = MiniMaxH3PromptEnhancer().enhance(
        "idea", "t2va", 5.0, "", "http://127.0.0.1:1234/v1", "model", "", 0.2,
        4096, 300, 0, True, False,
    )
    assert result[0] == "prompt"
    assert captured["args"][-5:] == (True, "auto", "follow_prompt", "audible", "")


def test_legacy_specialized_gguf_node_positional_call_still_reaches_backend(monkeypatch):
    captured = {}

    def fake_gguf(*args):
        captured["args"] = args
        return "prompt", VALIDATION, {"provider": "test"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    result = MiniMaxH3GGUFPromptEnhancer().enhance(
        "idea", "t2va", 5.0, "", "llama-server.exe", "model.gguf", "", "auto", 16384, 0,
        0.2, 4096, 300, 180, 0, True, True, False,
    )
    assert result[0] == "prompt"
    assert captured["args"][15:18] == (True, False, True)
    assert captured["args"][-2:] == ("", "none")


def test_main_and_specialized_nodes_forward_appended_fields_without_positional_shift(monkeypatch):
    remote_calls = []
    gguf_calls = []
    monkeypatch.setattr(
        prompt_enhancer_node,
        "enhance_prompt",
        lambda *args: (remote_calls.append(args) or ("prompt", VALIDATION, {"provider": "test"})),
    )
    monkeypatch.setattr(
        prompt_enhancer_node,
        "enhance_prompt_with_gguf_server",
        lambda *args: (gguf_calls.append(args) or ("prompt", VALIDATION, {"provider": "test"})),
    )
    MiniMaxH3PromptEnhancer().enhance(
        "idea", "t2va", 5.0, "", "http://127.0.0.1:1234/v1", "model", "", 0.2,
        4096, 300, 0, True, False, creative_treatment_json=CREATIVE, shot_plan_json=SHOTS,
    )
    MiniMaxH3GGUFPromptEnhancer().enhance(
        "idea", "t2va", 5.0, "", "llama-server.exe", "model.gguf", "", "auto", 16384, 0,
        0.2, 4096, 300, 180, 0, True, True, False,
        creative_treatment_json=CREATIVE, shot_plan_json=SHOTS,
    )
    assert remote_calls[0][-4:] == (CREATIVE, SHOTS, "", "none")
    assert gguf_calls[0][-4:] == (CREATIVE, SHOTS, "", "none")


def test_guide_builder_forwards_both_new_fields_to_the_request_contract():
    _system, request, _mode = MiniMaxH3PromptGuideBuilder().build(
        "A woman crosses a station.", "t2va", 5.0, "",
        creative_treatment_json=CREATIVE, shot_plan_json=SHOTS,
    )
    assert "genre:action" in request
    assert "Use exactly 1 " in request


def test_frontend_panel_is_non_persistent_while_both_json_storage_widgets_remain_persistent():
    source = FRONTEND.read_text(encoding="utf-8")
    assert 'const CREATIVE_TREATMENT_WIDGET = "creative_treatment_json"' in source
    assert 'const SHOT_PLAN_WIDGET = "shot_plan_json"' in source
    assert 'const CINEMATOGRAPHY_WIDGET = "cinematography_json"' in source
    assert '"MiniMaxH3PromptEnhancer"' in source
    assert '"MiniMaxH3GGUFPromptEnhancer"' in source
    assert '"MiniMaxH3PromptGuideBuilder"' in source
    panel_marker = 'node.addDOMWidget(\n        CREATIVE_PANEL_WIDGET'
    assert panel_marker in source
    panel_tail = source.split(panel_marker, 1)[1].split(");", 1)[0]
    assert "serialize: false" in panel_tail
    hide_storage = source.split("function hideJsonStorageWidget", 1)[1].split(
        "function writeJsonStorage", 1,
    )[0]
    assert "serialize = false" not in hide_storage
    assert "serializeValue" not in hide_storage


def test_frontend_contract_uses_canonical_choices_and_safe_shot_editor_controls():
    source = FRONTEND.read_text(encoding="utf-8")
    for token in (
        "action", "horror", "thriller", "romance", "comedy", "drama", "adventure", "mystery",
        "anime_general", "anime_ultradetailed_cinematic", "anime_retro_dramatic", "anime_retro_gag_family",
        "japanese_print_animation",
        "anime_shonen", "anime_shojo", "anime_shojo_pastel",
        "american_comic_pastel", "animation_2d", "pixel_art_16bit",
        "stylized_3d_animation", "game_3d_cinematic", "game_3d_nextgen", "low_poly_3d",
        "cel_shaded_3d", "documentary_observational", "live_action_cinematic",
        "live_action_classic_black_and_white",
        "live_action_gritty", "live_action_expressionist", "live_action_visceral_horror",
        "live_action_1980s_television", "live_action_latin_american_telenovela",
        "live_action_1980s_action", "live_action_classic_chinese_martial_arts",
        "live_action_classic_western", "live_action_revisionist_western",
        "live_action_1950s_studio_color",
        "live_action_midcentury_technicolor_epic", "midcentury_dye_transfer",
        "two_color_process", "bleach_bypass", "teal_orange", "cross_processed",
        "sepia", "saturated_slide_film", "classic_western_earth_sky", "revisionist_western_earth",
        "telenovela_broadcast_color",
        "cold_steel_blue", "sterile_white_cyan", "neon_cyan_magenta",
        "crime", "western", "sports_competition", "analog_1980s", "urban_industrial",
        "kinetic", "pulp_heightened", "stoic",
        "cyberpunk", "film_noir", "science_fiction", "high_fantasy", "retrofuturism",
        "epic", "intimate", "dark", "tense", "hopeful", "melancholic", "playful", "restrained",
    ):
        assert f'"{token}"' in source
    assert "+ Add shot" in source
    assert "+ Add independent segment" in source
    assert "Move up one position" in source
    assert "Move down one position" in source
    assert "Delete" in source
    assert "MAX_SHOTS = 64" in source
    assert "frameValue / 24" in source
    assert "/^[A-Za-z0-9_-]{1,64}$/" in source
    assert ".slice(0, 8000)" in source
    assert "rebalanceExactDurations" in source
    family_labels = (
        '"Anime"', '"Drawn & painted 2D"', '"Graphic & pixel styles"',
        '"3D animation"', '"Game cinematics"', '"Physical animation"',
        '"Live action"', '"Commercial & presentation"',
    )
    positions = [source.index(label) for label in family_labels]
    assert positions == sorted(positions)
    assert 'document.createElement("optgroup")' in source
    assert "Unavailable in loaded catalog" in source


def test_frontend_uses_collapsed_non_persistent_accordions_and_keeps_advanced_last():
    source = FRONTEND.read_text(encoding="utf-8")
    assert 'const ACCORDION_STATE_PROPERTY = "minimaxH3AccordionState"' in source
    assert 'details.open = accordionState(node, "modelSetup")' in source
    assert 'treatmentDetails.open = accordionState(node, "creativeDirection")' in source
    assert 'shotDetails.open = accordionState(node, "shotPlan")' in source
    assert 'details.open = accordionState(node, "advancedSettings")' in source
    assert "No preferences" in source
    assert "Auto-distribute" in source
    assert "Set duration per shot" in source
    assert "Prompt model backend" in source
    append_block = source.split("if (modelSetup) root.appendChild", 1)[1].split(
        "const panelWidget", 1,
    )[0]
    assert append_block.index("modelSetup.details") < append_block.index("treatmentDetails")
    assert append_block.index("treatmentDetails") < append_block.index("cinematographyDetails")
    assert append_block.index("cinematographyDetails") < append_block.index("shotDetails")
    assert append_block.index("shotDetails") < append_block.index("advancedSettings.details")
    assert "node.__minimaxProxyManagedWidgets = managedNames" in source
    assert "setWidgetVisible(node.widgets?.find((widget) => widget.name === name), false)" in source


def test_frontend_places_nonpersistent_music_style_proxy_below_background_score():
    source = FRONTEND.read_text(encoding="utf-8")
    assert 'const INSTRUMENTAL_STYLE_PROXY_WIDGET = "minimax_h3_instrumental_style_proxy"' in source
    proxy = source.split("function addInstrumentalStyleProxy", 1)[1].split(
        "function refreshBackendWidgets", 1,
    )[0]
    assert 'node.addWidget(\n        "combo"' in proxy
    assert "node.addDOMWidget" not in proxy
    assert 'node.widgets.indexOf(score)' in proxy
    assert 'node.widgets.splice(scoreIndex + 1, 0, proxyWidget)' in proxy
    assert "markPanelWidgetNonPersistent(proxyWidget)" in proxy
    for token in (
        "action_cinematic", "mystery_investigation", "suspense_build", "combat_rhythmic",
        "chinese_martial_arts", "horror_intense",
    ):
        assert f'["{token}",' in source
