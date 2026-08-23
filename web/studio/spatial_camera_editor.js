import { actionButton, element, selectInput } from "./domain_components.js";

const SVG_NS = "http://www.w3.org/2000/svg";
export const CAMERA_HORIZONTAL_EXTENT = 1;
const VIEW_STATE = new Map();
const SHAPES = [["smooth", "Smooth"], ["straight", "Straight"], ["arc_left", "Arc left"], ["arc_right", "Arc right"]];
const SPACES = [["subject", "Around subject"], ["scene", "In scene"]];
const AIM_MODES = [["", "Inherit previous aim"], ["anchor", "Keep anchor in frame"], ["target", "Aim at named subject"], ["travel", "Follow direction of travel"], ["custom", "Custom direction"]];
const SPEEDS = [["", "Automatic"], ["slow", "Slow"], ["normal", "Normal"], ["fast", "Fast"]];
const EASINGS = [["", "Automatic"], ["linear", "Constant"], ["ease_in", "Accelerate"], ["ease_out", "Decelerate"], ["ease_in_out", "Accelerate then settle"]];
const FRAMINGS = [["", "Unspecified"], ["extreme_close_up", "Extreme close-up"], ["close_up", "Close-up"], ["medium_close_up", "Medium close-up"], ["medium", "Medium"], ["medium_wide", "Medium wide"], ["wide", "Wide"], ["extreme_wide", "Extreme wide"]];
const ANGLES = [["", "Unspecified"], ["eye_level", "Eye level"], ["low_angle", "Low angle"], ["high_angle", "High angle"], ["overhead", "Overhead"], ["dutch_static", "Dutch"], ["worms_eye", "Worm's eye"]];

function clamp(value, minimum = -1, maximum = 1) {
    return Math.max(minimum, Math.min(maximum, Number(value)));
}

function clampHorizontal(value) { return clamp(value, -CAMERA_HORIZONTAL_EXTENT, CAMERA_HORIZONTAL_EXTENT); }

function round(value) { return Math.round(Number(value) * 100) / 100; }

export function cameraElevationLabel(value) {
    const elevation = Number(value ?? 0);
    if (elevation <= -.60) return "Very low";
    if (elevation <= -.15) return "Low";
    if (elevation < .15) return "Eye level";
    if (elevation < .60) return "Elevated";
    return "Very elevated";
}

export function cameraVerticalSegment(from, to) {
    const delta = Number(to ?? 0) - Number(from ?? 0);
    const magnitude = Math.abs(delta);
    const kind = magnitude < .10 ? "hold" : magnitude < .35 ? "drift" : magnitude < .90 ? "move" : "sweep";
    return {
        kind,
        direction: kind === "hold" ? null : delta > 0 ? "ascend" : "descend",
        crossedEyeLine: (from < -.15 && to >= .15) || (from >= .15 && to < -.15),
        delta: Math.round(delta * 100) / 100,
    };
}

export function cameraHorizontalDistance(point) {
    return round(Math.hypot(Number(point?.x ?? 0), Number(point?.z ?? 0)));
}

export function setCameraHorizontalDistance(point, distance) {
    const current = cameraHorizontalDistance(point);
    const requested = Math.max(0, Math.min(CAMERA_HORIZONTAL_EXTENT * Math.SQRT2, Number(distance)));
    const direction = current < .001 ? { x: 0, z: 1 } : { x: Number(point.x) / current, z: Number(point.z) / current };
    const maximum = CAMERA_HORIZONTAL_EXTENT / Math.max(Math.abs(direction.x), Math.abs(direction.z), 1 / Math.SQRT2);
    const scale = Math.min(requested, maximum);
    point.x = round(clampHorizontal(direction.x * scale));
    point.z = round(clampHorizontal(direction.z * scale));
    return point;
}

export function cameraDistanceLabel(value) {
    const distance = Number(value ?? 0);
    if (distance <= .30) return "Close";
    if (distance <= .70) return "Medium distance";
    if (distance <= 1.05) return "Far";
    return "Very far";
}

export function cameraHeightScale(value) {
    return round(1 - clamp(value) * .22);
}

function elevationBand(value) {
    return cameraElevationLabel(value).toLowerCase();
}

function svgNode(tag, attributes = {}, text = "") {
    const node = document.createElementNS?.(SVG_NS, tag) ?? document.createElement(tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    if (text) node.textContent = text;
    return node;
}

export function defaultSpatialWaypoints() {
    return [
        { id: "cam1", at: 0, x: -.72, y: 0, z: .62, framing: "wide", aimMode: "anchor" },
        { id: "cam2", at: 1, x: .42, y: 0, z: -.38, framing: "medium", aimMode: "anchor" },
    ];
}

export function normalizeSpatialWaypoints(value) {
    if (!Array.isArray(value) || value.length < 2) return defaultSpatialWaypoints();
    return value.slice(0, 6).map((point, index, all) => ({
        ...point,
        id: String(point?.id || `cam${index + 1}`),
        at: index === 0 ? 0 : index === all.length - 1 ? 1 : round(clamp(point?.at, 0.01, 0.99)),
        x: round(clampHorizontal(point?.x)), y: round(clamp(point?.y)), z: round(clampHorizontal(point?.z)),
    })).sort((a, b) => a.at - b.at);
}

export function projectCameraPoint(point, view = "perspective") {
    const x = Number(point.x) / CAMERA_HORIZONTAL_EXTENT;
    const z = Number(point.z) / CAMERA_HORIZONTAL_EXTENT;
    if (view === "top") return { x: 180 + x * 126, y: 122 + z * 82 };
    if (view === "front") return { x: 180 + x * 126, y: 122 - point.y * 82 };
    return { x: 180 + x * 90 - z * 55, y: 128 + x * 45 + z * 45 };
}

export function unprojectCameraPoint(screen, point, view = "perspective") {
    if (view === "top") return { ...point, x: round(clampHorizontal((screen.x - 180) / 126 * CAMERA_HORIZONTAL_EXTENT)), z: round(clampHorizontal((screen.y - 122) / 82 * CAMERA_HORIZONTAL_EXTENT)) };
    if (view === "front") return { ...point, x: round(clampHorizontal((screen.x - 180) / 126 * CAMERA_HORIZONTAL_EXTENT)), y: round(clamp((122 - screen.y) / 82)) };
    const horizontal = screen.x - 180;
    const vertical = screen.y - 128;
    return {
        ...point,
        x: round(clampHorizontal((45 * horizontal + 55 * vertical) / 6525 * CAMERA_HORIZONTAL_EXTENT)),
        z: round(clampHorizontal((-45 * horizontal + 90 * vertical) / 6525 * CAMERA_HORIZONTAL_EXTENT)),
    };
}

export function spatialPathD(waypoints, view = "perspective", shape = "smooth") {
    const points = waypoints.map((point) => projectCameraPoint(point, view));
    if (!points.length) return "";
    if (shape === "straight" || points.length < 2) return points.map((point, index) => `${index ? "L" : "M"} ${round(point.x)} ${round(point.y)}`).join(" ");
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

export function cameraAimTarget(waypoints, index, namedTargetPoint = null) {
    const point = resolvedCameraAimWaypoint(waypoints, index);
    if (!point) return null;
    if (point.aimMode === "anchor") return { x: 0, y: 0, z: 0 };
    if (point.aimMode === "travel") {
        if (waypoints[index + 1]) return { ...waypoints[index + 1] };
        const previous = waypoints[index - 1];
        if (!previous) return null;
        return {
            x: point.x + (point.x - previous.x),
            y: point.y + (point.y - previous.y),
            z: point.z + (point.z - previous.z),
        };
    }
    if (point.aimMode === "target") return namedTargetPoint ? { ...namedTargetPoint } : null;
    if (point.aimMode !== "custom") return null;
    const pan = Number(point.panDegrees ?? 0) * Math.PI / 180;
    const tilt = Number(point.tiltDegrees ?? 0) * Math.PI / 180;
    const horizontal = Math.cos(tilt);
    const length = .72;
    return {
        x: point.x + Math.sin(pan) * horizontal * length,
        y: point.y + Math.sin(tilt) * length,
        z: point.z - Math.cos(pan) * horizontal * length,
    };
}

export function resolvedCameraAimWaypoint(waypoints, index) {
    const point = waypoints[index];
    if (!point || point.aimMode) return point;
    for (let previous = index - 1; previous >= 0; previous -= 1) {
        const source = waypoints[previous];
        if (!source?.aimMode) continue;
        const inherited = { ...point, aimMode: source.aimMode };
        for (const key of ["aimTarget", "panDegrees", "tiltDegrees"]) {
            if (source[key] !== undefined) inherited[key] = structuredClone(source[key]);
        }
        return inherited;
    }
    return point;
}

export function aimAnglesForTarget(camera, target) {
    const dx = Number(target.x) - Number(camera.x);
    const dy = Number(target.y) - Number(camera.y);
    const dz = Number(target.z) - Number(camera.z);
    const horizontal = Math.hypot(dx, dz);
    if (horizontal < .0001 && Math.abs(dy) < .0001) return null;
    return {
        panDegrees: round(Math.atan2(dx, -dz) * 180 / Math.PI),
        tiltDegrees: round(Math.atan2(dy, horizontal) * 180 / Math.PI),
    };
}

export function cameraIconRotation(waypoints, index, view = "perspective", namedTargetPoint = null) {
    const point = waypoints[index];
    const targetPoint = cameraAimTarget(waypoints, index, namedTargetPoint);
    if (!point || !targetPoint) return 0;
    const here = projectCameraPoint(point, view);
    const target = projectCameraPoint(targetPoint, view);
    const dx = target.x - here.x;
    const dy = target.y - here.y;
    return round(Math.atan2(dy, dx) * 180 / Math.PI);
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
    const leftIndex = Math.min(Math.max(0, selectedIndex), waypoints.length - 2);
    const left = waypoints[leftIndex];
    const right = waypoints[leftIndex + 1];
    const next = { id: `cam${Date.now().toString(36)}`, at: round((left.at + right.at) / 2), x: round((left.x + right.x) / 2), y: round((left.y + right.y) / 2), z: round((left.z + right.z) / 2) };
    for (const key of ["aimMode", "aimTarget", "panDegrees", "tiltDegrees"]) {
        if (left[key] !== undefined) next[key] = structuredClone(left[key]);
    }
    return [...waypoints, next].sort((a, b) => a.at - b.at);
}

export function redistributeSpatialWaypointTiming(waypoints) {
    const last = Math.max(1, waypoints.length - 1);
    return waypoints.map((point, index) => ({ ...point, at: round(index / last) }));
}

function grid(svg, view) {
    const values = [-3, -2, -1, 0, 1, 2, 3];
    const line = (from, to) => {
        const a = projectCameraPoint(from, view); const b = projectCameraPoint(to, view);
        svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-grid", d: `M ${round(a.x)} ${round(a.y)} L ${round(b.x)} ${round(b.y)}` }));
    };
    if (view === "front") {
        for (const value of values) line({ x: value, y: -1, z: 0 }, { x: value, y: 1, z: 0 });
        for (const value of [-1, -.67, -.33, 0, .33, .67, 1]) line({ x: -3, y: value, z: 0 }, { x: 3, y: value, z: 0 });
    } else {
        for (const value of values) line({ x: value, y: 0, z: -3 }, { x: value, y: 0, z: 3 });
        for (const value of values) line({ x: -3, y: 0, z: value }, { x: 3, y: 0, z: value });
    }
}

function selectField(label, control) {
    const root = element("label", "minimax-h3-spatial-select");
    root.append(element("span", "", label), control);
    return root;
}

function slider(label, value, minimum, maximum, step, onInput, options = {}) {
    const root = element("label", "minimax-h3-spatial-slider");
    const formatValue = options.formatValue ?? String;
    const formatted = formatValue(value);
    const heading = element("span", ""); const output = element("output", "", formatted); output.value = formatted;
    heading.append(element("span", "", label), output);
    const input = document.createElement("input"); input.type = "range"; input.min = String(minimum); input.max = String(maximum); input.step = String(step); input.value = String(value);
    input.setAttribute("aria-label", label);
    if (options.valueText) input.setAttribute("aria-valuetext", options.valueText(value));
    input.addEventListener("input", () => {
        const nextFormatted = formatValue(input.value);
        output.value = nextFormatted; output.textContent = nextFormatted;
        if (options.valueText) input.setAttribute("aria-valuetext", options.valueText(input.value));
        onInput(Number(input.value), false);
    });
    input.addEventListener("change", () => onInput(Number(input.value), true));
    root.append(heading, input);
    if (options.scale) root.appendChild(element("small", "minimax-h3-spatial-slider-scale", options.scale));
    return root;
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

function interpolatePlacement(placement, progress) {
    if (!placement?.start) return null;
    if (!placement.end) return { ...placement.start };
    return {
        x: Number(placement.start.x) + (Number(placement.end.x) - Number(placement.start.x)) * progress,
        y: Number(placement.start.y) + (Number(placement.end.y) - Number(placement.start.y)) * progress,
        z: Number(placement.start.z) + (Number(placement.end.z) - Number(placement.start.z)) * progress,
    };
}

export function stagedAimPoint(shot, path, waypoint) {
    if (waypoint?.aimMode !== "target" || waypoint.aimTarget?.kind !== "subject") return null;
    const staging = Array.isArray(shot?.staging) ? shot.staging : [];
    const target = interpolatePlacement(staging.find((item) => item.subjectId === waypoint.aimTarget.id), Number(waypoint.at));
    if (!target) return { x: 0, y: 0, z: 0, unplaced: true };
    if (path?.coordinateSpace !== "subject" || path.anchorTarget?.kind !== "subject") return target;
    const anchor = interpolatePlacement(staging.find((item) => item.subjectId === path.anchorTarget.id), Number(waypoint.at));
    if (!anchor) return target;
    return { x: target.x - anchor.x, y: target.y - anchor.y, z: target.z - anchor.z };
}

export function renderSpatialCameraEditor(container, shot, project, commit, rerender) {
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
    const declaredSubjectIds = new Set((shot.subjects ?? []).filter((item) => item.presence !== "absent").map((item) => item.subjectId));
    const availableSubjects = (project?.subjects ?? []).filter((subject) => !declaredSubjectIds.size || declaredSubjectIds.has(subject.id));

    const toolbar = element("div", "minimax-h3-spatial-toolbar");
    const viewSwitch = element("div", "minimax-h3-spatial-segments"); viewSwitch.setAttribute("role", "group"); viewSwitch.setAttribute("aria-label", "Camera workspace view");
    for (const [token, label] of [["perspective", "3D"], ["top", "Top"], ["front", "Front"]]) {
        const button = actionButton(label, () => { state.view = token; renderScene(); }); button.setAttribute("aria-pressed", String(state.view === token)); viewSwitch.appendChild(button);
    }
    const shape = selectInput(path.pathShape ?? "smooth", SHAPES, { ariaLabel: "Path shape" });
    shape.addEventListener("change", () => { path.pathShape = shape.value; commit(); rerender(); });
    const speed = selectInput(path.speed ?? "", SPEEDS, { ariaLabel: "Overall camera pace" });
    speed.addEventListener("change", () => { if (speed.value) path.speed = speed.value; else delete path.speed; commit(); rerender(); });
    const easing = selectInput(path.easing ?? "", EASINGS, { ariaLabel: "Camera speed change" });
    easing.addEventListener("change", () => { if (easing.value) path.easing = easing.value; else delete path.easing; commit(); rerender(); });
    const space = selectInput(path.coordinateSpace ?? "subject", SPACES, { ariaLabel: "Coordinate space" });
    space.addEventListener("change", () => {
        path.coordinateSpace = space.value;
        if (space.value !== "subject") delete path.anchorTarget;
        commit(); rerender();
    });
    toolbar.append(viewSwitch, selectField("Path shape", shape), selectField("Overall pace", speed), selectField("Speed change", easing), selectField("Reference frame", space));
    if ((path.coordinateSpace ?? "subject") === "subject") {
        const subjects = availableSubjects;
        const anchor = selectInput(
            path.anchorTarget?.kind === "subject" ? path.anchorTarget.id : "",
            [["", subjects.length > 1 ? "Anchor: Choose subject…" : `Anchor: ${subjects[0]?.name || "shot subject"}`], ...subjects.map((subject) => [subject.id, `Anchor: ${subject.name || subject.id}`])],
            { ariaLabel: "Camera path subject anchor" },
        );
        anchor.addEventListener("change", () => {
            if (anchor.value) path.anchorTarget = { kind: "subject", id: anchor.value };
            else delete path.anchorTarget;
            commit(); rerender();
        });
        toolbar.appendChild(anchor);
        if (subjects.length > 1 && !path.anchorTarget?.id) {
            const examples = subjects.slice(0, 2).map((subject) => subject.name || subject.id).join(" or ");
            toolbar.appendChild(element("span", "minimax-h3-spatial-anchor-warning", `Choose ${examples} as the anchor so “behind” and camera aim are unambiguous.`));
        }
    }

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
            const existingIds = new Set(path.waypoints.map((point) => point.id));
            path.waypoints = addSpatialWaypoint(path.waypoints, state.selected);
            state.selected = Math.max(0, path.waypoints.findIndex((point) => !existingIds.has(point.id)));
            commit(); rerender();
        }, { disabled: path.waypoints.length >= 6 }));
        const compressed = path.waypoints.some((point, index) => index > 0 && point.at - path.waypoints[index - 1].at < .03);
        if (compressed) {
            const repair = actionButton("Space timing evenly", () => {
                path.waypoints = redistributeSpatialWaypointTiming(path.waypoints); commit(); rerender();
            });
            repair.title = "Repair camera positions that occupy almost the same moment.";
            timeline.appendChild(repair);
        }
    }

    function renderScene() {
        svg.replaceChildren(); grid(svg, state.view);
        const markerId = `minimax-h3-spatial-arrow-${String(shot.id || "shot").replace(/[^A-Za-z0-9_-]/g, "-")}`;
        const defs = svgNode("defs");
        const arrowMarker = svgNode("marker", { id: markerId, markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto", markerUnits: "strokeWidth" });
        arrowMarker.appendChild(svgNode("path", { class: "minimax-h3-spatial-arrowhead", d: "M 0 0 L 8 4 L 0 8 Z" }));
        defs.appendChild(arrowMarker); svg.appendChild(defs);
        const projected = path.waypoints.map((point) => projectCameraPoint(point, state.view));
        svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-path-shadow", d: spatialPathD(path.waypoints, state.view, path.pathShape) }));
        svg.appendChild(svgNode("path", { class: "minimax-h3-spatial-path", d: spatialPathD(path.waypoints, state.view, path.pathShape), "marker-end": `url(#${markerId})` }));
        const origin = projectCameraPoint({ x: 0, y: 0, z: 0 }, state.view);
        const target = svgNode("g", { class: "minimax-h3-spatial-target", transform: `translate(${origin.x} ${origin.y})` });
        target.append(svgNode("circle", { r: 16 }), svgNode("circle", { r: 4 })); svg.appendChild(target);
        const anchorSubject = (project?.subjects ?? []).find((subject) => subject.id === path.anchorTarget?.id);
        const originLabel = path.coordinateSpace === "subject"
            ? anchorSubject ? `AROUND ${String(anchorSubject.name || anchorSubject.id).toLocaleUpperCase()}` : ((project?.subjects ?? []).length > 1 ? "CHOOSE SUBJECT ANCHOR" : `AROUND ${String(project?.subjects?.[0]?.name || "SHOT SUBJECT").toLocaleUpperCase()}`)
            : "SCENE ORIGIN";
        svg.appendChild(svgNode("text", { class: "minimax-h3-spatial-origin-label", x: 14, y: 22 }, originLabel));
        if (state.view !== "front") {
            const labels = [
                ["FRAME LEFT", projectCameraPoint({ x: -CAMERA_HORIZONTAL_EXTENT, y: 0, z: 0 }, state.view)],
                ["FRAME RIGHT", projectCameraPoint({ x: CAMERA_HORIZONTAL_EXTENT, y: 0, z: 0 }, state.view)],
                ["BEHIND", projectCameraPoint({ x: 0, y: 0, z: -CAMERA_HORIZONTAL_EXTENT }, state.view)],
                ["IN FRONT", projectCameraPoint({ x: 0, y: 0, z: CAMERA_HORIZONTAL_EXTENT }, state.view)],
            ];
            for (const [label, position] of labels) svg.appendChild(svgNode("text", { class: "minimax-h3-spatial-axis-label", x: position.x, y: position.y - 8, "text-anchor": "middle" }, label));
        }
        projected.forEach((position, index) => {
            const point = path.waypoints[index]; const group = svgNode("g", { class: "minimax-h3-spatial-point", "data-selected": String(index === state.selected), "data-view": state.view, transform: `translate(${position.x} ${position.y})`, tabindex: "0", role: "button", "aria-label": `Camera position ${index + 1}, ${Math.round(point.at * 100)} percent, ${cameraElevationLabel(point.y).toLowerCase()}. Drag across the plane to reposition; use Camera height to change elevation.` });
            const resolvedAimPoint = resolvedCameraAimWaypoint(path.waypoints, index);
            const namedTargetPoint = stagedAimPoint(shot, path, resolvedAimPoint);
            const aimTarget = cameraAimTarget(path.waypoints, index, namedTargetPoint);
            if (aimTarget) {
                const aimPosition = projectCameraPoint(aimTarget, state.view);
                svg.appendChild(svgNode("path", {
                    class: "minimax-h3-spatial-aim-line",
                    "data-selected": String(index === state.selected),
                    d: `M ${round(position.x)} ${round(position.y)} L ${round(aimPosition.x)} ${round(aimPosition.y)}`,
                }));
                const reticle = svgNode("g", {
                    class: "minimax-h3-spatial-aim-target",
                    "data-selected": String(index === state.selected),
                    transform: `translate(${round(aimPosition.x)} ${round(aimPosition.y)})`,
                    "aria-label": `Aim target for camera position ${index + 1}`,
                    role: "button",
                    tabindex: index === state.selected ? "0" : "-1",
                });
                reticle.append(
                    svgNode("circle", { r: index === state.selected ? 8 : 6 }),
                    svgNode("path", { d: "M -11 0 L -4 0 M 4 0 L 11 0 M 0 -11 L 0 -4 M 0 4 L 0 11" }),
                );
                if (resolvedAimPoint.aimMode === "target") {
                    const targetSubject = availableSubjects.find((subject) => subject.id === resolvedAimPoint.aimTarget?.id);
                    reticle.appendChild(svgNode("text", { class: "minimax-h3-spatial-aim-label", x: 12, y: -10 }, targetSubject?.name || resolvedAimPoint.aimTarget?.id || "Target"));
                }
                reticle.addEventListener("keydown", (event) => {
                    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
                    event.preventDefault();
                    const step = event.shiftKey ? 15 : 5;
                    point.aimMode = "custom"; delete point.aimTarget;
                    if (event.key === "ArrowLeft") point.panDegrees = Math.max(-180, Number(point.panDegrees ?? 0) - step);
                    if (event.key === "ArrowRight") point.panDegrees = Math.min(180, Number(point.panDegrees ?? 0) + step);
                    if (event.key === "ArrowUp") point.tiltDegrees = Math.min(90, Number(point.tiltDegrees ?? 0) + step);
                    if (event.key === "ArrowDown") point.tiltDegrees = Math.max(-90, Number(point.tiltDegrees ?? 0) - step);
                    commit(); rerender();
                });
                reticle.addEventListener("pointerdown", (event) => {
                    event.preventDefault(); event.stopPropagation(); state.selected = index;
                    const move = (moveEvent) => {
                        const rect = svg.getBoundingClientRect();
                        const screen = { x: (moveEvent.clientX - rect.left) * 360 / rect.width, y: (moveEvent.clientY - rect.top) * 240 / rect.height };
                        const currentTarget = cameraAimTarget(path.waypoints, index) ?? { x: 0, y: 0, z: 0 };
                        const targetPoint = unprojectCameraPoint(screen, currentTarget, state.view);
                        const angles = aimAnglesForTarget(point, targetPoint);
                        if (!angles) return;
                        point.aimMode = "custom";
                        delete point.aimTarget;
                        point.panDegrees = angles.panDegrees;
                        point.tiltDegrees = angles.tiltDegrees;
                        renderScene(); renderInspector();
                    };
                    const up = () => {
                        document.removeEventListener("pointermove", move);
                        document.removeEventListener("pointerup", up);
                        commit(); rerender();
                    };
                    document.addEventListener("pointermove", move);
                    document.addEventListener("pointerup", up);
                });
                svg.appendChild(reticle);
            }
            const heightScale = state.view === "perspective" ? cameraHeightScale(point.y) : 1;
            const cameraGlyph = svgNode("g", { class: "minimax-h3-spatial-camera-glyph", transform: `rotate(${cameraIconRotation(path.waypoints, index, state.view, namedTargetPoint)}) scale(${heightScale})` });
            cameraGlyph.append(
                svgNode("rect", { class: "minimax-h3-spatial-camera-body", x: -11, y: -8, width: 20, height: 16, rx: 3 }),
                svgNode("path", { class: "minimax-h3-spatial-camera-lens", d: "M 8 -6 L 25 -3.5 L 25 3.5 L 8 6 Z" }),
                svgNode("path", { class: "minimax-h3-spatial-camera-front", d: "M 25 -5 L 25 5" }),
            );
            const badge = svgNode("g", { class: "minimax-h3-spatial-point-badge", transform: "translate(-12 -16)" });
            badge.append(svgNode("circle", { r: 8 }), svgNode("text", { y: 3.5, "text-anchor": "middle" }, String(index + 1)));
            const framing = String(point.framing ?? "auto").replaceAll("_", " ");
            group.append(cameraGlyph, badge, svgNode("text", { class: "minimax-h3-spatial-point-meta", x: 18, y: -17 }, `${framing} · ${elevationBand(point.y)}`));
            group.addEventListener("click", () => { state.selected = index; renderScene(); renderInspector(); renderTimeline(); });
            group.addEventListener("keydown", (event) => {
                if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Enter", " ", "a", "A"].includes(event.key)) return;
                event.preventDefault();
                if (["Enter", " "].includes(event.key)) { state.selected = index; renderScene(); renderInspector(); renderTimeline(); return; }
                if (["a", "A"].includes(event.key)) {
                    const modes = ["anchor", "target", "travel", "custom"];
                    point.aimMode = modes[(modes.indexOf(point.aimMode) + 1) % modes.length];
                    if (point.aimMode === "target") {
                        const fallback = availableSubjects.find((subject) => subject.id !== path.anchorTarget?.id) ?? availableSubjects[0];
                        if (fallback) point.aimTarget = { kind: "subject", id: fallback.id }; else point.aimMode = "anchor";
                    } else delete point.aimTarget;
                    if (point.aimMode !== "custom") { delete point.panDegrees; delete point.tiltDegrees; }
                    commit(); rerender(); return;
                }
                const delta = event.shiftKey ? .1 : .03;
                if (event.key === "ArrowLeft") point.x = round(clampHorizontal(point.x - delta));
                if (event.key === "ArrowRight") point.x = round(clampHorizontal(point.x + delta));
                if (event.key === "ArrowUp") {
                    if (state.view === "front") point.y = round(clamp(point.y + delta));
                    else point.z = round(clampHorizontal(point.z - delta));
                }
                if (event.key === "ArrowDown") {
                    if (state.view === "front") point.y = round(clamp(point.y - delta));
                    else point.z = round(clampHorizontal(point.z + delta));
                }
                commit(); renderScene(); renderInspector();
            });
            group.addEventListener("pointerdown", (event) => {
                event.preventDefault(); state.selected = index; group.setPointerCapture?.(event.pointerId);
                const move = (moveEvent) => {
                    const rect = svg.getBoundingClientRect();
                    const screen = { x: (moveEvent.clientX - rect.left) * 360 / rect.width, y: (moveEvent.clientY - rect.top) * 240 / rect.height };
                    Object.assign(point, unprojectCameraPoint(screen, point, state.view));
                    renderScene(); renderInspector(); renderTimeline();
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
        heading.append(element("strong", "", `Position ${state.selected + 1}`), element("span", "", `${Math.round(point.at * 100)}% of shot · ${cameraElevationLabel(point.y)}`));
        const update = (key) => (value, final) => { point[key] = round(value); renderScene(); if (final) { commit(); rerender(); } };
        const updateDistance = (value, final) => { setCameraHorizontalDistance(point, value); renderScene(); if (final) { commit(); rerender(); } };
        inspector.append(
            heading,
            slider("Frame left / right", point.x, -CAMERA_HORIZONTAL_EXTENT, CAMERA_HORIZONTAL_EXTENT, .02, update("x")),
            slider("Camera height", point.y, -1, 1, .05, update("y"), {
                formatValue: cameraElevationLabel,
                valueText: (value) => `${cameraElevationLabel(value)} — moves the camera body`,
                scale: "Very low  ·  Low  ·  Eye level  ·  Elevated  ·  Very elevated",
            }),
            slider("Behind / in front", point.z, -CAMERA_HORIZONTAL_EXTENT, CAMERA_HORIZONTAL_EXTENT, .02, update("z")),
            slider("Distance from anchor", cameraHorizontalDistance(point), 0, CAMERA_HORIZONTAL_EXTENT * Math.SQRT2, .05, updateDistance, {
                formatValue: cameraDistanceLabel,
                valueText: (value) => `${cameraDistanceLabel(value)} from the anchor; camera height stays unchanged`,
                scale: "Close  ·  Medium  ·  Far  ·  Very far",
            }),
        );
        const framing = selectInput(point.framing ?? "", FRAMINGS, { ariaLabel: `Framing at camera position ${state.selected + 1}` });
        framing.addEventListener("change", () => { if (framing.value) point.framing = framing.value; else delete point.framing; commit(); rerender(); });
        const angle = selectInput(point.angle ?? "", ANGLES, { ariaLabel: `Angle at camera position ${state.selected + 1}` });
        angle.addEventListener("change", () => { if (angle.value) point.angle = angle.value; else delete point.angle; commit(); rerender(); });
        inspector.append(element("p", "minimax-h3-spatial-control-help", "Drag the camera across the plane. Camera height changes its apparent scale here; Aim controls where the lens points."));
        inspector.append(selectField("Framing at this position", framing), selectField("Shot angle at this position", angle));
        const aim = selectInput(point.aimMode ?? "", AIM_MODES, { ariaLabel: `Camera aim at position ${state.selected + 1}` });
        aim.addEventListener("change", () => {
            if (aim.value) point.aimMode = aim.value; else delete point.aimMode;
            if (aim.value !== "custom") { delete point.panDegrees; delete point.tiltDegrees; }
            if (aim.value === "target") {
                const fallback = availableSubjects.find((subject) => subject.id !== path.anchorTarget?.id) ?? availableSubjects[0];
                if (fallback) point.aimTarget = { kind: "subject", id: fallback.id };
                else point.aimMode = "anchor";
            } else delete point.aimTarget;
            commit(); rerender();
        });
        const aimLabel = element("label", "minimax-h3-spatial-aim");
        aimLabel.append(element("span", "", "Where the camera faces"), aim);
        inspector.appendChild(aimLabel);
        if (point.aimMode === "target") {
            const target = selectInput(
                point.aimTarget?.id ?? "",
                [["", "Choose subject…", true], ...availableSubjects.map((subject) => [subject.id, subject.name || subject.id])],
                { ariaLabel: `Named aim target at camera position ${state.selected + 1}` },
            );
            target.addEventListener("change", () => {
                if (target.value) point.aimTarget = { kind: "subject", id: target.value };
                commit(); rerender();
            });
            inspector.appendChild(selectField("Named aim target", target));
            if (stagedAimPoint(shot, path, point)?.unplaced) {
                inspector.appendChild(element("p", "minimax-h3-spatial-anchor-warning", "This subject has no position in Staging. The name reaches H3, but the reticle stays at the origin until you place the subject."));
            }
        }
        if (point.aimMode === "custom") {
            inspector.append(
                slider("Pan · left / right (degrees)", point.panDegrees ?? 0, -180, 180, 5, update("panDegrees")),
                slider("Lens tilt · down / up (degrees)", point.tiltDegrees ?? 0, -90, 90, 5, update("tiltDegrees"), {
                    scale: "Tilts the lens only; camera height stays unchanged",
                }),
            );
        }
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
    root.append(toolbar, workspace, element("p", "minimax-h3-spatial-note", "3D: drag the camera body up/down for height; drag its floor marker across the plane; use Distance to move nearer/farther · the reticle controls aim"));
    container.appendChild(root);
}
