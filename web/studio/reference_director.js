import { effectivePictureBindingRole, generationMediaModel } from "./media_model.js";

export const DIRECTOR_DROP_TARGETS = Object.freeze([
    { purposeId: "subject_identity", label: "Identity", accepts: "picture", targetKind: "subject", tone: "identity" },
    { purposeId: "voice", label: "Voice", accepts: "audio", targetKind: "subject", tone: "voice" },
    { purposeId: "performance", label: "Performance", accepts: "video", targetKind: "subject", tone: "motion" },
    { purposeId: "environment_view", label: "Background / set", accepts: "picture", targetKind: "environment", tone: "environment" },
    { purposeId: "camera", label: "Camera", accepts: "video", targetKind: "shot", tone: "motion" },
    { purposeId: "soundtrack", label: "Music / soundtrack", accepts: "audio", targetKind: "shot", tone: "voice" },
    { purposeId: "continuity", label: "Continuity", accepts: "picture", targetKind: "shot", tone: "identity" },
]);

function physicalLabel(asset, binding) {
    const prefix = asset?.type === "video" ? "Video" : asset?.type === "audio" ? "Audio" : "Picture";
    return `<${prefix} ${binding?.slotIndex ?? "?"}>`;
}

function assetConnections(project, shotPlan, asset) {
    const connections = [];
    for (const subject of project.subjects ?? []) {
        if ((subject.identityAssetIds ?? []).includes(asset.id)) connections.push(`Identity · ${subject.name}`);
        if (subject.defaultVoiceAssetId === asset.id) connections.push(`Voice · ${subject.name}`);
    }
    for (const environment of project.environments ?? []) {
        if ((environment.views ?? []).some((view) => view.assetId === asset.id)) connections.push(`Background · ${environment.name}`);
    }
    for (const prop of project.props ?? []) {
        if ((prop.designAssetIds ?? []).includes(asset.id)) connections.push(`Design · ${prop.name}`);
    }
    for (const shot of shotPlan?.shots ?? []) {
        for (const use of shot.referenceUses ?? []) {
            if (use.assetId !== asset.id) continue;
            const role = String(use.role ?? "reference").replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
            const targetId = use.targetIds?.[0];
            const target = (project.subjects ?? []).find((item) => item.id === targetId)
                ?? (project.environments ?? []).find((item) => item.id === targetId);
            connections.push(`${role} · ${target?.name || shot.action || shot.name || shot.id}`);
        }
    }
    return [...new Set(connections)];
}

export function resolvedReferenceInputs(project = {}, generation = {}, director = {}) {
    const assets = new Map((project.assets ?? []).map((asset) => [asset.id, asset]));
    const media = generationMediaModel(project, generation, null);
    const rows = [];
    for (const binding of generation?.bindings ?? []) {
        const asset = assets.get(binding.assetId);
        if (!asset) continue;
        rows.push({
            assetId: asset.id,
            name: asset.name || asset.id,
            mediaType: asset.type,
            slotIndex: binding.slotIndex,
            label: physicalLabel(asset, binding),
            role: asset.type === "picture" ? effectivePictureBindingRole(project, generation, binding) : "reference",
            sourceReady: Boolean(director?.sources?.[asset.id]),
            active: media.activeAssetIds.has(asset.id),
        });
        if (asset.type === "video" && Number.isInteger(binding.soundtrackSlotIndex)) {
            rows.push({
                assetId: asset.id,
                name: `${asset.name || asset.id} soundtrack`,
                mediaType: "audio",
                slotIndex: binding.soundtrackSlotIndex,
                label: `<Audio ${binding.soundtrackSlotIndex}>`,
                role: "video_soundtrack",
                sourceReady: Boolean(director?.sources?.[asset.id]),
                active: media.activeAssetIds.has(asset.id),
                derivedFrom: physicalLabel(asset, binding),
            });
        }
    }
    const order = { picture: 0, video: 1, audio: 2 };
    return rows.sort((left, right) => (order[left.mediaType] ?? 99) - (order[right.mediaType] ?? 99)
        || Number(left.slotIndex) - Number(right.slotIndex) || left.assetId.localeCompare(right.assetId));
}

export function referenceDirectorModel(project = {}, shotPlan = {}, generationId = "") {
    const generation = (project.generations ?? []).find((item) => item.id === generationId) ?? project.generations?.[0] ?? null;
    const assets = (project.assets ?? []).map((asset) => {
        const binding = generation?.bindings?.find((item) => item.assetId === asset.id) ?? null;
        return {
            ...asset,
            binding,
            physicalLabel: binding ? physicalLabel(asset, binding) : "Unassigned",
            bindingRole: binding && asset.type === "picture" ? effectivePictureBindingRole(project, generation, binding) : "reference",
            connections: assetConnections(project, shotPlan, asset),
        };
    });
    const shots = (shotPlan?.shots ?? []).filter((shot) => !generation || (shot.generationId ?? "g1") === generation.id);
    const media = generation ? generationMediaModel(project, generation, shotPlan) : { activeAssetIds: new Set() };
    return {
        generation,
        assets,
        subjects: project.subjects ?? [],
        props: project.props ?? [],
        environments: project.environments ?? [],
        shots,
        assigned: assets.filter((asset) => asset.binding).length,
        activeAssetIds: media.activeAssetIds,
        targets: DIRECTOR_DROP_TARGETS,
    };
}

export function directorTargetAccepts(target, asset) {
    return Boolean(target && asset && target.accepts === asset.type);
}
