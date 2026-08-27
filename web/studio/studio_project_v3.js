export const STUDIO_PROJECT_WIDGET = "studio_project_json";
export const STUDIO_PROJECT_SCHEMA_VERSION = 3;

const clone = (value) => value == null ? value : JSON.parse(JSON.stringify(value));

export function emptyStudioProjectV3() {
    return {
        schemaVersion: STUDIO_PROJECT_SCHEMA_VERSION,
        project: {
            name: "Untitled project", mode: "auto", timingMode: "auto",
            look: { creativeTreatment: { schemaVersion: 2 }, cinematography: { schemaVersion: 2 } },
        },
        files: [], subjects: [], props: [], environments: [],
        generations: [{ id: "g1", order: 1 }], shots: [], links: [],
    };
}

export function parseStudioProjectV3(raw) {
    if (!String(raw ?? "").trim()) return { kind: "blank", raw: String(raw ?? ""), value: null };
    try {
        const value = typeof raw === "string" ? JSON.parse(raw) : clone(raw);
        if (!value || typeof value !== "object" || Array.isArray(value)) return { kind: "malformed", raw, value: null };
        if (value.schemaVersion !== STUDIO_PROJECT_SCHEMA_VERSION) return { kind: "future", raw, value };
        return { kind: "v3", raw: typeof raw === "string" ? raw : JSON.stringify(raw), value };
    } catch (error) {
        return { kind: "malformed", raw: String(raw ?? ""), value: null, message: error.message };
    }
}

function sourceFor(asset, referenceDirector) {
    return clone(referenceDirector?.sources?.[asset.id] ?? asset.source ?? null);
}

// Existing editors can keep their battle-tested local shapes while v3 becomes the
// only aggregate stored and executed. These documents are compatibility projections,
// never a second user-facing project model.
export function studioProjectFromDocuments({ mediaProject, shotPlan, creativeTreatment, cinematography, referenceDirector, previous } = {}) {
    const media = mediaProject && typeof mediaProject === "object" ? mediaProject : {};
    const plan = shotPlan && typeof shotPlan === "object" ? shotPlan : {};
    const prior = previous?.schemaVersion === 3 ? previous : emptyStudioProjectV3();
    const files = (media.assets ?? []).map((asset) => ({
        ...clone(asset),
        source: sourceFor(asset, referenceDirector) ?? undefined,
    }));
    const subjects = (media.subjects ?? []).map((subject) => {
        const mapped = {
            ...clone(subject),
            identityFileIds: [...(subject.identityAssetIds ?? subject.identityFileIds ?? [])],
        };
        delete mapped.identityAssetIds;
        if (subject.defaultVoiceAssetId || subject.defaultVoiceFileId) mapped.defaultVoiceFileId = subject.defaultVoiceAssetId ?? subject.defaultVoiceFileId;
        delete mapped.defaultVoiceAssetId;
        return mapped;
    });
    const props = (media.props ?? []).map((prop) => ({
        ...clone(prop),
        designFileIds: [...(prop.designAssetIds ?? prop.designFileIds ?? [])],
        designAssetIds: undefined,
    }));
    for (const prop of props) delete prop.designAssetIds;
    const environments = (media.environments ?? []).map((environment) => ({
        ...clone(environment),
        views: (environment.views ?? []).map((view) => {
            const mapped = { ...clone(view), fileId: view.assetId ?? view.fileId };
            delete mapped.assetId;
            return mapped;
        }),
    }));
    const shots = (plan.shots ?? []).map((shot) => {
        const mapped = {
            ...clone(shot),
            cast: clone(shot.cast ?? shot.subjects ?? []),
            referenceBindings: (shot.referenceBindings ?? shot.referenceUses ?? []).map((binding) => {
                const item = { ...clone(binding), fileId: binding.fileId ?? binding.assetId };
                delete item.assetId;
                return item;
            }),
        };
        delete mapped.subjects;
        delete mapped.referenceUses;
        if (mapped.environment?.viewIds?.length === 1) mapped.environment.viewId = mapped.environment.viewIds[0];
        return mapped;
    });
    const generations = (media.generations?.length ? media.generations : prior.generations ?? []).map((generation, index) => {
        const mapped = {
            ...clone(generation),
            id: generation.id || `g${index + 1}`,
            order: Number(generation.order) || index + 1,
        };
        // Physical slots are always recompiled from semantic use; keeping them here
        // would create a second authority. Activation roots and state policies remain facts.
        delete mapped.bindings;
        return mapped;
    });
    return {
        schemaVersion: 3,
        project: {
            ...clone(prior.project ?? {}),
            name: prior.project?.name || "Untitled project",
            mode: media.mode ?? prior.project?.mode ?? "auto",
            timingMode: plan.timingMode ?? prior.project?.timingMode ?? "auto",
            look: {
                creativeTreatment: clone(creativeTreatment ?? prior.project?.look?.creativeTreatment ?? { schemaVersion: 2 }),
                cinematography: clone(cinematography ?? prior.project?.look?.cinematography ?? { schemaVersion: 2 }),
            },
        },
        files, subjects, props, environments, generations, shots,
        links: clone(prior.links ?? []),
    };
}

export function stableStudioProjectJson(project) {
    return JSON.stringify(project);
}
