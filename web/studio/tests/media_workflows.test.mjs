import test from "node:test";
import assert from "node:assert/strict";

import {
    bindingPlanDiagnostics, createPlanningContext, createPurposeBinding, MEDIA_RECIPES,
} from "../media_workflows.js";

function fixtures() {
    return {
        project: {
            schemaVersion: 2, mode: "ref2va", assets: [],
            subjects: [{ id: "subject.1", h3Index: 1, name: "Ari", description: "", identityAssetIds: [], baseAppearanceStateId: "base", appearanceStates: [{ id: "base", name: "Base", controls: [] }] }],
            environments: [{ id: "environment.1", name: "Room", permanent: {}, views: [], defaultStateId: "base", states: [{ id: "base", name: "Base" }] }],
            generations: [{ id: "g1", order: 1, activation: { mode: "auto" }, bindings: [], subjectStates: [], environmentStates: [] }],
        },
        shotPlan: { schemaVersion: 2, timingMode: "auto", shots: [{ id: "s1", generationId: "g1", action: "Ari turns." }] },
    };
}

test("purpose assistant creates identity asset, relation, shot use and binding together", () => {
    const source = fixtures();
    const result = createPurposeBinding({ ...source, purposeId: "subject_identity", generationId: "g1", shotId: "s1", relationId: "subject.1", name: "Ari identity" });
    assert.equal(result.ok, true);
    assert.equal(result.project.assets[0].type, "picture");
    assert.deepEqual(result.project.subjects[0].identityAssetIds, [result.assetId]);
    assert.deepEqual(result.shotPlan.shots[0].referenceUses, [{ assetId: result.assetId, role: "identity_reinforcement" }]);
    assert.deepEqual(result.project.generations[0].bindings, [{ assetId: result.assetId, slotIndex: 1 }]);
    assert.equal(source.project.assets.length, 0, "planning must not mutate before atomic commit");
});

test("camera and environment purposes use existing v2 contract fields", () => {
    const camera = createPurposeBinding({ ...fixtures(), purposeId: "camera", generationId: "g1", shotId: "s1", name: "Move" });
    assert.deepEqual(camera.project.assets[0].cameraTransfer, { enabled: true, role: "camera_reference", aspects: ["motion"] });
    assert.deepEqual(camera.shotPlan.shots[0].referenceUses[0].cameraAspects, ["motion"]);
    const environment = createPurposeBinding({ ...fixtures(), purposeId: "environment_view", generationId: "g1", shotId: "s1", relationId: "environment.1", name: "Room wide" });
    assert.equal(environment.project.environments[0].views[0].assetId, environment.assetId);
    assert.equal(environment.shotPlan.shots[0].referenceUses[0].role, "environment_view");
});

test("recipe prerequisites produce deterministic no-write diagnostics", () => {
    const source = fixtures();
    const missingShot = bindingPlanDiagnostics({ ...source, purposeId: "performance", generationId: "g1", shotId: "missing" });
    assert.deepEqual(missingShot, ["Choose an existing shot."]);
    const wrongGeneration = structuredClone(source);
    wrongGeneration.project.generations.push({ id: "g2", order: 2, activation: { mode: "auto" }, bindings: [], subjectStates: [], environmentStates: [] });
    assert.deepEqual(bindingPlanDiagnostics({ ...wrongGeneration, purposeId: "voice", generationId: "g2", shotId: "s1" }), ["The selected shot belongs to a different generation."]);
    assert.deepEqual(MEDIA_RECIPES.map((item) => item.id), ["targeted_edit", "relight", "performance_transfer", "continuation"]);
});

test("LLM planning context is versioned, read-only and never an import envelope", () => {
    const source = fixtures();
    const context = createPlanningContext({
        projectDocument: { kind: "v2", value: source.project },
        shotDocument: { kind: "v2", value: source.shotPlan },
    });
    assert.equal(context.format, "minimax-h3-planning-context");
    assert.equal(context.formatVersion, 1);
    assert.equal(context.readOnly, true);
    assert.match(context.purpose, /not an import package/);
    assert.equal(context.documents.mediaProject.schemaVersion, 2);
    assert.equal("physicalFiles" in context, false);
});
