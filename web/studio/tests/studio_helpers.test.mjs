import assert from "node:assert/strict";
import test from "node:test";

import { dashboardSummaries } from "../drawer.js";
import { groupDiagnostics } from "../tab_coach.js";
import { physicalLabel } from "../tab_references.js";
import { SHOT_ROW_HEIGHT, shotRowModel, visibleShotRange } from "../tab_shots.js";

test("64-shot virtualization mounts only visible rows plus ten overscan rows", () => {
    for (const scrollTop of [0, SHOT_ROW_HEIGHT * 8, SHOT_ROW_HEIGHT * 50]) {
        const viewport = SHOT_ROW_HEIGHT * 10;
        const range = visibleShotRange(scrollTop, viewport, 64);
        assert.ok(range.start >= 0);
        assert.ok(range.end <= 64);
        assert.ok(range.end - range.start <= 20);
    }
});

test("shot list summaries separate title, timing, generation and full accessible action", () => {
    const action = "A deliberately long action summary that should end in a visual ellipsis without losing its accessible text";
    const model = shotRowModel({ generationId: "generation-with-a-long-id", action }, 0, "auto", 0);
    assert.deepEqual(model, {
        title: "Shot 1",
        timing: "Auto",
        generation: "generation-with-a-long-id",
        action,
        accessibleLabel: `Shot 1, automatic timing, generation generation-with-a-long-id. ${action}`,
    });
    assert.equal(shotRowModel({ generationId: "g1", action: "Move" }, 2, "exact", 4.5).timing, "4.50s");
});

test("physical reference labels derive from type and per-generation slot", () => {
    assert.equal(physicalLabel({ type: "picture" }, { slotIndex: 2 }), "<Picture 2>");
    assert.equal(physicalLabel({ type: "video" }, { slotIndex: 1 }), "<Video 1>");
    assert.equal(physicalLabel({ type: "audio" }, { slotIndex: 3 }), "<Audio 3>");
});

test("coach groups repeated stable codes without reimplementing heuristics", () => {
    const groups = groupDiagnostics([{ code: "coach.action.weak" }, { code: "coach.action.weak" }, { code: "camera.missing" }]);
    assert.deepEqual(groups.map((group) => [group.code, group.items.length]), [["coach.action.weak", 2], ["camera.missing", 1]]);
});

test("dashboard summaries use canonical widget documents", () => {
    const summary = dashboardSummaries({
        shotDocument: () => ({ value: { shots: [{}, {}] } }),
        projectDocument: () => ({ value: { subjects: [{}], environments: [{}, {}], assets: [{}, {}, {}], generations: [{ bindings: [{}, {}] }] } }),
        diagnostics: () => ({ diagnostics: [{}, {}, {}, {}] }),
    });
    assert.deepEqual(summary, { shots: 2, subjects: 1, environments: 2, assets: 3, active: 2, diagnostics: 4 });
});
