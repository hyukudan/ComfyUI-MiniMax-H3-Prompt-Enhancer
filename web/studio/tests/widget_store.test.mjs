import assert from "node:assert/strict";
import test from "node:test";

import { createWidgetStore } from "../widget_store.js";

test("hydrate observes raw JSON without writing it", () => {
    const raw = '{  "schemaVersion" : 1, "shots" : [] }';
    const widget = { value: raw };
    const store = createWidgetStore(widget, { supportedVersions: [1] });
    let writes = 0;
    store.hydrate();
    assert.equal(writes, 0);
    assert.equal(widget.value, raw);
    assert.equal(store.document.raw, raw);
});

test("an explicit edit performs one atomic commit and notifies subscribers", () => {
    const widget = { value: "" };
    const store = createWidgetStore(widget, { supportedVersions: [1] });
    const seen = [];
    store.subscribe((document) => seen.push([document.kind, document.dirty]));
    const next = '{"schemaVersion":1,"shots":[]}';
    assert.equal(store.commit(next, (raw) => {
        widget.value = raw;
        return true;
    }), true);
    assert.equal(widget.value, next);
    assert.deepEqual(seen, [["v1", true]]);
});

test("malformed and future documents reject structured commits", () => {
    for (const raw of ['{"schemaVersion":1', '{"schemaVersion":9,"shots":[]}']) {
        const widget = { value: raw };
        const store = createWidgetStore(widget, { supportedVersions: [1] });
        let writes = 0;
        assert.equal(store.commit('{"schemaVersion":1,"shots":[]}', () => {
            writes += 1;
            return true;
        }), false);
        assert.equal(writes, 0);
        assert.equal(widget.value, raw);
    }
});

test("hydration snapshots stay identical for every preservation state", () => {
    const snapshots = [
        "",
        " \n\t",
        '{  "schemaVersion" : 1, "shots" : [] }',
        '{"schemaVersion":1,"shots":[',
        '{\n"schemaVersion":27,"future":{"camera":true}\n}',
    ];
    for (const raw of snapshots) {
        const widget = { value: raw };
        const store = createWidgetStore(widget, { supportedVersions: [1] });
        store.hydrate();
        assert.equal(widget.value, raw);
        assert.equal(store.document.raw, raw);
    }
});
