import assert from "node:assert/strict";
import test from "node:test";

import {
    applyAudioClipToAsset, audioClipDuration, normalizedAudioClip,
} from "../audio_trim_editor.js";

test("normalizes an exact bounded voice fragment", () => {
    assert.deepEqual(normalizedAudioClip({ startSeconds: 1.25, endSeconds: 4.5 }), { startSeconds: 1.25, endSeconds: 4.5 });
    assert.equal(audioClipDuration({ startSeconds: 1.25, endSeconds: 4.5 }), 3.25);
});

test("rejects invalid or overlong fragments", () => {
    assert.equal(normalizedAudioClip({ startSeconds: -1, endSeconds: 2 }), null);
    assert.equal(normalizedAudioClip({ startSeconds: 2, endSeconds: 1 }), null);
    assert.equal(normalizedAudioClip({ startSeconds: 0, endSeconds: 15.01 }), null);
});

test("stores a clip on the logical asset and updates its selected duration", () => {
    const asset = { id: "voice", type: "audio", durationSeconds: 10 };
    applyAudioClipToAsset(asset, { startSeconds: 2, endSeconds: 6.5 }, 10);
    assert.deepEqual(asset.audioClip, { startSeconds: 2, endSeconds: 6.5 });
    assert.equal(asset.durationSeconds, 4.5);
    applyAudioClipToAsset(asset, null, 10);
    assert.equal(asset.audioClip, undefined);
    assert.equal(asset.durationSeconds, 10);
});
