# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
from pathlib import Path

import pytest

from creative_treatments import (
    CINEMATOGRAPHY_CHOICES,
    CINEMATOGRAPHY_JSON_KEYS,
    CINEMATOGRAPHY_SCHEMA_VERSION,
    CINEMATOGRAPHY_SUPPORTED_SCHEMA_VERSIONS,
    CREATIVE_TREATMENT_SCHEMA_VERSION,
    CREATIVE_TREATMENT_SUPPORTED_SCHEMA_VERSIONS,
    parse_cinematography,
    parse_creative_treatment,
)
from prompt_enhancer_node import _merge_visual_style_preset


SCHEMA_DIRECTORY = Path(__file__).parents[1] / "docs" / "schemas"


def test_v2_is_the_canonical_runtime_contract_while_v1_remains_supported():
    assert CREATIVE_TREATMENT_SCHEMA_VERSION == 2
    assert CREATIVE_TREATMENT_SUPPORTED_SCHEMA_VERSIONS == (1, 2)
    assert CINEMATOGRAPHY_SCHEMA_VERSION == 2
    assert CINEMATOGRAPHY_SUPPORTED_SCHEMA_VERSIONS == (1, 2)


@pytest.mark.parametrize(
    ("parser", "field", "value"),
    (
        (parse_creative_treatment, "genre", "action"),
        (parse_cinematography, "cameraMotion", "push_in"),
    ),
)
def test_v1_and_v2_sources_normalize_to_identical_v2_models(parser, field, value):
    legacy = parser({"schemaVersion": 1, field: value})
    native = parser({"schemaVersion": 2, field: value})

    assert legacy["schemaVersion"] == native["schemaVersion"] == 2
    assert legacy["sourceSchemaVersion"] == 1
    assert legacy["legacyInput"] is True
    assert native["sourceSchemaVersion"] == 2
    assert native["legacyInput"] is False
    assert legacy["canonicalJson"] == native["canonicalJson"]
    assert legacy["digest"] == native["digest"]
    assert json.loads(legacy["canonicalJson"])["schemaVersion"] == 2


@pytest.mark.parametrize("parser", (parse_creative_treatment, parse_cinematography))
def test_blank_sources_create_neutral_v2_models_without_claiming_a_migration(parser):
    parsed = parser("")
    assert parsed["schemaVersion"] == 2
    assert parsed["sourceSchemaVersion"] is None
    assert parsed["legacyInput"] is False
    assert json.loads(parsed["canonicalJson"])["schemaVersion"] == 2


def test_misplaced_shot_plan_in_cinematography_is_neutral_and_keeps_shots_authoritative():
    misplaced = {
        "schemaVersion": 2,
        "timingMode": "auto",
        "shots": [{"id": "s1", "generationId": "g1", "action": "They dance."}],
    }
    parsed = parse_cinematography(misplaced)
    assert parsed["requested"] is False
    assert parsed["sourceSchemaVersion"] is None
    assert "misplaced Shot Plan payload" in parsed["warnings"][0]


@pytest.mark.parametrize("legacy_blank", (False, True, "false", "False", " FALSE ", "true", "True", " TRUE ", " null ", "NULL", "None"))
@pytest.mark.parametrize("parser", (parse_creative_treatment, parse_cinematography))
def test_legacy_false_and_null_storage_values_are_neutral_v2_without_writes(parser, legacy_blank):
    parsed = parser(legacy_blank)
    assert parsed["schemaVersion"] == 2
    assert parsed["sourceSchemaVersion"] is None
    assert parsed["legacyInput"] is False
    assert parsed["requested"] is False
    assert json.loads(parsed["canonicalJson"])["schemaVersion"] == 2


@pytest.mark.parametrize("unsupported_scalar", (0, "0", '"false"', "[]"))
@pytest.mark.parametrize("parser", (parse_creative_treatment, parse_cinematography))
def test_other_scalar_storage_values_remain_invalid(parser, unsupported_scalar):
    with pytest.raises(ValueError, match="JSON object|blank, a JSON object string, or a mapping"):
        parser(unsupported_scalar)


@pytest.mark.parametrize(
    ("parser", "source"),
    (
        (parse_creative_treatment, {"schemaVersion": 1, "genre": "action"}),
        (parse_cinematography, {"schemaVersion": 1, "cameraMotion": "push_in"}),
    ),
)
def test_runtime_normalization_never_rewrites_the_legacy_source_mapping(parser, source):
    before = dict(source)
    parsed = parser(source)
    assert parsed["schemaVersion"] == 2
    assert source == before
    assert source["schemaVersion"] == 1


def test_legacy_camera_aliases_are_v1_compatibility_only():
    legacy = parse_cinematography({"schemaVersion": 1, "cameraMotion": "shake_slightly"})
    native_equivalent = parse_cinematography({
        "schemaVersion": 2,
        "cameraMotion": "shake",
        "cameraAmplitude": "small",
    })

    assert legacy["cameraMotion"] == "shake"
    assert legacy["cameraAmplitude"] == "small"
    assert legacy["canonicalJson"] == native_equivalent["canonicalJson"]
    assert legacy["digest"] == native_equivalent["digest"]
    with pytest.raises(ValueError, match="Unsupported cinematography cameraMotion"):
        parse_cinematography({"schemaVersion": 2, "cameraMotion": "shake_slightly"})


@pytest.mark.parametrize("version", (0, 3, True, "2"))
@pytest.mark.parametrize("parser", (parse_creative_treatment, parse_cinematography))
def test_unsupported_or_ambiguous_source_versions_fail_without_coercion(parser, version):
    with pytest.raises(ValueError, match="schemaVersion must be one of: 1, 2"):
        parser({"schemaVersion": version})


def test_visual_style_preset_overlay_emits_v2_without_mutating_the_source_string():
    assert json.loads(_merge_visual_style_preset("", "anime_shonen")) == {
        "schemaVersion": 2,
        "visualLanguage": "anime_shonen",
    }
    for legacy_blank in (False, "false", "null"):
        assert json.loads(_merge_visual_style_preset(legacy_blank, "anime_shonen")) == {
            "schemaVersion": 2,
            "visualLanguage": "anime_shonen",
        }
    legacy_source = '{"schemaVersion":1,"genre":"action","visualLanguage":"none"}'
    overlaid = json.loads(_merge_visual_style_preset(legacy_source, "anime_shonen"))
    assert overlaid == {
        "schemaVersion": 2,
        "genre": "action",
        "visualLanguage": "anime_shonen",
    }
    assert legacy_source == '{"schemaVersion":1,"genre":"action","visualLanguage":"none"}'
    assert _merge_visual_style_preset(legacy_source, "none") == legacy_source

    future = json.loads(_merge_visual_style_preset('{"schemaVersion":99}', "anime_shonen"))
    assert future == {"schemaVersion": 99, "visualLanguage": "anime_shonen"}
    with pytest.raises(ValueError, match="schemaVersion must be one of"):
        parse_creative_treatment(future)


def test_published_v2_schemas_match_runtime_keys_and_cinematography_catalogs():
    creative_schema = json.loads(
        (SCHEMA_DIRECTORY / "creative_treatment_v2.schema.json").read_text(encoding="utf-8")
    )
    cinematography_schema = json.loads(
        (SCHEMA_DIRECTORY / "cinematography_v2.schema.json").read_text(encoding="utf-8")
    )

    assert creative_schema["properties"]["schemaVersion"] == {"const": 2}
    assert set(creative_schema["properties"]) == {
        "schemaVersion",
        "contentFormat",
        "genre",
        "visualLanguage",
        "worldAesthetic",
        "tone",
        "titleScreenStyle",
        "animationCadence",
    }
    assert cinematography_schema["properties"]["schemaVersion"] == {"const": 2}
    for external, internal in CINEMATOGRAPHY_JSON_KEYS.items():
        assert cinematography_schema["properties"][external]["enum"] == list(
            CINEMATOGRAPHY_CHOICES[internal]
        )
