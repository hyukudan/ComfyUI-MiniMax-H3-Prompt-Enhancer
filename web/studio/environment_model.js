import { nextAvailableSlot } from "./media_model.js";

export function ensureEnvironmentViewBindings(project, shotPlan, environmentId = "") {
    const issues = [];
    const environments = new Map((project?.environments ?? []).map((item) => [item.id, item]));
    const assets = new Map((project?.assets ?? []).map((item) => [item.id, item]));
    for (const generation of project?.generations ?? []) {
        const required = new Set();
        for (const shot of shotPlan?.shots ?? []) {
            if ((shot.generationId ?? "g1") !== generation.id) continue;
            const selection = shot.environment;
            if (!selection?.environmentId || (environmentId && selection.environmentId !== environmentId)) continue;
            const environment = environments.get(selection.environmentId);
            if (!environment) continue;
            const selected = new Set(selection.viewIds ?? []);
            for (const view of environment.views ?? []) if (selected.has(view.id)) required.add(view.assetId);
        }
        for (const assetId of required) {
            if ((generation.bindings ?? []).some((binding) => binding.assetId === assetId)) continue;
            const asset = assets.get(assetId);
            if (asset?.type !== "picture") { issues.push(`Place view ${assetId} is not a picture.`); continue; }
            const slotIndex = nextAvailableSlot(project, generation, "picture");
            if (slotIndex === null) { issues.push(`No Picture slot is available for Place view ${asset.name || assetId} in ${generation.id}.`); continue; }
            (generation.bindings ??= []).push({ assetId, slotIndex });
        }
    }
    return { project, issues, ok: issues.length === 0 };
}

