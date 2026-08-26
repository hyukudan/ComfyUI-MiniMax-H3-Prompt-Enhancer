import assert from "node:assert/strict";
import test from "node:test";

import { insertSubjectMention } from "../../subject_mentions_model.js";

test("subject mention inserts at the caret with readable spacing", () => {
    assert.deepEqual(insertSubjectMention("Ana enters", 3, 3, "<Subject 1>"), {
        value: "Ana <Subject 1> enters", selectionStart: 15, selectionEnd: 15,
    });
});

test("subject mention replaces a selection without damaging surrounding prompt text", () => {
    assert.deepEqual(insertSubjectMention("The woman runs", 4, 9, "<Subject 2>"), {
        value: "The <Subject 2> runs", selectionStart: 15, selectionEnd: 15,
    });
});

test("subject mention chips do not accumulate the same alias repeatedly", () => {
    const result = insertSubjectMention("Ana enters as <Subject 1>", 25, 25, "<Subject 1>");
    assert.equal(result.value, "Ana enters as <Subject 1>");
    assert.equal(result.existing, true);
    assert.equal(result.selectionStart, 25);
});
