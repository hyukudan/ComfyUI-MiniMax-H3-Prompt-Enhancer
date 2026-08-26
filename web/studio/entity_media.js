import { element } from "./domain_components.js";
import {
    emptyReferenceDirector, mediaTypeForFile, referenceSourceForAsset, setReferenceSource, sourcePreviewUrl,
} from "./reference_sources.js";
import { uniqueId } from "./project_editor.js";

function directorForController(controller) {
    const documentState = controller.referenceDirectorDocument?.();
    return documentState?.kind === "v1" ? documentState.value : emptyReferenceDirector();
}

export function visualAssetPicker({ assets, controller, selectedIds = [], onChange, multiple = true, ariaLabel }) {
    const root = element("div", "minimax-h3-visual-asset-picker");
    root.setAttribute("role", "group");
    root.setAttribute("aria-label", ariaLabel);
    const selected = new Set(selectedIds);
    const director = directorForController(controller);
    for (const asset of assets) {
        const tile = element("label", "minimax-h3-visual-asset-tile");
        const input = document.createElement("input");
        input.type = multiple ? "checkbox" : "radio";
        input.name = multiple ? "" : ariaLabel;
        input.checked = selected.has(asset.id);
        tile.dataset.selected = String(input.checked);
        const preview = element("span", "minimax-h3-visual-asset-preview");
        const source = referenceSourceForAsset(director, asset.id);
        const url = sourcePreviewUrl(source);
        if (url && asset.type === "picture") {
            const image = element("img");
            image.src = url;
            image.alt = asset.name || asset.id;
            image.loading = "lazy";
            preview.appendChild(image);
        } else preview.appendChild(element("strong", "", asset.type === "audio" ? "≋" : "▧"));
        const copy = element("span", "minimax-h3-visual-asset-copy");
        copy.append(element("strong", "", asset.name || asset.id), element("small", "", source ? "Ready" : "Missing file"));
        input.addEventListener("change", () => {
            if (multiple) {
                if (input.checked) selected.add(asset.id); else selected.delete(asset.id);
                onChange([...selected]);
            } else onChange(input.checked ? asset.id : "");
        });
        tile.append(input, preview, copy);
        root.appendChild(tile);
    }
    if (!assets.length) root.appendChild(element("p", "minimax-h3-field-hint", "No compatible references yet. Import one here."));
    return root;
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
