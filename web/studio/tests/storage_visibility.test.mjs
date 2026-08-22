import assert from "node:assert/strict";
import test from "node:test";

import { hideCanonicalJsonWidget } from "../storage_visibility.js";

test("canonical JSON storage stays serialized while its technical editor stays hidden", () => {
    const computeSize = () => [320, 180];
    const serializeValue = () => "canonical";
    const widget = {
        type: "customtext",
        serialize: true,
        serializeValue,
        computeSize,
        options: {},
        inputEl: { style: {} },
        element: { style: {} },
    };

    assert.equal(hideCanonicalJsonWidget(widget), true);
    assert.deepEqual(widget.computeSize(), [0, -4]);
    assert.equal(widget.hidden, true);
    assert.equal(widget.options.hidden, true);
    assert.equal(widget.inputEl.style.display, "none");
    assert.equal(widget.element.style.display, "none");
    assert.equal(widget.type, "customtext");
    assert.equal(widget.serialize, true);
    assert.equal(widget.serializeValue, serializeValue);
    assert.equal(widget.__minimaxJsonStorageComputeSize, computeSize);

    hideCanonicalJsonWidget(widget);
    assert.equal(widget.__minimaxJsonStorageComputeSize, computeSize);
    assert.equal(widget.type, "customtext");
    assert.equal(widget.serializeValue, serializeValue);
});
