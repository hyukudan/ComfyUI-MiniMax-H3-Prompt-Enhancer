import {
    actionButton, bindCommit, createMasterDetail, element, emptyState, field, inspectorSection,
    selectInput, setOptional, textArea, textInput,
} from "./domain_components.js";
import { assetChooserPanel, assignedAssetGallery, importEntityAsset } from "./entity_media.js";
import { assetUsage } from "./media_model.js";
import { commitProject, projectForController, readOnlyProjectMessage, uniqueId } from "./project_editor.js";
import { ensurePropDesignBindings } from "./prop_model.js";
import { referenceSourceForAsset, sourcePreviewUrl } from "./reference_sources.js";

const CATEGORIES = [
    ["object", "Object / prop"], ["vehicle", "Vehicle"], ["product", "Product"],
    ["furniture", "Furniture"], ["weapon", "Weapon"], ["other", "Other"],
];

function nextH3Index(project) {
    const entities = [...(project.subjects ?? []), ...(project.props ?? [])];
    const used = new Set(entities.map((entity) => Number(entity.h3Index)));
    for (let index = 1; index <= 64; index += 1) if (!used.has(index)) return index;
    return 64;
}

export function createPropDraft(project, name = "New prop") {
    const props = project.props ??= [];
    return {
        id: uniqueId(props, "prop."), h3Index: nextH3Index(project),
        name: String(name).trim() || "New prop", category: "object", description: "", designAssetIds: [],
    };
}

function shotUses(controller, propId) {
    const plan = controller.shotDocument?.()?.value;
    return (plan?.shots ?? []).filter((shot) => (shot.props ?? []).some((use) => use.propId === propId && use.presence !== "absent"));
}

export function renderPropsTab(container, controller) {
    container.replaceChildren();
    const project = projectForController(controller);
    if (!project) return readOnlyProjectMessage(container, controller.projectDocument(), controller);
    const props = project.props ??= [];
    const ui = controller.projectUiState;
    if (!ui.propSelectedId || !props.some((item) => item.id === ui.propSelectedId)) ui.propSelectedId = props[0]?.id ?? null;
    const commit = () => commitProject(controller);
    const rerender = () => renderPropsTab(container, controller);

    const toolbar = element("div", "minimax-h3-studio-toolbar");
    const add = actionButton("+ Prop", () => {
        const prop = createPropDraft(project); props.push(prop); ui.propSelectedId = prop.id; commit(); rerender();
    }, { disabled: props.length >= 64 });
    toolbar.append(add, element("span", "minimax-h3-field-hint", `${props.length}/64 props`));
    container.appendChild(toolbar);
    if (!props.length) {
        container.appendChild(emptyState(
            "No props yet",
            "Create a reusable car, product or object, attach its design pictures here, then add and mention it from any Shot.",
            actionButton("Create prop", () => add.click()),
        ));
        return;
    }

    const { grid, master, inspector } = createMasterDetail();
    for (const prop of props) {
        const uses = shotUses(controller, prop.id);
        const row = element("button", "minimax-h3-master-row minimax-h3-subject-master-row");
        row.type = "button"; row.setAttribute("role", "option"); row.setAttribute("aria-selected", String(prop.id === ui.propSelectedId));
        row.addEventListener("click", () => { ui.propSelectedId = prop.id; rerender(); });
        const asset = (prop.designAssetIds ?? []).map((id) => project.assets?.find((item) => item.id === id)).find(Boolean);
        const url = sourcePreviewUrl(asset ? referenceSourceForAsset(controller.referenceDirectorDocument?.()?.value, asset.id) : null);
        const avatar = element("span", "minimax-h3-subject-master-avatar");
        if (url) { const image = element("img"); image.src = url; image.alt = ""; image.loading = "lazy"; avatar.appendChild(image); }
        else avatar.textContent = "◇";
        const copy = element("span", "minimax-h3-subject-master-copy");
        copy.append(element("span", "", prop.name || prop.id), element("small", "", `${prop.designAssetIds?.length ?? 0} design pictures · ${uses.length} shots`));
        row.append(avatar, copy); master.appendChild(row);
    }
    const prop = props.find((item) => item.id === ui.propSelectedId);
    const identity = inspectorSection("Object identity", "Reusable visual design", true);
    identity.body.appendChild(element("p", "minimax-h3-field-hint", "Prompt Studio keeps this object's design stable and assigns its image outputs automatically."));
    const name = textInput(prop.name); bindCommit(name, (value) => { prop.name = value.trim() || prop.id; }, commit); name.addEventListener("change", rerender);
    const category = selectInput(prop.category ?? "object", CATEGORIES); bindCommit(category, (value) => { prop.category = value; }, commit);
    const description = textArea(prop.description, "Stable, visible design: shape, colour, materials and distinctive details");
    bindCommit(description, (value) => setOptional(prop, "description", value.trim()), commit, "blur");
    identity.body.append(field("Name", name), field("Category", category), field("Stable physical design", description));

    const pictures = (project.assets ?? []).filter((asset) => asset.type === "picture");
    const heading = element("div", "minimax-h3-entity-media-heading");
    const actions = element("div", "minimax-h3-entity-media-actions");
    const input = document.createElement("input"); input.type = "file"; input.accept = "image/*"; input.hidden = true;
    const upload = actionButton("+ Upload design picture", () => input.click(), { disabled: typeof controller.uploadReferenceFile !== "function" });
    const choose = actionButton("Choose from Files", () => { ui.propAssetChooserId = prop.id; rerender(); });
    input.addEventListener("change", async () => {
        const file = input.files?.[0]; if (!file) return;
        upload.disabled = true; upload.textContent = "Importing…";
        const result = await importEntityAsset(controller, project, file, "picture", (nextProject, assetId) => {
            const nextProp = (nextProject.props ?? []).find((item) => item.id === prop.id);
            (nextProp.designAssetIds ??= []).push(assetId);
            ensurePropDesignBindings(nextProject, controller.shotDocument?.()?.value ?? {}, prop.id);
        });
        ui.propImportFeedback = result.message; ui.propImportValid = result.ok; delete ui.propAssetChooserId; rerender();
    });
    actions.append(upload, choose, input); heading.append(element("strong", "", "Design pictures"), actions); identity.body.appendChild(heading);
    identity.body.appendChild(assignedAssetGallery({
        assets: pictures, controller, selectedIds: prop.designAssetIds ?? [], primary: true,
        ariaLabel: `Design pictures connected to ${prop.name || prop.id}`,
        emptyMessage: "This prop has no design picture yet.",
        onUnlink: (assetId) => { prop.designAssetIds = (prop.designAssetIds ?? []).filter((id) => id !== assetId); commit(); rerender(); },
    }));
    if (ui.propAssetChooserId === prop.id) identity.body.appendChild(assetChooserPanel({
        assets: pictures, controller, selectedIds: prop.designAssetIds ?? [], multiple: true,
        ariaLabel: `Choose design pictures for ${prop.name || prop.id}`,
        usageForAsset: (assetId) => assetUsage(project, assetId),
        onChoose: (assetId) => {
            const selected = new Set(prop.designAssetIds ?? []);
            if (selected.has(assetId)) selected.delete(assetId); else selected.add(assetId);
            prop.designAssetIds = [...selected];
            const bindingResult = ensurePropDesignBindings(project, controller.shotDocument?.()?.value ?? {}, prop.id);
            if (bindingResult.issues.length) { ui.propImportFeedback = bindingResult.issues.join(" "); ui.propImportValid = false; }
            commit(); rerender();
        },
        onClose: () => { delete ui.propAssetChooserId; rerender(); },
    }));
    if (ui.propImportFeedback) {
        const feedback = element("p", "minimax-h3-studio-status", ui.propImportFeedback);
        feedback.dataset.valid = String(ui.propImportValid !== false); identity.body.appendChild(feedback); delete ui.propImportFeedback;
    }
    inspector.appendChild(identity.details);

    const uses = shotUses(controller, prop.id);
    const footer = element("div", "minimax-h3-studio-toolbar");
    footer.appendChild(actionButton("Duplicate prop", () => {
        const copy = structuredClone(prop); copy.id = uniqueId(props, "prop."); copy.h3Index = nextH3Index(project); copy.name = `${prop.name} copy`;
        props.push(copy); ui.propSelectedId = copy.id; commit(); rerender();
    }));
    footer.appendChild(actionButton("Delete prop", () => {
        props.splice(props.indexOf(prop), 1); ui.propSelectedId = null; commit(); rerender();
    }, { danger: true, disabled: uses.length > 0 }));
    inspector.appendChild(footer);
    if (uses.length) inspector.appendChild(element("p", "minimax-h3-usage-note", `Cannot delete. Used by: ${uses.map((shot) => shot.title || shot.id).join(", ")}`));
    grid.append(master, inspector); container.appendChild(grid);
}
