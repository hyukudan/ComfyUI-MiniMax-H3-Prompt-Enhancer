import test from "node:test";
import assert from "node:assert/strict";

import { createProjectBundle, parseProjectBundle, PROJECT_BUNDLE_FORMAT } from "../project_bundle.js";

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
