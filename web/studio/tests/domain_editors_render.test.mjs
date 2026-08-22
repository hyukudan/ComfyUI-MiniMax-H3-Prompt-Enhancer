import assert from "node:assert/strict";
import test from "node:test";

import { renderEnvironmentsTab } from "../tab_environments.js";
import { renderCameraTab } from "../tab_camera.js";
import { renderShotsTab } from "../tab_shots.js";
import { renderSubjectsTab } from "../tab_subjects.js";
import { createWidgetStore } from "../widget_store.js";

class TestElement {
    constructor(tagName) {
        this.tagName = tagName.toUpperCase();
        this.children = [];
        this.attributes = new Map();
        this.dataset = {};
        this.style = {};
        this.listeners = new Map();
        this.className = "";
        this.value = "";
        this.checked = false;
        this.disabled = false;
        this.scrollTop = 0;
        this.clientHeight = 440;
        this._text = "";
    }
    set textContent(value) { this._text = String(value ?? ""); this.children = []; }
    get textContent() { return this._text + this.children.map((child) => child.textContent ?? "").join(""); }
    append(...children) { for (const child of children) this.appendChild(child); }
    appendChild(child) { if (child === undefined || child === null) return child; child.parentElement = this; this.children.push(child); return child; }
    replaceChildren(...children) { for (const child of this.children) child.parentElement = null; this.children = []; this._text = ""; this.append(...children); }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    removeAttribute(name) { this.attributes.delete(name); }
    addEventListener(name, listener) { const listeners = this.listeners.get(name) ?? []; listeners.push(listener); this.listeners.set(name, listeners); }
    remove() { if (!this.parentElement) return; this.parentElement.children = this.parentElement.children.filter((child) => child !== this); this.parentElement = null; }
    click() { for (const listener of this.listeners.get("click") ?? []) listener({ preventDefault() {} }); }
    focus() {}
    querySelector(selector) {
        for (const child of this.children) {
            if (matches(child, selector)) return child;
            const nested = child.querySelector?.(selector);
            if (nested) return nested;
        }
        return null;
    }
}

function findByText(root, text) {
    if (root.textContent === text) return root;
    for (const child of root.children ?? []) {
        const match = findByText(child, text);
        if (match) return match;
    }
    return null;
}

function findByClass(root, className) {
    if (String(root.className ?? "").split(/\s+/).includes(className)) return root;
    for (const child of root.children ?? []) {
        const match = findByClass(child, className);
        if (match) return match;
    }
    return null;
}

function findField(root, label) {
    if (root.className === "minimax-h3-studio-field" && root.children?.[0]?.textContent === label) return root;
    for (const child of root.children ?? []) {
        const match = findField(child, label);
        if (match) return match;
    }
    return null;
}

function dispatch(element, eventName) {
    for (const listener of element.listeners.get(eventName) ?? []) listener({ preventDefault() {} });
}

function matches(element, selector) {
    if (selector === "[data-target-value]") return element.dataset.targetValue !== undefined;
    if (selector === "[data-shot-action]") return element.dataset.shotAction !== undefined;
    return false;
}

globalThis.document = { createElement: (tagName) => new TestElement(tagName) };

const project = {
    schemaVersion: 2,
    mode: "chained_multishot",
    assets: [
        { id: "portrait", type: "picture", name: "Portrait", available: true },
        { id: "move", type: "video", name: "Move", available: true, cameraTransfer: { enabled: true, role: "camera_reference", aspects: ["motion", "framing"] } },
    ],
    subjects: [{
        id: "marta", h3Index: 1, name: "Marta", description: "Stable identity", identityAssetIds: ["portrait"], baseAppearanceStateId: "base",
        appearanceStates: [{ id: "base", name: "Base", controls: [], attributes: {} }, { id: "wet", name: "Wet coat", controls: ["wardrobe", "wetness"], attributes: { wardrobe: "Wet coat", wetness: "Soaked" }, source: { mode: "asset", assetId: "portrait" } }],
    }],
    environments: [{
        id: "alley", name: "Alley", permanent: { geography: "Old quarter", architecture: "Brick", scale: "Narrow", fixedElements: ["Lamp"] },
        views: [{ id: "wide", name: "Wide", role: "overview", assetId: "portrait" }], defaultStateId: "day",
        states: [{ id: "day", name: "Day", temporary: {} }, { id: "night", name: "Night", temporary: { lighting: "Low key", temporaryElements: ["Puddles"] } }],
    }],
    generations: [{
        id: "g1", order: 1, activation: { mode: "auto" }, bindings: [{ assetId: "portrait", slotIndex: 1 }, { assetId: "move", slotIndex: 1 }],
        subjectStates: [{ subjectId: "marta", policy: "explicit", stateId: "base" }], environmentStates: [{ environmentId: "alley", policy: "explicit", stateId: "day", viewIds: ["wide"] }],
    }],
};

const plan = {
    schemaVersion: 2,
    timingMode: "exact",
    shots: [{
        id: "s1", generationId: "g1", openingState: "Marta waits", action: "Rain begins", durationSeconds: 4, transitionIn: "cut",
        cutContext: { timeRelation: "continuous", purpose: "state" }, subjectPresenceComplete: true,
        subjects: [{ subjectId: "marta", presence: "present", blocking: "Foreground" }], environment: { environmentId: "alley", viewIds: ["wide"] },
        referenceUses: [{ assetId: "move", role: "camera_transfer", cameraAspects: ["motion", "framing"], targetIds: ["marta"] }],
        cameraStart: { framing: "medium", composition: "rule_of_thirds", focus: { mode: "single_target", primaryTarget: { kind: "subject", id: "marta" } } },
        cameraEnd: { framing: "close_up", distance: "near" }, cameraPath: { motionType: "push_in", amplitude: "small", speed: "slow", easing: "ease_in", timing: "during_action" },
        appearanceTransitions: [{ subjectId: "marta", fromStateId: "base", toStateId: "wet", timing: "during_shot" }],
        environmentTransitions: [{ environmentId: "alley", fromStateId: "day", toStateId: "night", timing: "at_end" }],
    }],
};

function controllerFixture() {
    let writes = 0;
    return {
        shotUiState: { selectedId: "s1", plan: null },
        projectUiState: { sourceRaw: null, project: null },
        shotDocument: () => ({ kind: "v2", raw: JSON.stringify(plan), value: structuredClone(plan) }),
        projectDocument: () => ({ kind: "v2", raw: JSON.stringify(project), value: structuredClone(project) }),
        generationIds: () => ["g1"],
        cameraFields: () => [["shotScale"], ["cameraMotion"]],
        cameraValue: (key) => key === "shotScale" ? "wide" : "static",
        commitShotPlan: () => { writes += 1; return true; },
        commitProject: () => { writes += 1; return true; },
        get writes() { return writes; },
    };
}

for (const [name, render] of [["Shots", renderShotsTab], ["Subjects", renderSubjectsTab], ["Environments", renderEnvironmentsTab]]) {
    test(`${name} populated editor mounts without writes or runtime errors`, () => {
        const controller = controllerFixture();
        const container = new TestElement("section");
        render(container, controller);
        assert.equal(controller.writes, 0);
        assert.ok(container.children.length > 0);
        assert.doesNotMatch(container.textContent, /JSON array|comma-separated|Picture asset ID/);
        if (name === "Shots") {
            for (const label of ["Opening state", "Full presence declared", "Edit camera", "Appearance changes", "Environment changes"]) {
                assert.match(container.textContent, new RegExp(label));
            }
        } else {
            assert.match(container.textContent, /Cannot delete|Used by/);
        }
    });
}

test("Camera mounts the selected shot planner and precise controls without hydration writes", () => {
    const controller = controllerFixture();
    const container = new TestElement("section");
    renderCameraTab(container, controller);
    assert.equal(controller.writes, 0);
    for (const label of ["Shot camera", "Shot 1", "Visual camera planner", "Precise camera controls", "Camera start", "Camera end", "Composition", "Focus"]) {
        assert.match(container.textContent, new RegExp(label));
    }
});

test("Shots renders legacy boolean/null as an untouched empty plan and first edit writes v2", () => {
    for (const source of [false, true, "false", "true", " null "]) {
        const widget = { value: source };
        const store = createWidgetStore(widget, {
            supportedVersions: [1, 2],
            allowLegacyBlankScalars: true,
        });
        let writes = 0;
        const controller = {
            shotUiState: { selectedId: null, plan: null },
            projectUiState: { sourceRaw: null, project: null },
            shotDocument: () => store.document,
            projectDocument: () => ({ kind: "blank", raw: "", value: null }),
            generationIds: () => ["g1"],
            cameraFields: () => [],
            cameraValue: () => "none",
            commitShotPlan: (raw) => store.commit(raw, (value) => {
                writes += 1;
                widget.value = value;
                return true;
            }),
        };
        const container = new TestElement("section");
        renderShotsTab(container, controller);

        assert.equal(writes, 0);
        assert.equal(widget.value, source);
        assert.match(container.textContent, /No shots yet/);
        assert.doesNotMatch(container.textContent, /raw shot plan|malformed|JSON/);

        const add = findByText(container, "+ Add shot");
        assert.ok(add);
        add.click();
        const saved = JSON.parse(widget.value);
        assert.equal(writes, 1);
        assert.equal(saved.schemaVersion, 2);
        assert.equal(saved.shots.length, 1);
    }
});

test("renaming a subject patches its master card without rerendering or duplicate commits", () => {
    const controller = controllerFixture();
    const container = new TestElement("section");
    renderSubjectsTab(container, controller);

    const originalGrid = container.children[1];
    const originalMasterRow = originalGrid.children[0].children[0];
    const name = findField(container, "Name").children[1];
    name.value = "Marta renamed";
    dispatch(name, "input");

    assert.equal(controller.writes, 0);
    assert.equal(container.children[1], originalGrid);
    assert.equal(originalMasterRow.children[0].textContent, "Marta renamed");

    dispatch(name, "change");

    assert.equal(controller.writes, 1);
    assert.equal(container.children[1], originalGrid);
    assert.equal(originalMasterRow.children[0].textContent, "Marta renamed");
});

test("rendered shot rows keep compact metadata separate from the full accessible action", () => {
    const container = new TestElement("section");
    renderShotsTab(container, controllerFixture());
    const row = findByClass(container, "minimax-h3-virtual-row");
    assert.ok(row);
    assert.equal(row.children.length, 2);
    assert.match(row.children[0].textContent, /Shot 1.*0\.00s.*g1/);
    assert.equal(row.children[1].textContent, "Rain begins");
    assert.equal(row.children[1].attributes.get("title"), "Rain begins");
    assert.match(row.attributes.get("aria-label"), /Shot 1, starts at 0\.00s, generation g1\. Rain begins/);
});
