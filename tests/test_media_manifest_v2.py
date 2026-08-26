import json

from media_manifest import (
    MEDIA_MANIFEST_SCHEMA_VERSION,
    manifest_context_for_generation,
    parse_media_manifest,
    parse_media_project,
)
from prompt_guides import resolve_mode


def _project():
    return {
        "schemaVersion": 2,
        "mode": "ref2va",
        "assets": [
            {"id": "ana.identity", "type": "picture", "name": "Ana identity", "description": "front identity portrait"},
            {"id": "unused", "type": "picture", "name": "Unused", "description": "must never bleed"},
        ],
        "subjects": [{
            "id": "ana", "h3Index": 1, "name": "Ana",
            "description": "Adult woman with short dark hair.",
            "identityAssetIds": ["ana.identity"],
            "baseAppearanceStateId": "base",
            "appearanceStates": [{
                "id": "base", "name": "Base", "controls": ["wardrobe"],
                "attributes": {"wardrobe": "red coat"},
            }],
        }],
        "environments": [],
        "generations": [{
            "id": "g1", "order": 1, "activation": {"mode": "auto"},
            "bindings": [{"assetId": "ana.identity", "slotIndex": 1}],
            "subjectStates": [{"subjectId": "ana", "policy": "explicit", "stateId": "base"}],
            "environmentStates": [],
        }],
    }


def test_manifest_v2_compiles_canonical_project_and_scoped_context():
    compiled = parse_media_project(_project())
    assert MEDIA_MANIFEST_SCHEMA_VERSION == 2
    assert compiled["valid"], compiled["errors"]
    assert len(compiled["digest"]) == 64
    assert json.loads(compiled["canonicalJson"]) == _project()
    generation = compiled["generations"]["g1"]
    assert generation["activeAssetIds"] == ["ana.identity"]
    assert generation["inputMap"] == {"ana.identity": "<Picture 1>"}
    context = manifest_context_for_generation(compiled, "g1")
    assert "<Subject 1>" in context
    assert "red coat" in context
    assert "front identity portrait" in context
    assert "Unused" not in context
    assert "must never bleed" not in context


def test_manifest_v2_canonical_digest_is_independent_of_object_key_order():
    project = _project()
    reordered = {key: project[key] for key in reversed(project)}
    first = parse_media_project(project)
    second = parse_media_project(json.dumps(reordered))
    assert first["canonicalJson"] == second["canonicalJson"]
    assert first["digest"] == second["digest"]


def test_manifest_v2_rejects_duplicate_json_keys_and_future_versions():
    duplicate = parse_media_project('{"schemaVersion":2,"schemaVersion":2}')
    assert not duplicate["valid"]
    assert duplicate["diagnostics"][0]["code"] == "schema.media_manifest.invalid_json"
    future = parse_media_project({"schemaVersion": 9})
    assert not future["valid"]
    assert future["canonicalJson"] == '{"schemaVersion":9}'
    assert future["diagnostics"][0]["code"] == "schema.media_manifest.unsupported_version"


def test_manifest_v2_never_compiles_the_old_identity_instruction_as_prompt_content():
    project = _project()
    project["subjects"][0]["description"] = "Describe the stable identity."
    compiled = parse_media_project(project)
    assert not compiled["valid"]
    assert any(
        item["code"] == "schema.media_manifest.invalid_value"
        and item["field"].endswith(".description")
        for item in compiled["diagnostics"]
    )


def test_manifest_v2_detects_state_cycles_and_unknown_bases():
    project = _project()
    states = project["subjects"][0]["appearanceStates"]
    states[0]["extends"] = "other"
    states.append({"id": "other", "name": "Other", "controls": [], "extends": "base"})
    compiled = parse_media_project(project)
    assert not compiled["valid"]
    assert any(item["code"] == "appearance.state.cycle" for item in compiled["diagnostics"])


def test_manifest_v2_required_dependencies_need_bindings_and_cannot_be_excluded():
    project = _project()
    generation = project["generations"][0]
    generation["bindings"] = []
    compiled = parse_media_project(project)
    assert not compiled["valid"]
    assert any(item["code"] == "reference.binding.missing" for item in compiled["diagnostics"])

    project = _project()
    project["generations"][0]["activation"]["exclude"] = [{"kind": "asset", "id": "ana.identity"}]
    compiled = parse_media_project(project)
    assert not compiled["valid"]
    assert any(item["code"] == "reference.activation.required_excluded" for item in compiled["diagnostics"])


def test_manifest_v2_allows_physical_slot_reuse_between_generations():
    project = {
        "schemaVersion": 2, "mode": "chained_multishot",
        "assets": [
            {"id": "first", "type": "picture", "name": "First"},
            {"id": "second", "type": "picture", "name": "Second"},
        ],
        "subjects": [], "environments": [],
        "generations": [
            {"id": "g1", "order": 1, "activation": {"mode": "explicit", "roots": [{"kind": "asset", "id": "first"}]}, "bindings": [{"assetId": "first", "slotIndex": 1}], "subjectStates": [], "environmentStates": []},
            {"id": "g2", "order": 2, "activation": {"mode": "explicit", "roots": [{"kind": "asset", "id": "second"}]}, "bindings": [{"assetId": "second", "slotIndex": 1}], "subjectStates": [], "environmentStates": []},
        ],
    }
    compiled = parse_media_project(project)
    assert compiled["valid"], compiled["errors"]
    assert compiled["generations"]["g1"]["inputMap"] == {"first": "<Picture 1>"}
    assert compiled["generations"]["g2"]["inputMap"] == {"second": "<Picture 1>"}


def test_manifest_v2_legacy_adapter_projects_first_generation_without_changing_v1():
    legacy = {"items": [{"type": "picture", "role": "identity"}]}
    assert parse_media_manifest(legacy)["items"][0]["label"] == "<Picture 1>"
    projected = parse_media_manifest(_project())
    assert projected["items"][0]["label"] == "<Picture 1>"
    assert projected["subjects"][0]["label"] == "<Subject 1>"


def test_manifest_v2_projects_picture_frame_roles_for_auto_mode_resolution():
    project = _project()
    project["mode"] = "auto"
    project["subjects"] = []
    project["assets"] = [{"id": "opening", "type": "picture", "name": "Opening frame"}]
    project["generations"][0]["bindings"] = [{"assetId": "opening", "slotIndex": 1, "role": "first_frame"}]
    project["generations"][0]["subjectStates"] = []
    project["generations"][0]["activation"] = {"mode": "explicit", "roots": [{"kind": "asset", "id": "opening"}]}
    parsed = parse_media_manifest(project)
    assert parsed["items"][0]["role"] == "first_frame"
    assert resolve_mode("auto", media_manifest=json.dumps(project)) == "i2va"

    del project["generations"][0]["bindings"][0]["role"]
    project["mode"] = "i2va"
    assert parse_media_manifest(project)["items"][0]["role"] == "first_frame"


def test_manifest_v2_rejects_frame_role_on_non_picture_binding():
    project = _project()
    project["assets"][0]["type"] = "video"
    project["assets"][0]["audioMode"] = "off"
    project["generations"][0]["bindings"][0]["role"] = "first_frame"
    compiled = parse_media_project(project)
    assert not compiled["valid"]
    assert any("Only picture bindings" in item["message"] for item in compiled["diagnostics"])


def test_manifest_v2_environment_inheritance_and_carry_are_resolved():
    project = _project()
    project["mode"] = "chained_multishot"
    project["assets"].append({"id": "room.view", "type": "picture", "name": "Room"})
    project["environments"] = [{
        "id": "room", "name": "Room", "permanent": {"architecture": "stone walls"},
        "views": [{"id": "main", "name": "Main", "role": "overview", "assetId": "room.view"}],
        "defaultStateId": "day",
        "states": [
            {"id": "day", "name": "Day", "temporary": {"lighting": "daylight"}},
            {"id": "rain", "name": "Rain", "extends": "day", "temporary": {"weather": "rain"}},
        ],
    }]
    g1 = project["generations"][0]
    g1["bindings"].append({"assetId": "room.view", "slotIndex": 2})
    g1["environmentStates"] = [{"environmentId": "room", "policy": "explicit", "stateId": "rain", "viewIds": ["main"]}]
    project["generations"].append({
        "id": "g2", "order": 2, "activation": {"mode": "auto"},
        "bindings": [{"assetId": "ana.identity", "slotIndex": 1}, {"assetId": "room.view", "slotIndex": 2}],
        "subjectStates": [{"subjectId": "ana", "policy": "carry"}],
        "environmentStates": [{"environmentId": "room", "policy": "carry", "viewIds": ["main"]}],
    })
    compiled = parse_media_project(project)
    assert compiled["valid"], compiled["errors"]
    assert compiled["generations"]["g2"]["initialState"]["environments"]["room"] == "rain"
    context = manifest_context_for_generation(compiled, "g2")
    assert "daylight" in context and "rain" in context and "stone walls" in context
