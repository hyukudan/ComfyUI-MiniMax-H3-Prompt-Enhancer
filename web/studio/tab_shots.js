import {
    actionButton, bindCommit, captureOpenDisclosures, checkboxPicker, element, emptyState, field, inspectorSection,
    restoreOpenDisclosures, selectInput, setOptional, textArea, textInput,
} from "./domain_components.js";
import { resolveEntryStates } from "./derive.js";
import { projectForController } from "./project_editor.js";
import { editableShotPlan, normalizeShotPlanV2, parseStructuredJson, serializeStructuredJson } from "./schema.js";
import { cameraInstructionPreview } from "./camera_planner.js";
import { effectivePictureBindingRole } from "./media_model.js";
import {
    DIALOGUE_CHANNEL_CHOICES,
    DIALOGUE_DELIVERY_CHOICES,
    normalizedDialogueControls,
    voiceColorChoices,
} from "./dialogue_catalog.js";

export const SHOT_ROW_HEIGHT = 60;
export const SHOT_OVERSCAN = 5;

export function visibleShotRange(scrollTop, viewportHeight, count) {
    const first = Math.max(0, Math.floor(scrollTop / SHOT_ROW_HEIGHT) - SHOT_OVERSCAN);
    const visible = Math.ceil(viewportHeight / SHOT_ROW_HEIGHT);
    const end = Math.min(count, first + visible + SHOT_OVERSCAN * 2);
    return { start: first, end };
}

export function shotRowModel(shot, index, timingMode, elapsedSeconds = 0) {
    const timing = timingMode === "exact" ? `${Number(elapsedSeconds).toFixed(2)}s` : "Auto";
    const action = String(shot?.action || "No action yet").trim() || "No action yet";
    const generation = String(shot?.generationId || "g1");
    return {
        title: `Shot ${index + 1}`,
        timing,
        generation,
        action,
        accessibleLabel: `Shot ${index + 1}, ${timingMode === "exact" ? `starts at ${timing}` : "automatic timing"}, generation ${generation}. ${action}`,
    };
}

const FRAMING = [["", "Unspecified"], ["extreme_close_up", "Extreme close-up"], ["close_up", "Close-up"], ["medium_close_up", "Medium close-up"], ["medium", "Medium"], ["medium_wide", "Medium wide"], ["wide", "Wide"], ["extreme_wide", "Extreme wide"]];
const ANGLE = [["", "Unspecified"], ["eye_level", "Eye level"], ["low_angle", "Low angle"], ["high_angle", "High angle"], ["overhead", "Overhead"], ["dutch_static", "Dutch"], ["worms_eye", "Worm's eye"]];
const VIEWPOINT = [["", "Unspecified"], ["pov", "POV"], ["over_the_shoulder", "Over the shoulder"], ["mirror_or_reflection", "Mirror / reflection"], ["front", "Front"], ["three_quarter", "Three-quarter"], ["profile", "Profile"], ["rear_three_quarter", "Rear three-quarter"], ["rear", "Rear"]];
const COMPOSITION = [["", "Unspecified"], ["centered", "Centered"], ["rule_of_thirds", "Rule of thirds"], ["symmetrical", "Symmetrical"], ["layered_depth", "Layered depth"], ["frame_within_frame", "Frame within frame"], ["negative_space", "Negative space"], ["two_shot", "Two-shot"], ["custom", "Custom"]];
const DISTANCE = [["", "Unspecified"], ["intimate", "Intimate"], ["near", "Near"], ["medium", "Medium"], ["far", "Far"], ["very_far", "Very far"], ["custom", "Custom"]];
const FOCUS = [["", "Unspecified"], ["single_target", "Single target"], ["split_focus", "Split focus"], ["deep_focus", "Deep focus"], ["custom", "Custom"]];
const MOTION = [["", "Unspecified"], ["static", "Static"], ["zoom_in", "Zoom in"], ["zoom_out", "Zoom out"], ["push_in", "Push in"], ["pull_out", "Pull out"], ["pan_left", "Pan left"], ["pan_right", "Pan right"], ["truck_left", "Truck left"], ["truck_right", "Truck right"], ["tilt_up", "Tilt up"], ["tilt_down", "Tilt down"], ["pedestal_up", "Pedestal up"], ["pedestal_down", "Pedestal down"], ["arc", "Arc"], ["tracking", "Tracking"], ["shake", "Shake"], ["roll_clockwise", "Roll clockwise"], ["roll_counterclockwise", "Roll counter-clockwise"]];
const TRANSITIONS = [["", "Default cut"], ["cut", "Cut"], ["match_cut", "Match cut"], ["whip_pan", "Whip pan"], ["cross_dissolve", "Cross-dissolve"], ["fade_through_black", "Fade through black"], ["hold", "Hold"]];
const PRESENCE = [["", "Not declared"], ["present", "Present"], ["enters", "Enters"], ["exits", "Exits"], ["absent", "Absent"]];
const REFERENCE_ROLES = ["identity_reinforcement", "appearance", "environment_view", "scale", "placement", "continuity", "lighting", "composition", "performance", "voice", "exact_dialogue", "soundtrack", "camera_transfer"].map((value) => [value, value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase())]);
const CAMERA_ASPECTS = ["motion", "framing", "angle", "viewpoint", "composition", "focus", "distance", "stability", "lens", "parallax"];
const CHANGE_TIMING = [["at_cut", "At cut"], ["during_shot", "During shot"], ["at_end", "At end"], ["custom", "Custom"]];

export function shotProject(controller) {
    const project = projectForController(controller);
    return project ?? { schemaVersion: 2, assets: [], subjects: [], environments: [], generations: [] };
}

function generationIds(project, controller) {
    const ids = project.generations?.map((generation) => generation.id).filter(Boolean) ?? [];
    return ids.length ? ids : controller.generationIds();
}

export function commitPlan(controller, state) {
    return controller.commitShotPlan(serializeStructuredJson(normalizeShotPlanV2(state.plan)));
}

function readOnlyShotPlan(container, documentState, controller) {
    const status = element("div", "minimax-h3-studio-status", `The raw shot plan is ${documentState?.kind ?? "unavailable"}. It is preserved read-only.`);
    status.dataset.kind = documentState?.kind ?? "malformed";
    container.appendChild(status);
    if (documentState?.kind !== "malformed") return;
    const raw = textArea(documentState.raw); raw.className = "minimax-h3-source-editor"; raw.setAttribute("aria-label", "Raw shot plan JSON");
    const apply = actionButton("Parse and apply", () => {
        const parsed = parseStructuredJson(raw.value, { supportedVersions: [1, 2] });
        if (!['v1', 'v2'].includes(parsed.kind)) { raw.setAttribute("aria-invalid", "true"); return; }
        raw.removeAttribute("aria-invalid"); controller.replaceShotRaw(raw.value);
    });
    container.append(raw, apply);
}

function nextShotId(shots) {
    const used = new Set(shots.map((shot) => shot.id));
    let index = shots.length + 1;
    while (used.has(`s${index}`)) index += 1;
    return `s${index}`;
}

function targetChoices(project, kind) {
    if (kind === "subject") return project.subjects ?? [];
    if (kind === "environment") return project.environments ?? [];
    if (kind === "asset") return project.assets ?? [];
    return [];
}

function targetEditor(label, target, project, onChange) {
    const root = element("fieldset", "minimax-h3-target-editor");
    root.appendChild(element("legend", "", label));
    const kind = selectInput(target?.kind ?? "", [["", "None"], ["subject", "Subject"], ["environment", "Environment"], ["asset", "Media asset"], ["text", "Free text"]]);
    root.appendChild(kind);
    const renderValue = () => {
        root.querySelector("[data-target-value]")?.remove();
        if (!kind.value) return;
        let control;
        if (kind.value === "text") {
            control = textInput(target?.kind === "text" ? target.text : "", { placeholder: "Visible target" });
            control.addEventListener("change", () => onChange(control.value.trim() ? { kind: "text", text: control.value.trim() } : null));
        } else {
            const items = targetChoices(project, kind.value);
            control = selectInput(target?.kind === kind.value ? target.id : "", [["", `Select ${kind.value}…`], ...items.map((item) => [item.id, item.name || item.id])]);
            control.addEventListener("change", () => onChange(control.value ? { kind: kind.value, id: control.value } : null));
        }
        control.dataset.targetValue = "true"; root.appendChild(control);
    };
    kind.addEventListener("change", () => { onChange(null); renderValue(); }); renderValue();
    return root;
}

export function renderFrame(container, shot, key, label, project, provenance, commit, rerender) {
    const section = inspectorSection(label, key === "cameraEnd" && !shot.cameraEnd ? "inherits start" : "Framing, composition and focus", key === "cameraStart");
    const frame = shot[key] ?? {};
    const bindFrame = (property, choices, fieldLabel) => {
        const control = selectInput(frame[property], choices);
        bindCommit(control, (value) => {
            const target = shot[key] ?? (shot[key] = {}); setOptional(target, property, value);
            if (!Object.keys(target).length) delete shot[key];
        }, commit);
        section.body.appendChild(field(fieldLabel, control));
        const source = provenance?.[property];
        if (source) {
            const line = element("small", source.conflict ? "minimax-h3-provenance is-conflict" : "minimax-h3-provenance", `Defined by: ${source.label}`);
            section.body.appendChild(line);
        }
    };
    bindFrame("framing", FRAMING, "Framing"); bindFrame("angle", ANGLE, "Angle"); bindFrame("viewpoint", VIEWPOINT, "Viewpoint");
    bindFrame("composition", COMPOSITION, "Composition");
    const compositionNote = textInput(frame.compositionNote, { placeholder: "Required when composition is custom" });
    bindCommit(compositionNote, (value) => {
        const target = shot[key] ?? (shot[key] = {}); setOptional(target, "compositionNote", value.trim());
    }, commit);
    section.body.appendChild(field("Composition note", compositionNote));
    bindFrame("distance", DISTANCE, "Distance");
    const distanceNote = textInput(frame.distanceNote, { placeholder: "Required when distance is custom" });
    bindCommit(distanceNote, (value) => {
        const target = shot[key] ?? (shot[key] = {}); setOptional(target, "distanceNote", value.trim());
    }, commit);
    section.body.appendChild(field("Distance note", distanceNote));

    for (const [property, targetLabel] of [["primaryTarget", "Primary target"], ["secondaryTarget", "Secondary target"], ["foregroundTarget", "Foreground target"]]) {
        section.body.appendChild(targetEditor(targetLabel, frame[property], project, (value) => {
            const targetFrame = shot[key] ?? (shot[key] = {}); setOptional(targetFrame, property, value); commit();
        }));
    }
    const focusMode = selectInput(frame.focus?.mode ?? "", FOCUS);
    focusMode.addEventListener("change", () => {
        const targetFrame = shot[key] ?? (shot[key] = {});
        if (!focusMode.value) delete targetFrame.focus;
        else targetFrame.focus = { ...(targetFrame.focus ?? {}), mode: focusMode.value };
        commit(); rerender();
    });
    section.body.appendChild(field("Focus", focusMode));
    if (frame.focus) {
        section.body.appendChild(targetEditor("Focus primary target", frame.focus.primaryTarget, project, (value) => { setOptional(frame.focus, "primaryTarget", value); commit(); }));
        section.body.appendChild(targetEditor("Focus secondary target", frame.focus.secondaryTarget, project, (value) => { setOptional(frame.focus, "secondaryTarget", value); commit(); }));
        const focusNote = textInput(frame.focus.note, { placeholder: "Focus behavior or custom detail" });
        bindCommit(focusNote, (value) => setOptional(frame.focus, "note", value.trim()), commit);
        section.body.appendChild(field("Focus note", focusNote));
    }
    container.appendChild(section.details);
}

function renderStory(container, shot, commit, rerender, basicPrompt = "") {
    const section = inspectorSection("Story", shot.action || "No action yet", true);
    const opening = textArea(shot.openingState, "What is visible in the first frame");
    bindCommit(opening, (value) => setOptional(shot, "openingState", value.trim()), commit, "blur");
    const action = textArea(shot.action, "What visibly changes during this shot"); action.dataset.shotAction = "true";
    const inheritsBasicPrompt = !String(shot.action ?? "").trim() && Boolean(String(basicPrompt).trim());
    if (!String(shot.action ?? "").trim() && !inheritsBasicPrompt) action.setAttribute("aria-invalid", "true");
    bindCommit(action, (value) => { shot.action = value.trim(); }, commit, "blur");
    action.addEventListener("blur", () => rerender());
    section.body.append(
        field("Opening state", opening, "The first visible frame."),
        field("Action", action, "Movement, change and final visible result."),
    );
    if (!String(shot.action ?? "").trim()) {
        const required = element(
            "p", "minimax-h3-studio-status",
            inheritsBasicPrompt
                ? "This single Shot uses the Basic prompt as its Action. Save a separate Action only when you want different wording."
                : "Action is required before this Shot can generate.",
        );
        required.dataset.kind = inheritsBasicPrompt ? "info" : "error";
        section.body.appendChild(required);
        if (String(basicPrompt).trim()) {
            section.body.appendChild(actionButton("Use Basic prompt as Action", () => {
                shot.action = String(basicPrompt).trim();
                commit();
                rerender("[data-shot-action]");
            }));
        }
    }
    container.appendChild(section.details);
}

function nextBeatId(beats) {
    const used = new Set(beats.map((beat) => beat.id)); let index = beats.length + 1;
    while (used.has(`beat${index}`)) index += 1;
    return `beat${index}`;
}

function renderActionBeats(container, shot, project, commit, rerender) {
    const beats = shot.actionBeats ?? [];
    const section = inspectorSection("Action beats", beats.length ? `${beats.length} timed` : "Optional rhythm", false);
    section.body.appendChild(element("p", "minimax-h3-field-hint", "Use beats only when order or rhythm matters. Their percentages stay relative if the clip duration changes."));
    const add = actionButton("+ Add beat", () => {
        shot.actionBeats ??= [];
        const count = shot.actionBeats.length;
        const at = count ? Math.min(.95, Math.round(((count + 1) / (count + 2)) * 100) / 100) : .5;
        shot.actionBeats.push({ id: nextBeatId(shot.actionBeats), at, action: "" });
        shot.actionBeats.sort((a, b) => a.at - b.at); commit(); rerender();
    }, { disabled: beats.length >= 12 });
    add.className += " minimax-h3-button minimax-h3-button-secondary"; section.body.appendChild(add);
    for (const [index, beat] of beats.entries()) {
        const card = element("article", "minimax-h3-action-beat");
        const header = element("div", "minimax-h3-action-beat-header");
        const spanLabel = beat.endAt !== undefined
            ? `${Math.round(Number(beat.at) * 100)}–${Math.round(Number(beat.endAt) * 100)}%`
            : `${Math.round(Number(beat.at) * 100)}%`;
        header.append(element("strong", "", `Beat ${index + 1}`), element("span", "", spanLabel));
        header.appendChild(actionButton("Remove", () => {
            shot.actionBeats.splice(index, 1); if (!shot.actionBeats.length) delete shot.actionBeats; commit(); rerender();
        }, { danger: true })); card.appendChild(header);
        const timing = document.createElement("input"); timing.type = "range"; timing.min = index ? String(Number(beats[index - 1].at) + .01) : "0"; timing.max = index < beats.length - 1 ? String(Number(beats[index + 1].at) - .01) : "1"; timing.step = ".01"; timing.value = String(beat.at); timing.setAttribute("aria-label", `Beat ${index + 1} timing`);
        timing.addEventListener("change", () => { beat.at = Math.round(Number(timing.value) * 100) / 100; commit(); rerender(); }); card.appendChild(timing);
        const spanEnabled = document.createElement("input"); spanEnabled.type = "checkbox"; spanEnabled.checked = beat.endAt !== undefined;
        spanEnabled.addEventListener("change", () => {
            if (spanEnabled.checked) beat.endAt = Math.min(1, Math.max(Number(beat.at) + .01, Number(beats[index + 1]?.at ?? 1)));
            else delete beat.endAt;
            commit(); rerender();
        });
        card.appendChild(field("Reserve a time span", spanEnabled, "Use a span when dialogue or an action must fit inside a bounded part of the shot."));
        if (beat.endAt !== undefined) {
            const end = document.createElement("input"); end.type = "range"; end.min = String(Number(beat.at) + .01); end.max = "1"; end.step = ".01"; end.value = String(beat.endAt); end.setAttribute("aria-label", `Beat ${index + 1} end timing`);
            end.addEventListener("change", () => { beat.endAt = Math.round(Number(end.value) * 100) / 100; commit(); rerender(); });
            card.appendChild(field("End of beat", end, `${Math.round(Number(beat.endAt) * 100)}% of this shot.`));
        }
        const action = textArea(beat.action, "Visible action or reaction at this beat");
        bindCommit(action, (value) => {
            const text = value.trim();
            if (text) beat.action = text;
            else delete beat.action;
        }, commit, "blur"); card.appendChild(field("Action / reaction", action));
        const dialogueToggle = document.createElement("input"); dialogueToggle.type = "checkbox"; dialogueToggle.checked = Boolean(beat.dialogue);
        dialogueToggle.addEventListener("change", () => {
            if (dialogueToggle.checked) beat.dialogue = { text: "", delivery: "says" };
            else delete beat.dialogue;
            commit(); rerender();
        });
        card.appendChild(field("Dialogue at this beat", dialogueToggle));
        if (beat.dialogue) {
            const controls = normalizedDialogueControls(beat.dialogue);
            const dialogueGrid = element("div", "minimax-h3-action-beat-dialogue");
            const speaker = selectInput(beat.dialogue.speakerId ?? "", [["", "Unspecified speaker"], ...(project.subjects ?? []).map((subject) => [subject.id, subject.name || subject.id])], { ariaLabel: `Beat ${index + 1} speaker` });
            bindCommit(speaker, (value) => setOptional(beat.dialogue, "speakerId", value), commit);
            const channel = selectInput(controls.channel, DIALOGUE_CHANNEL_CHOICES, { ariaLabel: `Beat ${index + 1} channel` });
            bindCommit(channel, (value) => setOptional(beat.dialogue, "channel", value === "voice_over" ? value : ""), commit);
            const delivery = selectInput(controls.delivery, DIALOGUE_DELIVERY_CHOICES, { ariaLabel: `Beat ${index + 1} delivery` });
            bindCommit(delivery, (value) => { beat.dialogue.delivery = value; }, commit);
            const voiceColor = selectInput(controls.mood, voiceColorChoices(controls.mood), { ariaLabel: `Beat ${index + 1} voice color` });
            bindCommit(voiceColor, (value) => setOptional(beat.dialogue, "mood", value), commit);
            dialogueGrid.append(field("Speaker", speaker), field("Channel", channel), field("Delivery", delivery), field("Voice color", voiceColor));
            const text = textInput(beat.dialogue.text, { placeholder: "Exact spoken words" });
            bindCommit(text, (value) => { beat.dialogue.text = value.trim(); }, commit);
            const customTone = textInput(controls.mood, { placeholder: "Optional custom tone" });
            bindCommit(customTone, (value) => setOptional(beat.dialogue, "mood", value.trim()), commit, "blur");
            dialogueGrid.append(field("Spoken words", text), field("Custom tone", customTone, "Use this only when the Voice color catalog does not cover the performance.")); card.appendChild(dialogueGrid);
        }
        section.body.appendChild(card);
    }
    container.appendChild(section.details);
}

function renderTiming(container, shot, plan, commit, rerender) {
    const section = inspectorSection("Timing & cut", plan.timingMode === "exact" ? `${shot.durationSeconds ?? 1}s` : "Auto timing", false);
    const transition = selectInput(shot.transitionIn, TRANSITIONS);
    bindCommit(transition, (value) => setOptional(shot, "transitionIn", value), commit);
    section.body.appendChild(field("Transition in", transition));
    if (plan.timingMode === "exact") {
        const duration = textInput(shot.durationSeconds ?? 1, { type: "number" }); duration.min = "0.01"; duration.max = "150"; duration.step = "0.01";
        bindCommit(duration, (value) => { shot.durationSeconds = Math.max(0.01, Math.min(150, Number(value) || 1)); }, commit);
        section.body.appendChild(field("Duration (seconds)", duration));
    }
    const enabled = document.createElement("input"); enabled.type = "checkbox"; enabled.checked = Boolean(shot.cutContext);
    enabled.addEventListener("change", () => { if (enabled.checked) shot.cutContext = { timeRelation: "continuous", purpose: "unspecified" }; else delete shot.cutContext; commit(); rerender(); });
    section.body.appendChild(field("Describe cut context", enabled));
    if (shot.cutContext) {
        const relation = selectInput(shot.cutContext.timeRelation, [["continuous", "Continuous"], ["later", "Later"], ["earlier", "Earlier"], ["parallel", "Parallel"], ["unknown", "Unknown"]]);
        bindCommit(relation, (value) => { shot.cutContext.timeRelation = value; }, commit);
        const purpose = selectInput(shot.cutContext.purpose, [["subject", "Subject"], ["space", "Space"], ["state", "State"], ["viewpoint", "Viewpoint"], ["time", "Time"], ["rhythm", "Rhythm"], ["unspecified", "Unspecified"]]);
        bindCommit(purpose, (value) => { shot.cutContext.purpose = value; }, commit);
        section.body.append(field("Time relation", relation), field("Cut purpose", purpose));
    }
    container.appendChild(section.details);
}

function renderPresence(container, shot, project, entry, commit, rerender) {
    const declared = new Map((shot.subjects ?? []).map((item) => [item.subjectId, item]));
    const section = inspectorSection("Who's in it", `${declared.size} declared`, false);
    const complete = document.createElement("input"); complete.type = "checkbox"; complete.checked = Boolean(shot.subjectPresenceComplete);
    complete.addEventListener("change", () => {
        if (complete.checked) {
            shot.subjectPresenceComplete = true;
            shot.subjects ??= [];
            for (const subject of project.subjects ?? []) {
                if (!shot.subjects.some((item) => item.subjectId === subject.id)) shot.subjects.push({ subjectId: subject.id, presence: "absent" });
            }
        } else delete shot.subjectPresenceComplete;
        commit(); rerender();
    });
    section.body.appendChild(field("Full presence declared", complete, "When enabled, every project subject should be marked, including absent subjects."));
    for (const subject of project.subjects ?? []) {
        const row = element("div", "minimax-h3-presence-row");
        const presence = declared.get(subject.id);
        const control = selectInput(presence?.presence ?? "", shot.subjectPresenceComplete ? PRESENCE.slice(1) : PRESENCE, { ariaLabel: `${subject.name} presence` });
        control.dataset.subjectPresence = subject.id;
        control.addEventListener("change", () => {
            shot.subjects ??= [];
            const index = shot.subjects.findIndex((item) => item.subjectId === subject.id);
            if (!control.value && index >= 0) shot.subjects.splice(index, 1);
            else if (control.value && index >= 0) shot.subjects[index].presence = control.value;
            else if (control.value) shot.subjects.push({ subjectId: subject.id, presence: control.value });
            if (!shot.subjects.length) delete shot.subjects;
            commit(); rerender(`[data-subject-presence="${subject.id}"]`);
        });
        row.append(element("strong", "", subject.name || subject.id), control, element("small", "minimax-h3-state-chip", `Entry: ${entry?.subjects?.[subject.id] ?? subject.baseAppearanceStateId}`));
        if (presence && presence.presence !== "absent") {
            const blocking = textInput(presence.blocking, { placeholder: "Blocking / position" });
            bindCommit(blocking, (value) => setOptional(presence, "blocking", value.trim()), commit);
            row.appendChild(blocking);
        }
        section.body.appendChild(row);
    }
    if (!(project.subjects ?? []).length) section.body.appendChild(element("p", "minimax-h3-field-hint", "Create subjects first; they will appear here as selectable cast."));
    container.appendChild(section.details);
}

const SCALE_RELATIONS = [
    ["same_height", "Same height"], ["slightly_taller", "Slightly taller"], ["taller", "Clearly taller"],
    ["twice_height", "About twice as tall"], ["slightly_shorter", "Slightly shorter"],
    ["shorter", "Clearly shorter"], ["half_height", "About half as tall"], ["custom", "Custom visible relationship"],
];

function renderScaleRelationships(container, shot, project, commit, rerender) {
    const relationships = shot.scaleRelationships ?? [];
    const section = inspectorSection("Relative scale", relationships.length ? `${relationships.length} relationships` : "Optional", false);
    section.body.appendChild(element("p", "minimax-h3-field-hint", "Describe visible size relationships without inventing metres or exact measurements."));
    const choices = (project.subjects ?? []).map((subject) => [subject.id, subject.name || subject.id]);
    const add = actionButton("+ Add scale relationship", () => {
        if (choices.length < 2) return;
        shot.scaleRelationships ??= [];
        shot.scaleRelationships.push({ subjectId: choices[0][0], relativeToId: choices[1][0], relation: "same_height" });
        commit(); rerender();
    }, { disabled: choices.length < 2 || relationships.length >= 16 });
    add.className += " minimax-h3-button minimax-h3-button-secondary";
    section.body.appendChild(add);
    if (choices.length < 2) section.body.appendChild(element("p", "minimax-h3-field-hint", "Create at least two subjects to compare their visible scale."));
    for (const [index, relationship] of relationships.entries()) {
        const row = element("article", "minimax-h3-scale-relationship");
        const subject = selectInput(relationship.subjectId, choices, { ariaLabel: `Scale relationship ${index + 1} subject` });
        bindCommit(subject, (value) => { relationship.subjectId = value; }, commit);
        const relation = selectInput(relationship.relation, SCALE_RELATIONS, { ariaLabel: `Scale relationship ${index + 1} relation` });
        relation.addEventListener("change", () => { relationship.relation = relation.value; if (relation.value !== "custom") delete relationship.note; commit(); rerender(); });
        const landmark = selectInput(relationship.relativeToId, choices, { ariaLabel: `Scale relationship ${index + 1} comparison subject` });
        bindCommit(landmark, (value) => { relationship.relativeToId = value; }, commit);
        row.append(field("Subject", subject), field("Relationship", relation), field("Compared with", landmark));
        if (relationship.relation === "custom") {
            const note = textInput(relationship.note, { placeholder: "Visible relationship, without exact units" });
            bindCommit(note, (value) => setOptional(relationship, "note", value.trim()), commit);
            row.appendChild(field("Custom relationship", note));
        }
        row.appendChild(actionButton("Remove", () => {
            shot.scaleRelationships.splice(index, 1); if (!shot.scaleRelationships.length) delete shot.scaleRelationships; commit(); rerender();
        }, { danger: true }));
        section.body.appendChild(row);
    }
    container.appendChild(section.details);
}

function renderEnvironment(container, shot, project, entry, commit, rerender) {
    const environment = project.environments?.find((item) => item.id === shot.environment?.environmentId);
    const section = inspectorSection("Where", environment?.name || "No environment", false);
    const picker = selectInput(shot.environment?.environmentId ?? "", [["", "No environment"], ...(project.environments ?? []).map((item) => [item.id, item.name || item.id])]);
    picker.addEventListener("change", () => {
        if (!picker.value) delete shot.environment;
        else shot.environment = { environmentId: picker.value, viewIds: [] };
        commit(); rerender();
    });
    section.body.appendChild(field("Environment", picker));
    if (environment) {
        const entryState = entry?.environments?.[environment.id] ?? environment.defaultStateId;
        const state = environment.states?.find((item) => item.id === entryState);
        section.body.appendChild(element("p", "minimax-h3-state-chip", `Entry state: ${state?.name || entryState || "Unspecified"}`));
        const views = (environment.views ?? []).map((view) => ({ id: view.id, label: `${view.name || view.id} · ${view.role}` }));
        section.body.appendChild(field("Views used", checkboxPicker(views, shot.environment.viewIds, (ids) => {
            shot.environment.viewIds = ids; commit();
        }, "Environment views")));
    }
    container.appendChild(section.details);
}

function activeAssets(project, generationId) {
    const generation = project.generations?.find((item) => item.id === generationId);
    if (!generation) return [];
    const bound = new Set((generation.bindings ?? []).map((binding) => binding.assetId));
    return (project.assets ?? []).filter((asset) => bound.has(asset.id) && asset.available !== false);
}

function renderReferences(container, shot, project, commit, rerender) {
    const uses = shot.referenceUses ?? [];
    const available = activeAssets(project, shot.generationId);
    const section = inspectorSection("Uses references", `${uses.length} references`, false);
    for (const [index, use] of uses.entries()) {
        const row = element("fieldset", "minimax-h3-reference-use"); row.appendChild(element("legend", "", `Reference ${index + 1}`));
        const asset = selectInput(use.assetId, [["", "Select bound media…"], ...available.map((item) => [item.id, item.name || item.id])]);
        asset.addEventListener("change", () => {
            use.assetId = asset.value;
            if (use.role === "camera_transfer") {
                const source = project.assets?.find((item) => item.id === use.assetId);
                if (source?.type !== "video" || source.cameraTransfer?.enabled !== true) {
                    use.role = "continuity"; delete use.cameraAspects;
                } else use.cameraAspects = [...source.cameraTransfer.aspects];
            }
            commit(); rerender();
        });
        const sourceAsset = project.assets?.find((item) => item.id === use.assetId);
        const cameraRoleAvailable = sourceAsset?.type === "video" && sourceAsset.cameraTransfer?.enabled === true;
        const roleChoices = REFERENCE_ROLES.filter(([token]) => token !== "camera_transfer" || cameraRoleAvailable || use.role === "camera_transfer");
        const role = selectInput(use.role, roleChoices);
        role.addEventListener("change", () => {
            use.role = role.value;
            if (role.value === "camera_transfer") {
                const source = project.assets?.find((item) => item.id === use.assetId);
                use.cameraAspects = [...(source?.cameraTransfer?.aspects ?? ["motion"])];
            } else delete use.cameraAspects;
            commit(); rerender();
        });
        row.append(field("Media", asset), field("Role", role));
        const targetItems = [
            ...(project.subjects ?? []).map((item) => ({ id: item.id, label: `Subject · ${item.name || item.id}` })),
            ...(project.environments ?? []).map((item) => ({ id: item.id, label: `Environment · ${item.name || item.id}` })),
            ...(project.assets ?? []).map((item) => ({ id: item.id, label: `Media · ${item.name || item.id}` })),
        ];
        row.appendChild(field("Targets", checkboxPicker(targetItems, use.targetIds, (ids) => {
            if (ids.length) use.targetIds = ids; else delete use.targetIds; commit();
        }, `Targets for reference ${index + 1}`)));
        if (use.role === "camera_transfer") {
            const source = project.assets?.find((item) => item.id === use.assetId);
            const allowed = source?.cameraTransfer?.aspects ?? [];
            row.appendChild(field("Camera aspects", checkboxPicker(
                CAMERA_ASPECTS.filter((aspect) => allowed.includes(aspect)).map((aspect) => ({ id: aspect, label: aspect })),
                use.cameraAspects,
                (ids) => { if (!ids.length) { rerender(); return; } use.cameraAspects = ids; commit(); },
                `Camera aspects for reference ${index + 1}`,
            ), allowed.length ? "Limited to aspects declared by this video." : "This video has no enabled camera transfer aspects."));
        }
        const note = textInput(use.note, { placeholder: "Optional use note" }); bindCommit(note, (value) => setOptional(use, "note", value.trim()), commit);
        row.append(field("Note", note), actionButton("Remove reference", () => { uses.splice(index, 1); if (!uses.length) delete shot.referenceUses; commit(); rerender(); }, { danger: true }));
        section.body.appendChild(row);
    }
    section.body.appendChild(actionButton("+ Reference", () => {
        (shot.referenceUses ??= []).push({ assetId: available[0].id, role: "continuity" }); commit(); rerender();
    }, { disabled: !available.length }));
    if (!available.length) section.body.appendChild(element("p", "minimax-h3-usage-note", `No available file is active in ${shot.generationId}. Add or activate it in Library · Files first.`));
    container.appendChild(section.details);
}

export function renderCameraPath(container, shot, provenance, commit, rerender) {
    const path = shot.cameraPath ?? {};
    const section = inspectorSection("Camera path", path.motionType || "No movement override", false);
    const motion = selectInput(path.motionType, MOTION);
    motion.addEventListener("change", () => {
        if (!motion.value) delete shot.cameraPath;
        else if (motion.value === "static") shot.cameraPath = { motionType: "static" };
        else shot.cameraPath = { ...(shot.cameraPath ?? {}), motionType: motion.value };
        commit(); rerender();
    });
    section.body.appendChild(field("Motion", motion));
    if (provenance?.motion) section.body.appendChild(element("small", provenance.motion.conflict ? "minimax-h3-provenance is-conflict" : "minimax-h3-provenance", `Defined by: ${provenance.motion.label}`));
    if (path.motionType && path.motionType !== "static") {
        for (const [property, label, choices] of [
            ["amplitude", "Amplitude", [["", "Unspecified"], ["small", "Small"], ["medium", "Medium"], ["large", "Large"]]],
            ["speed", "Speed", [["", "Unspecified"], ["slow", "Slow"], ["normal", "Normal"], ["fast", "Fast"]]],
            ["easing", "Easing", [["", "Unspecified"], ["linear", "Linear"], ["ease_in", "Ease in"], ["ease_out", "Ease out"], ["ease_in_out", "Ease in/out"]]],
            ["timing", "Timing", [["", "Unspecified"], ["throughout", "Throughout"], ["during_opening", "During opening"], ["after_opening", "After opening"], ["during_action", "During action"], ["during_dialogue", "During dialogue"], ["after_dialogue", "After dialogue"], ["before_cut", "Before cut"]]],
        ]) {
            const control = selectInput(path[property], choices); bindCommit(control, (value) => setOptional(shot.cameraPath, property, value), commit);
            section.body.appendChild(field(label, control));
        }
    }
    container.appendChild(section.details);
}

function renderAppearanceTransitions(container, shot, project, entry, commit, rerender) {
    const transitions = shot.appearanceTransitions ?? [];
    const section = inspectorSection("Appearance changes", `${transitions.length} changes`, false);
    for (const [index, transition] of transitions.entries()) {
        const row = element("fieldset", "minimax-h3-transition-row"); row.appendChild(element("legend", "", `Appearance change ${index + 1}`));
        const subject = project.subjects?.find((item) => item.id === transition.subjectId);
        const resolvedFrom = entry?.subjects?.[transition.subjectId] ?? subject?.baseAppearanceStateId ?? transition.fromStateId;
        const commitTransition = () => { transition.fromStateId = resolvedFrom; commit(); };
        const subjectPicker = selectInput(transition.subjectId, (project.subjects ?? []).map((item) => [item.id, item.name || item.id]));
        subjectPicker.addEventListener("change", () => {
            const next = project.subjects.find((item) => item.id === subjectPicker.value); transition.subjectId = next.id;
            transition.fromStateId = entry?.subjects?.[next.id] ?? next.baseAppearanceStateId;
            transition.toStateId = next.appearanceStates?.find((state) => state.id !== transition.fromStateId)?.id ?? transition.fromStateId;
            commit(); rerender();
        });
        row.append(field("Subject", subjectPicker), element("p", "minimax-h3-state-chip", `From entry: ${resolvedFrom}`));
        const to = selectInput(transition.toStateId, (subject?.appearanceStates ?? []).map((state) => [state.id, state.name || state.id]));
        bindCommit(to, (value) => { transition.toStateId = value; }, commitTransition);
        const timing = selectInput(transition.timing, CHANGE_TIMING); bindCommit(timing, (value) => { transition.timing = value; }, commitTransition);
        const trigger = textInput(transition.trigger, { placeholder: "What causes the change" }); bindCommit(trigger, (value) => setOptional(transition, "trigger", value.trim()), commitTransition);
        const mechanism = textInput(transition.mechanism, { placeholder: "How it visibly happens" }); bindCommit(mechanism, (value) => setOptional(transition, "mechanism", value.trim()), commitTransition);
        row.append(field("To", to), field("When", timing), field("Trigger", trigger), field("Mechanism", mechanism));
        row.appendChild(actionButton("Remove change", () => { transitions.splice(index, 1); if (!transitions.length) delete shot.appearanceTransitions; commit(); rerender(); }, { danger: true }));
        section.body.appendChild(row);
    }
    section.body.appendChild(actionButton("+ Appearance change", () => {
        const subject = project.subjects[0]; const from = entry?.subjects?.[subject.id] ?? subject.baseAppearanceStateId;
        const to = subject.appearanceStates?.find((state) => state.id !== from)?.id ?? from;
        (shot.appearanceTransitions ??= []).push({ subjectId: subject.id, fromStateId: from, toStateId: to, timing: "during_shot" });
        commit(); rerender();
    }, { disabled: !(project.subjects ?? []).length }));
    container.appendChild(section.details);
}

function renderEnvironmentTransitions(container, shot, project, entry, commit, rerender) {
    const transitions = shot.environmentTransitions ?? [];
    const section = inspectorSection("Environment changes", `${transitions.length} changes`, false);
    for (const [index, transition] of transitions.entries()) {
        const row = element("fieldset", "minimax-h3-transition-row"); row.appendChild(element("legend", "", `Environment change ${index + 1}`));
        const environment = project.environments?.find((item) => item.id === transition.environmentId);
        const resolvedFrom = entry?.environments?.[transition.environmentId] ?? environment?.defaultStateId ?? transition.fromStateId;
        const commitTransition = () => { transition.fromStateId = resolvedFrom; commit(); };
        const picker = selectInput(transition.environmentId, (project.environments ?? []).map((item) => [item.id, item.name || item.id]));
        picker.addEventListener("change", () => {
            const next = project.environments.find((item) => item.id === picker.value); transition.environmentId = next.id;
            transition.fromStateId = entry?.environments?.[next.id] ?? next.defaultStateId;
            transition.toStateId = next.states?.find((state) => state.id !== transition.fromStateId)?.id ?? transition.fromStateId;
            commit(); rerender();
        });
        row.append(field("Environment", picker), element("p", "minimax-h3-state-chip", `From entry: ${resolvedFrom}`));
        const to = selectInput(transition.toStateId, (environment?.states ?? []).map((state) => [state.id, state.name || state.id])); bindCommit(to, (value) => { transition.toStateId = value; }, commitTransition);
        const timing = selectInput(transition.timing, CHANGE_TIMING); bindCommit(timing, (value) => { transition.timing = value; }, commitTransition);
        const trigger = textInput(transition.trigger, { placeholder: "What causes the change" }); bindCommit(trigger, (value) => setOptional(transition, "trigger", value.trim()), commitTransition);
        const mechanism = textInput(transition.mechanism, { placeholder: "How it visibly happens" }); bindCommit(mechanism, (value) => setOptional(transition, "mechanism", value.trim()), commitTransition);
        row.append(field("To", to), field("When", timing), field("Trigger", trigger), field("Mechanism", mechanism));
        row.appendChild(actionButton("Remove change", () => { transitions.splice(index, 1); if (!transitions.length) delete shot.environmentTransitions; commit(); rerender(); }, { danger: true }));
        section.body.appendChild(row);
    }
    section.body.appendChild(actionButton("+ Environment change", () => {
        const environment = project.environments[0]; const from = entry?.environments?.[environment.id] ?? environment.defaultStateId;
        const to = environment.states?.find((state) => state.id !== from)?.id ?? from;
        (shot.environmentTransitions ??= []).push({ environmentId: environment.id, fromStateId: from, toStateId: to, timing: "during_shot" });
        commit(); rerender();
    }, { disabled: !(project.environments ?? []).length }));
    container.appendChild(section.details);
}

function renderShotList(list, state, selectShot, reorder) {
    list.replaceChildren(); list.className = "minimax-h3-virtual-list"; list.setAttribute("role", "listbox"); list.setAttribute("aria-label", "Shots");
    const spacer = element("div", "minimax-h3-virtual-spacer"); spacer.style.height = `${state.plan.shots.length * SHOT_ROW_HEIGHT}px`; list.appendChild(spacer);
    let draggedId = null;
    const drawRows = () => {
        state.listScroll = list.scrollTop; spacer.replaceChildren();
        const range = visibleShotRange(list.scrollTop, list.clientHeight || 440, state.plan.shots.length);
        let elapsed = state.plan.shots.slice(0, range.start).reduce((sum, shot) => sum + (state.plan.timingMode === "exact" ? Number(shot.durationSeconds || 0) : 0), 0);
        for (let index = range.start; index < range.end; index += 1) {
            const shot = state.plan.shots[index]; const row = element("button", "minimax-h3-virtual-row"); row.type = "button";
            row.style.top = `${index * SHOT_ROW_HEIGHT}px`; row.dataset.shotId = shot.id; row.draggable = true;
            row.setAttribute("role", "option"); row.setAttribute("aria-selected", String(shot.id === state.selectedId));
            const summary = shotRowModel(shot, index, state.plan.timingMode, elapsed);
            const primary = element("span", "minimax-h3-shot-row-primary");
            primary.append(
                element("strong", "minimax-h3-shot-row-title", summary.title),
                element("span", "minimax-h3-shot-row-chip", summary.timing),
                element("span", "minimax-h3-shot-row-chip minimax-h3-shot-row-generation", summary.generation),
            );
            const action = element("span", "minimax-h3-shot-row-action", summary.action);
            action.setAttribute("title", summary.action);
            row.setAttribute("aria-label", summary.accessibleLabel);
            row.append(primary, action);
            elapsed += state.plan.timingMode === "exact" ? Number(shot.durationSeconds || 0) : 0;
            row.addEventListener("click", () => selectShot(shot.id));
            row.addEventListener("dragstart", (event) => { draggedId = shot.id; event.dataTransfer?.setData("text/plain", shot.id); });
            row.addEventListener("dragover", (event) => event.preventDefault());
            row.addEventListener("drop", (event) => { event.preventDefault(); if (draggedId && draggedId !== shot.id) reorder(draggedId, shot.id); });
            spacer.appendChild(row);
        }
    };
    list.addEventListener("scroll", drawRows, { passive: true });
    list.addEventListener("keydown", (event) => {
        const current = state.plan.shots.findIndex((shot) => shot.id === state.selectedId);
        if (event.altKey && ["ArrowUp", "ArrowDown"].includes(event.key)) {
            event.preventDefault(); reorder(state.selectedId, state.plan.shots[current + (event.key === "ArrowUp" ? -1 : 1)]?.id); return;
        }
        if (!["ArrowUp", "ArrowDown"].includes(event.key)) return;
        event.preventDefault(); const next = state.plan.shots[current + (event.key === "ArrowUp" ? -1 : 1)]; if (next) selectShot(next.id);
    });
    list.scrollTop = state.listScroll ?? 0; drawRows();
}

export function shotTimelineModel(plan = {}) {
    const shots = Array.isArray(plan.shots) ? plan.shots : [];
    const exact = plan.timingMode === "exact";
    const durations = shots.map((shot) => exact ? Math.max(0.01, Number(shot?.durationSeconds) || 1) : 1);
    const total = durations.reduce((sum, duration) => sum + duration, 0);
    let elapsed = 0;
    return shots.map((shot, index) => {
        const duration = durations[index];
        const item = {
            id: shot.id,
            index,
            title: `Shot ${index + 1}`,
            action: String(shot.action ?? "").trim() || "No action yet",
            start: exact ? elapsed : null,
            end: exact ? elapsed + duration : null,
            duration: exact ? duration : null,
            width: total > 0 ? duration / total * 100 : 100 / Math.max(1, shots.length),
        };
        elapsed += duration;
        return item;
    });
}

export function frameAnchorModel(project = {}, plan = {}) {
    const timeline = shotTimelineModel(plan);
    const assets = new Map((project.assets ?? []).map((asset) => [asset.id, asset]));
    const anchors = [];
    for (const generation of project.generations ?? []) {
        const shotIndexes = timeline.filter((item) => plan.shots[item.index]?.generationId === generation.id).map((item) => item.index);
        if (!shotIndexes.length) continue;
        const firstIndex = Math.min(...shotIndexes); const lastIndex = Math.max(...shotIndexes);
        for (const binding of generation.bindings ?? []) {
            const asset = assets.get(binding.assetId);
            if (asset?.type !== "picture") continue;
            const role = effectivePictureBindingRole(project, generation, binding);
            if (!["first_frame", "last_frame"].includes(role)) continue;
            const targetIndex = role === "first_frame" ? firstIndex : lastIndex;
            const target = timeline[targetIndex];
            const position = role === "first_frame"
                ? timeline.slice(0, targetIndex).reduce((sum, item) => sum + item.width, 0)
                : timeline.slice(0, targetIndex + 1).reduce((sum, item) => sum + item.width, 0);
            const seconds = role === "first_frame" ? target.start : target.end;
            const frame = seconds === null ? null : role === "first_frame"
                ? Math.round(seconds * 24) : Math.max(0, Math.round(seconds * 24) - 1);
            anchors.push({
                assetId: asset.id,
                assetName: asset.name || asset.id,
                generationId: generation.id,
                role,
                shotId: plan.shots[targetIndex]?.id,
                position,
                frame,
                physicalLabel: `<Picture ${binding.slotIndex ?? "?"}>`,
            });
        }
    }
    return anchors;
}

function compactSeconds(value) {
    return Number(value).toFixed(2).replace(/\.00$/, "").replace(/(\.\d)0$/, "$1");
}

function timelineSummary(plan) {
    const model = shotTimelineModel(plan);
    const total = model.reduce((sum, item) => sum + (item.duration ?? 0), 0);
    return plan.timingMode === "exact"
        ? `${compactSeconds(total)} s · ${Math.round(total * 24)}f`
        : `${model.length} equal shot${model.length === 1 ? "" : "s"}`;
}

function attributeSelectorValue(value) {
    return String(value).replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

function renderShotTimeline(plan, project, state, selectShot, commit, rerender) {
    const section = element("section", "minimax-h3-shot-timeline");
    const heading = element("div", "minimax-h3-shot-timeline-heading");
    heading.append(
        element("strong", "", "Shot timeline"),
        element("span", "", plan.timingMode === "exact"
            ? `${timelineSummary(plan)} · drag a boundary · double-click to split evenly`
            : "Equal-width overview · switch to Exact for time scale"),
    );
    const track = element("div", "minimax-h3-shot-timeline-track");
    track.setAttribute("role", "group");
    track.setAttribute("aria-label", "Shot timeline");
    const strip = element("div", "minimax-h3-shot-timeline-strip");
    strip.style.minWidth = `${Math.max(1, plan.shots.length) * 86}px`;
    const model = shotTimelineModel(plan);
    const clips = [];
    const choose = (id, focus = true) => {
        state.timelineScroll = track.scrollLeft;
        selectShot(id, focus ? `[data-timeline-shot-id="${attributeSelectorValue(id)}"]` : "");
    };
    for (const item of model) {
        const button = element("button", "minimax-h3-shot-timeline-clip");
        button.type = "button";
        button.style.width = `${item.width}%`;
        button.dataset.shotId = item.id;
        button.dataset.timelineShotId = item.id;
        button.setAttribute("aria-pressed", String(item.id === state.selectedId));
        button.tabIndex = item.id === state.selectedId ? 0 : -1;
        button.setAttribute("aria-label", item.start === null
            ? `${item.title}. ${item.action}`
            : `${item.title}, ${item.start.toFixed(2)} to ${item.end.toFixed(2)} seconds. ${item.action}`);
        const label = element("strong", "", item.title);
        const timing = element("span", "minimax-h3-shot-timeline-time", item.start === null
            ? "Auto"
            : `${compactSeconds(item.start)}–${compactSeconds(item.end)}s · ${Math.round(item.start * 24)}–${Math.max(Math.round(item.start * 24), Math.round(item.end * 24) - 1)}f`);
        const action = element("span", "minimax-h3-shot-timeline-action", item.action);
        action.title = item.action;
        button.append(label, timing, action);
        button.addEventListener("click", () => choose(item.id));
        button.addEventListener("keydown", (event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            let next = item.index;
            if (event.key === "ArrowLeft") next -= 1;
            if (event.key === "ArrowRight") next += 1;
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = model.length - 1;
            const target = model[Math.max(0, Math.min(model.length - 1, next))];
            if (target) choose(target.id);
        });
        clips.push(button);
        strip.appendChild(button);
    }
    if (plan.timingMode === "exact") {
        let boundary = 0;
        for (let index = 0; index < model.length - 1; index += 1) {
            boundary += model[index].width;
            const handle = element("div", "minimax-h3-shot-timeline-boundary");
            handle.dataset.timelineBoundary = String(index);
            handle.tabIndex = 0;
            handle.setAttribute("role", "separator");
            handle.setAttribute("aria-orientation", "vertical");
            handle.setAttribute("aria-label", `Boundary between Shot ${index + 1} and Shot ${index + 2}`);
            handle.setAttribute("aria-valuemin", compactSeconds(model[index].start + .01));
            handle.setAttribute("aria-valuemax", compactSeconds(model[index + 1].end - .01));
            handle.setAttribute("aria-valuenow", compactSeconds(model[index].end));
            handle.style.left = `${boundary}%`;
            const resizePair = (leftDuration) => {
                const left = plan.shots[index]; const right = plan.shots[index + 1];
                const pairTotal = Math.max(.02, Number(left.durationSeconds) + Number(right.durationSeconds));
                const adjusted = Math.max(.01, Math.min(pairTotal - .01, leftDuration));
                left.durationSeconds = Math.round(adjusted * 1000) / 1000;
                right.durationSeconds = Math.round((pairTotal - left.durationSeconds) * 1000) / 1000;
            };
            handle.addEventListener("dblclick", () => {
                state.timelineScroll = track.scrollLeft;
                const pairTotal = Number(plan.shots[index].durationSeconds) + Number(plan.shots[index + 1].durationSeconds);
                resizePair(pairTotal / 2); commit(); rerender(`[data-timeline-boundary="${index}"]`);
            });
            handle.addEventListener("keydown", (event) => {
                if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
                event.preventDefault(); state.timelineScroll = track.scrollLeft;
                const step = event.shiftKey ? .5 : 1 / 24;
                resizePair(Number(plan.shots[index].durationSeconds) + (event.key === "ArrowRight" ? step : -step));
                commit(); rerender(`[data-timeline-boundary="${index}"]`);
            });
            handle.addEventListener("pointerdown", (event) => {
                if (event.button !== 0) return;
                event.preventDefault(); handle.setPointerCapture?.(event.pointerId);
                const startX = event.clientX;
                const startLeft = Number(plan.shots[index].durationSeconds);
                const total = model.at(-1)?.end ?? 0;
                const width = strip.getBoundingClientRect().width || 1;
                let moved = false;
                const move = (moveEvent) => {
                    if (Math.abs(moveEvent.clientX - startX) < 2) return;
                    moved = true;
                    resizePair(startLeft + (moveEvent.clientX - startX) / width * total);
                    const current = shotTimelineModel(plan);
                    clips[index].style.width = `${current[index].width}%`;
                    clips[index + 1].style.width = `${current[index + 1].width}%`;
                    handle.style.left = `${current[index].end / total * 100}%`;
                    handle.setAttribute("aria-valuenow", compactSeconds(current[index].end));
                };
                const finish = () => {
                    handle.removeEventListener("pointermove", move);
                    handle.removeEventListener("pointerup", finish);
                    handle.removeEventListener("pointercancel", finish);
                    if (moved) {
                        state.timelineScroll = track.scrollLeft; commit(); rerender(`[data-timeline-boundary="${index}"]`);
                    }
                };
                handle.addEventListener("pointermove", move);
                handle.addEventListener("pointerup", finish);
                handle.addEventListener("pointercancel", finish);
            });
            strip.appendChild(handle);
        }
    }
    track.appendChild(strip);
    const anchors = frameAnchorModel(project, plan);
    if (anchors.length) {
        const lane = element("div", "minimax-h3-shot-anchor-lane");
        lane.style.minWidth = strip.style.minWidth;
        lane.setAttribute("aria-label", "Image frame anchors");
        for (const anchor of anchors) {
            const marker = element("button", "minimax-h3-shot-anchor");
            marker.type = "button";
            marker.style.left = `${anchor.position}%`;
            marker.dataset.edge = anchor.position >= 99.999 ? "end" : "start";
            const accessibleLabel = `${anchor.assetName}, ${anchor.role === "first_frame" ? "first frame" : "last frame"}${anchor.frame === null ? "" : `, frame ${anchor.frame}`}`;
            marker.setAttribute("aria-label", accessibleLabel);
            marker.title = accessibleLabel;
            const visual = element("span", "minimax-h3-shot-anchor-thumb", `P${String(anchor.physicalLabel).match(/\d+/)?.[0] ?? "?"}`);
            const copy = element("span", "minimax-h3-shot-anchor-copy");
            copy.append(
                element("strong", "", `${anchor.physicalLabel} · ${anchor.role === "first_frame" ? "First" : "Last"}`),
                element("small", "", anchor.frame === null ? anchor.assetName : `${anchor.assetName} · F${anchor.frame}`),
            );
            marker.append(visual, copy);
            marker.addEventListener("click", () => choose(anchor.shotId));
            lane.appendChild(marker);
        }
        track.appendChild(lane);
    }
    queueMicrotask(() => { track.scrollLeft = state.timelineScroll ?? 0; });
    section.append(heading, track);
    return section;
}

export function renderShotsTab(container, controller) {
    container.replaceChildren();
    const documentState = controller.shotDocument();
    const plan = editableShotPlan(documentState);
    if (!plan) return readOnlyShotPlan(container, documentState, controller);
    const project = shotProject(controller);
    const state = controller.shotUiState; state.plan = plan;
    if (!state.selectedId || !plan.shots.some((shot) => shot.id === state.selectedId)) state.selectedId = plan.shots[0]?.id ?? null;
    const commit = () => commitPlan(controller, state);
    const rerender = (focusSelector = "") => {
        state.panelScroll = container.scrollTop;
        state.openDisclosures = captureOpenDisclosures(container);
        state.focusSelector = focusSelector;
        renderShotsTab(container, controller);
    };
    const toolbar = element("div", "minimax-h3-studio-toolbar");
    const timing = selectInput(plan.timingMode, [["auto", "Timing: Auto"], ["exact", "Timing: Exact"]], { ariaLabel: "Shot timing mode" });
    timing.addEventListener("change", () => {
        state.plan.timingMode = timing.value;
        for (const shot of state.plan.shots) {
            if (timing.value === "auto") delete shot.durationSeconds; else shot.durationSeconds ??= 1;
        }
        commit(); rerender();
    });
    const add = actionButton("+ Add shot", () => {
        const shot = {
            id: nextShotId(state.plan.shots),
            generationId: generationIds(project, controller)[0] ?? "g1",
            action: String(controller.basicPrompt?.() ?? "").trim(),
        };
        if (state.plan.timingMode === "exact") shot.durationSeconds = 1;
        state.plan.shots.push(shot); state.selectedId = shot.id; commit(); rerender("[data-shot-action]");
    }, { disabled: plan.shots.length >= 64 });
    toolbar.append(add, timing, element("span", "minimax-h3-field-hint", `${plan.shots.length}/64 shots`)); container.appendChild(toolbar);
    if (documentState.kind === "v1") container.appendChild(element("p", "minimax-h3-studio-status", "Legacy shot plan. It remains unchanged until you edit a field; that explicit edit saves shot plan v2."));
    if (!plan.shots.length) {
        container.appendChild(emptyState("No shots yet", "Divide the scene into visible beats. Each shot can define cast, location, references and camera independently.", actionButton("Create first shot", () => add.click())));
        return;
    }

    container.appendChild(renderShotTimeline(
        plan, project, state,
        (id, focusSelector = "") => { state.selectedId = id; rerender(focusSelector); },
        commit, rerender,
    ));

    const grid = element("div", "minimax-h3-studio-grid minimax-h3-master-detail");
    const list = element("div", "minimax-h3-virtual-list");
    const reorder = (sourceId, targetId) => {
        if (!sourceId || !targetId || sourceId === targetId) return;
        const sourceIndex = state.plan.shots.findIndex((shot) => shot.id === sourceId); const targetIndex = state.plan.shots.findIndex((shot) => shot.id === targetId);
        if (sourceIndex < 0 || targetIndex < 0) return;
        const [moved] = state.plan.shots.splice(sourceIndex, 1); state.plan.shots.splice(targetIndex, 0, moved); commit(); rerender();
    };
    renderShotList(list, state, (id) => { state.selectedId = id; rerender(); }, reorder); grid.appendChild(list);
    const editor = element("div", "minimax-h3-studio-editor minimax-h3-inspector minimax-h3-shot-inspector");
    const shot = state.plan.shots.find((candidate) => candidate.id === state.selectedId);
    const entryStates = resolveEntryStates(project, state.plan).byShot.get(shot.id) ?? { subjects: {}, environments: {} };
    const header = element("div", "minimax-h3-studio-toolbar");
    header.append(element("strong", "", `${shot.id} · Shot ${state.plan.shots.indexOf(shot) + 1}`));
    const generation = selectInput(shot.generationId, generationIds(project, controller).map((id) => [id, id]));
    generation.addEventListener("change", () => { shot.generationId = generation.value; commit(); rerender(); }); header.appendChild(field("Generation", generation));
    editor.appendChild(header);
    renderStory(editor, shot, commit, rerender, controller.basicPrompt?.()); renderActionBeats(editor, shot, project, commit, rerender); renderTiming(editor, shot, state.plan, commit, rerender);
    renderPresence(editor, shot, project, entryStates, commit, rerender);
    renderScaleRelationships(editor, shot, project, commit, rerender);
    renderEnvironment(editor, shot, project, entryStates, commit, rerender);
    renderReferences(editor, shot, project, commit, rerender);
    const cameraSummary = element("section", "minimax-h3-shot-camera-summary");
    const cameraCopy = element("div", "");
    cameraCopy.append(
        element("strong", "", "Camera"),
        element("p", "", cameraInstructionPreview(shot, project)),
    );
    const editCamera = actionButton("Edit camera", () => controller.navigateStudio?.("camera"), {
        disabled: typeof controller.navigateStudio !== "function",
    });
    editCamera.className += " minimax-h3-button minimax-h3-button-secondary";
    cameraSummary.append(cameraCopy, editCamera);
    editor.appendChild(cameraSummary);
    renderAppearanceTransitions(editor, shot, project, entryStates, commit, rerender);
    renderEnvironmentTransitions(editor, shot, project, entryStates, commit, rerender);
    const actions = element("div", "minimax-h3-studio-toolbar");
    actions.appendChild(actionButton("Duplicate shot", () => {
        const copy = structuredClone(shot); copy.id = nextShotId(state.plan.shots); state.plan.shots.splice(state.plan.shots.indexOf(shot) + 1, 0, copy);
        state.selectedId = copy.id; commit(); rerender();
    }));
    actions.appendChild(actionButton("Delete shot", () => {
        const index = state.plan.shots.indexOf(shot); state.plan.shots.splice(index, 1);
        state.selectedId = state.plan.shots[Math.min(index, state.plan.shots.length - 1)]?.id ?? null; commit(); rerender();
    }, { danger: true })); editor.appendChild(actions);
    grid.appendChild(editor); container.appendChild(grid);
    restoreOpenDisclosures(container, state.openDisclosures);
    if (state.panelScroll !== undefined) container.scrollTop = state.panelScroll;
    if (state.focusSelector) {
        const selector = state.focusSelector; state.focusSelector = "";
        queueMicrotask(() => container.querySelector(selector)?.focus());
    }
}
