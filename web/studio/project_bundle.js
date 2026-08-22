export const PROJECT_BUNDLE_FORMAT = "minimax-h3-prompt-studio";

const DOCUMENTS = Object.freeze({
    shotPlan: 2,
    mediaProject: 2,
    creativeTreatment: 2,
    cinematography: 2,
});

export function createProjectBundle(documents = {}) {
    const bundleDocuments = {};
    for (const key of Object.keys(DOCUMENTS)) {
        const documentState = documents[key];
        if (documentState?.kind === "v2" && documentState.value && typeof documentState.value === "object") {
            bundleDocuments[key] = documentState.value;
        }
    }
    return {
        format: PROJECT_BUNDLE_FORMAT,
        formatVersion: 1,
        documents: bundleDocuments,
    };
}

export function parseProjectBundle(raw) {
    let value;
    try {
        value = typeof raw === "string" ? JSON.parse(raw) : raw;
    } catch {
        return { ok: false, message: "This is not valid JSON." };
    }
    if (!value || typeof value !== "object" || Array.isArray(value)
        || value.format !== PROJECT_BUNDLE_FORMAT || value.formatVersion !== 1
        || !value.documents || typeof value.documents !== "object" || Array.isArray(value.documents)) {
        return { ok: false, message: "Choose a Prompt Studio v2 package." };
    }
    const documents = {};
    for (const [key, documentValue] of Object.entries(value.documents)) {
        if (!(key in DOCUMENTS)) return { ok: false, message: `Unknown package document: ${key}.` };
        if (!documentValue || typeof documentValue !== "object" || Array.isArray(documentValue)
            || Number(documentValue.schemaVersion) !== DOCUMENTS[key]) {
            return { ok: false, message: `${key} must use schema v${DOCUMENTS[key]}.` };
        }
        documents[key] = documentValue;
    }
    if (!Object.keys(documents).length) return { ok: false, message: "The package contains no v2 documents." };
    return { ok: true, documents };
}
