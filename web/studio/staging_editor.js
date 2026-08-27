import { actionButton, element, field, selectInput } from "./domain_components.js";
import { projectCameraPoint, unprojectCameraPoint } from "./spatial_camera_editor.js";
import { sourcePreviewUrl } from "./reference_sources.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const FACING = [
    ["camera", "Camera"], ["travel", "Direction of travel"],
    ["frame_left", "Frame left"], ["frame_right", "Frame right"],
    ["away_from_camera", "Away from camera"], ["target", "Another subject"],
];
const MOVEMENT = [
    ["holds", "Holds position"], ["walks", "Walks"], ["runs", "Runs"],
    ["crosses", "Crosses frame"], ["approaches", "Approaches"],
    ["withdraws", "Moves away"], ["circles", "Circles"],
];

function svgNode(tag, attributes = {}, text = "") {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    if (text) node.textContent = text;
    return node;
}

export function defaultSubjectPlacement(subjectId, index = 0, count = 1) {
    const spread = count <= 1 ? 0 : -0.55 + (1.1 * index / (count - 1));
    return { subjectId, start: { x: spread, y: 0, z: 0, facing: "camera" } };
}

export function stagingPreview(staging = [], subjects = []) {
    const names = new Map(subjects.map((subject) => [subject.id, subject.name || subject.id]));
    if (!staging.length) return "No subject positions have been directed for this shot.";
    const zone = (point) => {
        const horizontal = point.x <= -.2 ? "frame left" : point.x >= .2 ? "frame right" : "frame center";
        const depth = point.z <= -.35 ? "background" : point.z >= .35 ? "foreground" : "midground";
        return `${horizontal}, ${depth}`;
    };
    return staging.map((item) => {
        const name = names.get(item.subjectId) || item.subjectId;
        if (!item.end) return `${name} holds at ${zone(item.start)}.`;
        return `${name} ${item.movement || "moves"} from ${zone(item.start)} to ${zone(item.end)}.`;
    }).join(" ");
}

function renderStage(stage, staging, subjects, phase, view, selectedId, selectSubject, commit, rerender, sources = {}) {
    const svg = svgNode("svg", { viewBox: "0 0 360 260", role: "img", "aria-label": `${phase} subject staging, ${view} view` });
    svg.append(
        svgNode("rect", { x: 28, y: 22, width: 304, height: 216, rx: 16, class: "minimax-h3-stage-floor" }),
        svgNode("line", { x1: 180, y1: 23, x2: 180, y2: 237, class: "minimax-h3-stage-grid" }),
        svgNode("line", { x1: 29, y1: 122, x2: 331, y2: 122, class: "minimax-h3-stage-grid" }),
        svgNode("text", { x: 40, y: 43, class: "minimax-h3-stage-axis" }, "FRAME LEFT"),
        svgNode("text", { x: 320, y: 43, "text-anchor": "end", class: "minimax-h3-stage-axis" }, "FRAME RIGHT"),
        svgNode("text", { x: 180, y: 229, "text-anchor": "middle", class: "minimax-h3-stage-axis" }, view === "front" ? "LOW" : "FOREGROUND"),
        svgNode("text", { x: 180, y: 39, "text-anchor": "middle", class: "minimax-h3-stage-axis" }, view === "front" ? "HIGH" : "BACKGROUND"),
    );
    const subjectMap = new Map(subjects.map((subject) => [subject.id, subject]));
    for (const item of staging) {
        const point = phase === "end" && item.end ? item.end : item.start;
        if (item.end) {
            const start = projectCameraPoint(item.start, view);
            const end = projectCameraPoint(item.end, view);
            svg.appendChild(svgNode("line", { x1: start.x, y1: start.y, x2: end.x, y2: end.y, class: "minimax-h3-stage-movement" }));
        }
        const projected = projectCameraPoint(point, view);
        const group = svgNode("g", { class: `minimax-h3-stage-subject${selectedId === item.subjectId ? " is-selected" : ""}`, tabindex: "0", role: "button", "aria-label": `${subjectMap.get(item.subjectId)?.name || item.subjectId}, ${phase} position` });
        const subject = subjectMap.get(item.subjectId);
        const identityAssetId = subject?.identityAssetIds?.[0];
        const previewUrl = sourcePreviewUrl(sources[identityAssetId]);
        const circle = svgNode("circle", { cx: projected.x, cy: projected.y, r: 22 });
        const portrait = previewUrl ? svgNode("image", {
            href: previewUrl, x: projected.x - 20, y: projected.y - 20, width: 40, height: 40,
            preserveAspectRatio: "xMidYMid slice", class: "minimax-h3-stage-portrait",
        }) : null;
        const label = svgNode("text", {
            x: projected.x, y: projected.y + (portrait ? 34 : 5), "text-anchor": "middle",
            class: portrait ? "minimax-h3-stage-subject-name" : "",
        }, (subject?.name || item.subjectId).slice(0, 12));
        group.append(circle);
        if (portrait) group.appendChild(portrait);
        group.appendChild(label);
        group.addEventListener("click", () => selectSubject(item.subjectId));
        group.addEventListener("keydown", (event) => {
            if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
            event.preventDefault();
            const delta = event.shiftKey ? .1 : .04;
            const screen = { x: projected.x + (event.key === "ArrowLeft" ? -delta * 210 : event.key === "ArrowRight" ? delta * 210 : 0), y: projected.y + (event.key === "ArrowUp" ? -delta * 140 : event.key === "ArrowDown" ? delta * 140 : 0) };
            Object.assign(point, unprojectCameraPoint(screen, point, view)); commit(); rerender();
        });
        group.addEventListener("pointerdown", (event) => {
            event.preventDefault(); selectSubject(item.subjectId); circle.setPointerCapture?.(event.pointerId);
            const rect = svg.getBoundingClientRect();
            const move = (moveEvent) => {
                const screen = { x: (moveEvent.clientX - rect.left) * 360 / rect.width, y: (moveEvent.clientY - rect.top) * 260 / rect.height };
                Object.assign(point, unprojectCameraPoint(screen, point, view));
                const next = projectCameraPoint(point, view); circle.setAttribute("cx", next.x); circle.setAttribute("cy", next.y);
                if (portrait) { portrait.setAttribute("x", next.x - 20); portrait.setAttribute("y", next.y - 20); }
                label.setAttribute("x", next.x); label.setAttribute("y", next.y + (portrait ? 34 : 5));
            };
            const up = () => { globalThis.removeEventListener?.("pointermove", move); globalThis.removeEventListener?.("pointerup", up); commit(); rerender(); };
            globalThis.addEventListener?.("pointermove", move); globalThis.addEventListener?.("pointerup", up, { once: true });
        });
        svg.appendChild(group);
    }
    stage.appendChild(svg);
}

export function renderStagingEditor(container, shot, project, commit, rerender, state = {}, sources = {}) {
    shot.staging ??= [];
    const staging = shot.staging;
    const declared = new Set((shot.subjects ?? []).filter((item) => item.presence !== "absent").map((item) => item.subjectId));
    const subjects = (project.subjects ?? []).filter((subject) => !declared.size || declared.has(subject.id));
    const selected = staging.find((item) => item.subjectId === state.stagingSubjectId) ?? staging[0];
    state.stagingSubjectId = selected?.subjectId ?? null;
    state.stagingPhase ??= "start"; state.stagingView ??= "perspective";
    if (state.stagingPhase === "end" && selected && !selected.end) state.stagingPhase = "start";

    const toolbar = element("div", "minimax-h3-staging-toolbar");
    const subjectPicker = selectInput(state.stagingSubjectId ?? "", [["", "Select staged subject…"], ...staging.map((item) => {
        const subject = subjects.find((candidate) => candidate.id === item.subjectId);
        return [item.subjectId, subject?.name || item.subjectId];
    })]);
    subjectPicker.addEventListener("change", () => { state.stagingSubjectId = subjectPicker.value; rerender(); });
    const phase = selectInput(state.stagingPhase, [["start", "Start positions"], ["end", "End positions"]]);
    phase.addEventListener("change", () => { state.stagingPhase = phase.value; rerender(); });
    const view = selectInput(state.stagingView, [["perspective", "3D view"], ["top", "Top view"], ["front", "Front view"]]);
    view.addEventListener("change", () => { state.stagingView = view.value; rerender(); });
    toolbar.append(field("Subject", subjectPicker), field("Phase", phase), field("View", view));
    container.appendChild(toolbar);

    const stage = element("div", "minimax-h3-staging-stage");
    renderStage(stage, staging, subjects, state.stagingPhase, state.stagingView, state.stagingSubjectId, (id) => { state.stagingSubjectId = id; rerender(); }, commit, rerender, sources);
    container.appendChild(stage);

    if (selected) {
        const inspector = element("section", "minimax-h3-staging-inspector");
        const name = subjects.find((item) => item.id === selected.subjectId)?.name || selected.subjectId;
        inspector.appendChild(element("h3", "", name));
        const movement = selectInput(selected.movement || "holds", MOVEMENT);
        movement.addEventListener("change", () => {
            selected.movement = movement.value;
            if (movement.value === "holds") { delete selected.end; delete selected.movement; state.stagingPhase = "start"; }
            else selected.end ??= { ...selected.start };
            commit(); rerender();
        });
        const activePoint = state.stagingPhase === "end" && selected.end ? selected.end : selected.start;
        const facing = selectInput(activePoint.facing || "camera", FACING);
        facing.addEventListener("change", () => {
            activePoint.facing = facing.value;
            if (facing.value === "target") {
                const other = subjects.find((item) => item.id !== selected.subjectId);
                if (other) activePoint.facingTarget = { kind: "subject", id: other.id }; else activePoint.facing = "camera";
            } else delete activePoint.facingTarget;
            commit(); rerender();
        });
        inspector.append(field("Movement", movement), field("Facing", facing));
        if (activePoint.facing === "target") {
            const target = selectInput(activePoint.facingTarget?.id || "", subjects.filter((item) => item.id !== selected.subjectId).map((item) => [item.id, item.name || item.id]));
            target.addEventListener("change", () => { activePoint.facingTarget = { kind: "subject", id: target.value }; commit(); rerender(); });
            inspector.appendChild(field("Facing subject", target));
        }
        const remove = actionButton("Remove from staging", () => {
            shot.staging.splice(shot.staging.indexOf(selected), 1); state.stagingSubjectId = shot.staging[0]?.subjectId ?? null;
            if (!shot.staging.length) delete shot.staging; commit(); rerender();
        });
        remove.className += " minimax-h3-button-danger"; inspector.appendChild(remove); container.appendChild(inspector);
    }
    const remaining = subjects.filter((subject) => !staging.some((item) => item.subjectId === subject.id));
    if (remaining.length) container.appendChild(actionButton("Add subject to staging", () => {
        const item = defaultSubjectPlacement(remaining[0].id, staging.length, staging.length + 1); shot.staging ??= []; shot.staging.push(item); state.stagingSubjectId = item.subjectId; commit(); rerender();
    }));
    const preview = element("output", "minimax-h3-staging-preview");
    preview.append(element("strong", "", "What H3 receives"), element("span", "", stagingPreview(staging, project.subjects ?? [])));
    container.appendChild(preview);
}
