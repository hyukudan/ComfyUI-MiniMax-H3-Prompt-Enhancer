export const STRUCTURED_JSON_KINDS = Object.freeze([
    "blank",
    "v1",
    "v2",
    "malformed",
    "future",
]);

function rawJsonValue(value) {
    if (typeof value === "string") return value;
    if (value === undefined || value === null) return "";
    return JSON.stringify(value);
}

export function parseStructuredJson(value, {
    supportedVersions = [1],
    allowLegacyBlankScalars = false,
} = {}) {
    const raw = rawJsonValue(value);
    if (!raw.trim()) {
        return { kind: "blank", raw, version: null, value: null, errors: [], dirty: false };
    }

    let parsed;
    try {
        parsed = JSON.parse(raw);
    } catch (error) {
        return {
            kind: "malformed",
            raw,
            version: null,
            value: null,
            errors: [String(error?.message ?? "Invalid JSON")],
            dirty: false,
        };
    }
    // Very old workflows could serialize the former Shot Plan enable/button
    // widget into this storage slot. Both boolean values therefore mean
    // "there is no structured plan" for callers that explicitly opt into the
    // compatibility path. Numeric/string scalars remain invalid.
    if (allowLegacyBlankScalars && (typeof parsed === "boolean" || parsed === null)) {
        return { kind: "blank", raw, version: null, value: null, errors: [], dirty: false };
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        return {
            kind: "malformed",
            raw,
            version: null,
            value: null,
            errors: ["Expected a JSON object."],
            dirty: false,
        };
    }

    const version = parsed.schemaVersion;
    if (!Number.isInteger(version) || version < 1) {
        return {
            kind: "malformed",
            raw,
            version: null,
            value: null,
            errors: ["schemaVersion must be a positive integer."],
            dirty: false,
        };
    }
    const supported = [...supportedVersions].sort((left, right) => left - right);
    const maximum = supported.at(-1) ?? 0;
    if (!supported.includes(version)) {
        return {
            kind: "future",
            raw,
            version,
            value: parsed,
            errors: [version > maximum
                ? `Schema version ${version} is newer than this editor supports.`
                : `Schema version ${version} is not supported by this editor.`],
            dirty: false,
        };
    }
    return {
        kind: version === 1 ? "v1" : "v2",
        raw,
        version,
        value: parsed,
        errors: [],
        dirty: false,
    };
}

export function structuredJsonIsEditable(document) {
    return document?.kind === "blank" || document?.kind === "v1" || document?.kind === "v2";
}

export function serializeStructuredJson(value) {
    return JSON.stringify(value);
}

const SHOT_TEXT_LIMIT = 8000;

function cleanText(value, maximum = SHOT_TEXT_LIMIT) {
    return typeof value === "string" ? value.replaceAll("\0", "").slice(0, maximum) : "";
}

function copyKnown(source, keys) {
    const result = {};
    for (const key of keys) {
        if (source?.[key] !== undefined) result[key] = structuredClone(source[key]);
    }
    return result;
}

export function emptyShotPlanV2() {
    return { schemaVersion: 2, timingMode: "auto", shots: [] };
}

export function migrateShotPlanV1(value) {
    const timingMode = value?.timingMode === "exact" ? "exact" : "auto";
    return {
        schemaVersion: 2,
        timingMode,
        shots: (Array.isArray(value?.shots) ? value.shots : []).slice(0, 64).map((shot, index) => {
            const migrated = {
                id: cleanText(shot?.id, 64) || `s${index + 1}`,
                generationId: "g1",
                action: cleanText(shot?.description),
            };
            if (timingMode === "exact" && Number(shot?.durationSeconds) > 0) {
                migrated.durationSeconds = Number(shot.durationSeconds);
            }
            if (shot?.transitionIn && shot.transitionIn !== "cut") migrated.transitionIn = shot.transitionIn;
            const cameraStart = {};
            if (shot?.shotScale && shot.shotScale !== "none") cameraStart.framing = shot.shotScale;
            if (shot?.cameraAngle && shot.cameraAngle !== "none") cameraStart.angle = shot.cameraAngle;
            if (Object.keys(cameraStart).length) migrated.cameraStart = cameraStart;
            if (shot?.cameraMotion && shot.cameraMotion !== "none") {
                migrated.cameraPath = { motionType: shot.cameraMotion };
                if (shot.cameraAmplitude && shot.cameraAmplitude !== "auto") {
                    migrated.cameraPath.amplitude = shot.cameraAmplitude;
                }
                if (shot.cameraSpeed && shot.cameraSpeed !== "auto") migrated.cameraPath.speed = shot.cameraSpeed;
            }
            return migrated;
        }),
    };
}

export function normalizeShotPlanV2(value) {
    const timingMode = value?.timingMode === "exact" ? "exact" : "auto";
    const shots = (Array.isArray(value?.shots) ? value.shots : []).slice(0, 64).map((source, index) => {
        const shot = {
            id: cleanText(source?.id, 64) || `s${index + 1}`,
            generationId: cleanText(source?.generationId, 64) || "g1",
            action: cleanText(source?.action),
        };
        const openingState = cleanText(source?.openingState);
        if (openingState) shot.openingState = openingState;
        if (timingMode === "exact" && Number(source?.durationSeconds) > 0) {
            shot.durationSeconds = Math.min(150, Number(source.durationSeconds));
        }
        Object.assign(shot, copyKnown(source, [
            "transitionIn", "cutContext", "subjectPresenceComplete", "subjects", "environment",
            "referenceUses", "cameraStart", "cameraEnd", "cameraPath", "appearanceTransitions",
            "environmentTransitions", "actionBeats",
            "scaleRelationships",
        ]));
        if (shot.cameraEnd && !Object.keys(shot.cameraEnd).length) delete shot.cameraEnd;
        if (shot.cameraStart && !Object.keys(shot.cameraStart).length) delete shot.cameraStart;
        if (shot.cameraPath && !Object.keys(shot.cameraPath).length) delete shot.cameraPath;
        return shot;
    });
    return { schemaVersion: 2, timingMode, shots };
}

export function editableShotPlan(document) {
    if (document?.kind === "v2") return normalizeShotPlanV2(document.value);
    if (document?.kind === "v1") return migrateShotPlanV1(document.value);
    if (document?.kind === "blank") return emptyShotPlanV2();
    return null;
}

export function parseMediaProject(value) {
    const raw = rawJsonValue(value);
    if (!raw.trim()) return { kind: "blank", raw, version: null, value: null, errors: [], dirty: false };
    let parsed;
    try {
        parsed = JSON.parse(raw);
    } catch (error) {
        return {
            kind: "malformed", raw, version: null, value: null,
            errors: [String(error?.message ?? "Invalid JSON")], dirty: false,
        };
    }
    if (Array.isArray(parsed) || (parsed && typeof parsed === "object" && parsed.schemaVersion === undefined)) {
        return { kind: "v1", raw, version: 1, value: parsed, errors: [], dirty: false };
    }
    return parseStructuredJson(raw, { supportedVersions: [2] });
}

export function emptyMediaProjectV2() {
    return {
        schemaVersion: 2,
        mode: "auto",
        assets: [],
        subjects: [],
        environments: [],
        generations: [{
            id: "g1", order: 1, activation: { mode: "auto" }, bindings: [],
            subjectStates: [], environmentStates: [],
        }],
    };
}

export function normalizeMediaProjectV2(value) {
    const project = emptyMediaProjectV2();
    project.mode = typeof value?.mode === "string" ? value.mode : "auto";
    for (const key of ["assets", "subjects", "environments", "generations"]) {
        if (Array.isArray(value?.[key])) project[key] = structuredClone(value[key]);
    }
    if (!project.generations.length) project.generations = emptyMediaProjectV2().generations;
    return project;
}

export function migrateMediaManifestV1(value) {
    const source = Array.isArray(value) ? { items: value } : (value ?? {});
    const rawItems = source.items ?? source.assets ?? source.media ?? [];
    const counters = { picture: 0, video: 0, audio: 0 };
    const labelToAsset = new Map();
    const assets = [];
    const bindings = [];
    for (const raw of Array.isArray(rawItems) ? rawItems : []) {
        if (!raw || typeof raw !== "object" || raw.enabled === false) continue;
        let type = String(raw.type ?? raw.kind ?? "").toLowerCase();
        if (type === "image") type = "picture";
        if (!(type in counters)) continue;
        counters[type] += 1;
        const asset = {
            id: `asset.${type}.${counters[type]}`,
            type,
            name: cleanText(raw.name ?? raw.label, 500) || `${type} ${counters[type]}`,
            available: true,
        };
        const description = cleanText(raw.description ?? raw.analysis);
        if (description) asset.description = description;
        const duration = Number(raw.durationSeconds ?? raw.duration_seconds ?? raw.duration ?? 0);
        if (duration > 0 && ["video", "audio"].includes(type)) asset.durationSeconds = duration;
        const binding = { assetId: asset.id, slotIndex: counters[type] };
        if (type === "video") {
            const audioMode = String(raw.audioMode ?? raw.audio_mode ?? "off").toLowerCase();
            asset.audioMode = ["paired", "alone"].includes(audioMode) ? audioMode : "off";
            if (asset.audioMode !== "off") {
                counters.audio += 1;
                binding.soundtrackSlotIndex = counters.audio;
            }
        }
        const label = `<${type[0].toUpperCase()}${type.slice(1)} ${binding.slotIndex}>`;
        labelToAsset.set(label, asset.id);
        assets.push(asset); bindings.push(binding);
    }
    const subjects = [];
    for (const [index, raw] of (Array.isArray(source.subjects) ? source.subjects : []).entries()) {
        if (!raw || typeof raw !== "object") continue;
        const numeric = Number(String(raw.id ?? raw.subject_id ?? index + 1).match(/\d+/)?.[0] ?? index + 1);
        const sources = Array.isArray(raw.sources) ? raw.sources : [raw.sources ?? raw.source].filter(Boolean);
        const identityAssetIds = sources.map((label) => labelToAsset.get(String(label))).filter((id) => assets.find((asset) => asset.id === id)?.type === "picture");
        subjects.push({
            id: `subject.${numeric}`, h3Index: numeric, name: cleanText(raw.name, 500) || `Subject ${numeric}`,
            description: cleanText(raw.description ?? raw.analysis),
            identityAssetIds, baseAppearanceStateId: "base",
            appearanceStates: [{ id: "base", name: "Base", controls: [], attributes: {} }],
        });
    }
    return {
        schemaVersion: 2,
        mode: cleanText(source.mode, 64) || "auto",
        assets,
        subjects,
        environments: [],
        generations: [{
            id: "g1", order: 1, activation: { mode: "auto" }, bindings,
            subjectStates: subjects.map((subject) => ({ subjectId: subject.id, policy: "explicit", stateId: "base" })),
            environmentStates: [],
        }],
    };
}
