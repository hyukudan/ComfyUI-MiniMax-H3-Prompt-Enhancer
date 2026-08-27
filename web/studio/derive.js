function addUse(index, key, label) {
    if (!key) return;
    const uses = index.get(key) ?? [];
    if (!uses.includes(label)) uses.push(label);
    index.set(key, uses);
}

function targetUses(target, label, indexes) {
    if (!target?.id) return;
    if (target.kind === "subject") addUse(indexes.subjects, target.id, label);
    if (target.kind === "environment") addUse(indexes.environments, target.id, label);
    if (target.kind === "asset") addUse(indexes.assets, target.id, label);
}

export function usageIndex(project = {}, plan = {}) {
    const indexes = {
        subjects: new Map(),
        appearanceStates: new Map(),
        environments: new Map(),
        props: new Map(),
        environmentStates: new Map(),
        environmentViews: new Map(),
        assets: new Map(),
    };
    const appearanceKey = (subjectId, stateId) => `${subjectId}:${stateId}`;
    const environmentKey = (environmentId, stateId) => `${environmentId}:${stateId}`;
    const viewKey = (environmentId, viewId) => `${environmentId}:${viewId}`;

    for (const subject of project.subjects ?? []) {
        for (const assetId of subject.identityAssetIds ?? []) addUse(indexes.assets, assetId, `Identity · ${subject.name || subject.id}`);
        for (const state of subject.appearanceStates ?? []) {
            if (state.source?.mode === "asset") addUse(indexes.assets, state.source.assetId, `Appearance · ${subject.name || subject.id} / ${state.name || state.id}`);
        }
    }
    for (const environment of project.environments ?? []) {
        for (const view of environment.views ?? []) addUse(indexes.assets, view.assetId, `View · ${environment.name || environment.id} / ${view.name || view.id}`);
    }
    for (const prop of project.props ?? []) {
        for (const assetId of prop.designAssetIds ?? []) addUse(indexes.assets, assetId, `Design · ${prop.name || prop.id}`);
    }
    for (const generation of project.generations ?? []) {
        const generationLabel = `Generation ${generation.order ?? generation.id}`;
        for (const binding of generation.bindings ?? []) addUse(indexes.assets, binding.assetId, `${generationLabel} binding`);
        for (const reference of [...(generation.activation?.roots ?? []), ...(generation.activation?.exclude ?? [])]) {
            if (reference.kind === "subject") addUse(indexes.subjects, reference.id, `${generationLabel} activation`);
            if (reference.kind === "environment") addUse(indexes.environments, reference.id, `${generationLabel} activation`);
            if (reference.kind === "asset") addUse(indexes.assets, reference.id, `${generationLabel} activation`);
        }
        for (const selection of generation.subjectStates ?? []) {
            addUse(indexes.subjects, selection.subjectId, `${generationLabel} initial state`);
            if (selection.stateId) addUse(indexes.appearanceStates, appearanceKey(selection.subjectId, selection.stateId), `${generationLabel} initial state`);
        }
        for (const selection of generation.environmentStates ?? []) {
            addUse(indexes.environments, selection.environmentId, `${generationLabel} initial state`);
            if (selection.stateId) addUse(indexes.environmentStates, environmentKey(selection.environmentId, selection.stateId), `${generationLabel} initial state`);
            for (const viewId of selection.viewIds ?? []) addUse(indexes.environmentViews, viewKey(selection.environmentId, viewId), `${generationLabel} initial view`);
        }
    }

    for (const [shotIndex, shot] of (plan.shots ?? []).entries()) {
        const label = `Shot ${shotIndex + 1} · ${shot.id}`;
        for (const presence of shot.subjects ?? []) addUse(indexes.subjects, presence.subjectId, `${label} presence`);
        for (const presence of shot.props ?? []) addUse(indexes.props, presence.propId, `${label} presence`);
        for (const relationship of shot.scaleRelationships ?? []) {
            addUse(indexes.subjects, relationship.subjectId, `${label} scale relationship`);
            addUse(indexes.subjects, relationship.relativeToId, `${label} scale landmark`);
        }
        if (shot.environment?.environmentId) {
            addUse(indexes.environments, shot.environment.environmentId, `${label} location`);
            for (const viewId of shot.environment.viewIds ?? []) addUse(indexes.environmentViews, viewKey(shot.environment.environmentId, viewId), `${label} view`);
        }
        for (const use of shot.referenceUses ?? []) {
            addUse(indexes.assets, use.assetId, `${label} reference`);
            for (const targetId of use.targetIds ?? []) {
                if ((project.subjects ?? []).some((item) => item.id === targetId)) addUse(indexes.subjects, targetId, `${label} reference target`);
                if ((project.environments ?? []).some((item) => item.id === targetId)) addUse(indexes.environments, targetId, `${label} reference target`);
            }
        }
        for (const transition of shot.appearanceTransitions ?? []) {
            addUse(indexes.subjects, transition.subjectId, `${label} appearance change`);
            addUse(indexes.appearanceStates, appearanceKey(transition.subjectId, transition.fromStateId), `${label} transition start`);
            addUse(indexes.appearanceStates, appearanceKey(transition.subjectId, transition.toStateId), `${label} transition end`);
        }
        for (const transition of shot.environmentTransitions ?? []) {
            addUse(indexes.environments, transition.environmentId, `${label} environment change`);
            addUse(indexes.environmentStates, environmentKey(transition.environmentId, transition.fromStateId), `${label} transition start`);
            addUse(indexes.environmentStates, environmentKey(transition.environmentId, transition.toStateId), `${label} transition end`);
        }
        for (const frame of [shot.cameraStart, shot.cameraEnd]) {
            for (const target of [frame?.primaryTarget, frame?.secondaryTarget, frame?.foregroundTarget, frame?.focus?.primaryTarget, frame?.focus?.secondaryTarget]) {
                targetUses(target, `${label} camera target`, indexes);
            }
        }
        targetUses(shot.cameraPath?.anchorTarget, `${label} camera path anchor`, indexes);
    }
    return indexes;
}

export function resolveEntryStates(project = {}, plan = {}) {
    const byShot = new Map();
    const generationFinal = new Map();
    const generations = [...(project.generations ?? [])].sort((left, right) => (left.order ?? 0) - (right.order ?? 0));
    const subjects = project.subjects ?? [];
    const environments = project.environments ?? [];
    let previousSubjects = Object.fromEntries(subjects.map((subject) => [subject.id, subject.baseAppearanceStateId]));
    let previousEnvironments = Object.fromEntries(environments.map((environment) => [environment.id, environment.defaultStateId]));

    for (const generation of generations) {
        const subjectStates = { ...previousSubjects };
        const environmentStates = { ...previousEnvironments };
        for (const subject of subjects) {
            const selection = generation.subjectStates?.find((item) => item.subjectId === subject.id);
            if (selection?.policy === "explicit" || selection?.policy === "reset") subjectStates[subject.id] = selection.stateId;
            else if (!subjectStates[subject.id]) subjectStates[subject.id] = subject.baseAppearanceStateId;
        }
        for (const environment of environments) {
            const selection = generation.environmentStates?.find((item) => item.environmentId === environment.id);
            if (selection?.policy === "explicit" || selection?.policy === "reset") environmentStates[environment.id] = selection.stateId;
            else if (!environmentStates[environment.id]) environmentStates[environment.id] = environment.defaultStateId;
        }
        for (const shot of (plan.shots ?? []).filter((item) => item.generationId === generation.id)) {
            byShot.set(shot.id, { subjects: { ...subjectStates }, environments: { ...environmentStates } });
            for (const transition of shot.appearanceTransitions ?? []) subjectStates[transition.subjectId] = transition.toStateId;
            for (const transition of shot.environmentTransitions ?? []) environmentStates[transition.environmentId] = transition.toStateId;
        }
        previousSubjects = { ...subjectStates };
        previousEnvironments = { ...environmentStates };
        generationFinal.set(generation.id, { subjects: previousSubjects, environments: previousEnvironments });
    }

    for (const shot of plan.shots ?? []) {
        if (!byShot.has(shot.id)) byShot.set(shot.id, { subjects: { ...previousSubjects }, environments: { ...previousEnvironments } });
    }
    return { byShot, generationFinal };
}

const GLOBAL_CAMERA_KEYS = {
    framing: "shotScale",
    angle: "cameraAngle",
    viewpoint: "cameraViewpoint",
    focus: "depthOfField",
    motion: "cameraMotion",
};

export function cameraProvenance(plan = {}, cinematography = {}, project = {}) {
    const assets = new Map((project.assets ?? []).map((asset) => [asset.id, asset]));
    const byShot = new Map();
    const frameAspects = ["framing", "angle", "viewpoint", "composition", "focus", "distance"];
    for (const shot of plan.shots ?? []) {
        const transfers = new Map();
        for (const use of shot.referenceUses ?? []) {
            if (use.role !== "camera_transfer") continue;
            const asset = assets.get(use.assetId);
            for (const aspect of use.cameraAspects ?? []) transfers.set(aspect, asset?.name || use.assetId);
        }
        const phases = { start: {}, end: {}, path: {} };
        for (const aspect of frameAspects) {
            const explicitStart = shot.cameraStart?.[aspect] !== undefined;
            const transfer = transfers.get(aspect);
            const globalKey = GLOBAL_CAMERA_KEYS[aspect];
            const hasGlobal = cinematography?.[globalKey] && cinematography[globalKey] !== "none";
            phases.start[aspect] = explicitStart && transfer
                ? { owner: "conflict", label: `This shot and ${transfer}`, conflict: true }
                : explicitStart
                    ? { owner: "shot", label: "This shot" }
                    : transfer
                        ? { owner: "media", label: transfer }
                        : hasGlobal
                            ? { owner: "global", label: "Global camera" }
                            : { owner: "none", label: "Unspecified" };
            if (shot.cameraEnd?.[aspect] !== undefined) phases.end[aspect] = { owner: "shot", label: "This shot" };
            else phases.end[aspect] = { owner: "inherited", label: `Inherits start · ${phases.start[aspect].label}` };
        }
        const explicitMotion = shot.cameraPath?.motionType !== undefined;
        const transferMotion = transfers.get("motion");
        phases.path.motion = explicitMotion && transferMotion
            ? { owner: "conflict", label: `This shot and ${transferMotion}`, conflict: true }
            : explicitMotion
                ? { owner: "shot", label: "This shot" }
                : transferMotion
                    ? { owner: "media", label: transferMotion }
                    : cinematography?.cameraMotion && cinematography.cameraMotion !== "none"
                        ? { owner: "global", label: "Global camera" }
                        : { owner: "none", label: "Unspecified" };
        byShot.set(shot.id, phases);
    }
    return byShot;
}

export function slotCapacity(generation = {}, assets = []) {
    const assetsById = new Map(assets.map((asset) => [asset.id, asset]));
    const used = { picture: new Set(), video: new Set(), audio: new Set() };
    for (const binding of generation.bindings ?? []) {
        const asset = assetsById.get(binding.assetId);
        if (asset?.type && used[asset.type]) used[asset.type].add(binding.slotIndex);
        if (binding.soundtrackSlotIndex) used.audio.add(binding.soundtrackSlotIndex);
    }
    return {
        picture: { used: used.picture.size, maximum: 9 },
        video: { used: used.video.size, maximum: 3 },
        audio: { used: used.audio.size, maximum: 3 },
    };
}
