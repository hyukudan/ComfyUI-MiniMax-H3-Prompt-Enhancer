function issue(severity, section, message, location = "") {
    return { severity, section, message, location };
}

function sourceIssue(documentState, label, section) {
    if (!["malformed", "future"].includes(documentState?.kind)) return null;
    return issue("error", section, `${label} cannot be used until its source is repaired.`, label);
}

function nonEmpty(value) {
    return typeof value === "string" && value.trim().length > 0;
}

function cameraPathIssues(shot) {
    const points = shot?.cameraPath?.waypoints;
    if (points === undefined) return [];
    if (!Array.isArray(points) || points.length < 2 || points.length > 6) {
        return [issue("error", "camera", "A spatial camera path needs between 2 and 6 positions.", shot.id)];
    }
    const timings = points.map((point) => Number(point?.at));
    if (timings.some((value) => !Number.isFinite(value) || value < 0 || value > 1)
        || timings.some((value, index) => index > 0 && value <= timings[index - 1])) {
        return [issue("error", "camera", "Camera positions need unique timings in playback order.", shot.id)];
    }
    return [];
}

export function localPreflight({ shotDocument, projectDocument } = {}) {
    const items = [];
    for (const candidate of [
        sourceIssue(shotDocument, "Shot plan", "shots"),
        sourceIssue(projectDocument, "Media project", "media"),
    ]) if (candidate) items.push(candidate);

    const shots = shotDocument?.kind === "v2" && Array.isArray(shotDocument.value?.shots)
        ? shotDocument.value.shots : [];
    const project = projectDocument?.kind === "v2" ? projectDocument.value : null;
    const generations = new Map((project?.generations ?? []).map((generation) => [generation.id, generation]));
    const assets = new Map((project?.assets ?? []).map((asset) => [asset.id, asset]));
    const subjects = project?.subjects ?? [];

    for (const shot of shots) {
        const label = shot?.id || "Shot";
        if (!nonEmpty(shot?.action)) items.push(issue("error", "shots", "Describe the visible action before generating.", label));
        if (project && !generations.has(shot?.generationId)) {
            items.push(issue("error", "shots", `Choose an existing generation for ${label}.`, label));
        }
        if (shot?.subjectPresenceComplete && subjects.some((subject) => !(shot.subjects ?? []).some((entry) => entry.subjectId === subject.id))) {
            items.push(issue("warning", "shots", "Full presence is enabled, but at least one subject has no presence state.", label));
        }
        for (const beat of shot?.actionBeats ?? []) {
            if (!nonEmpty(beat?.action) && !nonEmpty(beat?.dialogue)) {
                items.push(issue("warning", "shots", "An action beat is empty and will add no direction.", label));
                break;
            }
        }
        items.push(...cameraPathIssues(shot));
        for (const reference of shot?.referenceUses ?? []) {
            const asset = assets.get(reference?.assetId);
            if (!asset) {
                items.push(issue("error", "media", `A reference used by ${label} no longer exists.`, label));
                continue;
            }
            const generation = generations.get(shot?.generationId);
            if (generation && !(generation.bindings ?? []).some((binding) => binding.assetId === asset.id)) {
                items.push(issue("error", "media", `${asset.name || asset.id} is used by ${label} but has no file-slot assignment.`, label));
            }
        }
    }

    if (project) {
        for (const generation of project.generations ?? []) {
            for (const binding of generation.bindings ?? []) {
                if (!assets.has(binding?.assetId)) {
                    items.push(issue("error", "media", `Generation ${generation.order ?? generation.id} has an assignment for a missing reference.`, generation.id));
                }
            }
        }
    }

    const unique = [...new Map(items.map((item) => [
        [item.severity, item.section, item.location, item.message].join("|"), item,
    ])).values()];
    const errors = unique.filter((item) => item.severity === "error").length;
    const warnings = unique.filter((item) => item.severity === "warning").length;
    return {
        items: unique,
        errors,
        warnings,
        status: errors ? "blocked" : warnings ? "attention" : "ready",
        hasStructuredPlan: shots.length > 0 || Boolean(project),
    };
}
