// SPDX-License-Identifier: GPL-3.0-only
import assert from "node:assert/strict";
import test from "node:test";

import {
    clearDeliveryMarksOnLine,
    deliveryStatus,
    editDeliveryMark,
    hasQuotedDialogue,
    insertDeliveryToken,
    rovingIndex,
    updateRecentDeliveryMarks,
} from "../../delivery_palette_model.js";

const verbs = [
    { emoji: "💬", tier: "verb" },
    { emoji: "🤫", tier: "verb" },
    { emoji: "🎙️", tier: "verb" },
];

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

test("a new Delivery verb replaces the existing verb on only the caret line", () => {
    const source = 'One 💬 "hello"\nTwo 🤫 "quiet"';
    const result = editDeliveryMark(source, 6, 6, { emoji: "🎙️", tier: "verb" }, verbs);
    assert.equal(result.action, "replaced");
    assert.equal(result.oldToken, "💬");
    assert.equal(result.value, 'One 🎙️ "hello"\nTwo 🤫 "quiet"');
});

test("Voice colors toggle on their caret line while pause remains repeatable", () => {
    const source = 'She says 🥰 "hello"';
    const removed = editDeliveryMark(source, 8, 8, { emoji: "🥰", tier: "prose" }, verbs);
    assert.equal(removed.action, "removed");
    assert.equal(removed.value, 'She says "hello"');
    const pause = editDeliveryMark('She says "hello"', 10, 10, { emoji: "⏸️", tier: "pause" }, verbs);
    assert.equal(pause.action, "added");
    assert.equal(pause.value, 'She says " ⏸️ hello"');
});

test("clear removes only known marks from the caret line", () => {
    const source = 'One 💬 🥰 "hello"\nTwo 🤫 "quiet"';
    const result = clearDeliveryMarksOnLine(source, 7, 7, ["💬", "🤫", "🥰"]);
    assert.equal(result.count, 2);
    assert.equal(result.value, 'One "hello"\nTwo 🤫 "quiet"');
});

test("Recent Voice colors dedupe, promote and cap at three", () => {
    assert.deepEqual(updateRecentDeliveryMarks(["🥰", "⚡", "😐"], "⚡"), ["⚡", "🥰", "😐"]);
    assert.deepEqual(updateRecentDeliveryMarks(["🥰", "⚡", "😐"], "😢"), ["😢", "🥰", "⚡"]);
});
