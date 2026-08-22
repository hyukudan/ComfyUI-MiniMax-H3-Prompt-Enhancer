const GLOBAL_CAMERA_FIELDS = {
    motion: ["cameraMotion", "cameraAmplitude", "cameraSpeed"],
    framing: ["shotScale"],
    angle: ["cameraAngle"],
    viewpoint: ["cameraViewpoint"],
    focus: ["depthOfField"],
    lens: ["optics", "lensEffects"],
};
const SLOT_LIMITS = { picture: 9, video: 3, audio: 3 };

function clone(value) {
    return value === undefined ? undefined : structuredClone(value);
}

function removeEmptyCamera(shot, key) {
    if (shot[key] && !Object.keys(shot[key]).length) delete shot[key];
}

function clearShotCamera(shot, aspects) {
    let changed = false;
    const frameProperties = {
        framing: ["framing"],
        angle: ["angle"],
        viewpoint: ["viewpoint"],
        composition: ["composition", "compositionNote", "primaryTarget", "secondaryTarget", "foregroundTarget"],
        focus: ["focus"],
        distance: ["distance", "distanceNote"],
    };
    for (const aspect of aspects) {
        for (const key of frameProperties[aspect] ?? []) {
            for (const phase of ["cameraStart", "cameraEnd"]) {
                if (shot[phase]?.[key] !== undefined) {
                    delete shot[phase][key];
                    changed = true;
                }
            }
        }
        if (aspect === "motion" && shot.cameraPath) {
            delete shot.cameraPath;
            changed = true;
        }
    }
    removeEmptyCamera(shot, "cameraStart");
    removeEmptyCamera(shot, "cameraEnd");
    return changed;
}

function activateResource(project, action) {
    const generation = project?.generations?.find((item) => item.id === action.generationId);
    if (!generation) return false;
    const resource = action.resource;
    let changed = false;
    const exclude = generation.activation?.exclude ?? [];
    const filtered = exclude.filter((item) => !(item.kind === resource.kind && item.id === resource.id));
    if (filtered.length !== exclude.length) {
        if (filtered.length) generation.activation.exclude = filtered;
        else delete generation.activation.exclude;
        changed = true;
    }
    if (generation.activation?.mode === "explicit") {
        const roots = generation.activation.roots ??= [];
        if (!roots.some((item) => item.kind === resource.kind && item.id === resource.id)) {
            roots.push({ kind: resource.kind, id: resource.id });
            changed = true;
        }
    } else if (resource.kind === "subject") {
        const subject = project.subjects?.find((item) => item.id === resource.id);
        if (subject && !(generation.subjectStates ?? []).some((item) => item.subjectId === resource.id)) {
            (generation.subjectStates ??= []).push({ subjectId: resource.id, policy: "explicit", stateId: subject.baseAppearanceStateId });
            changed = true;
        }
    } else if (resource.kind === "environment") {
        const environment = project.environments?.find((item) => item.id === resource.id);
        if (environment && !(generation.environmentStates ?? []).some((item) => item.environmentId === resource.id)) {
            (generation.environmentStates ??= []).push({ environmentId: resource.id, policy: "explicit", stateId: environment.defaultStateId, viewIds: [] });
            changed = true;
        }
    }
    return changed;
}

function addBinding(project, action) {
    const generation = project?.generations?.find((item) => item.id === action.generationId);
    const asset = project?.assets?.find((item) => item.id === action.assetId);
    if (!generation || !asset || Number(action.slotIndex) > SLOT_LIMITS[asset.type]
        || (generation.bindings ?? []).some((item) => item.assetId === action.assetId)) return false;
    const occupied = new Set((generation.bindings ?? []).flatMap((binding) => {
        const boundAsset = project.assets.find((item) => item.id === binding.assetId);
        return boundAsset?.type === asset.type ? [Number(binding.slotIndex)] : [];
    }));
    if (occupied.has(Number(action.slotIndex))) return false;
    const binding = { assetId: action.assetId, slotIndex: Number(action.slotIndex) };
    if (asset.type === "video" && ["paired", "alone"].includes(asset.audioMode)) {
        const occupiedAudio = new Set();
        for (const existing of generation.bindings ?? []) {
            const existingAsset = project.assets.find((item) => item.id === existing.assetId);
            if (existingAsset?.type === "audio") occupiedAudio.add(Number(existing.slotIndex));
            if (existingAsset?.type === "video" && existing.soundtrackSlotIndex) occupiedAudio.add(Number(existing.soundtrackSlotIndex));
        }
        const soundtrackSlot = [1, 2, 3].find((slot) => !occupiedAudio.has(slot));
        if (!soundtrackSlot) return false;
        binding.soundtrackSlotIndex = soundtrackSlot;
    }
    (generation.bindings ??= []).push(binding);
    return true;
}

function alignTransition(shotPlan, action) {
    const shot = shotPlan?.shots?.find((item) => item.id === action.shotId);
    if (!shot) return false;
    const transitions = action.entityKind === "subject" ? shot.appearanceTransitions : shot.environmentTransitions;
    const idKey = action.entityKind === "subject" ? "subjectId" : "environmentId";
    if (!Array.isArray(transitions)) return false;
    let changed = false;
    for (const transition of transitions) {
        if (transition[idKey] !== action.entityId || transition.fromStateId === action.stateId) continue;
        transition.fromStateId = action.stateId;
        changed = true;
    }
    return changed;
}

export function applySafeActionDocuments(action, { shotPlan = null, project = null, camera = {} } = {}) {
    const nextShotPlan = clone(shotPlan);
    const nextProject = clone(project);
    const cameraUpdates = {};
    let changed = false;
    if (action?.kind === "clear_shot_camera") {
        const shot = nextShotPlan?.shots?.find((item) => item.id === action.shotId);
        if (shot) changed = clearShotCamera(shot, action.aspects ?? []);
    } else if (action?.kind === "clear_global_camera") {
        for (const aspect of action.aspects ?? []) {
            for (const field of GLOBAL_CAMERA_FIELDS[aspect] ?? []) {
                const neutral = ["cameraAmplitude", "cameraSpeed"].includes(field) ? "auto" : "none";
                if ((camera[field] ?? neutral) !== neutral) {
                    cameraUpdates[field] = neutral;
                    changed = true;
                }
            }
        }
    } else if (action?.kind === "activate_resource") {
        changed = activateResource(nextProject, action);
    } else if (action?.kind === "add_binding") {
        changed = addBinding(nextProject, action);
    } else if (action?.kind === "align_transition_from_state") {
        changed = alignTransition(nextShotPlan, action);
    }
    return { changed, shotPlan: nextShotPlan, project: nextProject, cameraUpdates };
}
