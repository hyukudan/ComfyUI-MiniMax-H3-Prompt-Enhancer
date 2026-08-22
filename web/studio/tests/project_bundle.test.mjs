import test from "node:test";
import assert from "node:assert/strict";

import {
    appendProjectBundleGenerations, applyDocumentTransaction, createProjectBundle, parseProjectBundle,
    PROJECT_BUNDLE_FORMAT, summarizeProjectBundle,
} from "../project_bundle.js";

test("append generations remaps collisions and preserves compatible shared resources", () => {
    const shared = { id: "hero", name: "Hero", appearances: [] };
    const result = appendProjectBundleGenerations({
        shotPlan: { schemaVersion: 2, timingMode: "auto", shots: [{ id: "s1", generationId: "g1", action: "Hero exits." }] },
        mediaProject: {
            schemaVersion: 2, mode: "single", assets: [], subjects: [shared], environments: [],
            generations: [{ id: "g1", order: 1, bindings: [], subjectStates: [], environmentStates: [] }],
        },
    }, {
        shotPlan: { schemaVersion: 2, timingMode: "auto", shots: [{ id: "s1", generationId: "g1", action: "Hero enters." }] },
        mediaProject: {
            schemaVersion: 2, mode: "single", assets: [], subjects: [shared], environments: [],
            generations: [{ id: "g1", order: 1, bindings: [], subjectStates: [], environmentStates: [] }],
        },
    });
    assert.equal(result.ok, true);
    assert.equal(result.documents.mediaProject.mode, "chained_multishot");
    assert.deepEqual(result.documents.mediaProject.generations.map(({ id, order }) => [id, order]), [["g1", 1], ["g2", 2]]);
    assert.deepEqual(result.documents.shotPlan.shots.map(({ id, generationId }) => [id, generationId]), [["s1", "g1"], ["s2", "g2"]]);
    assert.equal(result.documents.mediaProject.subjects.length, 1);
});

test("append generations rejects empty packages and conflicting shared definitions", () => {
    const current = {
        shotPlan: { schemaVersion: 2, timingMode: "auto", shots: [] },
        mediaProject: { schemaVersion: 2, assets: [], subjects: [{ id: "hero", name: "Old" }], environments: [], generations: [] },
    };
    assert.match(appendProjectBundleGenerations({
        shotPlan: { schemaVersion: 2, timingMode: "auto", shots: [] },
        mediaProject: { schemaVersion: 2, assets: [], subjects: [], environments: [], generations: [] },
    }, current).message, /no generations/);
    assert.match(appendProjectBundleGenerations({
        shotPlan: { schemaVersion: 2, timingMode: "auto", shots: [] },
        mediaProject: {
            schemaVersion: 2, assets: [], subjects: [{ id: "hero", name: "Changed" }], environments: [],
            generations: [{ id: "g1", bindings: [], subjectStates: [], environmentStates: [] }],
        },
    }, current).message, /different data/);
});

test("project transfer includes only native v2 structured documents", () => {
    const bundle = createProjectBundle({
        shotPlan: { kind: "v2", value: { schemaVersion: 2, shots: [] } },
        mediaProject: { kind: "blank", value: null },
        creativeTreatment: { kind: "v1", value: { schemaVersion: 1 } },
        cinematography: { kind: "v2", value: { schemaVersion: 2, shotScale: "none" } },
    });
    assert.equal(bundle.format, PROJECT_BUNDLE_FORMAT);
    assert.deepEqual(Object.keys(bundle.documents), ["shotPlan", "cinematography"]);
    assert.equal(parseProjectBundle(JSON.stringify(bundle)).ok, true);
});

test("project transfer deeply validates nested document contracts", () => {
    const base = { format: PROJECT_BUNDLE_FORMAT, formatVersion: 1 };
    assert.match(parseProjectBundle({ ...base, documents: { shotPlan: { schemaVersion: 2, timingMode: "auto", shots: "no" } } }).message, /shots must be an array/);
    assert.match(parseProjectBundle({ ...base, documents: { mediaProject: { schemaVersion: 2, assets: [], subjects: [], environments: [], generations: [{ id: "g1" }] } } }).message, /bindings must be an array/);
    assert.match(parseProjectBundle({ ...base, documents: { creativeTreatment: { schemaVersion: 2, tone: 42 } } }).message, /tone must be a string/);
});

test("project transfer preview reports replacement scope without mutating", () => {
    const rows = summarizeProjectBundle({
        shotPlan: { schemaVersion: 2, timingMode: "auto", shots: [] },
        mediaProject: { schemaVersion: 2, assets: [], subjects: [], environments: [], generations: [] },
    }, { shotPlan: { schemaVersion: 2, timingMode: "auto", shots: [] } });
    assert.deepEqual(rows.map(({ change, detail }) => [change, detail]), [["Unchanged", "0 shots"], ["Replace", "0 media · 0 subjects · 0 environments · 0 generations"]]);
});

test("document transaction restores exact snapshots when a handler fails", () => {
    const state = { shotPlan: "old-shot", mediaProject: "old-media", cinematography: "old-camera" };
    const result = applyDocumentTransaction([
        ["shotPlan", "new-shot"], ["mediaProject", "new-media"], ["cinematography", "new-camera"],
    ], {
        read: (key) => state[key],
        write: (key, value, options) => {
            if (key === "cinematography" && !options?.rollback) return false;
            state[key] = value; return true;
        },
    });
    assert.equal(result.ok, false);
    assert.equal(result.rolledBack, true);
    assert.deepEqual(state, { shotPlan: "old-shot", mediaProject: "old-media", cinematography: "old-camera" });
});

test("project transfer validates every document before any import is possible", () => {
    const wrongVersion = {
        format: PROJECT_BUNDLE_FORMAT,
        formatVersion: 1,
        documents: { shotPlan: { schemaVersion: 1, shots: [] } },
    };
    assert.deepEqual(parseProjectBundle("not json"), { ok: false, message: "This is not valid JSON." });
    assert.match(parseProjectBundle(wrongVersion).message, /schema v2/);
    assert.equal(parseProjectBundle({ ...wrongVersion, format: "something-else" }).ok, false);
    assert.equal(parseProjectBundle({ format: PROJECT_BUNDLE_FORMAT, formatVersion: 1, documents: {} }).ok, false);
});
