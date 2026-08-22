const SOURCE_LABELS = Object.freeze({
    blank: "Empty",
    v1: "v1",
    v2: "v2",
    malformed: "Needs repair",
    future: "Read only",
});

export function normalizedSourceState(documentState) {
    return documentState && SOURCE_LABELS[documentState.kind]
        ? documentState
        : { kind: "blank", raw: "", version: null, value: null, errors: [], dirty: false };
}

export function sourceStateLabel(documentState) {
    const state = normalizedSourceState(documentState);
    if (state.kind === "future" && state.version) return `v${state.version} · read only`;
    return SOURCE_LABELS[state.kind];
}

export function validateStructuredRaw(raw, { acceptedVersions = [1] } = {}) {
    let parsed;
    try {
        parsed = JSON.parse(raw);
    } catch (error) {
        return { valid: false, error: String(error?.message ?? "Invalid JSON"), value: null };
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        return { valid: false, error: "Expected a JSON object.", value: null };
    }
    if (!acceptedVersions.includes(parsed.schemaVersion)) {
        return {
            valid: false,
            error: `Expected schemaVersion ${acceptedVersions.join(" or ")}.`,
            value: parsed,
        };
    }
    return { valid: true, error: "", value: parsed };
}

export function createSourcePill(name, documentState) {
    const state = normalizedSourceState(documentState);
    const pill = document.createElement("span");
    pill.className = "minimax-h3-source-pill";
    pill.dataset.kind = state.kind;
    const nameElement = document.createElement("span");
    nameElement.className = "minimax-h3-source-name";
    nameElement.textContent = name;
    const value = document.createElement("span");
    value.textContent = sourceStateLabel(state);
    pill.append(nameElement, value);
    return pill;
}

function sourceButton(label, className = "minimax-h3-button minimax-h3-button-secondary") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    return button;
}

function appendRawViewer(wrapper, state) {
    const disclosure = document.createElement("details");
    disclosure.className = "minimax-h3-source-raw";
    const summary = document.createElement("summary");
    summary.textContent = "View source";
    const raw = document.createElement("pre");
    raw.textContent = state.raw ?? "";
    disclosure.append(summary, raw);
    wrapper.appendChild(disclosure);
}

async function copyText(value) {
    if (!globalThis.navigator?.clipboard?.writeText) return false;
    await globalThis.navigator.clipboard.writeText(value);
    return true;
}

export function createSourceStateCard({
    name,
    documentState,
    acceptedVersions = [1],
    onApplyRaw = null,
    legacyDescription = "This source is preserved until you choose to update it.",
} = {}) {
    const state = normalizedSourceState(documentState);
    const card = document.createElement("section");
    card.className = "minimax-h3-source-card";
    card.dataset.kind = state.kind;
    const heading = document.createElement("h3");
    heading.textContent = name ?? "Structured source";
    card.appendChild(heading);

    if (state.kind === "v1") {
        const copy = document.createElement("p");
        copy.textContent = legacyDescription;
        card.appendChild(copy);
        return card;
    }

    if (state.kind === "future") {
        const copy = document.createElement("p");
        copy.textContent = `Created by a newer version (v${state.version ?? "?"}). It will be preserved without changes.`;
        const copyButton = sourceButton("Copy source");
        const status = document.createElement("span");
        status.className = "minimax-h3-source-copy-status";
        status.setAttribute("aria-live", "polite");
        copyButton.addEventListener("click", () => {
            copyText(state.raw ?? "").then((copied) => {
                status.textContent = copied ? "Copied" : "Clipboard unavailable";
            }).catch(() => { status.textContent = "Clipboard unavailable"; });
        });
        card.append(copy, copyButton, status);
        appendRawViewer(card, state);
        return card;
    }

    if (state.kind === "malformed") {
        const copy = document.createElement("p");
        copy.textContent = "The original value is intact. Repair the JSON below, then apply it when validation passes.";
        const editor = document.createElement("textarea");
        editor.className = "minimax-h3-source-editor";
        editor.value = state.raw ?? "";
        editor.spellcheck = false;
        editor.setAttribute("aria-label", `Repair ${name ?? "structured source"}`);
        const feedback = document.createElement("p");
        feedback.className = "minimax-h3-source-feedback";
        feedback.setAttribute("aria-live", "polite");
        const actions = document.createElement("div");
        actions.className = "minimax-h3-source-actions";
        const apply = sourceButton("Apply repaired source", "minimax-h3-button minimax-h3-button-primary");
        const copyButton = sourceButton("Copy source");
        const validate = () => {
            const result = validateStructuredRaw(editor.value, { acceptedVersions });
            editor.setAttribute("aria-invalid", String(!result.valid));
            feedback.dataset.valid = String(result.valid);
            feedback.textContent = result.valid ? "Valid JSON · ready to apply" : result.error;
            apply.disabled = !result.valid || !onApplyRaw;
        };
        editor.addEventListener("input", validate);
        apply.addEventListener("click", () => onApplyRaw?.(editor.value));
        copyButton.addEventListener("click", () => {
            copyText(editor.value).then((copied) => {
                feedback.textContent = copied ? "Copied" : "Clipboard unavailable";
            }).catch(() => { feedback.textContent = "Clipboard unavailable"; });
        });
        actions.append(apply, copyButton);
        card.append(copy, editor, feedback, actions);
        validate();
        return card;
    }

    const copy = document.createElement("p");
    copy.textContent = state.kind === "blank" ? "No structured data has been added yet." : "This source is ready.";
    card.appendChild(copy);
    if (state.kind === "v2") appendRawViewer(card, state);
    return card;
}
