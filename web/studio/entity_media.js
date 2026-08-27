import { element } from "./domain_components.js";
import {
    emptyReferenceDirector, mediaTypeForFile, referenceSourceForAsset, setReferenceSource, sourcePreviewUrl,
} from "./reference_sources.js";
import { uniqueId } from "./project_editor.js";

function directorForController(controller) {
    const documentState = controller.referenceDirectorDocument?.();
    return documentState?.kind === "v1" ? documentState.value : emptyReferenceDirector();
}

function assetPreview(asset, controller, { audioControls = true } = {}) {
    const preview = element("span", "minimax-h3-visual-asset-preview");
    const director = directorForController(controller);
    const source = referenceSourceForAsset(director, asset.id);
    const url = sourcePreviewUrl(source);
    if (url && asset.type === "picture") {
        const image = element("img");
        image.src = url;
        image.alt = asset.name || asset.id;
        image.loading = "lazy";
        preview.appendChild(image);
    } else if (url && asset.type === "audio" && audioControls) {
        const audio = document.createElement("audio");
        audio.src = url;
        audio.controls = true;
        audio.preload = "metadata";
        preview.appendChild(audio);
    } else preview.appendChild(element("strong", "", asset.type === "audio" ? "≋" : "▧"));
    return { preview, source };
}

function assetCopy(asset, source, status = "") {
    const copy = element("span", "minimax-h3-visual-asset-copy");
    copy.append(
        element("strong", "", asset.name || asset.id),
        element("small", "", status || (source ? "Ready" : "Missing file")),
    );
    return copy;
}

export function assignedAssetGallery({ assets, controller, selectedIds = [], onUnlink, ariaLabel, emptyMessage = "No references connected yet.", primary = false }) {
    const root = element("div", "minimax-h3-assigned-media-gallery");
    root.setAttribute("role", "list");
    root.setAttribute("aria-label", ariaLabel);
    const byId = new Map((assets ?? []).map((asset) => [asset.id, asset]));
    const assigned = selectedIds.map((id) => byId.get(id)).filter(Boolean);
    for (const [index, asset] of assigned.entries()) {
        const tile = element("article", "minimax-h3-assigned-media-tile");
        tile.setAttribute("role", "listitem");
        const { preview, source } = assetPreview(asset, controller);
        const heading = assetCopy(asset, source, primary && index === 0 ? "Primary identity" : "Connected");
        const unlink = element("button", "minimax-h3-media-unlink", "Unlink");
        unlink.type = "button";
        unlink.title = `Unlink ${asset.name || asset.id}. The file remains in Library · Files.`;
        unlink.addEventListener("click", () => onUnlink?.(asset.id));
        tile.append(preview, heading, unlink);
        root.appendChild(tile);
    }
    if (!assigned.length) root.appendChild(element("p", "minimax-h3-assigned-media-empty", emptyMessage));
    return root;
}

export function assetChooserPanel({ assets, controller, selectedIds = [], onChoose, onClose, ariaLabel, multiple = false, usageForAsset = () => [] }) {
    const root = element("section", "minimax-h3-asset-chooser");
    root.setAttribute("aria-label", ariaLabel);
    const heading = element("div", "minimax-h3-asset-chooser-heading");
    const headingCopy = element("span", "");
    headingCopy.append(element("strong", "", ariaLabel), element("small", "", "Files are global; choosing one only links it here."));
    const close = element("button", "minimax-h3-asset-chooser-close", "Close");
    close.type = "button";
    close.addEventListener("click", () => onClose?.());
    heading.append(headingCopy, close);
    const search = document.createElement("input");
    search.type = "search";
    search.placeholder = "Search compatible files…";
    search.setAttribute("aria-label", "Search compatible files");
    const filters = element("div", "minimax-h3-asset-chooser-filters");
    const filter = document.createElement("select");
    filter.setAttribute("aria-label", "Filter files by usage");
    for (const [value, label] of [["all", "All files"], ["unused", "Unused"], ["used", "Already used"]]) {
        const option = document.createElement("option"); option.value = value; option.textContent = label; filter.appendChild(option);
    }
    filters.append(search, filter);
    const grid = element("div", "minimax-h3-visual-asset-picker");
    grid.setAttribute("role", "listbox");
    grid.setAttribute("aria-label", ariaLabel);
    const selected = new Set(selectedIds);
    for (const asset of assets ?? []) {
        const uses = usageForAsset(asset.id) ?? [];
        const tile = element("button", "minimax-h3-visual-asset-tile");
        tile.type = "button";
        tile.dataset.selected = String(selected.has(asset.id));
        tile.dataset.search = `${asset.name || asset.id} ${uses.join(" ")}`.toLowerCase();
        tile.dataset.used = String(uses.length > 0);
        tile.setAttribute("role", "option");
        tile.setAttribute("aria-selected", String(selected.has(asset.id)));
        const { preview, source } = assetPreview(asset, controller, { audioControls: false });
        const status = selected.has(asset.id) ? "Connected here" : uses[0] || (source ? "Unused" : "Missing file");
        const copy = assetCopy(asset, source, status);
        tile.append(preview, copy);
        tile.addEventListener("click", () => onChoose?.(asset.id, { multiple, selected: selected.has(asset.id) }));
        grid.appendChild(tile);
    }
    const applyFilter = () => {
        const query = String(search.value ?? "").trim().toLowerCase();
        for (const tile of grid.children ?? []) {
            const matchesText = !query || String(tile.dataset?.search ?? "").includes(query);
            const matchesUse = filter.value === "all" || (filter.value === "used" ? tile.dataset?.used === "true" : tile.dataset?.used !== "true");
            tile.hidden = !(matchesText && matchesUse);
        }
    };
    search.addEventListener("input", applyFilter);
    filter.addEventListener("change", applyFilter);
    root.append(heading, filters, grid);
    if (!(assets ?? []).length) root.appendChild(element("p", "minimax-h3-assigned-media-empty", "No compatible files yet. Import one from this field or Library · Files."));
    return root;
}

// Kept as a compatibility export for third-party callers. New entity editors
// should use assignedAssetGallery + assetChooserPanel so global media never
// masquerades as media already belonging to an entity.
export function visualAssetPicker({ assets, controller, selectedIds = [], onChange, multiple = true, ariaLabel }) {
    const selected = new Set(selectedIds);
    return assetChooserPanel({
        assets, controller, selectedIds, multiple, ariaLabel,
        onChoose: (assetId) => {
            if (!multiple) return onChange(selected.has(assetId) ? "" : assetId);
            if (selected.has(assetId)) selected.delete(assetId); else selected.add(assetId);
            onChange([...selected]);
        },
    });
}

export async function importEntityAsset(controller, project, file, expectedType, attach) {
    if (!file) return { ok: false, message: "Choose a file first." };
    const actualType = mediaTypeForFile(file);
    if (actualType !== expectedType) return { ok: false, message: `This field accepts ${expectedType === "picture" ? "images" : "audio"} only.` };
    if (typeof controller.uploadReferenceFile !== "function" || typeof controller.replaceProjectBundleAtomically !== "function") {
        return { ok: false, message: "Reference import is unavailable for this node." };
    }
    try {
        const source = await controller.uploadReferenceFile(file);
        const nextProject = structuredClone(project);
        const assetId = uniqueId(nextProject.assets ??= [], "asset.");
        const name = String(file.name).replace(/\.[^.]+$/, "") || `${expectedType} reference`;
        nextProject.assets.push({ id: assetId, type: expectedType, name, available: true });
        attach(nextProject, assetId);
        const nextDirector = setReferenceSource(directorForController(controller), assetId, source);
        const result = controller.replaceProjectBundleAtomically({ mediaProject: nextProject, referenceDirector: nextDirector });
        if (!result?.ok) return { ok: false, message: result?.message || "Could not save the imported reference." };
        return { ok: true, assetId, message: `${name} imported and connected.` };
    } catch (error) {
        return { ok: false, message: error?.message ?? "Reference upload failed." };
    }
}
