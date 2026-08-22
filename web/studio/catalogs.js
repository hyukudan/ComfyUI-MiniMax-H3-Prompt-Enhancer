export const CREATIVE_TREATMENT_WIDGET = "creative_treatment_json";
export const SHOT_PLAN_WIDGET = "shot_plan_json";
export const CINEMATOGRAPHY_WIDGET = "cinematography_json";
export const CREATIVE_PANEL_WIDGET = "MiniMax H3 creative direction";

export const STRUCTURED_SCHEMA_VERSIONS = Object.freeze({
    creativeTreatment: 2,
    shotPlan: 1,
    cinematography: 2,
});

function legacyScalarIsBlank(raw) {
    const normalized = String(raw ?? "").trim().toLocaleLowerCase();
    return normalized === "" || normalized === "false" || normalized === "true"
        || normalized === "null" || normalized === "none";
}

// Creative/Cinema alone may reinterpret legacy neutral storage as an editable
// blank draft. The returned view retains the exact raw bytes and source kind;
// hydration never mutates the underlying widget.
export function nativeStructuredDocumentView(documentState, neutralValues = {}) {
    if (!documentState || ["blank", "v2"].includes(documentState.kind)) return documentState;
    let semanticBlank = legacyScalarIsBlank(documentState.raw);
    if (!semanticBlank && documentState.kind === "v1") {
        semanticBlank = Object.entries(neutralValues).every(([field, neutral]) => {
            const value = documentState.value?.[field];
            return value === undefined || value === null || value === "" || value === neutral;
        });
    }
    if (!semanticBlank) return documentState;
    return {
        ...documentState,
        kind: "blank",
        value: null,
        version: null,
        semanticBlank: true,
        sourceKind: documentState.kind,
    };
}
