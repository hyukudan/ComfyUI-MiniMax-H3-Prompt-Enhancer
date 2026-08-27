import { nextAvailableSlot } from "./media_model.js";

function appearanceAssetIds(subject, stateId) {
    const states = new Map((subject?.appearanceStates ?? []).map((state) => [state.id, state]));
    const result = [];
    const seen = new Set();
    let state = states.get(stateId || subject?.baseAppearanceStateId);
    while (state && !seen.has(state.id)) {
        seen.add(state.id);
        if (state.source?.mode === "asset" && state.source.assetId) result.push(state.source.assetId);
        state = state.extends ? states.get(state.extends) : null;
    }
    return result;
}

export function ensureSubjectBindings(project, shotPlan, subjectId = "") {
    const issues = [];
    const subjects = (project?.subjects ?? []).filter((subject) => !subjectId || subject.id === subjectId);
    const subjectById = new Map(subjects.map((subject) => [subject.id, subject]));
    const assets = new Map((project?.assets ?? []).map((asset) => [asset.id, asset]));
    for (const generation of project?.generations ?? []) {
        const required = new Map();
        for (const shot of shotPlan?.shots ?? []) {
            if ((shot.generationId ?? "g1") !== generation.id) continue;
            for (const use of shot.subjects ?? []) {
                if (use.presence === "absent" || !subjectById.has(use.subjectId)) continue;
                const subject = subjectById.get(use.subjectId);
                const ids = required.get(subject.id) ?? new Set();
                for (const assetId of subject.identityAssetIds ?? []) ids.add(assetId);
                if (subject.defaultVoiceAssetId) ids.add(subject.defaultVoiceAssetId);
                for (const assetId of appearanceAssetIds(subject, use.appearanceStateId)) ids.add(assetId);
                required.set(subject.id, ids);
            }
        }
        for (const [id, assetIds] of required) {
            const subject = subjectById.get(id);
            for (const assetId of assetIds) {
                if ((generation.bindings ?? []).some((binding) => binding.assetId === assetId)) continue;
                const asset = assets.get(assetId);
                if (!asset) { issues.push(`${subject.name || id} references missing file ${assetId}.`); continue; }
                const slotIndex = nextAvailableSlot(project, generation, asset.type);
                if (slotIndex === null) { issues.push(`No ${asset.type} slot is available for ${subject.name || id} in ${generation.id}.`); continue; }
                (generation.bindings ??= []).push({ assetId, slotIndex });
            }
        }
    }
    return { project, issues, ok: issues.length === 0 };
}

