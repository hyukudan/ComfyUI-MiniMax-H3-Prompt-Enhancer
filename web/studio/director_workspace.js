import { cameraInstructionPreview } from "./camera_planner.js";
import { renderCameraTab } from "./tab_camera.js";
import { renderCameraLookTab } from "./tab_camera_look.js";
import { renderEnvironmentsTab } from "./tab_environments.js";
import { projectForController } from "./project_editor.js";
import { referenceDirectorModel, resolvedReferenceInputs } from "./reference_director.js";
import { editableShotPlan, normalizeShotPlanV2, serializeStructuredJson } from "./schema.js";
import { renderReferencesTab } from "./tab_references.js";
import { renderShotsTab } from "./tab_shots.js";
import { renderStagingTab } from "./tab_staging.js";
import { renderSubjectsTab } from "./tab_subjects.js";

function el(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
}

function button(label, action, className = "minimax-h3-button minimax-h3-button-secondary") {
    const control = el("button", className, label);
    control.type = "button";
    control.addEventListener("click", action);
    return control;
}

function directorState(controller) {
    return controller.directorUiState ??= { composeMode: "board", libraryMode: "media", generationId: "" };
}

function shotPlanForController(controller) {
    const source = controller.shotDocument();
    const sourceRaw = source?.raw ?? "";
    if (controller.shotUiState.sourceRaw !== sourceRaw || !controller.shotUiState.plan) {
        controller.shotUiState.sourceRaw = sourceRaw;
        controller.shotUiState.plan = editableShotPlan(source);
    }
    return controller.shotUiState.plan;
}

function commitPlan(controller, plan) {
    const raw = serializeStructuredJson(normalizeShotPlanV2(plan));
    const changed = controller.commitShotPlan(raw);
    if (changed !== false) controller.shotUiState.sourceRaw = raw;
    return changed;
}

function nextShotId(shots) {
    const ids = new Set(shots.map((shot) => shot.id));
    let index = shots.length + 1;
    while (ids.has(`s${index}`)) index += 1;
    return `s${index}`;
}

function subjectNames(shot, project) {
    const subjects = new Map((project?.subjects ?? []).map((subject) => [subject.id, subject.name || subject.id]));
    return (shot?.subjects ?? []).filter((entry) => entry.presence !== "absent").map((entry) => subjects.get(entry.subjectId) || entry.subjectId);
}

function environmentName(shot, project) {
    const id = shot?.environment?.environmentId;
    return (project?.environments ?? []).find((environment) => environment.id === id)?.name || id || "No background assigned";
}

function modeSwitch(state, rerender, options) {
    const group = el("div", "minimax-h3-director-mode-switch");
    group.setAttribute("role", "tablist");
    for (const [id, label] of options) {
        const control = button(label, () => { state.composeMode = id; rerender(); }, "minimax-h3-director-mode");
        control.setAttribute("role", "tab");
        control.setAttribute("aria-selected", String(state.composeMode === id));
        group.appendChild(control);
    }
    return group;
}

function renderBoard(container, controller, plan, project, rerender) {
    const selected = plan.shots.find((shot) => shot.id === controller.shotUiState.selectedId) ?? plan.shots[0];
    if (!selected) {
        const empty = el("section", "minimax-h3-empty-state minimax-h3-director-empty");
        empty.append(el("h3", "", "Build the first scene"), el("p", "", "Start with a visible action. Then place subjects, a background, references and camera direction around it."));
        empty.appendChild(button("Create first scene", () => {
            const shot = { id: nextShotId(plan.shots), generationId: project?.generations?.[0]?.id ?? "g1", action: String(controller.basicPrompt?.() ?? "").trim() };
            if (plan.timingMode === "exact") shot.durationSeconds = 1;
            plan.shots.push(shot); controller.shotUiState.selectedId = shot.id; commitPlan(controller, plan); rerender();
        }, "minimax-h3-button minimax-h3-button-primary"));
        container.appendChild(empty);
        return;
    }

    const layout = el("div", "minimax-h3-director-compose-grid");
    const stage = el("section", "minimax-h3-director-stage");
    stage.setAttribute("aria-label", "Selected scene board");
    const backdrop = el("div", "minimax-h3-director-backdrop");
    backdrop.append(el("span", "minimax-h3-director-kicker", "BACKGROUND / SET"), el("strong", "", environmentName(selected, project)));
    const cast = el("div", "minimax-h3-director-cast");
    const names = subjectNames(selected, project);
    if (!names.length) cast.appendChild(el("p", "minimax-h3-director-placeholder", "No subjects placed in this scene"));
    for (const name of names) {
        const card = el("article", "minimax-h3-director-subject-card");
        card.append(el("span", "minimax-h3-director-avatar", name.slice(0, 1).toUpperCase()), el("strong", "", name));
        cast.appendChild(card);
    }
    const action = el("div", "minimax-h3-director-action");
    action.append(el("span", "minimax-h3-director-kicker", "ACTION"), el("p", "", selected.action || "Describe what visibly happens in this scene."));
    const camera = el("div", "minimax-h3-director-camera-line");
    camera.append(el("span", "minimax-h3-director-kicker", "CAMERA"), el("p", "", cameraInstructionPreview(selected, project ?? {})));
    stage.append(backdrop, cast, action, camera);

    const lanes = el("section", "minimax-h3-director-lanes");
    lanes.appendChild(el("h3", "", "Reference lanes"));
    const roles = new Map();
    for (const use of selected.referenceUses ?? []) {
        const lane = ["voice", "exact_dialogue", "soundtrack"].includes(use.role) ? "Audio"
            : use.role === "camera_transfer" ? "Camera" : ["performance"].includes(use.role) ? "Performance" : "Continuity & look";
        const asset = (project?.assets ?? []).find((item) => item.id === use.assetId);
        const values = roles.get(lane) ?? []; values.push(asset?.name || use.assetId); roles.set(lane, values);
    }
    for (const laneName of ["Performance", "Camera", "Audio", "Continuity & look"]) {
        const lane = el("div", "minimax-h3-director-lane");
        lane.appendChild(el("strong", "", laneName));
        const values = roles.get(laneName) ?? [];
        lane.appendChild(el("span", values.length ? "" : "is-empty", values.join(" · ") || "Drop or connect a reference in Library"));
        lanes.appendChild(lane);
    }
    layout.append(stage, lanes);

    const inspector = el("aside", "minimax-h3-director-inspector");
    inspector.append(el("span", "minimax-h3-director-kicker", `SCENE ${plan.shots.indexOf(selected) + 1}`), el("h3", "", selected.id));
    const actionField = el("label", "minimax-h3-studio-field");
    actionField.appendChild(el("span", "", "Visible action"));
    const textarea = el("textarea"); textarea.value = selected.action ?? ""; textarea.placeholder = "What changes on screen?";
    textarea.addEventListener("blur", () => { selected.action = textarea.value.trim(); commitPlan(controller, plan); rerender(); });
    actionField.appendChild(textarea); inspector.appendChild(actionField);
    const summary = el("dl", "minimax-h3-director-scene-summary");
    for (const [term, value] of [["Generation", selected.generationId || "g1"], ["Cast", names.length || "—"], ["References", selected.referenceUses?.length || "—"], ["Duration", plan.timingMode === "exact" ? `${selected.durationSeconds ?? 1}s` : "Auto"]]) {
        summary.append(el("dt", "", term), el("dd", "", String(value)));
    }
    inspector.append(summary, button("Edit scene details", () => { directorState(controller).composeMode = "details"; rerender(); }), button("Stage subjects", () => { directorState(controller).composeMode = "staging"; rerender(); }), button("Direct camera", () => { directorState(controller).composeMode = "camera"; rerender(); }));
    layout.appendChild(inspector);
    container.appendChild(layout);
}

export function renderDirectorCompose(container, controller) {
    container.replaceChildren();
    const plan = shotPlanForController(controller);
    if (!plan) return renderShotsTab(container, controller);
    const project = projectForController(controller);
    const state = directorState(controller);
    if (!controller.shotUiState.selectedId || !plan.shots.some((shot) => shot.id === controller.shotUiState.selectedId)) controller.shotUiState.selectedId = plan.shots[0]?.id ?? null;
    const rerender = () => renderDirectorCompose(container, controller);
    const top = el("header", "minimax-h3-director-workspace-header");
    const copy = el("div"); copy.append(el("h2", "", "Compose"), el("p", "", "Build the cut as scenes, then direct each scene visually."));
    top.append(copy, modeSwitch(state, rerender, [["board", "Board"], ["details", "Details"], ["staging", "Staging"], ["camera", "Camera"]]));
    container.appendChild(top);
    if (state.composeMode !== "board") {
        const host = el("div", "minimax-h3-director-embedded-editor"); container.appendChild(host);
        ({ details: renderShotsTab, staging: renderStagingTab, camera: renderCameraTab }[state.composeMode] ?? renderShotsTab)(host, controller);
        return;
    }
    const strip = el("div", "minimax-h3-director-scene-strip"); strip.setAttribute("aria-label", "Scene strip");
    for (const [index, shot] of plan.shots.entries()) {
        const card = button("", () => { controller.shotUiState.selectedId = shot.id; rerender(); }, "minimax-h3-director-scene-card");
        card.dataset.selected = String(shot.id === controller.shotUiState.selectedId);
        card.append(el("span", "minimax-h3-director-scene-number", String(index + 1).padStart(2, "0")), el("strong", "", shot.action || "Untitled scene"), el("small", "", `${shot.generationId || "g1"} · ${subjectNames(shot, project).length} subjects`));
        strip.appendChild(card);
    }
    const add = button("+ Scene", () => {
        const shot = { id: nextShotId(plan.shots), generationId: project?.generations?.[0]?.id ?? "g1", action: "" };
        if (plan.timingMode === "exact") shot.durationSeconds = 1;
        plan.shots.push(shot); controller.shotUiState.selectedId = shot.id; commitPlan(controller, plan); rerender();
    }, "minimax-h3-director-add-scene"); add.disabled = plan.shots.length >= 64; strip.appendChild(add); container.appendChild(strip);
    renderBoard(container, controller, plan, project, rerender);
}

export function renderDirectorLibrary(container, controller) {
    container.replaceChildren();
    const state = directorState(controller);
    const top = el("header", "minimax-h3-director-workspace-header");
    const copy = el("div"); copy.append(el("h2", "", "Library"), el("p", "", "Import reusable media, define cast and environments, then connect them to the cut."));
    const switcher = el("div", "minimax-h3-director-mode-switch");
    for (const [id, label] of [["media", "Media"], ["subjects", "Subjects"], ["environments", "Environments"]]) {
        const control = button(label, () => { state.libraryMode = id; renderDirectorLibrary(container, controller); }, "minimax-h3-director-mode");
        control.setAttribute("aria-selected", String(state.libraryMode === id)); switcher.appendChild(control);
    }
    top.append(copy, switcher); container.appendChild(top);
    const host = el("div", "minimax-h3-director-library-host"); container.appendChild(host);
    ({ media: renderReferencesTab, subjects: renderSubjectsTab, environments: renderEnvironmentsTab }[state.libraryMode] ?? renderReferencesTab)(host, controller);
}

export function renderDirectorWiring(container, controller) {
    container.replaceChildren();
    const project = projectForController(controller);
    if (!project) return renderReferencesTab(container, controller);
    const state = directorState(controller);
    const generations = project.generations ?? [];
    if (!generations.some((generation) => generation.id === state.generationId)) state.generationId = generations[0]?.id ?? "";
    const generation = generations.find((item) => item.id === state.generationId) ?? generations[0] ?? { bindings: [] };
    const director = controller.referenceDirectorDocument?.()?.value ?? {};
    const rows = resolvedReferenceInputs(project, generation, director);
    const model = referenceDirectorModel(project, controller.shotDocument()?.value ?? {}, generation.id);
    const meaningful = new Set(model.assets.filter((asset) => asset.connections.length).map((asset) => asset.id));
    const top = el("header", "minimax-h3-director-workspace-header");
    const copy = el("div"); copy.append(el("h2", "", "Wiring"), el("p", "", "Audit the physical H3 slots and the semantic job attached to every file."));
    const choices = el("select"); choices.setAttribute("aria-label", "Generation");
    for (const item of generations) { const option = el("option", "", `Generation ${item.order ?? item.id}`); option.value = item.id; choices.appendChild(option); }
    choices.value = generation.id ?? ""; choices.addEventListener("change", () => { state.generationId = choices.value; renderDirectorWiring(container, controller); });
    top.append(copy, choices); container.appendChild(top);
    const stats = el("div", "minimax-h3-director-wiring-stats");
    const ready = rows.filter((row) => row.sourceReady && row.active && meaningful.has(row.assetId)).length;
    for (const [value, label] of [[`${ready}/${rows.length}`, "ready inputs"], [model.assigned, "bound assets"], [model.assets.length - model.assigned, "unbound assets"]]) {
        const item = el("div"); item.append(el("strong", "", String(value)), el("span", "", label)); stats.appendChild(item);
    }
    container.appendChild(stats);
    const groups = el("div", "minimax-h3-director-wiring-groups");
    for (const type of ["picture", "video", "audio"]) {
        const group = el("section", "minimax-h3-director-wiring-group");
        const typeRows = rows.filter((row) => row.mediaType === type);
        group.appendChild(el("h3", "", `${type === "picture" ? "Images" : type === "video" ? "Video" : "Audio"} · ${typeRows.length}`));
        if (!typeRows.length) group.appendChild(el("p", "minimax-h3-director-placeholder", "No input bound"));
        for (const row of typeRows) {
            const card = el("article", "minimax-h3-director-wire-card");
            const status = !row.sourceReady ? "Missing file" : !row.active ? "Inactive" : !meaningful.has(row.assetId) ? "Needs meaning" : "Ready";
            card.dataset.status = status.toLowerCase().replaceAll(" ", "-");
            const main = el("div"); main.append(el("strong", "", row.label), el("span", "", row.name), el("small", "", String(row.role).replaceAll("_", " ")));
            card.append(main, el("span", "minimax-h3-director-wire-status", status)); group.appendChild(card);
        }
        groups.appendChild(group);
    }
    container.append(groups, button("Open Library to connect references", () => controller.navigateStudio?.("library")));
}

export function renderDirectorLook(container, controller) {
    try {
        const creative = controller.creativeDocument?.();
        const camera = controller.cinematographyDocument?.();
        if (creative && camera && typeof controller.creativeFields === "function" && typeof controller.cameraFields === "function") {
            renderCameraLookTab(container, controller);
            return;
        }
    } catch {
        // Reference-only nodes deliberately do not own the enhancer's Look documents.
    }
    container.replaceChildren();
    const top = el("header", "minimax-h3-director-workspace-header");
    const copy = el("div"); copy.append(el("h2", "", "Look"), el("p", "", "Creative direction is compiled by the Prompt Enhancer, downstream from this reference workspace."));
    top.appendChild(copy); container.appendChild(top);
    const handoff = el("section", "minimax-h3-director-look-handoff");
    handoff.append(
        el("span", "minimax-h3-director-kicker", "DOWNSTREAM OWNERSHIP"),
        el("h3", "", "Keep reference meaning here; style the final prompt in the enhancer"),
        el("p", "", "The Director owns physical files, subjects, voices, environments and scene-scoped reference intent. Visual language, mood, global cinematography, titles and credits remain on MiniMax H3 Prompt Enhancer so there is only one authoritative Look."),
        el("p", "minimax-h3-studio-status", "Connect reference_context to the enhancer, then open its Look section. Reference camera intent still overrides only the explicit aspects assigned in Library."),
    );
    container.appendChild(handoff);
}
