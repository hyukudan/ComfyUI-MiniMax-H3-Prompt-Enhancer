# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pytest

from camera_authority import (
    CAMERA_AUTHORITY,
    CameraAuthorityResolution,
    CameraClaim,
    CameraPhase,
    CameraSourceKind,
    ShadowReason,
    camera_values_compatible,
    claims_from_global_cinematography,
    claims_from_shot_plan,
    claims_from_video_references,
    resolve_camera_authority,
    validate_generated_camera_claims,
)
from diagnostics import (
    CameraAspect,
    DiagnosticCode,
    DiagnosticCollector,
    DiagnosticLocation,
    LocationScope,
)


def _claim(
    source_kind: CameraSourceKind,
    value="wide",
    *,
    source_id: str | None = None,
    aspect: CameraAspect = CameraAspect.FRAMING,
    phase: CameraPhase = CameraPhase.START,
    shot_id: str = "s1",
    confidence: float = 1.0,
) -> CameraClaim:
    source_id = source_id or source_kind.value
    return CameraClaim(
        shot_id, aspect, phase, value, source_kind, source_id, confidence,
        DiagnosticLocation(LocationScope.CONFIGURATION, f"test.{source_id}", shot_id=shot_id),
    )


def _media_project(*, transfer=True, role="camera_reference", active=True, bound=True, aspects=("motion",)):
    asset = {
        "id": "camera.ref", "type": "video", "name": "Camera reference",
        "cameraTransfer": {"enabled": transfer, "role": role, "aspects": list(aspects)},
    }
    generation = {
        "activeAssetIds": ["camera.ref"] if active else [],
        "inputMap": {"camera.ref": "<Video 1>"} if bound else {},
    }
    return {
        "schemaVersion": 2,
        "project": {"assets": [asset]},
        "generations": {"g1": generation},
    }


def _video_shot(*, role="camera_transfer", aspects=("motion",), asset_id="camera.ref"):
    return {
        "schemaVersion": 2,
        "shots": [{
            "id": "s1", "generationId": "g1", "action": "Ana walks.",
            "referenceUses": [{"assetId": asset_id, "role": role, "cameraAspects": list(aspects)}],
        }],
    }


def test_precedence_table_is_exact_and_complete():
    assert CAMERA_AUTHORITY == {
        CameraSourceKind.SOURCE_PROMPT: 100,
        CameraSourceKind.VIDEO_REFERENCE: 90,
        CameraSourceKind.SHOT_PLAN: 80,
        CameraSourceKind.GLOBAL_CINEMATOGRAPHY: 60,
        CameraSourceKind.GENERATED_PROSE: 40,
        CameraSourceKind.CREATIVE_TREATMENT: 20,
    }


def test_no_claim_produces_no_owner_or_default():
    resolution = resolve_camera_authority(())
    assert resolution == CameraAuthorityResolution((), (), ())
    assert resolution.valid
    assert resolution.to_dict() == {"valid": True, "owners": [], "shadowed": [], "conflicts": []}


@pytest.mark.parametrize("aspect", tuple(CameraAspect))
@pytest.mark.parametrize("phase", tuple(CameraPhase))
def test_every_aspect_and_phase_resolves_only_its_exact_key(aspect, phase):
    claim = _claim(CameraSourceKind.SOURCE_PROMPT, aspect.value, aspect=aspect, phase=phase)
    resolution = resolve_camera_authority((claim,))
    assert resolution.owners == (resolution.owner_for("s1", phase, aspect),)
    different_aspect = next(item for item in CameraAspect if item is not aspect)
    assert resolution.owner_for("s1", phase, different_aspect) is None


def test_shot_plan_overrides_global_silently_and_records_shadow():
    shot = _claim(CameraSourceKind.SHOT_PLAN, "close_up")
    global_claim = _claim(CameraSourceKind.GLOBAL_CINEMATOGRAPHY, "wide", phase=CameraPhase.WHOLE_SHOT)
    collector = DiagnosticCollector()
    resolution = resolve_camera_authority((global_claim, shot), collector)

    owner = resolution.owner_for("s1", CameraPhase.START, CameraAspect.FRAMING)
    assert owner is not None and owner.claim is shot
    assert resolution.conflicts == ()
    assert len(resolution.shadowed) == 1
    assert resolution.shadowed[0].shadowed is global_claim
    assert resolution.shadowed[0].reason is ShadowReason.SHOT_OVERRIDES_GLOBAL
    assert collector.diagnostics == ()


def test_start_and_end_are_independent_owners_not_a_conflict():
    start = _claim(CameraSourceKind.SHOT_PLAN, "wide", phase=CameraPhase.START)
    end = _claim(CameraSourceKind.SHOT_PLAN, "close_up", phase=CameraPhase.END)
    resolution = resolve_camera_authority((end, start))
    assert resolution.valid
    assert [(owner.phase, owner.claim.value) for owner in resolution.owners] == [
        (CameraPhase.START, "wide"), (CameraPhase.END, "close_up"),
    ]


@pytest.mark.parametrize(
    "first_kind,second_kind",
    [
        (CameraSourceKind.SOURCE_PROMPT, CameraSourceKind.VIDEO_REFERENCE),
        (CameraSourceKind.SOURCE_PROMPT, CameraSourceKind.SHOT_PLAN),
        (CameraSourceKind.SOURCE_PROMPT, CameraSourceKind.GLOBAL_CINEMATOGRAPHY),
        (CameraSourceKind.VIDEO_REFERENCE, CameraSourceKind.SHOT_PLAN),
        (CameraSourceKind.VIDEO_REFERENCE, CameraSourceKind.GLOBAL_CINEMATOGRAPHY),
        (CameraSourceKind.VIDEO_REFERENCE, CameraSourceKind.VIDEO_REFERENCE),
    ],
)
def test_incompatible_explicit_authority_pairs_block_configuration(first_kind, second_kind):
    collector = DiagnosticCollector()
    first = _claim(first_kind, "wide", source_id=first_kind.value + ".1")
    second = _claim(second_kind, "close_up", source_id=second_kind.value + ".2")
    resolution = resolve_camera_authority((second, first), collector)
    assert not resolution.valid
    assert len(resolution.conflicts) == 1
    assert collector.diagnostics[0].code is DiagnosticCode.CAMERA_AUTHORITY_EXPLICIT_CONFLICT
    assert collector.diagnostics[0].blocks.valid
    assert collector.to_report()["summary"]["valid"] is False


def test_global_beats_treatment_and_generated_prose_without_configuration_conflict():
    global_claim = _claim(CameraSourceKind.GLOBAL_CINEMATOGRAPHY, "wide")
    prose = _claim(CameraSourceKind.GENERATED_PROSE, "medium")
    treatment = _claim(CameraSourceKind.CREATIVE_TREATMENT, "close_up")
    resolution = resolve_camera_authority((treatment, prose, global_claim))
    assert resolution.valid
    assert resolution.owners[0].claim is global_claim
    assert {item.shadowed for item in resolution.shadowed} == {prose, treatment}
    assert all(item.reason is ShadowReason.LOWER_AUTHORITY for item in resolution.shadowed)


def test_equal_and_compatible_values_merge_as_supporting_provenance():
    source = _claim(CameraSourceKind.SOURCE_PROMPT, {"motionType": "push_in"}, aspect=CameraAspect.MOTION)
    shot = _claim(
        CameraSourceKind.SHOT_PLAN,
        {"motionType": "push_in", "speed": "slow"},
        aspect=CameraAspect.MOTION,
    )
    prose = _claim(CameraSourceKind.GENERATED_PROSE, {"motionType": "push_in"}, aspect=CameraAspect.MOTION)
    resolution = resolve_camera_authority((shot, prose, source))
    assert resolution.valid
    assert resolution.owners[0].claim is source
    assert resolution.owners[0].supporting_claims == (shot, prose)
    assert camera_values_compatible(source.value, shot.value)
    assert not camera_values_compatible({"motionType": "push_in"}, {"speed": "slow"})


def test_resolution_is_deterministic_under_input_reordering():
    claims = (
        _claim(CameraSourceKind.CREATIVE_TREATMENT, "medium", source_id="treatment"),
        _claim(CameraSourceKind.SHOT_PLAN, "close_up", source_id="shot"),
        _claim(CameraSourceKind.GLOBAL_CINEMATOGRAPHY, "wide", source_id="global"),
    )
    assert resolve_camera_authority(claims).to_dict() == resolve_camera_authority(reversed(claims)).to_dict()


def test_shot_plan_builder_resolves_sparse_end_and_maps_path_as_one_motion_claim():
    plan = {
        "schemaVersion": 2,
        "shots": [{
            "id": "s1", "generationId": "g1", "action": "Ana walks.",
            "cameraStart": {
                "framing": "wide", "viewpoint": "rear",
                "composition": "rule_of_thirds", "primaryTarget": {"kind": "subject", "id": "ana"},
                "distance": "far",
            },
            "cameraEnd": {"framing": "medium"},
            "cameraPath": {"motionType": "push_in", "speed": "slow", "easing": "ease_out"},
        }],
    }
    claims = claims_from_shot_plan(plan)
    owners = resolve_camera_authority(claims)
    assert owners.owner_for("s1", CameraPhase.START, CameraAspect.FRAMING).claim.value == "wide"
    assert owners.owner_for("s1", CameraPhase.END, CameraAspect.FRAMING).claim.value == "medium"
    assert owners.owner_for("s1", CameraPhase.END, CameraAspect.VIEWPOINT).claim.value == "rear"
    motion = owners.owner_for("s1", CameraPhase.PATH, CameraAspect.MOTION).claim.to_dict()["value"]
    assert motion == {"easing": "ease_out", "motionType": "push_in", "speed": "slow"}
    assert not any(owner.aspect in {CameraAspect.LENS, CameraAspect.STABILITY} for owner in owners.owners)


def test_global_builder_omits_neutral_values_and_projects_only_supplied_aspects():
    claims = claims_from_global_cinematography({
        "shotScale": "wide", "cameraAngle": "none", "cameraViewpoint": "pov",
        "cameraMotion": "push_in", "cameraAmplitude": "small", "cameraSpeed": "auto",
        "optics": "lens_35mm", "lensEffects": "clean", "depthOfField": "none",
    }, ("s1", "s2"))
    assert len(claims) == 8
    assert {claim.phase for claim in claims} == {CameraPhase.WHOLE_SHOT}
    assert {claim.aspect for claim in claims} == {
        CameraAspect.FRAMING, CameraAspect.VIEWPOINT, CameraAspect.MOTION, CameraAspect.LENS,
    }
    assert all(claim.source_kind is CameraSourceKind.GLOBAL_CINEMATOGRAPHY for claim in claims)


def test_video_transfer_requires_every_structural_gate():
    claims = claims_from_video_references(_media_project(), _video_shot())
    assert len(claims) == 1
    assert claims[0].source_kind is CameraSourceKind.VIDEO_REFERENCE
    assert claims[0].aspect is CameraAspect.MOTION
    assert claims[0].to_dict()["value"] == {"cameraReferenceAssetId": "camera.ref"}


@pytest.mark.parametrize(
    "project,shot",
    [
        (_media_project(transfer=False), _video_shot()),
        (_media_project(role="performance"), _video_shot()),
        (_media_project(active=False), _video_shot()),
        (_media_project(bound=False), _video_shot()),
        (_media_project(), _video_shot(role="performance")),
        (_media_project(), _video_shot(asset_id="other.video")),
    ],
)
def test_video_without_any_one_required_gate_never_owns_camera(project, shot):
    assert claims_from_video_references(project, shot) == ()


def test_reuse_mode_or_video_presence_alone_never_grants_camera_authority():
    project = _media_project()
    project["project"]["assets"][0].pop("cameraTransfer")
    project["project"]["assets"][0]["reuse_mode"] = "direct_edit"
    assert claims_from_video_references(project, _video_shot(role="performance")) == ()


def test_video_can_claim_only_declared_and_requested_aspect_intersection():
    project = _media_project(aspects=("motion", "framing"))
    shot = _video_shot(aspects=("framing", "angle"))
    claims = claims_from_video_references(project, shot)
    assert [claim.aspect for claim in claims] == [CameraAspect.FRAMING]


def test_video_conflicts_with_shot_only_on_shared_aspect_and_whole_shot_projects_to_phases():
    project = _media_project(aspects=("motion", "framing"))
    shot_plan = _video_shot(aspects=("motion", "framing"))
    shot_plan["shots"][0].update({
        "cameraStart": {"framing": "wide", "angle": "eye_level"},
        "cameraPath": {"motionType": "static"},
    })
    claims = claims_from_video_references(project, shot_plan) + claims_from_shot_plan(shot_plan)
    resolution = resolve_camera_authority(claims)
    assert {(item.phase, item.aspect) for item in resolution.conflicts} == {
        (CameraPhase.START, CameraAspect.FRAMING),
        (CameraPhase.END, CameraAspect.FRAMING),
        (CameraPhase.PATH, CameraAspect.MOTION),
    }
    assert resolution.owner_for("s1", CameraPhase.START, CameraAspect.ANGLE).claim.source_kind is CameraSourceKind.SHOT_PLAN


def test_claim_values_are_deeply_immutable_and_serializable():
    source = {"motionType": "push_in", "qualifiers": ["slow"]}
    claim = _claim(CameraSourceKind.SHOT_PLAN, source, aspect=CameraAspect.MOTION)
    source["qualifiers"].append("large")
    assert claim.to_dict()["value"] == {"motionType": "push_in", "qualifiers": ["slow"]}
    with pytest.raises(TypeError):
        claim.value["motionType"] = "pull_out"


def test_claim_rejects_raw_discriminants_and_non_json_values():
    with pytest.raises(TypeError, match="CameraAspect"):
        CameraClaim(
            "s1", "framing", CameraPhase.START, "wide", CameraSourceKind.SHOT_PLAN, "shot:s1", 1,
            DiagnosticLocation(LocationScope.CONFIGURATION, "cameraStart"),
        )
    with pytest.raises(TypeError, match="JSON-compatible"):
        _claim(CameraSourceKind.SHOT_PLAN, object())


def test_generated_prose_matching_owner_is_realized_without_diagnostic():
    owner_claim = _claim(CameraSourceKind.SHOT_PLAN, {"motionType": "push_in"}, aspect=CameraAspect.MOTION,
                         phase=CameraPhase.PATH)
    generated = _claim(CameraSourceKind.GENERATED_PROSE, {"motionType": "push_in", "speed": "slow"},
                       aspect=CameraAspect.MOTION, phase=CameraPhase.PATH)
    authority = resolve_camera_authority((owner_claim,))
    collector = DiagnosticCollector()
    assert validate_generated_camera_claims(authority, (generated,), collector) == ()
    assert collector.diagnostics == ()


def test_generated_canonical_contradiction_is_repairable_output_error():
    owner_claim = _claim(CameraSourceKind.VIDEO_REFERENCE, {"motionType": "push_in"},
                         aspect=CameraAspect.MOTION, phase=CameraPhase.PATH)
    generated = _claim(CameraSourceKind.GENERATED_PROSE, {"motionType": "pull_out"},
                       aspect=CameraAspect.MOTION, phase=CameraPhase.PATH, confidence=0.95)
    authority = resolve_camera_authority((owner_claim,))
    collector = DiagnosticCollector()
    fingerprints = validate_generated_camera_claims(authority, (generated,), collector)
    diagnostic = collector.diagnostics[0]
    assert fingerprints == (diagnostic.fingerprint,)
    assert diagnostic.code is DiagnosticCode.CAMERA_AUTHORITY_OUTPUT_CONTRADICTION
    assert diagnostic.repair.eligible and diagnostic.repair.priority == 90
    assert diagnostic.location.scope is LocationScope.OUTPUT
    assert collector.to_report()["summary"]["valid"] is False


def test_generated_low_confidence_mismatch_is_advice_not_error():
    owner_claim = _claim(CameraSourceKind.SHOT_PLAN, "wide")
    generated = _claim(CameraSourceKind.GENERATED_PROSE, "close_up", confidence=0.5)
    collector = DiagnosticCollector()
    validate_generated_camera_claims(resolve_camera_authority((owner_claim,)), (generated,), collector)
    diagnostic = collector.diagnostics[0]
    assert diagnostic.code is DiagnosticCode.CAMERA_AUTHORITY_OUTPUT_AMBIGUOUS
    assert not diagnostic.blocks.valid and not diagnostic.repair.eligible
    assert collector.to_report()["summary"]["valid"] is True


def test_missing_generated_claim_is_quality_gap_and_whole_shot_can_satisfy_phases():
    start = _claim(CameraSourceKind.SHOT_PLAN, "wide", phase=CameraPhase.START)
    end = _claim(CameraSourceKind.SHOT_PLAN, "medium", phase=CameraPhase.END)
    collector = DiagnosticCollector()
    validate_generated_camera_claims(resolve_camera_authority((start, end)), (), collector)
    assert [item.code for item in collector.diagnostics] == [
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING,
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING,
    ]
    assert collector.to_report()["summary"] == {
        "errors": 0, "warnings": 2, "advice": 0, "info": 0,
        "suppressedCoach": 0, "valid": True, "qualityValid": False,
    }

    compatible_whole = _claim(CameraSourceKind.GENERATED_PROSE, "wide", phase=CameraPhase.WHOLE_SHOT)
    collector = DiagnosticCollector()
    validate_generated_camera_claims(resolve_camera_authority((start,)), (compatible_whole,), collector)
    assert collector.diagnostics == ()


def test_output_adherence_is_skipped_until_configuration_conflicts_are_resolved():
    source = _claim(CameraSourceKind.SOURCE_PROMPT, "wide")
    video = _claim(CameraSourceKind.VIDEO_REFERENCE, "close_up")
    authority = resolve_camera_authority((source, video))
    collector = DiagnosticCollector()
    assert validate_generated_camera_claims(authority, (), collector) == ()
    assert collector.diagnostics == ()
