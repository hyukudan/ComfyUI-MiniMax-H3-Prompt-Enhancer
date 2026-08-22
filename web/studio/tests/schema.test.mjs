import assert from "node:assert/strict";
import test from "node:test";

import {
    parseStructuredJson,
    serializeStructuredJson,
    structuredJsonIsEditable,
} from "../schema.js";

test("blank input remains byte-identical and editable", () => {
    const document = parseStructuredJson(" \n\t", { supportedVersions: [1] });
    assert.equal(document.kind, "blank");
    assert.equal(document.raw, " \n\t");
    assert.equal(document.dirty, false);
    assert.equal(structuredJsonIsEditable(document), true);
});

test("recognized v1 and v2 preserve their original bytes", () => {
    const v1 = '{  "schemaVersion" : 1, "shots" : [] }';
    const v2 = '{\n"schemaVersion":2,"shots":[]\n}';
    assert.deepEqual(
        [parseStructuredJson(v1, { supportedVersions: [1, 2] }).kind,
            parseStructuredJson(v2, { supportedVersions: [1, 2] }).kind],
        ["v1", "v2"],
    );
    assert.equal(parseStructuredJson(v1, { supportedVersions: [1, 2] }).raw, v1);
    assert.equal(parseStructuredJson(v2, { supportedVersions: [1, 2] }).raw, v2);
});

test("malformed and future JSON are read-only and never normalized", () => {
    const malformed = '{"schemaVersion":1,"shots":[';
    const future = '{ "schemaVersion": 19, "unknown": true }';
    const malformedDocument = parseStructuredJson(malformed, { supportedVersions: [1] });
    const futureDocument = parseStructuredJson(future, { supportedVersions: [1] });
    assert.equal(malformedDocument.kind, "malformed");
    assert.equal(futureDocument.kind, "future");
    assert.equal(malformedDocument.raw, malformed);
    assert.equal(futureDocument.raw, future);
    assert.equal(structuredJsonIsEditable(malformedDocument), false);
    assert.equal(structuredJsonIsEditable(futureDocument), false);
});

test("serialization happens only for an explicit edited value", () => {
    assert.equal(serializeStructuredJson({ schemaVersion: 1, shots: [] }), '{"schemaVersion":1,"shots":[]}');
});
