import assert from "node:assert/strict";
import test from "node:test";

import {
    editableShotPlan,
    emptyMediaProjectV2,
    migrateMediaManifestV1,
    migrateShotPlanV1,
    normalizeShotPlanV2,
    parseMediaProject,
    parseStructuredJson,
} from "../schema.js";

test("first structured edit migrates a v1 shot plan to v2 without touching the source document", () => {
    const raw = '{  "schemaVersion":1,"timingMode":"exact","shots":[{"id":"s1","description":"Runs.","durationSeconds":4,"shotScale":"wide"}] }';
    const document = parseStructuredJson(raw, { supportedVersions: [1, 2] });
    const migrated = editableShotPlan(document);
    assert.equal(document.raw, raw);
    assert.equal(document.kind, "v1");
    assert.deepEqual(migrated, migrateShotPlanV1(document.value));
    assert.equal(migrated.schemaVersion, 2);
    assert.equal(migrated.shots[0].action, "Runs.");
    assert.equal(migrated.shots[0].cameraStart.framing, "wide");
});

test("camera end remains a sparse delta and an empty end is omitted", () => {
    const plan = normalizeShotPlanV2({
        schemaVersion: 2,
        timingMode: "auto",
        shots: [{ id: "s1", generationId: "g1", action: "Runs.", cameraStart: { framing: "wide" }, cameraEnd: {} }],
    });
    assert.deepEqual(plan.shots[0].cameraStart, { framing: "wide" });
    assert.equal("cameraEnd" in plan.shots[0], false);
});

test("media project parser preserves blank, legacy, malformed, v2, and future raw", () => {
    const cases = [
        [" \n", "blank"],
        ['{"items":[]}', "v1"],
        ['{"schemaVersion":2,"assets":[],"subjects":[],"environments":[],"generations":[]}', "v2"],
        ['{"schemaVersion":2', "malformed"],
        ['{ "schemaVersion":77,"future":true }', "future"],
    ];
    for (const [raw, kind] of cases) {
        const parsed = parseMediaProject(raw);
        assert.equal(parsed.kind, kind);
        assert.equal(parsed.raw, raw);
    }
});

test("blank media project starts with one neutral generation and no aesthetic defaults", () => {
    const project = emptyMediaProjectV2();
    assert.equal(project.schemaVersion, 2);
    assert.deepEqual(project.generations.map((generation) => generation.id), ["g1"]);
    assert.deepEqual(project.assets, []);
    assert.equal(JSON.stringify(project).includes("cinematic"), false);
    assert.equal(JSON.stringify(project).includes("realistic"), false);
});

test("legacy media migrates deterministically only in the editable draft", () => {
    const source = {
        items: [{ type: "picture", name: "Ana" }, { type: "video", name: "Move", audio_mode: "off", duration: 4 }],
        subjects: [{ id: 1, description: "Adult woman with short dark hair.", sources: ["<Picture 1>"] }],
    };
    const project = migrateMediaManifestV1(source);
    assert.equal(project.schemaVersion, 2);
    assert.deepEqual(project.assets.map((asset) => asset.id), ["asset.picture.1", "asset.video.1"]);
    assert.deepEqual(project.subjects[0].identityAssetIds, ["asset.picture.1"]);
    assert.deepEqual(project.generations[0].bindings.map((binding) => binding.slotIndex), [1, 1]);
});
