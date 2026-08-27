import json

import pytest

from creative_treatments import parse_shot_plan
from media_manifest import manifest_context_for_generation, parse_media_project
from planning_context import compile_planning_context
from prompt_guides import normalize_reference_definitions
from studio_project import compile_studio_project, empty_studio_project


def _source(name: str) -> dict:
    return {
        "storage": "comfy_input",
        "file": f"minimax_h3_reference_director/{name} [input]",
        "sha256": "b" * 64,
        "mediaType": "picture",
        "sizeBytes": 42,
    }


def _media_project() -> dict:
    return {
        "schemaVersion": 2,
        "mode": "ref2va",
        "assets": [{"id": "car.image", "type": "picture", "name": "Car Y front"}],
        "subjects": [],
        "props": [{
            "id": "car.y", "h3Index": 1, "name": "Car Y", "category": "vehicle",
            "description": "A red two-door sports car with a black roof.",
            "designAssetIds": ["car.image"],
        }],
        "environments": [],
        "generations": [{
            "id": "g1", "order": 1, "activation": {"mode": "auto"},
            "bindings": [{"assetId": "car.image", "slotIndex": 1}],
            "subjectStates": [], "environmentStates": [],
        }],
    }


def _shot_plan() -> dict:
    return {
        "schemaVersion": 2,
        "timingMode": "auto",
        "shots": [{
            "id": "s1", "generationId": "g1",
            "action": "A driver opens <Subject 1> and gets inside.",
            "props": [{"propId": "car.y", "presence": "present", "note": "Driver enters it."}],
        }],
    }


def test_media_v2_prop_activates_design_picture_and_uses_subject_design_family():
    parsed = parse_media_project(_media_project())
    assert parsed["valid"], parsed["errors"]
    assert parsed["generations"]["g1"]["inputMap"] == {"car.image": "<Picture 1>"}

    planning = compile_planning_context(_media_project(), _shot_plan(), 5, mode="ref2va")
    assert planning["valid"], planning["diagnosticReport"]
    assert {tuple(item.values()) for item in planning["generations"]["g1"]["activeResources"]} >= {
        ("prop", "car.y"), ("asset", "car.image"),
    }
    context = manifest_context_for_generation(
        {**parsed, "generations": planning["generations"]}, "g1",
    )
    assert "<Subject 1> (Car Y), family design" in context
    assert "<Picture 1> supplies only the reusable physical design" in context


def test_prop_h3_indices_share_the_subject_namespace_and_design_assets_must_be_pictures():
    project = _media_project()
    project["subjects"] = [{
        "id": "ana", "h3Index": 1, "name": "Ana", "description": "Dark-haired woman.",
        "identityAssetIds": [], "baseAppearanceStateId": "base",
        "appearanceStates": [{"id": "base", "name": "Base", "controls": []}],
    }]
    duplicate = parse_media_project(project)
    assert not duplicate["valid"]
    assert any(item["code"] == "schema.media_manifest.duplicate_h3_index" for item in duplicate["diagnostics"])

    project = _media_project()
    project["assets"][0]["type"] = "audio"
    wrong_type = parse_media_project(project)
    assert not wrong_type["valid"]
    assert any(item["field"].endswith("designAssetIds") for item in wrong_type["diagnostics"])


def test_shot_plan_v2_normalizes_optional_prop_presence_and_rejects_duplicates():
    parsed = parse_shot_plan(_shot_plan(), 5, 0, "ref2va")
    assert parsed["shots"][0]["props"] == [{
        "propId": "car.y", "presence": "present", "note": "Driver enters it.",
    }]
    duplicate = _shot_plan()
    duplicate["shots"][0]["props"].append({"propId": "car.y"})
    with pytest.raises(ValueError, match="duplicate propId"):
        parse_shot_plan(duplicate, 5, 0, "ref2va")


def test_v3_compiles_prop_to_media_v2_shot_v2_physical_socket_and_design_contract():
    project = empty_studio_project()
    project["project"].update({"name": "Car scene", "mode": "ref2va"})
    project["files"] = [{
        "id": "car.image", "type": "picture", "name": "Car Y", "source": _source("car.webp"),
    }]
    project["props"] = [{
        "id": "car.y", "h3Index": 1, "name": "Car Y", "category": "vehicle",
        "description": "A red two-door sports car with a black roof.",
        "designFileIds": ["car.image"],
    }]
    project["shots"] = [{
        "id": "s1", "generationId": "g1", "action": "A driver gets into <Subject 1>.",
        "props": [{"propId": "car.y"}],
    }]

    compiled = compile_studio_project(project)
    assert compiled["mediaProject"]["props"][0]["designAssetIds"] == ["car.image"]
    assert compiled["shotPlan"]["shots"][0]["props"] == [{"propId": "car.y"}]
    assert compiled["inputMap"] == {"car.image": "<Picture 1>"}
    assert compiled["socketMap"] == {"car.image": "ref_image_1"}
    contracts = [
        json.loads(line.split(": ", 1)[1])
        for line in compiled["referenceContext"].splitlines()
        if "SUBJECT CONTRACT JSON" in line
    ]
    assert contracts == [{
        "appearanceState": {}, "category": "vehicle", "description": "A red two-door sports car with a black roof.",
        "family": "design", "identitySources": ["<Picture 1>"], "label": "<Subject 1>",
        "name": "Car Y", "voiceSource": None,
    }]


def test_prompt_normalizer_preserves_prop_as_design_not_character_or_speaker():
    context = "\n".join([
        "AUTHORITATIVE REFERENCE RELATIONSHIPS:",
        '- SUBJECT CONTRACT JSON: {"label":"<Subject 2>","family":"design","name":"Car Y","category":"vehicle","description":"red two-door car","identitySources":["<Picture 1>"],"voiceSource":null,"appearanceState":{}}',
    ])
    draft = """subject_definitions:
wrong

summary:
[reference generation] wrong

retention_analysis:
wrong

detailed_description:
Car Y waits at the curb.

overall_soundscape:
Traffic.

non_diegetic_music:
N/A"""
    normalized = normalize_reference_definitions(draft, "Car Y waits.", context)
    assert "<Subject 2> is the reusable design-family Prop Car Y (vehicle)" in normalized
    assert "stable physical design: red two-door car" in normalized
    assert "do not copy source people, background, pose, lighting, camera, or text" in normalized
    assert "<Subject 2> (Car Y; stable physical design: red two-door car)" in normalized
    assert "voice-timbre" not in normalized
