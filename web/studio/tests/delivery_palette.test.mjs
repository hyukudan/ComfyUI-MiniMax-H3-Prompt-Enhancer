// SPDX-License-Identifier: GPL-3.0-only
import assert from "node:assert/strict";
import test from "node:test";

import {
    deliveryStatus,
    hasQuotedDialogue,
    insertDeliveryToken,
    rovingIndex,
} from "../../delivery_palette_model.js";

test("delivery insertion preserves a selected line and moves the selection", () => {
    const source = 'Detective says "You knew."';
    const start = source.indexOf('"');
    const end = source.length;
    const result = insertDeliveryToken(source, start, end, "🤫");
    assert.equal(result.value, 'Detective says 🤫 "You knew."');
    assert.equal(result.value.slice(result.selectionStart, result.selectionEnd), source.slice(start, end));
});

test("delivery insertion keeps exact tokens and sensible padding at a caret", () => {
    assert.equal(insertDeliveryToken("She says", 8, 8, "💬").value, "She says 💬");
    assert.equal(insertDeliveryToken('"Hello"', 0, 0, "🥰").value, '🥰 "Hello"');
});

test("quoted dialogue recognizes straight, curly and H3 dialogue forms", () => {
    assert.equal(hasQuotedDialogue('She says "Hello".'), true);
    assert.equal(hasQuotedDialogue("She says “Hello”."), true);
    assert.equal(hasQuotedDialogue("<d>[English] Hello</d>"), true);
    assert.equal(hasQuotedDialogue("She says Hello."), false);
});

test("orphan marks warn without blocking and quoted marks confirm prose resolution", () => {
    const tokens = ["🤫"];
    assert.deepEqual(deliveryStatus("She whispers 🤫 hello", tokens, "added"), {
        kind: "warning",
        text: "Marks apply to quoted dialogue. Add the line in quotes or the mark will be dropped.",
    });
    assert.deepEqual(deliveryStatus('She whispers 🤫 "hello"', tokens, "written as prose"), {
        kind: "info",
        text: "written as prose",
    });
});

test("roving focus supports toolbar and two-column grid navigation", () => {
    assert.equal(rovingIndex(0, "ArrowLeft", 5), 4);
    assert.equal(rovingIndex(4, "ArrowRight", 5), 0);
    assert.equal(rovingIndex(3, "Home", 5), 0);
    assert.equal(rovingIndex(1, "End", 5), 4);
    assert.equal(rovingIndex(1, "ArrowDown", 6, 2), 3);
    assert.equal(rovingIndex(1, "ArrowUp", 6, 2), 5);
});
