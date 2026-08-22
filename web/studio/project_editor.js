import { emptyMediaProjectV2, normalizeMediaProjectV2, serializeStructuredJson } from "./schema.js";

export function editableProject(documentState) {
    if (documentState?.kind === "v2") return normalizeMediaProjectV2(documentState.value);
    if (documentState?.kind === "blank") return emptyMediaProjectV2();
    return null;
}

export function uniqueId(items, prefix) {
    const used = new Set(items.map((item) => item?.id));
    let index = items.length + 1;
    while (used.has(`${prefix}${index}`)) index += 1;
    return `${prefix}${index}`;
}

export function projectForController(controller) {
    const documentState = controller.projectDocument();
    const sourceRaw = documentState?.raw ?? "";
    if (controller.projectUiState.sourceRaw !== sourceRaw) {
        controller.projectUiState.sourceRaw = sourceRaw;
        controller.projectUiState.project = editableProject(documentState);
    }
    return controller.projectUiState.project;
}

export function commitProject(controller) {
    const project = controller.projectUiState.project;
    const raw = serializeStructuredJson(normalizeMediaProjectV2(project));
    const changed = controller.commitProject(raw);
    if (changed !== false) controller.projectUiState.sourceRaw = raw;
    return changed;
}

export function readOnlyProjectMessage(container, documentState, controller) {
    const message = document.createElement("div");
    message.className = "minimax-h3-studio-status";
    message.dataset.kind = documentState?.kind ?? "malformed";
    message.textContent = documentState?.kind === "v1"
        ? "This legacy media manifest is preserved unchanged. Prompt Studio editing requires Project v2."
        : `The raw media project is ${documentState?.kind ?? "unavailable"} and remains read-only.`;
    container.appendChild(message);
    if (documentState?.kind === "malformed") {
        const raw = document.createElement("textarea"); raw.value = documentState.raw; raw.setAttribute("aria-label", "Raw media manifest JSON");
        const apply = document.createElement("button"); apply.type = "button"; apply.textContent = "Parse and apply v2 JSON";
        apply.addEventListener("click", () => {
            const parsed = controllerSafeParse(raw.value);
            if (!parsed || parsed.schemaVersion !== 2) {
                raw.setAttribute("aria-invalid", "true"); return;
            }
            raw.removeAttribute("aria-invalid");
            controller.replaceProjectRaw(raw.value);
        });
        container.append(raw, apply);
    }
}

function controllerSafeParse(raw) {
    try { return JSON.parse(raw); } catch { return null; }
}

export function labeledInput(label, value, onChange, { multiline = false, type = "text" } = {}) {
    const wrapper = document.createElement("label");
    wrapper.className = "minimax-h3-studio-field";
    const title = document.createElement("span"); title.textContent = label;
    const control = document.createElement(multiline ? "textarea" : "input");
    if (!multiline) control.type = type;
    control.value = value ?? "";
    control.addEventListener(multiline ? "blur" : "change", () => onChange(control.value));
    wrapper.append(title, control);
    return wrapper;
}

export function labeledSelect(label, value, choices, onChange) {
    const wrapper = document.createElement("label"); wrapper.className = "minimax-h3-studio-field";
    const title = document.createElement("span"); title.textContent = label;
    const control = document.createElement("select");
    for (const [token, text] of choices) {
        const option = document.createElement("option"); option.value = token; option.textContent = text; control.appendChild(option);
    }
    control.value = value;
    control.addEventListener("change", () => onChange(control.value));
    wrapper.append(title, control);
    return wrapper;
}
