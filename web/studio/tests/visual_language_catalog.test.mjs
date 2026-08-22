import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
    VISUAL_LANGUAGE_TAXONOMY,
    previewRecordIsValid,
    visualLanguageHierarchy,
    visualLanguagePreview,
} from "../visual_language_catalog.js";

const NEW_VISUAL_LANGUAGES = [
    "vintage_rubberhose_2d",
    "cable_angular_graphic_comedy",
    "contemporary_vector_2d",
    "manga_monochrome_print",
    "anime_1960s70s_limited_cel",
    "mecha_super_robot_cel",
    "anime_ova_mechanical_detail",
    "anime_1990s_broadcast_cel",
    "anime_digital_compositing",
];

function taxonomyTokens() {
    return VISUAL_LANGUAGE_TAXONOMY.flatMap(([, branches]) => (
        branches.flatMap(([, tokens]) => tokens)
    ));
}

test("visual language hierarchy covers the real frontend catalog exactly once", () => {
    const source = readFileSync(new URL("../../backend_toggle.js", import.meta.url), "utf8");
    const block = source.split("    visualLanguage: [", 2)[1].split("    worldAesthetic: [", 1)[0];
    const frontendTokens = [...block.matchAll(/\["([a-z0-9_]+)",/g)].map((match) => match[1]);
    const taxonomy = taxonomyTokens();
    assert.equal(new Set(taxonomy).size, taxonomy.length, "a token appears in more than one family/branch");
    assert.deepEqual(new Set(taxonomy), new Set(frontendTokens));
    assert.ok(NEW_VISUAL_LANGUAGES.every((token) => taxonomy.includes(token)));
});

test("hierarchy searches family, era aliases and preserves unknown catalog values", () => {
    const choices = [
        ["manga_monochrome_print", "Classic monochrome manga print"],
        ["anime_1990s_broadcast_cel", "1990s broadcast cel anime"],
        ["future_local_style", "Future local style"],
    ];
    const print = visualLanguageHierarchy(choices, "screentone");
    assert.deepEqual(print[0].branches[0].choices, [["manga_monochrome_print", "Classic monochrome manga print"]]);
    const era = visualLanguageHierarchy(choices, "broadcast cel");
    assert.deepEqual(era[0].branches[0].choices, [["anime_1990s_broadcast_cel", "1990s broadcast cel anime"]]);
    const unknown = visualLanguageHierarchy(choices, "future local");
    assert.deepEqual(unknown, [{
        family: "Other",
        branches: [{ branch: "Unclassified", choices: [["future_local_style", "Future local style"]] }],
    }]);
});

test("preview cards reject remote or unprovenanced images and label placeholders honestly", () => {
    const placeholder = visualLanguagePreview("anime_general");
    assert.equal(placeholder.status, "placeholder");
    assert.equal(placeholder.label, "No sample installed");
    assert.match(placeholder.disclosure, /No bundled image claims to predict H3 output/);

    const valid = {
        kind: "original",
        src: "./previews/vintage_rubberhose_2d.webp",
        alt: "Original abstract line-and-shape study",
        provenance: {
            creator: "Project contributors",
            source: "Locally produced example",
            license: "GPL-3.0-only",
            sha256: "a".repeat(64),
        },
    };
    assert.equal(previewRecordIsValid(valid), true);
    assert.equal(previewRecordIsValid({ ...valid, src: "https://example.com/sample.webp" }), false);
    assert.equal(previewRecordIsValid({ ...valid, src: "./previews/../outside.webp" }), false);
    assert.equal(previewRecordIsValid({ ...valid, provenance: {} }), false);
    assert.equal(visualLanguagePreview("vintage_rubberhose_2d", {
        schemaVersion: 1,
        assets: { vintage_rubberhose_2d: valid },
    }).status, "available");
});
