import {
    actionButton, bindCommit, captureOpenDisclosures, checkboxPicker, createMasterDetail, element, emptyState, field,
    inspectorSection, masterRow, restoreOpenDisclosures, selectInput, setOptional, textArea, textInput, tokenList,
} from "./domain_components.js";
import { usageIndex } from "./derive.js";
import { commitProject, projectForController, readOnlyProjectMessage, uniqueId } from "./project_editor.js";

const APPEARANCE_CONTROLS = [
    ["wardrobe", "Wardrobe", "wardrobe"], ["hair", "Hair", "hair"], ["makeup", "Makeup", "makeup"],
    ["accessories", "Accessories", "accessories"], ["carried_items", "Carried items", "carriedItems"],
    ["damage", "Damage", "damage"], ["wetness", "Wetness", "wetness"],
    ["body_condition", "Body condition", "bodyCondition"], ["transformation", "Transformation", "transformation"],
    ["other", "Other", "other"],
];

function nextH3Index(subjects) {
    const used = new Set(subjects.map((subject) => Number(subject.h3Index)));
    for (let index = 1; index <= 64; index += 1) if (!used.has(index)) return index;
    return 64;
}

function newSubject(project) {
    const id = uniqueId(project.subjects, "subject.");
    return {
        id, h3Index: nextH3Index(project.subjects), name: "New subject", description: "",
        identityAssetIds: [], baseAppearanceStateId: "base",
        appearanceStates: [{ id: "base", name: "Base", controls: [], attributes: {} }],
    };
}

export function setSubjectGenerationPromptUse(generation, subjectId, included) {
    if (!generation || !subjectId) return false;
    const activation = generation.activation ?? { mode: "auto" };
    const roots = Array.isArray(activation.roots) ? [...activation.roots] : [];
    const index = roots.findIndex((root) => root.kind === "subject" && root.id === subjectId);
    if (included && index < 0) roots.push({ kind: "subject", id: subjectId });
    if (!included && index >= 0) roots.splice(index, 1);
    if ((included && index >= 0) || (!included && index < 0)) return false;
    const exclude = Array.isArray(activation.exclude) && activation.exclude.length
        ? { exclude: structuredClone(activation.exclude) } : {};
    generation.activation = roots.length
        ? { mode: "explicit", roots, ...exclude }
        : { mode: "auto", ...exclude };
    return true;
}

function renderAppearanceState(container, subject, appearance, project, uses, commit, rerender) {
    const key = `${subject.id}:${appearance.id}`;
    const stateUses = uses.appearanceStates.get(key) ?? [];
    const section = inspectorSection(
        appearance.name || appearance.id,
        [appearance.id === subject.baseAppearanceStateId ? "Base" : "", ...(appearance.controls ?? [])].filter(Boolean).join(" · ") || "No controlled changes",
        appearance.id === subject.baseAppearanceStateId,
    );
    const stable = element("p", "minimax-h3-field-hint", `Stable ID: ${appearance.id}`);
    const name = textInput(appearance.name);
    bindCommit(name, (value) => { appearance.name = value.trim() || appearance.id; }, commit);
    name.addEventListener("change", () => rerender(appearance.id));
    const extendsState = selectInput(appearance.extends ?? "", [
        ["", "No parent state"],
        ...(subject.appearanceStates ?? []).filter((item) => item !== appearance).map((item) => [item.id, item.name || item.id]),
    ]);
    bindCommit(extendsState, (value) => setOptional(appearance, "extends", value), commit);
    const description = textArea(appearance.description, "Only observable changes in this state");
    bindCommit(description, (value) => setOptional(appearance, "description", value.trim()), commit, "blur");
    section.body.append(stable, field("State name", name), field("Extends", extendsState), field("Observable appearance", description));

    const controls = element("fieldset", "minimax-h3-control-picker");
    controls.appendChild(element("legend", "", "What changes in this state"));
    const selected = new Set(appearance.controls ?? []);
    for (const [token, label] of APPEARANCE_CONTROLS) {
        const option = element("label", "minimax-h3-picker-option");
        const input = document.createElement("input"); input.type = "checkbox"; input.checked = selected.has(token);
        input.addEventListener("change", () => {
            if (input.checked) selected.add(token); else selected.delete(token);
            appearance.controls = APPEARANCE_CONTROLS.map(([value]) => value).filter((value) => selected.has(value));
            commit(); rerender(appearance.id);
        });
        option.append(input, element("span", "", label)); controls.appendChild(option);
    }
    section.body.appendChild(controls);

    appearance.attributes ??= {};
    for (const [token, label, attribute] of APPEARANCE_CONTROLS) {
        if (!selected.has(token)) continue;
        if (["accessories", "carriedItems"].includes(attribute)) {
            section.body.appendChild(field(label, tokenList(appearance.attributes[attribute], (value) => {
                if (value.length) appearance.attributes[attribute] = value; else delete appearance.attributes[attribute];
                commit(); rerender(appearance.id);
            }, `Add ${label.toLowerCase()}`)));
            continue;
        }
        const control = textInput(appearance.attributes[attribute]);
        bindCommit(control, (value) => setOptional(appearance.attributes, attribute, value.trim()), commit);
        section.body.appendChild(field(label, control));
    }

    const sourceMode = selectInput(appearance.source?.mode ?? "description", [["description", "Description"], ["asset", "Picture asset"]]);
    sourceMode.addEventListener("change", () => {
        appearance.source = sourceMode.value === "asset" ? { mode: "asset", assetId: "" } : { mode: "description" };
        commit(); rerender(appearance.id);
    });
    section.body.appendChild(field("Appearance source", sourceMode));
    if (appearance.source?.mode === "asset") {
        const pictures = (project.assets ?? []).filter((asset) => asset.type === "picture");
        const asset = selectInput(appearance.source.assetId, [["", "Select a picture…"], ...pictures.map((item) => [item.id, item.name || item.id])]);
        bindCommit(asset, (value) => { appearance.source.assetId = value; }, commit);
        const region = textInput(appearance.source.region, { placeholder: "Optional crop or region" });
        bindCommit(region, (value) => setOptional(appearance.source, "region", value.trim()), commit);
        section.body.append(field("Picture", asset), field("Region", region));
    }

    const actions = element("div", "minimax-h3-studio-toolbar");
    actions.appendChild(actionButton("Duplicate state", () => {
        const copy = structuredClone(appearance);
        copy.id = uniqueId(subject.appearanceStates, `${appearance.id}.copy.`);
        copy.name = `${appearance.name} copy`;
        subject.appearanceStates.push(copy); commit(); rerender(copy.id);
    }));
    const blocked = appearance.id === subject.baseAppearanceStateId || stateUses.length > 0;
    actions.appendChild(actionButton("Delete state", () => {
        subject.appearanceStates.splice(subject.appearanceStates.indexOf(appearance), 1); commit(); rerender();
    }, { danger: true, disabled: blocked }));
    section.body.appendChild(actions);
    if (appearance.id === subject.baseAppearanceStateId) section.body.appendChild(element("p", "minimax-h3-usage-note", "The base appearance cannot be deleted."));
    else if (stateUses.length) section.body.appendChild(element("p", "minimax-h3-usage-note", `Used by: ${stateUses.join(", ")}`));
    container.appendChild(section.details);
}

export function renderSubjectsTab(container, controller) {
    container.replaceChildren();
    const project = projectForController(controller);
    if (!project) return readOnlyProjectMessage(container, controller.projectDocument(), controller);
    const ui = controller.projectUiState;
    const shotDocument = controller.shotDocument?.();
    const uses = usageIndex(project, shotDocument?.kind === "v2" ? shotDocument.value : {});
    if (!ui.subjectSelectedId || !project.subjects.some((subject) => subject.id === ui.subjectSelectedId)) {
        ui.subjectSelectedId = project.subjects[0]?.id ?? null;
    }
    const commit = () => commitProject(controller);
    const rerender = (appearanceId = null) => {
        ui.subjectPanelScroll = container.scrollTop;
        ui.subjectOpenDisclosures = captureOpenDisclosures(container);
        ui.subjectAppearanceId = appearanceId;
        renderSubjectsTab(container, controller);
    };
    const toolbar = element("div", "minimax-h3-studio-toolbar");
    const addSubject = actionButton("+ Subject", () => {
        const subject = newSubject(project);
        project.subjects.push(subject);
        ui.subjectSelectedId = subject.id;
        const generation = project.generations.find((item) => item.id === ui.selectedGenerationId)
            ?? project.generations[0];
        setSubjectGenerationPromptUse(generation, subject.id, true);
        commit(); rerender();
    }, { disabled: project.subjects.length >= 64 });
    toolbar.append(addSubject, element("span", "minimax-h3-field-hint", `${project.subjects.length}/64 subjects`));
    container.appendChild(toolbar);
    if (!project.subjects.length) {
        container.appendChild(emptyState("No subjects yet", "Create a reusable identity, then define appearance changes without changing the face.", addSubject.cloneNode(true)));
        container.querySelector(".minimax-h3-empty-state button")?.addEventListener("click", () => addSubject.click());
        return;
    }

    const { grid, master, inspector } = createMasterDetail();
    const masterRows = new Map();
    for (const subject of project.subjects) {
        const subjectUses = uses.subjects.get(subject.id) ?? [];
        const row = masterRow(
            subject.name || subject.id,
            `<Subject ${subject.h3Index}> · ${subject.appearanceStates?.length ?? 0} states · ${subjectUses.length} uses`,
            subject.id === ui.subjectSelectedId,
            () => { ui.subjectSelectedId = subject.id; rerender(); },
        );
        masterRows.set(subject.id, row);
        master.appendChild(row);
    }
    const subject = project.subjects.find((item) => item.id === ui.subjectSelectedId);
    const identity = inspectorSection("Identity", `<Subject ${subject.h3Index}>`, true);
    identity.body.appendChild(element("p", "minimax-h3-field-hint", `Stable ID: ${subject.id}. Appearance states never change facial identity.`));
    const name = textInput(subject.name); bindCommit(name, (value) => { subject.name = value.trim() || subject.id; }, commit);
    name.addEventListener("input", () => {
        // Patch the existing row while typing. Rebuilding the whole tab used to
        // discard focus/selection, while waiting for the storage commit left
        // the saved card label looking stale.
        const label = masterRows.get(subject.id)?.children?.[0];
        if (label) label.textContent = name.value.trim() || subject.id;
    });
    const legacyInstruction = subject.description === "Describe the stable identity.";
    const description = textArea(legacyInstruction ? "" : subject.description, "Describe stable face, body and identity traits…");
    bindCommit(description, (value) => { subject.description = value.trim(); }, commit, "blur");
    identity.body.append(field("Name", name), field("Identity description", description));
    const pictures = (project.assets ?? []).filter((asset) => asset.type === "picture").map((asset) => ({ id: asset.id, label: asset.name || asset.id }));
    identity.body.appendChild(field("Identity pictures", checkboxPicker(pictures, subject.identityAssetIds, (ids) => {
        subject.identityAssetIds = ids; commit();
    }, "Identity picture assets"), "Only picture assets can reinforce identity."));
    const voiceAssets = (project.assets ?? []).filter((asset) => asset.type === "audio");
    const voice = selectInput(subject.defaultVoiceAssetId ?? "", [
        ["", "No default voice"],
        ...voiceAssets.map((asset) => [asset.id, asset.name || asset.id]),
    ]);
    bindCommit(voice, (value) => setOptional(subject, "defaultVoiceAssetId", value), commit);
    identity.body.appendChild(field(
        "Default voice",
        voice,
        "Inherited whenever this subject is active. A shot-level voice reference can override it for one scene.",
    ));
    inspector.appendChild(identity.details);

    const promptUse = inspectorSection("Use in prompts", "generation casting", true);
    promptUse.body.appendChild(element(
        "p", "minimax-h3-field-hint",
        "A saved identity reaches the LLM when a shot marks it present or when it is included for a generation here.",
    ));
    for (const generation of project.generations ?? []) {
        const rooted = (generation.activation?.roots ?? []).some((root) => root.kind === "subject" && root.id === subject.id);
        const control = document.createElement("input");
        control.type = "checkbox";
        control.checked = rooted;
        control.addEventListener("change", () => {
            if (setSubjectGenerationPromptUse(generation, subject.id, control.checked)) commit();
            rerender();
        });
        promptUse.body.appendChild(field(
            `Always include in Generation ${generation.order ?? generation.id}`,
            control,
            rooted
                ? "Its identity definition and selected appearance are sent even without an explicit shot cast."
                : "Otherwise, add this subject under Shots → Who’s in it when it appears.",
        ));
    }
    inspector.appendChild(promptUse.details);

    const statesHeading = element("div", "minimax-h3-studio-toolbar");
    statesHeading.append(element("strong", "", "Appearance states"), actionButton("+ Appearance state", () => {
        const id = uniqueId(subject.appearanceStates ?? [], "state.");
        (subject.appearanceStates ??= []).push({ id, name: "New appearance", controls: [], attributes: {} });
        commit(); rerender(id);
    }));
    inspector.appendChild(statesHeading);
    for (const appearance of subject.appearanceStates ?? []) renderAppearanceState(inspector, subject, appearance, project, uses, commit, rerender);

    const subjectActions = element("div", "minimax-h3-studio-toolbar");
    subjectActions.appendChild(actionButton("Duplicate subject", () => {
        const copy = structuredClone(subject);
        copy.id = uniqueId(project.subjects, "subject."); copy.h3Index = nextH3Index(project.subjects); copy.name = `${subject.name} copy`;
        project.subjects.push(copy); ui.subjectSelectedId = copy.id; commit(); rerender();
    }));
    const subjectUses = uses.subjects.get(subject.id) ?? [];
    subjectActions.appendChild(actionButton("Delete subject", () => {
        project.subjects.splice(project.subjects.indexOf(subject), 1); ui.subjectSelectedId = null; commit(); rerender();
    }, { danger: true, disabled: subjectUses.length > 0 }));
    inspector.appendChild(subjectActions);
    if (subjectUses.length) inspector.appendChild(element("p", "minimax-h3-usage-note", `Cannot delete. Used by: ${subjectUses.join(", ")}`));
    container.appendChild(grid);
    restoreOpenDisclosures(container, ui.subjectOpenDisclosures);
    if (ui.subjectPanelScroll !== undefined) container.scrollTop = ui.subjectPanelScroll;
}
