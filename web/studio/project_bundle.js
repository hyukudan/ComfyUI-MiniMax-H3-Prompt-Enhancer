export const PROJECT_BUNDLE_FORMAT = "minimax-h3-prompt-studio";

const DOCUMENTS = Object.freeze({ shotPlan: 2, mediaProject: 2, creativeTreatment: 2, cinematography: 2 });
const isRecord = (value) => Boolean(value) && typeof value === "object" && !Array.isArray(value);

function idsAreValid(items, path, errors) {
    const ids = new Set();
    items.forEach((item, index) => {
        if (!isRecord(item)) return errors.push(`${path}[${index}] must be an object.`);
        if (typeof item.id !== "string" || !item.id.trim()) errors.push(`${path}[${index}].id must be a non-empty string.`);
        else if (ids.has(item.id)) errors.push(`${path} contains duplicate id “${item.id}”.`);
        else ids.add(item.id);
    });
}

export function validateProjectBundleDocuments(documents) {
    const errors = [];
    for (const [key, value] of Object.entries(documents ?? {})) {
        if (!(key in DOCUMENTS)) { errors.push(`Unknown package document: ${key}.`); continue; }
        if (!isRecord(value) || value.schemaVersion !== DOCUMENTS[key]) { errors.push(`${key} must use schema v${DOCUMENTS[key]}.`); continue; }
        if (key === "shotPlan") {
            if (!Array.isArray(value.shots)) errors.push("shotPlan.shots must be an array.");
            else {
                if (value.shots.length > 64) errors.push("shotPlan.shots cannot contain more than 64 shots.");
                idsAreValid(value.shots, "shotPlan.shots", errors);
                value.shots.forEach((shot, index) => {
                    if (!isRecord(shot)) return;
                    if (shot.generationId !== undefined && typeof shot.generationId !== "string") errors.push(`shotPlan.shots[${index}].generationId must be a string.`);
                    if (shot.action !== undefined && typeof shot.action !== "string") errors.push(`shotPlan.shots[${index}].action must be a string.`);
                    if (shot.durationSeconds !== undefined && (!Number.isFinite(shot.durationSeconds) || shot.durationSeconds <= 0 || shot.durationSeconds > 150)) errors.push(`shotPlan.shots[${index}].durationSeconds must be between 0 and 150.`);
                });
            }
            if (value.timingMode !== undefined && !["auto", "exact"].includes(value.timingMode)) errors.push("shotPlan.timingMode must be auto or exact.");
        } else if (key === "mediaProject") {
            for (const field of ["assets", "subjects", "environments", "generations"]) {
                if (!Array.isArray(value[field])) errors.push(`mediaProject.${field} must be an array.`);
                else idsAreValid(value[field], `mediaProject.${field}`, errors);
            }
            (Array.isArray(value.assets) ? value.assets : []).forEach((asset, index) => {
                if (isRecord(asset) && !["picture", "video", "audio"].includes(asset.type)) errors.push(`mediaProject.assets[${index}].type must be picture, video or audio.`);
            });
            (Array.isArray(value.generations) ? value.generations : []).forEach((generation, index) => {
                if (!isRecord(generation)) return;
                for (const field of ["bindings", "subjectStates", "environmentStates"]) if (!Array.isArray(generation[field])) errors.push(`mediaProject.generations[${index}].${field} must be an array.`);
            });
        } else {
            for (const [field, fieldValue] of Object.entries(value)) if (field !== "schemaVersion" && typeof fieldValue !== "string") errors.push(`${key}.${field} must be a string.`);
        }
    }
    if (!Object.keys(documents ?? {}).length) errors.push("The package contains no v2 documents.");
    return { ok: errors.length === 0, errors };
}

export function createProjectBundle(documents = {}) {
    const bundleDocuments = {};
    for (const key of Object.keys(DOCUMENTS)) {
        const state = documents[key];
        if (state?.kind === "v2" && isRecord(state.value)) bundleDocuments[key] = state.value;
    }
    return { format: PROJECT_BUNDLE_FORMAT, formatVersion: 1, documents: bundleDocuments };
}

export function parseProjectBundle(raw) {
    let value;
    try { value = typeof raw === "string" ? JSON.parse(raw) : raw; }
    catch { return { ok: false, message: "This is not valid JSON." }; }
    if (!isRecord(value) || value.format !== PROJECT_BUNDLE_FORMAT || value.formatVersion !== 1 || !isRecord(value.documents)) return { ok: false, message: "Choose a Prompt Studio v2 package." };
    const validation = validateProjectBundleDocuments(value.documents);
    if (!validation.ok) return { ok: false, message: validation.errors[0], errors: validation.errors };
    return { ok: true, documents: structuredClone(value.documents) };
}

export function summarizeProjectBundle(documents, current = {}) {
    const labels = { shotPlan: "Shot plan", mediaProject: "Media project", creativeTreatment: "Creative treatment", cinematography: "Cinematography" };
    return Object.entries(documents).map(([key, value]) => ({
        key, label: labels[key],
        change: JSON.stringify(current[key]?.value ?? current[key] ?? null) === JSON.stringify(value) ? "Unchanged" : "Replace",
        detail: key === "shotPlan" ? `${value.shots.length} shots` : key === "mediaProject" ? `${value.assets.length} media · ${value.subjects.length} subjects · ${value.environments.length} environments · ${value.generations.length} generations` : `${Math.max(0, Object.keys(value).length - 1)} settings`,
    }));
}

function uniqueId(preferred, used, prefix) {
    if (preferred && !used.has(preferred)) { used.add(preferred); return preferred; }
    let index = 1;
    while (used.has(`${prefix}${index}`)) index += 1;
    const result = `${prefix}${index}`; used.add(result); return result;
}

function appendUniqueResources(currentItems, incomingItems, label, errors) {
    const result = structuredClone(currentItems ?? []);
    const byId = new Map(result.map((item) => [item.id, item]));
    for (const item of incomingItems ?? []) {
        const existing = byId.get(item.id);
        if (!existing) { const copy = structuredClone(item); result.push(copy); byId.set(copy.id, copy); continue; }
        if (JSON.stringify(existing) !== JSON.stringify(item)) errors.push(`${label} id “${item.id}” already exists with different data.`);
    }
    return result;
}

export function appendProjectBundleGenerations(incoming, current = {}) {
    const sourceShot = incoming?.shotPlan;
    const sourceMedia = incoming?.mediaProject;
    const currentShot = current?.shotPlan?.value ?? current?.shotPlan;
    const currentMedia = current?.mediaProject?.value ?? current?.mediaProject;
    if (!isRecord(sourceShot) || !isRecord(sourceMedia)) return { ok: false, message: "Append requires both Shot plan and Media project documents." };
    if (!isRecord(currentShot) || currentShot.schemaVersion !== 2 || !isRecord(currentMedia) || currentMedia.schemaVersion !== 2) return { ok: false, message: "The current Shot plan and Media project must both be editable v2 documents." };
    if (sourceShot.timingMode !== currentShot.timingMode) return { ok: false, message: "Append requires the same shot timing mode as the current project." };
    if (!(sourceMedia.generations ?? []).length) return { ok: false, message: "The package has no generations to append." };
    const errors = [];
    const mediaProject = structuredClone(currentMedia);
    mediaProject.assets = appendUniqueResources(currentMedia.assets, sourceMedia.assets, "Asset", errors);
    mediaProject.subjects = appendUniqueResources(currentMedia.subjects, sourceMedia.subjects, "Subject", errors);
    mediaProject.environments = appendUniqueResources(currentMedia.environments, sourceMedia.environments, "Environment", errors);
    if (errors.length) return { ok: false, message: errors[0], errors };

    const generationIds = new Set((currentMedia.generations ?? []).map((item) => item.id));
    const generationMap = new Map();
    let order = Math.max(0, ...(currentMedia.generations ?? []).map((item) => Number(item.order) || 0));
    const appendedGenerations = (sourceMedia.generations ?? []).map((generation) => {
        const id = uniqueId(generation.id, generationIds, "g"); generationMap.set(generation.id, id); order += 1;
        return { ...structuredClone(generation), id, order };
    });
    mediaProject.generations = [...(mediaProject.generations ?? []), ...appendedGenerations];
    if (mediaProject.generations.length > 64) return { ok: false, message: "Append would exceed 64 generations." };
    if (mediaProject.generations.length > 1) mediaProject.mode = "chained_multishot";

    const shotIds = new Set((currentShot.shots ?? []).map((item) => item.id));
    const appendedShots = [];
    for (const shot of sourceShot.shots ?? []) {
        const generationId = generationMap.get(shot.generationId);
        if (!generationId) return { ok: false, message: `Shot “${shot.id}” refers to a generation not included in the package.` };
        appendedShots.push({ ...structuredClone(shot), id: uniqueId(shot.id, shotIds, "s"), generationId });
    }
    const shotPlan = { ...structuredClone(currentShot), shots: [...(currentShot.shots ?? []), ...appendedShots] };
    if (shotPlan.shots.length > 64) return { ok: false, message: "Append would exceed 64 shots." };
    return {
        ok: true,
        documents: { shotPlan, mediaProject },
        detail: `${appendedGenerations.length} generations · ${appendedShots.length} shots · ${(sourceMedia.assets ?? []).length} referenced media`,
    };
}

export function applyDocumentTransaction(entries, { read, write }) {
    const snapshots = new Map(entries.map(([key]) => [key, read(key)]));
    const written = [];
    try {
        for (const [key, value] of entries) {
            if (write(key, value) !== true) throw new Error(`Could not write ${key}.`);
            written.push(key);
        }
        return { ok: true };
    } catch (error) {
        const failed = [];
        for (const key of written.reverse()) {
            try { if (write(key, snapshots.get(key), { rollback: true }) !== true) failed.push(key); } catch { failed.push(key); }
        }
        return { ok: false, rolledBack: failed.length === 0, message: failed.length ? `Import failed; rollback also failed for ${failed.join(", ")}.` : String(error?.message ?? "Import failed.") };
    }
}
