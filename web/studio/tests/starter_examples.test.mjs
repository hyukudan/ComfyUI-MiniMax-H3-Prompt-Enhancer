import test from "node:test";
import assert from "node:assert/strict";

import { applyStarterExample, STARTER_EXAMPLES } from "../starter_examples.js";

test("starter examples are small native v2 structures without external assets", () => {
    assert.equal(new Set(STARTER_EXAMPLES.map((example) => example.id)).size, STARTER_EXAMPLES.length);
    for (const example of STARTER_EXAMPLES) {
        assert.equal(example.shotPlan.schemaVersion, 2);
        assert.ok(example.shotPlan.shots.length >= 1 && example.shotPlan.shots.length <= 2);
        if (example.mediaProject) assert.equal(example.mediaProject.schemaVersion, 2);
        assert.doesNotMatch(JSON.stringify(example), /https?:|disney|pixar|ghibli|cartoon network/i);
    }
});

test("starter examples write only their declared v2 documents", () => {
    const writes = [];
    const controller = {
        replaceShotRaw: (raw) => { writes.push(["shot", JSON.parse(raw)]); return true; },
        replaceProjectRaw: (raw) => { writes.push(["project", JSON.parse(raw)]); return true; },
    };
    assert.equal(applyStarterExample(controller, STARTER_EXAMPLES[0]), true);
    assert.deepEqual(writes.map(([kind]) => kind), ["shot"]);
    writes.length = 0;
    assert.equal(applyStarterExample(controller, STARTER_EXAMPLES.at(-1)), true);
    assert.deepEqual(writes.map(([kind]) => kind), ["shot", "project"]);
    assert.equal(writes[1][1].generations[0].bindings[0].slotIndex, 1);
});
