import { nextAvailableSlot } from "./media_model.js";

export const MEDIA_BINDING_PURPOSES = Object.freeze([
    { id: "subject_identity", label: "Subject identity", type: "picture", role: "identity_reinforcement", relation: "subject", help: "Keep one subject recognizable from a connected picture." },
    { id: "environment_view", label: "Environment view", type: "picture", role: "environment_view", relation: "environment", help: "Anchor a place with a named, reusable view." },
    { id: "performance", label: "Performance", type: "video", role: "performance", help: "Transfer observable timing and performance from a video." },
    { id: "camera", label: "Camera", type: "video", role: "camera_transfer", help: "Request camera motion only from an explicit video reference." },
    { id: "voice", label: "Voice", type: "audio", role: "voice", help: "Guide voice qualities from a connected audio reference." },
    { id: "continuity", label: "Continuity", type: "picture", role: "continuity", help: "Reinforce visible continuity in a selected shot." },
]);

export const MEDIA_RECIPES = Object.freeze([
    { id: "targeted_edit", label: "Targeted edit", purpose: "targeted_edit", description: "Change a bounded detail while preserving the rest of the selected shot." },
    { id: "relight", label: "Relight", purpose: "relight", description: "Use a picture as lighting guidance without claiming identity or camera transfer." },
    { id: "performance_transfer", label: "Performance transfer", purpose: "performance", description: "Use video timing and observable acting as shot-scoped guidance." },
    { id: "continuation", label: "Continuation", purpose: "continuation_video", description: "Continue from a video reference while keeping it explicitly bound to one generation." },
]);

function purposeDefinition(id) {
    if (id === "targeted_edit") return { id, label: "Targeted edit", type: "picture", role: "appearance", help: "Guide a bounded visible edit from a connected picture." };
    if (id === "relight") return { id, label: "Relight", type: "picture", role: "lighting", help: "Guide lighting from a connected picture." };
    if (id === "continuation_video") return { id, label: "Continuation video", type: "video", role: "continuity", help: "Continue visible action from a connected video." };
    return MEDIA_BINDING_PURPOSES.find((item) => item.id === id) ?? null;
}

export function mediaPurpose(id) {
    return purposeDefinition(id);
}

function nextId(items, prefix) {
    const used = new Set(items.map((item) => item.id));
    let index = items.length + 1;
    while (used.has(`${prefix}${index}`)) index += 1;
    return `${prefix}${index}`;
}

export function bindingPlanDiagnostics({ project, shotPlan, purposeId, generationId, shotId, relationId } = {}) {
    const purpose = purposeDefinition(purposeId);
    const issues = [];
    const generation = project?.generations?.find((item) => item.id === generationId);
    const shot = shotPlan?.shots?.find((item) => item.id === shotId);
    if (!purpose) issues.push("Choose a reference purpose.");
    if (!generation) issues.push("Choose an existing generation.");
    if (!shot) issues.push("Choose an existing shot.");
    else if (generation && shot.generationId !== generation.id) issues.push("The selected shot belongs to a different generation.");
    if (purpose?.relation === "subject" && !project?.subjects?.some((item) => item.id === relationId)) issues.push("Choose the subject whose identity this picture anchors.");
    if (purpose?.relation === "environment" && !project?.environments?.some((item) => item.id === relationId)) issues.push("Choose the environment this view belongs to.");
    if (purpose && generation && nextAvailableSlot(project, generation, purpose.type) === null) issues.push(`No ${purpose.type} slot is available in this generation.`);
    return issues;
}

export function createPurposeBinding(input = {}) {
    const issues = bindingPlanDiagnostics(input);
    if (issues.length) return { ok: false, issues };
    const purpose = purposeDefinition(input.purposeId);
    const project = structuredClone(input.project);
    const shotPlan = structuredClone(input.shotPlan);
    const generation = project.generations.find((item) => item.id === input.generationId);
    const shot = shotPlan.shots.find((item) => item.id === input.shotId);
    const assetId = nextId(project.assets, "asset.");
    const asset = { id: assetId, type: purpose.type, name: String(input.name ?? "").trim() || purpose.label, available: true };
    if (purpose.id === "camera") asset.cameraTransfer = { enabled: true, role: "camera_reference", aspects: ["motion"] };
    project.assets.push(asset);
    const binding = { assetId, slotIndex: nextAvailableSlot(project, generation, purpose.type) };
    if (purpose.type === "picture") {
        const role = project.mode === "i2va" ? "first_frame" : project.mode === "l2va" ? "last_frame"
            : project.mode === "fl2va"
                ? (generation.bindings ?? []).some((item) => item.role === "first_frame") ? "last_frame" : "first_frame"
                : "reference";
        if (role !== "reference") binding.role = role;
    }
    generation.bindings.push(binding);
    if (purpose.relation === "subject") {
        const subject = project.subjects.find((item) => item.id === input.relationId);
        if (!(subject.identityAssetIds ??= []).includes(assetId)) subject.identityAssetIds.push(assetId);
    } else if (purpose.relation === "environment") {
        const environment = project.environments.find((item) => item.id === input.relationId);
        const viewId = nextId(environment.views ??= [], "view.");
        environment.views.push({ id: viewId, name: asset.name, role: "overview", assetId });
    }
    const use = { assetId, role: purpose.role };
    if (purpose.role === "camera_transfer") use.cameraAspects = ["motion"];
    (shot.referenceUses ??= []).push(use);
    return { ok: true, project, shotPlan, assetId, summary: `${purpose.label} · ${shot.id} · Generation ${generation.order ?? generation.id}` };
}

export function createPlanningContext({ projectDocument, shotDocument } = {}) {
    const project = projectDocument?.kind === "v2" ? structuredClone(projectDocument.value) : null;
    const shotPlan = shotDocument?.kind === "v2" ? structuredClone(shotDocument.value) : null;
    return {
        format: "minimax-h3-planning-context",
        formatVersion: 1,
        readOnly: true,
        purpose: "Context for an LLM to discuss or propose a Prompt Studio plan. It is not an import package and must not claim that physical media is attached.",
        instructions: [
            "Preserve schemaVersion, stable IDs and generation boundaries.",
            "Treat bindings as declarations for files the user connects separately on the generator node.",
            "Return suggestions for review; do not imply that this context can be auto-applied.",
        ],
        documents: { ...(project ? { mediaProject: project } : {}), ...(shotPlan ? { shotPlan } : {}) },
    };
}
