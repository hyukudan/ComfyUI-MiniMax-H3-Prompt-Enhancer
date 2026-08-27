import { renderCameraLookTab } from "./tab_camera_look.js";
import { renderCoachTab } from "./tab_coach.js";
import { createStudioIcon } from "./components/icons.js";
import { createSourceStateCard, normalizedSourceState } from "./components/source_state.js";
import { renderDirectorCompose, renderDirectorLibrary, renderDirectorLook, renderDirectorWiring } from "./director_workspace.js";
import { ensureStudioStyles } from "./styles.js";
import { STUDIO_MAX_WIDTH, STUDIO_MIN_WIDTH, STUDIO_UI_LEGACY_STORAGE_KEY, STUDIO_UI_STORAGE_KEY } from "./tokens.js";

export function createPanelElement(tagName, className, textContent = "") {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    if (textContent) element.textContent = textContent;
    return element;
}

export const STUDIO_SECTIONS = Object.freeze([
    { id: "storyboard", label: "Storyboard", icon: "shots", render: renderDirectorCompose },
    { id: "library", label: "Library", icon: "subjects", render: renderDirectorLibrary },
    { id: "look", label: "Look", icon: "look", render: renderCameraLookTab },
]);

export const DIRECTOR_SECTIONS = Object.freeze([
    { id: "compose", label: "Compose", icon: "shots", render: renderDirectorCompose },
    { id: "library", label: "Library", icon: "media", render: renderDirectorLibrary },
    { id: "wiring", label: "Wiring", icon: "wiring", render: renderDirectorWiring },
    { id: "look", label: "Look", icon: "look", render: renderDirectorLook },
]);

const SECTION_ALIASES = Object.freeze({
    overview: "storyboard", compose: "storyboard", shots: "storyboard", staging: "storyboard", camera: "storyboard",
    subjects: "library", environments: "library", cast_places: "library", media: "library", references: "library",
    camera_look: "look", coach: "review",
});
const SECTION_IDS = new Set(STUDIO_SECTIONS.map((item) => item.id));

export function normalizeStudioSection(section) {
    const normalized = SECTION_ALIASES[section] ?? section;
    return SECTION_IDS.has(normalized) || normalized === "review" ? normalized : "storyboard";
}

export function normalizeDirectorSection(section) {
    const aliases = { overview: "compose", shots: "compose", staging: "compose", camera: "compose", subjects: "library", environments: "library", media: "library", references: "library", camera_look: "look" };
    const normalized = aliases[section] ?? section;
    return DIRECTOR_SECTIONS.some((item) => item.id === normalized) || normalized === "review" ? normalized : "compose";
}

export function diagnosticFieldLabels(field) {
    const parts = String(field ?? "").replaceAll("[", ".").replaceAll("]", "").split(".").filter(Boolean);
    const leaf = parts.at(-1) ?? "";
    const aliases = {
        action: ["Action", "Action / reaction"], openingState: ["Opening state"],
        cutContext: ["Describe cut context"], durationSeconds: ["Duration (seconds)"], transitionIn: ["Transition in"],
        cameraMotion: ["Camera motion"], cameraStart: ["Framing", "Angle", "Viewpoint"], cameraEnd: ["Framing", "Angle", "Viewpoint"],
        framing: ["Framing"], angle: ["Angle"], viewpoint: ["Viewpoint"], composition: ["Composition"], focus: ["Focus"],
        optics: ["Optics"], lensEffects: ["Lens effects"], bindings: ["File slot", "Reference"], activation: ["Activation"],
        dialogue: ["Spoken words", "Dialogue at this beat"], text: ["Spoken words"],
        subjectId: ["Subject"], environmentId: ["Environment"], toStateId: ["To"],
        trigger: ["Trigger"], mechanism: ["Mechanism"], stateId: ["State"],
    };
    return aliases[leaf] ?? (leaf ? [leaf.replace(/([a-z])([A-Z])/g, "$1 $2")] : []);
}

export function focusDiagnosticLocation(panel, location = {}) {
    if (String(location.scope ?? "").toLowerCase() === "output") {
        return { found: false, reason: "This finding refers to generated output, not an editable Studio control." };
    }
    const fieldName = String(location.field ?? "");
    let target = null;
    if (/\.action$|\]\.action$/.test(fieldName)) target = panel.querySelector?.("[data-shot-action]");
    if (!target && /\.staging(?:\.|$)/.test(fieldName)) target = panel.querySelector?.(".minimax-h3-staging-stage, .minimax-h3-staging-inspector");
    if (!target && /cameraPath/.test(fieldName)) target = panel.querySelector?.(".minimax-h3-camera-planner, .minimax-h3-spatial-camera-editor");
    const wanted = new Set(diagnosticFieldLabels(fieldName).map((value) => value.toLowerCase()));
    if (!target && wanted.size) {
        for (const wrapper of panel.querySelectorAll?.(".minimax-h3-studio-field") ?? []) {
            const label = String(wrapper.firstElementChild?.textContent ?? "").trim().toLowerCase();
            if (!wanted.has(label)) continue;
            target = wrapper.querySelector?.("input, textarea, select, button, [tabindex]") ?? wrapper;
            break;
        }
    }
    if (!target) return { found: false, reason: "Opened the related section, but this report location has no exact editable control." };
    for (let ancestor = target.parentElement; ancestor && ancestor !== panel; ancestor = ancestor.parentElement) {
        if (ancestor.tagName === "DETAILS") ancestor.open = true;
    }
    const highlight = target.closest?.(".minimax-h3-studio-field, .minimax-h3-inspector-section") ?? target;
    highlight.classList?.add("minimax-h3-diagnostic-target");
    target.scrollIntoView?.({ block: "center", behavior: "smooth" });
    target.focus?.({ preventScroll: true });
    const timeout = globalThis.setTimeout?.(() => highlight.classList?.remove("minimax-h3-diagnostic-target"), 2600);
    timeout?.unref?.();
    return { found: true, target };
}

export function defaultDrawerWidth(
    viewportWidth = globalThis.innerWidth ?? 2560,
    viewportHeight = globalThis.innerHeight ?? Math.round(viewportWidth * 9 / 16),
) {
    if (viewportWidth >= 3200 || viewportHeight >= 1800) return 920;
    if (viewportWidth >= 2200) return 820;
    return 720;
}

export function drawerWidthBounds(viewportWidth = globalThis.innerWidth ?? 1440) {
    if (viewportWidth < 700) return { minimum: viewportWidth, maximum: viewportWidth };
    return {
        minimum: STUDIO_MIN_WIDTH,
        maximum: Math.max(STUDIO_MIN_WIDTH, Math.min(STUDIO_MAX_WIDTH, viewportWidth * 0.6)),
    };
}

export function clampDrawerWidth(width, viewportWidth = globalThis.innerWidth ?? 1440) {
    const { minimum, maximum } = drawerWidthBounds(viewportWidth);
    const fallback = Math.min(maximum, Math.max(minimum, defaultDrawerWidth(viewportWidth)));
    if (width === null || width === undefined || width === "") return fallback;
    const numeric = Number(width);
    return Number.isFinite(numeric) ? Math.min(maximum, Math.max(minimum, Math.round(numeric))) : fallback;
}

const DEFAULT_PREFS = Object.freeze({
    width: null,
    lastSection: "storyboard",
    railCollapsed: false,
    detailMode: "guided",
    collapsedBlocks: {},
});

export function normalizeStudioDetailMode(value) {
    return value === "advanced" ? "advanced" : "guided";
}

function storageOrNull(storage) {
    if (storage !== undefined) return storage;
    try { return globalThis.localStorage ?? null; } catch { return null; }
}

export function normalizeStudioPrefs(value = {}) {
    const lastSection = normalizeStudioSection(value?.lastSection);
    const storedWidth = value?.width;
    return {
        width: storedWidth !== null && storedWidth !== undefined && storedWidth !== "" && Number.isFinite(Number(storedWidth))
            ? Number(storedWidth)
            : DEFAULT_PREFS.width,
        lastSection: lastSection === "review" ? DEFAULT_PREFS.lastSection : lastSection,
        railCollapsed: Boolean(value?.railCollapsed),
        detailMode: normalizeStudioDetailMode(value?.detailMode),
        collapsedBlocks: value?.collapsedBlocks && typeof value.collapsedBlocks === "object" && !Array.isArray(value.collapsedBlocks)
            ? { ...value.collapsedBlocks }
            : {},
    };
}

export function readStudioPrefs(storage = undefined) {
    const target = storageOrNull(storage);
    if (!target?.getItem) return { ...DEFAULT_PREFS };
    try {
        const current = target.getItem(STUDIO_UI_STORAGE_KEY);
        if (current !== null) return normalizeStudioPrefs(JSON.parse(current));
        const legacy = JSON.parse(target.getItem(STUDIO_UI_LEGACY_STORAGE_KEY) ?? "{}");
        if (legacy?.lastSection === "camera") legacy.lastSection = "look";
        return normalizeStudioPrefs(legacy);
    } catch {
        return { ...DEFAULT_PREFS };
    }
}

export function writeStudioPrefs(prefs, storage = undefined) {
    const normalized = normalizeStudioPrefs(prefs);
    const target = storageOrNull(storage);
    if (!target?.setItem) return normalized;
    try { target.setItem(STUDIO_UI_STORAGE_KEY, JSON.stringify(normalized)); } catch { /* preference storage is optional */ }
    return normalized;
}

let activeDrawer = null;

export function closeStudioDrawer(nodeId = null) {
    if (!activeDrawer || (nodeId !== null && activeDrawer.nodeId !== nodeId)) return false;
    const closing = activeDrawer;
    activeDrawer = null;
    closing.cleanup?.();
    closing.element.remove();
    closing.node?.__minimaxStudioDashboard?.refresh?.();
    closing.returnFocus?.focus?.();
    return true;
}

export function studioDrawerIsOpenFor(nodeId) {
    return activeDrawer?.nodeId === nodeId;
}

function safeDocument(read) {
    try { return normalizedSourceState(read?.()); } catch { return normalizedSourceState(null); }
}

function sourceDocuments(controller) {
    return {
        shot: safeDocument(() => controller.shotDocument()),
        project: safeDocument(() => controller.projectDocument()),
        camera: safeDocument(() => controller.cinematographyDocument()),
    };
}

function reportCounts(controller) {
    const result = { errors: 0, warnings: 0, tips: 0, total: 0, stale: false };
    const report = controller.diagnostics?.() ?? {};
    result.stale = Boolean(report.stale);
    for (const item of report.diagnostics ?? []) {
        result.total += 1;
        if (item?.severity === "error") result.errors += 1;
        else if (item?.severity === "warning") result.warnings += 1;
        else result.tips += 1;
    }
    return result;
}

export function productionContext(controller) {
    const shot = safeDocument(() => controller.shotDocument());
    const project = safeDocument(() => controller.projectDocument());
    const shots = Array.isArray(shot.value?.shots) ? shot.value.shots : [];
    const exact = shot.value?.timingMode === "exact";
    const duration = exact
        ? shots.reduce((total, item) => total + Math.max(0, Number(item?.durationSeconds) || 0), 0)
        : null;
    const projectValue = project.kind === "v2" ? project.value : controller.projectUiState?.project ?? null;
    const generatedTiming = controller.generationTiming?.() ?? null;
    const seconds = exact ? duration : Number(generatedTiming?.seconds);
    const frames = exact ? Math.round(duration * 24) : Number(generatedTiming?.frames);
    const requestedMode = String(controller.mode?.() ?? projectValue?.mode ?? "auto").toLowerCase();
    const resolvedMode = String(controller.resolvedMode?.() ?? "").toLowerCase();
    const mode = requestedMode === "auto" && resolvedMode && resolvedMode !== "auto"
        ? `AUTO → ${resolvedMode.toUpperCase()}`
        : requestedMode.toUpperCase();
    return {
        mode,
        shots: shots.length,
        timing: Number.isFinite(seconds) && seconds > 0
            ? `${seconds.toFixed(2)} s · ${Number.isFinite(frames) && frames > 0 ? Math.round(frames) : Math.round(seconds * 24)}f`
            : "Auto",
        generations: Array.isArray(projectValue?.generations) ? projectValue.generations.length : 0,
        media: Array.isArray(projectValue?.assets) ? projectValue.assets.length : 0,
    };
}

function createIconButton(icon, label, className = "minimax-h3-icon-button") {
    const button = createPanelElement("button", className);
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.title = label;
    button.appendChild(createStudioIcon(icon));
    return button;
}

function createHeader(controller, onReview, onClose) {
    const header = createPanelElement("header", "minimax-h3-studio-header");
    const main = createPanelElement("div", "minimax-h3-header-main");
    const identity = createPanelElement("div", "minimax-h3-header-identity");
    const title = createPanelElement("h2", "", controller.isVisualReferenceDirector ? "Visual Reference Director" : "Prompt Studio");
    const context = createPanelElement("p", "minimax-h3-header-context");
    identity.append(title, context);
    const state = createPanelElement("div", "minimax-h3-header-state");
    const saved = createPanelElement("span", "minimax-h3-saved-state", "Saved automatically to workflow");
    saved.title = "Every explicit edit is stored immediately in the authoritative workflow data.";
    const review = createPanelElement("button", "minimax-h3-review-button");
    review.type = "button";
    review.append(createStudioIcon("review"), createPanelElement("span", "minimax-h3-review-label", "Review & Generate"));
    review.setAttribute("aria-live", "polite");
    review.addEventListener("click", onReview);
    const help = createIconButton("help", "Keyboard shortcuts");
    help.setAttribute("aria-expanded", "false");
    const close = createIconButton("close", "Close Prompt Studio");
    close.addEventListener("click", onClose);
    state.append(saved, review, help, close);
    main.append(identity, state);

    const shortcuts = createPanelElement("section", "minimax-h3-shortcuts");
    shortcuts.hidden = true;
    shortcuts.setAttribute("aria-label", "Prompt Studio keyboard shortcuts");
    shortcuts.appendChild(createPanelElement("h3", "", "Keyboard shortcuts"));
    const list = createPanelElement("dl", "");
    for (const [keys, action] of [
        ["1–9", "Open a section"],
        ["↑ / ↓", "Move through section navigation"],
        ["Ctrl + Enter", "Add an item in the active editor"],
        ["Ctrl + D", "Duplicate the selection"],
        ["Ctrl + Z", "Undo the last Studio change"],
        ["Esc", "Return from Review or close Studio"],
    ]) {
        list.append(createPanelElement("dt", "", keys), createPanelElement("dd", "", action));
    }
    shortcuts.appendChild(list);
    const setShortcutsOpen = (open) => {
        shortcuts.hidden = !open;
        help.setAttribute("aria-expanded", String(open));
    };
    help.addEventListener("click", () => setShortcutsOpen(shortcuts.hidden));
    const production = createPanelElement("div", "minimax-h3-production-context");
    production.setAttribute("role", "group");
    production.setAttribute("aria-label", "Production context");
    const productionFields = new Map();
    for (const [key, label] of [
        ["mode", "Mode"], ["shots", "Shots"], ["timing", "Duration"],
        ["generations", "Generations"], ["media", "Media"],
    ]) {
        const item = createPanelElement("span", "minimax-h3-production-context-item");
        item.dataset.contextKey = key;
        item.append(
            createPanelElement("small", "", label),
            createPanelElement("strong", "", "—"),
        );
        productionFields.set(key, item.querySelector("strong"));
        production.appendChild(item);
    }
    header.append(main, production, shortcuts);

    const refresh = () => {
        const project = safeDocument(() => controller.projectDocument());
        const projectValue = project.kind === "v2" ? project.value : controller.projectUiState?.project ?? null;
        const mode = projectValue?.mode ?? "auto";
        const generations = projectValue?.generations?.length ?? 1;
        context.textContent = controller.isVisualReferenceDirector
            ? `${mode} · ${generations} generation${generations === 1 ? "" : "s"} · physical + semantic references`
            : projectValue ? `${mode} · ${generations} generation${generations === 1 ? "" : "s"} · Studio Project v3` : "Visual prompt workspace";
        const counts = reportCounts(controller);
        review.dataset.state = counts.stale ? "stale" : counts.errors ? "error" : counts.warnings ? "warning" : "ready";
        review.querySelector(".minimax-h3-review-label").textContent = counts.stale
            ? `Review · stale`
            : counts.total ? `Review · ${counts.errors} errors · ${counts.warnings + counts.tips} notes` : "Review & Generate";
        const contextModel = productionContext(controller);
        for (const [key, target] of productionFields) target.textContent = String(contextModel[key]);
    };
    return { header, shortcuts, setShortcutsOpen, refresh, close };
}

function createNavigation(node, sections, onNavigate, onCollapse, director = false) {
    const rail = createPanelElement("nav", "minimax-h3-studio-rail");
    rail.setAttribute("aria-label", director ? "Visual Reference Director sections" : "Prompt Studio sections");
    const tablist = createPanelElement("div", "minimax-h3-studio-tabs");
    tablist.setAttribute("role", "tablist");
    tablist.setAttribute("aria-orientation", "vertical");
    const buttons = new Map();
    sections.forEach(({ id, label, icon }) => {
        const button = createPanelElement("button", "minimax-h3-studio-tab");
        button.type = "button";
        button.id = `minimax-h3-tab-${node.id}-${id}`;
        button.setAttribute("role", "tab");
        button.setAttribute("aria-label", label);
        button.title = label;
        button.append(createStudioIcon(icon, 20), createPanelElement("span", "minimax-h3-tab-label", label));
        button.addEventListener("click", () => onNavigate(id));
        button.addEventListener("keydown", (event) => {
            if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            const current = sections.findIndex((item) => item.id === id);
            const forward = ["ArrowDown", "ArrowRight"].includes(event.key);
            const next = event.key === "Home" ? 0 : event.key === "End" ? sections.length - 1
                : (current + (forward ? 1 : -1) + sections.length) % sections.length;
            const nextId = sections[next].id;
            buttons.get(nextId)?.focus();
            onNavigate(nextId);
        });
        buttons.set(id, button);
        tablist.appendChild(button);
    });
    const collapse = createIconButton("chevronLeft", "Collapse section rail", "minimax-h3-rail-collapse");
    collapse.addEventListener("click", onCollapse);
    rail.append(tablist, collapse);
    return { rail, buttons, collapse };
}

function sourceGate(sectionId, controller, panel) {
    const documents = sourceDocuments(controller);
    if (["storyboard", "shots", "staging", "camera"].includes(sectionId) && ["malformed", "future"].includes(documents.shot.kind)) {
        panel.appendChild(createSourceStateCard({
            name: "Shot plan",
            documentState: documents.shot,
            acceptedVersions: [1, 2],
            onApplyRaw: controller.replaceShotRaw ? (raw) => controller.replaceShotRaw(raw) : null,
        }));
        return true;
    }
    if (["storyboard", "library"].includes(sectionId) && documents.project.kind === "v1") {
        panel.classList.add("minimax-h3-source-gated");
        const unavailable = createPanelElement("section", "minimax-h3-empty-state minimax-h3-source-unavailable");
        unavailable.append(
            createPanelElement("h3", "", "Import this legacy project"),
            createPanelElement("p", "", "Convert this older source once to continue in Studio Project v3."),
        );
        const tools = createPanelElement("details", "minimax-h3-source-tools minimax-h3-source-tools-gate");
        tools.append(
            createPanelElement("summary", "", "Import & source tools"),
            createSourceStateCard({
                name: "Media project",
                documentState: documents.project,
                acceptedVersions: [2],
                legacyDescription: "The legacy source stays unchanged until you explicitly import it into Studio Project v3.",
            }),
        );
        panel.append(unavailable, tools);
        return true;
    }
    if (["storyboard", "library"].includes(sectionId) && ["malformed", "future"].includes(documents.project.kind)) {
        panel.appendChild(createSourceStateCard({
            name: "Media project",
            documentState: documents.project,
            acceptedVersions: [2],
            legacyDescription: "Fix or replace this source before importing it into Studio Project v3.",
            onApplyRaw: controller.replaceProjectRaw ? (raw) => controller.replaceProjectRaw(raw) : null,
        }));
        return true;
    }
    return false;
}

function isEditingTarget(target) {
    return target instanceof HTMLElement
        && (target.matches("input, textarea, select") || target.isContentEditable);
}

export function openStudioDrawer(node, controller, initialTab = null, returnFocus = null) {
    closeStudioDrawer();
    ensureStudioStyles();
    let prefs = readStudioPrefs();
    const drawer = createPanelElement("section", "minimax-h3-studio");
    drawer.setAttribute("role", "dialog");
    drawer.setAttribute("aria-modal", "false");
    drawer.setAttribute("aria-label", controller.isVisualReferenceDirector ? "MiniMax H3 Visual Reference Director" : "MiniMax H3 Prompt Studio");
    drawer.dataset.railCollapsed = String(prefs.railCollapsed);
    drawer.dataset.detailMode = prefs.detailMode;
    drawer.style.width = `${clampDrawerWidth(prefs.width, globalThis.innerWidth)}px`;

    const resizer = createPanelElement("div", "minimax-h3-studio-resizer");
    resizer.tabIndex = 0;
    resizer.setAttribute("role", "separator");
    resizer.setAttribute("aria-label", "Resize Prompt Studio");
    resizer.setAttribute("aria-orientation", "vertical");
    const body = createPanelElement("div", "minimax-h3-studio-body");
    const panel = createPanelElement("main", "minimax-h3-studio-panel");
    panel.setAttribute("role", "tabpanel");
    panel.tabIndex = -1;
    const sections = controller.isVisualReferenceDirector ? DIRECTOR_SECTIONS : STUDIO_SECTIONS;
    const normalizeSection = controller.isVisualReferenceDirector ? normalizeDirectorSection : normalizeStudioSection;
    let previousSection = normalizeSection(initialTab ?? prefs.lastSection);
    if (previousSection === "review") previousSection = prefs.lastSection;
    let currentSection = previousSection;

    const savePrefs = (patch) => {
        prefs = writeStudioPrefs({ ...prefs, ...patch });
        return prefs;
    };
    const updateResizer = () => {
        const { minimum, maximum } = drawerWidthBounds(globalThis.innerWidth);
        const width = clampDrawerWidth(parseFloat(drawer.style.width), globalThis.innerWidth);
        resizer.setAttribute("aria-valuemin", String(minimum));
        resizer.setAttribute("aria-valuemax", String(maximum));
        resizer.setAttribute("aria-valuenow", String(width));
    };

    let render = () => {};
    let applyDetailMode = () => {};
    const previousDetailMode = controller.studioDetailMode;
    controller.studioDetailMode = prefs.detailMode;
    const header = createHeader(
        controller,
        () => render("review"),
        () => closeStudioDrawer(node.id),
    );
    const navigation = createNavigation(node, sections, (id) => render(id), () => {
        const collapsed = drawer.dataset.railCollapsed !== "true";
        drawer.dataset.railCollapsed = String(collapsed);
        navigation.collapse.setAttribute("aria-label", collapsed ? "Expand section rail" : "Collapse section rail");
        savePrefs({ railCollapsed: collapsed });
    }, controller.isVisualReferenceDirector);

    const renderReview = () => {
        const toolbar = createPanelElement("div", "minimax-h3-review-toolbar");
        const back = createPanelElement("button", "minimax-h3-button minimax-h3-button-secondary", "Back to workspace");
        back.type = "button";
        back.prepend(createStudioIcon("chevronLeft"));
        back.addEventListener("click", () => render(previousSection));
        const title = createPanelElement("h2", "", "Review & Generate");
        toolbar.append(back, title);
        panel.appendChild(toolbar);
        const content = createPanelElement("div", "minimax-h3-review-content");
        panel.appendChild(content);
        renderCoachTab(content, controller);
        if (typeof controller.compileStudioProject === "function") {
            const output = createPanelElement("section", "minimax-h3-review-card minimax-h3-studio-output");
            const heading = createPanelElement("header");
            const copy = createPanelElement("div");
            copy.append(
                createPanelElement("h3", "", "Studio Project v3 output"),
                createPanelElement("p", "", "Compile the selected Generation to verify the exact H3 image, video and audio outputs before queueing."),
            );
            const generation = createPanelElement("select");
            generation.setAttribute("aria-label", "Generation to compile");
            for (const id of controller.generationIds?.() ?? ["g1"]) {
                const option = createPanelElement("option", "", id); option.value = id; generation.appendChild(option);
            }
            heading.append(copy, generation); output.appendChild(heading);
            const actions = createPanelElement("div", "minimax-h3-studio-toolbar");
            const compile = createPanelElement("button", "minimax-h3-button minimax-h3-button-secondary", "Compile outputs");
            const queue = createPanelElement("button", "minimax-h3-button minimax-h3-button-primary", "Generate this node");
            const status = createPanelElement("p", "minimax-h3-studio-status", "Not compiled yet");
            const mapping = createPanelElement("div", "minimax-h3-reference-output-list");
            const showCompilation = async () => {
                compile.disabled = true; queue.disabled = true; status.dataset.valid = "true"; status.textContent = "Compiling Studio Project v3…";
                mapping.replaceChildren();
                try {
                    const result = await controller.compileStudioProject(generation.value);
                    const rows = Object.entries(result.inputMap ?? {});
                    for (const [fileId, label] of rows) {
                        const row = createPanelElement("div", "minimax-h3-reference-output-card");
                        const details = createPanelElement("span", "", fileId);
                        const socket = result.socketMap?.[fileId];
                        if (socket) details.append(createPanelElement("code", "", `Enhancer ${socket} → H3 ${socket}`));
                        row.append(createPanelElement("strong", "", label), details); mapping.appendChild(row);
                    }
                    if (!rows.length) mapping.appendChild(createPanelElement("p", "minimax-h3-director-placeholder", "Text-only Generation · no physical reference outputs"));
                    status.textContent = `${rows.length} physical output${rows.length === 1 ? "" : "s"} ready · v3 digest ${String(result.digest ?? "").slice(0, 10)}`;
                    return true;
                } catch (error) {
                    status.dataset.valid = "false"; status.textContent = error?.message ?? "Studio Project compilation failed."; return false;
                } finally { compile.disabled = false; queue.disabled = false; }
            };
            compile.type = queue.type = "button";
            compile.addEventListener("click", showCompilation);
            queue.addEventListener("click", async () => {
                if (!await showCompilation()) return;
                queue.disabled = true; status.textContent = "Queueing this Prompt Enhancer…";
                try { await controller.runStudioNode(); status.textContent = "Queued successfully."; }
                catch (error) { status.dataset.valid = "false"; status.textContent = error?.message ?? "Could not queue the node."; }
                finally { queue.disabled = false; }
            });
            actions.append(compile, queue); output.append(actions, status, mapping); content.prepend(output);
        }
    };

    render = (requestedSection) => {
        if (!controller.isVisualReferenceDirector) {
            const legacyRoute = String(requestedSection ?? "");
            controller.directorUiState ??= {};
            if (legacyRoute === "subjects" || legacyRoute === "environments") {
                controller.directorUiState.castPlacesMode = legacyRoute;
            } else if (legacyRoute === "staging") controller.directorUiState.composeMode = "staging";
            else if (legacyRoute === "camera") controller.directorUiState.composeMode = "camera";
            else if (legacyRoute === "shots" || legacyRoute === "overview") controller.directorUiState.composeMode = "build";
        }
        const sectionId = normalizeSection(requestedSection);
        const changedSection = sectionId !== currentSection;
        currentSection = sectionId;
        panel.replaceChildren();
        panel.className = `minimax-h3-studio-panel minimax-h3-section-${sectionId}`;
        if (sectionId === "review") renderReview();
        else {
            previousSection = sectionId;
            if (!controller.isVisualReferenceDirector) savePrefs({ lastSection: sectionId });
            const section = sections.find((item) => item.id === sectionId) ?? sections[0];
            panel.removeAttribute("aria-label");
            panel.setAttribute("aria-labelledby", `minimax-h3-tab-${node.id}-${section.id}`);
            if (section.id === "overview") {
                renderOverview(panel, controller, { navigate: render, openReview: () => render("review") });
            } else {
                if (!sourceGate(section.id, controller, panel)) section.render(panel, controller);
            }
        }
        if (sectionId === "review") {
            panel.removeAttribute("aria-labelledby");
            panel.setAttribute("aria-label", "Prompt Studio Review");
        }
        for (const [id, button] of navigation.buttons) {
            const selected = id === sectionId;
            button.setAttribute("aria-selected", String(selected));
            button.tabIndex = selected ? 0 : -1;
        }
        header.refresh();
        if (changedSection) panel.scrollTop = 0;
        if (activeDrawer) activeDrawer.tabId = sectionId;
    };

    applyDetailMode = (requestedMode) => {
        const mode = normalizeStudioDetailMode(requestedMode);
        if (mode === prefs.detailMode) return;
        savePrefs({ detailMode: mode });
        drawer.dataset.detailMode = mode;
        controller.studioDetailMode = mode;
        render(currentSection);
    };

    const applyWidth = (width, persist = false) => {
        const value = clampDrawerWidth(width, globalThis.innerWidth);
        drawer.style.width = `${value}px`;
        updateResizer();
        if (persist && globalThis.innerWidth >= 700) savePrefs({ width: value });
    };
    let resizeStart = null;
    const onPointerMove = (event) => {
        if (!resizeStart) return;
        applyWidth(resizeStart.width + resizeStart.x - event.clientX);
    };
    const onPointerUp = (event) => {
        if (!resizeStart) return;
        onPointerMove(event);
        resizeStart = null;
        drawer.dataset.resizing = "false";
        applyWidth(parseFloat(drawer.style.width), true);
    };
    resizer.addEventListener("pointerdown", (event) => {
        if (globalThis.innerWidth < 700) return;
        event.preventDefault();
        resizeStart = { x: event.clientX, width: drawer.getBoundingClientRect().width };
        drawer.dataset.resizing = "true";
        resizer.setPointerCapture?.(event.pointerId);
    });
    resizer.addEventListener("dblclick", () => applyWidth(defaultDrawerWidth(globalThis.innerWidth), true));
    resizer.addEventListener("keydown", (event) => {
        if (!["ArrowLeft", "ArrowRight"].includes(event.key) || globalThis.innerWidth < 700) return;
        event.preventDefault();
        const step = event.shiftKey ? 64 : 16;
        const direction = event.key === "ArrowLeft" ? 1 : -1;
        applyWidth(parseFloat(drawer.style.width) + direction * step, true);
    });
    const onViewportResize = () => applyWidth(prefs.width);
    const onKeydown = (event) => {
        if (event.key === "Escape") {
            if (!header.shortcuts.hidden) {
                header.setShortcutsOpen(false);
                return;
            }
            if (activeDrawer?.tabId === "review") {
                event.preventDefault();
                render(previousSection);
                return;
            }
            closeStudioDrawer(node.id);
            return;
        }
        if (isEditingTarget(event.target) || event.ctrlKey || event.metaKey || event.altKey) return;
        if (/^[1-9]$/.test(event.key) && Number(event.key) <= sections.length) {
            event.preventDefault();
            render(sections[Number(event.key) - 1].id);
            return;
        }
        if (event.key === "?") {
            event.preventDefault();
            header.setShortcutsOpen(header.shortcuts.hidden);
        }
    };
    globalThis.addEventListener("pointermove", onPointerMove);
    globalThis.addEventListener("pointerup", onPointerUp);
    globalThis.addEventListener("resize", onViewportResize);
    drawer.addEventListener("keydown", onKeydown);
    const refreshHeaderSoon = () => queueMicrotask(header.refresh);
    body.addEventListener("change", refreshHeaderSoon);
    body.addEventListener("blur", refreshHeaderSoon, true);
    body.addEventListener("click", refreshHeaderSoon);

    body.append(navigation.rail, panel);
    drawer.append(resizer, header.header, body);
    document.body.appendChild(drawer);
    const previousNavigateStudio = controller.navigateStudio;
    const previousNavigateStudioLocation = controller.navigateStudioLocation;
    const previousSetStudioDetailMode = controller.setStudioDetailMode;
    controller.navigateStudio = render;
    controller.setStudioDetailMode = applyDetailMode;
    const navigateStudioLocation = (section, location = {}) => {
        render(section);
        queueMicrotask(() => {
            const result = focusDiagnosticLocation(panel, location);
            if (result.found) return;
            const feedback = createPanelElement("div", "minimax-h3-studio-status", result.reason);
            feedback.dataset.kind = "navigation-fallback";
            panel.prepend(feedback);
        });
    };
    controller.navigateStudioLocation = navigateStudioLocation;
    const cleanup = () => {
        globalThis.removeEventListener("pointermove", onPointerMove);
        globalThis.removeEventListener("pointerup", onPointerUp);
        globalThis.removeEventListener("resize", onViewportResize);
        if (controller.navigateStudio === render) {
            if (previousNavigateStudio === undefined) delete controller.navigateStudio;
            else controller.navigateStudio = previousNavigateStudio;
        }
        if (controller.navigateStudioLocation === navigateStudioLocation) {
            if (previousNavigateStudioLocation === undefined) delete controller.navigateStudioLocation;
            else controller.navigateStudioLocation = previousNavigateStudioLocation;
        }
        if (controller.setStudioDetailMode === applyDetailMode) {
            if (previousSetStudioDetailMode === undefined) delete controller.setStudioDetailMode;
            else controller.setStudioDetailMode = previousSetStudioDetailMode;
        }
        if (controller.studioDetailMode === prefs.detailMode) {
            if (previousDetailMode === undefined) delete controller.studioDetailMode;
            else controller.studioDetailMode = previousDetailMode;
        }
    };
    activeDrawer = { nodeId: node.id, node, element: drawer, controller, returnFocus, tabId: previousSection, render, cleanup };
    node.__minimaxStudioDashboard?.refresh?.();
    updateResizer();
    render(initialTab ?? prefs.lastSection);
    header.close.focus();
    return drawer;
}

export function refreshStudioDrawer(nodeId) {
    if (activeDrawer?.nodeId !== nodeId) return;
    activeDrawer.render(activeDrawer.tabId);
}

export function dashboardSummaries(controller) {
    const shot = controller.shotDocument();
    const project = controller.projectDocument();
    const shots = shot?.value?.shots?.length ?? 0;
    const staged = shot?.value?.shots?.reduce((count, item) => count + (item?.staging?.length ?? 0), 0) ?? 0;
    const subjects = project?.value?.subjects?.length ?? 0;
    const environments = project?.value?.environments?.length ?? 0;
    const assets = project?.value?.assets?.length ?? 0;
    const active = project?.value?.generations?.reduce((count, generation) => count + (generation?.bindings?.length ?? 0), 0) ?? 0;
    const diagnostics = controller.diagnostics()?.diagnostics?.length ?? 0;
    return { shots, staged, subjects, environments, assets, active, diagnostics };
}

export function studioRequestPreview(controller) {
    const studio = controller.studioProjectDocument?.();
    const shotDocument = controller.shotDocument?.();
    const projectDocument = controller.projectDocument?.();
    const useAggregate = studio?.kind === "v3" && studio.value?.shots?.length > 0;
    const shotsSource = useAggregate ? studio.value.shots : shotDocument?.kind === "v2" ? shotDocument.value?.shots ?? [] : [];
    if (!shotsSource.length) {
        return { authoritative: false, shots: [], total: 0, generationId: "" };
    }
    const project = useAggregate ? studio.value : projectDocument?.kind === "v2" ? projectDocument.value : {};
    const requestedGenerationId = controller.selectedGenerationId?.() ?? "";
    const generationId = requestedGenerationId
        || project.generations?.find((generation) => generation?.id)?.id
        || shotsSource[0]?.generationId
        || "";
    const selected = generationId
        ? shotsSource.filter((shot) => !shot?.generationId || shot.generationId === generationId)
        : shotsSource;
    const subjects = new Map((project.subjects ?? []).map((subject) => [subject.id, subject.name || subject.id]));
    const environments = new Map((project.environments ?? []).map((environment) => [environment.id, environment.name || environment.id]));
    const shots = selected.map((shot, index) => {
        const cast = (shot?.cast ?? shot?.subjects ?? [])
            .filter((item) => item?.presence !== "absent")
            .map((item) => subjects.get(item?.subjectId) || item?.subjectId)
            .filter(Boolean);
        const environment = environments.get(shot?.environment?.environmentId) || shot?.environment?.environmentId || "";
        const dialogue = (shot?.actionBeats ?? []).filter((beat) => String(beat?.dialogue?.text ?? "").trim()).length;
        const references = (shot?.referenceBindings ?? shot?.referenceUses ?? []).length;
        const camera = Boolean(shot?.cameraStart || shot?.cameraPath || shot?.cameraEnd || shot?.cameraMotion);
        return {
            id: shot?.id || `shot.${index + 1}`,
            label: `Shot ${String(index + 1).padStart(2, "0")}`,
            action: String(shot?.action || shot?.openingState || "Action missing").trim(),
            cast, environment, dialogue, references, camera,
        };
    });
    return { authoritative: shots.length > 0, shots, total: shots.length, generationId };
}

export function createStudioDashboard(node, controller) {
    ensureStudioStyles();
    const root = createPanelElement("div", "minimax-h3-dashboard");
    const open = createPanelElement("button", "minimax-h3-dashboard-open");
    open.type = "button";
    const workspaceName = controller.isVisualReferenceDirector ? "Director" : "Studio";
    const primaryDestination = controller.isVisualReferenceDirector ? null : "storyboard";
    const openLabel = controller.isVisualReferenceDirector ? "Open Director" : "Open Studio";
    open.append(createStudioIcon(controller.isVisualReferenceDirector ? "overview" : "shots", 20), createPanelElement("span", "", openLabel));
    open.addEventListener("click", () => {
        if (studioDrawerIsOpenFor(node.id)) closeStudioDrawer(node.id);
        else openStudioDrawer(node, controller, primaryDestination, open);
    });
    root.appendChild(open);
    const strip = createPanelElement("div", "minimax-h3-dashboard-links");
    const definitions = controller.isVisualReferenceDirector ? [
        ["compose", "Compose", "shots", (summary) => summary.shots],
        ["library", "Library", "media", (summary) => summary.assets],
        ["wiring", "Wiring", "wiring", (summary) => `${summary.active}/${summary.assets}`],
        ["look", "Look", "look", () => ""],
        ["review", "Review", "review", (summary) => summary.diagnostics],
    ] : [
        ["storyboard", "Storyboard", "shots", (summary) => summary.shots],
        ["library", "Library", "subjects", (summary) => summary.subjects + summary.environments + summary.assets],
        ["look", "Look", "look", () => ""],
        ["review", "Review & Generate", "review", (summary) => summary.diagnostics],
    ];
    const request = createPanelElement("section", "minimax-h3-node-request");
    const requestHeader = createPanelElement("div", "minimax-h3-node-request-header");
    const requestHeading = createPanelElement("div", "minimax-h3-node-request-heading");
    requestHeading.append(
        createPanelElement("strong", "", "What Prompt Studio sends"),
        createPanelElement("small", "", "Read-only · Studio Project v3 is the request source"),
    );
    const edit = createPanelElement("button", "minimax-h3-node-request-edit", "Edit Storyboard");
    edit.type = "button";
    edit.addEventListener("click", () => openStudioDrawer(node, controller, primaryDestination, edit));
    requestHeader.append(requestHeading, edit);
    const requestList = createPanelElement("div", "minimax-h3-node-request-list");
    const requestFooter = createPanelElement("small", "minimax-h3-node-request-footer");
    request.append(requestHeader, requestList, requestFooter);
    const refresh = () => {
        const summary = dashboardSummaries(controller);
        const preview = studioRequestPreview(controller);
        controller.setBasicPromptVisible?.(!preview.authoritative);
        request.hidden = !preview.authoritative;
        requestList.replaceChildren();
        if (preview.authoritative) {
            for (const shot of preview.shots.slice(0, 3)) {
                const row = createPanelElement("article", "minimax-h3-node-request-shot");
                const copy = createPanelElement("div", "minimax-h3-node-request-copy");
                copy.append(
                    createPanelElement("strong", "", shot.label),
                    createPanelElement("span", "", shot.action),
                );
                const facts = [
                    shot.cast.length ? shot.cast.join(", ") : "No cast",
                    shot.environment || "No environment",
                    shot.dialogue ? `${shot.dialogue} dialogue` : "No dialogue",
                    shot.references ? `${shot.references} shot ref${shot.references === 1 ? "" : "s"}` : "No shot refs",
                    shot.camera ? "Camera set" : "Camera automatic",
                ];
                row.append(copy, createPanelElement("small", "minimax-h3-node-request-facts", facts.join(" · ")));
                requestList.appendChild(row);
            }
            const remaining = preview.total - Math.min(3, preview.total);
            requestFooter.textContent = `${preview.total} Shot${preview.total === 1 ? "" : "s"}${preview.generationId ? ` · ${preview.generationId}` : ""}${remaining ? ` · ${remaining} more in Storyboard` : ""}`;
        }
        const isOpen = studioDrawerIsOpenFor(node.id);
        open.querySelector("span").textContent = isOpen ? `Close ${workspaceName}` : openLabel;
        open.setAttribute("aria-pressed", String(isOpen));
        open.title = isOpen ? `Close ${workspaceName} and return to the workflow` : `Open ${workspaceName}`;
        for (const [id, label, , value] of definitions) {
            const chip = root.querySelector(`[data-studio-tab="${id}"]`);
            if (!chip) continue;
            const count = value(summary);
            chip.querySelector(".minimax-h3-chip-count").textContent = String(count);
            chip.setAttribute("aria-label", count === "" ? label : `${label}: ${count}`);
        }
    };
    for (const [id, label, icon] of definitions) {
        const chip = createPanelElement("button", "minimax-h3-chip");
        chip.type = "button";
        chip.dataset.studioTab = id;
        chip.title = label;
        chip.append(createStudioIcon(icon, 16), createPanelElement("span", "minimax-h3-chip-count"));
        chip.addEventListener("click", () => openStudioDrawer(node, controller, id, chip));
        strip.appendChild(chip);
    }
    root.appendChild(strip);
    root.appendChild(request);
    refresh();
    return { root, refresh };
}
