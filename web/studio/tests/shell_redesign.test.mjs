import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
    clampDrawerWidth,
    defaultDrawerWidth,
    normalizeStudioSection,
    readStudioPrefs,
    STUDIO_SECTIONS,
    writeStudioPrefs,
} from "../drawer.js";
import { alignmentGuidance, overviewModel, sourceToolAttention } from "../overview.js";
import { validateStructuredRaw } from "../components/source_state.js";
import { STUDIO_UI_LEGACY_STORAGE_KEY, STUDIO_UI_STORAGE_KEY } from "../tokens.js";

function memoryStorage(initial = {}) {
    const entries = new Map(Object.entries(initial));
    return {
        getItem(key) { return entries.get(key) ?? null; },
        setItem(key, value) { entries.set(key, value); },
        value(key) { return entries.get(key); },
    };
}

function blankDocument() {
    return { kind: "blank", raw: "", value: null, version: null, errors: [], dirty: false };
}

function relativeLuminance(hex) {
    const channels = hex.match(/[a-f\d]{2}/gi).map((value) => {
        const channel = Number.parseInt(value, 16) / 255;
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(first, second) {
    const [light, dark] = [relativeLuminance(first), relativeLuminance(second)].sort((a, b) => b - a);
    return (light + 0.05) / (dark + 0.05);
}

test("drawer widths follow 1440p, 4K, desktop and mobile bounds", () => {
    assert.equal(defaultDrawerWidth(2560, 1440), 820);
    assert.equal(defaultDrawerWidth(3840, 2160), 920);
    assert.equal(clampDrawerWidth(null, 1440), 720);
    assert.equal(clampDrawerWidth(300, 1440), 420);
    assert.equal(clampDrawerWidth(1200, 1440), 864);
    assert.equal(clampDrawerWidth(1500, 3840), 1100);
    assert.equal(clampDrawerWidth(640, 680), 680);
});

test("UI preferences persist only shell state and normalize legacy deep links", () => {
    const storage = memoryStorage();
    const written = writeStudioPrefs({
        width: 712,
        lastSection: "references",
        railCollapsed: true,
        detailMode: "advanced",
        collapsedBlocks: { camera: true },
        project: { shouldNotPersist: true },
    }, storage);
    assert.equal(written.lastSection, "media");
    assert.deepEqual(readStudioPrefs(storage), {
        width: 712,
        lastSection: "media",
        railCollapsed: true,
        detailMode: "advanced",
        collapsedBlocks: { camera: true },
    });
    assert.equal(JSON.parse(storage.value(STUDIO_UI_STORAGE_KEY)).project, undefined);
    assert.equal(normalizeStudioSection("coach"), "review");
    assert.equal(normalizeStudioSection("unknown"), "overview");
});

test("malformed stored preferences fall back without throwing", () => {
    const storage = memoryStorage({ [STUDIO_UI_STORAGE_KEY]: "{" });
    assert.deepEqual(readStudioPrefs(storage), {
        width: null,
        lastSection: "overview",
        railCollapsed: false,
        detailMode: "guided",
        collapsedBlocks: {},
    });
});

test("persisting navigation before the first resize keeps the responsive default width", () => {
    const storage = memoryStorage();
    writeStudioPrefs({ ...readStudioPrefs(storage), lastSection: "shots" }, storage);
    assert.equal(readStudioPrefs(storage).width, null);
    assert.equal(clampDrawerWidth(readStudioPrefs(storage).width, 3840), 920);
});

test("v3 preferences migrate the former combined Camera & Look destination to Look", () => {
    const storage = memoryStorage({
        [STUDIO_UI_LEGACY_STORAGE_KEY]: JSON.stringify({ width: 810, lastSection: "camera", detailMode: "advanced" }),
    });
    assert.deepEqual(readStudioPrefs(storage), {
        width: 810,
        lastSection: "look",
        railCollapsed: false,
        detailMode: "advanced",
        collapsedBlocks: {},
    });
    assert.deepEqual(STUDIO_SECTIONS.map(({ id }) => id), ["overview", "shots", "staging", "subjects", "environments", "media", "camera", "look"]);
    assert.equal(normalizeStudioSection("camera_look"), "look");
});

test("Overview derives pipeline, library, continuity and diagnostic health", () => {
    const model = overviewModel({
        shotDocument: () => ({ kind: "v2", value: { shots: [
            { id: "s1", generationId: "g1" },
            { id: "s2", generationId: "g2" },
        ] } }),
        projectDocument: () => ({ kind: "v2", value: {
            mode: "chained_multishot",
            subjects: [{}, {}],
            environments: [{}],
            assets: [{}, {}, {}],
            generations: [
                { id: "g1", order: 1, bindings: [{}] },
                { id: "g2", order: 2, bindings: [{}, {}], subjectStates: [{ policy: "carry" }], environmentStates: [{ policy: "carry" }] },
            ],
        } }),
        cinematographyDocument: blankDocument,
        diagnostics: () => ({ stale: true, diagnostics: [{ severity: "error" }, { severity: "advice" }] }),
    });
    assert.equal(model.blank, false);
    assert.equal(model.shots, 2);
    assert.deepEqual([model.subjects, model.environments, model.assets], [2, 1, 3]);
    assert.deepEqual(model.generations.map((item) => [item.shots, item.bindings]), [[1, 1], [1, 2]]);
    assert.deepEqual(model.diagnostics, { errors: 1, warnings: 0, tips: 1 });
    assert.equal(model.stale, true);
});

test("Overview uses the live node mode for contextual boundary alignment", () => {
    const model = overviewModel({
        mode: () => "fl2va",
        shotDocument: blankDocument,
        projectDocument: () => ({ kind: "v2", value: { mode: "auto", generations: [] } }),
        cinematographyDocument: blankDocument,
        diagnostics: () => ({ diagnostics: [] }),
    });
    assert.equal(model.mode, "fl2va");
    assert.match(alignmentGuidance(model.mode), /opening \+ ending alignment/i);
    assert.match(alignmentGuidance("i2va"), /opening frame/i);
    assert.match(alignmentGuidance("l2va"), /final frame/i);
    assert.equal(alignmentGuidance("t2va"), null);
});

test("Overview treats legacy Project data as preserved read-only source", () => {
    const model = overviewModel({
        shotDocument: blankDocument,
        projectDocument: () => ({ kind: "v1", value: { assets: [{ id: "legacy" }] }, raw: "{}" }),
        cinematographyDocument: blankDocument,
        diagnostics: () => ({ diagnostics: [] }),
    });
    assert.equal(model.sources.project.kind, "v1");
    assert.equal(model.assets, 0);
    assert.equal(model.blank, false);
    assert.equal(sourceToolAttention(model.sources), 0);
});

test("source tools surface only malformed and future inputs as attention states", () => {
    assert.equal(sourceToolAttention({
        shot: { kind: "v1" },
        project: { kind: "v2" },
        camera: { kind: "blank" },
    }), 0);
    assert.equal(sourceToolAttention({
        shot: { kind: "malformed" },
        project: { kind: "v1" },
        camera: { kind: "future" },
    }), 2);
});

test("source tools stay collapsed at the end instead of occupying the header", () => {
    const drawerSource = readFileSync(new URL("../drawer.js", import.meta.url), "utf8");
    const overviewSource = readFileSync(new URL("../overview.js", import.meta.url), "utf8");
    const stylesSource = readFileSync(new URL("../styles.js", import.meta.url), "utf8");
    assert.doesNotMatch(drawerSource, /minimax-h3-header-sources/);
    assert.match(overviewSource, /createElement\("details"\)/);
    assert.match(overviewSource, /Import & source tools/);
    assert.match(stylesSource, /minimax-h3-source-tools/);
    assert.match(stylesSource, /minimax-h3-section-camera/);
});

test("Overview CTAs use explicit high-contrast primary and secondary states", () => {
    const overviewSource = readFileSync(new URL("../overview.js", import.meta.url), "utf8");
    const stylesSource = readFileSync(new URL("../styles.js", import.meta.url), "utf8");
    const tokensSource = readFileSync(new URL("../tokens.js", import.meta.url), "utf8");
    assert.match(overviewSource, /review\.className = "minimax-h3-button minimax-h3-button-primary"/);
    assert.match(tokensSource, /--h3-button-text:\s*#f7f9fc/);
    assert.match(tokensSource, /--h3-on-primary:\s*#0b1220/);
    assert.match(stylesSource, /\.minimax-h3-button-secondary\s*\{[^}]*color:\s*var\(--h3-button-text\)\s*!important/s);
    assert.match(stylesSource, /\.minimax-h3-button-primary:hover:not\(:disabled\)/);
    assert.match(stylesSource, /\.minimax-h3-button-secondary:hover:not\(:disabled\)/);
    assert.match(stylesSource, /\.minimax-h3-button:active:not\(:disabled\)/);
    assert.match(stylesSource, /cursor:\s*not-allowed/);
    assert.match(stylesSource, /\.minimax-h3-studio button:focus-visible/);
    assert.ok(contrastRatio("#0b1220", "#7ca6ff") >= 4.5, "primary button meets WCAG AA for normal text");
    assert.ok(contrastRatio("#f7f9fc", "#20262e") >= 4.5, "secondary button meets WCAG AA on the fallback surface");
    assert.match(stylesSource, /\.minimax-h3-review-button\s*\{[^}]*color:\s*var\(--h3-button-text\)/s);
    assert.match(stylesSource, /\.minimax-h3-review-button:hover:not\(:disabled\)/);
});

test("Overview density adapts across the 720, 820 and 920 drawer defaults", () => {
    const stylesSource = readFileSync(new URL("../styles.js", import.meta.url), "utf8");
    assert.match(stylesSource, /@container h3-studio \(max-width: 799px\)[\s\S]*?\.minimax-h3-overview-actions\s*\{[^}]*repeat\(2, minmax\(0, 1fr\)\)/);
    assert.match(stylesSource, /@container h3-studio \(max-width: 559px\)[\s\S]*?\.minimax-h3-overview-actions\s*\{[^}]*grid-template-columns:\s*1fr/);
    assert.match(stylesSource, /\.minimax-h3-overview-health\s*\{[^}]*flex-direction:\s*column/);
});

test("Review budget and dismissal controls stay responsive without horizontal overflow", () => {
    const stylesSource = readFileSync(new URL("../styles.js", import.meta.url), "utf8");
    assert.match(stylesSource, /\.minimax-h3-review-budget-rows\s*\{[^}]*repeat\(2, minmax\(0, 1fr\)\)/s);
    assert.match(stylesSource, /@container h3-studio \(max-width: 559px\)[\s\S]*?\.minimax-h3-review-budget-rows\s*\{[^}]*grid-template-columns:\s*1fr/s);
    assert.match(stylesSource, /\.minimax-h3-review-dismiss-toggle\s*\{[^}]*white-space:\s*nowrap/s);
    assert.match(stylesSource, /\.minimax-h3-review-card header\s*\{[^}]*minmax\(0, 1fr\)/s);
});

test("Shots keeps a distinct 16px inter-card rhythm at the 820px drawer default", () => {
    const stylesSource = readFileSync(new URL("../styles.js", import.meta.url), "utf8");
    const shotsSource = readFileSync(new URL("../tab_shots.js", import.meta.url), "utf8");
    const tokensSource = readFileSync(new URL("../tokens.js", import.meta.url), "utf8");
    assert.equal(defaultDrawerWidth(2560, 1440), 820);
    assert.match(shotsSource, /minimax-h3-shot-inspector/);
    assert.match(stylesSource, /\.minimax-h3-section-shots \.minimax-h3-shot-inspector\s*\{[^}]*row-gap:\s*var\(--h3-space-4\)/s);
    assert.match(tokensSource, /--h3-space-4:\s*16px/);
    assert.match(stylesSource, /\.minimax-h3-shot-inspector > \.minimax-h3-shot-camera-summary\s*\{[^}]*margin-block:\s*0/s);
});

test("ported visual-language navigation keeps an explicit pointer affordance", () => {
    const stylesSource = readFileSync(new URL("../styles.js", import.meta.url), "utf8");
    assert.match(stylesSource, /\.minimax-h3-searchable-select-popover button:not\(:disabled\)\s*\{\s*cursor:\s*pointer/);
    assert.match(stylesSource, /\.minimax-h3-visual-back\s*\{[^}]*cursor:\s*pointer/s);
});

test("Look cards keep intrinsic height and collapse fields before labels clip", () => {
    const stylesSource = readFileSync(new URL("../styles.js", import.meta.url), "utf8");
    const lookSource = readFileSync(new URL("../tab_camera_look.js", import.meta.url), "utf8");
    assert.match(stylesSource, /\.minimax-h3-section-camera,[\s\S]*?\.minimax-h3-section-look\s*\{[^}]*grid-auto-rows:\s*max-content/s);
    assert.match(stylesSource, /@container h3-studio-panel \(max-width: 620px\)[\s\S]*?\.minimax-h3-look-block \.minimax-h3-studio-columns\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/s);
    assert.match(stylesSource, /\.minimax-h3-progressive-disclosure\s*\{[^}]*gap:[^}]*padding:/s);
    assert.match(lookSource, /minimax-h3-look-camera/);
});

test("Media shell keeps cards separated and dense editors inside the panel", () => {
    const stylesSource = readFileSync(new URL("../styles.js", import.meta.url), "utf8");
    const mediaSource = readFileSync(new URL("../tab_references.js", import.meta.url), "utf8");
    assert.match(stylesSource, /\.minimax-h3-section-media\s*\{[^}]*display:\s*grid;[^}]*gap:\s*var\(--h3-space-4\)/s);
    assert.match(stylesSource, /@container h3-studio-panel \(min-width: 600px\)[\s\S]*?\.minimax-h3-master-detail\s*\{[^}]*grid-template-columns:\s*var\(--h3-list-width\) minmax\(0, 1fr\)/);
    assert.match(stylesSource, /\.minimax-h3-generation-pane\s*>\s*\*[\s\S]*?min-width:\s*0;[\s\S]*?max-width:\s*100%/);
    assert.match(stylesSource, /\.minimax-h3-chip-picker\s*\{[^}]*max-width:\s*100%;[^}]*flex-wrap:\s*wrap/s);
    assert.match(stylesSource, /\.minimax-h3-segmented\s*\{[^}]*max-width:\s*100%;[^}]*flex-wrap:\s*wrap/s);
    assert.match(stylesSource, /\.minimax-h3-media-steps\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/s);
    assert.match(stylesSource, /\.minimax-h3-media-workflows\s*\{[^}]*display:\s*grid;[^}]*gap:\s*var\(--h3-space-4\)/s);
    assert.match(stylesSource, /\.minimax-h3-media-recipes\s*\{[^}]*column-gap:\s*var\(--h3-space-2\);[^}]*row-gap:\s*var\(--h3-space-3\)/s);
    assert.match(stylesSource, /\.minimax-h3-media-recipes \+ \.minimax-h3-planning-context\s*\{[^}]*margin-top:\s*var\(--h3-space-1\)/s);
    for (const width of [720, 820, 920]) {
        const columns = width <= 799 ? 2 : 3;
        const rows = Math.ceil(4 / columns);
        assert.equal(rows, 2, `${width}px keeps the second recipe row separated by the declared row gap`);
    }
    assert.match(mediaSource, /\+ Add reference/);
    assert.match(mediaSource, /Reference setup · 2 steps/);
    assert.match(mediaSource, /actual files stay connected to the generator node/);
    assert.match(mediaSource, /File slot assignments/);
    assert.doesNotMatch(mediaSource, /actionButton\("\+ Asset"/);
});

test("source repair validates object shape and supported schema versions", () => {
    assert.equal(validateStructuredRaw('{"schemaVersion":2}', { acceptedVersions: [2] }).valid, true);
    assert.equal(validateStructuredRaw('{"schemaVersion":3}', { acceptedVersions: [2] }).valid, false);
    assert.equal(validateStructuredRaw("[]", { acceptedVersions: [2] }).valid, false);
    assert.equal(validateStructuredRaw("{", { acceptedVersions: [2] }).valid, false);
});
