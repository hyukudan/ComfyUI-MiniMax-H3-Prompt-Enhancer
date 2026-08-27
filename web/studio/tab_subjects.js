import {
    actionButton, bindCommit, captureOpenDisclosures, createMasterDetail, element, emptyState, field,
    inspectorSection, masterRow, restoreOpenDisclosures, selectInput, setOptional, textArea, textInput, tokenList,
} from "./domain_components.js";
import { usageIndex } from "./derive.js";
import { assetChooserPanel, assignedAssetGallery, importEntityAsset } from "./entity_media.js";
import { assetUsage } from "./media_model.js";
import { commitProject, projectForController, readOnlyProjectMessage, uniqueId } from "./project_editor.js";
import { applyAudioClipToAsset, renderAudioTrimEditor } from "./audio_trim_editor.js";
import { referenceSourceForAsset, sourcePreviewUrl } from "./reference_sources.js";
import { ensureSubjectBindings } from "./subject_model.js";

const APPEARANCE_CONTROLS = [
    ["wardrobe", "Wardrobe", "wardrobe"], ["hair", "Hair", "hair"], ["makeup", "Makeup", "makeup"],
    ["accessories", "Accessories", "accessories"], ["carried_items", "Carried items", "carriedItems"],
    ["damage", "Damage", "damage"], ["wetness", "Wetness", "wetness"],
    ["body_condition", "Body condition", "bodyCondition"], ["transformation", "Transformation", "transformation"],
    ["other", "Other", "other"],
];

function nextH3Index(entities) {
    const used = new Set(entities.map((entity) => Number(entity.h3Index)));
    for (let index = 1; index <= 64; index += 1) if (!used.has(index)) return index;
    return 64;
}

export function createSubjectDraft(project, name = "New subject") {
    const id = uniqueId(project.subjects, "subject.");
    return {
        id, h3Index: nextH3Index([...(project.subjects ?? []), ...(project.props ?? [])]), name: String(name).trim() || "New subject", description: "",
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

function renderAppearanceState(container, subject, appearance, project, uses, commit, rerender, selectedAppearanceId, controller, ui) {
    const key = `${subject.id}:${appearance.id}`;
    const stateUses = uses.appearanceStates.get(key) ?? [];
    const section = inspectorSection(
        appearance.name || appearance.id,
        [appearance.id === subject.baseAppearanceStateId ? "Base" : "", ...(appearance.controls ?? [])].filter(Boolean).join(" · ") || "No controlled changes",
        appearance.id === selectedAppearanceId,
    );
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
    section.body.append(field("State name", name), field("Extends", extendsState), field("Observable appearance", description));

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
        const sourceActions = element("div", "minimax-h3-entity-media-actions");
        const chooseSource = actionButton("Choose from Files", () => {
            ui.subjectAssetChooser = { target: "look", subjectId: subject.id, appearanceId: appearance.id };
            rerender(appearance.id);
        });
        const sourceInput = document.createElement("input");
        sourceInput.type = "file"; sourceInput.accept = "image/*"; sourceInput.hidden = true;
        const importSource = actionButton("+ Upload picture", () => sourceInput.click(), { disabled: typeof controller.uploadReferenceFile !== "function" });
        sourceInput.addEventListener("change", async () => {
            const file = sourceInput.files?.[0];
            if (!file) return;
            importSource.disabled = true; importSource.textContent = "Importing…";
            const result = await importEntityAsset(controller, project, file, "picture", (nextProject, assetId) => {
                const nextSubject = nextProject.subjects.find((item) => item.id === subject.id);
                nextSubject.appearanceStates.find((item) => item.id === appearance.id).source = { ...appearance.source, mode: "asset", assetId };
                ensureSubjectBindings(nextProject, controller.shotDocument?.()?.value ?? {}, subject.id);
            });
            ui.subjectImportFeedback = result.message; ui.subjectImportValid = result.ok;
            delete ui.subjectAssetChooser;
            rerender(appearance.id);
        });
        sourceActions.append(importSource, chooseSource, sourceInput);
        section.body.append(
            assignedAssetGallery({
                assets: pictures, controller, selectedIds: appearance.source.assetId ? [appearance.source.assetId] : [],
                ariaLabel: `Picture connected to ${appearance.name || appearance.id}`,
                emptyMessage: "This look has no picture. Its written appearance still reaches the LLM.",
                onUnlink: () => { appearance.source.assetId = ""; commit(); rerender(appearance.id); },
            }),
            sourceActions,
        );
        const chooser = ui.subjectAssetChooser;
        if (chooser?.target === "look" && chooser.subjectId === subject.id && chooser.appearanceId === appearance.id) {
            section.body.appendChild(assetChooserPanel({
                assets: pictures, controller, selectedIds: appearance.source.assetId ? [appearance.source.assetId] : [],
                ariaLabel: `Choose a picture for ${appearance.name || appearance.id}`,
                usageForAsset: (assetId) => assetUsage(project, assetId),
                onChoose: (assetId) => {
                    appearance.source.assetId = assetId;
                    ensureSubjectBindings(project, controller.shotDocument?.()?.value ?? {}, subject.id);
                    delete ui.subjectAssetChooser; commit(); rerender(appearance.id);
                },
                onClose: () => { delete ui.subjectAssetChooser; rerender(appearance.id); },
            }));
        }
        const region = textInput(appearance.source.region, { placeholder: "Optional crop or region" });
        bindCommit(region, (value) => setOptional(appearance.source, "region", value.trim()), commit);
        section.body.appendChild(field("Region", region));
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
        const subject = createSubjectDraft(project);
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
        const row = element("button", "minimax-h3-master-row minimax-h3-subject-master-row");
        row.type = "button"; row.setAttribute("role", "option");
        row.setAttribute("aria-selected", String(subject.id === ui.subjectSelectedId));
        row.addEventListener("click", () => { ui.subjectSelectedId = subject.id; rerender(); });
        const primaryAsset = (subject.identityAssetIds ?? []).map((id) => project.assets.find((asset) => asset.id === id)).find(Boolean);
        const primarySource = primaryAsset ? referenceSourceForAsset(controller.referenceDirectorDocument?.()?.value, primaryAsset.id) : null;
        const previewUrl = sourcePreviewUrl(primarySource);
        const avatar = element("span", "minimax-h3-subject-master-avatar");
        if (previewUrl) {
            const image = element("img"); image.src = previewUrl; image.alt = ""; image.loading = "lazy"; avatar.appendChild(image);
        } else avatar.textContent = String(subject.name || "S").slice(0, 1).toUpperCase();
        const rowCopy = element("span", "minimax-h3-subject-master-copy");
        const subjectName = element("span", "", subject.name || subject.id); subjectName.setAttribute("data-subject-name", "true");
        rowCopy.append(subjectName, element("small", "", `Image ${(subject.identityAssetIds ?? []).length ? "✓" : "—"} · Voice ${subject.defaultVoiceAssetId ? "✓" : "—"} · ${subject.appearanceStates?.length ?? 0} looks · ${subjectUses.length} uses`));
        row.append(avatar, rowCopy);
        masterRows.set(subject.id, { row, label: subjectName });
        master.appendChild(row);
    }
    const subject = project.subjects.find((item) => item.id === ui.subjectSelectedId);
    const identity = inspectorSection("Identity", "Stable visual identity", true);
    identity.body.appendChild(element("p", "minimax-h3-field-hint", "Appearance states can change clothes, hair or styling without changing the person's identity."));
    const name = textInput(subject.name); bindCommit(name, (value) => { subject.name = value.trim() || subject.id; }, commit);
    name.addEventListener("input", () => {
        // Patch the existing row while typing. Rebuilding the whole tab used to
        // discard focus/selection, while waiting for the storage commit left
        // the saved card label looking stale.
        const label = masterRows.get(subject.id)?.label;
        if (label) label.textContent = name.value.trim() || subject.id;
    });
    const legacyInstruction = subject.description === "Describe the stable identity.";
    const description = textArea(legacyInstruction ? "" : subject.description, "Describe stable face, body and identity traits…");
    bindCommit(description, (value) => { subject.description = value.trim(); }, commit, "blur");
    identity.body.append(field("Name", name), field("Identity description", description));
    const pictures = (project.assets ?? []).filter((asset) => asset.type === "picture");
    const identityHeading = element("div", "minimax-h3-entity-media-heading");
    const pictureInput = document.createElement("input");
    pictureInput.type = "file"; pictureInput.accept = "image/*"; pictureInput.hidden = true;
    const importPicture = actionButton("+ Upload image", () => pictureInput.click());
    importPicture.disabled = typeof controller.uploadReferenceFile !== "function";
    const choosePicture = actionButton("Choose from Files", () => {
        ui.subjectAssetChooser = { target: "identity", subjectId: subject.id };
        rerender();
    });
    const importStatus = element("span", "minimax-h3-field-hint"); importStatus.hidden = true;
    pictureInput.addEventListener("change", async () => {
        const file = pictureInput.files?.[0];
        if (!file) return;
        importPicture.disabled = true; importStatus.hidden = false; importStatus.textContent = "Importing…";
        const result = await importEntityAsset(controller, project, file, "picture", (nextProject, assetId) => {
            const nextSubject = nextProject.subjects.find((item) => item.id === subject.id);
            nextSubject.identityAssetIds = [...new Set([...(nextSubject.identityAssetIds ?? []), assetId])];
            ensureSubjectBindings(nextProject, controller.shotDocument?.()?.value ?? {}, subject.id);
        });
        ui.subjectImportFeedback = result.message; ui.subjectImportValid = result.ok;
        if (result.ok) ui.subjectSelectedId = subject.id;
        rerender();
    });
    const identityActions = element("div", "minimax-h3-entity-media-actions");
    identityActions.append(importPicture, choosePicture, pictureInput);
    identityHeading.append(element("strong", "", "Identity pictures"), identityActions);
    identity.body.append(identityHeading, assignedAssetGallery({
        assets: pictures, controller, selectedIds: subject.identityAssetIds ?? [], primary: true,
        ariaLabel: `Identity pictures connected to ${subject.name || subject.id}`,
        emptyMessage: `${subject.name || "This subject"} has no visual identity yet. Upload an image or choose one from Files.`,
        onUnlink: (assetId) => {
            subject.identityAssetIds = (subject.identityAssetIds ?? []).filter((id) => id !== assetId);
            commit(); rerender();
        },
    }), importStatus);
    if (ui.subjectAssetChooser?.target === "identity" && ui.subjectAssetChooser.subjectId === subject.id) {
        identity.body.appendChild(assetChooserPanel({
            assets: pictures, controller, selectedIds: subject.identityAssetIds ?? [], multiple: true,
            ariaLabel: `Choose identity pictures for ${subject.name || subject.id}`,
            usageForAsset: (assetId) => assetUsage(project, assetId),
            onChoose: (assetId, state) => {
                const ids = new Set(subject.identityAssetIds ?? []);
                if (state.selected) ids.delete(assetId); else ids.add(assetId);
                subject.identityAssetIds = [...ids];
                ensureSubjectBindings(project, controller.shotDocument?.()?.value ?? {}, subject.id);
                commit(); rerender();
            },
            onClose: () => { delete ui.subjectAssetChooser; rerender(); },
        }));
    }
    if (ui.subjectImportFeedback) {
        importStatus.hidden = false; importStatus.textContent = ui.subjectImportFeedback;
        importStatus.dataset.valid = String(ui.subjectImportValid !== false);
        delete ui.subjectImportFeedback;
    }
    const voiceAssets = (project.assets ?? []).filter((asset) => asset.type === "audio");
    const voiceInput = document.createElement("input");
    voiceInput.type = "file"; voiceInput.accept = "audio/*"; voiceInput.hidden = true;
    const importVoice = actionButton("+ Upload voice", () => voiceInput.click());
    importVoice.disabled = typeof controller.uploadReferenceFile !== "function";
    const chooseVoice = actionButton("Choose from Files", () => {
        ui.subjectAssetChooser = { target: "voice", subjectId: subject.id };
        rerender();
    });
    voiceInput.addEventListener("change", async () => {
        const file = voiceInput.files?.[0];
        if (!file) return;
        importVoice.disabled = true; importVoice.textContent = "Importing…";
        const result = await importEntityAsset(controller, project, file, "audio", (nextProject, assetId) => {
            nextProject.subjects.find((item) => item.id === subject.id).defaultVoiceAssetId = assetId;
            ensureSubjectBindings(nextProject, controller.shotDocument?.()?.value ?? {}, subject.id);
        });
        ui.subjectImportFeedback = result.message; ui.subjectImportValid = result.ok;
        if (result.ok) ui.subjectSelectedId = subject.id;
        rerender();
    });
    const voiceHeading = element("div", "minimax-h3-entity-media-heading");
    const voiceActions = element("div", "minimax-h3-entity-media-actions");
    voiceActions.append(importVoice, chooseVoice, voiceInput);
    voiceHeading.append(element("strong", "", "Default voice"), voiceActions);
    identity.body.append(
        voiceHeading,
        assignedAssetGallery({
            assets: voiceAssets, controller, selectedIds: subject.defaultVoiceAssetId ? [subject.defaultVoiceAssetId] : [],
            ariaLabel: `Default voice connected to ${subject.name || subject.id}`,
            emptyMessage: "No default voice. Shots can still use written dialogue or a Shot-specific voice.",
            onUnlink: () => { delete subject.defaultVoiceAssetId; commit(); rerender(); },
        }),
        element("p", "minimax-h3-field-hint", "Inherited whenever this subject is active; a Shot can override it."),
    );
    if (ui.subjectAssetChooser?.target === "voice" && ui.subjectAssetChooser.subjectId === subject.id) {
        identity.body.appendChild(assetChooserPanel({
            assets: voiceAssets, controller, selectedIds: subject.defaultVoiceAssetId ? [subject.defaultVoiceAssetId] : [],
            ariaLabel: `Choose a default voice for ${subject.name || subject.id}`,
            usageForAsset: (assetId) => assetUsage(project, assetId),
            onChoose: (assetId) => {
                subject.defaultVoiceAssetId = assetId;
                ensureSubjectBindings(project, controller.shotDocument?.()?.value ?? {}, subject.id);
                delete ui.subjectAssetChooser; commit(); rerender();
            },
            onClose: () => { delete ui.subjectAssetChooser; rerender(); },
        }));
    }
    const selectedVoiceAsset = voiceAssets.find((asset) => asset.id === subject.defaultVoiceAssetId);
    if (selectedVoiceAsset) {
        const source = referenceSourceForAsset(controller.referenceDirectorDocument?.()?.value, selectedVoiceAsset.id);
        identity.body.appendChild(renderAudioTrimEditor({
            asset: selectedVoiceAsset,
            url: sourcePreviewUrl(source),
            label: `${subject.name || subject.id} · Default voice fragment`,
            onChange: (clip, sourceDuration) => {
                applyAudioClipToAsset(selectedVoiceAsset, clip, sourceDuration);
                commit();
            },
        }));
    }
    inspector.appendChild(identity.details);

    const promptUse = inspectorSection("Casting & prompt use", "Advanced · generation activation", false);
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
    const statesHeading = element("div", "minimax-h3-studio-toolbar");
    statesHeading.append(element("strong", "", "Looks"), element("span", "minimax-h3-field-hint", "Reusable appearance states for Shot casting"), actionButton("+ Look", () => {
        const id = uniqueId(subject.appearanceStates ?? [], "state.");
        (subject.appearanceStates ??= []).push({ id, name: "New appearance", controls: [], attributes: {} });
        commit(); rerender(id);
    }));
    inspector.appendChild(statesHeading);
    for (const appearance of subject.appearanceStates ?? []) {
        renderAppearanceState(inspector, subject, appearance, project, uses, commit, rerender, ui.subjectAppearanceId, controller, ui);
    }
    inspector.appendChild(promptUse.details);

    const subjectActions = element("div", "minimax-h3-studio-toolbar");
    subjectActions.appendChild(actionButton("Duplicate subject", () => {
        const copy = structuredClone(subject);
        copy.id = uniqueId(project.subjects, "subject."); copy.h3Index = nextH3Index([...(project.subjects ?? []), ...(project.props ?? [])]); copy.name = `${subject.name} copy`;
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
