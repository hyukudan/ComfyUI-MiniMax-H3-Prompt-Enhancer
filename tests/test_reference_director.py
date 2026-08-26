import json

import pytest

from reference_director import (
    build_reference_project,
    canonical_reference_director,
    empty_reference_director,
    media_type_for_filename,
    parse_reference_director,
    reference_context_for_project,
    safe_source_filename,
)


def source(media_type="picture", filename="portrait-a1b2c3d4e5f6.webp"):
    return {
        "storage": "comfy_input",
        "file": f"minimax_h3_reference_director/{filename} [input]",
        "sha256": "a" * 64,
        "mediaType": media_type,
        "originalName": "portrait.webp",
        "sizeBytes": 42,
        "mimeType": "image/webp",
    }


def test_source_filename_is_flat_sanitized_and_typed():
    assert safe_source_filename(r"C:\secret folder\Ana final.WEBP") == "Ana-final.webp"
    assert media_type_for_filename("voice.MP3") == "audio"
    assert media_type_for_filename("acting.mov") == "video"
    with pytest.raises(ValueError, match="Unsupported"):
        safe_source_filename("notes.txt")


def test_reference_director_is_strict_separate_and_canonical():
    value = empty_reference_director()
    value["sources"]["asset.ana"] = source()
    parsed = parse_reference_director(value)
    assert parsed["valid"] is True
    canonical = canonical_reference_director(value)
    assert json.loads(canonical) == parsed["value"]
    broken = {**value, "mediaProject": {"schemaVersion": 2}}
    assert parse_reference_director(broken)["valid"] is False


def test_reference_director_rejects_paths_type_drift_and_bad_hashes():
    value = empty_reference_director()
    value["sources"]["asset.ana"] = {
        **source(media_type="audio"),
        "file": "minimax_h3_reference_director/../portrait.webp [input]",
        "sha256": "BAD",
    }
    issues = parse_reference_director(value)["issues"]
    assert any("traversal" in issue for issue in issues)
    assert any("does not match" in issue for issue in issues)
    assert any("SHA-256" in issue for issue in issues)


def test_reference_project_bundles_physical_and_semantic_documents_with_digest():
    director = empty_reference_director()
    director["sources"]["asset.ana"] = source()
    media = {
        "schemaVersion": 2,
        "assets": [{"id": "asset.ana", "type": "picture", "name": "Ana"}],
        "generations": [{"id": "g1", "bindings": [{"assetId": "asset.ana", "slotIndex": 1}]}],
    }
    shots = {"schemaVersion": 2, "shots": [{"id": "s1"}]}
    project = build_reference_project(director, json.dumps(media), json.dumps(shots))
    assert project["format"] == "minimax-h3-reference-project"
    assert project["director"]["sources"]["asset.ana"]["file"].endswith(" [input]")
    assert project["mediaProject"] == media
    assert project["shotPlan"] == shots
    assert project["inputsByGeneration"]["g1"][0]["label"] == "<Picture 1>"
    assert project["inputsByGeneration"]["g1"][0]["source"]["sha256"] == "a" * 64
    assert project["issues"] == []
    assert len(project["digest"]) == 64


def test_reference_project_orders_each_physical_modality_by_h3_slot():
    director = empty_reference_director()
    director["sources"]["picture.two"] = source(filename="two.webp")
    director["sources"]["picture.one"] = source(filename="one.webp")
    media = {
        "schemaVersion": 2,
        "assets": [
            {"id": "picture.two", "type": "picture"},
            {"id": "picture.one", "type": "picture"},
        ],
        "generations": [{"id": "g1", "bindings": [
            {"assetId": "picture.two", "slotIndex": 2},
            {"assetId": "picture.one", "slotIndex": 1},
        ]}],
    }
    project = build_reference_project(director, media)
    assert [item["label"] for item in project["inputsByGeneration"]["g1"]] == ["<Picture 1>", "<Picture 2>"]


def test_reference_project_rejects_malformed_or_legacy_semantic_documents():
    with pytest.raises(ValueError, match="Media Project JSON is invalid"):
        build_reference_project(empty_reference_director(), "{")
    with pytest.raises(ValueError, match="schemaVersion 2"):
        build_reference_project(empty_reference_director(), {"schemaVersion": 1})


def test_reference_project_reports_duplicate_and_gapped_slots():
    director = empty_reference_director()
    director["sources"]["picture.one"] = source(filename="one.webp")
    director["sources"]["picture.two"] = source(filename="two.webp")
    media = {
        "schemaVersion": 2,
        "assets": [{"id": "picture.one", "type": "picture"}, {"id": "picture.two", "type": "picture"}],
        "generations": [{"id": "g1", "bindings": [
            {"assetId": "picture.one", "slotIndex": 2}, {"assetId": "picture.two", "slotIndex": 2},
        ]}],
    }
    issues = build_reference_project(director, media)["issues"]
    assert any("duplicate picture" in issue for issue in issues)
    assert any("contiguous from 1" in issue for issue in issues)


def test_frame_roles_compile_boundary_semantics_before_identity_fallback():
    project = {
        "mediaProject": {"subjects": [{"id": "subject.1", "name": "Ana", "identityAssetIds": ["frame"]}], "environments": []},
        "shotPlan": {"shots": []},
        "inputsByGeneration": {"g1": [{
            "label": "<Picture 1>", "assetId": "frame", "mediaType": "picture", "role": "first_frame",
        }]},
    }
    context = reference_context_for_project(project, "g1")
    assert "fixes the exact opening frame" in context
    assert "supplies only the stable visual identity" not in context


def test_frame_boundary_keeps_an_explicit_secondary_identity_relationship():
    project = {
        "mediaProject": {"subjects": [{"id": "subject.1", "name": "Ana", "identityAssetIds": ["frame"]}], "environments": []},
        "shotPlan": {"shots": [{
            "id": "s1", "generationId": "g1",
            "referenceUses": [{"assetId": "frame", "role": "identity_reinforcement", "targetIds": ["subject.1"]}],
        }]},
        "inputsByGeneration": {"g1": [{
            "label": "<Picture 1>", "assetId": "frame", "mediaType": "picture", "role": "first_frame",
        }]},
    }
    context = reference_context_for_project(project, "g1")
    assert "fixes the exact opening frame" in context
    assert "supplies only the stable visual identity of Ana in shot s1" in context


def test_project_default_voice_compiles_without_a_shot_use():
    project = {
        "mediaProject": {
            "assets": [{"id": "voice", "type": "audio", "name": "Ana voice"}],
            "subjects": [{"id": "subject.1", "name": "Ana", "identityAssetIds": [], "defaultVoiceAssetId": "voice"}],
            "environments": [],
        },
        "shotPlan": {"shots": []},
        "inputsByGeneration": {"g1": [{
            "label": "<Audio 1>", "assetId": "voice", "mediaType": "audio", "role": "reference",
        }]},
    }
    context = reference_context_for_project(project, "g1")
    assert "voice timbre and delivery only for Ana as the project default" in context
    assert "supplies no dialogue words" in context


def test_visual_subject_identity_and_voice_compile_to_the_same_named_llm_subject():
    project = {
        "mediaProject": {
            "assets": [
                {"id": "ana.image", "type": "picture", "name": "Ana image"},
                {"id": "ana.voice", "type": "audio", "name": "Ana voice"},
            ],
            "subjects": [{
                "id": "subject.1", "h3Index": 1, "name": "Ana", "description": "",
                "identityAssetIds": ["ana.image"], "defaultVoiceAssetId": "ana.voice",
            }],
            "environments": [],
        },
        "shotPlan": {"shots": [{
            "id": "s1", "generationId": "g1", "action": "Ana turns.",
            "subjects": [{"subjectId": "subject.1", "presence": "present"}],
            "referenceUses": [
                {"assetId": "ana.image", "role": "identity_reinforcement", "targetIds": ["subject.1"]},
                {"assetId": "ana.voice", "role": "voice", "targetIds": ["subject.1"]},
            ],
        }]},
        "inputsByGeneration": {"g1": [
            {"label": "<Picture 1>", "assetId": "ana.image", "mediaType": "picture", "role": "reference"},
            {"label": "<Audio 1>", "assetId": "ana.voice", "mediaType": "audio", "role": "reference"},
        ]},
    }
    context = reference_context_for_project(project, "g1")
    assert "<Picture 1> supplies only the stable visual identity of Ana in shot s1" in context
    assert "<Audio 1> supplies voice timbre and delivery only for Ana in shot s1" in context
    assert "supplies no dialogue words" in context


def test_frame_mode_infers_the_same_effective_role_as_the_visual_editor():
    director = empty_reference_director()
    director["sources"]["frame"] = source(filename="frame.webp")
    media = {
        "schemaVersion": 2, "mode": "i2va",
        "assets": [{"id": "frame", "type": "picture"}],
        "generations": [{"id": "g1", "bindings": [{"assetId": "frame", "slotIndex": 1}]}],
    }
    project = build_reference_project(director, media)
    assert project["inputsByGeneration"]["g1"][0]["role"] == "first_frame"


def test_reference_context_rejects_an_unknown_explicit_generation():
    with pytest.raises(ValueError, match="Unknown reference generation"):
        reference_context_for_project({"inputsByGeneration": {"g1": []}}, "missing")


@pytest.mark.parametrize(("media_type", "role", "target_id", "expected"), [
    ("picture", "identity_reinforcement", "subject.1", "stable visual identity of Ana in shot s1"),
    ("audio", "voice", "subject.1", "voice timbre and delivery only for Ana in shot s1"),
    ("picture", "environment_view", "environment.1", "background/set for Rooftop in shot s1"),
    ("video", "performance", "subject.1", "performance timing and body motion for Ana in shot s1"),
    ("video", "camera_transfer", None, "only motion, framing in shot s1"),
    ("audio", "soundtrack", None, "music or soundtrack only in shot s1"),
    ("picture", "continuity", None, "visible continuity source in shot s1"),
    ("picture", "appearance", "subject.1", "appearance edit for Ana in shot s1"),
    ("picture", "lighting", None, "lighting guidance only in shot s1"),
])
def test_assistant_relationships_reach_the_llm_context(media_type, role, target_id, expected):
    use = {"assetId": "asset", "role": role}
    if target_id:
        use["targetIds"] = [target_id]
    if role == "camera_transfer":
        use["cameraAspects"] = ["motion", "framing"]
    project = {
        "mediaProject": {
            "assets": [{"id": "asset", "type": media_type, "name": "Reference", "description": "User-authored observation"}],
            "subjects": [{"id": "subject.1", "name": "Ana", "identityAssetIds": []}],
            "environments": [{"id": "environment.1", "name": "Rooftop", "views": []}],
        },
        "shotPlan": {"shots": [
            {"id": "wrong", "generationId": "g2", "referenceUses": [{"assetId": "asset", "role": "voice", "targetIds": ["subject.1"]}]},
            {"id": "s1", "generationId": "g1", "referenceUses": [use]},
        ]},
        "inputsByGeneration": {"g1": [{
            "label": f"<{media_type.title()} 1>", "assetId": "asset", "mediaType": media_type, "role": "reference",
        }]},
    }
    context = reference_context_for_project(project, "g1")
    assert expected in context
    assert 'user description: "User-authored observation"' in context
    assert "shot wrong" not in context
