import { actionButton, element, selectInput } from "./domain_components.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const VIEW_STATE = new Map();
const SHAPES = [["smooth", "Smooth"], ["straight", "Straight"], ["arc_left", "Arc left"], ["arc_right", "Arc right"]];
const SPACES = [["subject", "Around subject"], ["scene", "In scene"]];

function clamp(value, minimum = -1, maximum = 1) {
    return Math.max(minimum, Math.min(maximum, Number(value)));
}

function round(value) { return Math.round(Number(value) * 100) / 100; }

function svgNode(tag, attributes = {}, text = "") {
    const node = document.createElementNS?.(SVG_NS, tag) ?? document.createElement(tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    if (text) node.textContent = text;
    return node;
}

export function defaultSpatialWaypoints() {
    return [
        { id: "cam1", at: 0, x: -0.72, y: 0.08, z: 0.62, framing: "wide" },
        { id: "cam2", at: 1, x: 0.42, y: 0.04, z: -0.38, framing: "medium" },
    ];
}

export function normalizeSpatialWaypoints(value) {
    if (!Array.isArray(value) || value.length < 2) return defaultSpatialWaypoints();
    return value.slice(0, 6).map((point, index, all) => ({
        ...point,
        id: String(point?.id || `cam${index + 1}`),
        at: index === 0 ? 0 : index === all.length - 1 ? 1 : round(clamp(point?.at, 0.01, 0.99)),
        x: round(clamp(point?.x)), y: round(clamp(point?.y)), z: round(clamp(point?.z)),
    })).sort((a, b) => a.at - b.at);
}

export function projectCameraPoint(point, view = "perspective") {
    if (view === "top") return { x: 180 + point.x * 126, y: 122 + point.z * 82 };
    return { x: 180 + point.x * 116, y: 137 - point.y * 72 + point.z * 44 };
}

export function unprojectCameraPoint(screen, point, view = "perspective") {
    if (view === "top") return { ...point, x: round(clamp((screen.x - 180) / 126)), z: round(clamp((screen.y - 122) / 82)) };
    return { ...point, x: round(clamp((screen.x - 180) / 116)), z: round(clamp((screen.y - 137 + point.y * 72) / 44)) };
}

export function spatialPathD(waypoints, view = "perspective", shape = "smooth") {
    const points = waypoints.map((point) => projectCameraPoint(point, view));
    if (!points.length) return "";
    if (shape === "straight" || points.length < 3) return points.map((point, index) => `${index ? "L" : "M"} ${round(point.x)} ${round(point.y)}`).join(" ");
    let result = `M ${round(points[0].x)} ${round(points[0].y)}`;
    for (let index = 1; index < points.length; index += 1) {
        const previous = points[index - 1]; const point = points[index];
        const bend = shape === "arc_left" ? -24 : shape === "arc_right" ? 24 : 0;
        const cx = (previous.x + point.x) / 2 + bend;
        const cy = (previous.y + point.y) / 2 - (shape === "smooth" ? 10 : 0);
        result += ` Q ${round(cx)} ${round(cy)} ${round(point.x)} ${round(point.y)}`;
    }
    return result;
}

export function interpolateSpatialWaypoint(waypoints, progress) {
    const points = normalizeSpatialWaypoints(waypoints);
    const at = clamp(progress, 0, 1);
    const rightIndex = points.findIndex((point) => point.at >= at);
    if (rightIndex <= 0) return { ...points[0] };
    const right = points[rightIndex]; const left = points[rightIndex - 1];
    const span = right.at - left.at || 1; const mix = (at - left.at) / span;
    return {
        at,
        x: left.x + (right.x - left.x) * mix,
        y: left.y + (right.y - left.y) * mix,
        z: left.z + (right.z - left.z) * mix,
    };
}

export function addSpatialWaypoint(waypoints, selectedIndex = 0) {
    if (waypoints.length >= 6) return waypoints;
    const left = waypoints[selectedIndex] ?? waypoints[waypoints.length - 2];
    const right = waypoints[selectedIndex + 1] ?? waypoints[waypoints.length - 1];
    const next = { id: `cam${Date.now().toString(36)}`, at: round((left.at + right.at) / 2), x: round((left.x + right.x) / 2), y: round((left.y + right.y) / 2), z: round((left.z + right.z) / 2) };
    return [...waypoints, next].sort((a, b) => a.at - b.at);
}

function grid(svg, view) {
    if (view === "top") {
        for (let x = 54; x <= 306; x += 42) svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-grid", d: `M ${x} 38 L ${x} 206` }));
        for (let y = 38; y <= 206; y += 28) svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-grid", d: `M 54 ${y} L 306 ${y}` }));
        return;
    }
    for (let index = -5; index <= 5; index += 1) svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-grid", d: `M 180 62 L ${180 + index * 31} 210` }));
    for (let index = 0; index < 7; index += 1) {
        const y = 82 + index * 21; const width = 34 + index * 21;
        svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-grid", d: `M ${180 - width} ${y} L ${180 + width} ${y}` }));
    }
}

function slider(label, value, minimum, maximum, step, onInput) {
    const root = element("label", "minimax-h3-spatial-slider");
    const heading = element("span", ""); const output = element("output", "", String(value));
    heading.append(element("span", "", label), output);
    const input = document.createElement("input"); input.type = "range"; input.min = String(minimum); input.max = String(maximum); input.step = String(step); input.value = String(value);
    input.setAttribute("aria-label", label);
    input.addEventListener("input", () => { output.value = input.value; output.textContent = input.value; onInput(Number(input.value), false); });
    input.addEventListener("change", () => onInput(Number(input.value), true));
    root.append(heading, input); return root;
}

function ensurePath(shot) {
    const existing = shot.cameraPath ?? {};
    shot.cameraPath = {
        ...existing,
        motionType: existing.motionType && existing.motionType !== "static" ? existing.motionType : "tracking",
        coordinateSpace: existing.coordinateSpace ?? "subject",
        pathShape: existing.pathShape ?? "smooth",
        waypoints: normalizeSpatialWaypoints(existing.waypoints),
    };
    return shot.cameraPath;
}

export function renderSpatialCameraEditor(container, shot, commit, rerender) {
    const path = shot.cameraPath;
    const root = element("section", "minimax-h3-spatial-editor");
    if (!path?.waypoints) {
        const intro = element("div", "minimax-h3-spatial-empty");
        intro.append(
            element("div", "minimax-h3-spatial-empty-art", "⌁"),
            element("h3", "", "Build a spatial camera path"),
            element("p", "", "Place 2–6 timed camera positions around the subject or scene. Every point is converted into prompt direction."),
            actionButton("Create spatial path", () => { ensurePath(shot); commit(); rerender(); }),
        );
        root.appendChild(intro); container.appendChild(root); return;
    }
    path.waypoints = normalizeSpatialWaypoints(path.waypoints);
    const stateKey = String(shot.id ?? "shot");
    const state = VIEW_STATE.get(stateKey) ?? { view: "perspective", selected: 0, progress: 0 };
    state.selected = Math.min(state.selected, path.waypoints.length - 1); VIEW_STATE.set(stateKey, state);

    const toolbar = element("div", "minimax-h3-spatial-toolbar");
    const viewSwitch = element("div", "minimax-h3-spatial-segments"); viewSwitch.setAttribute("role", "group"); viewSwitch.setAttribute("aria-label", "Camera workspace view");
    for (const [token, label] of [["perspective", "Perspective"], ["top", "Top"]]) {
        const button = actionButton(label, () => { state.view = token; renderScene(); }); button.setAttribute("aria-pressed", String(state.view === token)); viewSwitch.appendChild(button);
    }
    const shape = selectInput(path.pathShape ?? "smooth", SHAPES, { ariaLabel: "Path shape" });
    shape.addEventListener("change", () => { path.pathShape = shape.value; commit(); rerender(); });
    const space = selectInput(path.coordinateSpace ?? "subject", SPACES, { ariaLabel: "Coordinate space" });
    space.addEventListener("change", () => { path.coordinateSpace = space.value; commit(); rerender(); });
    toolbar.append(viewSwitch, shape, space);

    const canvas = element("div", "minimax-h3-spatial-canvas");
    const svg = svgNode("svg", { viewBox: "0 0 360 240", role: "application", "aria-label": "Spatial camera path editor. Drag camera points or use the controls below." });
    const timeline = element("div", "minimax-h3-spatial-timeline");
    const inspector = element("div", "minimax-h3-spatial-inspector");
    const playback = element("div", "minimax-h3-spatial-playback");
    const play = actionButton("▶ Preview", () => {
        if (state.playing) { state.playing = false; play.textContent = "▶ Preview"; return; }
        state.playing = true; play.textContent = "■ Stop"; const startAt = performance.now(); const startProgress = state.progress >= 1 ? 0 : state.progress;
        const tick = (now) => {
            if (!state.playing || ("isConnected" in root && !root.isConnected)) { state.playing = false; play.textContent = "▶ Preview"; return; }
            state.progress = Math.min(1, startProgress + (now - startAt) / 4000);
            scrub.value = String(state.progress); progressLabel.textContent = `${Math.round(state.progress * 100)}%`; updatePlaybackMarker();
            if (state.progress < 1) (globalThis.requestAnimationFrame ?? ((callback) => setTimeout(() => callback(performance.now()), 16)))(tick);
            else { state.playing = false; play.textContent = "↻ Replay"; }
        };
        (globalThis.requestAnimationFrame ?? ((callback) => setTimeout(() => callback(performance.now()), 16)))(tick);
    });
    const scrub = document.createElement("input"); scrub.type = "range"; scrub.min = "0"; scrub.max = "1"; scrub.step = ".01"; scrub.value = String(state.progress); scrub.setAttribute("aria-label", "Camera path preview position");
    const progressLabel = element("output", "", `${Math.round(state.progress * 100)}%`);
    scrub.addEventListener("input", () => { state.playing = false; play.textContent = "▶ Preview"; state.progress = Number(scrub.value); progressLabel.textContent = `${Math.round(state.progress * 100)}%`; updatePlaybackMarker(); });
    playback.append(play, scrub, progressLabel);

    function renderTimeline() {
        timeline.replaceChildren();
        for (const [index, point] of path.waypoints.entries()) {
            const button = actionButton(`${index + 1} · ${Math.round(point.at * 100)}%`, () => { state.selected = index; renderScene(); renderInspector(); renderTimeline(); });
            button.setAttribute("aria-pressed", String(index === state.selected)); button.title = `Select camera position ${index + 1}`;
            timeline.appendChild(button);
        }
        timeline.appendChild(actionButton("+ Point", () => {
            path.waypoints = addSpatialWaypoint(path.waypoints, state.selected); state.selected = Math.min(state.selected + 1, path.waypoints.length - 1); commit(); rerender();
        }, { disabled: path.waypoints.length >= 6 }));
    }

    function renderScene() {
        svg.replaceChildren(); grid(svg, state.view);
        const projected = path.waypoints.map((point) => projectCameraPoint(point, state.view));
        svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-path-shadow", d: spatialPathD(path.waypoints, state.view, path.pathShape) }));
        svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-path", d: spatialPathD(path.waypoints, state.view, path.pathShape) }));
        const target = svgNode("g", { class: "minimax-h3-spatial-target", transform: "translate(180 122)" });
        target.append(svgNode("circle", { r: 16 }), svgNode("circle", { r: 4 })); svg.appendChild(target);
        svg.appendChild(svgNode("text", { class: "minimax-h3-spatial-origin-label", x: 14, y: 22 }, path.coordinateSpace === "subject" ? "SUBJECT-RELATIVE ORIGIN" : "SCENE ORIGIN"));
        projected.forEach((position, index) => {
            const point = path.waypoints[index]; const group = svgNode("g", { class: "minimax-h3-spatial-point", "data-selected": String(index === state.selected), transform: `translate(${position.x} ${position.y})`, tabindex: "0", role: "button", "aria-label": `Camera position ${index + 1}, ${Math.round(point.at * 100)} percent` });
            group.append(svgNode("circle", { r: index === state.selected ? 15 : 12 }), svgNode("path", { d: "M 10 -7 L 27 -14 L 27 14 L 10 7 Z" }), svgNode("text", { y: 4, "text-anchor": "middle" }, String(index + 1)));
            group.addEventListener("click", () => { state.selected = index; renderScene(); renderInspector(); renderTimeline(); });
            group.addEventListener("keydown", (event) => {
                if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Enter", " "].includes(event.key)) return;
                event.preventDefault();
                if (["Enter", " "].includes(event.key)) { state.selected = index; renderScene(); renderInspector(); renderTimeline(); return; }
                const delta = event.shiftKey ? .1 : .03;
                if (event.key === "ArrowLeft") point.x = round(clamp(point.x - delta));
                if (event.key === "ArrowRight") point.x = round(clamp(point.x + delta));
                if (event.key === "ArrowUp") point.z = round(clamp(point.z - delta));
                if (event.key === "ArrowDown") point.z = round(clamp(point.z + delta));
                commit(); renderScene(); renderInspector();
            });
            group.addEventListener("pointerdown", (event) => {
                event.preventDefault(); state.selected = index; group.setPointerCapture?.(event.pointerId);
                const move = (moveEvent) => {
                    const rect = svg.getBoundingClientRect();
                    const screen = { x: (moveEvent.clientX - rect.left) * 360 / rect.width, y: (moveEvent.clientY - rect.top) * 240 / rect.height };
                    Object.assign(point, unprojectCameraPoint(screen, point, state.view)); renderScene(); renderInspector(); renderTimeline();
                };
                const up = () => { document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); commit(); };
                document.addEventListener("pointermove", move); document.addEventListener("pointerup", up);
            });
            svg.appendChild(group);
        });
        const previewPoint = projectCameraPoint(interpolateSpatialWaypoint(path.waypoints, state.progress), state.view);
        const marker = svgNode("g", { class: "minimax-h3-spatial-playhead", "data-playback-marker": "true", transform: `translate(${previewPoint.x} ${previewPoint.y})` });
        marker.append(svgNode("circle", { r: 7 }), svgNode("path", { d: "M 7 -4 L 18 -8 L 18 8 L 7 4 Z" })); svg.appendChild(marker);
    }

    function updatePlaybackMarker() {
        const point = projectCameraPoint(interpolateSpatialWaypoint(path.waypoints, state.progress), state.view);
        svg.querySelector?.("[data-playback-marker]")?.setAttribute("transform", `translate(${point.x} ${point.y})`);
    }

    function renderInspector() {
        inspector.replaceChildren(); const point = path.waypoints[state.selected];
        const heading = element("div", "minimax-h3-spatial-inspector-heading");
        heading.append(element("strong", "", `Position ${state.selected + 1}`), element("span", "", `${Math.round(point.at * 100)}% of shot`));
        const update = (key) => (value, final) => { point[key] = round(value); renderScene(); if (final) { commit(); rerender(); } };
        inspector.append(heading, slider("Left / right", point.x, -1, 1, .01, update("x")), slider("Height", point.y, -1, 1, .01, update("y")), slider("Near / far", point.z, -1, 1, .01, update("z")));
        if (state.selected > 0 && state.selected < path.waypoints.length - 1) {
            const lower = path.waypoints[state.selected - 1].at + .01; const upper = path.waypoints[state.selected + 1].at - .01;
            inspector.appendChild(slider("Timing", point.at, lower, upper, .01, update("at")));
        }
        const actions = element("div", "minimax-h3-spatial-inspector-actions");
        const hold = actionButton(point.hold ? "Remove hold" : "Add hold", () => { if (point.hold) delete point.hold; else point.hold = true; commit(); rerender(); });
        const remove = actionButton("Delete point", () => { path.waypoints.splice(state.selected, 1); state.selected = Math.max(0, state.selected - 1); commit(); rerender(); }, { disabled: path.waypoints.length <= 2 || state.selected === 0 || state.selected === path.waypoints.length - 1 });
        actions.append(hold, remove); inspector.appendChild(actions);
    }

    renderScene(); renderTimeline(); renderInspector();
    const workspace = element("div", "minimax-h3-spatial-workspace"); workspace.append(canvas, inspector); canvas.append(svg, playback, timeline);
    root.append(toolbar, workspace, element("p", "minimax-h3-spatial-note", "Spatial direction preview · relative coordinates, not a physical simulation"));
    container.appendChild(root);
}
