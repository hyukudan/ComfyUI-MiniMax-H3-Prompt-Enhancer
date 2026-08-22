import assert from "node:assert/strict";
import test from "node:test";

import { applySafeActionDocuments } from "../coach_actions.js";
import { STRUCTURED_SCHEMA_VERSIONS, nativeStructuredDocumentView } from "../catalogs.js";
import { generationMediaModel, nextAvailableSlot } from "../media_model.js";
import { effectiveH3Resolution, formatResolutionLabel } from "../media_resolution.js";
import {
    cameraOverrideRows,
    filterVisualLanguageChoices,
    renderCameraLookTab,
    visualLanguagePopoverGeometry,
} from "../tab_camera_look.js";
import { diagnosticLocationLabel, diagnosticSection, groupDiagnosticsBySeverity, reviewReportState } from "../tab_coach.js";
import { bindingSuggestion, renderReferencesTab } from "../tab_references.js";

class FakeElement {
    constructor(tagName = "div") {
        this.tagName = tagName.toUpperCase();
        this.children = [];
        this.dataset = {};
        this.style = {};
        this.className = "";
        this.classList = {
            add: (...names) => { this.className += ` ${names.join(" ")}`; },
            toggle: () => {},
            contains: (name) => this.className.split(/\s+/).includes(name),
        };
        this.listeners = new Map();
        this.value = "";
        this.hidden = false;
    }
    append(...children) { this.children.push(...children); }
    appendChild(child) { this.children.push(child); return child; }
    replaceChildren(...children) { this.children = [...children]; }
    addEventListener(type, listener) {
        const listeners = this.listeners.get(type) ?? [];
        listeners.push(listener);
        this.listeners.set(type, listeners);
    }
    async dispatch(type, init = {}) {
        const event = { key: "", preventDefault() {}, target: this, ...init };
        for (const listener of this.listeners.get(type) ?? []) await listener(event);
    }
    setAttribute(name, value) { this[name] = value; }
    removeAttribute(name) { delete this[name]; }
    querySelector(selector) {
        const found = this.querySelectorAll(selector)[0];
        if (found) return found;
        // jsdom-less fixture: tab_references uses innerHTML for these two labels.
        return ["strong", "small"].includes(selector) ? new FakeElement(selector) : null;
    }
    querySelectorAll(selector) {
        const match = (element) => {
            if (selector.startsWith("[") && selector.endsWith("]")) {
                const [, attribute, expected] = selector.match(/^\[([^=]+)=['"]?([^'"]+)['"]?\]$/) ?? [];
                return attribute ? String(element[attribute]) === expected : false;
            }
            return element.tagName === selector.toUpperCase();
        };
        const results = [];
        const visit = (element) => {
            for (const child of element.children ?? []) {
                if (child && typeof child === "object") {
                    if (match(child)) results.push(child);
                    visit(child);
                }
            }
        };
        visit(this);
        return results;
    }
    contains(candidate) {
        return candidate === this || this.children.some((child) => child?.contains?.(candidate));
    }
    focus() { globalThis.document.activeElement = this; }
    select() { this.selected = true; }
}

function descendants(root) {
    return [root, ...(root.children ?? []).flatMap((child) => child && typeof child === "object" ? descendants(child) : [])];
}

function projectFixture() {
    return {
        schemaVersion: 2,
        mode: "chained_multishot",
        assets: [
            { id: "portrait", type: "picture", name: "Portrait", available: true },
            { id: "view", type: "picture", name: "Street", available: true },
            { id: "motion", type: "video", name: "Motion", available: true, durationSeconds: 4, audioMode: "paired" },
        ],
        subjects: [{
            id: "marta", h3Index: 1, name: "Marta", description: "Marta", identityAssetIds: ["portrait"],
            baseAppearanceStateId: "base", appearanceStates: [{ id: "base", name: "Base", controls: [] }],
        }],
        environments: [{
            id: "street", name: "Street", permanent: {}, defaultStateId: "night",
            views: [{ id: "overview", name: "Overview", role: "overview", assetId: "view" }],
            states: [{ id: "night", name: "Night" }],
        }],
        generations: [{
            id: "g1", order: 1, activation: { mode: "auto" },
            bindings: [{ assetId: "motion", slotIndex: 1, soundtrackSlotIndex: 1 }],
            subjectStates: [{ subjectId: "marta", policy: "explicit", stateId: "base" }],
            environmentStates: [{ environmentId: "street", policy: "explicit", stateId: "night", viewIds: ["overview"] }],
        }, {
            id: "g2", order: 2, activation: { mode: "explicit", roots: [{ kind: "asset", id: "motion" }] },
            bindings: [], subjectStates: [], environmentStates: [],
        }],
    };
}

test("media model resolves populated assets, dependencies and paired soundtrack capacity", () => {
    const project = projectFixture();
    const model = generationMediaModel(project, project.generations[0]);
    assert.deepEqual([...model.activeAssetIds].sort(), ["motion", "portrait", "view"]);
    assert.deepEqual(model.counts, { picture: 2, video: 1, audio: 1 });
    assert.equal(model.videoSeconds, 4);
    assert.equal(model.audioSeconds, 4);
    assert.match(model.resources.find((resource) => resource.id === "portrait").reasons.join(" "), /identity of Marta/);
    assert.equal(nextAvailableSlot(project, project.generations[0], "video"), 2);
});

test("first-reference assistant chooses a compatible generation and physical slots", () => {
    const project = projectFixture();
    const portrait = project.assets.find((asset) => asset.id === "portrait");
    const motion = project.assets.find((asset) => asset.id === "motion");
    assert.equal(bindingSuggestion(project, portrait, "g1").generation.id, "g1");
    assert.equal(bindingSuggestion(project, motion, "g1").generation.id, "g2", "already-bound references move to the next generation");
    const suggestion = bindingSuggestion(project, motion, "g2");
    assert.equal(suggestion.generation.id, "g2");
    assert.equal(suggestion.binding.slotIndex, 1);
    assert.equal(suggestion.binding.soundtrackSlotIndex, 1);
});

test("Visual language popover stays inside 720, 820 and 920 viewports", () => {
    for (const viewportWidth of [720, 820, 920]) {
        const rect = { left: viewportWidth - 278, right: viewportWidth - 18, top: 174, bottom: 206, width: 260 };
        const geometry = visualLanguagePopoverGeometry(rect, viewportWidth, 720);
        assert.ok(geometry.left >= 8);
        assert.ok(geometry.left + geometry.width <= viewportWidth - 8);
        assert.ok(geometry.top >= 8);
        assert.ok(geometry.top + geometry.maxHeight <= 720 - 8);
        assert.equal(geometry.placement, "below");
    }
    const above = visualLanguagePopoverGeometry(
        { left: 520, right: 790, top: 620, bottom: 652, width: 270 },
        820,
        720,
    );
    assert.equal(above.placement, "above");
    assert.ok(above.bottom >= 8);
    assert.ok(720 - above.bottom - above.maxHeight >= 8);
});

test("Media opens the purpose assistant inline without writing project data", async () => {
    const previousDocument = globalThis.document;
    globalThis.document = { createElement: (tagName) => new FakeElement(tagName) };
    try {
        const project = projectFixture();
        const raw = JSON.stringify(project);
        let writes = 0;
        const controller = {
            projectUiState: { sourceRaw: null, project: null },
            shotUiState: { selectedId: null },
            projectDocument: () => ({ kind: "v2", raw, value: project }),
            shotDocument: () => ({ kind: "v2", value: { shots: [] } }),
            commitProject: () => { writes += 1; return true; },
        };
        const container = new FakeElement();
        renderReferencesTab(container, controller);
        assert.ok(container.children.length >= 4);
        assert.equal(controller.projectUiState.selectedGenerationId, "g1");
        assert.equal(controller.projectUiState.selectedAssetId, "portrait");
        const labels = descendants(container).map((element) => element.textContent).filter(Boolean);
        assert.ok(labels.includes("+ Plan reference"));
        assert.ok(labels.includes("Export LLM planning context"));
        for (const recipe of ["Targeted edit", "Relight", "Performance transfer", "Continuation"]) assert.ok(labels.includes(recipe));
        const open = descendants(container).find((element) => element.textContent === "+ Plan reference");
        await open.dispatch("click");
        const openedLabels = descendants(container).map((element) => element.textContent).filter(Boolean);
        assert.ok(openedLabels.includes("Plan one reference by purpose"));
        assert.ok(openedLabels.includes("Cancel"));
        assert.equal(writes, 0, "opening the assistant is UI-only");
    } finally {
        globalThis.document = previousDocument;
    }
});

test("blank Project v2 mounts the assistant directly below its trigger after click", async () => {
    const previousDocument = globalThis.document;
    globalThis.document = { createElement: (tagName) => new FakeElement(tagName) };
    try {
        const project = {
            schemaVersion: 2, mode: "auto", assets: [], subjects: [], environments: [],
            generations: [{ id: "g1", order: 1, activation: { mode: "auto" }, bindings: [], subjectStates: [], environmentStates: [] }],
        };
        const raw = JSON.stringify(project);
        let writes = 0;
        const controller = {
            projectUiState: { sourceRaw: null, project: null }, shotUiState: { selectedId: null },
            projectDocument: () => ({ kind: "v2", raw, value: project }),
            shotDocument: () => ({ kind: "blank", raw: "", value: null }),
            commitProject: () => { writes += 1; return true; },
        };
        const container = new FakeElement();
        renderReferencesTab(container, controller);
        await descendants(container).find((element) => element.textContent === "+ Plan reference").dispatch("click");
        const workflows = descendants(container).find((element) => element.className === "minimax-h3-media-workflows");
        const assistantIndex = workflows.children.findIndex((element) => element.className.includes("minimax-h3-purpose-assistant"));
        const recipesIndex = workflows.children.findIndex((element) => element.className.includes("minimax-h3-media-recipes"));
        assert.equal(assistantIndex, 1, "assistant follows the trigger instead of mounting below recipes/export");
        assert.ok(assistantIndex < recipesIndex);
        assert.ok(descendants(workflows).some((element) => element.textContent === "Cancel"));
        assert.equal(writes, 0);
    } finally {
        globalThis.document = previousDocument;
    }
});

test("all five diagnostic safe actions mutate only their owned document", () => {
    const shotPlan = {
        schemaVersion: 2,
        timingMode: "auto",
        shots: [{
            id: "s1", generationId: "g1", action: "Walks",
            cameraStart: { framing: "close_up", angle: "eye_level" },
            cameraPath: { motionType: "push_in", speed: "slow" },
            appearanceTransitions: [{ subjectId: "marta", fromStateId: "wrong", toStateId: "wet", timing: "during_shot", trigger: "rain", mechanism: "rain" }],
        }],
    };
    const project = projectFixture();
    let result = applySafeActionDocuments({ kind: "clear_shot_camera", shotId: "s1", aspects: ["motion", "framing"] }, { shotPlan, project });
    assert.equal(result.changed, true);
    assert.equal(result.shotPlan.shots[0].cameraPath, undefined);
    assert.deepEqual(result.shotPlan.shots[0].cameraStart, { angle: "eye_level" });
    assert.equal(project.generations[0].bindings.length, 1, "source project stays immutable");

    result = applySafeActionDocuments({ kind: "clear_global_camera", aspects: ["motion", "lens"] }, {
        shotPlan, project, camera: { cameraMotion: "push_in", cameraAmplitude: "small", cameraSpeed: "slow", optics: "lens_35mm", lensEffects: "clean" },
    });
    assert.deepEqual(result.cameraUpdates, { cameraMotion: "none", cameraAmplitude: "auto", cameraSpeed: "auto", optics: "none", lensEffects: "none" });

    result = applySafeActionDocuments({ kind: "activate_resource", generationId: "g2", resource: { kind: "subject", id: "marta" } }, { shotPlan, project });
    assert.equal(result.changed, true);
    assert.deepEqual(result.project.generations[1].activation.roots.at(-1), { kind: "subject", id: "marta" });

    result = applySafeActionDocuments({ kind: "add_binding", generationId: "g2", assetId: "view", slotIndex: 2 }, { shotPlan, project });
    assert.equal(result.changed, true);
    assert.deepEqual(result.project.generations[1].bindings, [{ assetId: "view", slotIndex: 2 }]);

    result = applySafeActionDocuments({ kind: "align_transition_from_state", shotId: "s1", entityKind: "subject", entityId: "marta", stateId: "base" }, { shotPlan, project });
    assert.equal(result.changed, true);
    assert.equal(result.shotPlan.shots[0].appearanceTransitions[0].fromStateId, "base");
});

test("camera provenance rows and Review grouping expose usable locations", () => {
    const rows = cameraOverrideRows({ shots: [{ id: "s1", cameraStart: { framing: "close_up" } }, { id: "s2", cameraPath: { motionType: "pan_left" }, referenceUses: [{ assetId: "motion", role: "camera_transfer", cameraAspects: ["motion"] }] }] }, [
        ["shotScale", "Shot scale"], ["cameraMotion", "Camera motion"], ["colorPalette", "Color palette"],
    ], { assets: [{ id: "motion", name: "Motion", cameraTransfer: { enabled: true, aspects: ["motion"] } }] });
    assert.deepEqual(rows.map((row) => row.shotIds), [["s1"], ["s2"], []]);
    assert.deepEqual(rows[1].mediaOwners, [{ shotId: "s2", assetId: "motion", assetName: "Motion" }]);
    const diagnostics = [{ severity: "advice" }, { severity: "error" }, { severity: "warning" }, { severity: "error" }];
    assert.deepEqual(groupDiagnosticsBySeverity(diagnostics).map((group) => [group.severity, group.items.length]), [["error", 2], ["warning", 1], ["advice", 1]]);
    assert.equal(diagnosticLocationLabel({ generationId: "g2", shotId: "s3", field: "camera" }), "g2 · Shot s3 · camera");
    assert.equal(diagnosticSection({ category: "camera", location: { shotId: "s3", field: "shot_plan_json.shots[2].cameraPath" } }), "camera");
    assert.equal(diagnosticSection({ category: "camera", location: { shotId: "s3", field: "cinematography_json.cameraMotion" } }), "look");
});

test("Review distinguishes an untouched panel from a completed clean run", () => {
    assert.equal(reviewReportState({ diagnostics: [], stale: false }), "not-run");
    assert.equal(reviewReportState({
        schemaVersion: 1,
        stale: false,
        summary: { errors: 0, warnings: 0, advice: 0, valid: true, qualityValid: true },
        diagnostics: [],
    }), "clean");
    assert.equal(reviewReportState({ schemaVersion: 1, stale: true, diagnostics: [] }), "stale-clean");
    assert.equal(reviewReportState({ schemaVersion: 1, diagnostics: [{ severity: "warning" }] }), "findings");
});

test("Visual language search matches labels, tokens and catalog groups", () => {
    const choices = [
        ["none", "No preference"],
        ["anime_shonen", "Kinetic action anime (shōnen)"],
        ["live_action_gritty", "Gritty live action"],
        ["watercolor_2d", "Watercolor 2D animation"],
    ];
    const groups = [
        ["Anime", [["anime_shonen", "Kinetic action anime (shōnen)"], ["watercolor_2d", "Watercolor 2D animation"]]],
        ["Live action", [["live_action_gritty", "Gritty live action"]]],
    ];
    assert.deepEqual(filterVisualLanguageChoices(choices, groups, "shonen")[0].choices, [["anime_shonen", "Kinetic action anime (shōnen)"]]);
    assert.deepEqual(filterVisualLanguageChoices(choices, groups, "live action")[0], {
        group: "Live action", choices: [["live_action_gritty", "Gritty live action"]],
    });
    assert.deepEqual(filterVisualLanguageChoices(choices, groups, "missing"), []);
});

test("Look renders hierarchical visual-language navigation, global search and clipboard transfer", async () => {
    const previousDocument = globalThis.document;
    const navigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, "navigator");
    globalThis.document = { createElement: (tagName) => new FakeElement(tagName), activeElement: null };
    const creativeValues = { visualLanguage: "anime_shonen", tone: "future_mood" };
    let creativeCommits = 0;
    let importedPayload = "";
    let clipboardValue = "";
    Object.defineProperty(globalThis, "navigator", {
        configurable: true,
        value: { clipboard: {
            writeText: async (value) => { clipboardValue = value; },
            readText: async () => '{"schemaVersion":1,"name":"Imported","creativeTreatment":{"schemaVersion":2}}',
        } },
    });
    const controller = {
        studioDetailMode: "guided",
        setStudioDetailMode(mode) { this.studioDetailMode = mode; },
        creativeDocument: () => ({ kind: "v2", value: { schemaVersion: 2 } }),
        cinematographyDocument: () => ({ kind: "v2", value: { schemaVersion: 2 } }),
        creativeFields: () => [
            ["visualLanguage", "Visual language", [
                ["none", "No preference"], ["anime_shonen", "Kinetic action anime"], ["watercolor_2d", "Watercolor 2D animation"],
            ]],
            ["tone", "Mood (tone)", [
                ["none", "No preference"], ["epic", "Epic"], ["clinical", "Clinical"], ["pulp_heightened", "Heightened (pulp)"],
            ]],
        ],
        visualLanguageGroups: () => [["Animation", [["anime_shonen", "Kinetic action anime"], ["watercolor_2d", "Watercolor 2D animation"]]]],
        creativeValue: (key) => creativeValues[key] ?? "none",
        commitCreative: (key, value) => { creativeCommits += 1; creativeValues[key] = value; return true; },
        cameraFields: () => [],
        cameraValue: () => "none",
        lookNames: () => ["Cinema"],
        exportLook: () => ({ ok: true, name: "Cinema", payload: '{"schemaVersion":1,"name":"Cinema"}' }),
        importLook: (payload) => { importedPayload = payload; return { ok: true, name: "Imported" }; },
        shotDocument: () => ({ kind: "blank", value: { shots: [] } }),
        projectDocument: () => ({ kind: "blank" }),
        diagnostics: () => ({ diagnostics: [] }),
    };
    try {
        const container = new FakeElement();
        renderCameraLookTab(container, controller);
        const elements = descendants(container);
        const detailGroup = elements.find((element) => element.className === "minimax-h3-detail-mode");
        assert.ok(detailGroup, "Look owns its own Guided / Advanced control");
        const advanced = descendants(detailGroup).find((element) => element.textContent === "Advanced");
        assert.equal(advanced?.["aria-pressed"], "false");
        await advanced.dispatch("click");
        assert.equal(controller.studioDetailMode, "advanced");
        const combobox = elements.find((element) => element.role === "combobox");
        const search = elements.find((element) => element.type === "search");
        const controlled = elements.find((element) => element.id === combobox?.["aria-controls"]);
        assert.ok(combobox && controlled && search);
        assert.equal(controlled.role, "navigation");
        await combobox.dispatch("click");
        const family = descendants(controlled).find((element) => element.textContent === "Japanese manga & anime");
        assert.ok(family, "family level is rendered first");
        await family.dispatch("click");
        assert.equal(controlled.role, "navigation");
        const branch = descendants(controlled).find((element) => element.textContent === "Contemporary animation");
        assert.ok(branch, "era / technique level follows the family");
        await branch.dispatch("click");
        assert.equal(controlled.role, "listbox");
        assert.ok(controlled.querySelectorAll("[role='option']").length > 0, "variants are the final level");
        search.value = "water";
        await search.dispatch("input");
        assert.equal(controlled.role, "listbox");
        const matchingOption = controlled.querySelectorAll("[role='option']")[0];
        assert.equal(matchingOption.dataset.value, "watercolor_2d");
        await matchingOption.dispatch("click");
        assert.equal(creativeValues.visualLanguage, "watercolor_2d");
        assert.equal(descendants(container).filter((element) => element.className === "minimax-h3-visual-preview-notice").length, 1);
        assert.equal(descendants(container).filter((element) => element.textContent === "No sample installed").length, 0);

        const moodTrigger = descendants(container).find((element) => element.className.includes("minimax-h3-mood-trigger"));
        assert.match(moodTrigger.textContent, /Unavailable — future_mood/);
        assert.equal(creativeCommits, 1, "the earlier explicit Visual Language choice is the only commit so far");
        await moodTrigger.dispatch("click");
        const moodSearch = descendants(container).find((element) => element.placeholder === "Search moods…");
        moodSearch.value = "pulp";
        await moodSearch.dispatch("input");
        const moodList = descendants(container).find((element) => element.id === moodTrigger["aria-controls"]);
        const moodOption = moodList.querySelectorAll("[role='option']")[0];
        assert.equal(moodOption.dataset.value, "pulp_heightened");
        assert.match(descendants(moodOption).find((element) => element.tagName === "SMALL").textContent, /without camp/i);
        assert.equal(creativeValues.tone, "future_mood", "opening and searching preserve the unknown stored token");
        assert.equal(creativeCommits, 1, "opening and searching do not write Mood");
        await moodOption.dispatch("click");
        assert.equal(creativeValues.tone, "pulp_heightened");
        assert.equal(creativeCommits, 2, "only an explicit Mood selection commits");
        assert.ok(descendants(container).some((element) => /Mood shapes staging/.test(element.textContent)));

        const exportButton = descendants(container).find((element) => element.textContent === "Export JSON");
        await exportButton.dispatch("click");
        assert.equal(clipboardValue, '{"schemaVersion":1,"name":"Cinema"}');
        const importButton = descendants(container).find((element) => element.textContent === "Import JSON");
        await importButton.dispatch("click");
        assert.match(importedPayload, /"Imported"/);
        const status = descendants(container).find((element) => element.role === "status" && /Imported and applied/.test(element.textContent));
        assert.equal(status["aria-live"], "polite");
    } finally {
        globalThis.document = previousDocument;
        if (navigatorDescriptor) Object.defineProperty(globalThis, "navigator", navigatorDescriptor);
        else delete globalThis.navigator;
    }
});

test("Creative and cinematography are native v2; legacy sources import only on explicit action", async () => {
    assert.deepEqual(STRUCTURED_SCHEMA_VERSIONS, {
        creativeTreatment: 2, shotPlan: 1, cinematography: 2,
    });
    const previousDocument = globalThis.document;
    globalThis.document = { createElement: (tagName) => new FakeElement(tagName), activeElement: null };
    const imports = [];
    const creativeRaw = '{  "schemaVersion": 1, "visualLanguage": "anime_shonen" }';
    const cameraRaw = '{"schemaVersion":1,"cameraMotion":"push_in"}';
    const controller = {
        creativeDocument: () => ({ kind: "v1", raw: creativeRaw, value: JSON.parse(creativeRaw) }),
        cinematographyDocument: () => ({ kind: "v1", raw: cameraRaw, value: JSON.parse(cameraRaw) }),
        creativeFields: () => [],
        cameraFields: () => [],
        creativeValue: () => "none",
        cameraValue: () => "none",
        lookNames: () => [],
        shotDocument: () => ({ kind: "blank", value: { shots: [] } }),
        projectDocument: () => ({ kind: "blank" }),
        diagnostics: () => ({ diagnostics: [] }),
        importCreativeSource: (raw) => { imports.push(["creative", raw]); return { ok: true, fromVersion: 1, schemaVersion: 2 }; },
        importCinematographySource: (raw) => { imports.push(["camera", raw]); return { ok: true, fromVersion: 1, schemaVersion: 2 }; },
    };
    try {
        const container = new FakeElement();
        renderCameraLookTab(container, controller);
        const rendered = descendants(container);
        assert.equal(imports.length, 0, "rendering a v1 source must be observational");
        assert.equal(rendered.some((element) => element.role === "combobox"), false);
        assert.match(rendered.find((element) => /legacy v1 source/.test(element.textContent))?.textContent ?? "", /read-only/);
        const buttons = rendered.filter((element) => element.textContent === "Import v1 as v2");
        assert.equal(buttons.length, 2);
        await buttons[0].dispatch("click");
        await buttons[1].dispatch("click");
        assert.deepEqual(imports, [["creative", creativeRaw], ["camera", cameraRaw]]);
        assert.equal(rendered.filter((element) => element.role === "status").some((element) => /native v2/.test(element.textContent)), true);
    } finally {
        globalThis.document = previousDocument;
    }
});

test("legacy scalar and neutral v1 Creative/Camera sources are semantic blanks without raw clobber", () => {
    const creativeNeutrals = {
        contentFormat: "none", genre: "none", visualLanguage: "none",
        worldAesthetic: "none", tone: "none", titleScreenStyle: "none",
    };
    const cameraNeutrals = {
        colorPalette: "none", cameraMotion: "none", cameraAmplitude: "auto", cameraSpeed: "auto",
    };
    for (const raw of ["false", "null", "  false  "]) {
        const source = { kind: "malformed", raw, value: null, version: null, errors: ["legacy"] };
        const view = nativeStructuredDocumentView(source, creativeNeutrals);
        assert.equal(view.kind, "blank");
        assert.equal(view.raw, raw);
        assert.equal(view.semanticBlank, true);
        assert.equal(source.kind, "malformed", "source state remains untouched");
    }
    const neutralRaw = '{  "schemaVersion": 1, "colorPalette": "none", "cameraMotion": "none", "cameraAmplitude": "auto", "cameraSpeed": "auto" }';
    const neutralSource = { kind: "v1", raw: neutralRaw, version: 1, value: JSON.parse(neutralRaw) };
    const neutralView = nativeStructuredDocumentView(neutralSource, cameraNeutrals);
    assert.equal(neutralView.kind, "blank");
    assert.equal(neutralView.raw, neutralRaw);
    assert.equal(neutralSource.kind, "v1");
    const activeSource = { ...neutralSource, value: { ...neutralSource.value, cameraMotion: "push_in" } };
    assert.equal(nativeStructuredDocumentView(activeSource, cameraNeutrals), activeSource);
});

test("semantic blank Creative/Camera documents mount editors without import tools or hydration writes", () => {
    const previousDocument = globalThis.document;
    globalThis.document = { createElement: (tagName) => new FakeElement(tagName), activeElement: null };
    const writes = [];
    const controller = {
        creativeDocument: () => ({ kind: "blank", raw: "false", semanticBlank: true, sourceKind: "malformed" }),
        cinematographyDocument: () => ({
            kind: "blank", raw: '{"schemaVersion":1,"cameraMotion":"none","cameraAmplitude":"auto","cameraSpeed":"auto"}',
            semanticBlank: true, sourceKind: "v1",
        }),
        creativeFields: () => [["visualLanguage", "Visual language", [["none", "No preference"], ["anime_shonen", "Kinetic action anime"]]]],
        visualLanguageGroups: () => [["Animation", [["anime_shonen", "Kinetic action anime"]]]],
        creativeValue: () => "none",
        commitCreative: (_key, value) => { writes.push(["creative", value]); return true; },
        cameraFields: () => [["cameraMotion", "Camera motion", [["none", "None"], ["push_in", "Push in"]]]],
        cameraValue: () => "none",
        commitCamera: (_key, value) => { writes.push(["camera", value]); return true; },
        lookNames: () => [],
        shotDocument: () => ({ kind: "blank", value: { shots: [] } }),
        projectDocument: () => ({ kind: "blank" }),
        diagnostics: () => ({ diagnostics: [] }),
    };
    try {
        const container = new FakeElement();
        renderCameraLookTab(container, controller);
        const rendered = descendants(container);
        assert.deepEqual(writes, [], "hydration/render must not write legacy raw");
        assert.equal(rendered.some((element) => element.role === "combobox"), true);
        assert.equal(rendered.some((element) => element.textContent === "Import v1 as v2"), false);
        assert.equal(rendered.some((element) => /Import & source tools/.test(element.textContent)), false);
    } finally {
        globalThis.document = previousDocument;
    }
});

test("Resolution budget preview matches Python defaults and aligned custom sizing", () => {
    const cases = [
        ["auto", 0, 1280, 720],
        ["16:9", 0, 1280, 720],
        ["9:16", 0, 720, 1280],
        ["1:1", 0, 1080, 1080],
        ["4:3", 0, 960, 720],
        ["3:4", 0, 720, 960],
        ["21:9", 0, 1680, 720],
        ["16:9", 0.2, 592, 336],
        ["16:9", 0.3, 736, 416],
        ["16:9", 0.5, 944, 528],
        ["16:9", 2, 1888, 1056],
        ["9:16", 0.3, 416, 736],
        ["1:1", 0.5, 704, 704],
    ];
    for (const [ratio, budget, width, height] of cases) {
        const resolution = effectiveH3Resolution(ratio, budget);
        assert.deepEqual([resolution.width, resolution.height], [width, height]);
    }
    assert.equal(formatResolutionLabel(effectiveH3Resolution("16:9", 0)), "1280×720 · 0.92 MP");
    // Exact .5 step with an even lower integer follows Python's ties-to-even.
    assert.deepEqual(
        (({ width, height }) => [width, height])(effectiveH3Resolution("1:1", 1.132096)),
        [1056, 1056],
    );
});
