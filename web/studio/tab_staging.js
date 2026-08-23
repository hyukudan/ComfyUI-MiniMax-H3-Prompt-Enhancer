import { actionButton, element, emptyState, field, selectInput } from "./domain_components.js";
import { editableShotPlan } from "./schema.js";
import { renderStagingEditor, defaultSubjectPlacement } from "./staging_editor.js";
import { commitPlan, shotProject } from "./tab_shots.js";
import { ensureCameraPlannerStyles } from "./camera_planner_styles.js";

function shotLabel(shot, index) {
    const action = String(shot.action ?? "").trim();
    return `Shot ${index + 1}${action ? ` · ${action.slice(0, 72)}` : ""}`;
}

export function renderStagingTab(container, controller) {
    ensureCameraPlannerStyles();
    container.replaceChildren();
    const plan = editableShotPlan(controller.shotDocument());
    const project = shotProject(controller);
    if (!plan) return;
    const state = controller.shotUiState ??= {}; state.plan = plan;
    if (!state.selectedId || !plan.shots.some((shot) => shot.id === state.selectedId)) state.selectedId = plan.shots[0]?.id ?? null;
    if (!plan.shots.length || !(project.subjects ?? []).length) {
        container.appendChild(emptyState(
            "Staging needs a shot and subjects",
            "Create the cast and a shot first. Then place each subject in the frame and direct where they move or face.",
            actionButton(!plan.shots.length ? "Open Shots" : "Open Subjects", () => controller.navigateStudio?.(!plan.shots.length ? "shots" : "subjects")),
        ));
        return;
    }
    const shot = plan.shots.find((item) => item.id === state.selectedId);
    const commit = () => commitPlan(controller, state);
    const rerender = () => renderStagingTab(container, controller);
    const header = element("header", "minimax-h3-staging-header");
    header.append(element("h2", "", "Subject staging"), element("p", "", "Place several subjects independently. Camera waypoints can then aim at any staged subject while the anchor remains unchanged."));
    const selector = selectInput(shot.id, plan.shots.map((item, index) => [item.id, shotLabel(item, index)]));
    selector.addEventListener("change", () => { state.selectedId = selector.value; rerender(); });
    container.append(header, field("Shot", selector, "Selection is shared with Shots and Camera."));
    if (!shot.staging?.length) {
        const present = new Set((shot.subjects ?? []).filter((item) => item.presence !== "absent").map((item) => item.subjectId));
        const candidates = project.subjects.filter((subject) => !present.size || present.has(subject.id));
        container.appendChild(emptyState(
            "Direct where the cast stands",
            "No positions are saved yet. Creating staging places the visible cast across the frame; you can drag and refine every subject afterward.",
            actionButton("Create staging", () => {
                shot.staging = candidates.map((subject, index) => defaultSubjectPlacement(subject.id, index, candidates.length));
                state.stagingSubjectId = shot.staging[0]?.subjectId ?? null; commit(); rerender();
            }),
        ));
        return;
    }
    renderStagingEditor(container, shot, project, commit, rerender, state);
}
