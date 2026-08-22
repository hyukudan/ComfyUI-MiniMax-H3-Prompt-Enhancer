export const MEDIA_LIMITS = Object.freeze({ picture: 9, video: 3, audio: 3 });

function resourceKey(kind, id) {
    return `${kind}:${id}`;
}

function addReason(reasons, kind, id, reason) {
    if (!id) return false;
    const key = resourceKey(kind, id);
    const entry = reasons.get(key) ?? { kind, id, reasons: [] };
    if (!entry.reasons.includes(reason)) entry.reasons.push(reason);
    reasons.set(key, entry);
    return entry.reasons.length === 1;
}

export function generationMediaModel(project, generation, shotPlan = null) {
    const assets = new Map((project?.assets ?? []).map((item) => [item.id, item]));
    const subjects = new Map((project?.subjects ?? []).map((item) => [item.id, item]));
    const environments = new Map((project?.environments ?? []).map((item) => [item.id, item]));
    const subjectStates = new Map((generation?.subjectStates ?? []).map((item) => [item.subjectId, item]));
    const environmentStates = new Map((generation?.environmentStates ?? []).map((item) => [item.environmentId, item]));
    const reasons = new Map();
    const queue = [];
    const enqueue = (kind, id, reason) => {
        if (addReason(reasons, kind, id, reason)) queue.push({ kind, id });
    };

    if (generation?.activation?.mode === "explicit") {
        for (const root of generation.activation.roots ?? []) enqueue(root.kind, root.id, "explicit activation root");
    }
    for (const selection of generation?.subjectStates ?? []) enqueue("subject", selection.subjectId, "initial subject state");
    for (const selection of generation?.environmentStates ?? []) enqueue("environment", selection.environmentId, "initial environment state");
    for (const binding of generation?.bindings ?? []) enqueue("asset", binding.assetId, "physical binding");
    for (const shot of shotPlan?.shots ?? []) {
        if ((shot.generationId ?? "g1") !== generation?.id) continue;
        for (const presence of shot.subjects ?? []) {
            if (presence.presence !== "absent") enqueue("subject", presence.subjectId, `presence in shot ${shot.id}`);
        }
        if (shot.environment?.environmentId) enqueue("environment", shot.environment.environmentId, `location of shot ${shot.id}`);
        for (const reference of shot.referenceUses ?? []) enqueue("asset", reference.assetId, `reference in shot ${shot.id}`);
    }

    for (let index = 0; index < queue.length; index += 1) {
        const resource = queue[index];
        if (resource.kind === "subject") {
            const subject = subjects.get(resource.id);
            if (!subject) continue;
            for (const assetId of subject.identityAssetIds ?? []) enqueue("asset", assetId, `identity of ${subject.name}`);
            const selection = subjectStates.get(subject.id);
            const stateId = selection?.resolvedStateId ?? selection?.stateId ?? subject.baseAppearanceStateId;
            const states = new Map((subject.appearanceStates ?? []).map((state) => [state.id, state]));
            const seen = new Set();
            let current = states.get(stateId);
            while (current && !seen.has(current.id)) {
                seen.add(current.id);
                if (current.source?.mode === "asset") enqueue("asset", current.source.assetId, `appearance “${current.name}” of ${subject.name}`);
                current = current.extends ? states.get(current.extends) : null;
            }
        } else if (resource.kind === "environment") {
            const environment = environments.get(resource.id);
            const selection = environmentStates.get(resource.id);
            if (!environment || !selection) continue;
            const selectedViews = new Set(selection.viewIds ?? []);
            for (const view of environment.views ?? []) {
                if (selectedViews.has(view.id)) enqueue("asset", view.assetId, `view “${view.name}” of ${environment.name}`);
            }
        }
    }

    const excluded = new Set((generation?.activation?.exclude ?? []).map((item) => resourceKey(item.kind, item.id)));
    const resources = [...reasons.values()].map((entry) => ({
        ...entry,
        excluded: excluded.has(resourceKey(entry.kind, entry.id)),
        missing: entry.kind === "asset" ? !assets.has(entry.id)
            : entry.kind === "subject" ? !subjects.has(entry.id) : !environments.has(entry.id),
    }));
    const activeAssetIds = new Set(resources.filter((entry) => entry.kind === "asset" && !entry.excluded && !entry.missing).map((entry) => entry.id));
    const counts = { picture: 0, video: 0, audio: 0 };
    let videoSeconds = 0;
    let audioSeconds = 0;
    for (const assetId of activeAssetIds) {
        const asset = assets.get(assetId);
        counts[asset.type] += 1;
        if (asset.type === "video") {
            videoSeconds += Number(asset.durationSeconds ?? 0);
            if (["paired", "alone"].includes(asset.audioMode)) {
                counts.audio += 1;
                audioSeconds += Number(asset.durationSeconds ?? 0);
            }
        } else if (asset.type === "audio") {
            audioSeconds += Number(asset.durationSeconds ?? 0);
        }
    }
    const totalFiles = activeAssetIds.size;
    return {
        resources,
        activeAssetIds,
        counts,
        totalFiles,
        videoSeconds,
        audioSeconds,
        exceeded: {
            picture: counts.picture > MEDIA_LIMITS.picture,
            video: counts.video > MEDIA_LIMITS.video,
            audio: counts.audio > MEDIA_LIMITS.audio,
            files: totalFiles > 12,
            videoSeconds: videoSeconds > 15,
            audioSeconds: audioSeconds > 15,
        },
    };
}

export function nextAvailableSlot(project, generation, assetType, ignoredBinding = null) {
    const assets = new Map((project?.assets ?? []).map((item) => [item.id, item]));
    const occupied = new Set();
    for (const binding of generation?.bindings ?? []) {
        if (binding === ignoredBinding) continue;
        const boundAsset = assets.get(binding.assetId);
        if (boundAsset?.type === assetType) occupied.add(Number(binding.slotIndex));
        if (assetType === "audio" && boundAsset?.type === "video" && binding.soundtrackSlotIndex) {
            occupied.add(Number(binding.soundtrackSlotIndex));
        }
    }
    const maximum = MEDIA_LIMITS[assetType] ?? 0;
    for (let slot = 1; slot <= maximum; slot += 1) if (!occupied.has(slot)) return slot;
    return null;
}

export function assetUsage(project, assetId) {
    const usage = [];
    for (const subject of project?.subjects ?? []) {
        if ((subject.identityAssetIds ?? []).includes(assetId)) usage.push(`identity of ${subject.name}`);
        for (const state of subject.appearanceStates ?? []) {
            if (state.source?.mode === "asset" && state.source.assetId === assetId) usage.push(`appearance “${state.name}” of ${subject.name}`);
        }
    }
    for (const environment of project?.environments ?? []) {
        for (const view of environment.views ?? []) if (view.assetId === assetId) usage.push(`view “${view.name}” of ${environment.name}`);
    }
    for (const generation of project?.generations ?? []) {
        if ((generation.bindings ?? []).some((binding) => binding.assetId === assetId)) usage.push(`binding in ${generation.id}`);
    }
    return usage;
}
