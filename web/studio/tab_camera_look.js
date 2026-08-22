import {
    visualLanguageHierarchy,
    visualLanguagePreview,
    visualLanguageSearchText,
} from "./visual_language_catalog.js";
import { MOOD_GUARDRAIL, moodChoiceGroups } from "./mood_catalog.js";

const CAMERA_GROUPS = [
    ["Image", ["colorPalette", "exposureContrast", "imageTexture", "lensEffects"]],
    ["Framing", ["shotScale", "cameraAngle", "cameraViewpoint"]],
    ["Motion", ["cameraMotion", "cameraAmplitude", "cameraSpeed", "motionRendering"]],
    ["Optics & focus", ["optics", "depthOfField"]],
];

const SHOT_OVERRIDE_PATHS = {
    shotScale: [["cameraStart", "framing"], ["cameraEnd", "framing"]],
    cameraAngle: [["cameraStart", "angle"], ["cameraEnd", "angle"]],
    cameraViewpoint: [["cameraStart", "viewpoint"], ["cameraEnd", "viewpoint"]],
    cameraMotion: [["cameraPath", "motionType"]],
    cameraAmplitude: [["cameraPath", "amplitude"]],
    cameraSpeed: [["cameraPath", "speed"]],
    optics: [["cameraStart", "lens"], ["cameraEnd", "lens"]],
    depthOfField: [["cameraStart", "focus"], ["cameraEnd", "focus"]],
};

const CAMERA_FIELD_ASPECT = {
    shotScale: "framing",
    cameraAngle: "angle",
    cameraViewpoint: "viewpoint",
    cameraMotion: "motion",
    cameraAmplitude: "motion",
    cameraSpeed: "motion",
    optics: "lens",
    depthOfField: "focus",
};

let visualLanguageId = 0;
let moodId = 0;
const VISUAL_LANGUAGE_POPOVER_TOKENS = Object.freeze([
    "--h3-accent", "--h3-border", "--h3-border-strong", "--h3-button-text", "--h3-font",
    "--h3-input-bg", "--h3-radius-md", "--h3-space-1", "--h3-space-2", "--h3-surface",
    "--h3-surface-raised", "--h3-text", "--h3-text-muted",
]);

function normalizedSearchText(value) {
    return String(value ?? "")
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[_-]+/g, " ")
        .toLocaleLowerCase();
}

export function filterVisualLanguageChoices(choices, groups, query = "") {
    const terms = normalizedSearchText(query).trim().split(/\s+/).filter(Boolean);
    const groupForValue = new Map((groups ?? []).flatMap(([group, entries]) => (
        (entries ?? []).map(([value]) => [value, group])
    )));
    const orderedGroups = ["", ...(groups ?? []).map(([group]) => group), "Other"];
    const results = new Map(orderedGroups.map((group) => [group, []]));
    for (const [value, label] of choices ?? []) {
        const group = value === "none" ? "" : (groupForValue.get(value) ?? "Other");
        const searchable = normalizedSearchText(`${visualLanguageSearchText(value, label)} ${group}`);
        if (terms.every((term) => searchable.includes(term))) results.get(group).push([value, label]);
    }
    return orderedGroups
        .map((group) => ({ group, choices: results.get(group) }))
        .filter(({ choices: entries }) => entries.length);
}

function hasPath(object, path) {
    let value = object;
    for (const key of path) value = value?.[key];
    return value !== undefined && value !== null && value !== "";
}

export function cameraOverrideRows(shotPlan, fields, project = null) {
    const assets = new Map((project?.assets ?? []).map((asset) => [asset.id, asset]));
    return (fields ?? []).map(([key, label]) => ({
        key,
        label,
        shotIds: (shotPlan?.shots ?? []).filter((shot) => (SHOT_OVERRIDE_PATHS[key] ?? []).some((path) => hasPath(shot, path))).map((shot) => shot.id),
        mediaOwners: (shotPlan?.shots ?? []).flatMap((shot) => (shot.referenceUses ?? []).flatMap((use) => {
            const asset = assets.get(use.assetId);
            const aspect = CAMERA_FIELD_ASPECT[key];
            if (use.role !== "camera_transfer" || !asset?.cameraTransfer?.enabled || !aspect) return [];
            const requested = use.cameraAspects ?? [];
            const declared = asset.cameraTransfer.aspects ?? [];
            return requested.includes(aspect) && declared.includes(aspect)
                ? [{ shotId: shot.id, assetId: asset.id, assetName: asset.name }]
                : [];
        })),
    }));
}

function block(title, summary = "") {
    const details = document.createElement("details");
    details.className = "minimax-h3-inspector-block";
    details.open = true;
    const heading = document.createElement("summary");
    heading.textContent = summary ? `${title} · ${summary}` : title;
    const body = document.createElement("div");
    body.className = "minimax-h3-studio-editor";
    details.append(heading, body);
    return { details, body };
}

function button(label, action) {
    const control = document.createElement("button");
    control.type = "button";
    control.textContent = label;
    control.addEventListener("click", action);
    return control;
}

export function renderCameraLookTab(container, controller) {
    container.replaceChildren();
    const sourceTools = [];
    const intro = document.createElement("p");
    intro.className = "minimax-h3-studio-status";
    intro.textContent = "Global camera values are calm defaults. A shot or an explicit camera-reference video may own an aspect without creating a conflict.";
    container.appendChild(intro);

    const creativeDocument = controller.creativeDocument();
    const cameraDocument = controller.cinematographyDocument();
    const lookTargetsEditable = [creativeDocument?.kind, cameraDocument?.kind].every((kind) => ["blank", "v2"].includes(kind));
    const creative = block("Creative direction", "story-independent visual language");
    creative.details.className += " minimax-h3-look-block minimax-h3-look-creative";
    if (["blank", "v2"].includes(creativeDocument.kind)) {
        const toolbar = document.createElement("div");
        toolbar.className = "minimax-h3-studio-toolbar";
        toolbar.className += " minimax-h3-look-intro-toolbar";
        const help = document.createElement("span");
        help.textContent = "Format, genre, visual language, world, scene-wide mood and title styling";
        const explore = button("Explore", () => {
            controller.exploreLook?.(false);
            renderCameraLookTab(container, controller);
        });
        explore.disabled = !lookTargetsEditable;
        explore.title = "Try a catalog-valid creative direction and color palette. Shift is available on the node API for full cinematography.";
        toolbar.append(help, explore);
        creative.body.appendChild(toolbar);
        const fields = controller.creativeFields();
        const guided = (controller.studioDetailMode ?? "guided") !== "advanced";
        const advancedKeys = new Set(["contentFormat", "titleScreenStyle", "animationCadence"]);
        const renderFields = (definitions) => {
            const grid = document.createElement("div");
            grid.className = "minimax-h3-studio-columns";
            for (const [key, label, choices, title] of definitions) {
                const control = key === "visualLanguage"
                    ? visualLanguageField(
                        label,
                        controller.creativeValue(key),
                        choices,
                        controller.visualLanguageGroups?.() ?? [],
                        (value) => controller.commitCreative(key, value),
                    )
                    : key === "tone"
                        ? moodField(label, controller.creativeValue(key), choices, (value) => controller.commitCreative(key, value))
                        : choiceField(label, controller.creativeValue(key), choices, (value) => controller.commitCreative(key, value), false, title);
                if (key === "animationCadence") {
                    const wrapper = document.createElement("div");
                    wrapper.className = "minimax-h3-cadence-field";
                    const hint = document.createElement("p");
                    hint.className = "minimax-h3-field-hint";
                    const requested = controller.creativeValue(key) !== "adaptive";
                    const compatible = controller.animationCadenceCompatible?.() ?? false;
                    hint.dataset.status = requested && !compatible ? "inactive" : "experimental";
                    hint.textContent = requested && !compatible
                        ? "Inactive for the current visual language. The value is preserved, but no cadence prose will be emitted. FPS and duration remain unchanged."
                        : "Experimental request for compatible drawn, pixel, stop-motion or marionette styles. It changes neither FPS nor duration, and H3 adherence is not guaranteed.";
                    wrapper.append(control, hint);
                    grid.appendChild(wrapper);
                } else grid.appendChild(control);
            }
            return grid;
        };
        if (!guided) creative.body.appendChild(renderFields(fields));
        else {
            creative.body.appendChild(renderFields(fields.filter(([key]) => !advancedKeys.has(key))));
            const advancedFields = fields.filter(([key]) => advancedKeys.has(key));
            if (advancedFields.length) {
                const active = advancedFields.filter(([key]) => {
                    const value = controller.creativeValue(key);
                    return key === "animationCadence" ? value !== "adaptive" : !["", "none", null, undefined].includes(value);
                }).length;
                const disclosure = document.createElement("details");
                disclosure.className = "minimax-h3-progressive-disclosure";
                disclosure.open = active > 0;
                const summary = document.createElement("summary");
                summary.textContent = `Advanced creative options · ${active ? `${active} active` : "defaults"}`;
                const note = document.createElement("p");
                note.className = "minimax-h3-field-hint";
                note.textContent = "Content format, title treatment and experimental animation cadence stay stored when this section is collapsed.";
                disclosure.append(summary, note, renderFields(advancedFields));
                creative.body.appendChild(disclosure);
            }
        }
    } else {
        creative.body.appendChild(unavailableState("Creative direction", creativeDocument));
        sourceTools.push(rawStatus("creative_treatment_json", creativeDocument, controller));
    }
    container.appendChild(creative.details);

    const camera = block("Global camera", "shot values take precedence");
    camera.details.className += " minimax-h3-look-block minimax-h3-look-camera";
    if (["blank", "v2"].includes(cameraDocument.kind)) {
        const fields = new Map(controller.cameraFields().map((field) => [field[0], field]));
        for (const [groupLabel, keys] of CAMERA_GROUPS) {
            const group = document.createElement("section");
            group.className = "minimax-h3-camera-group";
            const heading = document.createElement("h4");
            heading.textContent = groupLabel;
            const grid = document.createElement("div");
            grid.className = "minimax-h3-studio-columns";
            for (const key of keys) {
                const field = fields.get(key);
                if (!field) continue;
                const disabled = ["cameraAmplitude", "cameraSpeed"].includes(key) && ["none", "static"].includes(controller.cameraValue("cameraMotion"));
                grid.appendChild(choiceField(field[1], controller.cameraValue(key), field[2], (value) => {
                    controller.commitCamera(key, value);
                    renderCameraLookTab(container, controller);
                }, disabled, disabled ? "Choose a moving camera motion first." : ""));
            }
            group.append(heading, grid);
            camera.body.appendChild(group);
        }
    } else {
        camera.body.appendChild(unavailableState("Global camera", cameraDocument));
        sourceTools.push(rawStatus("cinematography_json", cameraDocument, controller));
    }
    container.appendChild(camera.details);

    const looks = block("Looks", `${controller.lookNames?.().length ?? 0} saved in this browser`);
    looks.details.className += " minimax-h3-look-block minimax-h3-look-library";
    const lookState = controller.lookUiState ??= {
        selectedName: "",
        nameDraft: "",
        transferMode: "",
        transferText: "",
        status: "",
        statusKind: "info",
    };
    const lookRow = document.createElement("div");
    lookRow.className = "minimax-h3-look-row minimax-h3-look-row-library";
    const names = controller.lookNames?.() ?? [];
    const selectField = document.createElement("label");
    selectField.className = "minimax-h3-studio-field";
    const selectLabel = document.createElement("span"); selectLabel.textContent = "Saved look";
    const select = document.createElement("select");
    for (const name of names.length ? names : [""]) {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name || "No saved looks yet";
        select.appendChild(option);
    }
    select.disabled = !names.length;
    select.value = names.includes(lookState.selectedName) ? lookState.selectedName : (names[0] ?? "");
    lookState.selectedName = select.value;
    select.addEventListener("change", () => { lookState.selectedName = select.value; });
    selectField.append(selectLabel, select);
    const apply = button("Apply", () => {
        if (controller.applyLook?.(select.value)) {
            lookState.status = `Applied “${select.value}”. The shot plan was left untouched.`;
            lookState.statusKind = "success";
            renderCameraLookTab(container, controller);
        }
    });
    apply.disabled = !names.length || !lookTargetsEditable;
    const remove = button("Delete", () => {
        if (controller.deleteLook?.(select.value)) {
            lookState.status = `Deleted “${select.value}”. The applied direction is unchanged.`;
            lookState.statusKind = "success";
            lookState.selectedName = "";
            renderCameraLookTab(container, controller);
        }
    });
    remove.disabled = !names.length;
    lookRow.append(selectField, apply, remove);
    const saveRow = document.createElement("div");
    saveRow.className = "minimax-h3-look-row minimax-h3-look-row-save";
    const name = document.createElement("input");
    name.type = "text";
    name.maxLength = 64;
    name.placeholder = "Name the current direction and camera…";
    name.setAttribute("aria-label", "New look name");
    name.value = lookState.nameDraft;
    name.addEventListener("input", () => { lookState.nameDraft = name.value; });
    const save = button("Save current", () => {
        const result = controller.saveLook?.(name.value);
        if (result?.ok) {
            const eviction = result.evicted?.length ? ` Oldest removed: ${result.evicted.join(", ")}.` : "";
            lookState.status = `Saved “${result.name}”.${eviction}`;
            lookState.statusKind = "success";
            lookState.selectedName = result.name;
            lookState.nameDraft = "";
            renderCameraLookTab(container, controller);
        }
        else {
            name.setAttribute("aria-invalid", "true");
            name.title = result?.message ?? "Name the look before saving.";
            lookState.status = name.title;
            lookState.statusKind = "error";
            name.focus();
        }
    });
    save.disabled = !lookTargetsEditable;
    saveRow.append(name, save);
    const transferActions = document.createElement("div");
    transferActions.className = "minimax-h3-look-row minimax-h3-look-row-transfer";
    const exportButton = button("Export JSON", () => {
        exportLookToClipboard().catch(() => showFeedback("The Look could not be exported.", "error"));
    });
    exportButton.setAttribute("aria-label", "Export the selected Look as JSON");
    exportButton.disabled = !names.length && !lookTargetsEditable;
    const importButton = button(lookState.transferMode === "import" ? "Apply JSON" : "Import JSON", () => {
        importLookFromClipboard().catch(() => showFeedback("The Look could not be read from the clipboard.", "error"));
    });
    importButton.setAttribute("aria-label", "Import a Look from JSON");
    importButton.disabled = !lookTargetsEditable;
    transferActions.append(exportButton, importButton);
    const transfer = document.createElement("textarea");
    transfer.className = "minimax-h3-look-transfer";
    transfer.hidden = !lookState.transferMode;
    transfer.readOnly = lookState.transferMode === "export";
    transfer.spellcheck = false;
    transfer.maxLength = 20000;
    transfer.value = lookState.transferText;
    transfer.setAttribute("aria-label", lookState.transferMode === "export" ? "Look JSON to copy" : "Look JSON to import");
    transfer.addEventListener("input", () => { lookState.transferText = transfer.value; });
    const status = document.createElement("p");
    status.className = "minimax-h3-studio-status minimax-h3-look-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.setAttribute("aria-atomic", "true");
    status.dataset.kind = lookState.statusKind;
    status.hidden = !lookState.status;
    status.textContent = lookState.status;
    const showFeedback = (message, kind = "info") => {
        lookState.status = message;
        lookState.statusKind = kind;
        status.textContent = message;
        status.dataset.kind = kind;
        status.hidden = !message;
    };
    const showTransfer = (mode, value = "") => {
        lookState.transferMode = mode;
        lookState.transferText = value;
        transfer.hidden = false;
        transfer.readOnly = mode === "export";
        transfer.value = value;
        transfer.setAttribute("aria-label", mode === "export" ? "Look JSON to copy" : "Look JSON to import");
        importButton.textContent = mode === "import" ? "Apply JSON" : "Import JSON";
        transfer.focus();
        if (mode === "export") transfer.select();
    };
    const hideTransfer = () => {
        lookState.transferMode = "";
        lookState.transferText = "";
        transfer.hidden = true;
        transfer.value = "";
        importButton.textContent = "Import JSON";
    };
    const importText = (text) => {
        const result = controller.importLook?.(text) ?? { ok: false, message: "Look import is unavailable." };
        if (!result.ok) {
            showTransfer("import", String(text ?? ""));
            showFeedback(result.message, "error");
            return;
        }
        lookState.nameDraft = result.name;
        lookState.status = `Imported and applied “${result.name}”. Save current to keep it in this browser. The shot plan was left untouched.`;
        lookState.statusKind = "success";
        lookState.transferMode = "";
        lookState.transferText = "";
        renderCameraLookTab(container, controller);
    };
    const exportLookToClipboard = async () => {
        const result = controller.exportLook?.(select.value) ?? { ok: false, message: "Look export is unavailable." };
        if (!result.ok) {
            showFeedback(result.message, "error");
            return;
        }
        try {
            if (!globalThis.navigator?.clipboard?.writeText) throw new Error("Clipboard unavailable");
            await globalThis.navigator.clipboard.writeText(result.payload);
            hideTransfer();
            showFeedback(`Exported “${result.name}” to the clipboard as Look JSON v1.`, "success");
        } catch {
            showTransfer("export", result.payload);
            showFeedback("Clipboard access is unavailable. The Look JSON is selected below for manual copy.");
        }
    };
    const importLookFromClipboard = async () => {
        if (lookState.transferMode === "import" && transfer.value.trim()) {
            importText(transfer.value);
            return;
        }
        let text = "";
        try {
            text = String(await globalThis.navigator?.clipboard?.readText?.() ?? "");
        } catch {
            text = "";
        }
        if (text.trim()) {
            importText(text);
            return;
        }
        showTransfer("import", "");
        showFeedback("Paste Look JSON into the box, then choose Apply JSON.");
    };
    const help = document.createElement("p");
    help.className = "minimax-h3-panel-help";
    help.textContent = "A Look stores creative direction and global cinematography. Shot planning is deliberately excluded.";
    looks.body.append(help, lookRow, saveRow, transferActions, transfer, status);
    container.appendChild(looks.details);

    const overrides = block("Shot overrides", "provenance, not conflict");
    const shotDocument = controller.shotDocument();
    if (["v2", "v1"].includes(shotDocument?.kind)) {
        const table = document.createElement("div");
        table.className = "minimax-h3-provenance-table";
        const cameraFields = controller.cameraFields();
        const projectDocument = controller.projectDocument();
        const project = projectDocument?.kind === "v2" ? projectDocument.value : null;
        for (const row of cameraOverrideRows(shotDocument.value, cameraFields, project)) {
            const line = document.createElement("div");
            line.className = "minimax-h3-provenance-row";
            const aspect = document.createElement("strong"); aspect.textContent = row.label;
            const global = document.createElement("span"); global.textContent = `Global: ${controller.cameraValue(row.key)}`;
            const owners = document.createElement("span"); owners.className = "minimax-h3-chip-picker";
            if (!row.shotIds.length && !row.mediaOwners.length) owners.textContent = "Global only";
            for (const shotId of row.shotIds) {
                const chip = button(shotId, () => {
                    controller.shotUiState.selectedId = shotId;
                    controller.navigateStudio?.("shots");
                });
                chip.className = "minimax-h3-source-chip";
                chip.title = `${row.label} is owned by ${shotId}`;
                owners.appendChild(chip);
            }
            for (const owner of row.mediaOwners) {
                const chip = button(`${owner.shotId} · ${owner.assetName}`, () => {
                    controller.shotUiState.selectedId = owner.shotId;
                    controller.navigateStudio?.("shots");
                });
                chip.className = "minimax-h3-source-chip";
                chip.title = `${row.label} requested from explicit camera reference ${owner.assetId}`;
                owners.appendChild(chip);
            }
            line.append(aspect, global, owners);
            table.appendChild(line);
        }
        overrides.body.appendChild(table);
        const conflicts = (controller.diagnostics()?.diagnostics ?? []).filter((diagnostic) => diagnostic.code === "camera.authority.explicit_conflict");
        if (conflicts.length) {
            const warning = document.createElement("p");
            warning.className = "minimax-h3-studio-status";
            warning.dataset.kind = "error";
            warning.textContent = `${conflicts.length} explicit camera conflict${conflicts.length === 1 ? "" : "s"}. Open Review for the competing sources and safe fixes.`;
            overrides.body.prepend(warning);
        }
    } else {
        const empty = document.createElement("p");
        empty.textContent = "Shot provenance becomes available after the shot plan is editable.";
        overrides.body.appendChild(empty);
    }
    container.appendChild(overrides.details);

    if (sourceTools.length) {
        const sources = block("Import & source tools", "advanced");
        sources.details.open = false;
        sources.body.append(...sourceTools);
        container.appendChild(sources.details);
    }
}

function unavailableState(label, documentState) {
    const notice = document.createElement("p");
    notice.className = "minimax-h3-panel-help minimax-h3-unavailable-state";
    notice.textContent = documentState.kind === "malformed"
        ? `${label} is unavailable because the stored source is invalid. The original value is preserved; repair tools are available at the end of this page.`
        : documentState.kind === "v1"
            ? `${label} uses a legacy v1 source. It remains read-only and byte-preserved until you explicitly import it as native v2 in the source tools below.`
            : `${label} is read-only for this source version. The original value is preserved.`;
    return notice;
}

export function visualLanguagePopoverGeometry(rect, viewportWidth, viewportHeight, margin = 8) {
    const safeWidth = Math.max(0, Number(viewportWidth) || 0);
    const safeHeight = Math.max(0, Number(viewportHeight) || 0);
    const triggerWidth = Math.max(0, Number(rect?.width) || 0);
    const right = Number(rect?.right) || 0;
    const left = Number(rect?.left) || 0;
    const top = Number(rect?.top) || 0;
    const bottom = Number(rect?.bottom) || 0;
    const width = Math.max(0, Math.min(Math.max(triggerWidth, 360), 420, safeWidth - margin * 2));
    const boundedLeft = Math.min(
        Math.max(margin, left + width <= safeWidth - margin ? left : right - width),
        Math.max(margin, safeWidth - width - margin),
    );
    const below = Math.max(0, safeHeight - bottom - margin - 4);
    const above = Math.max(0, top - margin - 4);
    const placement = below < 280 && above > below ? "above" : "below";
    const availableHeight = placement === "above" ? above : below;
    const maxHeight = Math.max(0, Math.min(560, availableHeight));
    return {
        width,
        left: boundedLeft,
        maxHeight,
        placement,
        top: placement === "below" ? bottom + 4 : null,
        bottom: placement === "above" ? safeHeight - top + 4 : null,
    };
}

function visualLanguageField(label, value, choices, groups, commit) {
    const field = document.createElement("div");
    field.className = "minimax-h3-studio-field";
    const caption = document.createElement("span");
    const instanceId = ++visualLanguageId;
    caption.id = `minimax-h3-visual-language-label-${instanceId}`;
    caption.textContent = label;
    const wrapper = document.createElement("div");
    wrapper.className = "minimax-h3-searchable-select";
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "minimax-h3-searchable-select-trigger";
    trigger.setAttribute("role", "combobox");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-labelledby", caption.id);
    const popover = document.createElement("div");
    popover.className = "minimax-h3-searchable-select-popover";
    popover.hidden = true;
    popover.setAttribute("role", "dialog");
    popover.setAttribute("aria-label", "Choose visual language");
    const searchRow = document.createElement("div");
    searchRow.className = "minimax-h3-select-search";
    const icon = document.createElement("span");
    icon.className = "minimax-h3-select-search-icon";
    icon.textContent = "⌕";
    icon.setAttribute("aria-hidden", "true");
    const search = document.createElement("input");
    search.type = "search";
    search.autocomplete = "off";
    search.spellcheck = false;
    search.placeholder = "Search visual languages…";
    search.setAttribute("aria-label", "Search visual languages");
    const clear = button("×", () => {
        search.value = "";
        renderOptions();
        search.focus();
    });
    clear.className = "minimax-h3-select-search-clear";
    clear.setAttribute("aria-label", "Clear visual language search");
    const list = document.createElement("div");
    list.id = `minimax-h3-visual-language-options-${instanceId}`;
    list.className = "minimax-h3-searchable-select-options";
    list.setAttribute("role", "listbox");
    list.setAttribute("aria-labelledby", caption.id);
    trigger.setAttribute("aria-controls", list.id);
    search.setAttribute("aria-controls", list.id);
    const searchStatus = document.createElement("p");
    searchStatus.className = "minimax-h3-select-search-status";
    searchStatus.setAttribute("role", "status");
    searchStatus.setAttribute("aria-live", "polite");
    const navigation = document.createElement("div");
    navigation.className = "minimax-h3-visual-navigation";
    const back = button("← Back", () => {
        const staysInFamily = Boolean(selectedBranch);
        if (staysInFamily) selectedBranch = "";
        else selectedFamily = "";
        renderOptions();
        if (staysInFamily) back.focus(); else search.focus();
    });
    back.className = "minimax-h3-visual-back";
    const breadcrumb = document.createElement("span");
    breadcrumb.className = "minimax-h3-visual-breadcrumb";
    navigation.append(back, breadcrumb);
    const previewNotice = document.createElement("p");
    previewNotice.className = "minimax-h3-visual-preview-notice";
    previewNotice.textContent = "Preview samples are not installed. Labels describe the catalog vocabulary, not a guaranteed H3 result.";
    let selectedValue = value;
    let selectedFamily = "";
    let selectedBranch = "";
    let globalListenersActive = false;
    let removalObserver = null;

    const positionPopover = () => {
        if (popover.hidden || typeof trigger.getBoundingClientRect !== "function" || typeof window === "undefined") return;
        if (trigger.isConnected === false) { close(); return; }
        const viewport = window.visualViewport;
        const viewportWidth = viewport?.width ?? window.innerWidth;
        const viewportHeight = viewport?.height ?? window.innerHeight;
        const geometry = visualLanguagePopoverGeometry(trigger.getBoundingClientRect(), viewportWidth, viewportHeight);
        Object.assign(popover.style, {
            width: `${geometry.width}px`,
            maxHeight: `${geometry.maxHeight}px`,
            left: `${geometry.left}px`,
            top: geometry.top === null ? "auto" : `${geometry.top}px`,
            bottom: geometry.bottom === null ? "auto" : `${geometry.bottom}px`,
        });
        popover.dataset.placement = geometry.placement;
    };
    const outsidePointer = (event) => {
        if (!popover.contains(event.target) && !trigger.contains(event.target)) close();
    };
    const outsideFocus = (event) => {
        if (!popover.contains(event.target) && !trigger.contains(event.target)) close();
    };
    const detachGlobalListeners = () => {
        if (!globalListenersActive || typeof window === "undefined") return;
        document.removeEventListener?.("pointerdown", outsidePointer, true);
        document.removeEventListener?.("focusin", outsideFocus, true);
        window.removeEventListener?.("resize", positionPopover);
        window.removeEventListener?.("scroll", positionPopover, true);
        window.visualViewport?.removeEventListener?.("resize", positionPopover);
        window.visualViewport?.removeEventListener?.("scroll", positionPopover);
        globalListenersActive = false;
        removalObserver?.disconnect();
        removalObserver = null;
    };
    const attachGlobalListeners = () => {
        if (globalListenersActive || typeof window === "undefined") return;
        document.addEventListener?.("pointerdown", outsidePointer, true);
        document.addEventListener?.("focusin", outsideFocus, true);
        window.addEventListener?.("resize", positionPopover);
        window.addEventListener?.("scroll", positionPopover, true);
        window.visualViewport?.addEventListener?.("resize", positionPopover);
        window.visualViewport?.addEventListener?.("scroll", positionPopover);
        globalListenersActive = true;
        if (typeof MutationObserver !== "undefined" && document.body) {
            removalObserver = new MutationObserver(() => {
                if (trigger.isConnected === false) close();
            });
            removalObserver.observe(document.body, { childList: true, subtree: true });
        }
    };

    const navigableElements = () => [...list.querySelectorAll("button")];
    const focusOption = (index) => {
        const options = navigableElements();
        if (!options.length) return;
        options[(index + options.length) % options.length].focus();
    };
    const wireNavigationKeys = (control) => {
        control.addEventListener("keydown", (event) => {
            const options = navigableElements();
            const index = options.indexOf(control);
            if (event.key === "ArrowDown") { event.preventDefault(); focusOption(index + 1); }
            else if (event.key === "ArrowUp") { event.preventDefault(); focusOption(index - 1); }
            else if (event.key === "Home") { event.preventDefault(); focusOption(0); }
            else if (event.key === "End") { event.preventDefault(); focusOption(options.length - 1); }
            else if (event.key === "Escape") { event.preventDefault(); close(); trigger.focus(); }
        });
    };
    const close = () => {
        popover.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
        detachGlobalListeners();
        if (popover.parentElement && popover.parentElement !== wrapper) wrapper.appendChild(popover);
        delete popover.dataset.portal;
    };
    const choose = (token) => {
        if (commit(token) === false) return;
        selectedValue = token;
        renderOptions();
        close();
        trigger.focus();
    };
    const appendOption = (parent, token, text) => {
        const preview = visualLanguagePreview(token);
        const option = button(text, () => choose(token));
        option.className = "minimax-h3-searchable-select-option";
        option.dataset.value = token;
        option.dataset.preview = preview.status;
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", token === selectedValue ? "true" : "false");
        option.replaceChildren();
        if (preview.status === "available") {
            const thumbnail = document.createElement("img");
            thumbnail.className = "minimax-h3-visual-preview";
            thumbnail.src = preview.src;
            thumbnail.alt = preview.alt;
            thumbnail.loading = "lazy";
            option.appendChild(thumbnail);
        }
        const copy = document.createElement("span");
        copy.className = "minimax-h3-visual-option-copy";
        const optionLabel = document.createElement("strong");
        optionLabel.textContent = text;
        copy.appendChild(optionLabel);
        if (preview.status === "available") {
            const previewLabel = document.createElement("small");
            previewLabel.textContent = `${preview.kind} sample · provenance recorded`;
            copy.appendChild(previewLabel);
        }
        option.appendChild(copy);
        wireNavigationKeys(option);
        parent.appendChild(option);
    };
    const appendVariantGroups = (families) => {
        for (const resultFamily of families) {
            if (resultFamily.family && search.value) {
                const familyHeading = document.createElement("div");
                familyHeading.className = "minimax-h3-searchable-select-family";
                familyHeading.textContent = resultFamily.family;
                familyHeading.setAttribute("role", "presentation");
                list.appendChild(familyHeading);
            }
            for (const resultBranch of resultFamily.branches) {
                const group = document.createElement("div");
                group.className = "minimax-h3-searchable-select-branch";
                group.setAttribute("role", "group");
                group.setAttribute("aria-label", [resultFamily.family, resultBranch.branch].filter(Boolean).join(" — ") || "Visual language choices");
                if (resultBranch.branch && search.value) {
                    const heading = document.createElement("div");
                    heading.className = "minimax-h3-searchable-select-group";
                    heading.textContent = resultBranch.branch;
                    heading.setAttribute("role", "presentation");
                    group.appendChild(heading);
                }
                for (const [token, text] of resultBranch.choices) appendOption(group, token, text);
                list.appendChild(group);
            }
        }
    };
    const appendNavigationChoice = (title, count, onSelect) => {
        const control = button(title, onSelect);
        control.className = "minimax-h3-visual-nav-choice";
        control.dataset.visualNav = "true";
        const name = document.createElement("strong");
        name.textContent = title;
        const meta = document.createElement("span");
        meta.textContent = `${count} variant${count === 1 ? "" : "s"}  ›`;
        control.replaceChildren(name, meta);
        wireNavigationKeys(control);
        list.appendChild(control);
    };
    const appendDirectChoice = (title, onSelect) => {
        const control = button(title, onSelect);
        control.className = "minimax-h3-visual-nav-choice minimax-h3-visual-nav-neutral";
        control.dataset.visualNav = "true";
        const name = document.createElement("strong");
        name.textContent = title;
        const meta = document.createElement("span");
        meta.textContent = "Clear visual language";
        control.replaceChildren(name, meta);
        wireNavigationKeys(control);
        list.appendChild(control);
    };
    const renderOptions = () => {
        const labels = new Map(choices ?? []);
        trigger.textContent = `${labels.get(selectedValue) ?? `Unavailable — ${selectedValue}`}  ▾`;
        list.replaceChildren();
        const allFamilies = visualLanguageHierarchy(choices, "", normalizedSearchText);
        const resultFamilies = search.value ? visualLanguageHierarchy(choices, search.value, normalizedSearchText) : allFamilies;
        const count = resultFamilies.reduce((total, family) => (
            total + family.branches.reduce((branchTotal, branch) => branchTotal + branch.choices.length, 0)
        ), 0);
        if (search.value) {
            selectedFamily = "";
            selectedBranch = "";
            list.setAttribute("role", "listbox");
            list.removeAttribute("aria-label");
            list.setAttribute("aria-labelledby", caption.id);
            breadcrumb.textContent = "Search results";
            back.hidden = true;
            appendVariantGroups(resultFamilies);
            searchStatus.textContent = count ? `${count} visual language${count === 1 ? "" : "s"}` : "No matching visual languages.";
        } else if (!selectedFamily) {
            list.setAttribute("role", "navigation");
            list.removeAttribute("aria-labelledby");
            list.setAttribute("aria-label", "Visual language families");
            breadcrumb.textContent = "All families";
            back.hidden = true;
            const neutral = allFamilies.find((family) => !family.family);
            const neutralChoice = neutral?.branches[0]?.choices[0];
            if (neutralChoice) appendDirectChoice(neutralChoice[1], () => choose(neutralChoice[0]));
            for (const family of allFamilies.filter((item) => item.family)) {
                const familyCount = family.branches.reduce((total, branch) => total + branch.choices.length, 0);
                appendNavigationChoice(family.family, familyCount, () => { selectedFamily = family.family; renderOptions(); focusOption(0); });
            }
            searchStatus.textContent = `${count} visual languages in ${allFamilies.filter((family) => family.family).length} families.`;
        } else {
            const family = allFamilies.find((item) => item.family === selectedFamily);
            back.hidden = false;
            if (!family) { selectedFamily = ""; renderOptions(); return; }
            if (!selectedBranch) {
                list.setAttribute("role", "navigation");
                list.removeAttribute("aria-labelledby");
                list.setAttribute("aria-label", `${family.family} eras and techniques`);
                breadcrumb.textContent = `All families / ${family.family}`;
                for (const branch of family.branches) {
                    appendNavigationChoice(branch.branch || "General", branch.choices.length, () => { selectedBranch = branch.branch; renderOptions(); focusOption(0); });
                }
                searchStatus.textContent = `${family.branches.length} era or technique group${family.branches.length === 1 ? "" : "s"}.`;
            } else {
                const branch = family.branches.find((item) => item.branch === selectedBranch);
                list.setAttribute("role", "listbox");
                list.removeAttribute("aria-label");
                list.setAttribute("aria-labelledby", caption.id);
                breadcrumb.textContent = `All families / ${family.family} / ${selectedBranch}`;
                if (branch) appendVariantGroups([{ family: family.family, branches: [branch] }]);
                searchStatus.textContent = `${branch?.choices.length ?? 0} variant${branch?.choices.length === 1 ? "" : "s"}.`;
            }
        }
        searchStatus.dataset.visible = "true";
        clear.disabled = !search.value;
    };
    const open = () => {
        popover.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        search.value = "";
        selectedFamily = "";
        selectedBranch = "";
        renderOptions();
        if (document.body?.appendChild && popover.parentElement !== document.body) {
            if (typeof getComputedStyle === "function") {
                const tokenSource = field.closest?.(".minimax-h3-studio") ?? field;
                const sourceStyle = getComputedStyle(tokenSource);
                for (const token of VISUAL_LANGUAGE_POPOVER_TOKENS) {
                    const tokenValue = sourceStyle.getPropertyValue(token).trim();
                    if (tokenValue) popover.style.setProperty(token, tokenValue);
                }
            }
            document.body.appendChild(popover);
            popover.dataset.portal = "true";
            positionPopover();
            attachGlobalListeners();
        }
        search.focus();
    };
    trigger.addEventListener("click", () => popover.hidden ? open() : close());
    trigger.addEventListener("keydown", (event) => {
        if (["ArrowDown", "Enter", " "].includes(event.key) && popover.hidden) {
            event.preventDefault();
            open();
        } else if (event.key === "Escape" && !popover.hidden) {
            event.preventDefault();
            close();
        }
    });
    search.addEventListener("input", renderOptions);
    search.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown" || event.key === "Enter") {
            event.preventDefault();
            focusOption(0);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            focusOption(-1);
        } else if (event.key === "Escape") {
            event.preventDefault();
            if (search.value) {
                search.value = "";
                renderOptions();
            } else {
                close();
                trigger.focus();
            }
        }
    });
    popover.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !event.defaultPrevented) {
            event.preventDefault();
            close();
            trigger.focus();
        }
    });
    searchRow.append(icon, search, clear);
    popover.append(searchRow, navigation, searchStatus, list, previewNotice);
    wrapper.append(trigger, popover);
    field.append(caption, wrapper);
    renderOptions();
    return field;
}

function moodField(label, value, choices, commit) {
    const field = document.createElement("div");
    field.className = "minimax-h3-studio-field minimax-h3-mood-field";
    field.title = "Scene-wide mood: staging, camera, light, performance, mix. For how a spoken line sounds, use Delivery under the prompt.";
    const caption = document.createElement("span");
    const instanceId = ++moodId;
    caption.id = `minimax-h3-mood-label-${instanceId}`;
    caption.textContent = label;
    const wrapper = document.createElement("div");
    wrapper.className = "minimax-h3-searchable-select minimax-h3-mood-select";
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "minimax-h3-searchable-select-trigger minimax-h3-mood-trigger";
    trigger.setAttribute("role", "combobox");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-labelledby", caption.id);

    const popover = document.createElement("div");
    popover.className = "minimax-h3-searchable-select-popover minimax-h3-mood-popover";
    popover.hidden = true;
    popover.setAttribute("role", "dialog");
    popover.setAttribute("aria-label", "Choose scene-wide mood");
    const searchRow = document.createElement("div");
    searchRow.className = "minimax-h3-select-search";
    const searchIcon = document.createElement("span");
    searchIcon.className = "minimax-h3-select-search-icon";
    searchIcon.textContent = "⌕";
    searchIcon.setAttribute("aria-hidden", "true");
    const search = document.createElement("input");
    search.type = "search";
    search.autocomplete = "off";
    search.spellcheck = false;
    search.placeholder = "Search moods…";
    search.setAttribute("aria-label", "Search moods");
    const clear = button("×", () => {
        search.value = "";
        renderOptions();
        search.focus();
    });
    clear.className = "minimax-h3-select-search-clear";
    clear.setAttribute("aria-label", "Clear mood search");
    searchRow.append(searchIcon, search, clear);

    const searchStatus = document.createElement("p");
    searchStatus.className = "minimax-h3-select-search-status";
    searchStatus.setAttribute("role", "status");
    searchStatus.setAttribute("aria-live", "polite");
    const list = document.createElement("div");
    list.id = `minimax-h3-mood-options-${instanceId}`;
    list.className = "minimax-h3-searchable-select-options minimax-h3-mood-options";
    list.setAttribute("role", "listbox");
    list.setAttribute("aria-labelledby", caption.id);
    trigger.setAttribute("aria-controls", list.id);
    search.setAttribute("aria-controls", list.id);
    const guardrail = document.createElement("p");
    guardrail.className = "minimax-h3-mood-guardrail";
    guardrail.textContent = MOOD_GUARDRAIL;
    let selectedValue = value;
    let globalListenersActive = false;
    let removalObserver = null;

    const navigableOptions = () => [...list.querySelectorAll("button")];
    const focusOption = (index) => {
        const options = navigableOptions();
        if (options.length) options[(index + options.length) % options.length].focus();
    };
    const wireOptionKeys = (control) => {
        control.addEventListener("keydown", (event) => {
            const options = navigableOptions();
            const index = options.indexOf(control);
            if (event.key === "ArrowDown") { event.preventDefault(); focusOption(index + 1); }
            else if (event.key === "ArrowUp") { event.preventDefault(); focusOption(index - 1); }
            else if (event.key === "Home") { event.preventDefault(); focusOption(0); }
            else if (event.key === "End") { event.preventDefault(); focusOption(options.length - 1); }
            else if (event.key === "Escape") { event.preventDefault(); close(); trigger.focus(); }
        });
    };
    const positionPopover = () => {
        if (popover.hidden || typeof trigger.getBoundingClientRect !== "function" || typeof window === "undefined") return;
        if (trigger.isConnected === false) { close(); return; }
        const viewport = window.visualViewport;
        const geometry = visualLanguagePopoverGeometry(
            trigger.getBoundingClientRect(),
            viewport?.width ?? window.innerWidth,
            viewport?.height ?? window.innerHeight,
        );
        Object.assign(popover.style, {
            width: `${geometry.width}px`,
            maxHeight: `${geometry.maxHeight}px`,
            left: `${geometry.left}px`,
            top: geometry.top === null ? "auto" : `${geometry.top}px`,
            bottom: geometry.bottom === null ? "auto" : `${geometry.bottom}px`,
        });
        popover.dataset.placement = geometry.placement;
    };
    const outsidePointer = (event) => {
        if (!popover.contains(event.target) && !trigger.contains(event.target)) close();
    };
    const outsideFocus = (event) => {
        if (!popover.contains(event.target) && !trigger.contains(event.target)) close();
    };
    const detachGlobalListeners = () => {
        if (!globalListenersActive || typeof window === "undefined") return;
        document.removeEventListener?.("pointerdown", outsidePointer, true);
        document.removeEventListener?.("focusin", outsideFocus, true);
        window.removeEventListener?.("resize", positionPopover);
        window.removeEventListener?.("scroll", positionPopover, true);
        window.visualViewport?.removeEventListener?.("resize", positionPopover);
        window.visualViewport?.removeEventListener?.("scroll", positionPopover);
        globalListenersActive = false;
        removalObserver?.disconnect();
        removalObserver = null;
    };
    const close = () => {
        popover.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
        detachGlobalListeners();
        if (popover.parentElement && popover.parentElement !== wrapper) wrapper.appendChild(popover);
        delete popover.dataset.portal;
    };
    const attachGlobalListeners = () => {
        if (globalListenersActive || typeof window === "undefined") return;
        document.addEventListener?.("pointerdown", outsidePointer, true);
        document.addEventListener?.("focusin", outsideFocus, true);
        window.addEventListener?.("resize", positionPopover);
        window.addEventListener?.("scroll", positionPopover, true);
        window.visualViewport?.addEventListener?.("resize", positionPopover);
        window.visualViewport?.addEventListener?.("scroll", positionPopover);
        globalListenersActive = true;
        if (typeof MutationObserver !== "undefined" && document.body) {
            removalObserver = new MutationObserver(() => {
                if (trigger.isConnected === false) close();
            });
            removalObserver.observe(document.body, { childList: true, subtree: true });
        }
    };
    const choose = (token) => {
        if (commit(token) === false) return;
        selectedValue = token;
        renderOptions();
        close();
        trigger.focus();
    };
    const renderOptions = () => {
        const groups = moodChoiceGroups(choices, selectedValue, search.value);
        const labels = new Map(choices ?? []);
        trigger.textContent = `${labels.get(selectedValue) ?? `Unavailable — ${selectedValue}`}  ▾`;
        list.replaceChildren();
        let count = 0;
        for (const { group, choices: entries } of groups) {
            const groupElement = document.createElement("div");
            groupElement.className = "minimax-h3-mood-group";
            groupElement.setAttribute("role", "group");
            groupElement.setAttribute("aria-label", group || "Mood preference");
            if (group) {
                const heading = document.createElement("div");
                heading.className = "minimax-h3-mood-group-heading";
                heading.textContent = group;
                heading.setAttribute("role", "presentation");
                groupElement.appendChild(heading);
            }
            for (const entry of entries) {
                count += 1;
                const option = button(entry.label, () => choose(entry.token));
                option.className = "minimax-h3-mood-option";
                option.dataset.value = entry.token;
                option.setAttribute("role", "option");
                option.setAttribute("aria-selected", entry.token === selectedValue ? "true" : "false");
                const name = document.createElement("strong");
                name.textContent = entry.label;
                const description = document.createElement("small");
                description.textContent = entry.description;
                option.replaceChildren(name, description);
                wireOptionKeys(option);
                groupElement.appendChild(option);
            }
            list.appendChild(groupElement);
        }
        searchStatus.textContent = count ? `${count} mood${count === 1 ? "" : "s"}` : "No matching moods.";
        searchStatus.dataset.visible = "true";
        clear.disabled = !search.value;
    };
    const open = () => {
        popover.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        search.value = "";
        renderOptions();
        if (document.body?.appendChild && popover.parentElement !== document.body) {
            if (typeof getComputedStyle === "function") {
                const tokenSource = field.closest?.(".minimax-h3-studio") ?? field;
                const sourceStyle = getComputedStyle(tokenSource);
                for (const token of VISUAL_LANGUAGE_POPOVER_TOKENS) {
                    const tokenValue = sourceStyle.getPropertyValue(token).trim();
                    if (tokenValue) popover.style.setProperty(token, tokenValue);
                }
            }
            document.body.appendChild(popover);
            popover.dataset.portal = "true";
            positionPopover();
            attachGlobalListeners();
        }
        search.focus();
    };
    trigger.addEventListener("click", () => popover.hidden ? open() : close());
    trigger.addEventListener("keydown", (event) => {
        if (["ArrowDown", "Enter", " "].includes(event.key) && popover.hidden) {
            event.preventDefault();
            open();
        } else if (event.key === "Escape" && !popover.hidden) {
            event.preventDefault();
            close();
        }
    });
    search.addEventListener("input", renderOptions);
    search.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown" || event.key === "Enter") {
            event.preventDefault();
            focusOption(0);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            focusOption(-1);
        } else if (event.key === "Escape") {
            event.preventDefault();
            if (search.value) {
                search.value = "";
                renderOptions();
            } else {
                close();
                trigger.focus();
            }
        }
    });
    popover.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !event.defaultPrevented) {
            event.preventDefault();
            close();
            trigger.focus();
        }
    });

    popover.append(searchRow, searchStatus, list, guardrail);
    wrapper.append(trigger, popover);
    field.append(caption, wrapper);
    renderOptions();
    return field;
}

function choiceField(label, value, choices, commit, disabled = false, title = "") {
    const field = document.createElement("label");
    field.className = "minimax-h3-studio-field";
    const caption = document.createElement("span");
    caption.textContent = label;
    const select = document.createElement("select");
    for (const [token, text] of choices) {
        const option = document.createElement("option");
        option.value = token;
        option.textContent = text;
        select.appendChild(option);
    }
    select.value = value;
    select.disabled = disabled;
    if (title) field.title = title;
    select.addEventListener("change", () => commit(select.value));
    field.append(caption, select);
    return field;
}

function rawStatus(widgetName, documentState, controller) {
    const wrapper = document.createElement("div");
    wrapper.className = "minimax-h3-studio-status";
    wrapper.dataset.kind = documentState.kind;
    const message = document.createElement("p");
    message.className = "minimax-h3-source-state-message";
    message.textContent = documentState.kind === "malformed"
        ? `${widgetName} cannot be displayed because its stored JSON is invalid. The original value is preserved.`
        : documentState.kind === "v1"
            ? `${widgetName} is legacy v1. Importing here creates a sanitized v2 document; merely opening Studio changes nothing.`
            : `${widgetName} is ${documentState.kind}; its raw value is preserved.`;
    wrapper.appendChild(message);
    if (documentState.kind === "future") return wrapper;
    const repair = document.createElement("details");
    repair.className = "minimax-h3-inline-repair";
    const heading = document.createElement("summary");
    heading.textContent = documentState.kind === "v1" ? "Review legacy source" : "Repair source JSON";
    const raw = document.createElement("textarea");
    raw.className = "minimax-h3-inline-repair-source";
    raw.value = documentState.raw;
    raw.readOnly = documentState.kind === "v1";
    raw.setAttribute("aria-label", `Raw ${widgetName}`);
    const feedback = document.createElement("p");
    feedback.className = "minimax-h3-source-feedback";
    feedback.setAttribute("role", "status");
    feedback.setAttribute("aria-live", "polite");
    const apply = button(documentState.kind === "v1" ? "Import v1 as v2" : "Validate and import as v2", () => {
        try {
            const parsed = JSON.parse(raw.value);
            if (![1, 2].includes(parsed?.schemaVersion)) throw new TypeError("Expected schemaVersion 1 or 2");
            const importSource = widgetName === "creative_treatment_json"
                ? controller.importCreativeSource
                : controller.importCinematographySource;
            const result = importSource?.call(controller, raw.value)
                ?? { ok: false, message: "Import is unavailable." };
            if (!result.ok) throw new TypeError(result.message);
            raw.removeAttribute("aria-invalid");
            feedback.dataset.kind = "success";
            feedback.textContent = `Imported schema v${result.fromVersion} as native v2.`;
        } catch (error) {
            raw.setAttribute("aria-invalid", "true");
            feedback.dataset.kind = "error";
            feedback.textContent = String(error?.message ?? "Invalid structured source.");
        }
    });
    const actions = document.createElement("div");
    actions.className = "minimax-h3-inline-repair-actions";
    actions.appendChild(apply);
    repair.append(heading, raw, feedback, actions);
    wrapper.appendChild(repair);
    return wrapper;
}
