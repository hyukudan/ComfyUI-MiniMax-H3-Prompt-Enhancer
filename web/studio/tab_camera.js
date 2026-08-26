import { renderCameraDataFallback, renderVisualCameraPlanner } from "./camera_planner.js";
import { actionButton, element, emptyState, field, selectInput } from "./domain_components.js";
import { cameraProvenance } from "./derive.js";
import { editableShotPlan } from "./schema.js";
import { commitPlan, renderCameraPath, renderFrame, shotProject } from "./tab_shots.js";

function shotLabel(shot, index) {
    const action = String(shot.action ?? "").trim();
    return `Shot ${index + 1} · ${shot.id}${action ? ` · ${action.slice(0, 72)}` : ""}`;
}

export function renderCameraTab(container, controller, { embedded = false } = {}) {
    container.replaceChildren();
    const documentState = controller.shotDocument();
    const plan = editableShotPlan(documentState);
    if (!plan) {
        const status = element("div", "minimax-h3-studio-status", `The shot plan is ${documentState?.kind ?? "unavailable"}. Camera data is preserved read-only.`);
        status.dataset.kind = documentState?.kind ?? "malformed";
        container.appendChild(status);
        return;
    }

    const state = controller.shotUiState ??= {};
    state.plan = plan;
    if (!state.selectedId || !plan.shots.some((shot) => shot.id === state.selectedId)) state.selectedId = plan.shots[0]?.id ?? null;
    if (!plan.shots.length) {
        container.appendChild(emptyState(
            "Camera starts with a shot",
            "Create a Shot in Compose first, then direct its Start, Movement and End here.",
            actionButton("Open Compose", () => controller.navigateStudio?.("compose"), { disabled: typeof controller.navigateStudio !== "function" }),
        ));
        return;
    }

    const commit = () => commitPlan(controller, state);
    const rerender = () => {
        state.cameraPanelScroll = container.scrollTop;
        renderCameraTab(container, controller, { embedded });
    };
    const project = shotProject(controller);
    const shot = plan.shots.find((candidate) => candidate.id === state.selectedId);
    const cine = Object.fromEntries((controller.cameraFields?.() ?? []).map(([key]) => [key, controller.cameraValue(key)]));
    const provenance = cameraProvenance(plan, cine, project).get(shot.id) ?? { start: {}, end: {}, path: {} };

    const intro = element("header", "minimax-h3-camera-workspace-header");
    const title = element("div", "");
    title.append(
        element("h2", "", "Shot camera"),
        element("p", "", "Direct one shot at a time. Changes are written to that shot's existing cameraStart, cameraPath and cameraEnd fields."),
    );
    const backToShot = actionButton("Back to shot", () => controller.navigateStudio?.("compose"), {
        disabled: typeof controller.navigateStudio !== "function",
    });
    backToShot.className += " minimax-h3-button minimax-h3-button-secondary";
    intro.append(title, backToShot);

    const selector = selectInput(
        shot.id,
        plan.shots.map((candidate, index) => [candidate.id, shotLabel(candidate, index)]),
        { ariaLabel: "Shot to direct" },
    );
    selector.addEventListener("change", () => { state.selectedId = selector.value; rerender(); });
    const selectorBar = element("div", "minimax-h3-camera-shot-selector");
    selectorBar.append(
        field("Shot", selector, "Selection is shared with Compose."),
        element("span", "minimax-h3-state-chip", `Generation ${shot.generationId || "g1"}`),
    );

    const workspace = element("div", "minimax-h3-camera-workspace");
    renderVisualCameraPlanner(workspace, shot, project, commit, rerender);

    const preciseCamera = element("details", "minimax-h3-camera-advanced");
    preciseCamera.appendChild(element("summary", "", "Precise camera controls"));
    const preciseBody = element("div", "minimax-h3-camera-advanced-body");
    preciseBody.appendChild(element("p", "minimax-h3-field-hint", "Optional composition, viewpoint, targets, focus, easing and timing. These controls edit the same shot fields as the visual planner."));
    renderFrame(preciseBody, shot, "cameraStart", "Camera start", project, provenance.start, commit, rerender);
    renderFrame(preciseBody, shot, "cameraEnd", "Camera end", project, provenance.end, commit, rerender);
    renderCameraPath(preciseBody, shot, provenance.path, commit, rerender);
    renderCameraDataFallback(preciseBody, shot, commit, rerender);
    preciseCamera.appendChild(preciseBody);
    workspace.appendChild(preciseCamera);

    if (!embedded) container.append(intro, selectorBar, workspace);
    else container.append(element("p", "minimax-h3-studio-status", `Camera · ${shotLabel(shot, plan.shots.indexOf(shot))}`), workspace);
    if (state.cameraPanelScroll !== undefined) container.scrollTop = state.cameraPanelScroll;
}
