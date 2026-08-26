import test from "node:test";
import assert from "node:assert/strict";

import {
    bindingPlanDiagnostics, connectExistingReference, createPlanningContext, createPurposeBinding, disconnectPurposeReference, MEDIA_RECIPES, replacePurposeReference,
} from "../media_workflows.js";
import { referenceDirectorModel } from "../reference_director.js";
import { composeCameraSummary, composeConnectionInput, composeVisualAssignments, createImportedAssetDraft, createSceneSubjectBundle, setSceneEnvironment, setSceneSubjectPresence } from "../director_workspace.js";

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
    assert.deepEqual(result.shotPlan.shots[0].referenceUses, [{ assetId: result.assetId, role: "identity_reinforcement", targetIds: ["subject.1"] }]);
    assert.deepEqual(result.project.generations[0].bindings, [{ assetId: result.assetId, slotIndex: 1 }]);
    assert.equal(source.project.assets.length, 0, "planning must not mutate before atomic commit");
});

test("visual Director connects existing picture, voice and background assets without positional labels", () => {
    const source = fixtures();
    source.project.assets = [
        { id: "portrait", type: "picture", name: "Ari portrait" },
        { id: "voice", type: "audio", name: "Ari voice" },
        { id: "room", type: "picture", name: "Room view" },
    ];
    let result = connectExistingReference({ ...source, assetId: "portrait", purposeId: "subject_identity", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    assert.equal(result.ok, true);
    assert.deepEqual(result.project.subjects[0].identityAssetIds, ["portrait"]);
    assert.deepEqual(result.project.generations[0].bindings, [{ assetId: "portrait", slotIndex: 1 }]);
    assert.deepEqual(result.shotPlan.shots[0].referenceUses[0], { assetId: "portrait", role: "identity_reinforcement", targetIds: ["subject.1"] });

    result = connectExistingReference({ project: result.project, shotPlan: result.shotPlan, assetId: "voice", purposeId: "voice", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    assert.deepEqual(result.project.generations[0].bindings.at(-1), { assetId: "voice", slotIndex: 1 });
    assert.deepEqual(result.shotPlan.shots[0].referenceUses.at(-1), { assetId: "voice", role: "voice", targetIds: ["subject.1"] });

    result = connectExistingReference({ project: result.project, shotPlan: result.shotPlan, assetId: "room", purposeId: "environment_view", generationId: "g1", shotId: "s1", relationId: "environment.1" });
    assert.equal(result.project.environments[0].views[0].assetId, "room");
    assert.deepEqual(result.project.generations[0].bindings.map((binding) => [binding.assetId, binding.slotIndex]), [["portrait", 1], ["voice", 1], ["room", 2]]);
    assert.equal(JSON.stringify(result).includes("<Picture"), false, "visual links store meaning and never hard-code physical labels");
    assert.equal(source.project.generations[0].bindings.length, 0, "the visual operation is atomic and immutable");
});

test("Compose drop destinations inherit the selected scene generation and semantic target", () => {
    const source = fixtures();
    const shot = source.shotPlan.shots[0];
    assert.deepEqual(composeConnectionInput(source.project, source.shotPlan, shot, "portrait", "subject_identity", "subject.1"), {
        project: source.project,
        shotPlan: source.shotPlan,
        assetId: "portrait",
        purposeId: "subject_identity",
        generationId: "g1",
        shotId: "s1",
        relationId: "subject.1",
    });
});

test("Compose cast and set controls write only canonical shot-plan fields", () => {
    const shot = { id: "s1", generationId: "g1", action: "" };
    setSceneSubjectPresence(shot, "subject.1", true);
    assert.deepEqual(shot.subjects, [{ subjectId: "subject.1", presence: "present" }]);
    setSceneEnvironment(shot, "environment.1");
    assert.deepEqual(shot.environment, { environmentId: "environment.1", viewIds: [] });
    setSceneSubjectPresence(shot, "subject.1", false);
    setSceneEnvironment(shot, "");
    assert.equal(shot.subjects, undefined);
    assert.equal(shot.environment, undefined);
});

test("Compose preserves complete presence declarations by marking removed cast absent", () => {
    const shot = { subjectPresenceComplete: true, subjects: [{ subjectId: "subject.1", presence: "present" }] };
    setSceneSubjectPresence(shot, "subject.1", false);
    assert.deepEqual(shot.subjects, [{ subjectId: "subject.1", presence: "absent" }]);
});

test("Compose creates one canonical LLM subject and places that stable ID in the scene atomically", () => {
    const source = fixtures();
    source.project.subjects = [];
    const bundle = createSceneSubjectBundle(source.project, source.shotPlan, "s1", "Ana");
    assert.deepEqual(bundle.subject, {
        id: "subject.1", h3Index: 1, name: "Ana", description: "", identityAssetIds: [], baseAppearanceStateId: "base",
        appearanceStates: [{ id: "base", name: "Base", controls: [], attributes: {} }],
    });
    assert.deepEqual(bundle.shotPlan.shots[0].subjects, [{ subjectId: "subject.1", presence: "present" }]);
    assert.equal(source.project.subjects.length, 0, "the UI proposal must not mutate before the atomic commit");
    assert.equal(source.shotPlan.shots[0].subjects, undefined);
});

test("direct target import prepares a typed immutable library asset before upload commit", () => {
    const source = fixtures();
    source.project.assets = [{ id: "asset.1", type: "picture", name: "Existing" }];
    const draft = createImportedAssetDraft(source.project, { name: "Ana voice.wav" }, "audio", "Voice reference");
    assert.deepEqual(draft.asset, { id: "asset.2", type: "audio", name: "Ana voice", available: true });
    assert.equal(source.project.assets.length, 1);
});

test("Compose resolves the visible portrait, voice, performance and selected background from canonical IDs", () => {
    const source = fixtures();
    source.project.assets = [
        { id: "portrait", type: "picture", name: "Ari portrait" },
        { id: "voice", type: "audio", name: "Ari voice" },
        { id: "performance", type: "video", name: "Ari move" },
        { id: "wide", type: "picture", name: "Room wide" },
        { id: "detail", type: "picture", name: "Room detail" },
    ];
    source.project.subjects[0].identityAssetIds = ["portrait"];
    source.project.subjects[0].defaultVoiceAssetId = "voice";
    source.project.environments[0].views = [
        { id: "view.wide", name: "Wide", assetId: "wide" },
        { id: "view.detail", name: "Detail", assetId: "detail" },
    ];
    source.shotPlan.shots[0].subjects = [{ subjectId: "subject.1", presence: "present" }];
    source.shotPlan.shots[0].environment = { environmentId: "environment.1", viewIds: ["view.detail"] };
    source.shotPlan.shots[0].referenceUses = [{ assetId: "performance", role: "performance", targetIds: ["subject.1"] }];
    const result = composeVisualAssignments(source.project, source.shotPlan.shots[0]);
    assert.deepEqual(result.backgroundAssets.map((asset) => asset.id), ["detail"]);
    assert.deepEqual(result.subjects[0].identityAssets.map((asset) => asset.id), ["portrait"]);
    assert.equal(result.subjects[0].voiceAsset.id, "voice");
    assert.deepEqual(result.subjects[0].performanceAssets.map((asset) => asset.id), ["performance"]);
});

test("Compose turns each cut's native camera fields into three visual phases", () => {
    assert.deepEqual(composeCameraSummary({
        cameraStart: { framing: "wide", angle: "eye_level" },
        cameraPath: { motionType: "push_in", amplitude: "small", speed: "slow" },
        cameraEnd: { framing: "close_up" },
    }), {
        configured: true,
        kind: "spatial",
        icon: "→",
        start: "Wide · Eye level",
        movement: "Dolly in · Small · Slow",
        end: "Close up · Eye level",
    });
    assert.equal(composeCameraSummary({}).configured, false);
    assert.equal(composeCameraSummary({}).movement, "Inherited movement");
});

test("visual Director refuses incompatible media before writing either document", () => {
    const source = fixtures();
    source.project.assets = [{ id: "voice", type: "audio", name: "Voice" }];
    const result = connectExistingReference({ ...source, assetId: "voice", purposeId: "subject_identity", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    assert.equal(result.ok, false);
    assert.deepEqual(result.issues, ["Subject identity requires picture media."]);
    assert.deepEqual(source.project.generations[0].bindings, []);
});

test("Compose disconnects one semantic target, preserves Library media and prunes only unused wiring", () => {
    const source = fixtures();
    source.project.assets = [
        { id: "portrait", type: "picture", name: "Ari portrait" },
        { id: "shared", type: "picture", name: "Shared continuity" },
    ];
    source.project.subjects[0].identityAssetIds = ["portrait"];
    source.project.generations[0].bindings = [{ assetId: "portrait", slotIndex: 1 }, { assetId: "shared", slotIndex: 2 }];
    source.shotPlan.shots[0].referenceUses = [
        { assetId: "portrait", role: "identity_reinforcement", targetIds: ["subject.1"] },
        { assetId: "shared", role: "continuity" },
    ];
    const result = disconnectPurposeReference({ ...source, purposeId: "subject_identity", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    assert.equal(result.ok, true);
    assert.deepEqual(result.project.subjects[0].identityAssetIds, []);
    assert.deepEqual(result.shotPlan.shots[0].referenceUses, [{ assetId: "shared", role: "continuity" }]);
    assert.deepEqual(result.project.generations[0].bindings, [{ assetId: "shared", slotIndex: 2 }]);
    assert.equal(result.project.assets.length, 2, "disconnect must not delete reusable Library media");
    assert.deepEqual(source.project.subjects[0].identityAssetIds, ["portrait"], "disconnect must remain immutable until commit");
});

test("Compose replaces a visual destination instead of leaving a hidden old voice use", () => {
    const source = fixtures();
    source.project.assets = [
        { id: "old-voice", type: "audio", name: "Old voice" },
        { id: "new-voice", type: "audio", name: "New voice" },
    ];
    source.project.subjects[0].defaultVoiceAssetId = "old-voice";
    source.project.generations[0].bindings = [{ assetId: "old-voice", slotIndex: 1 }];
    source.shotPlan.shots[0].referenceUses = [{ assetId: "old-voice", role: "voice", targetIds: ["subject.1"] }];
    const result = replacePurposeReference({ ...source, assetId: "new-voice", purposeId: "voice", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    assert.equal(result.ok, true);
    assert.equal(result.project.subjects[0].defaultVoiceAssetId, "new-voice");
    assert.deepEqual(result.shotPlan.shots[0].referenceUses, [{ assetId: "new-voice", role: "voice", targetIds: ["subject.1"] }]);
    assert.deepEqual(result.project.generations[0].bindings, [{ assetId: "new-voice", slotIndex: 1 }]);
    assert.deepEqual(result.project.assets.map((asset) => asset.id), ["old-voice", "new-voice"]);
});

test("visual Director presents semantic names while deriving physical H3 labels", () => {
    const source = fixtures();
    source.project.assets = [{ id: "voice", type: "audio", name: "Ari voice" }];
    const connected = connectExistingReference({ ...source, assetId: "voice", purposeId: "voice", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    const model = referenceDirectorModel(connected.project, connected.shotPlan, "g1");
    assert.equal(model.assets[0].physicalLabel, "<Audio 1>");
    assert.deepEqual(model.assets[0].connections, ["Voice · Ari"]);
    assert.equal(model.shots[0].action, "Ari turns.");
});

test("project defaults connect identity, voice and environment without requiring a shot", () => {
    const source = fixtures();
    source.shotPlan.shots = [];
    source.project.assets = [
        { id: "portrait", type: "picture", name: "Ari portrait" },
        { id: "voice", type: "audio", name: "Ari voice" },
        { id: "room", type: "picture", name: "Room" },
    ];
    let result = connectExistingReference({ ...source, assetId: "portrait", purposeId: "subject_identity", generationId: "g1", relationId: "subject.1" });
    assert.equal(result.ok, true);
    result = connectExistingReference({ project: result.project, shotPlan: result.shotPlan, assetId: "voice", purposeId: "voice", generationId: "g1", relationId: "subject.1" });
    assert.equal(result.project.subjects[0].defaultVoiceAssetId, "voice");
    result = connectExistingReference({ project: result.project, shotPlan: result.shotPlan, assetId: "room", purposeId: "environment_view", generationId: "g1", relationId: "environment.1" });
    assert.equal(result.project.environments[0].views[0].assetId, "room");
    assert.equal(result.shotPlan.shots.length, 0);
});

test("purpose assistant records an authoritative frame role in frame modes", () => {
    const source = fixtures();
    source.project.mode = "i2va";
    const result = createPurposeBinding({ ...source, purposeId: "subject_identity", generationId: "g1", shotId: "s1", relationId: "subject.1", name: "Opening" });
    assert.equal(result.project.generations[0].bindings[0].role, "first_frame");
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
    assert.deepEqual(missingShot, ["Choose an existing shot.", "Choose the subject this reference controls."]);
    const wrongGeneration = structuredClone(source);
    wrongGeneration.project.generations.push({ id: "g2", order: 2, activation: { mode: "auto" }, bindings: [], subjectStates: [], environmentStates: [] });
    assert.deepEqual(bindingPlanDiagnostics({ ...wrongGeneration, purposeId: "voice", generationId: "g2", shotId: "s1" }), ["The selected shot belongs to a different generation.", "Choose the subject this reference controls."]);
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
