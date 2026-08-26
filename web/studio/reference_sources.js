export const REFERENCE_DIRECTOR_FORMAT = "minimax-h3-reference-director";
export const REFERENCE_DIRECTOR_VERSION = 1;
export const REFERENCE_DIRECTOR_WIDGET = "reference_director_json";

export function emptyReferenceDirector() {
    return { format: REFERENCE_DIRECTOR_FORMAT, formatVersion: REFERENCE_DIRECTOR_VERSION, sources: {} };
}

export function parseReferenceDirector(raw = "") {
    if (raw === null || raw === undefined || String(raw).trim() === "") return { kind: "v1", value: emptyReferenceDirector(), issues: [] };
    let value;
    try { value = typeof raw === "string" ? JSON.parse(raw) : raw; }
    catch { return { kind: "malformed", value: null, issues: ["Reference Director storage is not valid JSON."] }; }
    if (!value || typeof value !== "object" || Array.isArray(value)) return { kind: "malformed", value: null, issues: ["Reference Director storage must be an object."] };
    if (value.format !== REFERENCE_DIRECTOR_FORMAT || value.formatVersion !== REFERENCE_DIRECTOR_VERSION || !value.sources || typeof value.sources !== "object" || Array.isArray(value.sources)) {
        return { kind: "unsupported", value: null, issues: ["This Reference Director document is not supported."] };
    }
    return { kind: "v1", value: structuredClone(value), issues: [] };
}

export function sourcePreviewUrl(source = {}) {
    const annotated = String(source?.file ?? "");
    const suffix = " [input]";
    if (!annotated.endsWith(suffix)) return "";
    const relative = annotated.slice(0, -suffix.length).replaceAll("\\", "/");
    const slash = relative.lastIndexOf("/");
    const filename = slash >= 0 ? relative.slice(slash + 1) : relative;
    const subfolder = slash >= 0 ? relative.slice(0, slash) : "";
    if (!filename || relative.includes("../") || relative.startsWith("/")) return "";
    const parameters = new URLSearchParams({ filename, type: "input" });
    if (subfolder) parameters.set("subfolder", subfolder);
    return `/view?${parameters.toString()}`;
}

export function referenceSourceForAsset(director, assetId) {
    return director?.sources?.[assetId] ?? null;
}

export function setReferenceSource(director, assetId, source) {
    const next = structuredClone(director ?? emptyReferenceDirector());
    next.sources ??= {};
    next.sources[assetId] = structuredClone(source);
    return next;
}

export function removeReferenceSource(director, assetId) {
    const next = structuredClone(director ?? emptyReferenceDirector());
    if (next.sources) delete next.sources[assetId];
    return next;
}

export function mediaTypeForFile(file) {
    const mime = String(file?.type ?? "").toLowerCase();
    if (mime.startsWith("image/")) return "picture";
    if (mime.startsWith("video/")) return "video";
    if (mime.startsWith("audio/")) return "audio";
    const extension = String(file?.name ?? "").toLowerCase().split(".").pop();
    if (["avif", "bmp", "gif", "jpeg", "jpg", "png", "webp"].includes(extension)) return "picture";
    if (["avi", "mkv", "mov", "mp4", "webm"].includes(extension)) return "video";
    if (["aac", "flac", "m4a", "mp3", "ogg", "wav"].includes(extension)) return "audio";
    return "";
}
