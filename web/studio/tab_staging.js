import { actionButton, element, emptyState, field, selectInput } from "./domain_components.js";
import { editableShotPlan } from "./schema.js";
import { renderStagingEditor, defaultSubjectPlacement } from "./staging_editor.js";
import { commitPlan, shotProject } from "./tab_shots.js";
import { ensureCameraPlannerStyles } from "./camera_planner_styles.js";

function shotLabel(shot, index) {
    const action = String(shot.action ?? "").trim();
    return `Shot ${index + 1}${action ? ` · ${action.slice(0, 72)}` : ""}`;
}

export function renderStagingTab(container, controller, { embedded = false } = {}) {
    ensureCameraPlannerStyles();
    container.replaceChildren();
    const plan = editableShotPlan(controller.shotDocument());
    const project = shotProject(controller);
    if (!plan) return;
    const state = controller.shotUiState ??= {}; state.plan = plan;
    if (!state.selectedId || !plan.shots.some((shot) => shot.id === state.selectedId)) state.selectedId = plan.shots[0]?.id ?? null;
    if (!plan.shots.length) {
        container.appendChild(emptyState(
            "Stage starts with a Shot",
            "Create a Shot in Compose first. Stage will then arrange its visible Subjects.",
            actionButton("Open Compose", () => controller.navigateStudio?.("compose")),
        ));
        return;
    }
    if (!(project.subjects ?? []).length) {
        container.appendChild(emptyState(
            "This Shot has no Subjects to stage",
            "Create a reusable Subject in Cast & Places, then add it to the selected Shot.",
            actionButton("Open Cast & Places", () => controller.navigateStudio?.("cast_places")),
        ));
        return;
    }
    const shot = plan.shots.find((item) => item.id === state.selectedId);
    const commit = () => commitPlan(controller, state);
    const rerender = () => renderStagingTab(container, controller, { embedded });
    const header = element("header", "minimax-h3-staging-header");
    header.append(element("h2", "", "Subject staging"), element("p", "", "Place several subjects independently. Camera waypoints can then aim at any staged subject while the anchor remains unchanged."));
    const selector = selectInput(shot.id, plan.shots.map((item, index) => [item.id, shotLabel(item, index)]));
    selector.addEventListener("change", () => { state.selectedId = selector.value; rerender(); });
    if (!embedded) container.append(header, field("Shot", selector, "Selection is shared with Compose and Camera."));
    else container.appendChild(element("p", "minimax-h3-studio-status", `Stage workspace · ${shotLabel(shot, plan.shots.indexOf(shot))} · This Shot`));
    const present = new Set((shot.subjects ?? []).filter((item) => item.presence !== "absent").map((item) => item.subjectId));
    if (!present.size) {
        const chooser = element("section", "minimax-h3-staging-add-cast");
        chooser.append(element("h3", "", "Add cast to this Shot"), element("p", "", "Choose a reusable Subject here. Stage will add and position that Subject without leaving the Shot."));
        const choices = element("div", "minimax-h3-staging-add-cast-choices");
        for (const subject of project.subjects ?? []) choices.appendChild(actionButton(`+ ${subject.name || subject.id}`, () => {
            (shot.subjects ??= []).push({ subjectId: subject.id, presence: "present" });
            shot.staging = [defaultSubjectPlacement(subject.id, 0, 1)];
            state.stagingSubjectId = subject.id; commit(); rerender();
        }));
        chooser.appendChild(choices); container.appendChild(chooser);
        return;
    }
    if (!shot.staging?.length) {
        const candidates = project.subjects.filter((subject) => present.has(subject.id));
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
    renderStagingEditor(container, shot, project, commit, rerender, state, controller.referenceDirectorDocument?.()?.value?.sources ?? {});
}
