# SPDX-License-Identifier: GPL-3.0-only

import json
import re
from dataclasses import FrozenInstanceError

import pytest

from diagnostics import (
    DIAGNOSTIC_CATALOG,
    DIAGNOSTIC_CATALOG_VERSION,
    DIAGNOSTIC_REPORT_SCHEMA_VERSION,
    ActivateResourceAction,
    AddBindingAction,
    AlignTransitionFromStateAction,
    Basis,
    CameraAspect,
    Category,
    ClearGlobalCameraAction,
    ClearShotCameraAction,
    Diagnostic,
    DiagnosticBlocks,
    DiagnosticCode,
    DiagnosticCollector,
    DiagnosticLocation,
    DiagnosticRepair,
    DiagnosticResource,
    EntityKind,
    LegacyBucket,
    LocationScope,
    ResourceKind,
    Severity,
    compact_excerpt,
    diagnostic_fingerprint,
    diagnostic_report_digest,
)


OUTPUT_LOCATION = DiagnosticLocation(LocationScope.OUTPUT, "detailed_description", shot_id="s1", shot_index=0)


def test_catalog_covers_every_public_code_and_uses_fixed_policy():
    assert set(DIAGNOSTIC_CATALOG) == set(DiagnosticCode)
    assert {code.value for code in DiagnosticCode} == {
        "schema.media_manifest.invalid_json", "schema.media_manifest.unsupported_version",
        "schema.shot_plan.invalid_json", "schema.shot_plan.unsupported_version",
        "reference.activation.unknown_resource", "reference.activation.required_excluded",
        "reference.binding.missing", "reference.binding.duplicate_slot", "reference.binding.type_mismatch",
        "reference.capacity.exceeded", "reference.output.inactive_label", "reference.output.active_unused",
        "appearance.state.cycle", "appearance.transition.from_mismatch",
        "appearance.transition.subject_absent", "appearance.identity.illegal_change",
        "appearance.output.transition_missing", "environment.state.cycle",
        "environment.transition.from_mismatch", "environment.state.permanent_mutation",
        "environment.output.transition_missing", "camera.authority.explicit_conflict",
        "camera.authority.output_contradiction", "camera.authority.output_ambiguous",
        "camera.path.qualifier_without_motion", "camera.output.claim_missing",
        "coach.action.locomotion_under_specified", "coach.action.orientation_under_specified",
        "coach.action.manipulation_under_specified", "coach.identity.ambiguous_pronoun",
        "coach.action.opening_duplicate", "coach.cut.weak", "coach.dialogue.timing_pressure",
        "coach.prose.aesthetic_noise",
    }
    assert DIAGNOSTIC_CATALOG_VERSION >= 1
    assert DIAGNOSTIC_CATALOG[DiagnosticCode.COACH_WEAK_CUT].category is Category.COACH
    assert DIAGNOSTIC_CATALOG[DiagnosticCode.COACH_WEAK_CUT].basis is Basis.HEURISTIC
    assert not DIAGNOSTIC_CATALOG[DiagnosticCode.COACH_WEAK_CUT].blocks.valid
    assert DIAGNOSTIC_CATALOG[DiagnosticCode.MEDIA_MANIFEST_INVALID_JSON].blocks.valid


def test_diagnostic_serializes_to_the_versioned_schema_shape():
    related = DiagnosticResource(ResourceKind.SHOT, "s1")
    diagnostic = Diagnostic.create(
        DiagnosticCode.CAMERA_AUTHORITY_OUTPUT_CONTRADICTION,
        "The generated camera direction contradicts the resolved owner.",
        DiagnosticLocation(
            LocationScope.OUTPUT,
            "cameraPath.motionType",
            generation_id="g1",
            shot_id="s1",
            shot_index=0,
            section="detailed_description",
            start_offset=12,
            end_offset=34,
            excerpt="The camera pulls back.",
        ),
        confidence=0.98,
        repair_instruction="Make the generated camera motion follow the resolved owner.",
        related=(related,),
        suggestions=("Keep the camera claim explicit in the shot clause.",),
        actions=(ClearShotCameraAction("Clear local motion", "s1", (CameraAspect.MOTION,)),),
        data={"owner": {"source": "video", "rank": 90}, "observed": ["pull_out"]},
    )

    serialized = diagnostic.to_dict()
    assert serialized == {
        "code": "camera.authority.output_contradiction",
        "severity": "error",
        "category": "camera",
        "confidence": 0.98,
        "basis": "derived",
        "blocks": {"valid": True, "quality": False},
        "repair": {
            "eligible": True,
            "priority": 90,
            "instruction": "Make the generated camera motion follow the resolved owner.",
        },
        "message": "The generated camera direction contradicts the resolved owner.",
        "location": {
            "scope": "output",
            "field": "cameraPath.motionType",
            "generationId": "g1",
            "shotId": "s1",
            "shotIndex": 0,
            "section": "detailed_description",
            "startOffset": 12,
            "endOffset": 34,
            "excerpt": "The camera pulls back.",
        },
        "related": [{"kind": "shot", "id": "s1"}],
        "suggestions": ["Keep the camera claim explicit in the shot clause."],
        "actions": [{
            "kind": "clear_shot_camera",
            "label": "Clear local motion",
            "shotId": "s1",
            "aspects": ["motion"],
        }],
        "data": {"owner": {"source": "video", "rank": 90}, "observed": ["pull_out"]},
        "fingerprint": diagnostic.fingerprint,
    }
    assert re.fullmatch(r"[a-f0-9]{64}", diagnostic.fingerprint)
    json.dumps(serialized)


def test_fingerprint_ignores_message_excerpt_and_related_order_but_tracks_location():
    first_related = (
        DiagnosticResource(ResourceKind.ASSET, "camera.reference"),
        DiagnosticResource(ResourceKind.SHOT, "s1"),
    )
    first_location = DiagnosticLocation(
        LocationScope.OUTPUT, "cameraPath", shot_id="s1", start_offset=10, end_offset=20, excerpt="first",
    )
    second_location = DiagnosticLocation(
        LocationScope.OUTPUT, "cameraPath", shot_id="s1", start_offset=10, end_offset=20, excerpt="changed",
    )
    assert diagnostic_fingerprint(
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING, first_location, first_related,
    ) == diagnostic_fingerprint(
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING, second_location, reversed(first_related),
    )
    moved = DiagnosticLocation(LocationScope.OUTPUT, "cameraPath", shot_id="s1", start_offset=11, end_offset=20)
    assert diagnostic_fingerprint(
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING, first_location, first_related,
    ) != diagnostic_fingerprint(
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING, moved, first_related,
    )
    changed_message = Diagnostic.create(
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING,
        "First wording",
        first_location,
        repair_instruction="Add the required camera claim.",
        related=first_related,
    )
    other_wording = Diagnostic.create(
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING,
        "Completely different wording",
        second_location,
        repair_instruction="Add the required camera claim.",
        related=reversed(first_related),
    )
    assert changed_message.fingerprint == other_wording.fingerprint


def test_collector_deduplicates_fingerprints_and_preserves_first_diagnostic():
    collector = DiagnosticCollector()
    first = Diagnostic.create(
        DiagnosticCode.OUTPUT_ACTIVE_UNUSED,
        "First message",
        OUTPUT_LOCATION,
    )
    duplicate = Diagnostic.create(
        DiagnosticCode.OUTPUT_ACTIVE_UNUSED,
        "Later wording",
        OUTPUT_LOCATION,
    )
    assert collector.add(first)
    assert not collector.add(duplicate)
    assert collector.diagnostics == (first,)


def test_report_summary_and_legacy_projection_are_derived_from_policy_not_messages():
    collector = DiagnosticCollector()
    collector.emit(
        DiagnosticCode.MEDIA_MANIFEST_INVALID_JSON,
        "Arbitrary schema wording",
        DiagnosticLocation(LocationScope.INPUT, "media_manifest"),
    )
    collector.emit(
        DiagnosticCode.OUTPUT_ACTIVE_UNUSED,
        "Arbitrary warning wording",
        OUTPUT_LOCATION,
    )
    collector.emit(
        DiagnosticCode.CAMERA_OUTPUT_CLAIM_MISSING,
        "Arbitrary coverage wording",
        DiagnosticLocation(LocationScope.OUTPUT, "cameraPath", shot_id="s2"),
        repair_instruction="State the owned camera path.",
        legacy_bucket=LegacyBucket.COVERAGE_GAPS,
    )
    collector.emit(
        DiagnosticCode.COACH_WEAK_CUT,
        "Advisory only",
        DiagnosticLocation(LocationScope.CONFIGURATION, "shots[1].cutContext", shot_id="s2"),
    )
    collector.suppress_coach(3)

    projection = collector.legacy_projection().to_dict()
    assert projection == {
        "valid": False,
        "qualityValid": False,
        "errors": ["Arbitrary schema wording"],
        "warnings": ["Arbitrary warning wording"],
        "coverageGaps": ["Arbitrary coverage wording"],
        "styleCoverageGaps": [],
        "contentFormatCoverageGaps": [],
    }
    report = collector.to_report()
    assert report["schemaVersion"] == DIAGNOSTIC_REPORT_SCHEMA_VERSION
    assert report["catalogVersion"] == DIAGNOSTIC_CATALOG_VERSION
    assert report["summary"] == {
        "errors": 1,
        "warnings": 2,
        "advice": 1,
        "info": 0,
        "suppressedCoach": 3,
        "valid": False,
        "qualityValid": False,
    }
    assert report["diagnostics"][2]["data"]["legacyBucket"] == "coverageGaps"


def test_quality_blocker_does_not_make_an_otherwise_valid_report_invalid():
    collector = DiagnosticCollector()
    collector.emit(
        DiagnosticCode.APPEARANCE_OUTPUT_TRANSITION_MISSING,
        "The explicit appearance transition is absent.",
        OUTPUT_LOCATION,
        repair_instruction="Realize the explicit appearance transition.",
    )
    assert collector.to_report()["summary"]["valid"] is True
    assert collector.to_report()["summary"]["qualityValid"] is False
    assert collector.legacy_projection().errors == ()


def test_coach_diagnostics_never_block_or_become_repair_eligible():
    diagnostic = Diagnostic.create(
        DiagnosticCode.COACH_LOCOMOTION_UNDER_SPECIFIED,
        "Specify a visible route or destination.",
        DiagnosticLocation(LocationScope.CONFIGURATION, "shots[0].action", shot_id="s1"),
        confidence=0.8,
    )
    assert diagnostic.category is Category.COACH
    assert diagnostic.severity is Severity.ADVICE
    assert diagnostic.blocks == DiagnosticBlocks()
    assert diagnostic.repair == DiagnosticRepair()
    with pytest.raises(ValueError, match="not eligible"):
        Diagnostic.create(
            DiagnosticCode.COACH_LOCOMOTION_UNDER_SPECIFIED,
            "Do not repair this through the LLM.",
            OUTPUT_LOCATION,
            repair_instruction="Rewrite the action.",
        )


def test_all_safe_actions_have_allowlisted_discriminated_shapes():
    actions = (
        ClearShotCameraAction("Clear shot camera", "s1", (CameraAspect.MOTION, CameraAspect.FRAMING)),
        ClearGlobalCameraAction("Clear global camera", (CameraAspect.ANGLE,)),
        ActivateResourceAction(
            "Activate asset", "g1", DiagnosticResource(ResourceKind.ASSET, "asset.picture.1"),
        ),
        AddBindingAction("Bind asset", "g1", "asset.picture.1", 2),
        AlignTransitionFromStateAction(
            "Align transition", "s1", EntityKind.SUBJECT, "ana", "base",
        ),
    )
    assert [action.to_dict()["kind"] for action in actions] == [
        "clear_shot_camera", "clear_global_camera", "activate_resource", "add_binding",
        "align_transition_from_state",
    ]
    diagnostic = Diagnostic.create(
        DiagnosticCode.CAMERA_AUTHORITY_EXPLICIT_CONFLICT,
        "Two explicit owners conflict.",
        DiagnosticLocation(LocationScope.CONFIGURATION, "shots[0].cameraPath", shot_id="s1"),
        actions=actions,
    )
    assert diagnostic.to_dict()["actions"] == [action.to_dict() for action in actions]


@pytest.mark.parametrize(
    "factory,match",
    [
        (lambda: ClearShotCameraAction("Clear", "s1", ()), "at least one"),
        (lambda: ClearGlobalCameraAction("Clear", (CameraAspect.MOTION, CameraAspect.MOTION)), "unique"),
        (lambda: AddBindingAction("Bind", "g1", "a1", 0), "between 1 and 9"),
        (lambda: ActivateResourceAction(
            "Activate", "g1", DiagnosticResource(ResourceKind.SHOT, "s1"),
        ), "only asset"),
    ],
)
def test_safe_actions_reject_out_of_contract_values(factory, match):
    with pytest.raises(ValueError, match=match):
        factory()


def test_location_validates_offsets_and_excerpt_limit():
    with pytest.raises(ValueError, match="requires start"):
        DiagnosticLocation(LocationScope.OUTPUT, "prompt", end_offset=4)
    with pytest.raises(ValueError, match="precede"):
        DiagnosticLocation(LocationScope.OUTPUT, "prompt", start_offset=5, end_offset=4)
    with pytest.raises(ValueError, match="160"):
        DiagnosticLocation(LocationScope.OUTPUT, "prompt", excerpt="x" * 161)
    assert compact_excerpt(" one\n  two  three ") == "one two three"
    assert compact_excerpt("x" * 200, 10) == "xxxxxxxxx…"


def test_diagnostic_rejects_invalid_limits_and_non_json_data():
    with pytest.raises(ValueError, match="finite"):
        Diagnostic.create(DiagnosticCode.OUTPUT_ACTIVE_UNUSED, "message", OUTPUT_LOCATION, confidence=float("nan"))
    with pytest.raises(ValueError, match="three suggestions"):
        Diagnostic.create(
            DiagnosticCode.OUTPUT_ACTIVE_UNUSED, "message", OUTPUT_LOCATION,
            suggestions=("one", "two", "three", "four"),
        )
    with pytest.raises(TypeError, match="JSON-compatible"):
        Diagnostic.create(
            DiagnosticCode.OUTPUT_ACTIVE_UNUSED, "message", OUTPUT_LOCATION, data={"bad": object()},
        )
    with pytest.raises(ValueError, match="reserved"):
        Diagnostic.create(
            DiagnosticCode.OUTPUT_ACTIVE_UNUSED, "message", OUTPUT_LOCATION,
            data={"legacyBucket": "coverageGaps"},
        )


def test_diagnostic_data_and_core_objects_are_immutable():
    source = {"nested": {"items": [1, 2]}}
    diagnostic = Diagnostic.create(
        DiagnosticCode.OUTPUT_ACTIVE_UNUSED, "message", OUTPUT_LOCATION, data=source,
    )
    source["nested"]["items"].append(3)
    assert diagnostic.to_dict()["data"] == {"nested": {"items": [1, 2]}}
    with pytest.raises(TypeError):
        diagnostic.data["new"] = True
    with pytest.raises(FrozenInstanceError):
        diagnostic.message = "changed"


def test_report_digest_is_canonical_and_changes_with_structured_content():
    first = {"b": [2], "a": {"x": 1}}
    reordered = {"a": {"x": 1}, "b": [2]}
    assert diagnostic_report_digest(first) == diagnostic_report_digest(reordered)
    assert diagnostic_report_digest(first) != diagnostic_report_digest({"a": {"x": 2}, "b": [2]})
    collector = DiagnosticCollector()
    assert collector.digest() == diagnostic_report_digest(collector.to_report())


def test_schema_file_matches_report_contract_and_action_allowlist():
    with open("docs/schemas/diagnostic_report_v1.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    assert schema["properties"]["schemaVersion"]["const"] == DIAGNOSTIC_REPORT_SCHEMA_VERSION
    assert schema["properties"]["summary"]["additionalProperties"] is False
    assert schema["$defs"]["diagnostic"]["additionalProperties"] is False
    action_kinds = {
        branch["properties"]["kind"]["const"] for branch in schema["$defs"]["safeAction"]["oneOf"]
    }
    assert action_kinds == {
        "clear_shot_camera", "clear_global_camera", "activate_resource", "add_binding",
        "align_transition_from_state",
    }


def test_collector_rejects_unstructured_messages_as_internal_api():
    collector = DiagnosticCollector()
    with pytest.raises(TypeError, match="Diagnostic instances"):
        collector.add("media_manifest is invalid")
    with pytest.raises(TypeError, match="DiagnosticCode"):
        collector.emit("schema.media_manifest.invalid_json", "message", OUTPUT_LOCATION)
