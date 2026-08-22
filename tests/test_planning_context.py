# SPDX-License-Identifier: GPL-3.0-only

from planning_context import compile_planning_context, planning_context_for_generation


def _media_project():
    return {
        "schemaVersion": 2,
        "mode": "chained_multishot",
        "assets": [
            {"id": "ana.identity", "type": "picture", "name": "Ana identity"},
            {"id": "ana.wounded", "type": "picture", "name": "Ana wounded"},
            {"id": "bridge.overview", "type": "picture", "name": "Bridge overview"},
            {"id": "bridge.detail", "type": "picture", "name": "Bridge detail"},
            {"id": "unused", "type": "picture", "name": "Unused secret reference"},
            {
                "id": "camera.reference", "type": "video", "name": "Camera path",
                "durationSeconds": 6, "audioMode": "off",
                "cameraTransfer": {"enabled": True, "role": "camera_reference", "aspects": ["motion"]},
            },
        ],
        "subjects": [{
            "id": "ana", "h3Index": 1, "name": "Ana",
            "description": "Adult woman with short dark hair.",
            "identityAssetIds": ["ana.identity"], "baseAppearanceStateId": "base",
            "appearanceStates": [
                {"id": "base", "name": "Base", "controls": ["wardrobe"], "attributes": {"wardrobe": "red coat"}},
                {
                    "id": "wounded", "name": "Wounded", "extends": "base",
                    "controls": ["damage"], "attributes": {"damage": "bandaged arm"},
                    "source": {"mode": "asset", "assetId": "ana.wounded"},
                },
            ],
        }],
        "environments": [{
            "id": "bridge", "name": "Bridge", "permanent": {"architecture": "riveted iron bridge"},
            "views": [
                {"id": "overview", "name": "Overview", "role": "overview", "assetId": "bridge.overview"},
                {"id": "railing", "name": "Railing", "role": "detail", "assetId": "bridge.detail"},
            ],
            "defaultStateId": "day",
            "states": [
                {"id": "day", "name": "Day", "temporary": {"lighting": "overcast daylight"}},
                {"id": "rain", "name": "Rain", "extends": "day", "temporary": {"weather": "heavy rain"}},
            ],
        }],
        "generations": [
            {
                "id": "g1", "order": 1, "activation": {"mode": "auto"},
                "bindings": [
                    {"assetId": "ana.identity", "slotIndex": 1},
                    {"assetId": "bridge.overview", "slotIndex": 2},
                    {"assetId": "camera.reference", "slotIndex": 1},
                ],
                "subjectStates": [{"subjectId": "ana", "policy": "explicit", "stateId": "base"}],
                "environmentStates": [{"environmentId": "bridge", "policy": "explicit", "stateId": "day", "viewIds": ["overview"]}],
            },
            {
                "id": "g2", "order": 2,
                "activation": {"mode": "explicit", "roots": [{"kind": "subject", "id": "ana"}, {"kind": "environment", "id": "bridge"}]},
                "bindings": [
                    {"assetId": "ana.identity", "slotIndex": 1},
                    {"assetId": "ana.wounded", "slotIndex": 2},
                    {"assetId": "bridge.detail", "slotIndex": 3},
                ],
                "subjectStates": [{"subjectId": "ana", "policy": "carry"}],
                "environmentStates": [{"environmentId": "bridge", "policy": "carry", "viewIds": ["railing"]}],
            },
        ],
    }


def _shot_plan():
    return {
        "schemaVersion": 2, "timingMode": "auto", "shots": [
            {
                "id": "s1", "generationId": "g1", "action": "Ana crosses the bridge.",
                "subjectPresenceComplete": True,
                "subjects": [{"subjectId": "ana", "presence": "present"}],
                "environment": {"environmentId": "bridge", "viewIds": ["overview"]},
                "referenceUses": [{"assetId": "camera.reference", "role": "camera_transfer", "cameraAspects": ["motion"]}],
                "cameraStart": {"framing": "wide", "primaryTarget": {"kind": "subject", "id": "ana"}},
            },
            {
                "id": "s2", "generationId": "g2", "action": "Rain begins as Ana wraps her arm.",
                "subjectPresenceComplete": True,
                "subjects": [{"subjectId": "ana", "presence": "present"}],
                "environment": {"environmentId": "bridge", "viewIds": ["railing"]},
                "appearanceTransitions": [{
                    "subjectId": "ana", "fromStateId": "base", "toStateId": "wounded",
                    "timing": "during_shot", "trigger": "Ana wraps her arm.",
                }],
                "environmentTransitions": [{
                    "environmentId": "bridge", "fromStateId": "day", "toStateId": "rain",
                    "timing": "during_shot", "trigger": "Rain begins.",
                }],
            },
        ],
    }


def test_compiler_derives_exact_generation_closures_contexts_states_and_camera():
    compiled = compile_planning_context(_media_project(), _shot_plan(), 8, mode="chained_multishot")
    assert compiled["valid"], compiled["diagnosticReport"]
    assert compiled["planningSummary"] == {
        "generationCount": 2, "shotCount": 2, "activeAssetCount": 6,
        "subjectCount": 1, "environmentCount": 1, "diagnosticCount": 0,
    }
    assert compiled["generations"]["g1"]["activeAssetIds"] == [
        "ana.identity", "bridge.overview", "camera.reference",
    ]
    assert compiled["generations"]["g2"]["activeAssetIds"] == [
        "ana.identity", "ana.wounded", "bridge.detail",
    ]
    assert compiled["generations"]["g2"]["finalState"]["subjects"]["ana"] == "wounded"
    assert compiled["generations"]["g2"]["finalState"]["environments"]["bridge"] == "rain"
    assert compiled["cameraAuthority"]["valid"]
    assert any(owner["claim"]["sourceKind"] == "video_reference" for owner in compiled["cameraAuthority"]["owners"])
    context = planning_context_for_generation(compiled, "g2")
    assert context.count("bandaged arm") == 1
    assert "Appearance ana.wounded" in context
    assert "Unused secret reference" not in context
    assert len(compiled["digest"]) == len(compiled["authorityDigest"]) == 64


def test_compiler_digest_and_context_are_deterministic():
    first = compile_planning_context(_media_project(), _shot_plan(), 8, mode="chained_multishot")
    second = compile_planning_context(_media_project(), _shot_plan(), 8, mode="chained_multishot")
    assert first["digest"] == second["digest"]
    assert first["diagnosticsDigest"] == second["diagnosticsDigest"]
    assert first["generations"]["g2"]["context"] == second["generations"]["g2"]["context"]


def test_complete_presence_requires_every_generation_subject_even_when_absent():
    plan = _shot_plan()
    plan["shots"][1]["subjects"] = []
    compiled = compile_planning_context(_media_project(), plan, 8, mode="chained_multishot")
    assert not compiled["valid"]
    assert any("complete subject presence" in item["message"] for item in compiled["diagnosticReport"]["diagnostics"])


def test_transition_from_state_absence_and_inactive_environment_are_hard_errors():
    plan = _shot_plan()
    shot = plan["shots"][1]
    shot["subjects"][0]["presence"] = "absent"
    shot["appearanceTransitions"][0]["fromStateId"] = "wounded"
    shot["appearanceTransitions"][0]["toStateId"] = "base"
    shot.pop("environment")
    compiled = compile_planning_context(_media_project(), plan, 8, mode="chained_multishot")
    codes = {item["code"] for item in compiled["diagnosticReport"]["diagnostics"]}
    assert "appearance.transition.from_mismatch" in codes
    assert "appearance.transition.subject_absent" in codes
    assert "environment.transition.from_mismatch" in codes
    assert not compiled["valid"]


def test_reference_and_camera_transfer_must_be_known_active_bound_and_capable():
    project = _media_project()
    project["assets"][-1]["cameraTransfer"]["aspects"] = ["framing"]
    compiled = compile_planning_context(project, _shot_plan(), 8, mode="chained_multishot")
    diagnostics = compiled["diagnosticReport"]["diagnostics"]
    assert any(item["code"] == "reference.binding.type_mismatch" and "camera transfer" in item["message"] for item in diagnostics)

    project = _media_project()
    project["generations"][0]["bindings"] = project["generations"][0]["bindings"][:-1]
    compiled = compile_planning_context(project, _shot_plan(), 8, mode="chained_multishot")
    assert any(item["code"] == "reference.binding.missing" for item in compiled["diagnosticReport"]["diagnostics"])


def test_targets_must_exist_and_be_active_in_the_shot():
    plan = _shot_plan()
    plan["shots"][0]["cameraStart"]["primaryTarget"] = {"kind": "asset", "id": "unused"}
    compiled = compile_planning_context(_media_project(), plan, 8, mode="chained_multishot")
    # A target is a derived root, so it becomes active only if physically bound. The unbound
    # target therefore fails both closure and target-use checks without bleeding its definition.
    assert not compiled["valid"]
    assert any("unused" in item["message"] for item in compiled["diagnosticReport"]["diagnostics"])
    assert "Unused secret reference" not in compiled["generations"]["g1"]["context"]


def test_carry_uses_previous_generation_final_state_not_previous_initial_state():
    project = _media_project()
    project["generations"][0]["bindings"].insert(1, {"assetId": "ana.wounded", "slotIndex": 3})
    plan = _shot_plan()
    plan["shots"][0]["appearanceTransitions"] = [{
        "subjectId": "ana", "fromStateId": "base", "toStateId": "wounded", "timing": "at_end",
    }]
    plan["shots"][0]["environmentTransitions"] = [{
        "environmentId": "bridge", "fromStateId": "day", "toStateId": "rain", "timing": "at_end",
    }]
    plan["shots"][1]["appearanceTransitions"] = []
    plan["shots"][1]["environmentTransitions"] = []
    compiled = compile_planning_context(project, plan, 8, mode="chained_multishot")
    assert compiled["valid"], compiled["diagnosticReport"]
    initial = compiled["generations"]["g2"]["initialState"]
    assert initial["subjects"]["ana"] == "wounded"
    assert initial["environments"]["bridge"] == "rain"


def test_extra_binding_is_rejected_after_shot_derived_roots_are_known():
    project = _media_project()
    project["generations"][0]["bindings"].append({"assetId": "unused", "slotIndex": 4})
    compiled = compile_planning_context(project, _shot_plan(), 8, mode="chained_multishot")
    assert not compiled["valid"]
    assert any(
        item["data"].get("sourceCode") == "reference.binding.inactive"
        for item in compiled["diagnosticReport"]["diagnostics"]
    )


def test_schema_failures_become_typed_configuration_diagnostics():
    future_shots = {"schemaVersion": 9, "timingMode": "auto", "shots": []}
    compiled = compile_planning_context(_media_project(), future_shots, 8, mode="chained_multishot")
    assert not compiled["valid"]
    assert compiled["diagnosticReport"]["diagnostics"][0]["code"] == "schema.shot_plan.unsupported_version"

    invalid_media = _media_project()
    invalid_media["subjects"][0]["baseAppearanceStateId"] = "missing"
    compiled = compile_planning_context(invalid_media, _shot_plan(), 8, mode="chained_multishot")
    assert not compiled["valid"]
    diagnostic = compiled["diagnosticReport"]["diagnostics"][0]
    assert diagnostic["data"]["sourceCode"] == "appearance.state.unknown"
