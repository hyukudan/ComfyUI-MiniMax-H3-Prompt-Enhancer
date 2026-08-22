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

export function actionBeatIssues(shot) {
    const items = [];
    const beats = Array.isArray(shot?.actionBeats) ? shot.actionBeats : [];
    let previousEnd = 0;
    let everyBeatHasSpan = beats.length > 0;
    for (const [index, beat] of beats.entries()) {
        const start = Number(beat?.at);
        const end = beat?.endAt === undefined ? null : Number(beat.endAt);
        if (!Number.isFinite(start)) { everyBeatHasSpan = false; continue; }
        if (start < 0 || start > 1 || (end !== null && (!Number.isFinite(end) || end <= start || end > 1))) {
            items.push(issue("error", "shots", `Beat ${index + 1} needs a valid start and an end after it.`, shot?.id));
            continue;
        }
        if (end === null) everyBeatHasSpan = false;
        if (end !== null && start < previousEnd) items.push(issue("warning", "shots", `Beat ${index + 1} overlaps the previous reserved span.`, shot?.id));
        previousEnd = Math.max(previousEnd, end ?? start);
        const words = String(beat?.dialogue?.text ?? "").trim().split(/\s+/u).filter(Boolean).length;
        if (words && end !== null && Number(shot?.durationSeconds) > 0) {
            const available = (end - start) * Number(shot.durationSeconds);
            const estimate = words / 2.5;
            if (estimate > available) items.push(issue("warning", "shots", `Beat ${index + 1} reserves about ${available.toFixed(1)}s for roughly ${estimate.toFixed(1)}s of dialogue at 150 wpm.`, shot?.id));
        }
    }
    if (everyBeatHasSpan && beats.length > 1) {
        for (let index = 1; index < beats.length; index += 1) {
            const gap = Number(beats[index].at) - Number(beats[index - 1].endAt);
            if (gap > .15) items.push(issue("info", "shots", `There is an unassigned ${Math.round(gap * 100)}% gap before Beat ${index + 1}.`, shot?.id));
        }
    }
    return items;
}

export function localPreflight({ shotDocument, projectDocument, basicPrompt = "" } = {}) {
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

    for (const subject of subjects) {
        if (!nonEmpty(subject?.description) || subject.description === "Describe the stable identity.") {
            items.push(issue("error", "subjects", "Describe the stable identity before generating.", subject?.id || "Subject"));
        }
        const explicitlyIncluded = (project?.generations ?? []).some((generation) =>
            (generation.activation?.roots ?? []).some((root) => root.kind === "subject" && root.id === subject.id));
        const usedByShot = shots.some((shot) =>
            (shot.subjects ?? []).some((entry) => entry.subjectId === subject.id && entry.presence !== "absent")
            || (shot.appearanceTransitions ?? []).some((entry) => entry.subjectId === subject.id));
        if (!explicitlyIncluded && !usedByShot) {
            items.push(issue(
                "warning", "subjects",
                `${subject.name || subject.id} is saved in the identity library but is not used by any generation or shot, so it will not reach the LLM.`,
                subject.id,
            ));
        }
    }

    for (const shot of shots) {
        const label = shot?.id || "Shot";
        if (!nonEmpty(shot?.action)) {
            if (shots.length === 1 && nonEmpty(basicPrompt)) {
                items.push(issue("info", "shots", "This single Shot inherits its Action from the Basic prompt.", label));
            } else {
                items.push(issue("error", "shots", "Describe the visible action before generating.", label));
            }
        }
        if (project && !generations.has(shot?.generationId)) {
            items.push(issue("error", "shots", `Choose an existing generation for ${label}.`, label));
        }
        if (shot?.subjectPresenceComplete && subjects.some((subject) => !(shot.subjects ?? []).some((entry) => entry.subjectId === subject.id))) {
            items.push(issue("warning", "shots", "Full presence is enabled, but at least one subject has no presence state.", label));
        }
        for (const beat of shot?.actionBeats ?? []) {
            if (beat?.dialogue && !nonEmpty(beat.dialogue.text)) {
                items.push(issue("error", "shots", "Add the exact spoken words or turn dialogue off for this beat.", label));
            }
            if (!nonEmpty(beat?.action) && !nonEmpty(beat?.dialogue?.text)) {
                items.push(issue("warning", "shots", "An action beat is empty and will add no direction.", label));
                break;
            }
        }
        for (const relationship of shot?.scaleRelationships ?? []) {
            if (relationship?.relation === "custom" && !nonEmpty(relationship.note)) {
                items.push(issue("error", "shots", "Describe the custom visible scale relationship.", label));
            }
        }
        items.push(...actionBeatIssues(shot));
        items.push(...cameraPathIssues(shot));
        const hasDialogue = (shot?.actionBeats ?? []).some((beat) => nonEmpty(beat?.dialogue?.text));
        if (!hasDialogue && (shot?.referenceUses ?? []).some((reference) => ["voice", "exact_dialogue"].includes(reference?.role))) {
            items.push(issue("warning", "media", "A voice or exact-dialogue reference is assigned to a shot with no authored dialogue beat.", label));
        }
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
