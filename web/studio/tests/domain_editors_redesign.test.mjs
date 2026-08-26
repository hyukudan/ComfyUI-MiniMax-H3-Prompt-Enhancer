import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { cameraProvenance, resolveEntryStates, slotCapacity, usageIndex } from "../derive.js";
import { commitProject, editableProject, projectForController } from "../project_editor.js";
import { editableShotPlan, parseMediaProject, parseStructuredJson } from "../schema.js";
import { createWidgetStore } from "../widget_store.js";
import { setSubjectGenerationPromptUse } from "../tab_subjects.js";

const project = {
    schemaVersion: 2,
    mode: "chained_multishot",
    assets: [
        { id: "portrait", type: "picture", name: "Portrait" },
        { id: "move", type: "video", name: "Move", cameraTransfer: { enabled: true, role: "camera_reference", aspects: ["motion", "framing"] } },
    ],
    subjects: [{
        id: "marta", h3Index: 1, name: "Marta", description: "Stable identity", identityAssetIds: ["portrait"],
        baseAppearanceStateId: "base", appearanceStates: [
            { id: "base", name: "Base", controls: [] },
            { id: "wet", name: "Wet coat", controls: ["wardrobe", "wetness"] },
        ],
    }],
    environments: [{
        id: "alley", name: "Alley", permanent: {}, defaultStateId: "day",
        views: [{ id: "wide", name: "Wide", role: "overview", assetId: "portrait" }],
        states: [{ id: "day", name: "Day" }, { id: "night", name: "Night" }],
    }],
    generations: [
        { id: "g1", order: 1, activation: { mode: "auto" }, bindings: [{ assetId: "portrait", slotIndex: 1 }], subjectStates: [{ subjectId: "marta", policy: "explicit", stateId: "base" }], environmentStates: [{ environmentId: "alley", policy: "explicit", stateId: "day", viewIds: ["wide"] }] },
        { id: "g2", order: 2, activation: { mode: "auto" }, bindings: [{ assetId: "move", slotIndex: 1 }], subjectStates: [{ subjectId: "marta", policy: "carry" }], environmentStates: [{ environmentId: "alley", policy: "carry", viewIds: [] }] },
    ],
};

const plan = {
    schemaVersion: 2,
    timingMode: "auto",
    shots: [
        { id: "s1", generationId: "g1", action: "Rain starts", subjects: [{ subjectId: "marta", presence: "present" }], environment: { environmentId: "alley", viewIds: ["wide"] }, appearanceTransitions: [{ subjectId: "marta", fromStateId: "base", toStateId: "wet", timing: "during_shot" }] },
        { id: "s2", generationId: "g2", action: "Camera follows", cameraStart: { framing: "medium" }, referenceUses: [{ assetId: "move", role: "camera_transfer", cameraAspects: ["motion", "framing"] }] },
    ],
};

test("subject prompt use manages explicit generation roots without touching unrelated roots", () => {
    const generation = { activation: { mode: "auto", exclude: [{ kind: "asset", id: "unused" }] } };
    assert.equal(setSubjectGenerationPromptUse(generation, "juan", true), true);
    assert.deepEqual(generation.activation, {
        mode: "explicit",
        roots: [{ kind: "subject", id: "juan" }],
        exclude: [{ kind: "asset", id: "unused" }],
    });
    generation.activation.roots.push({ kind: "environment", id: "plaza" });
    assert.equal(setSubjectGenerationPromptUse(generation, "juan", false), true);
    assert.deepEqual(generation.activation.roots, [{ kind: "environment", id: "plaza" }]);
    assert.equal(setSubjectGenerationPromptUse(generation, "juan", false), false);
});

test("legacy media manifests remain read-only until an external v2 source replaces them", () => {
    const legacy = { kind: "v1", raw: '[{"type":"image"}]', value: [{ type: "image" }] };
    assert.equal(editableProject(legacy), null);
    const controller = { projectUiState: { sourceRaw: null, project: null }, projectDocument: () => legacy };
    assert.equal(projectForController(controller), null);
    assert.equal(controller.projectUiState.sourceRaw, legacy.raw);
});

test("blank media state creates a new v2 draft without committing during hydration", () => {
    const blank = editableProject({ kind: "blank", raw: "", value: null });
    assert.equal(blank.schemaVersion, 2);
    assert.equal(blank.generations[0].id, "g1");
});

test("legacy boolean/null shot storage is semantic blank without hydration writes", () => {
    for (const raw of ["false", "False", "true", "True", " null ", "None"]) {
        const widget = { value: raw };
        const store = createWidgetStore(widget, {
            supportedVersions: [1, 2],
            allowLegacyBlankScalars: true,
        });
        let writes = 0;
        store.hydrate();
        assert.equal(store.document.kind, "blank");
        assert.equal(store.document.raw, raw);
        assert.equal(widget.value, raw);
        assert.equal(writes, 0);
        assert.deepEqual(editableShotPlan(store.document), {
            schemaVersion: 2,
            timingMode: "auto",
            shots: [],
        });
    }
});

test("legacy blank scalar compatibility stays opt-in and does not relax malformed or future shots", () => {
    for (const raw of ["false", "null"]) {
        assert.equal(parseStructuredJson(raw, { supportedVersions: [1, 2] }).kind, "malformed");
    }
    for (const raw of ["0", '"false"', "[]", '{"schemaVersion":99,"shots":[]}']) {
        assert.notEqual(parseStructuredJson(raw, {
            supportedVersions: [1, 2],
            allowLegacyBlankScalars: true,
        }).kind, "blank");
    }
    assert.equal(parseMediaProject("false").kind, "malformed");
    assert.equal(parseMediaProject("null").kind, "malformed");
});

test("successive field commits keep the live project identity and include earlier edits", () => {
    const live = structuredClone(project);
    const writes = [];
    const controller = { projectUiState: { sourceRaw: "source", project: live }, commitProject: (raw) => { writes.push(raw); return true; } };
    live.subjects[0].name = "Marta R.";
    commitProject(controller);
    live.subjects[0].description = "Stable identity, green eyes";
    commitProject(controller);
    assert.equal(controller.projectUiState.project, live);
    assert.equal(JSON.parse(writes.at(-1)).subjects[0].name, "Marta R.");
    assert.equal(JSON.parse(writes.at(-1)).subjects[0].description, "Stable identity, green eyes");
});

test("usage guards include generation, shot, view, state and camera target relationships", () => {
    const uses = usageIndex(project, plan);
    assert.match(uses.subjects.get("marta").join(" "), /Shot 1/);
    assert.match(uses.appearanceStates.get("marta:wet").join(" "), /transition end/);
    assert.match(uses.environments.get("alley").join(" "), /Shot 1/);
    assert.match(uses.environmentViews.get("alley:wide").join(" "), /initial view|Shot 1/);
    assert.match(uses.assets.get("portrait").join(" "), /Identity/);
    assert.match(uses.assets.get("move").join(" "), /Shot 2 .*reference/);
});

test("entry states carry transition results across generation boundaries", () => {
    const resolved = resolveEntryStates(project, plan);
    assert.equal(resolved.byShot.get("s1").subjects.marta, "base");
    assert.equal(resolved.generationFinal.get("g1").subjects.marta, "wet");
    assert.equal(resolved.byShot.get("s2").subjects.marta, "wet");
    assert.equal(resolved.byShot.get("s2").environments.alley, "day");
});

test("camera provenance distinguishes ordinary inheritance from explicit media conflicts", () => {
    const provenance = cameraProvenance(plan, { shotScale: "wide", cameraMotion: "static" }, project).get("s2");
    assert.equal(provenance.start.framing.owner, "conflict");
    assert.equal(provenance.end.framing.owner, "inherited");
    assert.equal(provenance.path.motion.owner, "media");
});

test("slot capacity counts physical picture, video and soundtrack allocations", () => {
    const generation = { bindings: [{ assetId: "portrait", slotIndex: 1 }, { assetId: "move", slotIndex: 2, soundtrackSlotIndex: 1 }] };
    assert.deepEqual(slotCapacity(generation, project.assets), {
        picture: { used: 1, maximum: 9 }, video: { used: 1, maximum: 3 }, audio: { used: 1, maximum: 3 },
    });
});

test("normal domain editing routes no longer expose JSON or hand-written relationship IDs", async () => {
    const sources = await Promise.all(["tab_shots.js", "tab_subjects.js", "tab_environments.js"].map((name) => readFile(new URL(`../${name}`, import.meta.url), "utf8")));
    const normalUi = sources.join("\n").replace(/function readOnlyShotPlan[\s\S]*?function nextShotId/, "function nextShotId");
    assert.doesNotMatch(normalUi, /\(JSON|comma-separated|Picture asset ID|Identity asset IDs/);
});
