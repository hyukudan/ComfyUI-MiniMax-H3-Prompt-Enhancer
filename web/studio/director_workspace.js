import { cameraInstructionPreview, cameraSceneModel, VISUAL_CAMERA_MOTIONS } from "./camera_planner.js";
import { renderCameraTab } from "./tab_camera.js";
import { renderCameraLookTab } from "./tab_camera_look.js";
import { renderEnvironmentsTab } from "./tab_environments.js";
import { projectForController, uniqueId } from "./project_editor.js";
import { referenceDirectorModel, resolvedReferenceInputs } from "./reference_director.js";
import { disconnectPurposeReference, replacePurposeReference } from "./media_workflows.js";
import { mediaTypeForFile, setReferenceSource, sourcePreviewUrl } from "./reference_sources.js";
import { editableShotPlan, normalizeShotPlanV2, serializeStructuredJson } from "./schema.js";
import { renderReferencesTab } from "./tab_references.js";
import { renderShotsTab } from "./tab_shots.js";
import { renderStagingTab } from "./tab_staging.js";
import { createSubjectDraft, renderSubjectsTab } from "./tab_subjects.js";

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

const COMPOSE_TARGETS = Object.freeze({
    subject_identity: { label: "Image", type: "picture" },
    voice: { label: "Voice", type: "audio" },
    performance: { label: "Performance", type: "video" },
    environment_view: { label: "Background", type: "picture" },
    camera: { label: "Camera", type: "video" },
    soundtrack: { label: "Audio", type: "audio" },
    continuity: { label: "Continuity", type: "picture" },
});

const CAMERA_MOTION_LABELS = new Map(VISUAL_CAMERA_MOTIONS.flatMap((group) => group.items.map(([id, label]) => [id, label])));

function readableToken(value, fallback) {
    return value ? String(value).replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase()) : fallback;
}

export function composeCameraSummary(shot = {}) {
    const model = cameraSceneModel(shot);
    const start = shot.cameraStart ?? {};
    const end = { ...start, ...(shot.cameraEnd ?? {}) };
    const path = shot.cameraPath ?? {};
    const qualifiers = [path.amplitude && readableToken(path.amplitude), path.speed && readableToken(path.speed)].filter(Boolean);
    const configured = Boolean(shot.cameraStart || shot.cameraPath || shot.cameraEnd);
    return {
        configured,
        kind: model.kind,
        icon: model.kind === "orientation" ? "↷" : model.kind === "optical" ? "◎" : model.kind === "expressive" ? "≈" : model.kind === "spatial" ? "→" : "●",
        start: [readableToken(start.framing, "Inherited framing"), readableToken(start.angle, "Inherited angle")].join(" · "),
        movement: `${CAMERA_MOTION_LABELS.get(path.motionType) ?? (path.motionType ? readableToken(path.motionType) : "Inherited movement")}${qualifiers.length ? ` · ${qualifiers.join(" · ")}` : ""}`,
        end: [readableToken(end.framing, "Inherit start"), readableToken(end.angle, "Inherit start")].join(" · "),
    };
}

export function composeConnectionInput(project, shotPlan, shot, assetId, purposeId, relationId = "") {
    return {
        project,
        shotPlan,
        assetId,
        purposeId,
        generationId: shot?.generationId || project?.generations?.[0]?.id || "g1",
        shotId: shot?.id || "",
        relationId,
    };
}

export function setSceneSubjectPresence(shot, subjectId, present) {
    shot.subjects ??= [];
    const index = shot.subjects.findIndex((entry) => entry.subjectId === subjectId);
    if (present && index >= 0) shot.subjects[index].presence = "present";
    else if (present) shot.subjects.push({ subjectId, presence: "present" });
    else if (shot.subjectPresenceComplete && index >= 0) shot.subjects[index].presence = "absent";
    else if (index >= 0) shot.subjects.splice(index, 1);
    if (!shot.subjects.length) delete shot.subjects;
    return shot;
}

export function setSceneEnvironment(shot, environmentId) {
    if (environmentId) shot.environment = { environmentId, viewIds: [] };
    else delete shot.environment;
    return shot;
}

export function createSceneSubjectBundle(project, shotPlan, shotId, name) {
    const nextProject = structuredClone(project);
    const nextPlan = structuredClone(shotPlan);
    const subject = createSubjectDraft(nextProject, name);
    nextProject.subjects.push(subject);
    const shot = nextPlan.shots.find((candidate) => candidate.id === shotId);
    if (shot) setSceneSubjectPresence(shot, subject.id, true);
    return { project: nextProject, shotPlan: nextPlan, subject };
}

export function createImportedAssetDraft(project, file, mediaType, fallbackName = "Reference") {
    const nextProject = structuredClone(project);
    const asset = {
        id: uniqueId(nextProject.assets, "asset."),
        type: mediaType,
        name: String(file?.name ?? "").replace(/\.[^.]+$/, "") || fallbackName,
        available: true,
    };
    nextProject.assets.push(asset);
    return { project: nextProject, asset };
}

export function composeVisualAssignments(project, shot) {
    const assets = new Map((project?.assets ?? []).map((asset) => [asset.id, asset]));
    const uses = shot?.referenceUses ?? [];
    const environment = (project?.environments ?? []).find((item) => item.id === shot?.environment?.environmentId);
    const selectedViewIds = new Set(shot?.environment?.viewIds ?? []);
    const environmentViews = (environment?.views ?? []).filter((view) => !selectedViewIds.size || selectedViewIds.has(view.id));
    const subjects = [];
    for (const presence of shot?.subjects ?? []) {
        if (presence.presence === "absent") continue;
        const subject = (project?.subjects ?? []).find((item) => item.id === presence.subjectId);
        if (!subject) continue;
        const performanceAssetIds = uses
            .filter((use) => use.role === "performance" && (use.targetIds ?? []).includes(subject.id))
            .map((use) => use.assetId);
        subjects.push({
            subject,
            identityAssets: (subject.identityAssetIds ?? []).map((id) => assets.get(id)).filter(Boolean),
            voiceAsset: assets.get(subject.defaultVoiceAssetId) ?? null,
            performanceAssets: performanceAssetIds.map((id) => assets.get(id)).filter(Boolean),
        });
    }
    return {
        environment,
        backgroundAssets: environmentViews.map((view) => assets.get(view.assetId)).filter(Boolean),
        subjects,
    };
}

function composeMediaVisual(asset, source) {
    const visual = el("span", "minimax-h3-director-asset-visual");
    visual.dataset.type = asset.type;
    const url = sourcePreviewUrl(source);
    if (url && asset.type === "picture") {
        const image = el("img"); image.src = url; image.alt = ""; image.loading = "lazy"; visual.appendChild(image);
    } else if (url && asset.type === "video") {
        const video = el("video"); video.src = url; video.muted = true; video.preload = "metadata"; video.playsInline = true; visual.appendChild(video);
    } else visual.appendChild(el("strong", "", asset.type === "video" ? "▶" : asset.type === "audio" ? "≋" : "▧"));
    return visual;
}

function composeBoundMedia(asset, source, role) {
    const item = el("span", "minimax-h3-director-bound-media");
    item.dataset.type = asset.type;
    item.title = `${role}: ${asset.name || asset.id}`;
    item.append(composeMediaVisual(asset, source), el("small", "", `${role} · ${asset.name || asset.id}`));
    return item;
}

function composeSubjectAvatar(name, identityAsset, source) {
    const avatar = el("span", "minimax-h3-director-avatar");
    const url = identityAsset?.type === "picture" ? sourcePreviewUrl(source) : "";
    if (url) {
        const image = el("img"); image.src = url; image.alt = `${name} identity reference`; image.loading = "lazy"; avatar.appendChild(image);
    } else avatar.textContent = name.slice(0, 1).toUpperCase();
    return avatar;
}

function composeDropTarget(controller, purposeId, relationId, selectedAsset, connect, importFile, disconnect, connected = false) {
    const definition = COMPOSE_TARGETS[purposeId];
    const wrapper = el("span", "minimax-h3-director-drop-wrapper");
    wrapper.dataset.connected = String(connected);
    const target = button(`${definition.label}${connected ? " ✓" : ""}`, () => connect(purposeId, relationId), "minimax-h3-director-drop-target");
    target.dataset.purpose = purposeId;
    target.dataset.type = definition.type;
    target.dataset.connected = String(connected);
    target.disabled = Boolean(selectedAsset && selectedAsset.type !== definition.type);
    target.title = `${definition.type} reference → ${definition.label}`;
    const fileInput = el("input"); fileInput.type = "file"; fileInput.hidden = true;
    fileInput.accept = definition.type === "picture" ? "image/*" : definition.type === "video" ? "video/*" : "audio/*";
    fileInput.addEventListener("change", () => { const file = fileInput.files?.[0]; if (file) importFile(file, purposeId, relationId); });
    const importButton = button("+", () => fileInput.click(), "minimax-h3-director-drop-import");
    importButton.setAttribute("aria-label", `Import ${definition.label.toLowerCase()} file directly`);
    importButton.title = `Import and connect a ${definition.type} file`;
    for (const eventName of ["dragenter", "dragover"]) target.addEventListener(eventName, (event) => {
        event.preventDefault();
        const dragged = controller.projectUiState.draggedAssetId;
        const asset = controller.projectUiState.project?.assets?.find((item) => item.id === dragged);
        target.dataset.drag = asset?.type === definition.type ? "ready" : "invalid";
    });
    target.addEventListener("dragleave", () => delete target.dataset.drag);
    target.addEventListener("drop", (event) => {
        event.preventDefault(); delete target.dataset.drag;
        const file = event.dataTransfer?.files?.[0];
        if (file) importFile(file, purposeId, relationId);
        else connect(purposeId, relationId, controller.projectUiState.draggedAssetId);
    });
    wrapper.append(target, importButton);
    if (connected) {
        const disconnectButton = button("×", () => disconnect(purposeId, relationId), "minimax-h3-director-drop-disconnect");
        disconnectButton.setAttribute("aria-label", `Disconnect ${definition.label.toLowerCase()} reference`);
        disconnectButton.title = `Disconnect from ${definition.label}; keep the file in Library`;
        wrapper.appendChild(disconnectButton);
    }
    wrapper.appendChild(fileInput);
    return wrapper;
}

function renderComposeAssetTray(container, controller, project, shotPlan, shot, rerender) {
    const assets = project?.assets ?? [];
    const sourceDocument = controller.referenceDirectorDocument?.();
    const sources = sourceDocument?.value?.sources ?? {};
    const selectedId = controller.projectUiState.selectedAssetId;
    const tray = el("section", "minimax-h3-director-asset-tray");
    const header = el("div", "minimax-h3-director-tray-header");
    header.append(el("div", "", "References"), el("span", "", assets.length ? "Select or drag onto a highlighted destination" : "Import files in Library first"));
    tray.appendChild(header);
    const rail = el("div", "minimax-h3-director-asset-rail");
    for (const asset of assets) {
        const card = button("", () => { controller.projectUiState.selectedAssetId = asset.id; rerender(); }, "minimax-h3-director-asset-card");
        card.draggable = true; card.dataset.selected = String(asset.id === selectedId); card.dataset.type = asset.type;
        card.setAttribute("aria-label", `${asset.name || asset.id}, ${asset.type}${sources[asset.id] ? ", file ready" : ", missing physical file"}`);
        card.addEventListener("dragstart", (event) => {
            controller.projectUiState.draggedAssetId = asset.id;
            event.dataTransfer?.setData("text/plain", asset.id); if (event.dataTransfer) event.dataTransfer.effectAllowed = "link";
        });
        card.addEventListener("dragend", () => { delete controller.projectUiState.draggedAssetId; });
        const copy = el("span", "minimax-h3-director-asset-copy");
        copy.append(el("strong", "", asset.name || asset.id), el("small", "", `${asset.type} · ${sources[asset.id] ? "ready" : "needs file"}`));
        card.append(composeMediaVisual(asset, sources[asset.id]), copy); rail.appendChild(card);
    }
    if (!assets.length) rail.appendChild(button("Open Library", () => controller.navigateStudio?.("library"), "minimax-h3-director-tray-empty"));
    tray.appendChild(rail); container.appendChild(tray);
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

    renderComposeAssetTray(container, controller, project, plan, selected, rerender);
    const sources = controller.referenceDirectorDocument?.()?.value?.sources ?? {};
    const visualAssignments = composeVisualAssignments(project, selected);
    const subjectAssignments = new Map(visualAssignments.subjects.map((entry) => [entry.subject.id, entry]));
    const selectedAsset = (project?.assets ?? []).find((asset) => asset.id === controller.projectUiState.selectedAssetId) ?? null;
    const feedback = el("p", "minimax-h3-director-compose-feedback"); feedback.setAttribute("role", "status");
    const connectionPlan = (purposeId, relationId) => {
        let workingPlan = plan;
        if (purposeId === "environment_view" && relationId && !selected.environment?.environmentId) {
            workingPlan = structuredClone(plan);
            const workingShot = workingPlan.shots.find((shot) => shot.id === selected.id);
            if (workingShot) workingShot.environment = { environmentId: relationId, viewIds: [] };
        }
        return workingPlan;
    };
    const connect = (purposeId, relationId = "", explicitAssetId = "") => {
        const assetId = explicitAssetId || controller.projectUiState.selectedAssetId;
        const workingPlan = connectionPlan(purposeId, relationId);
        const workingShot = workingPlan.shots.find((shot) => shot.id === selected.id) ?? selected;
        const result = replacePurposeReference(composeConnectionInput(project, workingPlan, workingShot, assetId, purposeId, relationId));
        if (!result.ok) {
            feedback.dataset.valid = "false"; feedback.textContent = result.issues.join(" "); return;
        }
        const committed = controller.replaceProjectBundleAtomically?.({ mediaProject: result.project, shotPlan: result.shotPlan });
        if (!committed?.ok) {
            feedback.dataset.valid = "false"; feedback.textContent = committed?.message || "Could not update Project and Shot Plan together."; return;
        }
        controller.projectUiState.selectedAssetId = assetId;
        delete controller.projectUiState.draggedAssetId;
        controller.directorUiState.composeFeedback = result.summary;
        rerender();
    };
    const importFile = async (file, purposeId, relationId = "") => {
        const definition = COMPOSE_TARGETS[purposeId];
        const mediaType = mediaTypeForFile(file);
        if (mediaType !== definition.type) {
            feedback.dataset.valid = "false"; feedback.hidden = false;
            feedback.textContent = `${definition.label} requires a ${definition.type} file.`; return;
        }
        const directorDocument = controller.referenceDirectorDocument?.();
        if (directorDocument?.kind !== "v1") {
            feedback.dataset.valid = "false"; feedback.hidden = false;
            feedback.textContent = directorDocument?.issues?.[0] || "Physical reference storage is unavailable."; return;
        }
        if ((project.assets ?? []).length >= 128) {
            feedback.dataset.valid = "false"; feedback.hidden = false; feedback.textContent = "The reference library is full."; return;
        }
        feedback.dataset.valid = "true"; feedback.hidden = false; feedback.textContent = `Importing ${file.name}…`;
        try {
            const source = await controller.uploadReferenceFile(file);
            const draft = createImportedAssetDraft(project, file, mediaType, `${definition.label} reference`);
            const nextProject = draft.project;
            const assetId = draft.asset.id;
            const name = draft.asset.name;
            const workingPlan = connectionPlan(purposeId, relationId);
            const workingShot = workingPlan.shots.find((shot) => shot.id === selected.id) ?? selected;
            const connected = replacePurposeReference(composeConnectionInput(nextProject, workingPlan, workingShot, assetId, purposeId, relationId));
            if (!connected.ok) throw new Error(connected.issues.join(" "));
            const nextDirector = setReferenceSource(directorDocument.value, assetId, source);
            const committed = controller.replaceProjectBundleAtomically?.({ mediaProject: connected.project, shotPlan: connected.shotPlan, referenceDirector: nextDirector });
            if (!committed?.ok) throw new Error(committed?.message || "Could not import and connect the file atomically.");
            controller.projectUiState.selectedAssetId = assetId;
            controller.directorUiState.composeFeedback = `${name} imported and connected to ${definition.label}.`;
            rerender();
        } catch (error) {
            feedback.dataset.valid = "false"; feedback.hidden = false; feedback.textContent = error?.message || "Import failed.";
        }
    };
    const disconnect = (purposeId, relationId = "") => {
        const result = disconnectPurposeReference({
            project,
            shotPlan: plan,
            purposeId,
            generationId: selected.generationId || project?.generations?.[0]?.id || "g1",
            shotId: selected.id,
            relationId,
        });
        if (!result.ok) {
            feedback.dataset.valid = "false"; feedback.textContent = result.issues.join(" "); return;
        }
        const committed = controller.replaceProjectBundleAtomically?.({ mediaProject: result.project, shotPlan: result.shotPlan });
        if (!committed?.ok) {
            feedback.dataset.valid = "false"; feedback.textContent = committed?.message || "Could not disconnect the reference atomically."; return;
        }
        controller.directorUiState.composeFeedback = `${result.summary}. The file remains in Library.`;
        rerender();
    };
    const layout = el("div", "minimax-h3-director-compose-grid");
    const stage = el("section", "minimax-h3-director-stage");
    stage.setAttribute("aria-label", "Selected scene board");
    const backdrop = el("div", "minimax-h3-director-backdrop");
    const backdropCopy = el("div"); backdropCopy.append(el("span", "minimax-h3-director-kicker", "BACKGROUND / SET"), el("strong", "", environmentName(selected, project)));
    backdrop.append(backdropCopy);
    const backgroundMedia = el("div", "minimax-h3-director-backdrop-media");
    for (const asset of visualAssignments.backgroundAssets.slice(0, 2)) backgroundMedia.appendChild(composeBoundMedia(asset, sources[asset.id], "Background"));
    if (backgroundMedia.childElementCount) backdrop.appendChild(backgroundMedia);
    const environmentTargetId = selected.environment?.environmentId || ((project?.environments ?? []).length === 1 ? project.environments[0].id : "");
    const activeEnvironment = (project?.environments ?? []).find((environment) => environment.id === environmentTargetId);
    if (environmentTargetId) backdrop.appendChild(composeDropTarget(controller, "environment_view", environmentTargetId, selectedAsset, connect, importFile, disconnect, Boolean(activeEnvironment?.views?.length)));
    else backdrop.appendChild(el("small", "minimax-h3-director-lane-guidance", (project?.environments ?? []).length ? "Choose the scene set in Details" : "Create an environment in Library"));
    const cast = el("div", "minimax-h3-director-cast");
    const names = subjectNames(selected, project);
    if (!names.length) cast.appendChild(el("p", "minimax-h3-director-placeholder", "No subjects placed in this scene"));
    for (const entry of (selected.subjects ?? []).filter((item) => item.presence !== "absent")) {
        const subject = (project?.subjects ?? []).find((candidate) => candidate.id === entry.subjectId);
        const name = subject?.name || entry.subjectId;
        const assigned = subjectAssignments.get(entry.subjectId) ?? { identityAssets: [], voiceAsset: null, performanceAssets: [] };
        const card = el("article", "minimax-h3-director-subject-card");
        const targets = el("div", "minimax-h3-director-subject-targets");
        const performanceConnected = (selected.referenceUses ?? []).some((use) => use.role === "performance" && (use.targetIds ?? []).includes(entry.subjectId));
        targets.append(
            composeDropTarget(controller, "subject_identity", entry.subjectId, selectedAsset, connect, importFile, disconnect, Boolean(subject?.identityAssetIds?.length)),
            composeDropTarget(controller, "voice", entry.subjectId, selectedAsset, connect, importFile, disconnect, Boolean(subject?.defaultVoiceAssetId)),
            composeDropTarget(controller, "performance", entry.subjectId, selectedAsset, connect, importFile, disconnect, performanceConnected),
        );
        const boundMedia = el("div", "minimax-h3-director-bound-strip");
        for (const asset of assigned.identityAssets.slice(0, 2)) boundMedia.appendChild(composeBoundMedia(asset, sources[asset.id], "Image"));
        if (assigned.voiceAsset) boundMedia.appendChild(composeBoundMedia(assigned.voiceAsset, sources[assigned.voiceAsset.id], "Voice"));
        for (const asset of assigned.performanceAssets.slice(0, 1)) boundMedia.appendChild(composeBoundMedia(asset, sources[asset.id], "Performance"));
        card.append(
            composeSubjectAvatar(name, assigned.identityAssets[0], sources[assigned.identityAssets[0]?.id]),
            el("strong", "", name),
            el("small", "minimax-h3-director-llm-subject", `LLM · <Subject ${subject?.h3Index ?? "?"}>`),
            boundMedia,
            targets,
        );
        cast.appendChild(card);
    }
    const action = el("div", "minimax-h3-director-action");
    action.append(el("span", "minimax-h3-director-kicker", "ACTION"), el("p", "", selected.action || "Describe what visibly happens in this scene."));
    const cameraSummary = composeCameraSummary(selected);
    const camera = button("", () => { directorState(controller).composeMode = "camera"; rerender(); }, "minimax-h3-director-camera-line");
    camera.setAttribute("aria-label", `Direct camera for ${selected.id}. ${cameraInstructionPreview(selected, project ?? {})}`);
    const cameraHeading = el("span", "minimax-h3-director-camera-heading");
    cameraHeading.append(el("span", "minimax-h3-director-kicker", "CAMERA · THIS CUT"), el("strong", "", cameraSummary.configured ? "Directed" : "Inherited"), el("span", "minimax-h3-director-camera-edit", "Edit →"));
    const phases = el("span", "minimax-h3-director-camera-phases");
    for (const [index, label, value] of [["1", "Start", cameraSummary.start], [cameraSummary.icon, "Move", cameraSummary.movement], ["3", "End", cameraSummary.end]]) {
        const phase = el("span", "minimax-h3-director-camera-phase");
        phase.append(el("b", "", index), el("small", "", label), el("span", "", value)); phases.appendChild(phase);
    }
    camera.append(cameraHeading, phases);
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
    const lanePurpose = { Camera: "camera", Audio: "soundtrack", "Continuity & look": "continuity" };
    const presentSubjects = (selected.subjects ?? []).filter((item) => item.presence !== "absent");
    for (const laneName of ["Performance", "Camera", "Audio", "Continuity & look"]) {
        const lane = el("div", "minimax-h3-director-lane");
        lane.appendChild(el("strong", "", laneName));
        const values = roles.get(laneName) ?? [];
        lane.appendChild(el("span", values.length ? "" : "is-empty", values.join(" · ") || "Drop or connect a reference in Library"));
        if (laneName === "Performance" && presentSubjects.length === 1) lane.appendChild(composeDropTarget(controller, "performance", presentSubjects[0].subjectId, selectedAsset, connect, importFile, disconnect, values.length > 0));
        else if (lanePurpose[laneName]) lane.appendChild(composeDropTarget(controller, lanePurpose[laneName], "", selectedAsset, connect, importFile, disconnect, values.length > 0));
        else lane.appendChild(el("small", "minimax-h3-director-lane-guidance", "Use a subject card"));
        lanes.appendChild(lane);
    }
    layout.append(stage, lanes);

    const inspector = el("aside", "minimax-h3-director-inspector");
    inspector.append(el("span", "minimax-h3-director-kicker", `SCENE ${plan.shots.indexOf(selected) + 1}`), el("h3", "", selected.id));
    const setup = el("section", "minimax-h3-director-scene-setup");
    const setupHeading = el("div", "minimax-h3-director-inspector-heading");
    const setupActions = el("div", "minimax-h3-director-setup-actions");
    setupActions.append(
        button("+ Subject", () => { controller.directorUiState.creatingSubject = true; rerender(); }, "minimax-h3-director-text-button"),
        button("Manage Library", () => { controller.directorUiState.libraryMode = "subjects"; controller.navigateStudio?.("library"); }, "minimax-h3-director-text-button"),
    );
    setupHeading.append(el("strong", "", "Cast & set"), setupActions);
    setup.appendChild(setupHeading);
    if (controller.directorUiState.creatingSubject) {
        const creator = el("form", "minimax-h3-director-inline-creator");
        const nameInput = el("input"); nameInput.type = "text"; nameInput.maxLength = 200; nameInput.placeholder = "Subject name, e.g. Ana"; nameInput.setAttribute("aria-label", "New subject name");
        const status = el("span", "minimax-h3-director-inline-status"); status.setAttribute("role", "status");
        const create = button("Create & place", () => {}, "minimax-h3-button minimax-h3-button-primary"); create.type = "submit";
        const cancel = button("Cancel", () => { controller.directorUiState.creatingSubject = false; rerender(); }, "minimax-h3-button minimax-h3-button-secondary");
        creator.addEventListener("submit", (event) => {
            event.preventDefault();
            const name = nameInput.value.trim();
            if (!name) { nameInput.setAttribute("aria-invalid", "true"); status.textContent = "Name the subject first."; nameInput.focus(); return; }
            const bundle = createSceneSubjectBundle(project, plan, selected.id, name);
            const committed = controller.replaceProjectBundleAtomically?.({ mediaProject: bundle.project, shotPlan: bundle.shotPlan });
            if (!committed?.ok) { status.textContent = committed?.message || "Could not create the subject and place it atomically."; return; }
            controller.projectUiState.subjectSelectedId = bundle.subject.id;
            controller.directorUiState.creatingSubject = false;
            controller.directorUiState.composeFeedback = `${bundle.subject.name} created as <Subject ${bundle.subject.h3Index}> and placed in this scene.`;
            rerender();
        });
        creator.append(nameInput, create, cancel, status); setup.appendChild(creator); queueMicrotask(() => nameInput.focus());
    }
    const castPicker = el("div", "minimax-h3-director-cast-picker"); castPicker.setAttribute("aria-label", "Subjects in this scene");
    for (const subject of project?.subjects ?? []) {
        const present = (selected.subjects ?? []).some((entry) => entry.subjectId === subject.id && entry.presence !== "absent");
        const chip = button(subject.name || subject.id, () => { setSceneSubjectPresence(selected, subject.id, !present); commitPlan(controller, plan); rerender(); }, "minimax-h3-director-cast-chip");
        chip.setAttribute("aria-pressed", String(present)); castPicker.appendChild(chip);
    }
    if (!(project?.subjects ?? []).length) castPicker.appendChild(el("span", "minimax-h3-director-placeholder", "Create subjects in Library"));
    setup.appendChild(castPicker);
    const environmentField = el("label", "minimax-h3-studio-field"); environmentField.appendChild(el("span", "", "Environment / background"));
    const environmentSelect = el("select");
    for (const [value, label] of [["", "No environment"], ...(project?.environments ?? []).map((environment) => [environment.id, environment.name || environment.id])]) {
        const option = el("option", "", label); option.value = value; environmentSelect.appendChild(option);
    }
    environmentSelect.value = selected.environment?.environmentId ?? "";
    environmentSelect.addEventListener("change", () => { setSceneEnvironment(selected, environmentSelect.value); commitPlan(controller, plan); rerender(); });
    environmentField.appendChild(environmentSelect); setup.appendChild(environmentField); inspector.appendChild(setup);
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
    feedback.textContent = controller.directorUiState.composeFeedback || "";
    feedback.dataset.valid = "true"; feedback.hidden = !feedback.textContent; container.appendChild(feedback);
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
        const cameraSummary = composeCameraSummary(shot);
        const card = button("", () => { controller.shotUiState.selectedId = shot.id; rerender(); }, "minimax-h3-director-scene-card");
        card.dataset.selected = String(shot.id === controller.shotUiState.selectedId);
        card.append(
            el("span", "minimax-h3-director-scene-number", String(index + 1).padStart(2, "0")),
            el("strong", "", shot.action || "Untitled scene"),
            el("small", "", `${shot.generationId || "g1"} · ${subjectNames(shot, project).length} subjects`),
            el("small", "minimax-h3-director-scene-camera", `${cameraSummary.icon} ${cameraSummary.movement}`),
        );
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
