import { nextAvailableSlot } from "./media_model.js";

export function ensurePropDesignBindings(project, shotPlan, propId = "") {
    const issues = [];
    const props = (project?.props ?? []).filter((prop) => !propId || prop.id === propId);
    const assets = new Map((project?.assets ?? []).map((asset) => [asset.id, asset]));
    for (const generation of project?.generations ?? []) {
        const present = new Set((shotPlan?.shots ?? [])
            .filter((shot) => (shot.generationId ?? "g1") === generation.id)
            .flatMap((shot) => (shot.props ?? []).filter((use) => use.presence !== "absent").map((use) => use.propId)));
        for (const prop of props) {
            if (!present.has(prop.id)) continue;
            for (const assetId of prop.designAssetIds ?? []) {
                if ((generation.bindings ?? []).some((binding) => binding.assetId === assetId)) continue;
                const asset = assets.get(assetId);
                if (asset?.type !== "picture") {
                    issues.push(`${prop.name || prop.id} design reference ${assetId} is not a picture.`); continue;
                }
                const slotIndex = nextAvailableSlot(project, generation, "picture");
                if (slotIndex === null) {
                    issues.push(`No Picture slot is available for ${prop.name || prop.id} in ${generation.id}.`); continue;
                }
                (generation.bindings ??= []).push({ assetId, slotIndex });
            }
        }
    }
    return { project, issues, ok: issues.length === 0 };
}
