import { createEmptyState } from "./components/empty_state.js";
import { createSourcePill, createSourceStateCard, normalizedSourceState } from "./components/source_state.js";
import { localPreflight } from "./preflight.js";
import { appendProjectBundleGenerations, createProjectBundle, parseProjectBundle, summarizeProjectBundle } from "./project_bundle.js";
import { applyStarterExample, STARTER_EXAMPLES } from "./starter_examples.js";

function safeDocument(read) {
    try {
        return normalizedSourceState(read?.());
    } catch {
        return normalizedSourceState(null);
    }
}

function diagnosticCounts(report) {
    const counts = { errors: 0, warnings: 0, tips: 0 };
    for (const item of report?.diagnostics ?? []) {
        if (item?.severity === "error") counts.errors += 1;
        else if (item?.severity === "warning") counts.warnings += 1;
        else counts.tips += 1;
    }
    return counts;
}

export function sourceToolAttention(sources) {
    return Object.values(sources ?? {}).filter((source) => ["malformed", "future"].includes(source?.kind)).length;
}

export function alignmentGuidance(mode) {
    const normalized = String(mode ?? "").toLowerCase();
    if (normalized === "i2va") {
        return "Opening alignment · Match the opening frame to the connected start image.";
    }
    if (normalized === "fl2va") {
        return "Opening + ending alignment · Match both boundary frames to the connected first and last images.";
    }
    if (normalized === "l2va") {
        return "Ending alignment · Match the final frame to the connected end image.";
    }
    return null;
}

export function overviewModel(controller) {
    const shot = safeDocument(() => controller.shotDocument());
    const project = safeDocument(() => controller.projectDocument());
    const camera = safeDocument(() => controller.cinematographyDocument());
    const creative = safeDocument(() => controller.creativeDocument());
    const shots = Array.isArray(shot.value?.shots) ? shot.value.shots : [];
    const projectValue = project.kind === "v2" ? project.value : null;
    const projectGenerations = Array.isArray(projectValue?.generations) ? projectValue.generations : [];
    const shotGenerationIds = shots.map((item) => item?.generationId).filter(Boolean);
    const generationIds = [...new Set([
        ...projectGenerations.map((item) => item?.id).filter(Boolean),
        ...shotGenerationIds,
    ])];
    if (!generationIds.length && shots.length) generationIds.push("g1");
    const generations = generationIds.map((id, index) => {
        const projectGeneration = projectGenerations.find((item) => item?.id === id);
        return {
            id,
            order: projectGeneration?.order ?? index + 1,
            shots: shots.filter((item) => (item?.generationId ?? "g1") === id).length,
            bindings: projectGeneration?.bindings?.length ?? 0,
            carrySubjects: projectGeneration?.subjectStates?.filter((item) => item?.policy === "carry").length ?? 0,
            carryEnvironments: projectGeneration?.environmentStates?.filter((item) => item?.policy === "carry").length ?? 0,
        };
    }).sort((left, right) => left.order - right.order);
    const report = controller.diagnostics?.() ?? { diagnostics: [], stale: false };
    return {
        blank: shot.kind === "blank" && project.kind === "blank" && camera.kind === "blank",
        mode: controller.mode?.() ?? projectValue?.mode ?? "auto",
        shots: shots.length,
        subjects: projectValue?.subjects?.length ?? 0,
        environments: projectValue?.environments?.length ?? 0,
        assets: projectValue?.assets?.length ?? 0,
        generations,
        sources: { shot, project, camera, creative },
        preflight: localPreflight({ shotDocument: shot, projectDocument: project, basicPrompt: controller.basicPrompt?.() }),
        diagnostics: diagnosticCounts(report),
        stale: Boolean(report?.stale),
    };
}

function projectTransfer(controller, model) {
    const details = document.createElement("details");
    details.className = "minimax-h3-project-transfer";
    const summary = document.createElement("summary");
    summary.textContent = "Project v2 transfer";
    const body = document.createElement("div");
    body.className = "minimax-h3-project-transfer-body";
    const help = document.createElement("p");
    help.textContent = "Copy or paste one portable package containing the current v2 shot, media, creative and camera documents. This does not include physical media files.";
    const textarea = document.createElement("textarea");
    textarea.placeholder = "Paste a Prompt Studio v2 package here…";
    textarea.setAttribute("aria-label", "Prompt Studio v2 package");
    const feedback = document.createElement("p");
    feedback.className = "minimax-h3-source-feedback";
    const preview = document.createElement("ul");
    preview.className = "minimax-h3-project-transfer-preview";
    preview.hidden = true;
    const actions = document.createElement("div");
    actions.className = "minimax-h3-studio-toolbar";
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "minimax-h3-button minimax-h3-button-secondary";
    copy.textContent = "Copy v2 package";
    copy.addEventListener("click", async () => {
        const raw = JSON.stringify(createProjectBundle({
            shotPlan: model.sources.shot,
            mediaProject: model.sources.project,
            creativeTreatment: model.sources.creative,
            cinematography: model.sources.camera,
        }), null, 2);
        textarea.value = raw;
        try {
            if (!globalThis.navigator?.clipboard?.writeText) throw new Error("Clipboard unavailable");
            await globalThis.navigator.clipboard.writeText(raw);
            feedback.textContent = "Copied. Physical pictures, videos and audio remain separate.";
            feedback.dataset.valid = "true";
        } catch {
            textarea.focus(); textarea.select();
            feedback.textContent = "Package prepared. Copy it from the field above.";
            feedback.dataset.valid = "true";
        }
    });
    const apply = document.createElement("button");
    apply.type = "button";
    apply.className = "minimax-h3-button minimax-h3-button-primary";
    apply.textContent = "Preview import";
    const append = document.createElement("button");
    append.type = "button";
    append.className = "minimax-h3-button minimax-h3-button-secondary";
    append.textContent = "Append generations";
    append.disabled = true;
    let pending = null;
    let pendingAppend = null;
    apply.addEventListener("click", () => {
        if (pending) {
            const result = controller.replaceProjectBundleAtomically?.(pending.documents)
                ?? { ok: false, message: "Atomic project import is unavailable in this node." };
            if (!result.ok) {
                feedback.textContent = result.rolledBack === false ? `${result.message} Reopen the workflow before editing further.` : `${result.message} No project changes were kept.`;
                feedback.dataset.valid = "false";
                return;
            }
            feedback.textContent = "Imported all previewed documents as one transaction.";
            feedback.dataset.valid = "true";
            pending = null; preview.hidden = true; apply.textContent = "Preview import";
            pendingAppend = null; append.disabled = true;
            return;
        }
        const parsed = parseProjectBundle(textarea.value);
        if (!parsed.ok) {
            feedback.textContent = parsed.message;
            feedback.dataset.valid = "false";
            return;
        }
        pending = parsed;
        pendingAppend = appendProjectBundleGenerations(parsed.documents, {
            shotPlan: model.sources.shot, mediaProject: model.sources.project,
        });
        append.disabled = !pendingAppend.ok;
        preview.replaceChildren(...summarizeProjectBundle(parsed.documents, {
            shotPlan: model.sources.shot, mediaProject: model.sources.project,
            creativeTreatment: model.sources.creative, cinematography: model.sources.camera,
        }).map((item) => {
            const row = document.createElement("li");
            row.textContent = `${item.change}: ${item.label} · ${item.detail}`;
            return row;
        }));
        preview.hidden = false;
        apply.textContent = "Apply previewed package";
        feedback.textContent = pendingAppend.ok
            ? `Review every replacement above. You may replace the package or append only ${pendingAppend.detail}. Nothing has changed yet.`
            : `Review every replacement above, then apply. Append is unavailable: ${pendingAppend.message} Nothing has changed yet.`;
        feedback.dataset.valid = "true";
    });
    append.addEventListener("click", () => {
        if (!pendingAppend?.ok) return;
        const result = controller.replaceProjectBundleAtomically?.(pendingAppend.documents)
            ?? { ok: false, message: "Atomic project import is unavailable in this node." };
        if (!result.ok) { feedback.textContent = `${result.message} No appended data was kept.`; feedback.dataset.valid = "false"; return; }
        feedback.textContent = `Appended ${pendingAppend.detail} as one transaction.`; feedback.dataset.valid = "true";
        pending = null; pendingAppend = null; preview.hidden = true; apply.textContent = "Preview import"; append.disabled = true;
    });
    actions.append(copy, apply, append);
    textarea.addEventListener("input", () => {
        if (!pending) return;
        pending = null; pendingAppend = null; preview.hidden = true; apply.textContent = "Preview import"; append.disabled = true;
        feedback.textContent = "Package changed. Preview it again before applying.";
    });
    body.append(help, textarea, preview, actions, feedback);
    details.append(summary, body);
    return details;
}

function preflightSummary(model, navigate) {
    const section = document.createElement("section");
    section.className = "minimax-h3-preflight";
    section.dataset.status = model.preflight.status;
    const header = document.createElement("div");
    header.className = "minimax-h3-preflight-header";
    const text = document.createElement("div");
    const eyebrow = document.createElement("span");
    eyebrow.className = "minimax-h3-preflight-eyebrow";
    eyebrow.textContent = "Before generation · local checks";
    const heading = document.createElement("h3");
    const copy = document.createElement("p");
    if (!model.preflight.hasStructuredPlan) {
        heading.textContent = "Ready for a prompt-only run";
        copy.textContent = "Shots and media planning are optional. Add them only when you need precise continuity or references.";
    } else if (model.preflight.status === "ready") {
        heading.textContent = "Ready to generate";
        copy.textContent = "The current shot and media structure passes immediate checks.";
    } else {
        heading.textContent = model.preflight.errors ? "Needs attention before generating" : "Ready with a few notes";
        copy.textContent = `${model.preflight.errors} blocking · ${model.preflight.warnings} notes`;
    }
    text.append(eyebrow, heading, copy);
    const badge = document.createElement("span");
    badge.className = "minimax-h3-preflight-badge";
    badge.textContent = model.preflight.status === "ready" ? "Ready" : model.preflight.errors ? String(model.preflight.errors) : String(model.preflight.warnings);
    header.append(text, badge);
    section.appendChild(header);
    if (model.preflight.items.length) {
        const list = document.createElement("div");
        list.className = "minimax-h3-preflight-list";
        for (const item of model.preflight.items.slice(0, 3)) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "minimax-h3-preflight-item";
            button.dataset.severity = item.severity;
            const message = document.createElement("span");
            message.textContent = item.message;
            const action = document.createElement("strong");
            action.textContent = `Open ${item.section === "media" ? "Media" : item.section === "camera" ? "Camera" : item.section === "staging" ? "Staging" : "Shots"}`;
            button.append(message, action);
            button.addEventListener("click", () => navigate(item.section));
            list.appendChild(button);
        }
        if (model.preflight.items.length > 3) {
            const more = document.createElement("p");
            more.className = "minimax-h3-muted";
            more.textContent = `+ ${model.preflight.items.length - 3} more local checks`;
            list.appendChild(more);
        }
        section.appendChild(list);
    }
    return section;
}

function overviewAction(title, description, actionLabel, onAction) {
    const card = document.createElement("article");
    card.className = "minimax-h3-overview-action";
    const heading = document.createElement("h3");
    heading.textContent = title;
    const copy = document.createElement("p");
    copy.textContent = description;
    const action = document.createElement("button");
    action.type = "button";
    action.className = "minimax-h3-button minimax-h3-button-secondary";
    action.textContent = actionLabel;
    action.addEventListener("click", onAction);
    card.append(heading, copy, action);
    return card;
}

function starterExamples(controller) {
    const section = document.createElement("section");
    section.className = "minimax-h3-starters";
    const heading = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = "Or start with a small example";
    const copy = document.createElement("p");
    copy.textContent = "Examples add editable v2 structure only. They contain no external images, brands or hidden prompt text.";
    heading.append(title, copy);
    const grid = document.createElement("div");
    grid.className = "minimax-h3-starter-grid";
    for (const example of STARTER_EXAMPLES) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "minimax-h3-starter-card";
        const name = document.createElement("strong");
        name.textContent = example.title;
        const description = document.createElement("span");
        description.textContent = example.description;
        const action = document.createElement("em");
        action.textContent = "Use example";
        button.append(name, description, action);
        button.addEventListener("click", () => applyStarterExample(controller, example));
        grid.appendChild(button);
    }
    section.append(heading, grid);
    return section;
}

export function renderSourceTools(controller, model = overviewModel(controller)) {
    const section = document.createElement("details");
    section.className = "minimax-h3-source-tools";
    const summary = document.createElement("summary");
    const title = document.createElement("span");
    title.textContent = "Import & source tools";
    summary.appendChild(title);
    const attention = sourceToolAttention(model.sources);
    if (attention) {
        const state = document.createElement("span");
        state.className = "minimax-h3-source-tools-attention";
        state.textContent = `${attention} need${attention === 1 ? "s" : ""} attention`;
        summary.appendChild(state);
    }
    const body = document.createElement("div");
    body.className = "minimax-h3-source-tools-body";
    const help = document.createElement("p");
    help.className = "minimax-h3-field-hint";
    help.textContent = "Inspect structured inputs, repair invalid JSON or copy a read-only source.";
    const pills = document.createElement("div");
    pills.className = "minimax-h3-source-pills";
    pills.append(
        createSourcePill("Shot plan", model.sources.shot),
        createSourcePill("Media project", model.sources.project),
        createSourcePill("Camera", model.sources.camera),
    );
    body.append(help, pills, projectTransfer(controller, model));
    const exceptional = document.createElement("div");
    exceptional.className = "minimax-h3-source-cards";
    if (model.sources.project.kind === "v2") {
        exceptional.appendChild(createSourceStateCard({
            name: "Media project v2",
            documentState: model.sources.project,
            acceptedVersions: [2],
        }));
    }
    if (["malformed", "future"].includes(model.sources.shot.kind)) {
        exceptional.appendChild(createSourceStateCard({
            name: "Shot plan",
            documentState: model.sources.shot,
            acceptedVersions: [1, 2],
            onApplyRaw: controller.replaceShotRaw ? (raw) => controller.replaceShotRaw(raw) : null,
        }));
    }
    if (["v1", "malformed", "future"].includes(model.sources.project.kind)) {
        exceptional.appendChild(createSourceStateCard({
            name: "Media project",
            documentState: model.sources.project,
            acceptedVersions: [2],
            legacyDescription: "This legacy manifest is preserved unchanged and is read-only in Prompt Studio.",
            onApplyRaw: controller.replaceProjectRaw ? (raw) => controller.replaceProjectRaw(raw) : null,
        }));
    }
    if (["malformed", "future"].includes(model.sources.camera.kind)) {
        exceptional.appendChild(createSourceStateCard({
            name: "Camera",
            documentState: model.sources.camera,
            acceptedVersions: [1],
            onApplyRaw: controller.replaceStructuredRaw
                ? (raw) => controller.replaceStructuredRaw("cinematography_json", raw)
                : null,
        }));
    }
    if (exceptional.childElementCount) body.appendChild(exceptional);
    section.append(summary, body);
    return section;
}

function healthSummary(model, onReview) {
    const section = document.createElement("section");
    section.className = "minimax-h3-overview-health";
    const text = document.createElement("div");
    const heading = document.createElement("h3");
    heading.textContent = "Project health";
    const summary = document.createElement("p");
    if (model.stale) summary.textContent = "Review is based on an earlier run. Run the node again after editing.";
    else if (model.diagnostics.errors || model.diagnostics.warnings || model.diagnostics.tips) {
        summary.textContent = `${model.diagnostics.errors} errors · ${model.diagnostics.warnings} warnings · ${model.diagnostics.tips} tips`;
    } else summary.textContent = "Run the node to validate continuity and receive contextual guidance.";
    text.append(heading, summary);
    const review = document.createElement("button");
    review.type = "button";
    review.className = "minimax-h3-button minimax-h3-button-primary";
    review.textContent = "Open Review";
    review.addEventListener("click", onReview);
    section.append(text, review);
    return section;
}

function pipelineSection(model, navigate) {
    const section = document.createElement("section");
    section.className = "minimax-h3-overview-section";
    const heading = document.createElement("h3");
    heading.textContent = "Pipeline";
    const pipeline = document.createElement("div");
    pipeline.className = "minimax-h3-pipeline";
    for (const generation of model.generations) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "minimax-h3-generation-card";
        const title = document.createElement("strong");
        title.textContent = `Generation ${generation.order}`;
        const details = document.createElement("span");
        details.textContent = `${generation.shots} shots · ${generation.bindings} media bindings`;
        button.append(title, details);
        button.addEventListener("click", () => navigate("shots"));
        pipeline.appendChild(button);
    }
    if (!model.generations.length) {
        const hint = document.createElement("p");
        hint.className = "minimax-h3-muted";
        hint.textContent = "Your generations and shots will appear here as the plan grows.";
        pipeline.appendChild(hint);
    }
    section.append(heading, pipeline);
    return section;
}

function librarySection(model, navigate) {
    const section = document.createElement("section");
    section.className = "minimax-h3-overview-section";
    const heading = document.createElement("h3");
    heading.textContent = "Library";
    const grid = document.createElement("div");
    grid.className = "minimax-h3-library-grid";
    for (const [id, count, label] of [
        ["subjects", model.subjects, "Subjects"],
        ["environments", model.environments, "Environments"],
        ["media", model.assets, "Media assets"],
    ]) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "minimax-h3-library-card";
        const value = document.createElement("strong");
        value.textContent = String(count);
        const title = document.createElement("span");
        title.textContent = label;
        button.append(value, title);
        button.addEventListener("click", () => navigate(id));
        grid.appendChild(button);
    }
    section.append(heading, grid);
    return section;
}

function continuitySection(model) {
    const carrying = model.generations.slice(1).filter((item) => item.carrySubjects || item.carryEnvironments);
    if (!carrying.length) return null;
    const section = document.createElement("section");
    section.className = "minimax-h3-overview-section";
    const heading = document.createElement("h3");
    heading.textContent = "Continuity";
    const list = document.createElement("ul");
    for (const generation of carrying) {
        const item = document.createElement("li");
        item.textContent = `Generation ${generation.order} carries ${generation.carrySubjects} subject and ${generation.carryEnvironments} environment states forward.`;
        list.appendChild(item);
    }
    section.append(heading, list);
    return section;
}

export function renderOverview(container, controller, { navigate = () => {}, openReview = () => {} } = {}) {
    container.replaceChildren();
    container.classList.add("minimax-h3-overview");
    const model = overviewModel(controller);
    const intro = document.createElement("div");
    intro.className = "minimax-h3-overview-intro";
    const title = document.createElement("h2");
    title.textContent = model.blank ? "Plan your video" : "Your production at a glance";
    const copy = document.createElement("p");
    copy.textContent = "Your prompt remains the narrative source. Prompt Studio adds reusable structure, continuity and camera intent.";
    intro.append(title, copy);
    container.appendChild(intro);

    const alignment = alignmentGuidance(model.mode);
    if (alignment) {
        const guidance = document.createElement("div");
        guidance.className = "minimax-h3-studio-status";
        guidance.dataset.kind = "guidance";
        guidance.textContent = alignment;
        container.appendChild(guidance);
    }

    if (model.blank) {
        const actions = document.createElement("div");
        actions.className = "minimax-h3-overview-actions";
        actions.append(
            overviewAction("Plan shots", "Divide the scene into purposeful shots with their own action and camera.", "Open Shots", () => navigate("shots")),
            overviewAction("Add a subject", "Keep identity and appearance states consistent across the sequence.", "Open Subjects", () => navigate("subjects")),
            overviewAction("Register media", "Connect pictures, videos and audio to physical generation slots.", "Open Media", () => navigate("media")),
        );
        container.appendChild(actions);
        container.appendChild(starterExamples(controller));
        container.appendChild(createEmptyState({
            title: "Prompt Coach is ready when you are",
            description: "Run the node after planning to check continuity, camera authority and prompt clarity.",
            actionLabel: "Open Review",
            onAction: openReview,
        }));
    } else {
        container.appendChild(pipelineSection(model, navigate));
        const continuity = continuitySection(model);
        if (continuity) container.appendChild(continuity);
        container.append(librarySection(model, navigate), preflightSummary(model, navigate), healthSummary(model, openReview));
    }
    container.appendChild(renderSourceTools(controller, model));
}
