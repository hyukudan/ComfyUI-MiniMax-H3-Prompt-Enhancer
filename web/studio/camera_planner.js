import { actionButton, element, selectInput } from "./domain_components.js";
import { ensureCameraPlannerStyles } from "./camera_planner_styles.js";
import { renderSpatialCameraEditor } from "./spatial_camera_editor.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const MOTION_LABELS = Object.freeze({
    static: "Locked off", zoom_in: "Zoom in", zoom_out: "Zoom out",
    push_in: "Dolly in", pull_out: "Dolly out",
    pan_left: "Pan left", pan_right: "Pan right",
    truck_left: "Truck left", truck_right: "Truck right",
    tilt_up: "Tilt up", tilt_down: "Tilt down",
    pedestal_up: "Pedestal up", pedestal_down: "Pedestal down",
    arc: "Orbit / arc", tracking: "Track subject", shake: "Handheld shake",
    roll_clockwise: "Roll clockwise", roll_counterclockwise: "Roll counter-clockwise",
});

export const VISUAL_CAMERA_MOTIONS = Object.freeze([
    { label: "Distance", items: [["static", "Locked", "●"], ["push_in", "Dolly in", "→"], ["pull_out", "Dolly out", "←"], ["zoom_in", "Zoom in", "+"], ["zoom_out", "Zoom out", "−"]] },
    { label: "Across the scene", items: [["truck_left", "Truck left", "←"], ["truck_right", "Truck right", "→"], ["arc", "Orbit / arc", "↷"], ["tracking", "Track subject", "⇢"]] },
    { label: "Aim & height", items: [["pan_left", "Pan left", "↶"], ["pan_right", "Pan right", "↷"], ["tilt_up", "Tilt up", "↑"], ["tilt_down", "Tilt down", "↓"], ["pedestal_up", "Pedestal up", "⇡"], ["pedestal_down", "Pedestal down", "⇣"]] },
    { label: "Expressive", items: [["roll_clockwise", "Roll clockwise", "⟳"], ["roll_counterclockwise", "Roll counter-clockwise", "⟲"], ["shake", "Handheld shake", "≈"]] },
]);

const FRAMING = [["", "Unspecified"], ["extreme_close_up", "Extreme close-up"], ["close_up", "Close-up"], ["medium_close_up", "Medium close-up"], ["medium", "Medium"], ["medium_wide", "Medium wide"], ["wide", "Wide"], ["extreme_wide", "Extreme wide"]];
const ANGLE = [["", "Unspecified"], ["eye_level", "Eye level"], ["low_angle", "Low angle"], ["high_angle", "High angle"], ["overhead", "Overhead"], ["dutch_static", "Dutch"], ["worms_eye", "Worm's eye"]];
const AMPLITUDE = [["", "Travel: Auto"], ["small", "Travel: Gentle"], ["medium", "Travel: Standard"], ["large", "Travel: Bold"]];
const SPEED = [["", "Pace: Auto"], ["slow", "Pace: Slow"], ["normal", "Pace: Normal"], ["fast", "Pace: Fast"]];
const FRAME_ENUMS = Object.freeze({
    framing: new Set(FRAMING.slice(1).map(([value]) => value)),
    angle: new Set(ANGLE.slice(1).map(([value]) => value)),
    viewpoint: new Set(["pov", "over_the_shoulder", "mirror_or_reflection", "front", "three_quarter", "profile", "rear_three_quarter", "rear"]),
    composition: new Set(["centered", "rule_of_thirds", "symmetrical", "layered_depth", "frame_within_frame", "negative_space", "two_shot", "custom"]),
    distance: new Set(["intimate", "near", "medium", "far", "very_far", "custom"]),
});
const FRAME_KEYS = new Set([...Object.keys(FRAME_ENUMS), "compositionNote", "primaryTarget", "secondaryTarget", "foregroundTarget", "focus", "distanceNote"]);
const PATH_ENUMS = Object.freeze({
    amplitude: new Set(["small", "medium", "large"]), speed: new Set(["slow", "normal", "fast"]),
    easing: new Set(["linear", "ease_in", "ease_out", "ease_in_out"]),
    timing: new Set(["throughout", "during_opening", "after_opening", "during_action", "during_dialogue", "after_dialogue", "before_cut"]),
});

const SPATIAL_ENDS = Object.freeze({
    push_in: [120, 122], pull_out: [30, 190], truck_left: [28, 160], truck_right: [132, 160],
    pedestal_up: [76, 105], pedestal_down: [76, 202], arc: [230, 155], tracking: [132, 118],
});

function title(value) {
    return String(value ?? "").replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

function resolvedEnd(shot) {
    return { ...(shot?.cameraStart ?? {}), ...(shot?.cameraEnd ?? {}) };
}

export function cameraSceneModel(shot = {}) {
    const motion = shot.cameraPath?.motionType ?? "static";
    const start = { x: 76, y: 164 };
    const spatial = SPATIAL_ENDS[motion];
    const end = spatial ? { x: spatial[0], y: spatial[1] } : { ...start };
    const kind = spatial ? "spatial" : ["pan_left", "pan_right", "tilt_up", "tilt_down", "roll_clockwise", "roll_counterclockwise"].includes(motion) ? "orientation" : motion.startsWith("zoom_") ? "optical" : motion === "shake" ? "expressive" : "static";
    let path = `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
    if (motion === "arc") path = `M ${start.x} ${start.y} Q 151 58 ${end.x} ${end.y}`;
    else if (kind === "orientation") path = `M 62 164 Q 76 134 90 164`;
    else if (kind === "optical") path = `M 61 164 L 91 164`;
    else if (kind === "expressive") path = `M 57 164 L 65 157 L 73 171 L 81 157 L 92 164`;
    return {
        motion, kind, start, end, path,
        startLabel: title(shot.cameraStart?.framing || "start"),
        endLabel: title(resolvedEnd(shot).framing || "end"),
    };
}

export function cameraAnnotationLayout(model) {
    const clampLabelX = (x) => Math.max(52, Math.min(308, x));
    const startY = model.start.y + 34;
    const proposedEndY = model.end.y - 24;
    const endY = Math.abs(startY - proposedEndY) < 32 ? startY - 32 : proposedEndY;
    return {
        start: { x: clampLabelX(model.start.x), y: startY, textAnchor: "middle" },
        end: { x: clampLabelX(model.end.x), y: endY, textAnchor: "middle" },
        axes: {
            left: { x: 24, y: 220, textAnchor: "start" },
            right: { x: 336, y: 220, textAnchor: "end" },
        },
        notePlacement: "below-svg",
    };
}

export function cameraInstructionPreview(shot = {}) {
    const start = shot.cameraStart ?? {};
    const end = resolvedEnd(shot);
    const path = shot.cameraPath ?? {};
    const startBits = [start.framing, start.angle].filter(Boolean).map(title);
    const endBits = [end.framing, end.angle].filter(Boolean).map(title);
    const parts = [`Start${startBits.length ? `: ${startBits.join(", ")}` : ": inherited / unspecified"}.`];
    if (!path.motionType) parts.push("Movement: no shot-level override.");
    else if (path.motionType === "static") parts.push("Movement: locked off throughout the shot.");
    else {
        const qualifiers = [path.amplitude && `${title(path.amplitude)} travel`, path.speed && `${title(path.speed)} pace`, path.easing && title(path.easing), path.timing && title(path.timing)].filter(Boolean);
        const anchor = path.anchorTarget?.kind === "subject" ? ` · anchored to ${path.anchorTarget.id}` : "";
        const aimed = Array.isArray(path.waypoints) ? path.waypoints.filter((point) => point.aimMode).length : 0;
        const spatial = Array.isArray(path.waypoints) ? ` · ${path.waypoints.length} timed positions · ${title(path.pathShape || "smooth")} · ${title(path.coordinateSpace || "subject")}-relative${anchor}${aimed ? ` · ${aimed} aimed positions` : ""}` : "";
        parts.push(`Movement: ${MOTION_LABELS[path.motionType] ?? title(path.motionType)}${qualifiers.length ? ` · ${qualifiers.join(" · ")}` : ""}${spatial}.`);
    }
    parts.push(`End${endBits.length ? `: ${endBits.join(", ")}` : ": inherits the start"}.`);
    return parts.join(" ");
}

export function setVisualCameraMotion(shot, motionType) {
    if (!motionType) {
        delete shot.cameraPath;
        return;
    }
    if (motionType === "static") {
        shot.cameraPath = { motionType: "static" };
        return;
    }
    shot.cameraPath = { ...(shot.cameraPath ?? {}), motionType };
}

function setFrameField(shot, phase, key, value) {
    const frame = shot[phase] ?? (shot[phase] = {});
    if (value) frame[key] = value; else delete frame[key];
    if (!Object.keys(frame).length) delete shot[phase];
}

function svgNode(tag, attributes = {}, text = "") {
    const node = document.createElementNS?.(SVG_NS, tag) ?? document.createElement(tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    if (text) node.textContent = text;
    return node;
}

function appendCamera(svg, position, phase, label, annotation) {
    const group = svgNode("g", { class: "minimax-h3-camera-position", "data-phase": phase, transform: `translate(${position.x} ${position.y})` });
    const labelX = annotation.x - position.x;
    const labelY = annotation.y - position.y;
    group.append(
        svgNode("circle", { cx: 0, cy: 0, r: 12 }),
        svgNode("path", { class: "minimax-h3-camera-direction", d: "M 12 -7 L 34 -16 L 34 16 L 12 7 Z" }),
        svgNode("text", { x: labelX, y: labelY, "text-anchor": annotation.textAnchor }, `${phase === "start" ? "START" : "END"} · ${label}`),
    );
    svg.appendChild(group);
}

function renderStage(shot) {
    const model = cameraSceneModel(shot);
    const annotations = cameraAnnotationLayout(model);
    const stage = element("div", "minimax-h3-camera-stage");
    const svg = svgNode("svg", { viewBox: "0 0 360 230", role: "img", "aria-label": `Camera guide. ${cameraInstructionPreview(shot)}` });
    for (let index = 0; index < 8; index += 1) {
        const inset = index * 22;
        svg.appendChild(svgNode("path", { class: "minimax-h3-camera-grid-line", d: `M ${18 + inset} ${205 - inset * .42} L 180 ${70 + inset * .06} L ${342 - inset} ${205 - inset * .42}` }));
    }
    for (let index = -4; index <= 4; index += 1) {
        svg.appendChild(svgNode("path", { class: "minimax-h3-camera-grid-line", d: `M 180 70 L ${180 + index * 39} 205` }));
    }
    svg.append(
        svgNode("path", { class: "minimax-h3-camera-axis", d: "M 22 205 L 338 205" }),
        svgNode("text", { class: "minimax-h3-camera-axis-label", x: annotations.axes.left.x, y: annotations.axes.left.y, "text-anchor": annotations.axes.left.textAnchor }, "FRAME LEFT"),
        svgNode("text", { class: "minimax-h3-camera-axis-label", x: annotations.axes.right.x, y: annotations.axes.right.y, "text-anchor": annotations.axes.right.textAnchor }, "FRAME RIGHT"),
        svgNode("path", { class: "minimax-h3-camera-trajectory", "data-kind": model.kind, d: model.path }),
    );
    const subject = svgNode("g", { class: "minimax-h3-camera-subject", transform: "translate(185 92)" });
    subject.append(svgNode("circle", { cx: 0, cy: 0, r: 11 }), svgNode("path", { d: "M -16 38 L -9 11 L 9 11 L 16 38 Z" }), svgNode("text", { x: 23, y: 5 }, "PRIMARY TARGET"));
    svg.appendChild(subject);
    appendCamera(svg, model.start, "start", model.startLabel, annotations.start);
    if (model.end.x !== model.start.x || model.end.y !== model.start.y) appendCamera(svg, model.end, "end", model.endLabel, annotations.end);
    stage.append(svg, element("p", "minimax-h3-camera-stage-note", "Direction guide · not a physical simulation"));
    return stage;
}

function phaseControl(shot, phase, number, label, commit, rerender) {
    const root = element("div", "minimax-h3-camera-phase");
    const heading = element("div", "minimax-h3-camera-phase-heading");
    heading.append(element("span", "minimax-h3-camera-phase-number", number), element("span", "", label));
    const controls = element("div", "minimax-h3-camera-phase-controls");
    const frame = shot[phase] ?? {};
    const framing = selectInput(frame.framing, phase === "cameraEnd" ? [["", "Inherit start"], ...FRAMING.slice(1)] : FRAMING, { ariaLabel: `${label} framing` });
    const angle = selectInput(frame.angle, phase === "cameraEnd" ? [["", "Inherit start"], ...ANGLE.slice(1)] : ANGLE, { ariaLabel: `${label} angle` });
    for (const [control, key] of [[framing, "framing"], [angle, "angle"]]) {
        control.addEventListener("change", () => { setFrameField(shot, phase, key, control.value); commit(); rerender(); });
    }
    const framingLabel = element("label"); framingLabel.append(element("span", "", "Framing"), framing);
    const angleLabel = element("label"); angleLabel.append(element("span", "", "Angle"), angle);
    controls.append(framingLabel, angleLabel); root.append(heading, controls);
    return root;
}

function wireRovingButtons(buttons, selectedIndex) {
    buttons.forEach((button, index) => { button.tabIndex = index === selectedIndex ? 0 : -1; });
    for (const [index, button] of buttons.entries()) {
        button.addEventListener("keydown", (event) => {
            if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const delta = ['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1;
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + delta + buttons.length) % buttons.length;
            buttons[next].tabIndex = 0; button.tabIndex = -1; buttons[next].focus();
        });
    }
}

function movementPhase(shot, commit, rerender) {
    const root = element("div", "minimax-h3-camera-phase");
    const heading = element("div", "minimax-h3-camera-phase-heading");
    heading.append(element("span", "minimax-h3-camera-phase-number", "2"), element("span", "", "Movement"));
    const groups = element("div", "minimax-h3-camera-motion-groups");
    const buttons = [];
    const selectedToken = shot.cameraPath?.motionType ?? "";
    for (const group of VISUAL_CAMERA_MOTIONS) {
        const block = element("div", "minimax-h3-camera-motion-group"); block.appendChild(element("span", "", group.label));
        const row = element("div", "minimax-h3-camera-motion-buttons"); row.setAttribute("role", "group"); row.setAttribute("aria-label", `${group.label} camera movements`);
        for (const [token, label, symbol] of group.items) {
            const button = actionButton(label, () => { setVisualCameraMotion(shot, token); commit(); rerender(); });
            button.className = "minimax-h3-camera-motion-button";
            button.dataset.motion = token; button.setAttribute("aria-pressed", String(selectedToken === token));
            // Put the symbol first without losing the button's accessible text.
            const textNode = element("span", "", label); button.textContent = ""; button.append(element("span", "minimax-h3-camera-motion-symbol", symbol), textNode);
            buttons.push(button); row.appendChild(button);
        }
        block.appendChild(row); groups.appendChild(block);
    }
    wireRovingButtons(buttons, Math.max(0, buttons.findIndex((button) => button.dataset.motion === selectedToken)));
    root.append(heading, groups);
    if (selectedToken && selectedToken !== "static") {
        const feel = element("div", "minimax-h3-camera-feel");
        const amplitude = selectInput(shot.cameraPath?.amplitude, AMPLITUDE, { ariaLabel: "Camera travel" });
        const speed = selectInput(shot.cameraPath?.speed, SPEED, { ariaLabel: "Camera pace" });
        for (const [control, key] of [[amplitude, "amplitude"], [speed, "speed"]]) {
            control.addEventListener("change", () => { if (control.value) shot.cameraPath[key] = control.value; else delete shot.cameraPath[key]; commit(); rerender(); });
        }
        feel.append(amplitude, speed); root.appendChild(feel);
    }
    return root;
}

function cameraFragment(shot) {
    const result = {};
    for (const key of ["cameraStart", "cameraPath", "cameraEnd"]) if (shot[key]) result[key] = shot[key];
    return result;
}

function shortTextIsValid(value) {
    return typeof value === "string" && Boolean(value.trim()) && value.length <= 500 && !value.includes("\0");
}

function cameraTargetError(value, path) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return `${path} must be an object.`;
    const expected = value.kind === "text" ? new Set(["kind", "text"]) : new Set(["kind", "id"]);
    const unknown = Object.keys(value).filter((key) => !expected.has(key));
    if (unknown.length) return `${path} contains unsupported keys: ${unknown.join(", ")}.`;
    if (value.kind === "text") return shortTextIsValid(value.text) ? "" : `${path}.text must contain 1–500 characters.`;
    if (!["subject", "environment", "asset"].includes(value.kind)) return `${path}.kind must be subject, environment, asset or text.`;
    return /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(value.id ?? "") ? "" : `${path}.id is not a valid project id.`;
}

function cameraFocusError(value, path) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return `${path} must be an object.`;
    const allowed = new Set(["mode", "primaryTarget", "secondaryTarget", "note"]);
    const unknown = Object.keys(value).filter((key) => !allowed.has(key));
    if (unknown.length) return `${path} contains unsupported keys: ${unknown.join(", ")}.`;
    if (!["single_target", "split_focus", "deep_focus", "custom"].includes(value.mode)) return `${path}.mode is not supported.`;
    for (const key of ["primaryTarget", "secondaryTarget"]) if (value[key]) {
        const error = cameraTargetError(value[key], `${path}.${key}`); if (error) return error;
    }
    return value.note === undefined || shortTextIsValid(value.note) ? "" : `${path}.note must contain 1–500 characters.`;
}

function cameraFrameError(value, path) {
    const unknown = Object.keys(value).filter((key) => !FRAME_KEYS.has(key));
    if (unknown.length) return `${path} contains unsupported keys: ${unknown.join(", ")}.`;
    for (const [key, choices] of Object.entries(FRAME_ENUMS)) if (value[key] !== undefined && !choices.has(value[key])) return `${path}.${key} is not supported.`;
    for (const key of ["compositionNote", "distanceNote"]) if (value[key] !== undefined && !shortTextIsValid(value[key])) return `${path}.${key} must contain 1–500 characters.`;
    for (const key of ["primaryTarget", "secondaryTarget", "foregroundTarget"]) if (value[key]) {
        const error = cameraTargetError(value[key], `${path}.${key}`); if (error) return error;
    }
    return value.focus ? cameraFocusError(value.focus, `${path}.focus`) : "";
}

function cameraPathError(value) {
    const allowed = new Set(["motionType", ...Object.keys(PATH_ENUMS), "coordinateSpace", "pathShape", "anchorTarget", "waypoints"]);
    const unknown = Object.keys(value).filter((key) => !allowed.has(key));
    if (unknown.length) return `cameraPath contains unsupported keys: ${unknown.join(", ")}.`;
    if (!MOTION_LABELS[value.motionType]) return "cameraPath.motionType is not supported by shot plan v2.";
    for (const [key, choices] of Object.entries(PATH_ENUMS)) if (value[key] !== undefined && !choices.has(value[key])) return `cameraPath.${key} is not supported.`;
    if (value.coordinateSpace !== undefined && !["subject", "scene"].includes(value.coordinateSpace)) return "cameraPath.coordinateSpace is not supported.";
    if (value.pathShape !== undefined && !["straight", "smooth", "arc_left", "arc_right"].includes(value.pathShape)) return "cameraPath.pathShape is not supported.";
    if (value.anchorTarget) {
        const error = cameraTargetError(value.anchorTarget, "cameraPath.anchorTarget"); if (error) return error;
    }
    if (value.waypoints !== undefined) {
        if (!Array.isArray(value.waypoints) || value.waypoints.length < 2 || value.waypoints.length > 6) return "cameraPath.waypoints must contain 2–6 positions.";
        let previous = -1;
        for (const [index, point] of value.waypoints.entries()) {
            if (!point || typeof point !== "object" || Array.isArray(point)) return `cameraPath.waypoints[${index}] must be an object.`;
            const unknownPoint = Object.keys(point).filter((key) => !["id", "at", "x", "y", "z", "framing", "angle", "hold", "aimMode", "panDegrees", "tiltDegrees"].includes(key));
            if (unknownPoint.length) return `cameraPath.waypoints[${index}] contains unsupported keys: ${unknownPoint.join(", ")}.`;
            if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(point.id ?? "")) return `cameraPath.waypoints[${index}].id is invalid.`;
            for (const key of ["at", "x", "y", "z"]) if (typeof point[key] !== "number" || !Number.isFinite(point[key])) return `cameraPath.waypoints[${index}].${key} must be numeric.`;
            if (point.at < 0 || point.at > 1 || point.at <= previous) return "cameraPath.waypoints timing must be strictly increasing from 0 to 1.";
            if (["x", "y", "z"].some((key) => point[key] < -1 || point[key] > 1)) return `cameraPath.waypoints[${index}] coordinates must be between -1 and 1.`;
            if (point.aimMode !== undefined && !["anchor", "travel", "custom"].includes(point.aimMode)) return `cameraPath.waypoints[${index}].aimMode is not supported.`;
            if (point.panDegrees !== undefined && (!Number.isFinite(point.panDegrees) || point.panDegrees < -180 || point.panDegrees > 180)) return `cameraPath.waypoints[${index}].panDegrees must be between -180 and 180.`;
            if (point.tiltDegrees !== undefined && (!Number.isFinite(point.tiltDegrees) || point.tiltDegrees < -90 || point.tiltDegrees > 90)) return `cameraPath.waypoints[${index}].tiltDegrees must be between -90 and 90.`;
            if ((point.panDegrees !== undefined || point.tiltDegrees !== undefined) && point.aimMode !== "custom") return `cameraPath.waypoints[${index}] custom angles require aimMode custom.`;
            previous = point.at;
        }
        if (value.waypoints[0].at !== 0 || value.waypoints.at(-1).at !== 1) return "cameraPath.waypoints must start at 0 and end at 1.";
    }
    if (value.motionType === "static" && ["amplitude", "speed", "easing", "coordinateSpace", "pathShape", "anchorTarget", "waypoints"].some((key) => value[key] !== undefined)) return "A locked camera cannot include movement properties.";
    return "";
}

export function parseCameraFragment(raw) {
    let value;
    try { value = JSON.parse(raw); } catch (error) { return { ok: false, error: String(error?.message ?? "Invalid JSON") }; }
    if (!value || typeof value !== "object" || Array.isArray(value)) return { ok: false, error: "Expected one camera object." };
    const allowed = new Set(["cameraStart", "cameraPath", "cameraEnd"]);
    const unknown = Object.keys(value).filter((key) => !allowed.has(key));
    if (unknown.length) return { ok: false, error: `Unsupported camera keys: ${unknown.join(", ")}.` };
    for (const key of Object.keys(value)) {
        if (!value[key] || typeof value[key] !== "object" || Array.isArray(value[key]) || !Object.keys(value[key]).length) return { ok: false, error: `${key} must be a non-empty object.` };
    }
    for (const key of ["cameraStart", "cameraEnd"]) if (value[key]) {
        const error = cameraFrameError(value[key], key); if (error) return { ok: false, error };
    }
    if (value.cameraPath) {
        const error = cameraPathError(value.cameraPath); if (error) return { ok: false, error };
    }
    return { ok: true, value };
}

export function renderCameraDataFallback(container, shot, commit, rerender) {
    const details = element("details", "minimax-h3-camera-data-fallback");
    details.appendChild(element("summary", "", "Advanced text / data fallback"));
    details.appendChild(element("p", "minimax-h3-field-hint", "Edit this shot's exact camera v2 fragment. This is optional; the visual planner and precise controls above edit the same data."));
    const editor = document.createElement("textarea"); editor.value = JSON.stringify(cameraFragment(shot), null, 2); editor.spellcheck = false; editor.setAttribute("aria-label", "Camera v2 fragment");
    const feedback = element("p", "minimax-h3-camera-data-feedback"); feedback.setAttribute("aria-live", "polite");
    const apply = actionButton("Apply camera fragment", () => {
        const parsed = parseCameraFragment(editor.value);
        if (!parsed.ok) { feedback.dataset.kind = "error"; feedback.textContent = parsed.error; editor.setAttribute("aria-invalid", "true"); return; }
        editor.removeAttribute("aria-invalid"); feedback.dataset.kind = "ready"; feedback.textContent = "Applied to this shot.";
        for (const key of ["cameraStart", "cameraPath", "cameraEnd"]) {
            if (parsed.value[key]) shot[key] = structuredClone(parsed.value[key]); else delete shot[key];
        }
        commit(); rerender();
    });
    details.append(editor, feedback, apply); container.appendChild(details);
}

export function renderVisualCameraPlanner(container, shot, project, commit, rerender) {
    ensureCameraPlannerStyles();
    const root = element("section", "minimax-h3-camera-planner");
    const heading = element("div", "minimax-h3-camera-planner-header");
    const titleBlock = element("div", "minimax-h3-camera-planner-title");
    const headingId = `minimax-h3-camera-planner-${String(shot.id ?? "shot").replace(/[^A-Za-z0-9_-]/g, "-")}`;
    const titleNode = element("h3", "", "Visual camera planner"); titleNode.id = headingId;
    titleBlock.append(titleNode, element("p", "", "Choose a start, a readable movement and an end. The result is saved directly to this shot."));
    heading.append(titleBlock, element("span", "minimax-h3-camera-planner-badge", "Direction guide · shot plan v2"));
    root.setAttribute("aria-labelledby", headingId);
    root.appendChild(heading);
    renderSpatialCameraEditor(root, shot, project, commit, rerender);
    const phaseDetails = element("details", "minimax-h3-camera-preset-disclosure");
    phaseDetails.open = !Array.isArray(shot.cameraPath?.waypoints);
    phaseDetails.appendChild(element("summary", "", Array.isArray(shot.cameraPath?.waypoints) ? "Framing & movement presets" : "Start, movement & end"));
    const phases = element("div", "minimax-h3-camera-phases");
    phases.append(
        phaseControl(shot, "cameraStart", "1", "Start frame", commit, rerender),
        movementPhase(shot, commit, rerender),
        phaseControl(shot, "cameraEnd", "3", "End frame", commit, rerender),
    );
    phaseDetails.appendChild(phases);
    const preview = element("output", "minimax-h3-camera-preview"); preview.setAttribute("aria-live", "polite");
    preview.append(element("strong", "", "Structured camera summary"), element("span", "", cameraInstructionPreview(shot)));
    root.append(phaseDetails, preview); container.appendChild(root);
}
