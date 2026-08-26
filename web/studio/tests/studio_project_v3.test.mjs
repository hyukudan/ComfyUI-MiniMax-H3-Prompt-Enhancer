import assert from "node:assert/strict";
import test from "node:test";

import {
    emptyStudioProjectV3,
    parseStudioProjectV3,
    studioProjectFromDocuments,
} from "../studio_project_v3.js";

test("Studio Project v3 is the aggregate for files, identity, voice, places, Shots and Look", () => {
    const project = studioProjectFromDocuments({
        mediaProject: {
            schemaVersion: 2, mode: "ref2va",
            assets: [
                { id: "ana.face", type: "picture", name: "Ana" },
                { id: "ana.voice", type: "audio", name: "Ana voice" },
                { id: "cliff", type: "picture", name: "Cliff" },
            ],
            subjects: [{ id: "ana", name: "Ana", identityAssetIds: ["ana.face"], defaultVoiceAssetId: "ana.voice" }],
            environments: [{ id: "coast", name: "Coast", views: [{ id: "wide", name: "Wide", assetId: "cliff" }] }],
            generations: [{ id: "g1", order: 1, activation: { mode: "explicit", roots: [{ kind: "subject", id: "ana" }] }, bindings: [{ assetId: "ana.face", slotIndex: 8 }] }],
        },
        shotPlan: {
            schemaVersion: 2, timingMode: "auto",
            shots: [{ id: "s1", generationId: "g1", action: "Ana looks out.", subjects: [{ subjectId: "ana", presence: "present" }], environment: { environmentId: "coast", viewIds: ["wide"] }, referenceUses: [{ assetId: "ana.voice", role: "voice", targetIds: ["ana"] }] }],
        },
        creativeTreatment: { schemaVersion: 2, genre: "drama" },
        cinematography: { schemaVersion: 2, colorPalette: "cool" },
        referenceDirector: { sources: { "ana.face": { file: "ana.png" } } },
    });
    assert.equal(project.schemaVersion, 3);
    assert.equal(project.subjects[0].defaultVoiceFileId, "ana.voice");
    assert.deepEqual(project.subjects[0].identityFileIds, ["ana.face"]);
    assert.equal(project.environments[0].views[0].fileId, "cliff");
    assert.deepEqual(project.shots[0].cast, [{ subjectId: "ana", presence: "present" }]);
    assert.equal(project.shots[0].referenceBindings[0].fileId, "ana.voice");
    assert.equal(project.project.look.creativeTreatment.genre, "drama");
    assert.equal(project.files[0].source.file, "ana.png");
    assert.deepEqual(project.generations[0].activation.roots, [{ kind: "subject", id: "ana" }]);
    assert.equal(project.generations[0].bindings, undefined, "v3 must derive physical slots instead of copying them");
});

test("Studio Project v3 parser preserves blank, valid, malformed and unsupported sources", () => {
    assert.equal(parseStudioProjectV3("").kind, "blank");
    assert.equal(parseStudioProjectV3(JSON.stringify(emptyStudioProjectV3())).kind, "v3");
    assert.equal(parseStudioProjectV3("{").kind, "malformed");
    assert.equal(parseStudioProjectV3('{"schemaVersion":4}').kind, "future");
});
