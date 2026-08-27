import { cameraInstructionPreview, cameraSceneModel, VISUAL_CAMERA_MOTIONS } from "./camera_planner.js";
import { renderCameraTab } from "./tab_camera.js";
import { renderCameraLookTab } from "./tab_camera_look.js";
import { createEnvironmentDraft, renderEnvironmentsTab } from "./tab_environments.js";
import { projectForController, uniqueId } from "./project_editor.js";
import { referenceDirectorModel, resolvedReferenceInputs } from "./reference_director.js";
import { disconnectPurposeReference, replacePurposeReference } from "./media_workflows.js";
import { mediaTypeForFile, referenceSourceForAsset, setReferenceSource, sourcePreviewUrl } from "./reference_sources.js";
import { editableShotPlan, normalizeShotPlanV2, serializeStructuredJson } from "./schema.js";
import { renderReferencesTab } from "./tab_references.js";
import { renderStagingTab } from "./tab_staging.js";
import { createSubjectDraft, renderSubjectsTab } from "./tab_subjects.js";
import { insertSubjectMention } from "../subject_mentions_model.js";
import {
    DIALOGUE_CHANNEL_CHOICES,
    DIALOGUE_DELIVERY_CHOICES,
    normalizedDialogueControls,
    voiceColorChoices,
} from "./dialogue_catalog.js";

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
    return controller.directorUiState ??= { composeMode: "build", libraryMode: "subjects", castPlacesMode: "subjects", generationId: "" };
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

function applySceneEdit(controller, result, rerender) {
    if (!result || commitPlan(controller, result.plan) === false) return false;
    controller.shotUiState.plan = result.plan;
    controller.shotUiState.selectedId = result.selectedId;
    delete directorState(controller).confirmDeleteShotId;
    rerender();
    return true;
}

function nextShotId(shots) {
    const ids = new Set(shots.map((shot) => shot.id));
    let index = shots.length + 1;
    while (ids.has(`s${index}`)) index += 1;
    return `s${index}`;
}

export function duplicateScene(plan, shotId) {
    const next = structuredClone(plan);
    const index = next.shots.findIndex((shot) => shot.id === shotId);
    if (index < 0 || next.shots.length >= 64) return null;
    const copy = structuredClone(next.shots[index]);
    copy.id = nextShotId(next.shots);
    next.shots.splice(index + 1, 0, copy);
    return { plan: next, selectedId: copy.id };
}

export function removeScene(plan, shotId) {
    const next = structuredClone(plan);
    const index = next.shots.findIndex((shot) => shot.id === shotId);
    if (index < 0) return null;
    next.shots.splice(index, 1);
    return { plan: next, selectedId: next.shots[Math.min(index, next.shots.length - 1)]?.id ?? null };
}

export function moveScene(plan, shotId, direction) {
    const next = structuredClone(plan);
    const index = next.shots.findIndex((shot) => shot.id === shotId);
    const target = index + Math.sign(direction);
    if (index < 0 || target < 0 || target >= next.shots.length) return null;
    [next.shots[index], next.shots[target]] = [next.shots[target], next.shots[index]];
    return { plan: next, selectedId: shotId };
}

export function reorderScene(plan, shotId, beforeShotId) {
    if (!shotId || shotId === beforeShotId) return null;
    const next = structuredClone(plan);
    const from = next.shots.findIndex((shot) => shot.id === shotId);
    const moving = from >= 0 ? next.shots.splice(from, 1)[0] : null;
    const target = next.shots.findIndex((shot) => shot.id === beforeShotId);
    if (!moving || target < 0) return null;
    next.shots.splice(target, 0, moving);
    return { plan: next, selectedId: shotId };
}

function subjectNames(shot, project) {
    const subjects = new Map((project?.subjects ?? []).map((subject) => [subject.id, subject.name || subject.id]));
    return (shot?.subjects ?? []).filter((entry) => entry.presence !== "absent").map((entry) => subjects.get(entry.subjectId) || entry.subjectId);
}

function environmentName(shot, project) {
    const id = shot?.environment?.environmentId;
    return (project?.environments ?? []).find((environment) => environment.id === id)?.name || id || "No background assigned";
}

function shotEditorialName(shot) {
    const raw = String(shot?.title || shot?.action || "").trim();
    const cleaned = raw.replace(/^SHOT-[A-Z0-9_-]+:\s*/i, "").replace(/\s+/g, " ");
    const title = cleaned || "Untitled shot";
    return title.length > 72 ? `${title.slice(0, 69)}…` : title;
}

export function shotEditorialTitle(shot, index = 0) {
    return `Shot ${String(index + 1).padStart(2, "0")} — ${shotEditorialName(shot)}`;
}

function generationDisplay(project, generationId) {
    const generation = (project?.generations ?? []).find((item) => item.id === generationId);
    const inferred = Math.max(1, (project?.generations ?? []).indexOf(generation) + 1);
    return `Generation ${generation?.order ?? inferred}`;
}

const COMPOSE_TARGETS = Object.freeze({
    subject_identity: { label: "Image", type: "picture" },
    identity_override: { label: "Image override", type: "picture" },
    voice: { label: "Voice", type: "audio" },
    voice_override: { label: "Voice override", type: "audio" },
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

export function addSceneDialogueBeat(shot, speakerId, text, delivery = "says", channel = "on_screen", mood = "") {
    const spoken = String(text ?? "").trim();
    if (!spoken) return null;
    shot.actionBeats ??= [];
    const used = new Set(shot.actionBeats.map((beat) => beat.id));
    let index = shot.actionBeats.length + 1;
    while (used.has(`beat${index}`)) index += 1;
    const count = shot.actionBeats.length;
    const at = count ? Math.min(.95, Math.round(((count + 1) / (count + 2)) * 100) / 100) : .5;
    const legacyVoiceOver = delivery === "voice_over";
    const dialogue = {
        text: spoken,
        delivery: DIALOGUE_DELIVERY_CHOICES.some(([id]) => id === delivery) ? delivery : "says",
    };
    if (channel === "voice_over" || legacyVoiceOver) dialogue.channel = "voice_over";
    if (String(mood ?? "").trim()) dialogue.mood = String(mood).trim();
    if (speakerId) dialogue.speakerId = speakerId;
    const beat = { id: `beat${index}`, at, dialogue };
    shot.actionBeats.push(beat);
    shot.actionBeats.sort((left, right) => Number(left.at) - Number(right.at));
    return beat;
}

export function removeSceneDialogueBeat(shot, beatId) {
    const beat = (shot.actionBeats ?? []).find((item) => item.id === beatId);
    if (!beat?.dialogue) return false;
    delete beat.dialogue;
    if (!beat.action) shot.actionBeats.splice(shot.actionBeats.indexOf(beat), 1);
    if (!shot.actionBeats.length) delete shot.actionBeats;
    return true;
}

export function composeSceneAudio(project, shot) {
    const assets = new Map((project?.assets ?? []).map((asset) => [asset.id, asset]));
    const subjects = new Map((project?.subjects ?? []).map((subject) => [subject.id, subject]));
    const presentIds = new Set((shot?.subjects ?? []).filter((entry) => entry.presence !== "absent").map((entry) => entry.subjectId));
    const voices = [...presentIds].map((id) => subjects.get(id)).filter(Boolean).map((subject) => ({
        subjectId: subject.id,
        name: subject.name || subject.id,
        alias: `<Subject ${subject.h3Index ?? "?"}>`,
        asset: assets.get(subject.defaultVoiceAssetId) ?? null,
    }));
    const dialogues = (shot?.actionBeats ?? []).filter((beat) => beat.dialogue).map((beat) => {
        const subject = subjects.get(beat.dialogue.speakerId);
        const controls = normalizedDialogueControls(beat.dialogue);
        return {
            beatId: beat.id,
            at: Number(beat.at ?? 0),
            text: beat.dialogue.text ?? "",
            delivery: controls.delivery,
            channel: controls.channel,
            mood: controls.mood,
            subjectId: subject?.id ?? "",
            speaker: subject?.name || "Unspecified speaker",
            alias: subject ? `<Subject ${subject.h3Index ?? "?"}>` : "",
        };
    });
    const references = (shot?.referenceUses ?? []).filter((use) => ["voice", "exact_dialogue", "soundtrack"].includes(use.role)).map((use) => ({
        asset: assets.get(use.assetId) ?? null,
        assetId: use.assetId,
        role: use.role,
        targetIds: use.targetIds ?? [],
    }));
    return { voices, dialogues, references };
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

export function createSceneEnvironmentBundle(project, shotPlan, shotId, name) {
    const nextProject = structuredClone(project);
    const nextPlan = structuredClone(shotPlan);
    const environment = createEnvironmentDraft(nextProject, name);
    nextProject.environments.push(environment);
    const shot = nextPlan.shots.find((candidate) => candidate.id === shotId);
    if (shot) setSceneEnvironment(shot, environment.id);
    return { project: nextProject, shotPlan: nextPlan, environment };
}

export function connectSubjectAssetToScene(project, shotPlan, shotId, assetId, subjectId) {
    const asset = project?.assets?.find((item) => item.id === assetId);
    const purposeId = asset?.type === "picture" ? "subject_identity"
        : asset?.type === "audio" ? "voice"
        : asset?.type === "video" ? "performance" : "";
    if (!purposeId) return { ok: false, issues: ["Choose an image, audio or video reference for the Subject."] };
    const nextPlan = structuredClone(shotPlan);
    const shot = nextPlan.shots?.find((item) => item.id === shotId);
    if (!shot) return { ok: false, issues: ["Choose an existing shot."] };
    setSceneSubjectPresence(shot, subjectId, true);
    const result = replacePurposeReference(composeConnectionInput(project, nextPlan, shot, assetId, purposeId, subjectId));
    if (result.ok && purposeId === "subject_identity") {
        const subject = result.project.subjects.find((item) => item.id === subjectId);
        if (subject && /^(?:new\s+)?subject(?:\s+\d+)?$/i.test(String(subject.name ?? "").trim())) {
            subject.name = asset.name || subject.name;
            result.summary = `${asset.name} → identity and Subject name`;
        }
    }
    return result;
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

export function composeLlmHandoff(project, shotPlan, shot) {
    const generationId = shot?.generationId ?? project?.generations?.[0]?.id ?? "g1";
    const shotIndex = Math.max(0, (shotPlan?.shots ?? []).findIndex((candidate) => candidate.id === shot?.id));
    const model = referenceDirectorModel(project, shotPlan, generationId);
    const byAsset = new Map(model.assets.map((asset) => [asset.id, asset]));
    const visual = composeVisualAssignments(project, shot);
    const link = (asset, role) => asset ? {
        assetId: asset.id,
        name: asset.name || asset.id,
        role,
        physicalLabel: byAsset.get(asset.id)?.physicalLabel ?? "Unassigned",
    } : null;
    const subjects = visual.subjects.map((entry) => ({
        id: entry.subject.id,
        name: entry.subject.name || entry.subject.id,
        alias: `<Subject ${entry.subject.h3Index ?? "?"}>`,
        links: [
            ...entry.identityAssets.map((asset) => link(asset, "Image")),
            link(entry.voiceAsset, "Voice"),
            ...entry.performanceAssets.map((asset) => link(asset, "Performance")),
        ].filter(Boolean),
    }));
    const environment = visual.environment ? {
        id: visual.environment.id,
        name: visual.environment.name || visual.environment.id,
        links: visual.backgroundAssets.map((asset) => link(asset, "Background")).filter(Boolean),
    } : null;
    const subjectById = new Map(subjects.map((subject) => [subject.id, subject]));
    const referenceUses = (shot?.referenceUses ?? []).map((use) => {
        const asset = byAsset.get(use.assetId);
        const target = subjectById.get(use.targetIds?.[0]) ?? (use.targetIds?.[0] === environment?.id ? environment : null);
        return {
            ...link(asset ?? { id: use.assetId, name: use.assetId }, readableToken(use.role, "Reference")),
            target: target?.alias || target?.name || "This Shot",
        };
    });
    const camera = composeCameraSummary(shot);
    const lines = [`Shot ${String(shotIndex + 1).padStart(2, "0")}`, `Action: ${shot?.action || "Unspecified"}`];
    if (subjects.length) {
        lines.push("Cast:");
        for (const subject of subjects) lines.push(`- ${subject.alias} ${subject.name}${subject.links.length ? ` | ${subject.links.map((item) => `${item.role} ${item.physicalLabel}`).join(" | ")}` : ""}`);
    }
    if (environment) lines.push(`Set: ${environment.name}${environment.links.length ? ` | ${environment.links.map((item) => item.physicalLabel).join(", ")}` : ""}`);
    if (referenceUses.length) {
        lines.push("Shot references:");
        for (const item of referenceUses) lines.push(`- ${item.role} ${item.physicalLabel} → ${item.target}`);
    }
    lines.push(`Camera: ${camera.start} → ${camera.movement} → ${camera.end}`);
    return { generationId, subjects, environment, referenceUses, camera, text: lines.join("\n") };
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

function composeLlmLinkChip(item, sources) {
    const chip = el("span", "minimax-h3-director-llm-link", `${item.role} · ${item.physicalLabel}`);
    const state = item.physicalLabel === "Unassigned" ? "unassigned" : sources[item.assetId] ? "ready" : "missing";
    chip.dataset.state = state;
    chip.title = `${item.name} · ${state === "ready" ? "physical file ready" : state === "missing" ? "physical file missing" : "H3 slot unassigned"}`;
    return chip;
}

function composeLlmHandoffPanel(handoff, sources) {
    const section = el("section", "minimax-h3-director-llm-handoff");
    const heading = el("div", "minimax-h3-director-inspector-heading");
    const copy = button("Copy brief", async () => {
        const status = section.querySelector("[role=status]");
        try {
            if (!globalThis.navigator?.clipboard?.writeText) throw new Error("Clipboard unavailable");
            await globalThis.navigator.clipboard.writeText(handoff.text);
            status.textContent = "Copied";
        } catch (error) { status.textContent = error?.message || "Clipboard unavailable"; }
    }, "minimax-h3-director-text-button");
    heading.append(el("strong", "", "LLM handoff"), copy); section.appendChild(heading);
    section.appendChild(el("p", "minimax-h3-director-llm-note", "Derived from this Shot · aliases and H3 outputs are not editable here."));
    for (const subject of handoff.subjects) {
        const row = el("div", "minimax-h3-director-llm-row");
        const identity = el("span", "minimax-h3-director-llm-identity"); identity.append(el("b", "", subject.alias), el("span", "", subject.name));
        const links = el("span", "minimax-h3-director-llm-links");
        for (const item of subject.links) links.appendChild(composeLlmLinkChip(item, sources));
        if (!subject.links.length) links.appendChild(el("small", "", "No media assigned"));
        row.append(identity, links); section.appendChild(row);
    }
    if (handoff.environment) {
        const row = el("div", "minimax-h3-director-llm-row");
        const identity = el("span", "minimax-h3-director-llm-identity"); identity.append(el("b", "", "SET"), el("span", "", handoff.environment.name));
        const links = el("span", "minimax-h3-director-llm-links");
        for (const item of handoff.environment.links) links.appendChild(composeLlmLinkChip(item, sources));
        if (!handoff.environment.links.length) links.appendChild(el("small", "", "No background media"));
        row.append(identity, links); section.appendChild(row);
    }
    const shotOnly = handoff.referenceUses.filter((item) => !["Identity reinforcement", "Voice", "Environment view"].includes(item.role));
    if (shotOnly.length) {
        const row = el("div", "minimax-h3-director-llm-row");
        const identity = el("span", "minimax-h3-director-llm-identity"); identity.append(el("b", "", "CUT"), el("span", "", generationDisplay(project, handoff.generationId)));
        const links = el("span", "minimax-h3-director-llm-links");
        for (const item of shotOnly) links.appendChild(composeLlmLinkChip(item, sources));
        row.append(identity, links); section.appendChild(row);
    }
    const status = el("small", "minimax-h3-director-llm-copy-status"); status.setAttribute("role", "status"); section.appendChild(status);
    return section;
}

function composeAudioPlayer(asset, source) {
    const url = sourcePreviewUrl(source);
    if (!asset || !url) return null;
    const audio = el("audio", "minimax-h3-director-audio-player");
    audio.controls = true; audio.preload = "metadata"; audio.src = url;
    audio.setAttribute("aria-label", `Preview ${asset.name || asset.id}`);
    return audio;
}

function composeDialogueField(label, control, wide = false) {
    const wrapper = el("label", `minimax-h3-director-dialogue-field${wide ? " is-wide" : ""}`);
    wrapper.append(el("small", "", label), control);
    return wrapper;
}

function composeDialogueSoundPanel(controller, project, plan, shot, sources, rerender) {
    const model = composeSceneAudio(project, shot);
    const section = el("section", "minimax-h3-director-dialogue-sound");
    const heading = el("div", "minimax-h3-director-inspector-heading");
    heading.append(
        el("strong", "", "Dialogue & sound"),
        button("+ Dialogue", () => { controller.directorUiState.creatingDialogue = true; rerender(); }, "minimax-h3-director-text-button"),
    );
    section.appendChild(heading);
    if (controller.directorUiState.creatingDialogue) {
        const form = el("form", "minimax-h3-director-dialogue-form");
        const speaker = el("select"); speaker.setAttribute("aria-label", "Dialogue speaker");
        for (const voice of model.voices) { const option = el("option", "", `${voice.name} · ${voice.alias}`); option.value = voice.subjectId; speaker.appendChild(option); }
        const delivery = el("select"); delivery.setAttribute("aria-label", "Dialogue delivery");
        for (const [value, label] of DIALOGUE_DELIVERY_CHOICES) { const option = el("option", "", label); option.value = value; delivery.appendChild(option); }
        const channel = el("select"); channel.setAttribute("aria-label", "Dialogue channel");
        for (const [value, label] of DIALOGUE_CHANNEL_CHOICES) { const option = el("option", "", label); option.value = value; channel.appendChild(option); }
        const voiceColor = el("select"); voiceColor.setAttribute("aria-label", "Dialogue voice color");
        for (const [value, label] of voiceColorChoices()) { const option = el("option", "", label); option.value = value; voiceColor.appendChild(option); }
        const words = el("textarea"); words.placeholder = "Exact spoken words"; words.maxLength = 4000; words.setAttribute("aria-label", "Exact spoken words");
        const status = el("small", "minimax-h3-director-inline-status"); status.setAttribute("role", "status");
        const create = button("Add line", () => {}, "minimax-h3-button minimax-h3-button-primary"); create.type = "submit";
        const cancel = button("Cancel", () => { controller.directorUiState.creatingDialogue = false; rerender(); }, "minimax-h3-button minimax-h3-button-secondary");
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            if (!model.voices.length) { status.textContent = "Place a subject in this Shot first."; return; }
            const nextPlan = structuredClone(plan);
            const nextShot = nextPlan.shots.find((item) => item.id === shot.id);
            const beat = addSceneDialogueBeat(nextShot, speaker.value, words.value, delivery.value, channel.value, voiceColor.value);
            if (!beat) { status.textContent = "Write the exact spoken words first."; words.focus(); return; }
            if (commitPlan(controller, nextPlan) === false) { status.textContent = "Could not save the dialogue line."; return; }
            controller.shotUiState.plan = nextPlan;
            controller.directorUiState.creatingDialogue = false;
            controller.directorUiState.composeFeedback = `Dialogue added to ${model.voices.find((item) => item.subjectId === speaker.value)?.name || "this Shot"}.`;
            rerender();
        });
        form.append(
            composeDialogueField("Speaker", speaker),
            composeDialogueField("Channel", channel),
            composeDialogueField("Delivery", delivery),
            composeDialogueField("Voice color", voiceColor),
            composeDialogueField("Exact spoken words", words, true),
            create, cancel, status,
        );
        section.appendChild(form);
        queueMicrotask(() => words.focus());
    }
    const voiceGroup = el("div", "minimax-h3-director-sound-group"); voiceGroup.appendChild(el("small", "minimax-h3-director-kicker", "SUBJECT VOICES"));
    for (const voice of model.voices) {
        const row = el("div", "minimax-h3-director-voice-row");
        const copy = el("span"); copy.append(el("b", "", `${voice.name} · ${voice.alias}`), el("small", "", voice.asset ? `Default voice · ${voice.asset.name || voice.asset.id}` : "No default voice assigned"));
        row.appendChild(copy);
        const player = composeAudioPlayer(voice.asset, sources[voice.asset?.id]); if (player) row.appendChild(player);
        voiceGroup.appendChild(row);
    }
    if (!model.voices.length) voiceGroup.appendChild(el("small", "", "Place a subject to assign dialogue and voice."));
    section.appendChild(voiceGroup);
    const dialogueGroup = el("div", "minimax-h3-director-sound-group"); dialogueGroup.appendChild(el("small", "minimax-h3-director-kicker", "LINES IN THIS SHOT"));
    for (const dialogue of model.dialogues) {
        const row = el("div", "minimax-h3-director-dialogue-row");
        const channel = dialogue.channel === "voice_over" ? "V.O." : "On-screen";
        const voiceColor = dialogue.mood ? ` · ${dialogue.mood}` : "";
        const copy = el("span"); copy.append(el("b", "", `${dialogue.alias || "S?"} · ${dialogue.speaker}`), el("q", "", dialogue.text), el("small", "", `${channel} · ${readableToken(dialogue.delivery, "Says")}${voiceColor} · ${Math.round(dialogue.at * 100)}%`));
        const remove = button("×", () => {
            const nextPlan = structuredClone(plan);
            const nextShot = nextPlan.shots.find((item) => item.id === shot.id);
            if (!removeSceneDialogueBeat(nextShot, dialogue.beatId)) return;
            if (commitPlan(controller, nextPlan) === false) return;
            controller.shotUiState.plan = nextPlan;
            controller.directorUiState.composeFeedback = `Dialogue removed from ${dialogue.speaker}.`;
            rerender();
        }, "minimax-h3-director-text-button");
        remove.setAttribute("aria-label", `Remove dialogue by ${dialogue.speaker}`); row.append(copy, remove); dialogueGroup.appendChild(row);
    }
    if (!model.dialogues.length) dialogueGroup.appendChild(el("small", "", "No authored dialogue in this Shot."));
    section.appendChild(dialogueGroup);
    const referenceGroup = el("div", "minimax-h3-director-sound-group"); referenceGroup.appendChild(el("small", "minimax-h3-director-kicker", "SHOT AUDIO REFERENCES"));
    for (const reference of model.references) {
        const row = el("div", "minimax-h3-director-audio-reference-row");
        row.appendChild(el("span", "", `${readableToken(reference.role)} · ${reference.asset?.name || reference.assetId}`));
        const player = composeAudioPlayer(reference.asset, sources[reference.assetId]); if (player) row.appendChild(player);
        referenceGroup.appendChild(row);
    }
    if (!model.references.length) referenceGroup.appendChild(el("small", "", "No voice override, exact dialogue audio or soundtrack assigned."));
    section.appendChild(referenceGroup);
    const ambience = el("p", "minimax-h3-director-ambience-note");
    ambience.append(el("b", "", "Ambience · "), document.createTextNode("derived from visible action and the Prompt Enhancer Audio policies; this Shot does not create an unsupported parallel sound field."));
    section.appendChild(ambience);
    return section;
}

function composeDropTarget(controller, purposeId, relationId, selectedAsset, connect, importFile, disconnect, connected = false) {
    const definition = COMPOSE_TARGETS[purposeId];
    const wrapper = el("span", "minimax-h3-director-drop-wrapper");
    wrapper.dataset.connected = String(connected);
    const projectDefault = ["subject_identity", "voice"].includes(purposeId);
    wrapper.dataset.scope = projectDefault ? "project" : "shot";
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
    wrapper.append(target, el("small", "minimax-h3-reference-scope", projectDefault ? "Project default" : "This Shot"), importButton);
    if (connected) {
        const disconnectButton = button("×", () => disconnect(purposeId, relationId), "minimax-h3-director-drop-disconnect");
        disconnectButton.setAttribute("aria-label", `Disconnect ${definition.label.toLowerCase()} reference`);
        disconnectButton.title = `Disconnect from ${definition.label}; keep the file in Library · Files`;
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
    header.append(el("div", "", "References"), el("span", "", assets.length
        ? "Select or drag onto a highlighted destination"
        : "Import files in Library · Files first"));
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
    if (!assets.length) rail.appendChild(button(
        "Open Library",
        () => controller.navigateStudio?.(controller.isVisualReferenceDirector ? "library" : "media"),
        "minimax-h3-director-tray-empty",
    ));
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
        empty.append(el("h3", "", "Build the first Shot"), el("p", "", "A Shot is one continuous block between cuts. Start with visible action, then add cast, background, references and camera."));
        empty.appendChild(button("Create first Shot", () => {
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
    const llmHandoff = composeLlmHandoff(project, plan, selected);
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
        let uploaded = false;
        try {
            if (typeof controller.uploadReferenceFile !== "function" || typeof controller.replaceProjectBundleAtomically !== "function") {
                throw new Error("Direct import is unavailable in this ComfyUI session.");
            }
            const draft = createImportedAssetDraft(project, file, mediaType, `${definition.label} reference`);
            const nextProject = draft.project;
            const assetId = draft.asset.id;
            const name = draft.asset.name;
            const workingPlan = connectionPlan(purposeId, relationId);
            const workingShot = workingPlan.shots.find((shot) => shot.id === selected.id) ?? selected;
            const connected = replacePurposeReference(composeConnectionInput(nextProject, workingPlan, workingShot, assetId, purposeId, relationId));
            if (!connected.ok) throw new Error(connected.issues.join(" "));
            const source = await controller.uploadReferenceFile(file);
            uploaded = true;
            const nextDirector = setReferenceSource(directorDocument.value, assetId, source);
            const committed = controller.replaceProjectBundleAtomically({ mediaProject: connected.project, shotPlan: connected.shotPlan, referenceDirector: nextDirector });
            if (!committed?.ok) throw new Error(committed?.message || "Could not import and connect the file atomically.");
            controller.projectUiState.selectedAssetId = assetId;
            controller.directorUiState.composeFeedback = `${name} imported and connected to ${definition.label}.`;
            rerender();
        } catch (error) {
            feedback.dataset.valid = "false"; feedback.hidden = false;
            const recovery = uploaded ? " Project data was rolled back; the content-addressed upload remains safely reusable in ComfyUI input." : "";
            feedback.textContent = `${error?.message || "Import failed."}${recovery}`;
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
        controller.directorUiState.composeFeedback = `${result.summary}. The file remains in Library · Files.`;
        rerender();
    };
    const connectSubjectAsset = (subjectId, explicitAssetId = "") => {
        const assetId = explicitAssetId || controller.projectUiState.selectedAssetId;
        const result = connectSubjectAssetToScene(project, plan, selected.id, assetId, subjectId);
        if (!result.ok) {
            feedback.dataset.valid = "false"; feedback.hidden = false;
            feedback.textContent = result.issues.join(" "); return;
        }
        const committed = controller.replaceProjectBundleAtomically?.({ mediaProject: result.project, shotPlan: result.shotPlan });
        if (!committed?.ok) {
            feedback.dataset.valid = "false"; feedback.hidden = false;
            feedback.textContent = committed?.message || "Could not place the Subject and connect its reference together."; return;
        }
        controller.projectUiState.selectedAssetId = assetId;
        delete controller.projectUiState.draggedAssetId;
        controller.directorUiState.composeFeedback = `${result.summary}; Subject placed in this Shot.`;
        rerender();
    };
    const makeSubjectDropReceiver = (control, subjectId) => {
        control.dataset.subjectDrop = "true";
        for (const eventName of ["dragenter", "dragover"]) control.addEventListener(eventName, (event) => {
            event.preventDefault();
            const assetId = controller.projectUiState.draggedAssetId || event.dataTransfer?.getData("text/plain");
            const asset = project?.assets?.find((item) => item.id === assetId);
            control.dataset.drag = ["picture", "audio", "video"].includes(asset?.type) ? "ready" : "invalid";
        });
        control.addEventListener("dragleave", () => delete control.dataset.drag);
        control.addEventListener("drop", (event) => {
            event.preventDefault(); delete control.dataset.drag;
            connectSubjectAsset(subjectId, controller.projectUiState.draggedAssetId || event.dataTransfer?.getData("text/plain"));
        });
        return control;
    };
    const layout = el("div", "minimax-h3-director-compose-grid");
    const stage = el("section", "minimax-h3-director-stage");
    stage.setAttribute("aria-label", "Selected Shot workspace");
    const backdrop = el("div", "minimax-h3-director-backdrop");
    const backdropCopy = el("div"); backdropCopy.append(el("span", "minimax-h3-director-kicker", "BACKGROUND / SET"), el("strong", "", environmentName(selected, project)));
    backdrop.append(backdropCopy);
    const backgroundMedia = el("div", "minimax-h3-director-backdrop-media");
    for (const asset of visualAssignments.backgroundAssets.slice(0, 2)) backgroundMedia.appendChild(composeBoundMedia(asset, sources[asset.id], "Background"));
    if (backgroundMedia.childElementCount) backdrop.appendChild(backgroundMedia);
    const environmentTargetId = selected.environment?.environmentId || ((project?.environments ?? []).length === 1 ? project.environments[0].id : "");
    const backgroundConnected = (selected.referenceUses ?? []).some((use) =>
        use.role === "environment_view" && (use.targetIds ?? []).includes(environmentTargetId));
    if (environmentTargetId) backdrop.appendChild(composeDropTarget(controller, "environment_view", environmentTargetId, selectedAsset, connect, importFile, disconnect, backgroundConnected));
    else if ((project?.environments ?? []).length) backdrop.appendChild(el("small", "minimax-h3-director-lane-guidance", "Choose this Shot's set in Cast & set"));
    else backdrop.appendChild(button("+ Environment", () => { directorState(controller).creatingEnvironment = true; directorState(controller).creatingSubject = false; rerender(); }, "minimax-h3-director-text-button"));
    const cast = el("div", "minimax-h3-director-cast");
    const names = subjectNames(selected, project);
    if (!names.length) {
        const onlySubject = (project?.subjects ?? []).length === 1 ? project.subjects[0] : null;
        if (onlySubject) {
            const emptyTarget = button(
                selectedAsset ? `Place ${onlySubject.name || onlySubject.id} with ${selectedAsset.name || selectedAsset.id}` : `Drop a reference to place ${onlySubject.name || onlySubject.id}`,
                () => connectSubjectAsset(onlySubject.id),
                "minimax-h3-director-empty-subject-target",
            );
            emptyTarget.setAttribute("aria-label", `Place ${onlySubject.name || onlySubject.id} in this Shot and connect the selected reference`);
            makeSubjectDropReceiver(emptyTarget, onlySubject.id); cast.appendChild(emptyTarget);
        } else cast.appendChild(el("p", "minimax-h3-director-placeholder", "Choose a Subject below, then drop its reference onto that Subject"));
    }
    for (const entry of (selected.subjects ?? []).filter((item) => item.presence !== "absent")) {
        const subject = (project?.subjects ?? []).find((candidate) => candidate.id === entry.subjectId);
        const name = subject?.name || entry.subjectId;
        const assigned = subjectAssignments.get(entry.subjectId) ?? { identityAssets: [], voiceAsset: null, performanceAssets: [] };
        const card = el("article", "minimax-h3-director-subject-card");
        const targets = el("div", "minimax-h3-director-subject-targets");
        const shotUses = selected.referenceUses ?? [];
        const performanceConnected = shotUses.some((use) => use.role === "performance" && (use.targetIds ?? []).includes(entry.subjectId));
        const identityOverrideConnected = shotUses.some((use) => use.role === "identity_reinforcement" && (use.targetIds ?? []).includes(entry.subjectId));
        const voiceOverrideConnected = shotUses.some((use) => use.role === "voice" && (use.targetIds ?? []).includes(entry.subjectId));
        targets.append(
            composeDropTarget(controller, "subject_identity", entry.subjectId, selectedAsset, connect, importFile, disconnect, Boolean(subject?.identityAssetIds?.length)),
            composeDropTarget(controller, "voice", entry.subjectId, selectedAsset, connect, importFile, disconnect, Boolean(subject?.defaultVoiceAssetId)),
            composeDropTarget(controller, "identity_override", entry.subjectId, selectedAsset, connect, importFile, disconnect, identityOverrideConnected),
            composeDropTarget(controller, "voice_override", entry.subjectId, selectedAsset, connect, importFile, disconnect, voiceOverrideConnected),
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
    const action = el("label", "minimax-h3-director-action");
    action.appendChild(el("span", "minimax-h3-director-kicker", "VISIBLE ACTION · THIS SHOT"));
    const actionInput = el("textarea"); actionInput.value = selected.action ?? ""; actionInput.placeholder = "Describe what visibly changes during this Shot.";
    actionInput.setAttribute("aria-label", "Visible action for selected Shot");
    actionInput.addEventListener("blur", () => { selected.action = actionInput.value.trim(); commitPlan(controller, plan); rerender(); });
    action.appendChild(actionInput);
    const mentionRow = el("div", "minimax-h3-shot-mention-row");
    mentionRow.appendChild(el("span", "", "Insert subject"));
    for (const subject of project?.subjects ?? []) {
        const mention = `<Subject ${subject.h3Index}>`;
        const identityAsset = (subject.identityAssetIds ?? []).map((id) => project.assets.find((asset) => asset.id === id)).find(Boolean);
        const mentionButton = button("", () => {
            const result = insertSubjectMention(actionInput.value, actionInput.selectionStart, actionInput.selectionEnd, mention);
            actionInput.value = result.value;
            actionInput.setSelectionRange(result.selectionStart, result.selectionEnd); actionInput.focus();
            selected.action = result.value.trim(); commitPlan(controller, plan);
        }, "minimax-h3-director-text-button minimax-h3-shot-subject-chip");
        const avatar = el("span", "minimax-h3-shot-subject-avatar");
        const previewUrl = sourcePreviewUrl(sources[identityAsset?.id]);
        if (previewUrl) { const image = el("img"); image.src = previewUrl; image.alt = ""; avatar.appendChild(image); }
        else avatar.textContent = String(subject.name || "S").slice(0, 1).toUpperCase();
        const chipCopy = el("span", "minimax-h3-shot-subject-copy");
        chipCopy.append(el("strong", "", subject.name || mention), el("small", "", identityAsset ? `Identity · ${identityAsset.name || identityAsset.id}` : "No identity image"));
        mentionButton.append(avatar, chipCopy, el("span", "minimax-h3-shot-subject-status", identityAsset ? "✓" : "+"));
        mentionButton.title = [subject.description, identityAsset ? `Identity: ${identityAsset.name || identityAsset.id}` : "No identity image", subject.defaultVoiceAssetId ? "Default voice assigned" : "No default voice"].filter(Boolean).join(" · ");
        mentionButton.setAttribute("aria-label", `Insert ${subject.name || mention}, ${mention}`);
        mentionRow.appendChild(mentionButton);
    }
    if ((project?.subjects ?? []).length) action.appendChild(mentionRow);
    const cameraSummary = composeCameraSummary(selected);
    const camera = button("", () => { directorState(controller).composeMode = "camera"; rerender(); }, "minimax-h3-director-camera-line");
    camera.setAttribute("aria-label", `Direct camera for ${shotEditorialTitle(selected, plan.shots.indexOf(selected))}. ${cameraInstructionPreview(selected, project ?? {})}`);
    const cameraHeading = el("span", "minimax-h3-director-camera-heading");
    cameraHeading.append(el("span", "minimax-h3-director-kicker", "CAMERA · THIS SHOT"), el("strong", "", cameraSummary.configured ? "Directed" : "Inherited"), el("span", "minimax-h3-director-camera-edit", "Edit →"));
    const phases = el("span", "minimax-h3-director-camera-phases");
    for (const [index, label, value] of [["1", "Start", cameraSummary.start], [cameraSummary.icon, "Move", cameraSummary.movement], ["3", "End", cameraSummary.end]]) {
        const phase = el("span", "minimax-h3-director-camera-phase");
        phase.append(el("b", "", index), el("small", "", label), el("span", "", value)); phases.appendChild(phase);
    }
    camera.append(cameraHeading, phases);
    stage.append(backdrop, cast, action, camera);

    const lanes = el("section", "minimax-h3-director-lanes");
    const lanesHeading = el("div", "minimax-h3-director-scene-heading");
    const lanesIdentity = el("div");
    lanesIdentity.append(el("h3", "", "References"), el("small", "", "Connect here or manage reusable files in Library · Files."));
    lanesHeading.append(lanesIdentity, el("span", "minimax-h3-scope-chip", "This Shot"));
    lanes.appendChild(lanesHeading);
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
        lane.appendChild(el("span", values.length ? "" : "is-empty", values.join(" · ")
            || "Drop or connect a reference in Library · Files"));
        if (laneName === "Performance" && presentSubjects.length === 1) lane.appendChild(composeDropTarget(controller, "performance", presentSubjects[0].subjectId, selectedAsset, connect, importFile, disconnect, values.length > 0));
        else if (lanePurpose[laneName]) lane.appendChild(composeDropTarget(controller, lanePurpose[laneName], "", selectedAsset, connect, importFile, disconnect, values.length > 0));
        else lane.appendChild(el("small", "minimax-h3-director-lane-guidance", "Use a subject card"));
        lanes.appendChild(lane);
    }
    layout.append(stage, lanes);

    const inspector = el("aside", "minimax-h3-director-inspector");
    const inspectorHeading = el("div", "minimax-h3-director-scene-heading");
    const inspectorIdentity = el("div"); inspectorIdentity.append(el("span", "minimax-h3-director-kicker", "SHOT INSPECTOR"), el("h3", "", "This Shot"));
    inspectorHeading.append(inspectorIdentity, el("span", "minimax-h3-scope-chip", "This Shot")); inspector.appendChild(inspectorHeading);
    const setup = el("section", "minimax-h3-director-scene-setup");
    const setupHeading = el("div", "minimax-h3-director-inspector-heading");
    const setupActions = el("div", "minimax-h3-director-setup-actions");
    setupActions.append(
        button("+ Subject", () => { controller.directorUiState.creatingSubject = true; controller.directorUiState.creatingEnvironment = false; rerender(); }, "minimax-h3-director-text-button"),
        button("+ Environment", () => { controller.directorUiState.creatingEnvironment = true; controller.directorUiState.creatingSubject = false; rerender(); }, "minimax-h3-director-text-button"),
        button(controller.isVisualReferenceDirector ? "Manage Library" : "Manage Subjects", () => {
            controller.directorUiState.libraryMode = "subjects";
            controller.directorUiState.castPlacesMode = "subjects";
            controller.navigateStudio?.(controller.isVisualReferenceDirector ? "library" : "subjects");
        }, "minimax-h3-director-text-button"),
    );
    setupHeading.append(el("strong", "", "Cast & background"), setupActions);
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
            controller.directorUiState.composeFeedback = `${bundle.subject.name} created as <Subject ${bundle.subject.h3Index}> and placed in this Shot.`;
            rerender();
        });
        creator.append(nameInput, create, cancel, status); setup.appendChild(creator); queueMicrotask(() => nameInput.focus());
    }
    if (controller.directorUiState.creatingEnvironment) {
        const creator = el("form", "minimax-h3-director-inline-creator");
        const nameInput = el("input"); nameInput.type = "text"; nameInput.maxLength = 200; nameInput.placeholder = "Environment name, e.g. Ana's apartment"; nameInput.setAttribute("aria-label", "New environment name");
        const status = el("span", "minimax-h3-director-inline-status"); status.setAttribute("role", "status");
        const create = button("Create & use", () => {}, "minimax-h3-button minimax-h3-button-primary"); create.type = "submit";
        const cancel = button("Cancel", () => { controller.directorUiState.creatingEnvironment = false; rerender(); }, "minimax-h3-button minimax-h3-button-secondary");
        creator.addEventListener("submit", (event) => {
            event.preventDefault();
            const name = nameInput.value.trim();
            if (!name) { nameInput.setAttribute("aria-invalid", "true"); status.textContent = "Name the environment first."; nameInput.focus(); return; }
            const bundle = createSceneEnvironmentBundle(project, plan, selected.id, name);
            const committed = controller.replaceProjectBundleAtomically?.({ mediaProject: bundle.project, shotPlan: bundle.shotPlan });
            if (!committed?.ok) { status.textContent = committed?.message || "Could not create and assign the environment atomically."; return; }
            controller.projectUiState.environmentSelectedId = bundle.environment.id;
            controller.directorUiState.creatingEnvironment = false;
            controller.directorUiState.composeFeedback = `${bundle.environment.name} created and assigned to this Shot. Use + Background to import its view.`;
            rerender();
        });
        creator.append(nameInput, create, cancel, status); setup.appendChild(creator); queueMicrotask(() => nameInput.focus());
    }
    const castPicker = el("div", "minimax-h3-director-cast-picker"); castPicker.setAttribute("aria-label", "Subjects in this Shot");
    for (const subject of project?.subjects ?? []) {
        const present = (selected.subjects ?? []).some((entry) => entry.subjectId === subject.id && entry.presence !== "absent");
        const chip = button(subject.name || subject.id, () => { setSceneSubjectPresence(selected, subject.id, !present); commitPlan(controller, plan); rerender(); }, "minimax-h3-director-cast-chip");
        chip.setAttribute("aria-pressed", String(present)); castPicker.appendChild(chip);
        chip.setAttribute("aria-label", `${present ? "Remove" : "Place"} ${subject.name || subject.id}; drop a reference to connect it`);
        makeSubjectDropReceiver(chip, subject.id);
    }
    if (!(project?.subjects ?? []).length) castPicker.appendChild(el(
        "span", "minimax-h3-director-placeholder",
        `Create a Subject here or open ${controller.isVisualReferenceDirector ? "Library" : "Cast & Places"}`,
    ));
    setup.appendChild(castPicker);
    const environmentField = el("label", "minimax-h3-studio-field"); environmentField.appendChild(el("span", "", "Environment / background"));
    const environmentSelect = el("select");
    for (const [value, label] of [["", "No environment"], ...(project?.environments ?? []).map((environment) => [environment.id, environment.name || environment.id])]) {
        const option = el("option", "", label); option.value = value; environmentSelect.appendChild(option);
    }
    environmentSelect.value = selected.environment?.environmentId ?? "";
    environmentSelect.addEventListener("change", () => { setSceneEnvironment(selected, environmentSelect.value); commitPlan(controller, plan); rerender(); });
    environmentField.appendChild(environmentSelect); setup.appendChild(environmentField); inspector.appendChild(setup);
    inspector.appendChild(composeDialogueSoundPanel(controller, project, plan, selected, sources, rerender));
    const summary = el("dl", "minimax-h3-director-scene-summary");
    for (const [term, value] of [["Generation", generationDisplay(project, selected.generationId)], ["Cast", names.length || "—"], ["References", selected.referenceUses?.length || "—"], ["Duration", plan.timingMode === "exact" ? `${selected.durationSeconds ?? 1}s` : "Auto"]]) {
        summary.append(el("dt", "", term), el("dd", "", String(value)));
    }
    inspector.append(
        summary,
        composeLlmHandoffPanel(llmHandoff, sources),
        button("Stage subjects", () => { directorState(controller).composeMode = "staging"; rerender(); }),
        button("Direct camera", () => { directorState(controller).composeMode = "camera"; rerender(); }),
    );
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
    const copy = el("div");
    copy.append(
        el("h2", "", "Storyboard"),
        el("p", "", controller.isVisualReferenceDirector
            ? "Maintain a legacy reference project or migrate it into Prompt Studio."
            : "Build the prompt visually, Shot by Shot: cast, identity and voice, environment, action, sound and camera stay connected in one Studio Project."),
    );
    if (state.composeMode === "board" || state.composeMode === "details") state.composeMode = "build";
    top.appendChild(copy); container.appendChild(top);
    const selected = plan.shots.find((shot) => shot.id === controller.shotUiState.selectedId) ?? plan.shots[0] ?? null;
    const selectedIndex = selected ? plan.shots.indexOf(selected) : -1;
    const context = el("section", "minimax-h3-director-shot-context");
    const contextTop = el("div", "minimax-h3-director-shot-context-top");
    const identity = el("div", "minimax-h3-director-shot-context-identity");
    identity.append(
        el("span", "minimax-h3-director-kicker", selected ? "EDITING" : "COMPOSE"),
        el("strong", "", selected ? shotEditorialTitle(selected, selectedIndex) : "No Shot selected"),
    );
    const metadata = el("div", "minimax-h3-director-shot-context-meta");
    if (selected) metadata.append(
        el("span", "", generationDisplay(project, selected.generationId)),
        el("span", "", plan.timingMode === "exact" ? `${selected.durationSeconds ?? 1}s` : "Auto duration"),
        el("span", "minimax-h3-scope-chip", "This Shot"),
    );
    identity.appendChild(metadata);
    const contextActions = el("div", "minimax-h3-director-scene-actions");
    if (selected) {
        const moveLeft = button("←", () => applySceneEdit(controller, moveScene(plan, selected.id, -1), rerender), "minimax-h3-director-text-button");
        moveLeft.disabled = selectedIndex <= 0; moveLeft.title = "Move Shot left"; moveLeft.setAttribute("aria-label", "Move selected Shot left");
        const moveRight = button("→", () => applySceneEdit(controller, moveScene(plan, selected.id, 1), rerender), "minimax-h3-director-text-button");
        moveRight.disabled = selectedIndex >= plan.shots.length - 1; moveRight.title = "Move Shot right"; moveRight.setAttribute("aria-label", "Move selected Shot right");
        const duplicate = button("Duplicate", () => applySceneEdit(controller, duplicateScene(plan, selected.id), rerender), "minimax-h3-director-text-button");
        duplicate.disabled = plan.shots.length >= 64; contextActions.append(moveLeft, moveRight, duplicate);
        if (state.confirmDeleteShotId === selected.id) contextActions.append(
            button("Confirm delete", () => applySceneEdit(controller, removeScene(plan, selected.id), rerender), "minimax-h3-director-text-button minimax-h3-director-delete-confirm"),
            button("Cancel", () => { delete state.confirmDeleteShotId; rerender(); }, "minimax-h3-director-text-button"),
        );
        else contextActions.appendChild(button("Delete", () => { state.confirmDeleteShotId = selected.id; rerender(); }, "minimax-h3-director-text-button minimax-h3-director-delete"));
    }
    contextTop.append(identity, modeSwitch(state, rerender, [["build", "Content"], ["staging", "Stage"], ["camera", "Camera"]]), contextActions);
    context.appendChild(contextTop);
    const strip = el("div", "minimax-h3-director-scene-strip"); strip.setAttribute("aria-label", "Shot strip");
    for (const [index, shot] of plan.shots.entries()) {
        const cameraSummary = composeCameraSummary(shot);
        const card = button("", () => { controller.shotUiState.selectedId = shot.id; rerender(); }, "minimax-h3-director-scene-card");
        card.dataset.selected = String(shot.id === controller.shotUiState.selectedId);
        card.draggable = true;
        card.addEventListener("dragstart", (event) => {
            state.draggedShotId = shot.id;
            event.dataTransfer?.setData("text/plain", shot.id);
            if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
        });
        card.addEventListener("dragover", (event) => {
            if (!state.draggedShotId || state.draggedShotId === shot.id) return;
            event.preventDefault(); card.dataset.drag = "before";
            if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
        });
        card.addEventListener("dragleave", () => delete card.dataset.drag);
        card.addEventListener("drop", (event) => {
            event.preventDefault(); delete card.dataset.drag;
            const movingId = state.draggedShotId || event.dataTransfer?.getData("text/plain");
            delete state.draggedShotId;
            applySceneEdit(controller, reorderScene(plan, movingId, shot.id), rerender);
        });
        card.addEventListener("dragend", () => { delete state.draggedShotId; });
        card.append(
            el("span", "minimax-h3-director-scene-number", String(index + 1).padStart(2, "0")),
            el("strong", "", shotEditorialName(shot)),
            el("small", "", `${generationDisplay(project, shot.generationId)} · ${subjectNames(shot, project).length} subjects`),
            el("small", "minimax-h3-director-scene-camera", `${cameraSummary.icon} ${cameraSummary.movement}`),
        );
        strip.appendChild(card);
    }
    const add = button("+ Shot", () => {
        const shot = { id: nextShotId(plan.shots), generationId: project?.generations?.[0]?.id ?? "g1", action: "" };
        if (plan.timingMode === "exact") shot.durationSeconds = 1;
        plan.shots.push(shot); controller.shotUiState.selectedId = shot.id; commitPlan(controller, plan); rerender();
    }, "minimax-h3-director-add-scene"); add.disabled = plan.shots.length >= 64; strip.appendChild(add); context.appendChild(strip); container.appendChild(context);
    if (state.composeMode === "build") renderBoard(container, controller, plan, project, rerender);
    else {
        const host = el("div", "minimax-h3-director-embedded-editor"); container.appendChild(host);
        if (state.composeMode === "staging") renderStagingTab(host, controller, { embedded: true });
        else renderCameraTab(host, controller, { embedded: true });
    }
}

export function renderCastPlaces(container, controller) {
    container.replaceChildren();
    const state = directorState(controller);
    if (!["subjects", "environments"].includes(state.castPlacesMode)) state.castPlacesMode = "subjects";
    const top = el("header", "minimax-h3-director-workspace-header");
    const copy = el("div");
    copy.append(el("h2", "", "Cast & Places"), el("p", "", "Create reusable Subjects and Environments here. Compose decides which ones each Shot uses."));
    const switcher = el("div", "minimax-h3-director-mode-switch");
    for (const [id, label] of [["subjects", "Subjects"], ["environments", "Environments"]]) {
        const control = button(label, () => { state.castPlacesMode = id; renderCastPlaces(container, controller); }, "minimax-h3-director-mode");
        control.setAttribute("aria-selected", String(state.castPlacesMode === id)); switcher.appendChild(control);
    }
    top.append(copy, switcher); container.appendChild(top);
    const host = el("div", "minimax-h3-director-library-host"); container.appendChild(host);
    (state.castPlacesMode === "environments" ? renderEnvironmentsTab : renderSubjectsTab)(host, controller);
}

function renderFilesLibrary(container, controller) {
    container.replaceChildren();
    const project = projectForController(controller);
    if (!project) return renderReferencesTab(container, controller);
    const state = directorState(controller);
    const sourceDocument = controller.referenceDirectorDocument?.();
    const director = sourceDocument?.kind === "v1" ? sourceDocument.value : { format: "minimax-h3-reference-director", formatVersion: 1, sources: {} };
    if (!["all", "picture", "video", "audio"].includes(state.fileFilter)) state.fileFilter = "all";

    const toolbar = el("div", "minimax-h3-files-toolbar");
    const filters = el("div", "minimax-h3-director-mode-switch");
    for (const [id, label] of [["all", "All"], ["picture", "Images"], ["video", "Video"], ["audio", "Audio"]]) {
        const control = button(label, () => { state.fileFilter = id; renderFilesLibrary(container, controller); }, "minimax-h3-director-mode");
        control.setAttribute("aria-selected", String(state.fileFilter === id)); filters.appendChild(control);
    }
    const fileInput = el("input"); fileInput.type = "file"; fileInput.multiple = true; fileInput.accept = "image/*,video/*,audio/*"; fileInput.hidden = true;
    const feedback = el("p", "minimax-h3-studio-status"); feedback.hidden = true;
    const importButton = button("+ Import files", () => fileInput.click(), "minimax-h3-button minimax-h3-button-primary");
    fileInput.addEventListener("change", async () => {
        const files = [...(fileInput.files ?? [])]; if (!files.length) return;
        importButton.disabled = true; feedback.hidden = false; feedback.dataset.valid = "true"; feedback.textContent = `Importing ${files.length} file${files.length === 1 ? "" : "s"}…`;
        const nextProject = structuredClone(project); let nextDirector = structuredClone(director); const failures = [];
        for (const file of files) {
            const type = mediaTypeForFile(file);
            if (!type) { failures.push(`${file.name}: unsupported`); continue; }
            try {
                const source = await controller.uploadReferenceFile(file);
                const id = uniqueId(nextProject.assets, "asset.");
                nextProject.assets.push({ id, type, name: String(file.name).replace(/\.[^.]+$/, "") || `${type} file`, available: true });
                nextDirector = setReferenceSource(nextDirector, id, source);
            } catch (error) { failures.push(`${file.name}: ${error?.message ?? "upload failed"}`); }
        }
        const result = controller.replaceProjectBundleAtomically?.({ mediaProject: nextProject, referenceDirector: nextDirector });
        if (!result?.ok) failures.push(result?.message ?? "Could not save imported files.");
        if (failures.length) { state.fileFeedback = failures.join(" "); state.fileFeedbackValid = false; }
        else { state.fileFeedback = `${files.length} file${files.length === 1 ? "" : "s"} imported. Drag or connect them from Storyboard.`; state.fileFeedbackValid = true; }
        renderDirectorLibrary(container, controller);
    });
    toolbar.append(filters, importButton, fileInput); container.append(toolbar, feedback);
    if (state.fileFeedback) { feedback.hidden = false; feedback.dataset.valid = String(state.fileFeedbackValid !== false); feedback.textContent = state.fileFeedback; delete state.fileFeedback; }

    const assets = (project.assets ?? []).filter((asset) => state.fileFilter === "all" || asset.type === state.fileFilter);
    if (!assets.length) {
        const empty = el("section", "minimax-h3-empty-state");
        empty.append(el("h3", "", project.assets?.length ? "No files in this filter" : "Import your first reference"), el("p", "", "Images, video and audio live here once, then Subjects, Environments and Shots refer to them visually."));
        container.appendChild(empty); return;
    }
    const grid = el("div", "minimax-h3-files-grid");
    for (const asset of assets) {
        const source = referenceSourceForAsset(director, asset.id);
        const card = el("article", "minimax-h3-file-card"); card.dataset.type = asset.type; card.dataset.ready = String(Boolean(source));
        const visual = el("div", "minimax-h3-file-preview"); const url = sourcePreviewUrl(source);
        if (url && asset.type === "picture") { const image = el("img"); image.src = url; image.alt = asset.name; image.loading = "lazy"; visual.appendChild(image); }
        else if (url && asset.type === "video") { const video = el("video"); video.src = url; video.muted = true; video.preload = "metadata"; video.playsInline = true; visual.appendChild(video); }
        else visual.appendChild(el("strong", "", asset.type === "audio" ? "≋" : asset.type === "video" ? "▶" : "▧"));
        const copy = el("div", "minimax-h3-file-copy");
        copy.append(el("strong", "", asset.name || asset.id), el("small", "", `${asset.type === "picture" ? "Image" : asset.type === "video" ? "Video" : "Audio"} · ${source ? "Ready" : "Missing physical file"}`));
        const connect = button("Use in Storyboard", () => controller.navigateStudio?.("storyboard"), "minimax-h3-director-text-button");
        card.append(visual, copy, connect); grid.appendChild(card);
    }
    container.appendChild(grid);
}

export function renderDirectorLibrary(container, controller) {
    container.replaceChildren();
    const state = directorState(controller);
    const top = el("header", "minimax-h3-director-workspace-header");
    if (!["subjects", "environments", "media"].includes(state.libraryMode)) state.libraryMode = "subjects";
    const copy = el("div"); copy.append(el("h2", "", "Library"), el("p", "", "Create reusable Subjects and Environments, attach identity, voice and place references, and keep raw files in one visual library."));
    const switcher = el("div", "minimax-h3-director-mode-switch");
    for (const [id, label] of [["subjects", "Subjects"], ["environments", "Environments"], ["media", "Files"]]) {
        const control = button(label, () => { state.libraryMode = id; renderDirectorLibrary(container, controller); }, "minimax-h3-director-mode");
        control.setAttribute("aria-selected", String(state.libraryMode === id)); switcher.appendChild(control);
    }
    top.append(copy, switcher); container.appendChild(top);
    const host = el("div", "minimax-h3-director-library-host"); container.appendChild(host);
    ({ media: renderFilesLibrary, subjects: renderSubjectsTab, environments: renderEnvironmentsTab }[state.libraryMode] ?? renderSubjectsTab)(host, controller);
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
        el("p", "", "Prompt Studio owns physical files, subjects, voices, environments and shot-scoped reference intent. Visual language, mood, global cinematography, titles and credits remain in the same MiniMax H3 Prompt Enhancer, so there is only one authoritative project."),
        el("p", "minimax-h3-studio-status", "Connect reference_context to the enhancer, then open its Look section. Reference camera intent still overrides only the explicit aspects assigned in Library."),
    );
    container.appendChild(handoff);
}
