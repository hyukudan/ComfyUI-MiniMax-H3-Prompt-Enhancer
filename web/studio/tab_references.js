import { assetUsage, effectivePictureBindingRole, generationMediaModel, MEDIA_LIMITS, nextAvailableSlot } from "./media_model.js";
import { commitProject, labeledInput, labeledSelect, projectForController, readOnlyProjectMessage, uniqueId } from "./project_editor.js";
import { captureOpenDisclosures, restoreOpenDisclosures } from "./domain_components.js";
import {
    bindingPlanDiagnostics, createPlanningContext, createPurposeBinding, mediaPurpose,
    MEDIA_BINDING_PURPOSES, MEDIA_RECIPES,
} from "./media_workflows.js";

const CAMERA_TRANSFER_ASPECTS = ["motion", "framing", "angle", "viewpoint", "composition", "focus", "distance", "stability", "lens", "parallax"];
const PROJECT_MODES = [["auto", "Auto"], ["t2va", "T2VA"], ["i2va", "I2VA"], ["fl2va", "FL2VA"], ["l2va", "L2VA"], ["ref2va", "Ref2VA"], ["chained_multishot", "Chained"]];
const PICTURE_BINDING_ROLES = [["reference", "General reference"], ["first_frame", "First frame"], ["last_frame", "Last frame"]];

export function physicalLabel(asset, binding) {
    const prefix = asset?.type === "video" ? "Video" : asset?.type === "audio" ? "Audio" : "Picture";
    return `<${prefix} ${binding?.slotIndex ?? "?"}>`;
}

export function bindingRoleLabel(binding = {}) {
    return binding.role === "first_frame" ? "First frame" : binding.role === "last_frame" ? "Last frame" : "Reference";
}

function suggestedPictureRole(project, generation) {
    if (project.mode === "i2va") return "first_frame";
    if (project.mode === "l2va") return "last_frame";
    if (project.mode !== "fl2va") return "reference";
    return (generation.bindings ?? []).some((binding) => binding.role === "first_frame") ? "last_frame" : "first_frame";
}

function mediaVisual(asset, compact = false) {
    const visual = document.createElement("span");
    visual.className = `minimax-h3-media-visual${compact ? " is-compact" : ""}`;
    visual.dataset.type = asset?.type ?? "picture";
    visual.setAttribute("aria-hidden", "true");
    const glyph = document.createElement("strong");
    glyph.textContent = asset?.type === "video" ? "▶" : asset?.type === "audio" ? "≋" : "▧";
    const caption = document.createElement("small");
    caption.textContent = compact ? String(asset?.name ?? "").slice(0, 2).toUpperCase() : "Physical preview stays on generator";
    visual.append(glyph, caption);
    return visual;
}

export function bindingSuggestion(project, asset, preferredGenerationId = "") {
    if (!project || !asset) return null;
    const candidates = [...(project.generations ?? [])].sort((left, right) => {
        if (left.id === preferredGenerationId) return -1;
        if (right.id === preferredGenerationId) return 1;
        return Number(left.order ?? 0) - Number(right.order ?? 0);
    });
    for (const generation of candidates) {
        if ((generation.bindings ?? []).some((binding) => binding.assetId === asset.id)) continue;
        const slotIndex = nextAvailableSlot(project, generation, asset.type);
        if (slotIndex === null) continue;
        const suggestion = { generation, binding: { assetId: asset.id, slotIndex } };
        if (asset.type === "picture") {
            const role = suggestedPictureRole(project, generation);
            if (role !== "reference") suggestion.binding.role = role;
        }
        if (asset.type === "video" && ["paired", "alone"].includes(asset.audioMode)) {
            const soundtrackSlotIndex = nextAvailableSlot(project, generation, "audio");
            if (soundtrackSlotIndex === null) continue;
            suggestion.binding.soundtrackSlotIndex = soundtrackSlotIndex;
        }
        return suggestion;
    }
    return null;
}

function actionButton(label, action, className = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    if (className) button.className = className;
    button.addEventListener("click", action);
    return button;
}

function section(title, summary = "") {
    const details = document.createElement("details");
    details.className = "minimax-h3-inspector-block";
    details.open = true;
    details.dataset.disclosureKey = title;
    const heading = document.createElement("summary");
    heading.textContent = summary ? `${title} · ${summary}` : title;
    const body = document.createElement("div");
    body.className = "minimax-h3-studio-editor";
    details.append(heading, body);
    return { details, body };
}

function checkbox(label, checked, onChange, disabled = false, title = "") {
    const field = document.createElement("label");
    field.className = "minimax-h3-check-row";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = checked;
    input.disabled = disabled;
    if (title) field.title = title;
    input.addEventListener("change", () => onChange(input.checked));
    const text = document.createElement("span");
    text.textContent = label;
    field.append(input, text);
    return field;
}

function helpText(text, className = "minimax-h3-panel-help") {
    const help = document.createElement("p");
    help.className = className;
    help.textContent = text;
    return help;
}

function renderMediaOnboarding() {
    const guide = document.createElement("section");
    guide.className = "minimax-h3-media-onboarding";
    guide.setAttribute("aria-label", "How media references work");

    const intro = document.createElement("div");
    intro.className = "minimax-h3-media-onboarding-intro";
    const title = document.createElement("strong");
    title.textContent = "Reference setup · 2 steps";
    const note = document.createElement("span");
    note.textContent = "Prompt Studio stores the logical contract; actual files stay connected to the generator node.";
    intro.append(title, note);

    const steps = document.createElement("ol");
    steps.className = "minimax-h3-media-steps";
    const content = [
        ["Describe a reference", "Add a picture, video or audio reference and record what it represents."],
        ["Connect and assign its file", "Load the actual file on the generator node, then map this reference to the matching Picture, Video or Audio slot below."],
    ];
    for (const [index, [heading, description]] of content.entries()) {
        const item = document.createElement("li");
        const number = document.createElement("span");
        number.className = "minimax-h3-media-step-number";
        number.setAttribute("aria-hidden", "true");
        number.textContent = String(index + 1);
        const copy = document.createElement("div");
        const strong = document.createElement("strong");
        strong.textContent = heading;
        const span = document.createElement("span");
        span.textContent = description;
        copy.append(strong, span);
        item.append(number, copy);
        steps.appendChild(item);
    }
    guide.append(intro, steps);
    return guide;
}

function commitAndRender(container, controller) {
    commitProject(controller);
    renderReferencesTab(container, controller);
}

function workflowSelection(project, controller, purposeId = "continuity") {
    const generation = selectedGeneration(project, controller);
    const shots = controller.shotDocument()?.value?.shots ?? [];
    const shot = shots.find((item) => item.id === controller.shotUiState?.selectedId && item.generationId === generation.id)
        ?? shots.find((item) => item.generationId === generation.id) ?? null;
    const purpose = mediaPurpose(purposeId);
    return {
        purposeId,
        generationId: generation.id,
        shotId: shot?.id ?? "",
        relationId: purpose?.relation === "subject" ? project.subjects[0]?.id ?? ""
            : purpose?.relation === "environment" ? project.environments[0]?.id ?? "" : "",
        name: purpose?.label ?? "Reference",
    };
}

function renderPlanningContextExport(controller) {
    const details = document.createElement("details");
    details.className = "minimax-h3-inspector-block minimax-h3-planning-context";
    const summary = document.createElement("summary");
    summary.textContent = "Export LLM planning context";
    const body = document.createElement("div");
    body.className = "minimax-h3-studio-editor";
    body.appendChild(helpText("Creates a versioned, read-only context package for discussing this plan with an LLM. Prompt Studio never imports or applies its response automatically."));
    const output = document.createElement("textarea");
    output.readOnly = true;
    output.setAttribute("aria-label", "LLM planning context JSON");
    const feedback = helpText("No physical files or hidden prompts are included.", "minimax-h3-source-feedback");
    const prepare = () => {
        output.value = JSON.stringify(createPlanningContext({
            projectDocument: controller.projectDocument(), shotDocument: controller.shotDocument(),
        }), null, 2);
    };
    details.addEventListener("toggle", () => { if (details.open) prepare(); });
    const copy = actionButton("Copy context JSON", async () => {
        prepare();
        try {
            if (!globalThis.navigator?.clipboard?.writeText) throw new Error("Clipboard unavailable");
            await globalThis.navigator.clipboard.writeText(output.value);
            feedback.textContent = "Copied. Review any LLM suggestions manually; this file is not importable.";
            feedback.dataset.valid = "true";
        } catch {
            output.focus(); output.select();
            feedback.textContent = "Context prepared. Copy it from the field above.";
        }
    }, "minimax-h3-button minimax-h3-button-secondary");
    body.append(output, copy, feedback);
    details.append(summary, body);
    return details;
}

function renderPurposeAssistant(container, project, controller) {
    const state = controller.projectUiState.mediaAssistant;
    if (!state) return null;
    const panel = document.createElement("section");
    panel.className = "minimax-h3-media-assistant minimax-h3-purpose-assistant";
    const heading = document.createElement("div");
    heading.className = "minimax-h3-media-assistant-heading";
    const title = document.createElement("strong"); title.textContent = "Plan one reference by purpose";
    const cancel = actionButton("Cancel", () => { delete controller.projectUiState.mediaAssistant; renderReferencesTab(container, controller); });
    heading.append(title, cancel); panel.appendChild(heading);
    const set = (key, value) => { state[key] = value; renderReferencesTab(container, controller); };
    const activePurpose = mediaPurpose(state.purposeId);
    const purposes = [
        ...(activePurpose && !MEDIA_BINDING_PURPOSES.some((item) => item.id === activePurpose.id) ? [[activePurpose.id, activePurpose.label]] : []),
        ...MEDIA_BINDING_PURPOSES.map((item) => [item.id, item.label]),
    ];
    panel.appendChild(labeledSelect("Purpose", state.purposeId, purposes, (value) => {
        controller.projectUiState.mediaAssistant = workflowSelection(project, controller, value);
        renderReferencesTab(container, controller);
    }));
    const generations = project.generations.map((item) => [item.id, `Generation ${item.order ?? item.id}`]);
    panel.appendChild(labeledSelect("Generation", state.generationId, generations, (value) => {
        state.generationId = value;
        state.shotId = (controller.shotDocument()?.value?.shots ?? []).find((item) => item.generationId === value)?.id ?? "";
        renderReferencesTab(container, controller);
    }));
    const shots = (controller.shotDocument()?.value?.shots ?? []).filter((item) => item.generationId === state.generationId);
    panel.appendChild(labeledSelect("Shot", state.shotId, shots.map((item) => [item.id, item.action || item.id]), (value) => set("shotId", value)));
    const purpose = mediaPurpose(state.purposeId);
    if (purpose?.relation === "subject") panel.appendChild(labeledSelect("Subject", state.relationId, project.subjects.map((item) => [item.id, item.name]), (value) => set("relationId", value)));
    if (purpose?.relation === "environment") panel.appendChild(labeledSelect("Environment", state.relationId, project.environments.map((item) => [item.id, item.name]), (value) => set("relationId", value)));
    panel.appendChild(labeledInput("Reference name", state.name, (value) => { state.name = value; }));
    if (purpose) panel.appendChild(helpText(`${purpose.help} The physical ${purpose.type} still connects on the generator node.`));
    const planInput = { project, shotPlan: controller.shotDocument()?.value, ...state };
    const issues = bindingPlanDiagnostics(planInput);
    const status = helpText(issues.length ? issues.join(" ") : "Ready: this will create the logical reference, its relationship, shot use and generation file-slot binding together.", "minimax-h3-source-feedback");
    status.dataset.valid = String(!issues.length);
    const apply = actionButton("Create complete binding", () => {
        const result = createPurposeBinding(planInput);
        if (!result.ok) return;
        const committed = controller.replaceProjectBundleAtomically?.({ mediaProject: result.project, shotPlan: result.shotPlan });
        if (!committed?.ok) { status.textContent = committed?.message ?? "Atomic Media + Shot update is unavailable."; status.dataset.valid = "false"; return; }
        controller.projectUiState.selectedAssetId = result.assetId;
        controller.projectUiState.selectedGenerationId = state.generationId;
        if (controller.shotUiState) controller.shotUiState.selectedId = state.shotId;
        delete controller.projectUiState.mediaAssistant;
        renderReferencesTab(container, controller);
    }, "minimax-h3-button minimax-h3-button-primary");
    apply.disabled = issues.length > 0 || typeof controller.replaceProjectBundleAtomically !== "function";
    panel.append(status, apply);
    return panel;
}

function renderMediaWorkflowTools(container, project, controller) {
    const section = document.createElement("section");
    section.className = "minimax-h3-media-workflows";
    const header = document.createElement("div"); header.className = "minimax-h3-studio-toolbar";
    const title = document.createElement("div"); title.innerHTML = "<strong>Plan by outcome</strong><span>Start with what you want to preserve or transfer</span>";
    const start = actionButton("+ Plan reference", () => {
        controller.projectUiState.mediaAssistant = workflowSelection(project, controller);
        renderReferencesTab(container, controller);
    }, "minimax-h3-button minimax-h3-button-primary");
    header.append(title, start); section.appendChild(header);
    const recipes = document.createElement("div"); recipes.className = "minimax-h3-starter-grid minimax-h3-media-recipes";
    for (const recipe of MEDIA_RECIPES) {
        const selection = workflowSelection(project, controller, recipe.purpose);
        const issues = bindingPlanDiagnostics({ project, shotPlan: controller.shotDocument()?.value, ...selection });
        const card = actionButton("", () => {
            const purpose = recipe.purpose;
            controller.projectUiState.mediaAssistant = { ...selection, purposeId: purpose, name: recipe.label };
            renderReferencesTab(container, controller);
        }, "minimax-h3-starter-card");
        const name = document.createElement("strong"); name.textContent = recipe.label;
        const description = document.createElement("span"); description.textContent = recipe.description;
        const state = document.createElement("em"); state.textContent = issues.length ? `Needs: ${issues[0]}` : "Set up recipe";
        card.append(name, description, state); recipes.appendChild(card);
    }
    const assistant = renderPurposeAssistant(container, project, controller);
    if (assistant) section.appendChild(assistant);
    section.append(recipes, renderPlanningContextExport(controller));
    return section;
}

function selectedAsset(project, controller) {
    const selected = project.assets.find((asset) => asset.id === controller.projectUiState.selectedAssetId) ?? project.assets[0] ?? null;
    controller.projectUiState.selectedAssetId = selected?.id ?? null;
    return selected;
}

function selectedGeneration(project, controller) {
    const selected = project.generations.find((generation) => generation.id === controller.projectUiState.selectedGenerationId) ?? project.generations[0];
    controller.projectUiState.selectedGenerationId = selected.id;
    return selected;
}

function renderAssetMaster(container, project, controller) {
    const panel = document.createElement("section");
    panel.className = "minimax-h3-master-pane";
    const header = document.createElement("div");
    header.className = "minimax-h3-studio-toolbar";
    const title = document.createElement("h3");
    title.textContent = `Reference library · ${project.assets.length}`;
    const add = actionButton("+ Add reference", () => {
        const id = uniqueId(project.assets, "asset.");
        project.assets.push({ id, type: "picture", name: `Picture reference ${project.assets.length + 1}`, available: true });
        controller.projectUiState.selectedAssetId = id;
        commitAndRender(container, controller);
    });
    add.disabled = project.assets.length >= 128;
    header.append(title, add);
    const list = document.createElement("div");
    list.className = "minimax-h3-master-list";
    list.setAttribute("role", "listbox");
    const selectedId = controller.projectUiState.selectedAssetId ?? project.assets[0]?.id;
    for (const asset of project.assets) {
        const row = actionButton("", () => {
            controller.projectUiState.selectedAssetId = asset.id;
            renderReferencesTab(container, controller);
        }, "minimax-h3-master-row");
        row.setAttribute("role", "option");
        row.setAttribute("aria-selected", String(asset.id === selectedId));
        const icon = asset.type === "video" ? "Video" : asset.type === "audio" ? "Audio" : "Picture";
        const meta = [icon, asset.available === false ? "unavailable" : "available"];
        if (asset.type === "video" && asset.cameraTransfer?.enabled) meta.push(`camera: ${asset.cameraTransfer.aspects.join(", ")}`);
        const copy = document.createElement("span");
        copy.className = "minimax-h3-media-row-copy";
        const name = document.createElement("strong"); name.textContent = asset.name;
        const detail = document.createElement("small"); detail.textContent = meta.join(" · ");
        copy.append(name, detail);
        row.append(mediaVisual(asset, true), copy);
        list.appendChild(row);
    }
    if (!project.assets.length) {
        const empty = document.createElement("div");
        empty.className = "minimax-h3-empty-state";
        empty.textContent = "No references yet. Add one here to describe its role; connect the actual file on the generator node.";
        list.appendChild(empty);
    }
    panel.append(header, list);
    return panel;
}

function renderTranscript(body, asset, container, controller) {
    const block = section("Transcript", `${asset.transcript?.length ?? 0} entries`);
    for (const [index, entry] of (asset.transcript ?? []).entries()) {
        const row = document.createElement("div");
        row.className = "minimax-h3-inline-editor";
        const normalized = typeof entry === "string" ? { text: entry } : entry;
        row.append(
            labeledInput("Language", normalized.language ?? "", (value) => {
                asset.transcript[index] = { ...normalized, text: normalized.text, ...(value ? { language: value } : {}) };
                commitProject(controller);
            }),
            labeledInput("Text", normalized.text ?? "", (value) => {
                asset.transcript[index] = typeof entry === "string" && !normalized.language ? value : { ...normalized, text: value };
                commitProject(controller);
            }, { multiline: true }),
        );
        row.appendChild(actionButton("Remove", () => {
            asset.transcript.splice(index, 1);
            if (!asset.transcript.length) delete asset.transcript;
            commitAndRender(container, controller);
        }));
        block.body.appendChild(row);
    }
    block.body.appendChild(actionButton("+ Transcript entry", () => {
        (asset.transcript ??= []).push({ text: "Transcript text" });
        commitAndRender(container, controller);
    }));
    body.appendChild(block.details);
}

function renderAssetInspector(container, project, asset, controller) {
    const inspector = document.createElement("section");
    inspector.className = "minimax-h3-inspector-pane";
    if (!asset) {
        inspector.classList.add("minimax-h3-empty-state");
        inspector.textContent = "Add a reference to define its logical media contract. The file itself remains on the generator node.";
        return inspector;
    }
    const identity = section("Reference details", `${asset.type} · ${asset.id}`);
    const hero = document.createElement("div");
    hero.className = "minimax-h3-media-preview-card";
    const heroCopy = document.createElement("div");
    const heroTitle = document.createElement("strong"); heroTitle.textContent = asset.name;
    const heroNote = document.createElement("span"); heroNote.textContent = "Logical reference · connect the physical file on the matching generator input.";
    heroCopy.append(heroTitle, heroNote); hero.append(mediaVisual(asset), heroCopy);
    identity.body.appendChild(hero);
    identity.body.append(
        labeledInput("Name", asset.name, (value) => { asset.name = value || asset.id; commitProject(controller); }),
        labeledSelect("Type", asset.type, [["picture", "Picture"], ["video", "Video"], ["audio", "Audio"]], (value) => {
            asset.type = value;
            if (value !== "video") { delete asset.audioMode; delete asset.cameraTransfer; }
            if (!["video", "audio"].includes(value)) delete asset.durationSeconds;
            commitAndRender(container, controller);
        }),
        checkbox("Available to the project", asset.available !== false, (value) => { asset.available = value; commitProject(controller); }),
        labeledInput("Description", asset.description ?? "", (value) => { if (value) asset.description = value; else delete asset.description; commitProject(controller); }, { multiline: true }),
    );
    if (["video", "audio"].includes(asset.type)) {
        identity.body.appendChild(labeledInput("Duration (seconds)", asset.durationSeconds ?? "", (value) => {
            const duration = Number(value);
            if (duration > 0) asset.durationSeconds = Math.min(15, duration); else delete asset.durationSeconds;
            commitProject(controller);
        }, { type: "number" }));
    }
    if (asset.type === "video") {
        identity.body.appendChild(labeledSelect("Audio track", asset.audioMode ?? "off", [["off", "Ignore"], ["paired", "Paired with video"], ["alone", "Use alone"]], (value) => {
            asset.audioMode = value;
            commitAndRender(container, controller);
        }));
    }
    inspector.appendChild(identity.details);
    inspector.appendChild(renderFirstAssignment(container, project, asset, controller));
    {
        const structuredAnalysis = asset.analysis !== undefined && typeof asset.analysis !== "string";
        const analysis = section("Analysis", structuredAnalysis ? "structured source preserved" : "optional observations");
        analysis.body.appendChild(helpText("Record only observations that should guide prompting. This does not upload or inspect the physical file."));
        if (!structuredAnalysis) analysis.body.appendChild(labeledInput("Observed analysis", asset.analysis ?? "", (value) => { if (value) asset.analysis = value; else delete asset.analysis; commitProject(controller); }, { multiline: true }));
        else {
            const note = document.createElement("p");
            note.className = "minimax-h3-studio-status";
            note.textContent = "This asset contains structured analysis. It is preserved by the Studio and remains visible in source recovery tools.";
            analysis.body.appendChild(note);
        }
        inspector.appendChild(analysis.details);
    }
    if (["video", "audio"].includes(asset.type)) renderTranscript(inspector, asset, container, controller);
    if (asset.type === "video") {
        const transfer = section("Camera transfer", asset.cameraTransfer?.enabled ? asset.cameraTransfer.aspects.join(", ") : "off");
        transfer.body.appendChild(checkbox("This video is an explicit camera reference", Boolean(asset.cameraTransfer?.enabled), (enabled) => {
            if (enabled) asset.cameraTransfer = { enabled: true, role: "camera_reference", aspects: ["motion"] };
            else delete asset.cameraTransfer;
            commitAndRender(container, controller);
        }));
        if (asset.cameraTransfer?.enabled) {
            const aspects = document.createElement("div");
            aspects.className = "minimax-h3-chip-picker";
            for (const aspect of CAMERA_TRANSFER_ASPECTS) {
                const active = asset.cameraTransfer.aspects.includes(aspect);
                const chip = checkbox(aspect, active, (checked) => {
                    const selected = new Set(asset.cameraTransfer.aspects);
                    if (checked) selected.add(aspect); else if (selected.size > 1) selected.delete(aspect);
                    asset.cameraTransfer.aspects = [...selected];
                    commitAndRender(container, controller);
                }, active && asset.cameraTransfer.aspects.length === 1, "A camera transfer needs at least one aspect.");
                aspects.appendChild(chip);
            }
            transfer.body.appendChild(aspects);
        }
        inspector.appendChild(transfer.details);
    }
    const uses = assetUsage(project, asset.id);
    const shotUses = controller.shotDocument()?.value?.shots?.flatMap((shot) => (shot.referenceUses ?? []).filter((use) => use.assetId === asset.id).map(() => `reference in shot ${shot.id}`)) ?? [];
    uses.push(...shotUses);
    const footer = document.createElement("div");
    footer.className = "minimax-h3-inspector-actions";
    const remove = actionButton("Delete asset", () => {
        project.assets.splice(project.assets.indexOf(asset), 1);
        controller.projectUiState.selectedAssetId = project.assets[0]?.id ?? null;
        commitAndRender(container, controller);
    });
    remove.disabled = uses.length > 0;
    footer.appendChild(remove);
    if (uses.length) {
        const reason = document.createElement("span");
        reason.textContent = `Used by ${uses.join(", ")}`;
        footer.appendChild(reason);
    }
    inspector.appendChild(footer);
    return inspector;
}

function renderFirstAssignment(container, project, asset, controller) {
    const card = document.createElement("section");
    card.className = "minimax-h3-media-assistant";
    const heading = document.createElement("div");
    heading.className = "minimax-h3-media-assistant-heading";
    const title = document.createElement("strong");
    title.textContent = "Use this reference in a generation";
    const badge = document.createElement("span");
    const assignments = (project.generations ?? []).flatMap((generation) => (generation.bindings ?? [])
        .filter((binding) => binding.assetId === asset.id)
        .map((binding) => ({ generation, binding })));
    badge.textContent = assignments.length ? `${assignments.length} assigned` : "Next step";
    heading.append(title, badge);
    card.appendChild(heading);

    if (assignments.length) {
        const list = document.createElement("div");
        list.className = "minimax-h3-media-assistant-assignments";
        for (const { generation, binding } of assignments) {
            const item = document.createElement("span");
            item.textContent = `Generation ${generation.order ?? generation.id} · ${physicalLabel(asset, binding)}`;
            list.appendChild(item);
        }
        card.appendChild(list);
    }

    const suggestion = bindingSuggestion(project, asset, controller.projectUiState.selectedGenerationId);
    if (!suggestion) {
        const note = helpText(assignments.length
            ? "This reference is assigned everywhere it can be used. Manage or remove assignments in the generation section below."
            : "No compatible file slot is available. Free a Picture, Video or Audio slot in a generation first.", "minimax-h3-media-empty-note");
        card.appendChild(note);
        return card;
    }

    const availableSuggestions = (project.generations ?? []).map((generation) => bindingSuggestion({ ...project, generations: [generation] }, asset, generation.id)).filter(Boolean);
    const generationChoices = availableSuggestions.map(({ generation }) => [generation.id, `Generation ${generation.order ?? generation.id}`]);
    const selectedId = generationChoices.some(([id]) => id === suggestion.generation.id)
        ? suggestion.generation.id : generationChoices[0]?.[0];
    if (generationChoices.length > 1) {
        card.appendChild(labeledSelect("Target generation", selectedId, generationChoices, (value) => {
            controller.projectUiState.selectedGenerationId = value;
            renderReferencesTab(container, controller);
        }));
    }
    const chosen = availableSuggestions.find(({ generation }) => generation.id === selectedId) ?? suggestion;
    const explanation = document.createElement("p");
    explanation.textContent = `Prompt Studio will refer to this file as ${physicalLabel(asset, chosen.binding)}. Connect the actual file to the matching generator input.`;
    const assign = actionButton(`Assign to Generation ${chosen.generation.order ?? chosen.generation.id} · ${physicalLabel(asset, chosen.binding)}`, () => {
        (chosen.generation.bindings ??= []).push({ ...chosen.binding });
        controller.projectUiState.selectedGenerationId = chosen.generation.id;
        commitAndRender(container, controller);
    }, "minimax-h3-button minimax-h3-button-primary");
    card.append(explanation, assign);
    return card;
}

function allResources(project) {
    return [
        ...(project.assets ?? []).map((item) => ({ kind: "asset", id: item.id, label: item.name })),
        ...(project.subjects ?? []).map((item) => ({ kind: "subject", id: item.id, label: item.name })),
        ...(project.environments ?? []).map((item) => ({ kind: "environment", id: item.id, label: item.name })),
    ];
}

function renderActivation(container, project, generation, controller) {
    const shotDocument = controller.shotDocument();
    const model = generationMediaModel(project, generation, shotDocument?.kind === "v2" ? shotDocument.value : null);
    const block = section("Included media", `${model.activeAssetIds.size} active assets`);
    block.body.appendChild(helpText("Choose which logical references this generation may use. File connections are assigned separately below."));
    const activationChoices = [["auto", "Automatic dependency closure"]];
    if (allResources(project).length || generation.activation?.mode === "explicit") activationChoices.push(["explicit", "Explicit roots"]);
    block.body.appendChild(labeledSelect("Activation", generation.activation?.mode ?? "auto", activationChoices, (value) => {
        const first = allResources(project)[0];
        generation.activation = value === "explicit" ? { mode: "explicit", roots: first ? [{ kind: first.kind, id: first.id }] : [] } : { mode: "auto" };
        commitAndRender(container, controller);
    }));
    if (generation.activation?.mode === "explicit") {
        const roots = document.createElement("div");
        roots.className = "minimax-h3-inline-list";
        for (const [index, root] of (generation.activation.roots ?? []).entries()) {
            const row = document.createElement("div");
            row.className = "minimax-h3-inline-editor";
            row.append(
                labeledSelect("Kind", root.kind, [["asset", "Asset"], ["subject", "Subject"], ["environment", "Environment"]], (value) => {
                    root.kind = value;
                    root.id = allResources(project).find((resource) => resource.kind === value)?.id ?? "";
                    commitAndRender(container, controller);
                }),
                labeledSelect("Resource", root.id, allResources(project).filter((resource) => resource.kind === root.kind).map((resource) => [resource.id, resource.label]), (value) => { root.id = value; commitProject(controller); }),
            );
            const remove = actionButton("Remove", () => { generation.activation.roots.splice(index, 1); commitAndRender(container, controller); });
            remove.disabled = generation.activation.roots.length <= 1;
            row.appendChild(remove);
            roots.appendChild(row);
        }
        roots.appendChild(actionButton("+ Root", () => {
            const first = allResources(project)[0];
            if (!first) return;
            generation.activation.roots.push({ kind: first.kind, id: first.id });
            commitAndRender(container, controller);
        }));
        block.body.appendChild(roots);
    }
    const list = document.createElement("div");
    list.className = "minimax-h3-activation-list";
    for (const resource of model.resources) {
        const row = document.createElement("div");
        row.className = "minimax-h3-activation-row";
        row.dataset.state = resource.missing ? "error" : resource.excluded ? "excluded" : "active";
        const label = project[`${resource.kind}s`]?.find((item) => item.id === resource.id)?.name ?? resource.id;
        row.textContent = `${resource.kind} · ${label} — ${resource.reasons.join(", ")}${resource.missing ? " (missing)" : ""}`;
        list.appendChild(row);
    }
    if (!model.resources.length) {
        const empty = document.createElement("p");
        empty.textContent = "No active media yet. Add an initial state, explicit root or binding.";
        list.appendChild(empty);
    }
    block.body.appendChild(list);
    const optional = section("Optional exclusions", "required dependencies stay locked");
    const required = new Set(model.resources.map((item) => `${item.kind}:${item.id}`));
    const excludes = generation.activation?.exclude ?? [];
    for (const resource of allResources(project)) {
        const key = `${resource.kind}:${resource.id}`;
        const locked = required.has(key);
        const excluded = excludes.some((item) => item.kind === resource.kind && item.id === resource.id);
        optional.body.appendChild(checkbox(`${resource.kind} · ${resource.label}`, excluded, (checked) => {
            generation.activation.exclude = excludes.filter((item) => !(item.kind === resource.kind && item.id === resource.id));
            if (checked) generation.activation.exclude.push({ kind: resource.kind, id: resource.id });
            if (!generation.activation.exclude.length) delete generation.activation.exclude;
            commitAndRender(container, controller);
        }, locked && !excluded, locked ? "Required by the current dependency closure." : ""));
    }
    block.body.appendChild(optional.details);
    return { block, model };
}

function occupiedSlots(project, generation, type, ignoredBinding = null) {
    const assets = new Map(project.assets.map((asset) => [asset.id, asset]));
    const occupied = new Set();
    for (const binding of generation.bindings ?? []) {
        if (binding === ignoredBinding) continue;
        const asset = assets.get(binding.assetId);
        if (asset?.type === type) occupied.add(Number(binding.slotIndex));
        if (type === "audio" && asset?.type === "video" && binding.soundtrackSlotIndex) occupied.add(Number(binding.soundtrackSlotIndex));
    }
    return occupied;
}

function renderBindings(container, project, generation, model, controller) {
    const block = section("File slot assignments", `${generation.bindings?.length ?? 0} mapped`);
    block.body.appendChild(helpText("Map each logical reference to the matching input slot on the generator node. This screen does not upload or connect the file."));
    if (!(generation.bindings ?? []).length) {
        block.body.appendChild(helpText("No file slots mapped for this generation yet. Connect files on the generator node, then add a binding here.", "minimax-h3-media-empty-note"));
    }
    for (const binding of generation.bindings ?? []) {
        const asset = project.assets.find((candidate) => candidate.id === binding.assetId);
        const row = document.createElement("div");
        row.className = "minimax-h3-binding-row";
        const availableAssets = project.assets.filter((candidate) => candidate.id === binding.assetId || !(generation.bindings ?? []).some((other) => other !== binding && other.assetId === candidate.id));
        row.appendChild(labeledSelect("Asset", binding.assetId, availableAssets.map((item) => [item.id, item.name]), (value) => {
            binding.assetId = value;
            const replacement = project.assets.find((item) => item.id === value);
            binding.slotIndex = nextAvailableSlot(project, generation, replacement?.type, binding) ?? 1;
            if (replacement?.type !== "video") delete binding.soundtrackSlotIndex;
            if (replacement?.type !== "picture") delete binding.role;
            commitAndRender(container, controller);
        }));
        const type = asset?.type ?? "picture";
        const occupied = occupiedSlots(project, generation, type, binding);
        const choices = Array.from({ length: MEDIA_LIMITS[type] ?? 0 }, (_, index) => index + 1).filter((slot) => slot === Number(binding.slotIndex) || !occupied.has(slot)).map((slot) => [String(slot), `${type} ${slot}`]);
        row.appendChild(labeledSelect("Slot", String(binding.slotIndex), choices, (value) => { binding.slotIndex = Number(value); commitAndRender(container, controller); }));
        if (asset?.type === "picture") {
            row.appendChild(labeledSelect("Frame role", effectivePictureBindingRole(project, generation, binding), PICTURE_BINDING_ROLES, (value) => {
                if (value === "reference") delete binding.role; else binding.role = value;
                commitAndRender(container, controller);
            }));
        }
        if (asset?.type === "video" && ["paired", "alone"].includes(asset.audioMode)) {
            const audioOccupied = occupiedSlots(project, generation, "audio", binding);
            const audioChoices = Array.from({ length: MEDIA_LIMITS.audio }, (_, index) => index + 1).filter((slot) => slot === Number(binding.soundtrackSlotIndex) || !audioOccupied.has(slot)).map((slot) => [String(slot), `Audio ${slot}`]);
            row.appendChild(labeledSelect("Soundtrack slot", String(binding.soundtrackSlotIndex ?? audioChoices[0]?.[0] ?? ""), audioChoices, (value) => { binding.soundtrackSlotIndex = Number(value); commitProject(controller); }));
        }
        const label = document.createElement("strong");
        label.textContent = `${physicalLabel(asset, binding)} · ${bindingRoleLabel({ role: effectivePictureBindingRole(project, generation, binding) })}`;
        row.append(label, actionButton("Remove", () => { generation.bindings.splice(generation.bindings.indexOf(binding), 1); commitAndRender(container, controller); }));
        block.body.appendChild(row);
    }
    const bound = new Set((generation.bindings ?? []).map((binding) => binding.assetId));
    const candidate = project.assets.find((asset) => model.activeAssetIds.has(asset.id) && !bound.has(asset.id) && nextAvailableSlot(project, generation, asset.type) !== null)
        ?? project.assets.find((asset) => !bound.has(asset.id) && nextAvailableSlot(project, generation, asset.type) !== null);
    const add = actionButton("+ Binding", () => {
        if (!candidate) return;
        const binding = { assetId: candidate.id, slotIndex: nextAvailableSlot(project, generation, candidate.type) };
        if (candidate.type === "picture") {
            const role = suggestedPictureRole(project, generation);
            if (role !== "reference") binding.role = role;
        }
        if (candidate.type === "video" && ["paired", "alone"].includes(candidate.audioMode)) binding.soundtrackSlotIndex = nextAvailableSlot(project, generation, "audio");
        generation.bindings.push(binding);
        commitAndRender(container, controller);
    });
    add.disabled = !candidate || generation.bindings.length >= 15;
    block.body.appendChild(add);
    const capacity = document.createElement("div");
    capacity.className = "minimax-h3-capacity";
    capacity.textContent = `Pictures ${model.counts.picture}/${MEDIA_LIMITS.picture} · Videos ${model.counts.video}/${MEDIA_LIMITS.video} · Audio ${model.counts.audio}/${MEDIA_LIMITS.audio} · Files ${model.totalFiles}/12 · Video ${model.videoSeconds.toFixed(1)}/15s · Audio ${model.audioSeconds.toFixed(1)}/15s`;
    capacity.dataset.state = Object.values(model.exceeded).some(Boolean) ? "error" : "ok";
    block.body.appendChild(capacity);
    return block.details;
}

function statePolicyChoices(generation) {
    const choices = [["none", "Not included"], ["explicit", "Explicit"], ["reset", "Reset"]];
    if (Number(generation.order) > 1) choices.push(["carry", "Carry from previous generation"]);
    return choices;
}

function renderInitialStates(container, project, generation, controller) {
    const block = section("Initial states", `${generation.subjectStates.length} subjects · ${generation.environmentStates.length} environments`);
    const subjectHeading = document.createElement("h4"); subjectHeading.textContent = "Subjects"; block.body.appendChild(subjectHeading);
    for (const subject of project.subjects) {
        const selection = generation.subjectStates.find((item) => item.subjectId === subject.id);
        const row = document.createElement("div"); row.className = "minimax-h3-state-row";
        const name = document.createElement("strong"); name.textContent = subject.name; row.appendChild(name);
        row.appendChild(labeledSelect("Policy", selection?.policy ?? "none", statePolicyChoices(generation), (policy) => {
            const index = generation.subjectStates.findIndex((item) => item.subjectId === subject.id);
            if (policy === "none") { if (index >= 0) generation.subjectStates.splice(index, 1); }
            else {
                const next = { subjectId: subject.id, policy };
                if (policy !== "carry") next.stateId = policy === "reset" ? subject.baseAppearanceStateId : subject.baseAppearanceStateId;
                if (policy === "reset") next.reason = "Return to the base appearance";
                if (index >= 0) generation.subjectStates[index] = next; else generation.subjectStates.push(next);
            }
            commitAndRender(container, controller);
        }));
        if (selection && selection.policy !== "carry") row.appendChild(labeledSelect("State", selection.stateId, subject.appearanceStates.map((state) => [state.id, state.name]), (value) => { selection.stateId = value; commitProject(controller); }));
        if (selection?.policy === "reset") row.appendChild(labeledInput("Reason", selection.reason ?? "", (value) => { selection.reason = value || "Continuity reset"; commitProject(controller); }));
        block.body.appendChild(row);
    }
    const environmentHeading = document.createElement("h4"); environmentHeading.textContent = "Environments"; block.body.appendChild(environmentHeading);
    for (const environment of project.environments) {
        const selection = generation.environmentStates.find((item) => item.environmentId === environment.id);
        const row = document.createElement("div"); row.className = "minimax-h3-state-row";
        const name = document.createElement("strong"); name.textContent = environment.name; row.appendChild(name);
        row.appendChild(labeledSelect("Policy", selection?.policy ?? "none", statePolicyChoices(generation), (policy) => {
            const index = generation.environmentStates.findIndex((item) => item.environmentId === environment.id);
            if (policy === "none") { if (index >= 0) generation.environmentStates.splice(index, 1); }
            else {
                const next = { environmentId: environment.id, policy, viewIds: [] };
                if (policy !== "carry") next.stateId = environment.defaultStateId;
                if (policy === "reset") next.reason = "Return to the default environment state";
                if (index >= 0) generation.environmentStates[index] = next; else generation.environmentStates.push(next);
            }
            commitAndRender(container, controller);
        }));
        if (selection && selection.policy !== "carry") row.appendChild(labeledSelect("State", selection.stateId, environment.states.map((state) => [state.id, state.name]), (value) => { selection.stateId = value; commitProject(controller); }));
        if (selection?.policy === "reset") row.appendChild(labeledInput("Reason", selection.reason ?? "", (value) => { selection.reason = value || "Continuity reset"; commitProject(controller); }));
        if (selection) {
            const views = document.createElement("div"); views.className = "minimax-h3-chip-picker";
            for (const view of environment.views ?? []) views.appendChild(checkbox(view.name, selection.viewIds.includes(view.id), (checked) => {
                const selected = new Set(selection.viewIds);
                if (checked) selected.add(view.id); else selected.delete(view.id);
                selection.viewIds = [...selected];
                commitAndRender(container, controller);
            }));
            row.appendChild(views);
        }
        block.body.appendChild(row);
    }
    return block.details;
}

function renderGenerationInspector(container, project, generation, controller) {
    const panel = document.createElement("section");
    panel.className = "minimax-h3-generation-pane";
    const tabs = document.createElement("div");
    tabs.className = "minimax-h3-segmented";
    for (const item of project.generations) {
        const button = actionButton(item.id, () => { controller.projectUiState.selectedGenerationId = item.id; renderReferencesTab(container, controller); });
        button.setAttribute("aria-pressed", String(item.id === generation.id));
        tabs.appendChild(button);
    }
    const add = actionButton("+ Generation", () => {
        if (project.generations.length && typeof window.confirm === "function" && !window.confirm("Adding another generation switches the project to Chained Multishot. Continue?")) return;
        const id = uniqueId(project.generations, "g");
        project.generations.push({ id, order: project.generations.length + 1, activation: { mode: "auto" }, bindings: [], subjectStates: [], environmentStates: [] });
        project.mode = "chained_multishot";
        controller.projectUiState.selectedGenerationId = id;
        commitAndRender(container, controller);
    });
    add.disabled = project.generations.length >= 64;
    tabs.appendChild(add);
    panel.appendChild(tabs);
    const { block, model } = renderActivation(container, project, generation, controller);
    panel.append(block.details, renderBindings(container, project, generation, model, controller), renderInitialStates(container, project, generation, controller));
    const generationShots = controller.shotDocument()?.value?.shots?.filter((shot) => shot.generationId === generation.id) ?? [];
    if (project.generations.length > 1) {
        const remove = actionButton("Delete generation", () => {
            project.generations.splice(project.generations.indexOf(generation), 1);
            project.generations.forEach((item, index) => { item.order = index + 1; });
            controller.projectUiState.selectedGenerationId = project.generations[0].id;
            commitAndRender(container, controller);
        });
        remove.disabled = generationShots.length > 0;
        remove.title = generationShots.length ? `Used by ${generationShots.map((shot) => shot.id).join(", ")}` : "";
        panel.appendChild(remove);
    }
    return panel;
}

export function renderReferencesTab(container, controller) {
    if ((container.children?.length ?? container.childElementCount ?? 0) > 0) {
        const remembered = captureOpenDisclosures(container);
        if (remembered !== null) controller.projectUiState.mediaOpenDisclosures = remembered;
    }
    container.replaceChildren();
    const documentState = controller.projectDocument();
    const project = projectForController(controller);
    if (!project) return readOnlyProjectMessage(container, documentState, controller);
    const toolbar = document.createElement("div");
    toolbar.className = "minimax-h3-studio-toolbar";
    const title = document.createElement("div");
    title.innerHTML = "<strong>Media references</strong><span>Describe logical references and map them to generator inputs</span>";
    toolbar.append(title, labeledSelect("Project mode", project.mode, PROJECT_MODES, (value) => { project.mode = value; commitProject(controller); }));
    container.append(toolbar, renderMediaOnboarding(), renderMediaWorkflowTools(container, project, controller));

    const assetArea = document.createElement("div");
    assetArea.className = "minimax-h3-master-detail minimax-h3-media-assets";
    const asset = selectedAsset(project, controller);
    assetArea.append(renderAssetMaster(container, project, controller), renderAssetInspector(container, project, asset, controller));
    container.appendChild(assetArea);

    const generationHeading = document.createElement("div");
    generationHeading.className = "minimax-h3-media-generation-heading";
    const generationTitle = document.createElement("h3");
    generationTitle.textContent = "Generation assignments";
    const generationHelp = document.createElement("p");
    generationHelp.textContent = "Control availability, match references to physical input slots and define continuity state per generation.";
    generationHeading.append(generationTitle, generationHelp);
    container.append(generationHeading, renderGenerationInspector(container, project, selectedGeneration(project, controller), controller));
    restoreOpenDisclosures(container, controller.projectUiState.mediaOpenDisclosures);
}
