import assert from "node:assert/strict";
import test from "node:test";

import { importEntityAsset } from "../entity_media.js";

function project() {
    return {
        schemaVersion: 2,
        assets: [],
        subjects: [{ id: "ana", identityAssetIds: [] }],
        environments: [],
        generations: [{ id: "g1", order: 1, activation: { mode: "auto" }, bindings: [] }],
    };
}

test("inline entity import stores one physical source and attaches its logical asset atomically", async () => {
    let committed = null;
    const controller = {
        referenceDirectorDocument: () => ({
            kind: "v1",
            value: { format: "minimax-h3-reference-director", formatVersion: 1, sources: {} },
        }),
        uploadReferenceFile: async () => ({ file: "minimax_h3_reference_director/ana.png [input]", sha256: "a".repeat(64) }),
        replaceProjectBundleAtomically: (documents) => { committed = documents; return { ok: true }; },
    };
    const result = await importEntityAsset(controller, project(), { name: "ana.png", type: "image/png" }, "picture", (next, assetId) => {
        next.subjects[0].identityAssetIds.push(assetId);
    });
    assert.equal(result.ok, true);
    assert.deepEqual(committed.mediaProject.assets, [{ id: "asset.1", type: "picture", name: "ana", available: true }]);
    assert.deepEqual(committed.mediaProject.subjects[0].identityAssetIds, ["asset.1"]);
    assert.equal(committed.referenceDirector.sources["asset.1"].file, "minimax_h3_reference_director/ana.png [input]");
});

test("inline entity import rejects an incompatible file without uploading or committing", async () => {
    let calls = 0;
    const controller = {
        uploadReferenceFile: async () => { calls += 1; },
        replaceProjectBundleAtomically: () => { calls += 1; },
    };
    const result = await importEntityAsset(controller, project(), { name: "voice.wav", type: "audio/wav" }, "picture", () => {});
    assert.equal(result.ok, false);
    assert.match(result.message, /images only/);
    assert.equal(calls, 0);
});
