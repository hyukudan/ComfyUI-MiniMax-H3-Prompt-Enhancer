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
