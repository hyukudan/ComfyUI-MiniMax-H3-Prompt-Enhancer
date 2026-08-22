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
FRONTEND_ROOT = FRONTEND.parent


def _all_frontend_source() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(FRONTEND_ROOT.rglob("*.js"))
    )
README = Path(__file__).parents[1] / "README.md"
NEW_FIELDS = [
    "creative_treatment_json", "shot_plan_json", "cinematography_json", "instrumental_style",
    "acoustic_space", "dialogue_coverage",
]
JSON_FIELDS = NEW_FIELDS[:3]
NEW_FIELD_DEFAULTS = ["", "", "", "none", "none", "off"]
# Appended after NEW_FIELDS on the two LLM-backed nodes only; the guide builder never calls an LLM.
CACHING_FIELDS = ["always_re_enhance"]
DELIVERY_FIELDS = ["delivery_target"]
DELIVERY_TARGET_CALLABLES = {
    prompt_enhancer.enhance_prompt_with_completion,
    prompt_enhancer.enhance_prompt,
    gguf_server.enhance_prompt_with_gguf_server,
}
VALIDATION = {"valid": True, "errors": [], "mode": "t2va"}
CREATIVE = '{"schemaVersion":1,"genre":"action","visualLanguage":"none","worldAesthetic":"none","tone":"none"}'
SHOTS = '{"schemaVersion":1,"timingMode":"auto","shots":[{"id":"s1","description":"One shot."}]}'
CINEMATOGRAPHY = '{"schemaVersion":1,"colorPalette":"warm","cameraMotion":"push_in","cameraAmplitude":"small","cameraSpeed":"slow"}'


def _input_names(node_class):
    inputs = node_class.INPUT_TYPES()
    return [*inputs["required"], *inputs.get("optional", {})]


def _appended_fields(node_class):
    caching = CACHING_FIELDS if node_class in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer) else []
    delivery = DELIVERY_FIELDS if node_class in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer) else []
    return [
        *NEW_FIELDS, *caching, *delivery,
        "dialogue_language", "visual_style_preset", "target_megapixels", "editing_intent",
        "lora_trigger_words",
    ]


# One deliberate rename, recorded so every other drift still fails this file. Two booleans spanned
# four states for three meanings and the spare one lied -- enhance off with invent on ran the most
# conservative profile while the UI promised an invented scene -- so they became one ordered widget.
# creative_latitude takes enhance_description's exact slot and invent_scene was the last widget of
# all, which is why nothing else moved; the frontend converts the old pair on load.
LEGACY_RENAMES = {"enhance_description": "creative_latitude"}


def test_readme_minimal_media_manifest_example_is_valid():
    doc_path = Path(__file__).parents[1] / "docs" / "media_references_and_manifests.md"
    text = doc_path.read_text(encoding="utf-8") if doc_path.exists() else README.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    assert match, "Media manifest example is missing in documentation"
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
        legacy = [LEGACY_RENAMES.get(field, field) for field in fixture["nodes"][name]]
        assert current[:len(legacy)] == legacy
        assert current[len(legacy):] == _appended_fields(node_class)


def test_new_serialized_inputs_have_neutral_migration_defaults():
    for node_class in (MiniMaxH3PromptEnhancer, MiniMaxH3GGUFPromptEnhancer, MiniMaxH3PromptGuideBuilder):
        optional = node_class.INPUT_TYPES()["optional"]
        appended = _appended_fields(node_class)
        assert list(optional)[-len(appended):] == appended
        if "always_re_enhance" in appended:
            assert optional["always_re_enhance"][1]["default"] is False
        if "delivery_target" in appended:
            assert optional["delivery_target"][1]["default"] == "local"
        if "dialogue_language" in appended:
            assert optional["dialogue_language"][1]["default"] == "auto"
        if "visual_style_preset" in appended:
            assert optional["visual_style_preset"][1]["default"] == "none"
        if "target_megapixels" in appended:
            assert optional["target_megapixels"][1]["default"] == 0.0
        for name in JSON_FIELDS:
            options = optional[name][1]
            assert options["default"] == ""
            assert options["multiline"] is True
            assert options["dynamicPrompts"] is False
        assert optional["instrumental_style"][1]["default"] == "none"
        assert optional["acoustic_space"][1]["default"] == "none"
        assert optional["dialogue_coverage"][1]["default"] == "off"


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
    assert "the shots require a clip duration of ${roundedDuration(total)} s" in frontend
    assert "the current effective duration is ${roundedDuration(expected)} s" in frontend


def test_existing_outputs_keep_their_positions_and_new_outputs_are_appended():
    assert MiniMaxH3PromptGuideBuilder.RETURN_NAMES == (
        "system_prompt", "user_prompt", "resolved_mode", "treatment_warnings", "width", "height",
    )
    expected_enhancer_outputs = (
        "enhanced_prompt", "validation_report", "enhancement_manifest", "duration_seconds", "aspect_ratio",
        "treatment_warnings", "width", "height",
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
    callables = {
        build_user_request: [],
        prompt_enhancer.enhance_prompt_with_completion: [],
        prompt_enhancer.enhance_prompt: [],
        gguf_server.enhance_prompt_with_gguf_server: [],
        MiniMaxH3PromptGuideBuilder.build: [],
        MiniMaxH3PromptEnhancer.enhance: CACHING_FIELDS,
        MiniMaxH3GGUFPromptEnhancer.enhance: CACHING_FIELDS,
    }
    for callable_, caching in callables.items():
        parameters = [
            parameter for parameter in inspect.signature(callable_).parameters.values()
            if parameter.name != "self"
        ]
        # creative_latitude replaced the enhance_description/invent_scene pair. It defaults to
        # None so an API caller that still passes the old flags keeps its exact behaviour, which
        # is what this test exists to guarantee.
        if parameters[-1].name == "lora_trigger_words":
            assert parameters[-1].default == ""
            parameters = parameters[:-1]
        if parameters[-1].name == "creative_latitude":
            assert parameters[-1].default is None
            parameters = parameters[:-1]
        if parameters[-1].name == "invent_scene":
            assert parameters[-1].default is False
            parameters = parameters[:-1]
        if parameters[-1].name == "editing_intent":
            assert parameters[-1].default == "none"
            parameters = parameters[:-1]
        if parameters[-1].name == "target_megapixels":
            assert parameters[-1].default == 0.0
            parameters = parameters[:-1]
        if parameters[-1].name == "visual_style_preset":
            assert parameters[-1].default == "none"
            parameters = parameters[:-1]
        if parameters[-1].name == "dialogue_language":
            assert parameters[-1].default == "auto"
            parameters = parameters[:-1]
        if caching:
            assert [parameter.name for parameter in parameters[-2:]] == [*caching, "delivery_target"]
            assert [parameter.default for parameter in parameters[-2:]] == [False, "local"]
            parameters = parameters[:-2]
        if callable_ in DELIVERY_TARGET_CALLABLES:
            assert parameters[-1].name == "delivery_target"
            assert parameters[-1].default == "local"
            parameters = parameters[:-1]
        assert [parameter.name for parameter in parameters[-len(NEW_FIELDS):]] == NEW_FIELDS
        assert [parameter.default for parameter in parameters[-len(NEW_FIELDS):]] == NEW_FIELD_DEFAULTS


def test_legacy_guide_builder_positional_call_still_uses_neutral_behavior():
    system, request, mode, warnings, width, height = MiniMaxH3PromptGuideBuilder().build(
        "A woman crosses a quiet station.", "t2va", 5.0, "",
    )
    assert "MiniMax H3" in system
    assert mode == "t2va"
    assert warnings == ""
    assert width == 1280
    assert height == 720
    assert "SECONDARY CREATIVE TREATMENT" not in request
    assert "AUTHORITATIVE EXPLICIT SHOT PLAN" not in request


def test_legacy_main_node_positional_call_still_reaches_remote_backend(monkeypatch):
    captured = {}

    def fake_remote(*args, **kwargs):
        captured["args"] = args
        return "prompt", VALIDATION, {"provider": "test"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt", fake_remote)
    result = MiniMaxH3PromptEnhancer().enhance(
        "idea", "t2va", 5.0, "", "http://127.0.0.1:1234/v1", "model", "", 0.2,
        4096, 300, 0, True, False,
    )
    assert result[0] == "prompt"
    assert captured["args"][-5:] == (True, "auto", "follow_prompt", "audible", "")
    assert result[-3:] == ("", 1280, 720)


def test_legacy_specialized_gguf_node_positional_call_still_reaches_backend(monkeypatch):
    captured = {}

    def fake_gguf(*args, **kwargs):
        captured["kwargs"] = kwargs
        captured["args"] = args
        return "prompt", VALIDATION, {"provider": "test"}

    monkeypatch.setattr(prompt_enhancer_node, "enhance_prompt_with_gguf_server", fake_gguf)
    result = MiniMaxH3GGUFPromptEnhancer().enhance(
        "idea", "t2va", 5.0, "", "llama-server.exe", "model.gguf", "", "auto", 16384, 0,
        0.2, 4096, 300, 180, 0, True, True, False,
    )
    assert result[0] == "prompt"
    assert captured["args"][15:18] == (True, False, True)
    # The tail travels by keyword now, so the positional block ends where it always did.
    assert captured["args"][-7:] == ("", "none", "none", "off", "local", "auto", "none")
    assert captured["kwargs"]["invent_scene"] is False
    assert captured["kwargs"]["lora_trigger_words"] == ""
    assert result[-3:] == ("", 1280, 720)


def test_main_and_specialized_nodes_forward_appended_fields_without_positional_shift(monkeypatch):
    remote_calls = []
    gguf_calls = []
    monkeypatch.setattr(
        prompt_enhancer_node,
        "enhance_prompt",
        lambda *args, **kwargs: (remote_calls.append(args) or ("prompt", VALIDATION, {"provider": "test"})),
    )
    monkeypatch.setattr(
        prompt_enhancer_node,
        "enhance_prompt_with_gguf_server",
        lambda *args, **kwargs: (gguf_calls.append(args) or ("prompt", VALIDATION, {"provider": "test"})),
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
    assert remote_calls[0][-9:] == (CREATIVE, SHOTS, "", "none", "none", "off", "local", "auto", "none")
    # invent_scene left the positional block, so both backends now end at the same field.
    assert gguf_calls[0][-9:] == (CREATIVE, SHOTS, "", "none", "none", "off", "local", "auto", "none")


def test_guide_builder_forwards_both_new_fields_to_the_request_contract():
    _system, request, _mode, _warnings, _width, _height = MiniMaxH3PromptGuideBuilder().build(
        "A woman crosses a station.", "t2va", 5.0, "",
        creative_treatment_json=CREATIVE, shot_plan_json=SHOTS,
    )
    assert "anticipation, action, impact, and recovery" in request
    assert "genre:action" not in request
    assert "Use exactly 1 " in request


def test_frontend_panel_is_non_persistent_while_both_json_storage_widgets_remain_persistent():
    source = FRONTEND.read_text(encoding="utf-8")
    all_source = _all_frontend_source()
    assert 'const CREATIVE_TREATMENT_WIDGET = "creative_treatment_json"' in all_source
    assert 'const SHOT_PLAN_WIDGET = "shot_plan_json"' in all_source
    assert 'const CINEMATOGRAPHY_WIDGET = "cinematography_json"' in all_source
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
        "american_comic_pastel", "animation_2d", "heroic_limited_cel_tv",
        "midcentury_graphic_cel_comedy", "classic_morning_adventure_cel", "pixel_art_16bit",
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
        "titleScreenStyle", "minimal_cinematic", "bold_broadcast", "classic_cel",
        "illustrated_pulp", "elegant_editorial", "neon_technology", "pixel_art_title",
        "silent_intertitle",
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
        '"Anime"', '"Classic television cel"', '"Drawn & painted 2D"', '"Graphic & pixel styles"',
        '"3D animation"', '"Game cinematics"', '"Physical animation"',
        '"Live action"', '"Commercial & presentation"',
    )
    positions = [source.index(label) for label in family_labels]
    assert positions == sorted(positions)
    camera_look = (FRONTEND_ROOT / "studio" / "tab_camera_look.js").read_text(encoding="utf-8")
    assert "controller.visualLanguageGroups?.()" in camera_look
    assert 'heading.className = "minimax-h3-searchable-select-group"' in camera_look
    assert "Unavailable in loaded catalog" in source


def test_frontend_mirrors_the_new_camera_axes_and_legacy_motion_migration():
    source = FRONTEND.read_text(encoding="utf-8")
    for token in (
        "shotScale", "cameraAngle", "cameraViewpoint", "extreme_close_up", "medium_close_up",
        "extreme_wide", "eye_level", "low_angle", "high_angle", "overhead", "dutch_static",
        "worms_eye", "over_the_shoulder", "mirror_or_reflection", "lens_18mm", "lens_35mm",
        "lens_50mm", "lens_85mm_compressed", "match_cut", "whip_pan",
    ):
        assert f'"{token}"' in source
    assert '["shake", "Handheld shake"]' in source
    assert '["pov", "POV"]' not in source
    assert '["shake_slightly", "Shake slightly"]' not in source
    assert "const LEGACY_CAMERA_MOTIONS = {" in source
    assert 'shake_slightly: { cameraMotion: "shake", cameraAmplitude: "small" }' in source
    assert 'pov: { cameraMotion: "none", cameraViewpoint: "pov" }' in source
    assert '["none", "static", "pov"]' not in source
    # "still motion" is decided in one place, so every caller stays in step and the rule is
    # not re-derived per site. The point of the check is that "pov" is not one of them.
    assert source.count('["none", "static"].includes') == 1
    assert "function isStillMotion(motion) {" in source
    assert source.count("isStillMotion(") >= 5
    assert 'sanitizeEnumWidget(node, "dialogue_coverage", ["off", "on"], "off");' in source
    assert 'assignMigratedValue(manifest, "");' in source
    assert '"underwater_muffled",' in source


def test_frontend_uses_compact_non_persistent_accordions_and_keeps_advanced_last():
    source = FRONTEND.read_text(encoding="utf-8")
    assert 'const ACCORDION_STATE_PROPERTY = "minimaxH3AccordionState"' in source
    assert 'details.open = accordionState(node, "modelSetup")' in source
    assert 'details.open = accordionState(node, "audioSettings")' in source
    assert 'details.open = accordionState(node, "chainedMultishot")' in source
    assert 'details.open = accordionState(node, "advancedSettings")' in source
    assert "Prompt model backend" in source
    append_block = source.split("function mountCompactCreativePanel", 1)[1].split(
        "function addCreativeDirectionPanel", 1,
    )[0]
    assert append_block.index("audioSettings.details") < append_block.index("modelSetup.details")
    assert append_block.index("modelSetup.details") < append_block.index("chainedSettings.details")
    assert append_block.index("chainedSettings.details") < append_block.index("advancedSettings.details")
    assert "createStudioDashboard(node, studioController)" in source
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


def test_frontend_sanitizer_accepts_every_selectable_preset():
    """A short allow-list in the sanitizer silently resets valid choices back to "none".

    The frontend validates widget values against its own copy of the list, so a preset the
    backend accepts but the sanitizer does not know is discarded on load — the user picks a
    style, sees it revert, and the request goes out with no visual language at all.
    """
    from creative_treatments import VISUAL_LANGUAGE_PROFILES

    frontend = FRONTEND.read_text(encoding="utf-8")
    start = frontend.index('sanitizeEnumWidget(node, "visual_style_preset", [')
    block = frontend[start:frontend.index('], "none");', start)]
    for name in VISUAL_LANGUAGE_PROFILES:
        assert f'"{name}"' in block, f"{name} would be reset to none by the frontend"


def test_frontend_migrates_the_legacy_latitude_pair_rather_than_dropping_it():
    """Renaming a widget in place is only safe if the old value is converted, not reinterpreted.

    A workflow saved before the swap holds a boolean where the enum now sits. Left alone it would
    sanitise to the default, silently promoting every conservative_grounded workflow to
    enhanced_production and demoting every invented one.
    """
    frontend = FRONTEND.read_text(encoding="utf-8")
    start = frontend.index("function migrateLegacyLatitudePair")
    body = frontend[start:frontend.index("function repairLegacyModelDiscoveryShift")]
    assert 'typeof widget.value !== "boolean"' in body, "must only act on a pre-swap workflow"
    for level in ("conservative_grounded", "enhanced_production", "invented_production"):
        assert level in body
    # It has to convert the boolean before the sanitiser sees it, or the sanitiser discards it and
    # falls back to the default. onConfigure runs first; the sanitiser runs from onDrawForeground.
    assert "migrateLegacyLatitudePair(this, arguments[0]);" in frontend
    assert 'sanitizeEnumWidget(node, "creative_latitude"' in frontend
    for dead in ('sanitizeBooleanWidget(node, "enhance_description"',
                 'sanitizeBooleanWidget(node, "invent_scene"'):
        assert dead not in frontend, f"{dead} outlived the widget it sanitised"
