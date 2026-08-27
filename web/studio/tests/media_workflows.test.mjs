import test from "node:test";
import assert from "node:assert/strict";

import {
    bindingPlanDiagnostics, connectExistingReference, createPlanningContext, createPurposeBinding, disconnectPurposeReference, MEDIA_RECIPES, replacePurposeReference,
} from "../media_workflows.js";
import { referenceDirectorModel } from "../reference_director.js";
import { addSceneDialogueBeat, composeCameraSummary, composeConnectionInput, composeLlmHandoff, composeSceneAudio, composeVisualAssignments, composeVisualMentionLinks, connectSubjectAssetToScene, createImportedAssetDraft, createSceneEnvironmentBundle, createScenePropBundle, createSceneSubjectBundle, duplicateScene, moveScene, removeScene, removeSceneDialogueBeat, removeSceneSubjectFromShot, reorderScene, setSceneEnvironment, setScenePropPresence, setSceneSubjectPresence, shotEditorialTitle } from "../director_workspace.js";
import { ensureSubjectBindings } from "../subject_model.js";

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

test("Compose shows editorial Shot names without persistence tokens or internal IDs", () => {
    assert.equal(
        shotEditorialTitle({ id: "s1", action: "SHOT-PERSIST-240826: el faro gira" }, 0),
        "Shot 01 — el faro gira",
    );
});

test("purpose assistant creates a reusable Subject identity default without a duplicate Shot use", () => {
    const source = fixtures();
    const result = createPurposeBinding({ ...source, purposeId: "subject_identity", generationId: "g1", shotId: "s1", relationId: "subject.1", name: "Ari identity" });
    assert.equal(result.ok, true);
    assert.equal(result.project.assets[0].type, "picture");
    assert.deepEqual(result.project.subjects[0].identityAssetIds, [result.assetId]);
    assert.equal(result.shotPlan.shots[0].referenceUses, undefined);
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
    assert.equal(result.shotPlan.shots[0].referenceUses, undefined);

    result = connectExistingReference({ project: result.project, shotPlan: result.shotPlan, assetId: "voice", purposeId: "voice", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    assert.deepEqual(result.project.generations[0].bindings.at(-1), { assetId: "voice", slotIndex: 1 });
    assert.equal(result.project.subjects[0].defaultVoiceAssetId, "voice");
    assert.equal(result.shotPlan.shots[0].referenceUses, undefined);

    result = connectExistingReference({ project: result.project, shotPlan: result.shotPlan, assetId: "room", purposeId: "environment_view", generationId: "g1", shotId: "s1", relationId: "environment.1" });
    assert.equal(result.project.environments[0].views[0].assetId, "room");
    assert.deepEqual(result.shotPlan.shots[0].environment, { environmentId: "environment.1", viewIds: ["view.1"] });
    assert.deepEqual(result.shotPlan.shots[0].referenceUses, [{ assetId: "room", role: "environment_view", targetIds: ["environment.1"] }]);
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

test("removing a Subject from a Shot keeps the Library entity and clears Shot-only assignments", () => {
    const shot = {
        subjectPresenceComplete: true,
        subjects: [{ subjectId: "subject.1", presence: "present" }, { subjectId: "subject.2", presence: "present" }],
        staging: [{ subjectId: "subject.1" }, { subjectId: "subject.2" }],
        appearanceTransitions: [{ subjectId: "subject.1" }],
        scaleRelationships: [{ subjectId: "subject.1", relativeToId: "subject.2" }],
        referenceUses: [
            { assetId: "voice", role: "voice", targetIds: ["subject.1"] },
            { assetId: "group", role: "performance", targetIds: ["subject.1", "subject.2"] },
        ],
        actionBeats: [{ dialogue: { speakerId: "subject.1", text: "Stay." } }],
    };

    const result = removeSceneSubjectFromShot(shot, "subject.1");

    assert.equal(result.hadDialogue, true);
    assert.deepEqual(shot.subjects, [{ subjectId: "subject.1", presence: "absent" }, { subjectId: "subject.2", presence: "present" }]);
    assert.deepEqual(shot.staging, [{ subjectId: "subject.2" }]);
    assert.equal(shot.appearanceTransitions, undefined);
    assert.equal(shot.scaleRelationships, undefined);
    assert.deepEqual(shot.referenceUses, [{ assetId: "group", role: "performance", targetIds: ["subject.2"] }]);
    assert.equal(shot.actionBeats[0].dialogue.text, "Stay.", "authored dialogue is never silently deleted");
});

test("placing a library Subject in the Shot makes it available to Dialogue Speaker", () => {
    const project = {
        assets: [],
        subjects: [
            { id: "subject.1", h3Index: 1, name: "Ana" },
            { id: "subject.2", h3Index: 2, name: "Sergio" },
        ],
    };
    const shot = { subjects: [{ subjectId: "subject.1", presence: "present" }] };

    setSceneSubjectPresence(shot, "subject.2", true);

    assert.deepEqual(
        composeSceneAudio(project, shot).voices.map((voice) => [voice.subjectId, voice.name]),
        [["subject.1", "Ana"], ["subject.2", "Sergio"]],
    );
});

test("Compose duplicates, moves, drags and removes complete cuts without reusing IDs", () => {
    const plan = { schemaVersion: 2, timingMode: "exact", shots: [
        { id: "s1", generationId: "g1", durationSeconds: 2, action: "First", cameraPath: { motionType: "push_in" }, referenceUses: [{ assetId: "portrait", role: "continuity" }] },
        { id: "s2", generationId: "g1", durationSeconds: 3, action: "Second" },
    ] };
    const duplicated = duplicateScene(plan, "s1");
    assert.deepEqual(duplicated.plan.shots.map((shot) => shot.id), ["s1", "s3", "s2"]);
    assert.deepEqual(duplicated.plan.shots[1].cameraPath, { motionType: "push_in" });
    duplicated.plan.shots[1].referenceUses[0].role = "lighting";
    assert.equal(plan.shots[0].referenceUses[0].role, "continuity", "the duplicate must own its nested camera and reference data");
    assert.deepEqual(moveScene(plan, "s2", -1).plan.shots.map((shot) => shot.id), ["s2", "s1"]);
    assert.deepEqual(reorderScene(duplicated.plan, "s2", "s1").plan.shots.map((shot) => shot.id), ["s2", "s1", "s3"]);
    const removed = removeScene(plan, "s1");
    assert.deepEqual(removed.plan.shots.map((shot) => shot.id), ["s2"]);
    assert.equal(removed.selectedId, "s2");
    assert.equal(plan.shots.length, 2, "scene operations stay immutable until the widget commit succeeds");
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

test("Compose creates one canonical environment and assigns it to the scene atomically", () => {
    const source = fixtures();
    source.project.environments = [];
    const bundle = createSceneEnvironmentBundle(source.project, source.shotPlan, "s1", "Ana's apartment");
    assert.deepEqual(bundle.environment, {
        id: "environment.1", name: "Ana's apartment", permanent: {}, views: [], defaultStateId: "base",
        states: [{ id: "base", name: "Base", temporary: {} }],
    });
    assert.deepEqual(bundle.shotPlan.shots[0].environment, { environmentId: "environment.1", viewIds: [] });
    assert.equal(source.project.environments.length, 0);
    assert.equal(source.shotPlan.shots[0].environment, undefined);
});

test("Compose creates a reusable Prop in the shared H3 Subject namespace and adds it to one Shot", () => {
    const source = fixtures();
    source.project.subjects[0].h3Index = 1;
    const bundle = createScenePropBundle(source.project, source.shotPlan, "s1", "Car Y");
    assert.deepEqual(bundle.prop, {
        id: "prop.1", h3Index: 2, name: "Car Y", category: "object", description: "", designAssetIds: [],
    });
    assert.deepEqual(bundle.shotPlan.shots[0].props, [{ propId: "prop.1", presence: "present" }]);
    assert.equal(source.project.props, undefined);
    assert.equal(source.shotPlan.shots[0].props, undefined);
});

test("Compose resolves Prop design pictures and exposes them to the LLM as design-family Subject aliases", () => {
    const source = fixtures();
    source.project.assets = [{ id: "car", type: "picture", name: "Car Y front" }];
    source.project.props = [{ id: "prop.1", h3Index: 2, name: "Car Y", category: "vehicle", description: "red coupe", designAssetIds: ["car"] }];
    source.project.generations[0].bindings = [{ assetId: "car", slotIndex: 1 }];
    const shot = source.shotPlan.shots[0];
    setScenePropPresence(shot, "prop.1", true);
    const visual = composeVisualAssignments(source.project, shot);
    assert.deepEqual(visual.props[0].designAssets.map((asset) => asset.id), ["car"]);
    const handoff = composeLlmHandoff(source.project, source.shotPlan, shot);
    assert.deepEqual(handoff.props[0], {
        id: "prop.1", name: "Car Y", alias: "<Subject 2>", family: "design",
        links: [{ assetId: "car", name: "Car Y front", role: "Design", physicalLabel: "<Picture 1>" }],
    });
    assert.match(handoff.text, /<Subject 2> Car Y \| reusable design \| <Picture 1>/);
    assert.doesNotMatch(handoff.text, /<Object/);
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

test("Compose resolves a per-Shot look picture and binds it to the same generation", () => {
    const source = fixtures();
    source.project.assets = [
        { id: "portrait", type: "picture", name: "Ari portrait" },
        { id: "raincoat", type: "picture", name: "Ari raincoat" },
    ];
    source.project.subjects[0].identityAssetIds = ["portrait"];
    source.project.subjects[0].appearanceStates.push({
        id: "rain", name: "Rain look", extends: "base", controls: ["wardrobe"],
        attributes: { wardrobe: "yellow raincoat" }, source: { mode: "asset", assetId: "raincoat" },
    });
    source.shotPlan.shots[0].subjects = [{ subjectId: "subject.1", presence: "present", appearanceStateId: "rain" }];

    const visual = composeVisualAssignments(source.project, source.shotPlan.shots[0]);
    assert.equal(visual.subjects[0].appearanceState.name, "Rain look");
    assert.deepEqual(visual.subjects[0].appearanceAssets.map((asset) => asset.id), ["raincoat"]);
    const result = ensureSubjectBindings(source.project, source.shotPlan, "subject.1");
    assert.equal(result.ok, true);
    assert.deepEqual(source.project.generations[0].bindings.map((binding) => binding.assetId), ["portrait", "raincoat"]);
    const handoff = composeLlmHandoff(source.project, source.shotPlan, source.shotPlan.shots[0]);
    assert.ok(handoff.subjects[0].links.some((link) => link.role === "Look" && link.assetId === "raincoat"));
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

test("Compose LLM handoff derives subject and physical aliases from the same generation bindings", () => {
    const source = fixtures();
    source.project.assets = [
        { id: "portrait", type: "picture", name: "Ari portrait" },
        { id: "voice", type: "audio", name: "Ari voice" },
        { id: "room", type: "picture", name: "Room wide" },
        { id: "music", type: "audio", name: "Score" },
    ];
    source.project.subjects[0].identityAssetIds = ["portrait"];
    source.project.subjects[0].defaultVoiceAssetId = "voice";
    source.project.environments[0].views = [{ id: "view.1", name: "Wide", assetId: "room" }];
    source.project.generations[0].bindings = [
        { assetId: "portrait", slotIndex: 1 }, { assetId: "room", slotIndex: 2 },
        { assetId: "voice", slotIndex: 1 }, { assetId: "music", slotIndex: 2 },
    ];
    const shot = source.shotPlan.shots[0];
    shot.subjects = [{ subjectId: "subject.1", presence: "present" }];
    shot.environment = { environmentId: "environment.1", viewIds: ["view.1"] };
    shot.referenceUses = [{ assetId: "music", role: "soundtrack" }];
    const result = composeLlmHandoff(source.project, source.shotPlan, shot);
    assert.equal(result.subjects[0].alias, "<Subject 1>");
    assert.deepEqual(result.subjects[0].links.map((item) => [item.role, item.physicalLabel]), [["Image", "<Picture 1>"], ["Voice", "<Audio 1>"]]);
    assert.deepEqual(result.environment.links.map((item) => item.physicalLabel), ["<Picture 2>"]);
    assert.deepEqual(result.referenceUses.map((item) => [item.role, item.physicalLabel, item.target]), [["Soundtrack", "<Audio 2>", "This Shot"]]);
    assert.match(result.text, /<Subject 1> Ari \| Image <Picture 1> \| Voice <Audio 1>/);
    assert.match(result.text, /Set: Room \| <Picture 2>/);
});

test("Compose makes assigned visual references clickable without exposing audio aliases", () => {
    const links = composeVisualMentionLinks({
        environment: { links: [{ name: "Can Misses", role: "Background", physicalLabel: "<Picture 4>" }] },
        referenceUses: [
            { name: "Camera move", role: "Performance", physicalLabel: "<Video 1>" },
            { name: "Malak voice", role: "Voice", physicalLabel: "<Audio 1>" },
            { name: "Duplicate set", role: "Background", physicalLabel: "<Picture 4>" },
            { name: "Not bound", role: "Reference", physicalLabel: "Unassigned" },
        ],
    });
    assert.deepEqual(links.map((item) => [item.name, item.physicalLabel]), [
        ["Can Misses", "<Picture 4>"], ["Camera move", "<Video 1>"],
    ]);
});

test("Compose authors exact dialogue against the visible subject and keeps voice, override and soundtrack roles distinct", () => {
    const source = fixtures();
    source.project.assets = [
        { id: "voice", type: "audio", name: "Ari voice" },
        { id: "override", type: "audio", name: "Close mic" },
        { id: "music", type: "audio", name: "Score" },
    ];
    source.project.subjects[0].defaultVoiceAssetId = "voice";
    const shot = source.shotPlan.shots[0];
    shot.subjects = [{ subjectId: "subject.1", presence: "present" }];
    shot.referenceUses = [
        { assetId: "override", role: "voice", targetIds: ["subject.1"] },
        { assetId: "music", role: "soundtrack" },
    ];
    assert.equal(addSceneDialogueBeat(
        shot, "subject.1", "  We leave now.  ", "whispers", "voice_over", "calm, steady",
    ).id, "beat1");
    assert.equal(addSceneDialogueBeat(shot, "subject.1", "", "says"), null);
    const model = composeSceneAudio(source.project, shot);
    assert.deepEqual(model.voices.map((item) => [item.alias, item.asset.id]), [["<Subject 1>", "override"]]);
    assert.equal(model.voices[0].override, true);
    assert.deepEqual(
        model.dialogues.map((item) => [item.speaker, item.text, item.delivery, item.channel, item.mood]),
        [["Ari", "We leave now.", "whispers", "voice_over", "calm, steady"]],
    );
    assert.deepEqual(model.references.map((item) => item.role), ["soundtrack"]);
    assert.equal(removeSceneDialogueBeat(shot, "beat1"), true);
    assert.equal(shot.actionBeats, undefined);
});

test("visual Director refuses incompatible media before writing either document", () => {
    const source = fixtures();
    source.project.assets = [{ id: "voice", type: "audio", name: "Voice" }];
    const result = connectExistingReference({ ...source, assetId: "voice", purposeId: "subject_identity", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    assert.equal(result.ok, false);
    assert.deepEqual(result.issues, ["Subject identity requires picture media."]);
    assert.deepEqual(source.project.generations[0].bindings, []);
});

test("disconnecting a Subject default preserves an independent Shot override and its wiring", () => {
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
    assert.deepEqual(result.shotPlan.shots[0].referenceUses, [
        { assetId: "portrait", role: "identity_reinforcement", targetIds: ["subject.1"] },
        { assetId: "shared", role: "continuity" },
    ]);
    assert.deepEqual(result.project.generations[0].bindings, [{ assetId: "portrait", slotIndex: 1 }, { assetId: "shared", slotIndex: 2 }]);
    assert.equal(result.project.assets.length, 2, "disconnect must not delete reusable Library media");
    assert.deepEqual(source.project.subjects[0].identityAssetIds, ["portrait"], "disconnect must remain immutable until commit");
});

test("Compose replaces one Shot voice override without mutating the Subject default", () => {
    const source = fixtures();
    source.project.assets = [
        { id: "old-voice", type: "audio", name: "Old voice" },
        { id: "new-voice", type: "audio", name: "New voice" },
    ];
    source.project.subjects[0].defaultVoiceAssetId = "old-voice";
    source.project.generations[0].bindings = [{ assetId: "old-voice", slotIndex: 1 }];
    source.shotPlan.shots[0].referenceUses = [{ assetId: "old-voice", role: "voice", targetIds: ["subject.1"] }];
    const result = replacePurposeReference({ ...source, assetId: "new-voice", purposeId: "voice_override", generationId: "g1", shotId: "s1", relationId: "subject.1" });
    assert.equal(result.ok, true);
    assert.equal(result.project.subjects[0].defaultVoiceAssetId, "old-voice");
    assert.deepEqual(result.shotPlan.shots[0].referenceUses, [{ assetId: "new-voice", role: "voice", targetIds: ["subject.1"] }]);
    assert.deepEqual(result.project.generations[0].bindings, [{ assetId: "old-voice", slotIndex: 1 }, { assetId: "new-voice", slotIndex: 2 }]);
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

test("Subject defaults need no Shot while an Environment view is selected by a Shot", () => {
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
    const withoutShot = connectExistingReference({ project: result.project, shotPlan: result.shotPlan, assetId: "room", purposeId: "environment_view", generationId: "g1", relationId: "environment.1" });
    assert.equal(withoutShot.ok, false);
    result.shotPlan.shots.push({ id: "s1", generationId: "g1", action: "Ari enters.", environment: { environmentId: "environment.1", viewIds: [] } });
    const withShot = connectExistingReference({ project: result.project, shotPlan: result.shotPlan, assetId: "room", purposeId: "environment_view", generationId: "g1", shotId: "s1", relationId: "environment.1" });
    assert.equal(withShot.ok, true);
    assert.equal(withShot.project.environments[0].views[0].assetId, "room");
    assert.equal(withShot.shotPlan.shots[0].referenceUses[0].role, "environment_view");
    assert.deepEqual(withShot.shotPlan.shots[0].environment.viewIds, ["view.1"]);
    const detached = disconnectPurposeReference({ project: withShot.project, shotPlan: withShot.shotPlan, purposeId: "environment_view", generationId: "g1", shotId: "s1", relationId: "environment.1" });
    assert.equal(detached.ok, true);
    assert.equal(detached.project.environments[0].views[0].assetId, "room", "detaching one Shot must preserve the reusable Environment gallery");
    assert.equal(detached.shotPlan.shots[0].referenceUses, undefined);
    assert.deepEqual(detached.shotPlan.shots[0].environment, { environmentId: "environment.1", viewIds: [] });
});

test("dropping a reference on an absent Subject places it and assigns the semantic role atomically", () => {
    const source = fixtures();
    source.shotPlan.shots[0].subjects = [];
    source.project.assets = [{ id: "portrait", type: "picture", name: "Ari portrait" }];
    const result = connectSubjectAssetToScene(source.project, source.shotPlan, "s1", "portrait", "subject.1");
    assert.equal(result.ok, true);
    assert.deepEqual(result.shotPlan.shots[0].subjects, [{ subjectId: "subject.1", presence: "present" }]);
    assert.deepEqual(result.project.subjects[0].identityAssetIds, ["portrait"]);
    assert.deepEqual(result.project.generations[0].bindings, [{ assetId: "portrait", slotIndex: 1 }]);
    assert.deepEqual(source.shotPlan.shots[0].subjects, [], "drop remains atomic and immutable before commit");
});

test("an identity drop gives a still-placeholder Subject the useful asset name", () => {
    const source = fixtures();
    source.project.subjects[0].name = "New subject";
    source.project.assets = [{ id: "portrait", type: "picture", name: "Malako" }];
    const result = connectSubjectAssetToScene(source.project, source.shotPlan, "s1", "portrait", "subject.1");
    assert.equal(result.ok, true);
    assert.equal(result.project.subjects[0].name, "Malako");
    assert.equal(source.project.subjects[0].name, "New subject", "rename remains immutable before commit");
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
