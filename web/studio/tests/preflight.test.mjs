import test from "node:test";
import assert from "node:assert/strict";

import { actionBeatIssues, localPreflight } from "../preflight.js";

function documentState(value) {
    return { kind: "v2", value };
}

test("local preflight accepts a bound reference and ordered camera playback", () => {
    const result = localPreflight({
        shotDocument: documentState({ shots: [{
            id: "s1", generationId: "g1", action: "Ana crosses the room.",
            referenceUses: [{ assetId: "portrait" }],
            cameraPath: { waypoints: [{ at: 0 }, { at: .4 }, { at: 1 }] },
        }] }),
        projectDocument: documentState({
            subjects: [], assets: [{ id: "portrait", name: "Ana portrait", type: "image" }],
            generations: [{ id: "g1", order: 1, bindings: [{ assetId: "portrait", slotIndex: 1 }] }],
        }),
    });
    assert.equal(result.status, "ready");
    assert.equal(result.items.length, 0);
});

test("local preflight routes actionable shot, media and camera problems", () => {
    const result = localPreflight({
        shotDocument: documentState({ shots: [{
            id: "s1", generationId: "missing", action: " ",
            referenceUses: [{ assetId: "portrait" }],
            cameraPath: { waypoints: [{ at: 0 }, { at: 0 }] },
        }] }),
        projectDocument: documentState({
            assets: [{ id: "portrait", name: "Ana portrait", type: "image" }],
            generations: [{ id: "g1", order: 1, bindings: [] }],
        }),
    });
    assert.equal(result.status, "blocked");
    assert.deepEqual(new Set(result.items.map((item) => item.section)), new Set(["shots", "camera"]));
    assert.ok(result.errors >= 3);
});

test("complete presence and empty beats are non-blocking local notes", () => {
    const result = localPreflight({
        shotDocument: documentState({ shots: [{
            id: "s1", generationId: "g1", action: "Ana waits.", subjectPresenceComplete: true,
            subjects: [], actionBeats: [{}],
        }] }),
        projectDocument: documentState({
            subjects: [{ id: "ana", description: "Adult woman with short dark hair." }], assets: [], generations: [{ id: "g1", bindings: [] }],
        }),
    });
    assert.equal(result.status, "attention");
    assert.equal(result.errors, 0);
    assert.equal(result.warnings, 2);
});

test("dialogue-only beats read the structured dialogue text", () => {
    const result = localPreflight({
        shotDocument: documentState({ shots: [{
            id: "s1", generationId: "g1", action: "Ana listens.",
            actionBeats: [{ dialogue: { text: "We leave now.", delivery: "whispers" } }],
        }] }),
        projectDocument: documentState({
            subjects: [], assets: [], generations: [{ id: "g1", bindings: [] }],
        }),
    });
    assert.equal(result.status, "ready");
    assert.equal(result.items.some((item) => item.message.includes("action beat is empty")), false);
});

test("unfinished identity, dialogue and custom scale drafts are explicit blocking items", () => {
    const result = localPreflight({
        shotDocument: documentState({ shots: [{
            id: "s1", generationId: "g1", action: "Ana waits.",
            actionBeats: [{ action: "Ana looks up.", dialogue: { text: "", delivery: "says" } }],
            scaleRelationships: [{ relation: "custom", subjectId: "ana", relativeToId: "bea" }],
        }] }),
        projectDocument: documentState({
            subjects: [{ id: "ana", description: "Describe the stable identity." }],
            assets: [], generations: [{ id: "g1", bindings: [] }],
        }),
    });
    assert.equal(result.status, "blocked");
    assert.ok(result.items.some(({ section, message }) => section === "subjects" && message.includes("stable identity")));
    assert.ok(result.items.some(({ message }) => message.includes("exact spoken words")));
    assert.ok(result.items.some(({ message }) => message.includes("custom visible scale")));
});

test("malformed and future sources are blocking without reading their values", () => {
    const result = localPreflight({
        shotDocument: { kind: "future", value: { shots: [{ action: "ignored" }] } },
        projectDocument: { kind: "malformed", value: null },
    });
    assert.equal(result.errors, 2);
    assert.equal(result.status, "blocked");
});

test("timed action spans expose overlaps, gaps and an honest speech-rate estimate", () => {
    const issues = actionBeatIssues({
        id: "s1", durationSeconds: 10,
        actionBeats: [
            { at: 0, endAt: .4, action: "First action." },
            { at: .3, endAt: .45, dialogue: { text: "one two three four five six seven eight nine ten" } },
            { at: .7, endAt: .9, action: "Final action." },
        ],
    });
    assert.ok(issues.some(({ message }) => message.includes("overlaps")));
    assert.ok(issues.some(({ message }) => message.includes("150 wpm")));
    assert.ok(issues.some(({ message }) => message.includes("25% gap")));
});

test("voice ownership without authored dialogue is visible before generation", () => {
    const result = localPreflight({
        shotDocument: documentState({ shots: [{
            id: "s1", generationId: "g1", action: "Ana listens.",
            referenceUses: [{ assetId: "voice", role: "voice" }],
        }] }),
        projectDocument: documentState({
            subjects: [], assets: [{ id: "voice", name: "Voice", type: "audio" }],
            generations: [{ id: "g1", bindings: [{ assetId: "voice", slotIndex: 1 }] }],
        }),
    });
    assert.ok(result.items.some(({ message }) => message.includes("no authored dialogue beat")));
});
