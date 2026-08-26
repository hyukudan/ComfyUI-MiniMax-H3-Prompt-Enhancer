import test from "node:test";
import assert from "node:assert/strict";

import {
    emptyReferenceDirector, mediaTypeForFile, parseReferenceDirector, removeReferenceSource,
    setReferenceSource, sourcePreviewUrl,
} from "../reference_sources.js";

const source = {
    storage: "comfy_input",
    file: "minimax_h3_reference_director/Ana portrait-aabbcc.webp [input]",
    sha256: "a".repeat(64), mediaType: "picture", originalName: "Ana portrait.webp",
    sizeBytes: 42, mimeType: "image/webp",
};

test("physical source storage stays separate and updates immutably", () => {
    const original = emptyReferenceDirector();
    const connected = setReferenceSource(original, "asset.ana", source);
    assert.equal(original.sources["asset.ana"], undefined);
    assert.equal(connected.sources["asset.ana"].sha256, "a".repeat(64));
    const removed = removeReferenceSource(connected, "asset.ana");
    assert.equal(removed.sources["asset.ana"], undefined);
    assert.ok(connected.sources["asset.ana"]);
});

test("preview URLs use ComfyUI view parameters and reject traversal", () => {
    assert.equal(
        sourcePreviewUrl(source),
        "/view?filename=Ana+portrait-aabbcc.webp&type=input&subfolder=minimax_h3_reference_director",
    );
    assert.equal(sourcePreviewUrl({ file: "../secret.webp [input]" }), "");
    assert.equal(sourcePreviewUrl(null), "");
});

test("reference storage distinguishes blank, malformed and unsupported", () => {
    assert.equal(parseReferenceDirector("").kind, "v1");
    assert.equal(parseReferenceDirector("{").kind, "malformed");
    assert.equal(parseReferenceDirector(JSON.stringify({ format: "other", formatVersion: 1, sources: {} })).kind, "unsupported");
});

test("file media typing accepts browser MIME and portable extensions", () => {
    assert.equal(mediaTypeForFile({ name: "portrait.bin", type: "image/webp" }), "picture");
    assert.equal(mediaTypeForFile({ name: "voice.MP3", type: "" }), "audio");
    assert.equal(mediaTypeForFile({ name: "clip.mov", type: "" }), "video");
    assert.equal(mediaTypeForFile({ name: "notes.txt", type: "text/plain" }), "");
});
