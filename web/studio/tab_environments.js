import {
    actionButton, bindCommit, captureOpenDisclosures, createMasterDetail, element, emptyState, field, inspectorSection,
    restoreOpenDisclosures, selectInput, setOptional, textArea, textInput, tokenList,
} from "./domain_components.js";
import { usageIndex } from "./derive.js";
import { assetChooserPanel, assignedAssetGallery, importEntityAsset } from "./entity_media.js";
import { assetUsage } from "./media_model.js";
import { commitProject, projectForController, readOnlyProjectMessage, uniqueId } from "./project_editor.js";
import { referenceSourceForAsset, sourcePreviewUrl } from "./reference_sources.js";
import { ensureEnvironmentViewBindings } from "./environment_model.js";

const VIEW_ROLES = [["overview", "Overview"], ["alternate", "Alternate"], ["detail", "Detail"], ["lighting", "Lighting"], ["custom", "Custom"]];
const TEMPORARY_FIELDS = [
    ["lighting", "Lighting"], ["weather", "Weather"], ["atmosphere", "Atmosphere"],
    ["condition", "Condition"], ["timeOfDay", "Time of day"], ["other", "Other temporary detail"],
];

export function createEnvironmentDraft(project, name = "New environment") {
    const id = uniqueId(project.environments, "environment.");
    return {
        id, name: String(name ?? "").trim() || "New environment", permanent: {}, views: [], defaultStateId: "base",
        states: [{ id: "base", name: "Base", temporary: {} }],
    };
}

function renderView(container, environment, view, project, uses, commit, rerender, controller) {
    const section = inspectorSection(view.name || view.id, view.role || "View", false);
    section.body.appendChild(element("p", "minimax-h3-field-hint", "A reusable visual angle of this Place."));
    const name = textInput(view.name); bindCommit(name, (value) => { view.name = value.trim() || view.id; }, commit);
    name.addEventListener("change", rerender);
    const role = selectInput(view.role, VIEW_ROLES); bindCommit(role, (value) => { view.role = value; }, commit);
    const pictures = (project.assets ?? []).filter((asset) => asset.type === "picture");
    const ui = controller.projectUiState;
    const pictureHeading = element("div", "minimax-h3-entity-media-heading");
    const pictureActions = element("div", "minimax-h3-entity-media-actions");
    const pictureInput = document.createElement("input");
    pictureInput.type = "file"; pictureInput.accept = "image/*"; pictureInput.hidden = true;
    const importPicture = actionButton("+ Upload picture", () => pictureInput.click(), { disabled: typeof controller.uploadReferenceFile !== "function" });
    const choosePicture = actionButton("Choose from Files", () => {
        ui.environmentAssetChooser = { target: "view", environmentId: environment.id, viewId: view.id };
        rerender();
    });
    pictureInput.addEventListener("change", async () => {
        const file = pictureInput.files?.[0];
        if (!file) return;
        importPicture.disabled = true; importPicture.textContent = "Importing…";
        const result = await importEntityAsset(controller, project, file, "picture", (nextProject, assetId) => {
            const nextEnvironment = nextProject.environments.find((item) => item.id === environment.id);
            nextEnvironment.views.find((item) => item.id === view.id).assetId = assetId;
            ensureEnvironmentViewBindings(nextProject, controller.shotDocument?.()?.value ?? {}, environment.id);
        });
        ui.environmentImportFeedback = result.message; ui.environmentImportValid = result.ok;
        delete ui.environmentAssetChooser;
        rerender();
    });
    pictureActions.append(importPicture, choosePicture, pictureInput);
    pictureHeading.append(element("strong", "", "View picture"), pictureActions);
    const description = textArea(view.description, "What this view establishes");
    bindCommit(description, (value) => setOptional(view, "description", value.trim()), commit, "blur");
    section.body.append(
        field("View name", name), field("Role", role), pictureHeading,
        assignedAssetGallery({
            assets: pictures, controller, selectedIds: view.assetId ? [view.assetId] : [],
            ariaLabel: `Picture connected to ${view.name || view.id}`,
            emptyMessage: "This environment view has no picture yet.",
            onUnlink: () => { view.assetId = ""; commit(); rerender(); },
        }),
    );
    const chooser = ui.environmentAssetChooser;
    if (chooser?.target === "view" && chooser.environmentId === environment.id && chooser.viewId === view.id) {
        section.body.appendChild(assetChooserPanel({
            assets: pictures, controller, selectedIds: view.assetId ? [view.assetId] : [],
            ariaLabel: `Choose a picture for ${view.name || view.id}`,
            usageForAsset: (assetId) => assetUsage(project, assetId),
            onChoose: (assetId) => {
                view.assetId = assetId;
                ensureEnvironmentViewBindings(project, controller.shotDocument?.()?.value ?? {}, environment.id);
                delete ui.environmentAssetChooser; commit(); rerender();
            },
            onClose: () => { delete ui.environmentAssetChooser; rerender(); },
        }));
    }
    section.body.appendChild(field("Description", description));
    const viewUses = uses.environmentViews.get(`${environment.id}:${view.id}`) ?? [];
    section.body.appendChild(actionButton("Delete view", () => {
        environment.views.splice(environment.views.indexOf(view), 1); commit(); rerender();
    }, { danger: true, disabled: viewUses.length > 0 }));
    if (viewUses.length) section.body.appendChild(element("p", "minimax-h3-usage-note", `Cannot delete. Used by: ${viewUses.join(", ")}`));
    container.appendChild(section.details);
}

function renderState(container, environment, environmentState, uses, commit, rerender) {
    const isDefault = environmentState.id === environment.defaultStateId;
    const section = inspectorSection(environmentState.name || environmentState.id, isDefault ? "Default" : "Temporary state", isDefault);
    section.body.appendChild(element("p", "minimax-h3-field-hint", "Temporary states do not redefine permanent geography or architecture."));
    const name = textInput(environmentState.name); bindCommit(name, (value) => { environmentState.name = value.trim() || environmentState.id; }, commit);
    name.addEventListener("change", rerender);
    const extendsState = selectInput(environmentState.extends ?? "", [
        ["", "No parent state"],
        ...(environment.states ?? []).filter((item) => item !== environmentState).map((item) => [item.id, item.name || item.id]),
    ]);
    bindCommit(extendsState, (value) => setOptional(environmentState, "extends", value), commit);
    section.body.append(field("State name", name), field("Extends", extendsState));
    environmentState.temporary ??= {};
    for (const [key, label] of TEMPORARY_FIELDS) {
        const control = key === "other" ? textArea(environmentState.temporary[key]) : textInput(environmentState.temporary[key]);
        bindCommit(control, (value) => setOptional(environmentState.temporary, key, value.trim()), commit, key === "other" ? "blur" : "change");
        section.body.appendChild(field(label, control));
    }
    section.body.appendChild(field("Temporary elements", tokenList(environmentState.temporary.temporaryElements, (items) => {
        if (items.length) environmentState.temporary.temporaryElements = items; else delete environmentState.temporary.temporaryElements;
        commit(); rerender();
    }, "Add a temporary element")));
    const actions = element("div", "minimax-h3-studio-toolbar");
    actions.appendChild(actionButton("Duplicate state", () => {
        const copy = structuredClone(environmentState);
        copy.id = uniqueId(environment.states, `${environmentState.id}.copy.`); copy.name = `${environmentState.name} copy`;
        environment.states.push(copy); commit(); rerender();
    }));
    const stateUses = uses.environmentStates.get(`${environment.id}:${environmentState.id}`) ?? [];
    actions.appendChild(actionButton("Delete state", () => {
        environment.states.splice(environment.states.indexOf(environmentState), 1); commit(); rerender();
    }, { danger: true, disabled: isDefault || stateUses.length > 0 }));
    section.body.appendChild(actions);
    if (isDefault) section.body.appendChild(element("p", "minimax-h3-usage-note", "The default state cannot be deleted."));
    else if (stateUses.length) section.body.appendChild(element("p", "minimax-h3-usage-note", `Cannot delete. Used by: ${stateUses.join(", ")}`));
    container.appendChild(section.details);
}

export function renderEnvironmentsTab(container, controller) {
    container.replaceChildren();
    const project = projectForController(controller);
    if (!project) return readOnlyProjectMessage(container, controller.projectDocument(), controller);
    const ui = controller.projectUiState;
    const shotDocument = controller.shotDocument?.();
    const uses = usageIndex(project, shotDocument?.kind === "v2" ? shotDocument.value : {});
    if (!ui.environmentSelectedId || !project.environments.some((item) => item.id === ui.environmentSelectedId)) {
        ui.environmentSelectedId = project.environments[0]?.id ?? null;
    }
    const commit = () => commitProject(controller);
    const rerender = () => {
        ui.environmentPanelScroll = container.scrollTop;
        ui.environmentOpenDisclosures = captureOpenDisclosures(container);
        renderEnvironmentsTab(container, controller);
    };
    const toolbar = element("div", "minimax-h3-studio-toolbar");
    const addEnvironment = actionButton("+ Environment", () => {
        const environment = createEnvironmentDraft(project); project.environments.push(environment); ui.environmentSelectedId = environment.id; commit(); rerender();
    }, { disabled: project.environments.length >= 64 });
    toolbar.append(addEnvironment, element("span", "minimax-h3-field-hint", `${project.environments.length}/64 environments`));
    container.appendChild(toolbar);
    if (!project.environments.length) {
        const emptyAdd = actionButton("Create environment", () => addEnvironment.click());
        container.appendChild(emptyState("No environments yet", "Separate permanent geography and architecture from weather, lighting and other temporary states.", emptyAdd));
        return;
    }

    const { grid, master, inspector } = createMasterDetail();
    for (const environment of project.environments) {
        const environmentUses = uses.environments.get(environment.id) ?? [];
        const row = element("button", "minimax-h3-master-row minimax-h3-subject-master-row");
        row.type = "button"; row.setAttribute("role", "option"); row.setAttribute("aria-selected", String(environment.id === ui.environmentSelectedId));
        row.addEventListener("click", () => { ui.environmentSelectedId = environment.id; rerender(); });
        const view = (environment.views ?? [])[0];
        const asset = project.assets?.find((item) => item.id === view?.assetId);
        const url = sourcePreviewUrl(asset ? referenceSourceForAsset(controller.referenceDirectorDocument?.()?.value, asset.id) : null);
        const avatar = element("span", "minimax-h3-subject-master-avatar");
        if (url) { const image = element("img"); image.src = url; image.alt = ""; image.loading = "lazy"; avatar.appendChild(image); }
        else avatar.textContent = "⌂";
        const copy = element("span", "minimax-h3-subject-master-copy");
        copy.append(element("span", "", environment.name || environment.id), element("small", "", `${environment.views?.length ?? 0} views · ${environment.states?.length ?? 0} states · ${environmentUses.length} uses`));
        row.append(avatar, copy); master.appendChild(row);
    }
    const environment = project.environments.find((item) => item.id === ui.environmentSelectedId);
    const permanent = inspectorSection("Permanent", environment.name || environment.id, true);
    permanent.body.appendChild(element("p", "minimax-h3-field-hint", "These details remain fixed across every temporary state."));
    const name = textInput(environment.name); bindCommit(name, (value) => { environment.name = value.trim() || environment.id; }, commit);
    name.addEventListener("change", rerender);
    permanent.body.appendChild(field("Name", name));
    environment.permanent ??= {};
    for (const [key, label, multiline] of [
        ["geography", "Geography", true], ["architecture", "Architecture", true], ["scale", "Scale", false], ["other", "Other permanent detail", true],
    ]) {
        const control = multiline ? textArea(environment.permanent[key]) : textInput(environment.permanent[key]);
        bindCommit(control, (value) => setOptional(environment.permanent, key, value.trim()), commit, multiline ? "blur" : "change");
        permanent.body.appendChild(field(label, control));
    }
    permanent.body.appendChild(field("Fixed elements", tokenList(environment.permanent.fixedElements, (items) => {
        if (items.length) environment.permanent.fixedElements = items; else delete environment.permanent.fixedElements;
        commit(); rerender();
    }, "Add a fixed element")));
    inspector.appendChild(permanent.details);

    const pictures = (project.assets ?? []).filter((asset) => asset.type === "picture");
    const viewsHeading = element("div", "minimax-h3-studio-toolbar");
    const addView = actionButton("+ View", () => {
        const id = uniqueId(environment.views ?? [], "view.");
        (environment.views ??= []).push({ id, name: "New view", role: "overview", assetId: pictures[0].id });
        commit(); rerender();
    }, { disabled: !pictures.length || environment.views?.length >= 24 });
    const viewInput = document.createElement("input"); viewInput.type = "file"; viewInput.accept = "image/*"; viewInput.hidden = true;
    const importView = actionButton("+ Import view picture", () => viewInput.click(), { disabled: typeof controller.uploadReferenceFile !== "function" || environment.views?.length >= 24 });
    viewInput.addEventListener("change", async () => {
        const file = viewInput.files?.[0];
        if (!file) return;
        importView.disabled = true; importView.textContent = "Importing…";
        const result = await importEntityAsset(controller, project, file, "picture", (nextProject, assetId) => {
            const nextEnvironment = nextProject.environments.find((item) => item.id === environment.id);
            const id = uniqueId(nextEnvironment.views ??= [], "view.");
            nextEnvironment.views.push({ id, name: String(file.name).replace(/\.[^.]+$/, "") || "New view", role: "overview", assetId });
            ensureEnvironmentViewBindings(nextProject, controller.shotDocument?.()?.value ?? {}, environment.id);
        });
        ui.environmentImportFeedback = result.message; ui.environmentImportValid = result.ok;
        if (result.ok) ui.environmentSelectedId = environment.id;
        rerender();
    });
    viewsHeading.append(element("strong", "", "Views"), addView, importView, viewInput);
    inspector.appendChild(viewsHeading);
    if (!pictures.length) inspector.appendChild(element("p", "minimax-h3-usage-note", "Import a view picture here to create the first visual view."));
    if (ui.environmentImportFeedback) {
        const feedback = element("p", "minimax-h3-studio-status", ui.environmentImportFeedback);
        feedback.dataset.valid = String(ui.environmentImportValid !== false); inspector.appendChild(feedback);
        delete ui.environmentImportFeedback;
    }
    for (const view of environment.views ?? []) renderView(inspector, environment, view, project, uses, commit, rerender, controller);

    const statesHeading = element("div", "minimax-h3-studio-toolbar");
    statesHeading.append(element("strong", "", "Temporary states"), actionButton("+ Temporary state", () => {
        const id = uniqueId(environment.states ?? [], "state.");
        (environment.states ??= []).push({ id, name: "New state", temporary: {} }); commit(); rerender();
    }, { disabled: environment.states?.length >= 64 }));
    inspector.appendChild(statesHeading);
    const defaultState = selectInput(environment.defaultStateId, (environment.states ?? []).map((state) => [state.id, state.name || state.id]));
    defaultState.addEventListener("change", () => { environment.defaultStateId = defaultState.value; commit(); rerender(); });
    inspector.appendChild(field("Default state", defaultState));
    for (const state of environment.states ?? []) renderState(inspector, environment, state, uses, commit, rerender);

    const actions = element("div", "minimax-h3-studio-toolbar");
    actions.appendChild(actionButton("Duplicate environment", () => {
        const copy = structuredClone(environment); copy.id = uniqueId(project.environments, "environment."); copy.name = `${environment.name} copy`;
        project.environments.push(copy); ui.environmentSelectedId = copy.id; commit(); rerender();
    }));
    const environmentUses = uses.environments.get(environment.id) ?? [];
    actions.appendChild(actionButton("Delete environment", () => {
        project.environments.splice(project.environments.indexOf(environment), 1); ui.environmentSelectedId = null; commit(); rerender();
    }, { danger: true, disabled: environmentUses.length > 0 }));
    inspector.appendChild(actions);
    if (environmentUses.length) inspector.appendChild(element("p", "minimax-h3-usage-note", `Cannot delete. Used by: ${environmentUses.join(", ")}`));
    container.appendChild(grid);
    restoreOpenDisclosures(container, ui.environmentOpenDisclosures);
    if (ui.environmentPanelScroll !== undefined) container.scrollTop = ui.environmentPanelScroll;
}
